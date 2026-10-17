"""TASK 72 Phases 2-5 + 7 — source-anchored within-source passage retrieval.

Experiment-only. Never writes to production retrieval or prior task artifacts.

Pipeline (deterministic, no dense, no new tokenizer, no corpus change):

  PHASE 2 algorithm
    1. Global source/unit retrieval exactly as Task-69 (BM25 pool 2000 ->
       Reranker(diversify) top-10 unit tier + SourceIndex metadata fills).
       The R0 rebuild is gated BYTE-EXACT vs frozen task69_rag_evidence.jsonl.
    2. Selected sources = distinct sources of that combined list, ordered by
       first appearance (source_candidate_rank 1..D). Same top source
       candidates the existing system already produced.
    3. For each selected source: BM25Index.search(query, allowed=<that
       source's doc indices>) — same global IDF/tokenizer/normalization,
       candidate set restricted to the source (within_source_rank/score).
    4. Rank within-source units by that BM25 score (deterministic
       (-score, doc_index) tie-break inside BM25Index).
    5. Merge (PRE-REGISTERED policy): round-robin over selected sources in
       source_candidate_rank order — pass p takes each source's within-source
       rank-p unit — until keep slots are filled; then append the Task-69
       metadata-fill units whose source has NO lexical candidates (tail,
       max 3, never displacing unit slots; source-metadata semantics
       unchanged). No per-source hard cap: production diversify also keeps
       excess units ("excess units stay in the list").
    6. Every merged result carries full contract metadata (channel, ranks,
       normalization, provenance) and is validated with validate_result.

  PHASE 3 configs
    R0  EVIDENCE_K=5  TEXT_TRUNC=500    global (Task-69; rebuilt + gated)
    R7  EVIDENCE_K=10 TEXT_TRUNC=1000   global (frozen task71 evidence, re-scored)
    R8  EVIDENCE_K=5  TEXT_TRUNC=500    within-source BM25   <- primary
    R9  EVIDENCE_K=10 TEXT_TRUNC=1000   within-source BM25   (same results as R8,
        wider evidence window; cheap => RUN, not NOT_RUN)

  PHASE 8 pre-registered criteria (stated before results are read):
    A material unit improvement: R8-R0 unit_recall@5 >= +0.05 AND
       unit_mrr >= +0.05
    C selection-limited: unit metrics improve materially but ceiling gain
       < +0.02 and Ev0 reduction < 3
    B source-limited: residual misses are source-miss / corpus-absence /
       zero lexical overlap (candidate miss), not rank depth
    D cost-limited: retrieval runtime > 2x R0 or context median > 1.2x R7

Outputs
  data/evaluation/task72_retrieval_results.jsonl
  data/evaluation/task72_failure_cases.jsonl
  data/evaluation/task72_metrics.json
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import statistics
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "experiments" / "dapt_01" / "evaluation"))

import score_task60  # noqa: E402
from svk_corpus.retrieval import (  # noqa: E402
    BM25Index,
    RetrievalResult,
    load_corpus,
)
from svk_corpus.retrieval.contract import validate_result  # noqa: E402
from svk_corpus.retrieval.normalization import expand_query_text  # noqa: E402
from svk_corpus.retrieval.rerank import Reranker  # noqa: E402
from svk_corpus.retrieval.source_channel import (  # noqa: E402
    SourceUnitExpander,
    build_source_index,
)

# Task-69 builder: reuse its helpers verbatim so rendering/validation cannot drift.
_t69spec = importlib.util.spec_from_file_location(
    "t69build", REPO / "experiments" / "task69" / "build_rag_evidence.py"
)
t69 = importlib.util.module_from_spec(_t69spec)
_t69spec.loader.exec_module(t69)

CASES_PATH = REPO / "data" / "evaluation" / "dapt01_eval_cases.jsonl"
CORPUS_PATH = REPO / "data" / "release" / "rag_corpus.jsonl"
MANIFEST_PATH = REPO / "manifests" / "source_manifest.csv"
FROZEN_EVIDENCE = REPO / "data" / "evaluation" / "task69_rag_evidence.jsonl"
FROZEN_METRICS = REPO / "data" / "evaluation" / "task69_retrieval_metrics.json"
R7_EVIDENCE = REPO / "data" / "evaluation" / "task71_r7_evidence.jsonl"
T70_CASES = REPO / "data" / "evaluation" / "task70_retrieval_failure_cases.jsonl"

OUT_RESULTS = REPO / "data" / "evaluation" / "task72_retrieval_results.jsonl"
OUT_FAILURES = REPO / "data" / "evaluation" / "task72_failure_cases.jsonl"
OUT_METRICS = REPO / "data" / "evaluation" / "task72_metrics.json"

FROZEN_SHA = "06625f72190e3ae130447345afdc04342bd19cb76f842285706480cba7765b81"
TOP_K = 10
POOL = 2000
MAX_METADATA_FILL = 3

CONFIGS = {
    "R0": {"evidence_k": 5, "text_trunc": 500, "mode": "global"},
    "R7": {"evidence_k": 10, "text_trunc": 1000, "mode": "global"},
    "R8": {"evidence_k": 5, "text_trunc": 500, "mode": "within_source"},
    "R9": {"evidence_k": 10, "text_trunc": 1000, "mode": "within_source"},
}

KNOWN_CASES = ["002", "007", "010", "011", "013", "014", "018", "021", "023", "044", "047"]

PHASE8_CRITERIA = {
    "A_material_unit_improvement": (
        "R8-R0 unit_recall_at_5 >= +0.05 AND unit_mrr >= +0.05"
    ),
    "C_selection_limited": (
        "unit metrics improve materially but evidence ceiling gain < +0.02 "
        "and Ev0 reduction < 3"
    ),
    "B_source_limited": (
        "residual unit misses are source-miss / corpus-absence / zero lexical "
        "overlap (candidate miss), not within-source rank depth"
    ),
    "D_cost_limited": (
        "within-source retrieval runtime > 2x R0 global runtime, or R8 context "
        "median > 1.2x R7 context median"
    ),
}


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def unit_key(text_id: str) -> str:
    return text_id.rsplit(":", 1)[0] if text_id.count(":") >= 2 else text_id


def evidence_score_of(case: dict, block: str) -> tuple[float | None, list[str]]:
    groups = case.get("scoring") or []
    if case.get("abstention_case"):
        hits: list[str] = []
        for g in groups:
            for pat in g.get("forbidden_claims", []):
                import re

                if re.search(pat, block, flags=re.IGNORECASE):
                    hits.append(pat)
        return None, hits
    passes = [score_task60.group_pass(g, block) for g in groups]
    return (sum(passes) / len(passes) if passes else None), []


def recall(vals: list[bool | None], k: int) -> float | None:
    if not vals:
        return None
    return round(sum(1.0 for v in vals if v is not None and v <= k) / len(vals), 4)


def mrr(vals: list[int | None]) -> float | None:
    if not vals:
        return None
    return round(sum((1.0 / v) if v else 0.0 for v in vals) / len(vals), 4)


# ---------------------------------------------------------------------------
# result-row builders (mirror Task-69 result dicts exactly, + audit fields)
# ---------------------------------------------------------------------------

def result_row(r, eid: str, rank: int, channel: str, query: str, norm_tokens,
               audit: dict | None = None) -> tuple[dict, object]:
    cr = t69.build_canonical(r, eid, rank, channel, query, norm_tokens)
    violations = validate_result(cr)
    loc = dict(r.doc.locator or {})
    row = {
        "result_id": cr.result_id,
        "text_id": r.doc.text_id,
        "source_id": r.doc.source_id,
        "parent_source_id": r.doc.parent_source_id,
        "retrieval_channel": channel,
        "retrieval_rank": rank,
        "retrieval_score": round(float(r.score), 4),
        "unit_bm25_rank": cr.unit_bm25_rank,
        "unit_bm25_score": cr.unit_bm25_score,
        "metadata_match": cr.metadata_match.__dict__ if cr.metadata_match else None,
        "methods": dict(cr.methods),
        "title": r.doc.title,
        "locator": loc,
        "locator_citation": (loc.get("citation") or "") if isinstance(loc, dict) else "",
        "provenance": {
            "author": r.doc.author,
            "religious_scope": r.doc.religious_scope,
            "religious_scope_confidence": r.doc.religious_scope_confidence,
            "knowledge_layer": r.doc.knowledge_layer,
            "teacher_or_author": r.doc.teacher_or_author,
            "lineage": r.doc.lineage,
            "source_quality": r.doc.source_quality,
            "sect": r.doc.sect,
            "language": r.doc.language,
            "script": r.doc.script,
            "publication_year": r.doc.publication_year,
        },
        "text": r.doc.text,
        "contract_valid": not violations,
        "contract_violations": violations,
    }
    if audit:
        row.update(audit)
    return row, cr


def build_block_and_metrics(case: dict, results_out: list[dict], cards: dict,
                            cfg: dict) -> dict:
    eid = case["example_id"]
    query = case["question"]
    k, trunc = cfg["evidence_k"], cfg["text_trunc"]
    ctx_items = []
    for pos, res in enumerate(results_out[:k], 1):
        ctx_items.append({
            "pos": pos,
            "text_id": res["text_id"],
            "source_id": res["source_id"],
            "title": res["title"],
            "retrieval_channel": res["retrieval_channel"],
            "retrieval_rank": res["retrieval_rank"],
            "retrieval_score": res["retrieval_score"],
            "provenance": res["provenance"],
            "locator_citation": res["locator_citation"],
            "text_truncated": t69.truncate(res["text"], trunc),
        })
    block = t69.build_context_block(ctx_items, cards)
    block_sha = hashlib.sha256(block.encode("utf-8")).hexdigest()
    ev, forbidden = evidence_score_of(case, block)
    return {
        "evidence_k": k,
        "text_trunc": trunc,
        "n_evidence_items": len(ctx_items),
        "context_text": block,
        "context_sha256": block_sha,
        "context_chars": len(block),
        "user_content_chars": len(block) + len(query) + 2,
        "evidence_answer_score": ev,
        "evidence_forbidden_hits": forbidden,
    }


def case_ranks(results_out: list[dict], case: dict) -> tuple[int | None, int | None]:
    prov = case.get("provenance") or {}
    esrc = prov.get("source_id")
    eunits = prov.get("unit_ids") or []
    first = None
    if esrc:
        first = next((i for i, r in enumerate(results_out, 1) if r["source_id"] == esrc), None)
    uhit = None
    for i, r in enumerate(results_out, 1):
        if any(unit_key(r["text_id"]) == u for u in eunits):
            uhit = i
            break
    return first, uhit


def aggregate(per_case: list[dict], cfg: dict) -> dict:
    src = [p for p in per_case if p["expected_source"]]
    unit = [p for p in per_case if p["expected_units"]]
    src_first = [p["source_first_rank"] for p in src]
    unit_hit = [p["unit_hit_rank"] for p in unit]
    scored = [p["evidence_answer_score"] for p in per_case
              if p["evidence_answer_score"] is not None]
    ev_k = cfg["evidence_k"]

    metadata_only = [
        p["example_id"] for p in src
        if p["results_sources_hit"] and p["results_sources_hit_only_metadata"]
    ]
    shum = [
        p["example_id"] for p in unit
        if p["source_first_rank"] is not None and p["unit_hit_rank"] is None
    ]
    zero_hit = [p["example_id"] for p in unit if p["unit_hit_rank"] is None]
    src_zero = [p["example_id"] for p in src if p["source_first_rank"] is None]
    ranking_miss = [
        p["example_id"] for p in unit
        if p["source_first_rank"] is not None and p["unit_hit_rank"] is None
        and p["expected_unit_in_candidate_set"]
    ]
    candidate_miss = [
        p["example_id"] for p in unit
        if not p["expected_unit_in_candidate_set"]
    ]
    width_miss = [
        p["example_id"] for p in unit
        if p["unit_hit_rank"] is not None and ev_k < p["unit_hit_rank"] <= TOP_K
    ]
    return {
        "config": cfg,
        "n_source_level": len(src),
        "source_recall_at_1": recall(src_first, 1),
        "source_recall_at_3": recall(src_first, 3),
        "source_recall_at_5": recall(src_first, 5),
        "source_recall_at_10": recall(src_first, 10),
        "source_mrr": mrr(src_first),
        "source_zero_hit_cases": src_zero,
        "n_unit_labeled": len(unit),
        "unit_recall_at_1": recall(unit_hit, 1),
        "unit_recall_at_3": recall(unit_hit, 3),
        "unit_recall_at_5": recall(unit_hit, 5),
        "unit_recall_at_10": recall(unit_hit, 10),
        "unit_mrr": mrr(unit_hit),
        "unit_zero_hit_cases": zero_hit,
        "zero_hit": len(zero_hit),
        "evidence_ceiling_mean": (
            round(sum(scored) / len(scored), 4) if scored else None
        ),
        "evidence_ceiling_full": sum(1 for s in scored if s == 1.0),
        "ev0_count": sum(1 for s in scored if s == 0.0),
        "ev0_cases": [p["example_id"] for p in per_case
                      if p["evidence_answer_score"] == 0.0],
        "metadata_only_cases": metadata_only,
        "n_metadata_only": len(metadata_only),
        "source_hit_but_unit_miss_cases": shum,
        "n_source_hit_but_unit_miss": len(shum),
        "ranking_miss_cases": ranking_miss,
        "n_ranking_miss": len(ranking_miss),
        "candidate_miss_cases": candidate_miss,
        "n_candidate_miss": len(candidate_miss),
        "selection_width_miss_cases": width_miss,
        "n_selection_width_miss": len(width_miss),
        "abstention_forbidden_hits": sum(
            1 for p in per_case if p["evidence_forbidden_hits"]
        ),
        "contract_violations": sum(
            1 for p in per_case for r in p["results"] if r["contract_violations"]
        ),
        "context_chars": {
            "median": statistics.median(p["context_chars"] for p in per_case),
            "mean": round(statistics.mean(p["context_chars"] for p in per_case), 1),
            "max": max(p["context_chars"] for p in per_case),
        },
        "user_content_chars": {
            "median": statistics.median(p["user_content_chars"] for p in per_case),
            "max": max(p["user_content_chars"] for p in per_case),
        },
        "n_results_median": statistics.median(len(p["results"]) for p in per_case),
    }


def main() -> int:
    t_start = time.time()
    frozen_sha = sha256_file(CASES_PATH)
    if frozen_sha != FROZEN_SHA:
        print(f"STOP: frozen benchmark sha mismatch {frozen_sha}")
        return 3
    log(f"frozen benchmark sha verified {frozen_sha[:16]}…")

    cases = load_jsonl(CASES_PATH)
    cards = t69.load_manifest_cards(MANIFEST_PATH)
    frozen_rows = {r["example_id"]: r for r in load_jsonl(FROZEN_EVIDENCE)}
    frozen_metrics = {p["example_id"]: p for p in
                      json.loads(FROZEN_METRICS.read_text())["per_case"]}
    r7_rows = {r["example_id"]: r for r in load_jsonl(R7_EVIDENCE)}
    t70_rows = {r["case_id"]: r for r in load_jsonl(T70_CASES)}
    if len(cases) != 47 or len(frozen_rows) != 47 or len(r7_rows) != 47:
        print("STOP: expected 47 rows in cases/frozen/R7 inputs")
        return 3

    t0 = time.time()
    docs = load_corpus(CORPUS_PATH, MANIFEST_PATH)
    bm25 = BM25Index(docs, k1=1.5, b=0.75)
    sidx = build_source_index(MANIFEST_PATH)
    expander = SourceUnitExpander(docs)
    diversify = Reranker(strategy="diversify", max_per_source=3)
    src_indices: dict[str, list[int]] = {}
    doc_unit_key: dict[str, str] = {}
    for i, d in enumerate(docs):
        src_indices.setdefault(d.source_id, []).append(i)
        doc_unit_key[d.text_id] = unit_key(d.text_id)
    corpus_unit_keys = set(doc_unit_key.values())
    log(f"corpus {len(docs)} docs, {len(src_indices)} sources, index {time.time()-t0:.1f}s")

    results_rows: list[dict] = []
    per_config_cases: dict[str, list[dict]] = {c: [] for c in CONFIGS}
    runtime = {"global_step_seconds": 0.0, "within_source_seconds": 0.0,
               "merge_and_score_seconds": 0.0, "per_case": []}
    r0_gate_ok = 0
    violations_total: list[dict] = []

    for case in cases:
        eid = case["example_id"]
        query = case["question"]
        prov = case.get("provenance") or {}
        esrc = prov.get("source_id")
        eunits = prov.get("unit_ids") or []

        # ---- global retrieval: identical to Task-69 (full ranking; pool = head) ----
        tg = time.time()
        full = bm25.search(query, top_k=10**9)
        pool = full[:POOL]
        pool_rank = {r.doc.text_id: r.rank for r in pool}
        global_rank = {r.doc.text_id: r.rank for r in full}
        pool_rank_by_unit: dict[str, int] = {}
        global_rank_by_unit: dict[str, int] = {}
        for tid, rank in pool_rank.items():
            pool_rank_by_unit.setdefault(unit_key(tid), rank)
        for tid, rank in global_rank.items():
            global_rank_by_unit.setdefault(unit_key(tid), rank)
        unit_tier = diversify.rerank([
            RetrievalResult(doc=h.doc, score=h.score, rank=h.rank,
                            methods={"bm25": h.rank})
            for h in pool
        ])[:TOP_K]
        unit_ids = {r.doc.text_id for r in unit_tier}
        unit_sids = {r.doc.source_id for r in unit_tier}
        smatches = sidx.search(query, top_k=TOP_K)
        missing = [m for m in smatches if m.source_id not in unit_sids
                   and not m.identifier_only]
        n_fill = min(MAX_METADATA_FILL, len(missing))
        fill = expander.expand(missing[:n_fill], top_k=n_fill)
        keep0 = max(TOP_K - len(fill), 0)
        combined0 = list(unit_tier[:keep0]) + fill
        combined0 = combined0[:TOP_K]
        norm_tokens = tuple(expand_query_text(query))
        runtime["global_step_seconds"] += time.time() - tg

        # ---- R0 results (Task-69 code path) + BYTE-EXACT gate vs frozen ----
        results0 = []
        for i, r in enumerate(combined0, 1):
            ch = t69.channel_of(r, unit_ids)
            row, _ = result_row(r, eid, i, ch, query, norm_tokens)
            results0.append(row)
        m0 = build_block_and_metrics(case, results0, cards, CONFIGS["R0"])
        fr = frozen_rows[eid]
        gate_match = (
            [(r["text_id"], r["retrieval_rank"], r["retrieval_channel"])
             for r in results0]
            == [(r["text_id"], r["retrieval_rank"], r["retrieval_channel"])
                for r in fr["results"]]
            and m0["context_sha256"] == fr["evidence_context"]["sha256"]
        )
        if not gate_match:
            print(f"STOP: R0 rebuild not byte-exact for {eid}")
            return 3
        r0_gate_ok += 1
        # cross-check recomputed ranks vs frozen Task-69 metrics
        fmeta = frozen_metrics[eid]
        first0, uhit0 = case_ranks(results0, case)
        if first0 != fmeta["source_first_rank"] or uhit0 != fmeta["unit_hit_rank"]:
            print(f"STOP: R0 rank mismatch for {eid}: "
                  f"src {first0} vs {fmeta['source_first_rank']}, "
                  f"unit {uhit0} vs {fmeta['unit_hit_rank']}")
            return 3

        # ---- selected sources (same top source candidates, first appearance) ----
        sel: dict[str, int] = {}
        for r in combined0:
            sel.setdefault(r.doc.source_id, len(sel) + 1)

        # ---- within-source BM25 (Phase 2 steps 3-4) ----
        tw = time.time()
        within: dict[str, list] = {}
        within_map: dict[str, dict[str, tuple[int, float]]] = {}
        for sid in sel:
            allowed = src_indices.get(sid, [])
            cands = bm25.search(query, top_k=len(allowed), allowed=allowed) if allowed else []
            within[sid] = cands
            within_map[sid] = {
                unit_key(c.doc.text_id): (c.rank, c.score) for c in cands
            }
        runtime["within_source_seconds"] += time.time() - tw

        # ---- merge (pre-registered round-robin) + fills kept only w/o lex ----
        tm = time.time()
        lex = sorted(
            [(cr, sid) for sid, cr in sel.items() if within[sid]],
            key=lambda x: x[0],
        )
        fills_kept = [f for f in fill
                      if not within.get(f.doc.source_id)]
        keep8 = max(TOP_K - len(fills_kept), 0)
        merged: list[tuple[str, int, object]] = []
        p = 0
        while len(merged) < keep8 and any(p < len(within[sid]) for _, sid in lex):
            for cr, sid in lex:
                if len(merged) >= keep8:
                    break
                if p < len(within[sid]):
                    merged.append((sid, p + 1, within[sid][p]))
            p += 1

        results8 = []
        for i, (sid, wrank, c) in enumerate(merged, 1):
            rr = RetrievalResult(
                doc=c.doc, score=c.score, rank=wrank,
                methods={"bm25": global_rank.get(c.doc.text_id, wrank)},
            )
            rr.extra = type("NS", (), {  # contract: global pool rank/score
                "bm25_rank": pool_rank.get(c.doc.text_id),
                "bm25_score": c.score,
            })()
            audit = {
                "source_candidate_rank": sel[sid],
                "within_source_rank": wrank,
                "within_source_score": round(float(c.score), 6),
                "global_unit_rank": global_rank.get(c.doc.text_id),
                "global_pool_rank": pool_rank.get(c.doc.text_id),
            }
            row, cr = result_row(rr, eid, i, "unit_bm25", query, norm_tokens, audit)
            results8.append(row)
            if row["contract_violations"]:
                violations_total.append({"config": "R8", "result_id": row["result_id"],
                                         "violations": row["contract_violations"]})
        for j, f in enumerate(fills_kept, 1):
            i = len(results8) + 1
            audit = {
                "source_candidate_rank": sel.get(f.doc.source_id),
                "within_source_rank": None,
                "within_source_score": None,
                "global_unit_rank": global_rank.get(f.doc.text_id),
                "global_pool_rank": pool_rank.get(f.doc.text_id),
            }
            row, cr = result_row(f, eid, i, "source_metadata", query, norm_tokens, audit)
            results8.append(row)
            if row["contract_violations"]:
                violations_total.append({"config": "R8", "result_id": row["result_id"],
                                         "violations": row["contract_violations"]})
        results8 = results8[:TOP_K]
        runtime["merge_and_score_seconds"] += time.time() - tm
        runtime["per_case"].append({
            "example_id": eid,
            "n_selected_sources": len(sel),
            "n_lex_sources": len(lex),
            "n_merged": len(results8),
            "n_fills_kept": len(fills_kept),
        })

        # ---- expected-unit analysis in within-source space ----
        esrc_selected = esrc in sel if esrc else False
        unit_within: dict[str, dict] = {}
        in_candidate = False
        for u in eunits:
            wr = ws = None
            if esrc_selected:
                got = within_map.get(esrc, {}).get(u)
                if got:
                    wr, ws = got
            unit_within[u] = {
                "within_source_rank": wr,
                "within_source_score": round(ws, 6) if ws is not None else None,
                "global_pool_rank": pool_rank_by_unit.get(u),
                "global_unit_rank": global_rank_by_unit.get(u),
                "in_corpus": u in corpus_unit_keys,
            }
            if wr is not None:
                in_candidate = True

        # ---- per-config case records ----
        def pack(results_out: list[dict], cfg: dict, extra: dict | None = None) -> dict:
            mb = build_block_and_metrics(case, results_out, cards, cfg)
            first, uhit = case_ranks(results_out, case)
            src_hits = [r for r in results_out if r["source_id"] == esrc] if esrc else []
            rec = {
                "config": cfg,
                "source_first_rank": first,
                "unit_hit_rank": uhit,
                "results": results_out,
                **mb,
                "results_sources_hit": bool(src_hits),
                "results_sources_hit_only_metadata": bool(src_hits) and all(
                    r["retrieval_channel"] == "source_metadata" for r in src_hits),
                "expected_source_selected_r8": esrc_selected if cfg["mode"] == "within_source" else None,
            }
            if extra:
                rec.update(extra)
            return rec

        # candidate-set flags per config
        pool_in = any(pool_rank_by_unit.get(u) is not None for u in eunits) if eunits else False
        rec0 = pack(results0, CONFIGS["R0"],
                    {"expected_unit_in_candidate_set": pool_in,
                     "unit_within_source": unit_within,
                     "selected_sources": sel})
        rec8 = pack(results8, CONFIGS["R8"],
                    {"expected_unit_in_candidate_set": in_candidate,
                     "unit_within_source": unit_within,
                     "selected_sources": sel})
        rec9 = pack(results8, CONFIGS["R9"],
                    {"expected_unit_in_candidate_set": in_candidate,
                     "unit_within_source": unit_within,
                     "selected_sources": sel})

        # R7 from frozen task71 evidence (re-score block independently)
        r7row = r7_rows[eid]
        r7_results = r7row["results"]
        r7_block = r7row["evidence_context"]["text"]
        ev7, forb7 = evidence_score_of(case, r7_block)
        first7, uhit7 = case_ranks(r7_results, case)
        src_hits7 = [r for r in r7_results if r["source_id"] == esrc] if esrc else []
        rec7 = {
            "config": CONFIGS["R7"],
            "source_first_rank": first7,
            "unit_hit_rank": uhit7,
            "results": r7_results,
            "context_text": r7_block,
            "context_sha256": r7row["evidence_context"]["sha256"],
            "context_chars": len(r7_block),
            "user_content_chars": len(r7_block) + len(query) + 2,
            "evidence_answer_score": ev7,
            "evidence_forbidden_hits": forb7,
            "n_evidence_items": r7row["evidence_context"]["n_items"],
            "expected_unit_in_candidate_set": pool_in,
            "results_sources_hit": bool(src_hits7),
            "results_sources_hit_only_metadata": bool(src_hits7) and all(
                r["retrieval_channel"] == "source_metadata" for r in src_hits7),
            "source": "frozen task71_r7_evidence.jsonl (re-scored)",
        }

        for name, rec in (("R0", rec0), ("R7", rec7), ("R8", rec8), ("R9", rec9)):
            per_config_cases[name].append({
                "example_id": eid,
                "category": case["category"],
                "language": case["language"],
                "expected_source": esrc,
                "expected_units": eunits,
                **{k: v for k, v in rec.items() if k != "config"},
            })

        results_rows.append({
            "example_id": eid,
            "category": case["category"],
            "language": case["language"],
            "query": query,
            "expected_source": esrc,
            "expected_units": eunits,
            "selected_sources_r8": sel,
            "configs": {
                "R0": {k: v for k, v in rec0.items() if k != "config"},
                "R7": {k: v for k, v in rec7.items() if k != "config"},
                "R8": {k: v for k, v in rec8.items() if k != "config"},
                "R9": {k: v for k, v in rec9.items() if k != "config"},
            },
        })
        log(f"  {eid} sel={len(sel)} lex={len(lex)} merged={len(results8)} "
            f"r0_u={rec0['unit_hit_rank']} r8_u={rec8['unit_hit_rank']} "
            f"ev0={rec0['evidence_answer_score']}→{rec8['evidence_answer_score']}")

    # ------------------------------------------------------------------
    # aggregates + gates
    # ------------------------------------------------------------------
    aggs = {name: aggregate(rows, CONFIGS[name]) for name, rows in per_config_cases.items()}

    # R7 reference gate: frozen re-score must equal Task-71 published numbers
    r7_gate = (aggs["R7"]["evidence_ceiling_mean"] == 0.7403
               and aggs["R7"]["evidence_ceiling_full"] == 31
               and aggs["R7"]["ev0_count"] == 10)
    if not r7_gate:
        print("STOP: R7 frozen re-score does not match Task-71 published numbers:",
              aggs["R7"]["evidence_ceiling_mean"], aggs["R7"]["evidence_ceiling_full"],
              aggs["R7"]["ev0_count"])
        return 3

    # source retrieval set-invariance: same expected-source presence in top-10
    src_invariant = all(
        (aggs[c]["source_zero_hit_cases"] == aggs["R0"]["source_zero_hit_cases"])
        for c in ("R7", "R8", "R9")
    )
    if not src_invariant:
        print("STOP: source presence not invariant across configs")
        return 3

    # ------------------------------------------------------------------
    # Phase 5: failure-case table
    # ------------------------------------------------------------------
    fail_rows: list[dict] = []
    for row in results_rows:
        eid = row["example_id"]
        t70 = t70_rows.get(eid, {})
        t70_cls = t70.get("classification")
        t70_cls_name = t70.get("class_name")
        eunits = row["expected_units"] or []
        c0 = row["configs"]["R0"]
        c8 = row["configs"]["R8"]
        c7 = row["configs"]["R7"]
        uw = c8.get("unit_within_source") or {}
        within_ranks = {u: (uw.get(u) or {}).get("within_source_rank") for u in eunits}
        pool_ranks = {u: (uw.get(u) or {}).get("global_pool_rank") for u in eunits}
        global_ranks = {u: (uw.get(u) or {}).get("global_unit_rank") for u in eunits}
        in_corpus_units = [u for u in eunits if u in corpus_unit_keys]
        note = ""
        if not eunits:
            note = "UNKNOWN — no expected units recorded in frozen benchmark"
        elif not in_corpus_units:
            note = "UNKNOWN — expected unit not present in corpus (corpus absence)"
        elif row["expected_source"] and row["expected_source"] not in row["selected_sources_r8"]:
            note = "expected source not in selected set (cannot anchor within-source)"
        fail_rows.append({
            "case_id": eid,
            "category": row["category"],
            "task70_classification": t70_cls,
            "task70_class_name": t70_cls_name,
            "in_ev0_set": bool(t70.get("in_ev0_set")),
            "in_known_list": eid.rsplit("-", 1)[-1] in KNOWN_CASES,
            "expected_source": row["expected_source"],
            "expected_units": eunits,
            "global_source_rank_r0": c0["source_first_rank"],
            "global_unit_pool_rank_r0": pool_ranks,
            "global_unit_full_rank_r0": global_ranks,
            "r0_unit_hit_rank": c0["unit_hit_rank"],
            "r7_unit_hit_rank": c7["unit_hit_rank"],
            "r8_source_candidate_rank": (
                row["selected_sources_r8"].get(row["expected_source"])
                if row["expected_source"] else None),
            "r8_within_source_rank": within_ranks,
            "r8_unit_hit_rank": c8["unit_hit_rank"],
            "r9_unit_hit_rank": row["configs"]["R9"]["unit_hit_rank"],
            "r0_evidence_score": c0["evidence_answer_score"],
            "r7_evidence_score": c7["evidence_answer_score"],
            "r8_evidence_score": c8["evidence_answer_score"],
            "unit_recovered_r8_vs_r0": bool(
                eunits and c0["unit_hit_rank"] is None and c8["unit_hit_rank"] is not None),
            "unit_recovered_r7_vs_r0": bool(
                eunits and c0["unit_hit_rank"] is None and c7["unit_hit_rank"] is not None),
            "ev0_recovered_r8": bool(
                c0["evidence_answer_score"] == 0.0
                and (c8["evidence_answer_score"] or 0) > 0),
            "ev0_recovered_r7": bool(
                c0["evidence_answer_score"] == 0.0
                and (c7["evidence_answer_score"] or 0) > 0),
            "note": note,
        })

    # ------------------------------------------------------------------
    # metrics payload
    # ------------------------------------------------------------------
    deltas_r8_r0 = {
        k: round((aggs["R8"][k] or 0) - (aggs["R0"][k] or 0), 4)
        for k in ("unit_recall_at_1", "unit_recall_at_3", "unit_recall_at_5",
                  "unit_recall_at_10", "unit_mrr", "evidence_ceiling_mean")
    }
    deltas_r9_r7 = {
        k: round((aggs["R9"][k] or 0) - (aggs["R7"][k] or 0), 4)
        for k in ("unit_recall_at_1", "unit_recall_at_3", "unit_recall_at_5",
                  "unit_recall_at_10", "unit_mrr", "evidence_ceiling_mean")
    }
    ev0_delta_r8 = aggs["R8"]["ev0_count"] - aggs["R0"]["ev0_count"]

    # expected-unit within-source rank distribution (ranked depth question)
    wr_vals, wr_top5, wr_top10 = [], 0, 0
    for row in results_rows:
        for u in (row["expected_units"] or []):
            got = ((row["configs"]["R8"].get("unit_within_source") or {})
                   .get(u) or {}).get("within_source_rank")
            if got is not None:
                wr_vals.append(got)
                if got <= 5:
                    wr_top5 += 1
                if got <= 10:
                    wr_top10 += 1

    metrics = {
        "task": "TASK 72 — source-anchored within-source passage retrieval",
        "frozen_sha256": frozen_sha,
        "design": {
            "algorithm": (
                "global BM25 (Task-69 exact) -> selected sources by first "
                "appearance -> per-source BM25 (allowed indices, global IDF) -> "
                "round-robin merge by (within_source_rank, source_candidate_rank) "
                "up to top_k - fills_kept; metadata fills kept only for sources "
                "with zero lexical candidates (tail, max 3)"
            ),
            "configs": CONFIGS,
            "phase8_pre_registered_criteria": PHASE8_CRITERIA,
            "no_dense": True,
            "no_new_tokenizer": True,
            "corpus_normalization_unchanged": True,
            "source_metadata_semantics_unchanged": True,
        },
        "gates": {
            "phase1_baseline": "PASS (task72_phase1.py)",
            "r0_byte_exact_vs_task69": f"{r0_gate_ok}/47",
            "r7_frozen_rescore_matches_task71": bool(r7_gate),
            "source_presence_invariant_across_configs": bool(src_invariant),
            "contract_violations": violations_total,
        },
        "aggregate": aggs,
        "deltas": {"R8_minus_R0": deltas_r8_r0, "R9_minus_R7": deltas_r9_r7,
                   "R8_ev0_delta": ev0_delta_r8},
        "within_source_rank_of_expected_units": {
            "n_with_rank": len(wr_vals),
            "median": statistics.median(wr_vals) if wr_vals else None,
            "top5": wr_top5,
            "top10": wr_top10,
            "min": min(wr_vals) if wr_vals else None,
            "max": max(wr_vals) if wr_vals else None,
        },
        "runtime_seconds": {
            "global_step_total": round(runtime["global_step_seconds"], 2),
            "within_source_total": round(runtime["within_source_seconds"], 2),
            "merge_and_score_total": round(runtime["merge_and_score_seconds"], 2),
            "r0_equivalent": round(runtime["global_step_seconds"], 2),
            "r8_equivalent": round(
                runtime["global_step_seconds"] + runtime["within_source_seconds"]
                + runtime["merge_and_score_seconds"], 2),
            "r8_vs_r0_ratio": round(
                (runtime["global_step_seconds"] + runtime["within_source_seconds"]
                 + runtime["merge_and_score_seconds"])
                / runtime["global_step_seconds"], 3),
        },
        "phase5_known_cases": [
            r for r in fail_rows if r["in_known_list"] or r["in_ev0_set"]
            or r["task70_classification"] == "D"
        ],
        "phase5_all_cases_file": str(OUT_FAILURES.relative_to(REPO)),
        "not_measured": [
            "generation e2e scores for R8/R9: NOT_RUN in this script "
            "(retrieval-only phases; BASE generation decided separately in report)",
            "graded passage relevance: NOT_MEASURED (no graded qrels exist)",
            "dense/reranker channels: NOT_APPLICABLE (forbidden by task)",
        ],
    }

    # ------------------------------------------------------------------
    # writes (new files only)
    # ------------------------------------------------------------------
    OUT_RESULTS.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in results_rows),
        encoding="utf-8")
    OUT_FAILURES.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in fail_rows),
        encoding="utf-8")
    OUT_METRICS.write_text(json.dumps(metrics, indent=2, ensure_ascii=False),
                           encoding="utf-8")
    log(f"wrote {OUT_RESULTS.relative_to(REPO)} ({len(results_rows)})")
    log(f"wrote {OUT_FAILURES.relative_to(REPO)} ({len(fail_rows)})")
    log(f"wrote {OUT_METRICS.relative_to(REPO)}")

    print("\n=== headline aggregates ===")
    for name in ("R0", "R7", "R8", "R9"):
        a = aggs[name]
        print(f"{name}: srcR@5={a['source_recall_at_5']} srcR@10={a['source_recall_at_10']} "
              f"unitR@5={a['unit_recall_at_5']} unitR@10={a['unit_recall_at_10']} "
              f"unitMRR={a['unit_mrr']} ceiling={a['evidence_ceiling_mean']}/"
              f"{a['evidence_ceiling_full']} ev0={a['ev0_count']} "
              f"width_miss={a['n_selection_width_miss']} rank_miss={a['n_ranking_miss']} "
              f"cand_miss={a['n_candidate_miss']}")
    print("R8-R0 deltas:", json.dumps(deltas_r8_r0))
    print("R9-R7 deltas:", json.dumps(deltas_r9_r7))
    print("within-source ranks of expected units:",
          json.dumps(metrics["within_source_rank_of_expected_units"]))
    print("runtime:", json.dumps(metrics["runtime_seconds"]))
    print(f"total wall {time.time() - t_start:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

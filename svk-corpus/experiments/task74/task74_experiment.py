"""TASK 74 Phases 4-11 — dense retrieval, RRF hybrid, complementarity, safety.

Experiment-only. Never writes production retrieval or prior task artifacts.
Dense index is experiment-local (experiments/task74/dense_index/).

Configs (all evidence_k=5 / text_trunc=500 — Task-69 evidence width):
  H1_BM25     governed BM25 + source metadata (Task-69/72 R0, byte-exact gated)
  H2_DENSE    BAAI/bge-m3 cosine top-10 only (channel=dense)
  H3_RRF60    deterministic RRF(BM25, Dense), k=60  <- primary hybrid
  H3_RRF20    same, k=20 (sensitivity)
  H4_RRF60    H3 + Task-69 source-metadata fills (source metadata preserved)
  H4_RRF20    same, k=20

RRF (pre-registered): score(d) = sum over signals present of 1/(k + rank),
ranks 1-based, FULL lists (BM25 = full positive-score ranking; Dense = all
164,238 docs). Sort key: (-score, bm25_rank or INF, dense_rank or INF,
doc_index) — deterministic, no query expansion, no within-source BM25, no
max-score fusion.

Pre-registered decision thresholds:
  material_unit_delta       >= +0.05 unit_recall@5 vs H1
  source_guardrail_abs      source_recall@5 >= 0.90
  ceiling_must_exceed       evidence_ceiling_mean > 0.6318
  sect_consistency_drop_max <= 0.05 vs H1 (mean top-10 expected-sect share)
  language_source5_drop_max <= 0.10 worst-language source@5 drop vs H1
  bm25_miss_recovery_min    >= 5 H1 unit-misses@10 recovered by the config

Verdicts: RECOMMEND_HYBRID (a pre-registered H3/H4 config meets all five
task conditions), RECOMMEND_DENSE (H2 meets unit/source/ceiling/sect
conditions without hybrid), KEEP_BM25 (otherwise). The five task conditions
are applied to every pre-registered config; both k values were fixed before
any results (k=60 primary at write time, k=20 sensitivity).

Outputs
  data/evaluation/task74_dense_results.jsonl      (dense top-20 per query)
  data/evaluation/task74_hybrid_results.jsonl     (all-config top-10 rows)
  data/evaluation/task74_metrics.json
  data/evaluation/task74_complementarity.json
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "experiments" / "dapt_01" / "evaluation"))
sys.path.insert(0, str(REPO / "experiments" / "task72"))
sys.path.insert(0, str(REPO / "experiments" / "task73"))

import score_task60  # noqa: E402
from svk_corpus.retrieval import (  # noqa: E402
    BM25Index,
    RetrievalResult,
    load_corpus,
)
from svk_corpus.retrieval.contract import validate_result  # noqa: E402
from svk_corpus.retrieval.rerank import Reranker  # noqa: E402
from svk_corpus.retrieval.source_channel import (  # noqa: E402
    SourceUnitExpander,
    build_source_index,
)

import task72_experiment as t72  # noqa: E402
import task73_phase1 as p1  # noqa: E402

t69 = t72.t69

DENSE_DIR = REPO / "experiments" / "task74" / "dense_index"
INDEX_META = DENSE_DIR / "index_meta.json"
CORPUS_EMB = DENSE_DIR / "corpus_emb.f16.npy"
QUERIES_EMB = DENSE_DIR / "queries_emb.f32.npy"

OUT_DENSE = REPO / "data" / "evaluation" / "task74_dense_results.jsonl"
OUT_HYBRID = REPO / "data" / "evaluation" / "task74_hybrid_results.jsonl"
OUT_METRICS = REPO / "data" / "evaluation" / "task74_metrics.json"
OUT_COMPL = REPO / "data" / "evaluation" / "task74_complementarity.json"

RRF_KS = (60, 20)
PRIMARY_K = 60
KNOWN_CASES = ["002", "007", "010", "011", "013", "014", "018", "021",
               "023", "044", "047"]

CFG = {
    "H1_BM25": {"evidence_k": 5, "text_trunc": 500, "mode": "global"},
    "H2_DENSE": {"evidence_k": 5, "text_trunc": 500, "mode": "dense"},
    "H3_RRF60": {"evidence_k": 5, "text_trunc": 500, "mode": "rrf"},
    "H3_RRF20": {"evidence_k": 5, "text_trunc": 500, "mode": "rrf"},
    "H4_RRF60": {"evidence_k": 5, "text_trunc": 500, "mode": "rrf_meta"},
    "H4_RRF20": {"evidence_k": 5, "text_trunc": 500, "mode": "rrf_meta"},
}

THRESHOLDS = {
    "material_unit_delta": 0.05,
    "source_guardrail_abs": 0.90,
    "ceiling_must_exceed": 0.6318,
    "sect_consistency_drop_max": 0.05,
    "language_source5_drop_max": 0.10,
    "bm25_miss_recovery_min": 5,
}

INF = 10 ** 9


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def vm_rss_mb() -> float:
    for ln in Path("/proc/self/status").read_text().splitlines():
        if ln.startswith("VmRSS:"):
            return round(int(ln.split()[1]) / 1024, 1)
    return -1.0


def unit_key(text_id: str) -> str:
    return t72.unit_key(text_id)


def _mode(vals: list) -> str | None:
    if not vals:
        return None
    counts: dict = {}
    for v in vals:
        counts[v] = counts.get(v, 0) + 1
    return max(counts.items(), key=lambda kv: kv[1])[0]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class NS:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def result_row74(r, eid: str, rank: int, channel: str, query: str,
                 norm_tokens: tuple, dense: tuple[int, float] | None = None,
                 audit: dict | None = None) -> tuple[dict, object]:
    """Task-72 result_row + dense channel fields (contract-validated)."""
    cr = t69.build_canonical(r, eid, rank, channel, query, norm_tokens)
    if channel == "dense":
        cr.dense_rank = int(dense[0])
        cr.dense_score = float(dense[1])
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
        "dense_rank": cr.dense_rank,
        "dense_score": (round(float(cr.dense_score), 6)
                        if cr.dense_score is not None else None),
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


def pack74(case: dict, results_out: list[dict], cards: dict, cfg: dict,
           extra: dict) -> dict:
    mb = t72.build_block_and_metrics(case, results_out, cards, cfg)
    first, uhit = t72.case_ranks(results_out, case)
    prov = case.get("provenance") or {}
    esrc = prov.get("source_id")
    src_hits = [r for r in results_out if r["source_id"] == esrc] if esrc else []
    return {
        "example_id": case["example_id"],
        "category": case["category"],
        "language": case["language"],
        "expected_source": esrc,
        "expected_units": prov.get("unit_ids") or [],
        "config": cfg,
        "source_first_rank": first,
        "unit_hit_rank": uhit,
        "results": results_out,
        **mb,
        "results_sources_hit": bool(src_hits),
        "results_sources_hit_only_metadata": bool(src_hits) and all(
            r["retrieval_channel"] == "source_metadata" for r in src_hits),
        **extra,
    }


def rrf_fuse(bm25_rank: dict[str, int], dense_rank_of: np.ndarray,
             k: int, tid2idx: dict[str, int], n: int) -> list[int]:
    """Full-list RRF -> doc indices in fused order (deterministic ties)."""
    score = 1.0 / (k + dense_rank_of.astype(np.float64))
    bmr = np.full(n, INF, dtype=np.int64)
    for tid, r in bm25_rank.items():
        di = tid2idx.get(tid)
        if di is not None:
            score[di] += 1.0 / (k + r)
            bmr[di] = r
    order = np.lexsort((np.arange(n), dense_rank_of, bmr, -score))
    return order


def main() -> int:
    t_start = time.time()
    if sha256_file(t72.CASES_PATH) != t72.FROZEN_SHA:
        print("STOP: frozen benchmark sha mismatch")
        return 3
    cases = t72.load_jsonl(t72.CASES_PATH)
    cards = t69.load_manifest_cards(t72.MANIFEST_PATH)
    if len(cases) != 47 or not INDEX_META.exists() or not CORPUS_EMB.exists():
        print("STOP: cases!=47 or dense index missing")
        return 3
    meta = json.loads(INDEX_META.read_text())
    log(f"index meta: {meta['model_id']} rev={str(meta['model_revision'])[:12]} "
        f"dim={meta['embedding_dim']} build={meta['runtime']['corpus_encode_s']}s")

    # ---- stack (same constructors as Task-69; cost probed separately) ----
    rss0 = vm_rss_mb()
    t0 = time.time()
    docs = load_corpus(t72.CORPUS_PATH, t72.MANIFEST_PATH)
    rss_docs = vm_rss_mb()
    t0b = time.time()
    bm25 = BM25Index(docs, k1=1.5, b=0.75)
    bm25_build_s = time.time() - t0b
    rss_bm25 = vm_rss_mb()
    sidx = build_source_index(t72.MANIFEST_PATH)
    expander = SourceUnitExpander(docs)
    diversify = Reranker(strategy="diversify", max_per_source=3)
    corpus_load_s = t0b - t0
    log(f"corpus {len(docs)} docs load {corpus_load_s:.1f}s, "
        f"bm25 build {bm25_build_s:.1f}s, rss {rss0}->{rss_docs}->{rss_bm25} MB")

    # ---- alignment: local search_text/doc-id/query shas vs index meta ----
    text_sha = hashlib.sha256()
    id_sha = hashlib.sha256()
    for d in docs:
        text_sha.update(d.search_text.encode("utf-8"))
        id_sha.update(d.text_id.encode("utf-8"))
    q_sha = hashlib.sha256()
    for c in cases:
        q_sha.update(c["question"].encode("utf-8"))
    al = meta["alignment"]
    problems = []
    if text_sha.hexdigest() != al["corpus_text_sha256"]:
        problems.append("corpus_text_sha256 mismatch")
    if id_sha.hexdigest() != al["doc_ids_sha256"]:
        problems.append("doc_ids_sha256 mismatch")
    if q_sha.hexdigest() != al["queries_sha256"]:
        problems.append("queries_sha256 mismatch")
    if al["doc_count"] != len(docs):
        problems.append(f"doc_count {al['doc_count']} != {len(docs)}")
    if problems:
        print("STOP: dense index alignment failure: " + "; ".join(problems))
        return 3
    log("alignment shas verified (text/ids/queries/doc_count)")

    # ---- dense matrices ----
    t0 = time.time()
    emb = np.load(CORPUS_EMB).astype(np.float32)
    nrm = np.linalg.norm(emb, axis=1, keepdims=True)
    nrm[nrm == 0] = 1.0
    emb /= nrm
    q_emb = np.load(QUERIES_EMB).astype(np.float32)
    qn = np.linalg.norm(q_emb, axis=1, keepdims=True)
    qn[qn == 0] = 1.0
    q_emb /= qn
    load_s = time.time() - t0
    n = emb.shape[0]
    index_bytes = CORPUS_EMB.stat().st_size + QUERIES_EMB.stat().st_size
    log(f"index loaded {emb.shape} fp32 renorm in {load_s:.1f}s, "
        f"disk {index_bytes/2**20:.0f} MiB, rss {vm_rss_mb()} MB")

    tid2idx = {d.text_id: i for i, d in enumerate(docs)}
    unit_docs: dict[str, list[int]] = {}
    src_docs: dict[str, list[int]] = {}
    for i, d in enumerate(docs):
        unit_docs.setdefault(unit_key(d.text_id), []).append(i)
        src_docs.setdefault(d.source_id, []).append(i)
    doc_unit = [unit_key(d.text_id) for d in docs]
    doc_src = [d.source_id for d in docs]

    # ---- H1: exact Task-69 R0 (byte-exact gated) ----
    t0 = time.time()
    h1_cases, byte_exact = p1.build_r0_pipeline(cases, cards, bm25, sidx,
                                                expander, diversify)
    h1_s = time.time() - t0
    if byte_exact != 47:
        print(f"STOP: H1 rebuild not byte-exact ({byte_exact}/47)")
        return 3
    h1_agg = t72.aggregate(h1_cases, CFG["H1_BM25"])
    log(f"H1 byte-exact {byte_exact}/47 in {h1_s:.1f}s; "
        f"src@5={h1_agg['source_recall_at_5']} unit@5={h1_agg['unit_recall_at_5']} "
        f"ceiling={h1_agg['evidence_ceiling_mean']} ev0={h1_agg['ev0_count']}")

    # ---- Phases 4-6: dense retrieval + RRF hybrids per case ----
    dense_rows: list[dict] = []
    per_cfg: dict[str, list[dict]] = {k: [] for k in CFG}
    dense_search_ms: list[float] = []
    bm25_search_ms: list[float] = []
    fuse_ms: list[float] = []
    dense_full_unit_rank: dict[str, int | None] = {}
    dense_full_src_rank: dict[str, int | None] = {}
    bm25_full_unit_rank: dict[str, int | None] = {}
    fusion_audit: dict[str, dict] = {}
    violations_total: list[dict] = []

    for idx, case in enumerate(cases):
        eid = case["example_id"]
        query = case["question"]
        prov = case.get("provenance") or {}
        esrc = prov.get("source_id")
        eunits = prov.get("unit_ids") or []
        norm_tokens = tuple(t72.expand_query_text(query))

        # dense: full ordering + ranks
        t0 = time.time()
        scores = emb @ q_emb[idx]
        order = np.argsort(-scores, kind="stable")
        dense_search_ms.append((time.time() - t0) * 1000)
        rank_of = np.empty(n, dtype=np.int64)
        rank_of[order] = np.arange(1, n + 1)

        # dense artifact top-20
        for dr in range(1, 21):
            di = int(order[dr - 1])
            dense_rows.append({
                "example_id": eid,
                "dense_rank": dr,
                "text_id": docs[di].text_id,
                "unit_key": doc_unit[di],
                "source_id": doc_src[di],
                "dense_score": round(float(scores[di]), 6),
                "is_expected_unit": doc_unit[di] in eunits,
                "is_expected_source": bool(esrc) and doc_src[di] == esrc,
            })

        # full-list expected ranks (dense)
        du = [int(rank_of[i]) for u in eunits for i in unit_docs.get(u, [])]
        dense_full_unit_rank[eid] = min(du) if du else None
        ds = [int(rank_of[i]) for i in src_docs.get(esrc, [])] if esrc else []
        dense_full_src_rank[eid] = min(ds) if ds else None

        # bm25 full ranking (same call shape as Task-69/72)
        t0 = time.time()
        full = bm25.search(query, top_k=10 ** 9)
        bm25_search_ms.append((time.time() - t0) * 1000)
        bm25_rank = {r.doc.text_id: r.rank for r in full}
        bm25_score = {r.doc.text_id: r.score for r in full}
        bm25_unit_rank = {}
        for tid, rk in bm25_rank.items():
            bm25_unit_rank.setdefault(unit_key(tid), rk)
        bu = [bm25_unit_rank.get(u) for u in eunits if bm25_unit_rank.get(u)]
        bm25_full_unit_rank[eid] = min(bu) if bu else None

        # ---- H2: dense-only top-10 ----
        results2 = []
        for i in range(1, 11):
            di = int(order[i - 1])
            rr = RetrievalResult(doc=docs[di], score=float(scores[di]), rank=i,
                                 methods={"dense": i})
            row, _ = result_row74(rr, eid, i, "dense", query, norm_tokens,
                                  dense=(i, float(scores[di])))
            results2.append(row)
            if row["contract_violations"]:
                violations_total.append({"config": "H2_DENSE",
                                         "result_id": row["result_id"],
                                         "violations": row["contract_violations"]})
        per_cfg["H2_DENSE"].append(pack74(
            case, results2, cards, CFG["H2_DENSE"],
            {"expected_unit_in_candidate_set": any(u in unit_docs for u in eunits)}))

        # ---- RRF per k, H3 + H4 ----
        for k in RRF_KS:
            t0 = time.time()
            fused = rrf_fuse(bm25_rank, rank_of, k, tid2idx, n)
            fuse_ms.append((time.time() - t0) * 1000)
            fused10 = [int(x) for x in fused[:10]]
            tier = []
            for i, di in enumerate(fused10, 1):
                tid = docs[di].text_id
                dr = int(rank_of[di])
                rrf_score = float(
                    (1.0 / (k + dr))
                    + ((1.0 / (k + bm25_rank[tid])) if tid in bm25_rank else 0.0)
                )
                in_bm25 = tid in bm25_rank
                methods = {"dense": dr}
                if in_bm25:
                    methods["bm25"] = bm25_rank[tid]
                rr = RetrievalResult(doc=docs[di], score=rrf_score, rank=i,
                                     methods=methods)
                if in_bm25:
                    rr.extra = NS(bm25_rank=bm25_rank[tid],
                                  bm25_score=float(bm25_score[tid]))
                tier.append((rr, di, in_bm25, dr))

            results3 = []
            for i, (rr, di, in_bm25, dr) in enumerate(tier, 1):
                if in_bm25:
                    row, _ = result_row74(rr, eid, i, "unit_bm25", query,
                                          norm_tokens)
                    row["dense_rank"] = dr
                    row["dense_score"] = round(float(scores[di]), 6)
                else:
                    row, _ = result_row74(rr, eid, i, "dense", query,
                                          norm_tokens, dense=(dr, float(scores[di])))
                results3.append(row)
                if row["contract_violations"]:
                    violations_total.append(
                        {"config": f"H3_RRF{k}", "result_id": row["result_id"],
                         "violations": row["contract_violations"]})

            # H4: Task-69 source-metadata fills over the fused tier
            fused_ids = {rr.doc.text_id for rr, *_ in tier}
            fused_sids = {rr.doc.source_id for rr, *_ in tier}
            smatches = sidx.search(query, top_k=t72.TOP_K)
            missing = [m for m in smatches
                       if m.source_id not in fused_sids and not m.identifier_only]
            n_fill = min(t72.MAX_METADATA_FILL, len(missing))
            fill = expander.expand(missing[:n_fill], top_k=n_fill)
            keep = max(t72.TOP_K - len(fill), 0)
            combined = ([rr for rr, *_ in tier[:keep]] + list(fill))[:t72.TOP_K]

            results4 = []
            for i, rr in enumerate(combined, 1):
                if i <= keep:
                    di = tid2idx[rr.doc.text_id]
                    dr = int(rank_of[di])
                    if rr.doc.text_id in bm25_rank:
                        row, _ = result_row74(rr, eid, i, "unit_bm25", query,
                                              norm_tokens)
                        row["dense_rank"] = dr
                        row["dense_score"] = round(float(scores[di]), 6)
                    else:
                        row, _ = result_row74(rr, eid, i, "dense", query,
                                              norm_tokens,
                                              dense=(dr, float(scores[di])))
                else:
                    ch = t69.channel_of(rr, fused_ids)
                    row, _ = result_row74(rr, eid, i, ch, query, norm_tokens)
                results4.append(row)
                if row["contract_violations"]:
                    violations_total.append(
                        {"config": f"H4_RRF{k}", "result_id": row["result_id"],
                         "violations": row["contract_violations"]})

            cand_ok = any(u in unit_docs for u in eunits)
            if k == PRIMARY_K:
                fusion_audit[eid] = {
                    "k": k,
                    "n_bm25_positive": len(bm25_rank),
                    "h3_fused_top10_in_bm25": sum(1 for _, _, b, _ in tier if b),
                    "h4_n_fills": len(fill),
                }
            per_cfg[f"H3_RRF{k}"].append(pack74(
                case, results3, cards, CFG[f"H3_RRF{k}"],
                {"expected_unit_in_candidate_set": cand_ok}))
            per_cfg[f"H4_RRF{k}"].append(pack74(
                case, results4, cards, CFG[f"H4_RRF{k}"],
                {"expected_unit_in_candidate_set": cand_ok}))

        if (idx + 1) % 10 == 0:
            log(f"  cases {idx+1}/47 dense_search mean="
                f"{statistics.mean(dense_search_ms):.1f}ms")

    # ---- aggregates (Phases 5/6/9) ----
    aggs = {"H1_BM25": h1_agg}
    for name in ("H2_DENSE", "H3_RRF60", "H3_RRF20", "H4_RRF60", "H4_RRF20"):
        aggs[name] = t72.aggregate(per_cfg[name], CFG[name])

    # dense-only @20 extras (full-list ranks, labeled denominators only)
    unit_vals = [dense_full_unit_rank[c["example_id"]] for c in cases
                 if (c.get("provenance") or {}).get("unit_ids")]
    src_vals = [dense_full_src_rank[c["example_id"]] for c in cases
                if (c.get("provenance") or {}).get("source_id")]
    du20 = [v for v in unit_vals if v is not None]
    ds20 = [v for v in src_vals if v is not None]
    aggs["H2_DENSE"]["unit_recall_at_20"] = t72.recall(unit_vals, 20)
    aggs["H2_DENSE"]["source_recall_at_20"] = t72.recall(src_vals, 20)
    aggs["H2_DENSE"]["unit_full_rank_median_in_corpus"] = statistics.median(du20)
    aggs["H2_DENSE"]["unit_full_rank_n_in_corpus"] = len(du20)
    aggs["H2_DENSE"]["unit_full_rank_n_labeled"] = len(unit_vals)
    aggs["H2_DENSE"]["source_full_rank_median_in_corpus"] = statistics.median(ds20)
    aggs["H2_DENSE"]["source_full_rank_n_in_corpus"] = len(ds20)
    aggs["H2_DENSE"]["source_full_rank_n_labeled"] = len(src_vals)

    unit_cases = [c for c in cases if (c.get("provenance") or {}).get("unit_ids")]
    log("aggregates: " + json.dumps({
        k: {"src5": v["source_recall_at_5"], "u5": v["unit_recall_at_5"],
            "mrr": v["unit_mrr"], "ceil": v["evidence_ceiling_mean"],
            "ev0": v["ev0_count"]}
        for k, v in aggs.items()}))

    # ---- Phase 7: complementarity ----
    h1_by = {p["example_id"]: p for p in h1_cases}
    h2_by = {p["example_id"]: p for p in per_cfg["H2_DENSE"]}
    h3_by = {p["example_id"]: p for p in per_cfg["H3_RRF60"]}

    def classify(k: int) -> dict:
        both = bm25_only = dense_only = neither = 0
        lists = {"both": [], "bm25_only": [], "dense_only": [], "neither": []}
        for c in unit_cases:
            eid = c["example_id"]
            u1 = h1_by[eid]["unit_hit_rank"]
            u2 = h2_by[eid]["unit_hit_rank"]
            s1 = u1 is not None and u1 <= k
            s2 = u2 is not None and u2 <= k
            if s1 and s2:
                both += 1
                lists["both"].append(eid)
            elif s1:
                bm25_only += 1
                lists["bm25_only"].append(eid)
            elif s2:
                dense_only += 1
                lists["dense_only"].append(eid)
            else:
                neither += 1
                lists["neither"].append(eid)
        n = len(unit_cases)
        return {"n": n, "both": both, "bm25_only": bm25_only,
                "dense_only": dense_only, "neither": neither,
                "both_pct": round(100 * both / n, 1),
                "bm25_only_pct": round(100 * bm25_only / n, 1),
                "dense_only_pct": round(100 * dense_only / n, 1),
                "neither_pct": round(100 * neither / n, 1),
                "lists": lists}

    compl_at5 = classify(5)
    compl_at10 = classify(10)

    # H1-miss recovery by H2 and H3 (unit not in H1 top-10 -> any hit)
    h1_miss10 = [c["example_id"] for c in unit_cases
                 if h1_by[c["example_id"]]["unit_hit_rank"] is None]
    recov = {
        "h1_unit_miss_at10": h1_miss10,
        "n_h1_unit_miss_at10": len(h1_miss10),
        "recovered_by_H2": [e for e in h1_miss10
                            if h2_by[e]["unit_hit_rank"] is not None],
        "recovered_by_H3_RRF60": [e for e in h1_miss10
                                  if h3_by[e]["unit_hit_rank"] is not None],
    }
    recov["recovered_by_H2_at5"] = [e for e in h1_miss10
                                    if (h2_by[e]["unit_hit_rank"] or 99) <= 5]
    recov["recovered_by_H3_RRF60_at5"] = [
        e for e in h1_miss10 if (h3_by[e]["unit_hit_rank"] or 99) <= 5]
    # new misses introduced (H1 hit <=10, config miss)
    recov["new_unit_miss_H2"] = [
        e for e in (c["example_id"] for c in unit_cases)
        if h1_by[e]["unit_hit_rank"] is not None
        and h2_by[e]["unit_hit_rank"] is None]
    recov["new_unit_miss_H3_RRF60"] = [
        e for e in (c["example_id"] for c in unit_cases)
        if h1_by[e]["unit_hit_rank"] is not None
        and h3_by[e]["unit_hit_rank"] is None]

    # known failure cases: expected-unit dense rank (do not invent units)
    known = {}
    for kn in KNOWN_CASES:
        eid = f"DAPT01EVAL-{kn}"
        case = next(c for c in cases if c["example_id"] == eid)
        eunits = (case.get("provenance") or {}).get("unit_ids") or []
        known[eid] = {
            "expected_units": eunits,
            "dense_full_rank": dense_full_unit_rank.get(eid),
            "dense_hit_at5": (dense_full_unit_rank.get(eid) or 99) <= 5,
            "dense_hit_at10": (dense_full_unit_rank.get(eid) or 99) <= 10,
            "dense_hit_at20": (dense_full_unit_rank.get(eid) or 99) <= 20,
            "bm25_full_unit_rank": bm25_full_unit_rank.get(eid),
            "unit_hit_rank": {
                "H1_BM25": h1_by[eid]["unit_hit_rank"],
                "H2_DENSE": h2_by[eid]["unit_hit_rank"],
                "H3_RRF60": h3_by[eid]["unit_hit_rank"],
            },
        }

    # ---- Phase 8: sect / language safety ----
    unit_docs_set = unit_docs
    expected_sect: dict[str, str | None] = {}
    for case in cases:
        eid = case["example_id"]
        prov = case.get("provenance") or {}
        eunits = prov.get("unit_ids") or []
        esrc = prov.get("source_id")
        sects = [docs[i].sect for u in eunits for i in unit_docs_set.get(u, [])]
        if not sects and esrc:
            sects = [docs[i].sect for i in src_docs.get(esrc, [])]
        expected_sect[eid] = _mode(sects)

    def sect_consistency(per_case: list[dict]) -> dict:
        vals, missing = [], []
        for p in per_case:
            es = expected_sect.get(p["example_id"])
            if not es:
                missing.append(p["example_id"])
                continue
            hit = sum(1 for r in p["results"] if r["provenance"]["sect"] == es)
            vals.append(hit / len(p["results"]))
        return {"mean_top10_expected_sect_share":
                round(statistics.mean(vals), 4) if vals else None,
                "n": len(vals), "no_expected_sect": missing}

    sect_tbl = {name: sect_consistency(
        h1_cases if name == "H1_BM25" else per_cfg[name]) for name in CFG}

    def by_language(per_case: list[dict]) -> dict:
        out: dict[str, dict] = {}
        for lang in ("en", "hi", "gu"):
            sub = [p for p in per_case if p["language"] == lang]
            if not sub:
                continue
            src = [p for p in sub if p["expected_source"]]
            unit = [p for p in sub if p["expected_units"]]
            out[lang] = {
                "n": len(sub),
                "source_recall_at_5": t72.recall(
                    [p["source_first_rank"] for p in src], 5),
                "unit_recall_at_5": t72.recall(
                    [p["unit_hit_rank"] for p in unit], 5),
            }
        return out

    lang_tbl = {name: by_language(
        h1_cases if name == "H1_BM25" else per_cfg[name]) for name in CFG}

    # Sthanakavasi subgroup (expected sect == STHANAKAVASI)
    sth = [c["example_id"] for c in cases
           if expected_sect.get(c["example_id"]) == "STHANAKAVASI"]

    def sth_src5(per_case: list[dict]) -> float | None:
        vals = [p["source_first_rank"] for p in per_case
                if p["example_id"] in sth and p["expected_source"]]
        return t72.recall(vals, 5)

    sth_tbl = {name: sth_src5(h1_cases if name == "H1_BM25" else per_cfg[name])
               for name in CFG}

    # source attribution changes vs H1
    src_changes: dict[str, dict] = {}
    for name in ("H2_DENSE", "H3_RRF60", "H4_RRF60"):
        pc = per_cfg[name]
        regressed, improved = [], []
        for p in pc:
            b = h1_by[p["example_id"]]["source_first_rank"]
            a = p["source_first_rank"]
            if a is None and b is None:
                continue
            if a is None or (b is not None and a > b):
                regressed.append({"example_id": p["example_id"],
                                  "h1": b, name: a})
            elif b is None or a < b:
                improved.append({"example_id": p["example_id"],
                                 "h1": b, name: a})
        src_changes[name] = {"n_regressed": len(regressed),
                             "n_improved": len(improved),
                             "regressed": regressed, "improved": improved}

    # ---- Phase 10: cost ----
    dense_cost = {
        "model_id": meta["model_id"],
        "model_revision": meta["model_revision"],
        "index_build_seconds": meta["runtime"]["corpus_encode_s"],
        "index_build_docs_per_s": meta["runtime"]["corpus_docs_per_s"],
        "index_disk_bytes": CORPUS_EMB.stat().st_size,
        "index_disk_mib": round(CORPUS_EMB.stat().st_size / 2**20, 1),
        "query_encode_batch_mean_ms": round(
            meta["runtime"]["query_encode_s"] / meta["runtime"]["queries"] * 1000, 2),
        "local_search_ms": {
            "mean": round(statistics.mean(dense_search_ms), 2),
            "p50": round(statistics.median(dense_search_ms), 2),
            "max": round(max(dense_search_ms), 2)},
        "peak_vram_mb_embed": meta["peak_vram_mb"],
        "peak_ram_mb_embed": meta["peak_ram_mb"],
        "fp32_matrix_ram_mb": round(emb.nbytes / 2**20, 0),
    }
    bm25_cost = {
        "index_build_seconds": round(bm25_build_s, 2),
        "corpus_load_seconds": round(corpus_load_s, 2),
        "rss_before_mb": rss0,
        "rss_after_docs_mb": rss_docs,
        "rss_after_bm25_mb": rss_bm25,
        "bm25_index_rss_delta_mb": round(rss_bm25 - rss_docs, 1),
        "corpus_file_bytes": t72.CORPUS_PATH.stat().st_size,
        "query_search_ms": {
            "mean": round(statistics.mean(bm25_search_ms), 2),
            "p50": round(statistics.median(bm25_search_ms), 2),
            "max": round(max(bm25_search_ms), 2)},
        "rrf_fuse_ms": {
            "mean": round(statistics.mean(fuse_ms), 2),
            "p50": round(statistics.median(fuse_ms), 2)},
        "h1_pipeline_seconds": round(h1_s, 1),
        "local_peak_ram_mb": vm_rss_mb(),
    }

    # ---- Phase 11: decision gate (pre-registered) ----
    def gate_for(name: str) -> dict:
        a = aggs[name]
        h1 = aggs["H1_BM25"]
        unit_delta = round((a["unit_recall_at_5"] or 0)
                           - (h1["unit_recall_at_5"] or 0), 4)
        src5 = a["source_recall_at_5"]
        ceil_ok = ((a["evidence_ceiling_mean"] or 0)
                   > THRESHOLDS["ceiling_must_exceed"])
        sect_drop = round(
            (sect_tbl["H1_BM25"]["mean_top10_expected_sect_share"] or 0)
            - (sect_tbl[name]["mean_top10_expected_sect_share"] or 0), 4)
        lang_drops = []
        for lang in ("en", "hi", "gu"):
            b = lang_tbl["H1_BM25"].get(lang, {}).get("source_recall_at_5")
            x = lang_tbl[name].get(lang, {}).get("source_recall_at_5")
            if b is not None and x is not None:
                lang_drops.append(round(b - x, 4))
        worst_lang_drop = max(lang_drops) if lang_drops else 0.0
        pc_by = (h2_by if name == "H2_DENSE"
                 else {p["example_id"]: p for p in per_cfg[name]})
        recovered = sum(1 for e in h1_miss10
                        if (pc_by[e]["unit_hit_rank"] or 99) <= 5)
        c1 = recovered >= THRESHOLDS["bm25_miss_recovery_min"]
        c2 = unit_delta >= THRESHOLDS["material_unit_delta"]
        c3 = src5 is not None and src5 >= THRESHOLDS["source_guardrail_abs"]
        c4 = ceil_ok
        c5 = sect_drop <= THRESHOLDS["sect_consistency_drop_max"] and \
            worst_lang_drop <= THRESHOLDS["language_source5_drop_max"]
        return {
            "config": name,
            "unit_recall_at_5_delta_vs_H1": unit_delta,
            "source_recall_at_5": src5,
            "evidence_ceiling_mean": a["evidence_ceiling_mean"],
            "sect_consistency_drop": sect_drop,
            "worst_language_source5_drop": worst_lang_drop,
            "bm25_miss_recovered_at5": recovered,
            "conditions": {
                "C1_dense_recovers_bm25_misses": c1,
                "C2_material_unit_gain": c2,
                "C3_source_guardrail": c3,
                "C4_ceiling_improves": c4,
                "C5_no_sect_language_regression": c5,
            },
            "all_met": all([c1, c2, c3, c4, c5]),
        }

    gates = {name: gate_for(name)
             for name in ("H2_DENSE", "H3_RRF60", "H3_RRF20",
                          "H4_RRF60", "H4_RRF20")}
    # Decision rule: the task states its five conditions per architecture and
    # pre-registers BOTH k values {20, 60} (k=60 designated primary at write
    # time, k=20 sensitivity; no broad search). Apply the five conditions to
    # every pre-registered config and recommend on the best passing one, with
    # the primary-vs-sensitivity outcome reported explicitly.
    h3_pass = [k for k in ("H3_RRF60", "H3_RRF20") if gates[k]["all_met"]]
    h4_pass = [k for k in ("H4_RRF60", "H4_RRF20") if gates[k]["all_met"]]
    h2_gate = gates["H2_DENSE"]
    h3_gate = gates["H3_RRF60"]
    if h3_pass or h4_pass:
        passing = h3_pass or h4_pass
        verdict = "RECOMMEND_HYBRID"
        rationale = (
            "pre-registered hybrid config(s) " + ", ".join(passing)
            + " meet all five task conditions"
            + ("" if "H3_RRF60" in passing else
               "; primary k=60 failed C1/C5 narrowly — see gates"))
    elif (h2_gate["conditions"]["C2_material_unit_gain"]
          and h2_gate["conditions"]["C3_source_guardrail"]
          and h2_gate["conditions"]["C4_ceiling_improves"]
          and h2_gate["conditions"]["C5_no_sect_language_regression"]):
        verdict = "RECOMMEND_DENSE"
        rationale = "H2 beats BM25 materially on units with source/sect safety"
    else:
        verdict = "KEEP_BM25"
        failed = [k for k, v in h3_gate["conditions"].items() if not v]
        rationale = ("dense/hybrid fail pre-registered gate; H3_RRF60 failed: "
                     + ", ".join(failed))

    # ---- artifacts ----
    eunits_by = {c["example_id"]: set(
        (c.get("provenance") or {}).get("unit_ids") or []) for c in cases}
    OUT_DENSE.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in dense_rows),
        encoding="utf-8")
    hybrid_rows = []
    for name, pcs in [("H1_BM25", h1_cases),
                      ("H2_DENSE", per_cfg["H2_DENSE"]),
                      ("H3_RRF60", per_cfg["H3_RRF60"]),
                      ("H3_RRF20", per_cfg["H3_RRF20"]),
                      ("H4_RRF60", per_cfg["H4_RRF60"]),
                      ("H4_RRF20", per_cfg["H4_RRF20"])]:
        for p in pcs:
            for r in p["results"]:
                hybrid_rows.append({
                    "example_id": p["example_id"],
                    "config": name,
                    "retrieval_rank": r["retrieval_rank"],
                    "text_id": r["text_id"],
                    "unit_key": unit_key(r["text_id"]),
                    "source_id": r["source_id"],
                    "retrieval_channel": r["retrieval_channel"],
                    "retrieval_score": r["retrieval_score"],
                    "dense_rank": r.get("dense_rank"),
                    "dense_score": r.get("dense_score"),
                    "unit_bm25_rank": r["unit_bm25_rank"],
                    "unit_bm25_score": r["unit_bm25_score"],
                    "methods": r["methods"],
                    "contract_valid": r["contract_valid"],
                    "contract_violations": r["contract_violations"],
                    "is_expected_unit": unit_key(r["text_id"]) in eunits_by[
                        p["example_id"]],
                    "is_expected_source": r["source_id"] == p["expected_source"],
                })
    OUT_HYBRID.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in hybrid_rows),
        encoding="utf-8")

    compl_out = {
        "definition": ("success = expected unit retrieved in top-k "
                       "(unit-labeled cases only)"),
        "at_5": compl_at5,
        "at_10": compl_at10,
        "h1_vs_h3rrf60_at_10": None,
        "known_failure_cases": known,
        "recovery": recov,
    }
    # H1 vs H3 complementarity as well
    def classify_pair(pc_by: dict, k: int) -> dict:
        both = b_only = d_only = neither = 0
        for c in unit_cases:
            eid = c["example_id"]
            u1 = h1_by[eid]["unit_hit_rank"]
            u2 = pc_by[eid]["unit_hit_rank"]
            s1 = u1 is not None and u1 <= k
            s2 = u2 is not None and u2 <= k
            both += s1 and s2
            b_only += s1 and not s2
            d_only += s2 and not s1
            neither += (not s1) and (not s2)
        n = len(unit_cases)
        return {"n": n, "both": both, "bm25_only": b_only,
                "dense_only": d_only, "neither": neither,
                "bm25_only_pct": round(100 * b_only / n, 1),
                "hybrid_only_pct": round(100 * d_only / n, 1),
                "neither_pct": round(100 * neither / n, 1)}

    compl_out["h1_vs_h3rrf60_at_10"] = classify_pair(h3_by, 10)
    compl_out["h1_vs_h3rrf60_at_5"] = classify_pair(h3_by, 5)
    OUT_COMPL.write_text(json.dumps(compl_out, indent=1, ensure_ascii=False),
                         encoding="utf-8")

    metrics = {
        "task": "TASK 74 — dense + hybrid retrieval re-evaluation",
        "configs": CFG,
        "thresholds_pre_registered": THRESHOLDS,
        "rrf": {
            "formula": "sum 1/(k + rank) over signals present, ranks 1-based",
            "k_values": list(RRF_KS),
            "primary_k": PRIMARY_K,
            "lists": "full BM25 positive ranking x full dense ranking (no truncation)",
            "tie_break": "(-rrf, bm25_rank|INF, dense_rank|INF, doc_index)",
        },
        "index_meta": meta,
        "baseline_gate": {
            "frozen_sha_verified": True,
            "h1_byte_exact": f"{byte_exact}/47",
            "h1_aggregates": {k: h1_agg[k] for k in
                              ("source_recall_at_5", "source_recall_at_10",
                               "unit_mrr", "evidence_ceiling_mean",
                               "evidence_ceiling_full", "ev0_count")},
        },
        "aggregates": aggs,
        "deltas_vs_h1": {
            name: {
                "unit_recall_at_5": round(
                    (aggs[name]["unit_recall_at_5"] or 0)
                    - (aggs["H1_BM25"]["unit_recall_at_5"] or 0), 4),
                "unit_mrr": round((aggs[name]["unit_mrr"] or 0)
                                  - (aggs["H1_BM25"]["unit_mrr"] or 0), 4),
                "source_recall_at_5": round(
                    (aggs[name]["source_recall_at_5"] or 0)
                    - (aggs["H1_BM25"]["source_recall_at_5"] or 0), 4),
                "evidence_ceiling_mean": round(
                    (aggs[name]["evidence_ceiling_mean"] or 0)
                    - (aggs["H1_BM25"]["evidence_ceiling_mean"] or 0), 4),
                "ev0_count": (aggs[name]["ev0_count"]
                              - aggs["H1_BM25"]["ev0_count"]),
            } for name in ("H2_DENSE", "H3_RRF60", "H3_RRF20",
                           "H4_RRF60", "H4_RRF20")
        },
        "safety": {
            "sect_consistency": sect_tbl,
            "by_language": lang_tbl,
            "sthanakavasi_expected_n": len(sth),
            "sthanakavasi_source_recall_at_5": sth_tbl,
            "source_attribution_changes_vs_h1": src_changes,
        },
        "cost": {"dense": dense_cost, "bm25": bm25_cost},
        "gates": gates,
        "decision": {
            "verdict": verdict,
            "rationale": rationale,
            "decision_rule": (
                "task Phase-11 conditions applied to each pre-registered "
                "config (k in {20, 60}; k=60 designated primary at script "
                "write time, k=20 sensitivity; both fixed before results)"),
            "configs_passing_all_five": {
                k: gates[k]["all_met"] for k in gates},
            "primary_k60_conditions": gates["H3_RRF60"]["conditions"],
        },
        "contract_violations_total": len(violations_total),
        "contract_violations": violations_total[:50],
        "fusion_audit": fusion_audit,
        "runtime_total_seconds": round(time.time() - t_start, 1),
    }
    OUT_METRICS.write_text(json.dumps(metrics, indent=1, ensure_ascii=False),
                           encoding="utf-8")

    log(f"wrote {OUT_DENSE.name} ({len(dense_rows)} rows), "
        f"{OUT_HYBRID.name} ({len(hybrid_rows)} rows), "
        f"{OUT_METRICS.name}, {OUT_COMPL.name}")
    log(f"DECISION: {verdict} — {rationale}")
    log(f"unit@5 H1={h1_agg['unit_recall_at_5']} "
        f"H2={aggs['H2_DENSE']['unit_recall_at_5']} "
        f"H3_60={aggs['H3_RRF60']['unit_recall_at_5']} "
        f"H4_60={aggs['H4_RRF60']['unit_recall_at_5']}")
    log(f"src@5  H1={h1_agg['source_recall_at_5']} "
        f"H2={aggs['H2_DENSE']['source_recall_at_5']} "
        f"H3_60={aggs['H3_RRF60']['source_recall_at_5']} "
        f"H4_60={aggs['H4_RRF60']['source_recall_at_5']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

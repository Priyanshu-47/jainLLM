"""TASK 73 Phases 4-6 — zero-shot query-expansion retrieval experiment.

Arms (all k5/500 evidence, corpus/tokenizer/normalization/candidate policy
identical to Task-69/72; no corpus or production changes):

  R0     exact Task-69 pipeline on Q0 only (gated byte-exact vs frozen
         task69_rag_evidence + rank crosscheck + published aggregates)
  M2ref  Q0 + score-order merge — faithful reproduction of the Task-72
         post-hoc M2 (integrity gate: recomputed aggregate must equal
         task72_metrics.json["post_hoc_sensitivity"]["M2_K5_aggregate"]
         on the whitelisted keys; decomposition reference only)
  R10    union max-score retrieval over Q0 + all VALID expansion variants:
           union_score(d) = max_q score_q(d)
           union order     = (-union_score, q0_rank(d) or +inf, doc_index)
         candidate policy run on the union ranking (pool 2000 -> diversify
         top-10 -> same Q0 metadata fills), selected sources = distinct
         sources of that combined list, score-order merge = union order
         filtered to selected sources + fills kept only for sources with no
         positive union-score doc.

STOP (exit 3, no artifacts written) on: frozen sha mismatch, expansions sha
mismatch, R0 not byte-exact, R0 aggregates != published, M2ref integrity
mismatch, any contract violation.

Outputs:
  data/evaluation/task73_retrieval_results.jsonl
  data/evaluation/task73_metrics.json
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(REPO / "experiments" / "task72"))

import task73_phase1 as p1  # noqa: E402
import task72_experiment as t72  # noqa: E402
from svk_corpus.retrieval import RetrievalResult  # noqa: E402

EXPANSIONS_PATH = REPO / "data" / "evaluation" / "task73_query_expansions.jsonl"
OUT_RESULTS = REPO / "data" / "evaluation" / "task73_retrieval_results.jsonl"
OUT_METRICS = REPO / "data" / "evaluation" / "task73_metrics.json"
EXPECTED_EXPANSIONS_SHA = (
    "c5daf50449a39a7a6d173511854b555533647481db0d85b29c397860ee855f73"
)
T72_METRICS_PATH = t72.OUT_METRICS
M2REF_GATE_KEYS = [
    "source_recall_at_1", "source_recall_at_3", "source_recall_at_5",
    "source_recall_at_10", "source_mrr",
    "unit_recall_at_1", "unit_recall_at_3", "unit_recall_at_5",
    "unit_recall_at_10", "unit_mrr",
    "evidence_ceiling_mean", "evidence_ceiling_full", "ev0_count",
    "zero_hit", "source_zero_hit_cases", "unit_zero_hit_cases", "ev0_cases",
    "metadata_only_cases", "source_hit_but_unit_miss_cases",
]
TARGETS = {"unit_recall_at_5": 0.46, "ev0_max": 12, "source_recall_at_5_min": 0.90}
DELTA_KEYS = [
    "source_recall_at_1", "source_recall_at_3", "source_recall_at_5",
    "source_recall_at_10", "source_mrr",
    "unit_recall_at_1", "unit_recall_at_3", "unit_recall_at_5",
    "unit_recall_at_10", "unit_mrr",
    "evidence_ceiling_mean", "evidence_ceiling_full", "ev0_count",
    "n_ranking_miss", "n_candidate_miss", "n_metadata_only",
    "n_source_hit_but_unit_miss",
]
INF = 10**12


def stop(msg: str) -> int:
    print(f"STOP: {msg}")
    return 3


def load_expansions() -> dict[str, dict]:
    rows = t72.load_jsonl(EXPANSIONS_PATH)
    if len(rows) != 47:
        raise SystemExit(f"expected 47 expansion rows, got {len(rows)}")
    return {r["example_id"]: r for r in rows}


def queries_of(exp_row: dict) -> list[tuple[str, str]]:
    """[("Q0", original), ("Qk", variant_k)] for valid variants only."""
    out = [("Q0", exp_row["original_query"])]
    for k in (1, 2, 3):
        if exp_row.get(f"variant_{k}_valid"):
            out.append((f"Q{k}", exp_row[f"variant_{k}"].strip()))
    return out


def main() -> int:
    t_start = time.time()
    if t72.sha256_file(t72.CASES_PATH) != t72.FROZEN_SHA:
        return stop("frozen benchmark sha mismatch")
    exp_sha = t72.sha256_file(EXPANSIONS_PATH)
    if exp_sha != EXPECTED_EXPANSIONS_SHA:
        return stop(f"expansions sha mismatch {exp_sha}")
    t72.log(f"frozen sha + expansions sha verified ({exp_sha[:16]}…)")

    cases = t72.load_jsonl(t72.CASES_PATH)
    cards = t72.t69.load_manifest_cards(t72.MANIFEST_PATH)
    expansions = load_expansions()
    frozen_rows = {r["example_id"]: r for r in t72.load_jsonl(t72.FROZEN_EVIDENCE)}
    frozen_metrics = {p["example_id"]: p for p in
                      json.loads(t72.FROZEN_METRICS.read_text())["per_case"]}
    if len(cases) != 47 or len(frozen_rows) != 47:
        return stop("expected 47 rows in cases/frozen inputs")

    if not T72_METRICS_PATH.exists():
        return stop(f"missing {T72_METRICS_PATH} (M2ref integrity dependency)")
    t72_metrics = json.loads(T72_METRICS_PATH.read_text())
    m2_expected = (t72_metrics.get("post_hoc_sensitivity") or {}
                   ).get("M2_K5_aggregate")
    if not m2_expected:
        return stop("task72_metrics.json has no post_hoc_sensitivity.M2_K5_aggregate")
    t72.log(f"M2ref gate loaded from task72_metrics.json "
            f"(unit@5={m2_expected['unit_recall_at_5']}, "
            f"src@5={m2_expected['source_recall_at_5']}, "
            f"ceiling={m2_expected['evidence_ceiling_mean']}, "
            f"ev0={m2_expected['ev0_count']})")

    docs, bm25, sidx, expander, diversify = p1.build_retrieval_stack()
    doc_index = {d.text_id: i for i, d in enumerate(docs)}
    unit_docs: dict[str, list[str]] = {}
    src_indices: dict[str, list[int]] = {}
    for i, d in enumerate(docs):
        unit_docs.setdefault(t72.unit_key(d.text_id), []).append(d.text_id)
        src_indices.setdefault(d.source_id, []).append(i)
    t72.log(f"corpus {len(docs)} docs indexed")

    cfg_r0 = dict(t72.CONFIGS["R0"])
    cfg_m2 = dict(t72.CONFIGS["R0"], mode="score_order_merge", label="M2ref")
    cfg_r10 = dict(t72.CONFIGS["R0"], mode="union_score_order", label="R10")

    results_rows: list[dict] = []
    per_config: dict[str, list[dict]] = {"R0": [], "M2ref": [], "R10": []}
    fx_raw: dict[str, dict] = {}
    violations: list[dict] = []
    byte_exact = 0
    rank_xcheck = 0
    rt = {"r0": 0.0, "m2ref": 0.0, "r10": 0.0, "variant_search": 0.0}

    for case in cases:
        eid = case["example_id"]
        query = case["question"]
        prov = case.get("provenance") or {}
        esrc = prov.get("source_id")
        eunits = prov.get("unit_ids") or []
        qpairs = queries_of(expansions[eid])

        # ------------------------------------------------------------------ Q0
        t0 = time.time()
        full0 = bm25.search(query, top_k=10**9)
        q0_full = {h.doc.text_id: (h.rank, h.score) for h in full0}
        pool0 = full0[: t72.POOL]
        pool_rank = {h.doc.text_id: h.rank for h in pool0}
        pool_rank_by_unit: dict[str, int] = {}
        for tid, rank in pool_rank.items():
            pool_rank_by_unit.setdefault(t72.unit_key(tid), rank)

        unit_tier = diversify.rerank([
            RetrievalResult(doc=h.doc, score=h.score, rank=h.rank,
                            methods={"bm25": h.rank})
            for h in pool0
        ])[: t72.TOP_K]
        unit_ids = {r.doc.text_id for r in unit_tier}
        unit_sids = {r.doc.source_id for r in unit_tier}
        smatches = sidx.search(query, top_k=t72.TOP_K)
        missing = [m for m in smatches if m.source_id not in unit_sids
                   and not m.identifier_only]
        n_fill = min(t72.MAX_METADATA_FILL, len(missing))
        fill = expander.expand(missing[:n_fill], top_k=n_fill)
        keep0 = max(t72.TOP_K - len(fill), 0)
        combined0 = (list(unit_tier[:keep0]) + fill)[: t72.TOP_K]
        norm_tokens = tuple(t72.expand_query_text(query))

        results0 = []
        for i, r in enumerate(combined0, 1):
            ch = t72.t69.channel_of(r, unit_ids)
            row, _ = t72.result_row(r, eid, i, ch, query, norm_tokens)
            results0.append(row)
            if row["contract_violations"]:
                violations.append({"config": "R0", "result_id": row["result_id"],
                                   "violations": row["contract_violations"]})
        m0 = t72.build_block_and_metrics(case, results0, cards, cfg_r0)
        fr = frozen_rows[eid]
        if ([(r["text_id"], r["retrieval_rank"], r["retrieval_channel"])
             for r in results0]
                == [(r["text_id"], r["retrieval_rank"], r["retrieval_channel"])
                    for r in fr["results"]]
                and m0["context_sha256"] == fr["evidence_context"]["sha256"]):
            byte_exact += 1
        else:
            return stop(f"R0 rebuild not byte-exact for {eid}")
        first0, uhit0 = t72.case_ranks(results0, case)
        fmeta = frozen_metrics[eid]
        if (first0 == fmeta["source_first_rank"]
                and uhit0 == fmeta["unit_hit_rank"]):
            rank_xcheck += 1
        else:
            return stop(f"R0 rank mismatch for {eid}: "
                        f"src {first0} vs {fmeta['source_first_rank']}, "
                        f"unit {uhit0} vs {fmeta['unit_hit_rank']}")
        sel: dict[str, int] = {}
        for r in combined0:
            sel.setdefault(r.doc.source_id, len(sel) + 1)
        rt["r0"] += time.time() - t0

        # -------------------------------------------------------------- M2ref
        t0 = time.time()
        within: dict[str, list] = {}
        for sid in sel:
            allowed = src_indices.get(sid, [])
            within[sid] = (bm25.search(query, top_k=len(allowed), allowed=allowed)
                           if allowed else [])
        fills_kept_m2 = [f for f in fill if not within.get(f.doc.source_id)]
        keep_m2 = max(t72.TOP_K - len(fills_kept_m2), 0)
        m2_units = [h for h in full0 if h.doc.source_id in sel][:keep_m2]
        results_m2 = []
        for i, h in enumerate(m2_units, 1):
            rr = RetrievalResult(doc=h.doc, score=h.score, rank=h.rank,
                                 methods={"bm25": h.rank})
            rr.extra = type("NS", (), {
                "bm25_rank": pool_rank.get(h.doc.text_id),
                "bm25_score": h.score,
            })()
            row, _ = t72.result_row(rr, eid, i, "unit_bm25", query, norm_tokens)
            results_m2.append(row)
            if row["contract_violations"]:
                violations.append({"config": "M2ref", "result_id": row["result_id"],
                                   "violations": row["contract_violations"]})
        for f in fills_kept_m2:
            i = len(results_m2) + 1
            row, _ = t72.result_row(f, eid, i, "source_metadata", query, norm_tokens)
            results_m2.append(row)
            if row["contract_violations"]:
                violations.append({"config": "M2ref", "result_id": row["result_id"],
                                   "violations": row["contract_violations"]})
        results_m2 = results_m2[: t72.TOP_K]
        mm2 = t72.build_block_and_metrics(case, results_m2, cards, cfg_m2)
        rt["m2ref"] += time.time() - t0

        # ---------------------------------------------------------------- R10
        t0 = time.time()
        variant_fulls: list[tuple[str, dict[str, tuple[int, float]]]] = []
        for label, qtext in qpairs[1:]:
            t_vs = time.time()
            vh = bm25.search(qtext, top_k=10**9)
            rt["variant_search"] += time.time() - t_vs
            variant_fulls.append(
                (label, {h.doc.text_id: (h.rank, h.score) for h in vh}))
        # union: max score per doc, tie-break (-score, q0_rank or INF, doc_index)
        best: dict[str, dict] = {}
        for h in full0:
            best[h.doc.text_id] = {
                "doc": h.doc, "score": h.score, "q0_rank": h.rank,
                "best_label": "Q0"}
        for label, vd in variant_fulls:
            for tid, (vrank, vscore) in vd.items():
                e = best.get(tid)
                if e is None:
                    e = {"doc": docs[doc_index[tid]], "score": vscore,
                         "q0_rank": None, "best_label": label}
                    best[tid] = e
                elif vscore > e["score"]:
                    e["score"] = vscore
                    e["best_label"] = label
        if not set(q0_full).issubset(best):
            return stop(f"union lost Q0 docs for {eid}")
        union_full = sorted(
            best.items(),
            key=lambda kv: (-kv[1]["score"],
                            kv[1]["q0_rank"] if kv[1]["q0_rank"] is not None
                            else INF,
                            doc_index[kv[0]]),
        )
        union_rank = {tid: i for i, (tid, _) in enumerate(union_full, 1)}
        union_src_lex = {e["doc"].source_id for _, e in union_full}

        pool10 = union_full[: t72.POOL]
        unit_tier10 = diversify.rerank([
            RetrievalResult(doc=e["doc"], score=e["score"], rank=union_rank[tid],
                            methods={"bm25": union_rank[tid]})
            for tid, e in pool10
        ])[: t72.TOP_K]
        # fills are Q0-driven (Task-72 semantics: computed once from the Q0
        # metadata search + Q0 tier); only the kept-filter differs per arm.
        keep10 = max(t72.TOP_K - len(fill), 0)
        combined10 = (list(unit_tier10[:keep10]) + fill)[: t72.TOP_K]
        sel10: dict[str, int] = {}
        for r in combined10:
            sel10.setdefault(r.doc.source_id, len(sel10) + 1)
        fills_kept10 = [f for f in fill
                        if f.doc.source_id not in union_src_lex]
        keep_m = max(t72.TOP_K - len(fills_kept10), 0)
        r10_units = [(tid, e) for tid, e in union_full
                     if e["doc"].source_id in sel10][:keep_m]

        results10 = []
        for i, (tid, e) in enumerate(r10_units, 1):
            rr = RetrievalResult(doc=e["doc"], score=e["score"],
                                 rank=union_rank[tid],
                                 methods={"bm25": union_rank[tid]})
            rr.extra = type("NS", (), {
                "bm25_rank": union_rank[tid],
                "bm25_score": e["score"],
            })()
            audit = {
                "expansion_best_query": e["best_label"],
                "expansion_q0_rank": e["q0_rank"],
                "expansion_union_rank": union_rank[tid],
                "expansion_union_score": round(float(e["score"]), 6),
            }
            row, _ = t72.result_row(rr, eid, i, "unit_bm25", query,
                                    norm_tokens, audit)
            results10.append(row)
            if row["contract_violations"]:
                violations.append({"config": "R10", "result_id": row["result_id"],
                                   "violations": row["contract_violations"]})
        for f in fills_kept10:
            i = len(results10) + 1
            audit = {
                "expansion_best_query": "Q0",
                "expansion_q0_rank": q0_full.get(f.doc.text_id, (None,))[0],
                "expansion_union_rank": union_rank.get(f.doc.text_id),
                "expansion_union_score": None,
            }
            row, _ = t72.result_row(f, eid, i, "source_metadata", query,
                                    norm_tokens, audit)
            results10.append(row)
            if row["contract_violations"]:
                violations.append({"config": "R10", "result_id": row["result_id"],
                                   "violations": row["contract_violations"]})
        results10 = results10[: t72.TOP_K]
        mr10 = t72.build_block_and_metrics(case, results10, cards, cfg_r10)
        rt["r10"] += time.time() - t0

        # ------------------------------------------------------- pack records
        pool_in = any(pool_rank_by_unit.get(u) is not None for u in eunits) \
            if eunits else False
        pool10_rank_by_unit: dict[str, int] = {}
        for i, (tid, _) in enumerate(pool10, 1):
            pool10_rank_by_unit.setdefault(t72.unit_key(tid), i)
        union_in = any(pool10_rank_by_unit.get(u) is not None for u in eunits) \
            if eunits else False

        def pack(results_out: list[dict], cfg: dict, block: dict,
                 cand: bool, selmap: dict) -> dict:
            first, uhit = t72.case_ranks(results_out, case)
            src_hits = ([r for r in results_out if r["source_id"] == esrc]
                        if esrc else [])
            return {
                "config": cfg,
                "source_first_rank": first,
                "unit_hit_rank": uhit,
                "results": results_out,
                **block,
                "results_sources_hit": bool(src_hits),
                "results_sources_hit_only_metadata": bool(src_hits) and all(
                    r["retrieval_channel"] == "source_metadata"
                    for r in src_hits),
                "expected_unit_in_candidate_set": cand,
                "selected_sources": selmap,
            }

        rec0 = pack(results0, cfg_r0, m0, pool_in, sel)
        recm = pack(results_m2, cfg_m2, mm2, pool_in, sel)
        recx = pack(results10, cfg_r10, mr10, union_in, sel10)
        for name, rec in (("R0", rec0), ("M2ref", recm), ("R10", recx)):
            per_config[name].append({
                "example_id": eid,
                "category": case["category"],
                "language": case["language"],
                "expected_source": esrc,
                "expected_units": eunits,
                **{k: v for k, v in rec.items() if k != "config"},
            })

        # ------------------------------------------------------------ forensics
        eu_tids = [t for u in eunits for t in unit_docs.get(u, [])]
        in_union = [t for t in eu_tids if t in union_rank]
        feat_tid = None
        if in_union:
            feat_tid = min(in_union, key=lambda t: union_rank[t])
        elif eu_tids:
            in_q0 = [t for t in eu_tids if t in q0_full]
            if in_q0:
                feat_tid = min(in_q0, key=lambda t: q0_full[t][0])
        feat = None
        if feat_tid:
            per_q = {}
            q0e = q0_full.get(feat_tid)
            per_q["Q0"] = (q0e[0], round(float(q0e[1]), 6)) if q0e else (None, None)
            for label, vd in variant_fulls:
                ve = vd.get(feat_tid)
                per_q[label] = ((ve[0], round(float(ve[1]), 6))
                                if ve else (None, None))
            present = [(lab, s) for lab, (r, s) in per_q.items()
                       if s is not None]
            best_lab = None
            if present:
                top = max(s for _, s in present)
                for pref in ("Q0", "Q1", "Q2", "Q3"):
                    if any(lab == pref and s == top for lab, s in present):
                        best_lab = pref
                        break
            e = best.get(feat_tid)
            feat = {
                "text_id": feat_tid,
                "q0_full_rank": per_q["Q0"][0],
                "q0_score": per_q["Q0"][1],
                "union_full_rank": union_rank.get(feat_tid),
                "union_score": (round(float(e["score"]), 6) if e else None),
                "best_query": best_lab,
                "per_query_rank_score": per_q,
            }
        r10_hit_tid = None
        if recx["unit_hit_rank"]:
            r10_hit_tid = results10[recx["unit_hit_rank"] - 1]["text_id"]
        fx_raw[eid] = {
            "example_id": eid,
            "n_queries": len(qpairs),
            "queries_used": [lab for lab, _ in qpairs],
            "expected_unit_feature": feat,
            "r10_hit_text_id": r10_hit_tid,
            "r10_hit_best_query": (
                results10[recx["unit_hit_rank"] - 1].get("expansion_best_query")
                if recx["unit_hit_rank"] else None),
            "pool_in_q0": pool_in,
            "pool_in_union": union_in,
        }

        results_rows.append({
            "example_id": eid,
            "category": case["category"],
            "language": case["language"],
            "query": query,
            "expected_source": esrc,
            "expected_units": eunits,
            "expansion": {
                lab: (expansions[eid][f"variant_{int(lab[1:])}"]
                      if lab != "Q0" else query)
                for lab, _ in qpairs
            },
            "n_valid_variants": expansions[eid]["n_valid_variants"],
            "forensics_raw": fx_raw[eid],
            "configs": {
                "R0": {k: v for k, v in rec0.items() if k != "config"},
                "M2ref": {k: v for k, v in recm.items() if k != "config"},
                "R10": {k: v for k, v in recx.items() if k != "config"},
            },
        })
        t72.log(
            f"  {eid} q={len(qpairs)} r0_u={rec0['unit_hit_rank']} "
            f"m2_u={recm['unit_hit_rank']} r10_u={recx['unit_hit_rank']} "
            f"ev={m0['evidence_answer_score']}→{mm2['evidence_answer_score']}"
            f"→{mr10['evidence_answer_score']}"
        )

    # ------------------------------------------------------------------ gates
    aggs = {name: t72.aggregate(rows, cfg)
            for name, rows, cfg in (
                ("R0", per_config["R0"], cfg_r0),
                ("M2ref", per_config["M2ref"], cfg_m2),
                ("R10", per_config["R10"], cfg_r10))}
    problems = []
    if byte_exact != 47:
        problems.append(f"byte-exact {byte_exact}/47")
    if rank_xcheck != 47:
        problems.append(f"rank crosscheck {rank_xcheck}/47")
    for key, want in p1.EXPECTED.items():
        if aggs["R0"][key] != want:
            problems.append(f"R0 {key}: {aggs['R0'][key]} != {want}")
    m2_diff = {k: {"expected": m2_expected.get(k), "actual": aggs["M2ref"].get(k)}
               for k in M2REF_GATE_KEYS
               if aggs["M2ref"].get(k) != m2_expected.get(k)}
    if m2_diff:
        problems.append(f"M2ref integrity mismatch: {m2_diff}")
    if violations:
        problems.append(f"{len(violations)} contract violations")
    if problems:
        print("PHASE4_6_GATE_FAIL")
        for p in problems:
            print("  -", p)
        return 3
    t72.log(f"PHASE4_6_GATES_PASS byte_exact={byte_exact} "
            f"m2ref_keys={len(M2REF_GATE_KEYS)} violations=0")

    # ------------------------------------------------- deltas / forensics sets
    def deltas(a: dict, b: dict) -> dict:
        return {k: (round((a.get(k) or 0) - (b.get(k) or 0), 4)
                    if not isinstance(a.get(k), list) else None)
                for k in DELTA_KEYS}

    by = {name: {r["example_id"]: r for r in per_config[name]}
          for name in per_config}

    def urank(name: str, eid: str) -> float:
        v = by[name][eid]["unit_hit_rank"]
        return v if v is not None else INF

    def srank(name: str, eid: str) -> float:
        v = by[name][eid]["source_first_rank"]
        return v if v is not None else INF

    eids = [c["example_id"] for c in cases]
    unit_improved = [e for e in eids if urank("R10", e) < urank("R0", e)]
    unit_regressed = [e for e in eids if urank("R10", e) > urank("R0", e)]
    src_improved = [e for e in eids if srank("R10", e) < srank("R0", e)]
    src_regressed = [e for e in eids if srank("R10", e) > srank("R0", e)]
    m2_improved = [e for e in eids if urank("M2ref", e) < urank("R0", e)]
    m2_regressed = [e for e in eids if urank("M2ref", e) > urank("R0", e)]

    known = [f"DAPT01EVAL-{s}" for s in t72.KNOWN_CASES]
    fx_case_ids = sorted(set(known) | set(unit_improved) | set(unit_regressed)
                         | set(src_improved) | set(src_regressed))
    forensics = []
    for eid in fx_case_ids:
        row = {"example_id": eid}
        row.update(fx_raw[eid])
        for name in ("R0", "M2ref", "R10"):
            r = by[name][eid]
            row[name] = {
                "unit_hit_rank": r["unit_hit_rank"],
                "source_first_rank": r["source_first_rank"],
                "evidence_answer_score": r["evidence_answer_score"],
                "unit_top5": (r["unit_hit_rank"] is not None
                              and r["unit_hit_rank"] <= 5),
                "unit_top10": (r["unit_hit_rank"] is not None
                               and r["unit_hit_rank"] <= 10),
            }
        ur0, ur10 = urank("R0", eid), urank("R10", eid)
        row["unit_delta_r10_vs_r0"] = (
            "improved" if ur10 < ur0 else
            "regressed" if ur10 > ur0 else "unchanged")
        row["known_miss_case"] = eid in known
        forensics.append(row)

    ev0_r0 = set(aggs["R0"]["ev0_cases"])
    ev0_r10 = set(aggs["R10"]["ev0_cases"])
    ev0_m2 = set(aggs["M2ref"]["ev0_cases"])
    zero_r0 = set(aggs["R0"]["unit_zero_hit_cases"])
    zero_r10 = set(aggs["R10"]["unit_zero_hit_cases"])
    zero_m2 = set(aggs["M2ref"]["unit_zero_hit_cases"])

    # ------------------------------------------------------------ query drift
    exp_rows = list(expansions.values())
    n_slots = sum(3 for _ in exp_rows)
    n_valid = sum(r["n_valid_variants"] for r in exp_rows)
    drift_reasons: dict[str, int] = {}
    invalid_cases = {}
    for r in exp_rows:
        for k in (1, 2, 3):
            reason = r[f"variant_{k}_invalid_reason"]
            if reason:
                drift_reasons[reason] = drift_reasons.get(reason, 0) + 1
                invalid_cases.setdefault(r["example_id"], []).append(
                    f"v{k}:{reason}")
    zero_valid = [r["example_id"] for r in exp_rows if r["n_valid_variants"] == 0]

    # ------------------------------------------------------- targets + verdict
    a0, am, ax = aggs["R0"], aggs["M2ref"], aggs["R10"]
    target_unit5 = ax["unit_recall_at_5"] >= TARGETS["unit_recall_at_5"]
    target_ev0 = ax["ev0_count"] <= TARGETS["ev0_max"]
    target_src5 = ax["source_recall_at_5"] >= TARGETS["source_recall_at_5_min"]
    drift_low = (n_valid / n_slots >= 0.90) and len(zero_valid) <= 1
    decision = all([target_unit5, target_ev0, target_src5, drift_low])

    runtimes = {
        "phase1_gate_seconds": 72.1,
        "r0_arm_seconds": round(rt["r0"], 1),
        "m2ref_arm_seconds": round(rt["m2ref"], 1),
        "r10_arm_seconds": round(rt["r10"], 1),
        "r10_variant_search_seconds": round(rt["variant_search"], 1),
        "experiment_total_seconds": round(time.time() - t_start, 1),
    }

    metrics = {
        "task": "TASK 73 — zero-shot query expansion retrieval experiment",
        "inputs": {
            "frozen_sha": t72.FROZEN_SHA,
            "expansions_sha256": exp_sha,
            "task72_metrics_sha256": t72.sha256_file(T72_METRICS_PATH),
        },
        "phase1_gate": {"expected": p1.EXPECTED,
                        "actual": {k: a0[k] for k in p1.EXPECTED},
                        "byte_exact": byte_exact,
                        "rank_crosscheck": rank_xcheck, "pass": True},
        "query_expansion": {
            "total_slots": n_slots,
            "valid": n_valid,
            "invalid": n_slots - n_valid,
            "valid_fraction": round(n_valid / n_slots, 4),
            "invalid_by_reason": drift_reasons,
            "cases_with_invalid": invalid_cases,
            "cases_zero_valid": zero_valid,
            "manual_review": "all 141 variants reviewed against guard rules",
        },
        "aggregate": aggs,
        "gates": {
            "r0_byte_exact": f"{byte_exact}/47",
            "r0_rank_crosscheck": f"{rank_xcheck}/47",
            "r0_published_aggregates": "match",
            "m2ref_integrity_keys": len(M2REF_GATE_KEYS),
            "m2ref_integrity": "match",
            "contract_violations": 0,
        },
        "deltas": {
            "M2ref_minus_R0": deltas(am, a0),
            "R10_minus_R0": deltas(ax, a0),
            "R10_minus_M2ref": deltas(ax, am),
        },
        "targets": {
            "unit_recall_at_5": {"target": TARGETS["unit_recall_at_5"],
                                 "r0": a0["unit_recall_at_5"],
                                 "m2ref": am["unit_recall_at_5"],
                                 "r10": ax["unit_recall_at_5"],
                                 "met": target_unit5},
            "ev0_count": {"max": TARGETS["ev0_max"], "r0": a0["ev0_count"],
                          "m2ref": am["ev0_count"], "r10": ax["ev0_count"],
                          "met": target_ev0},
            "source_recall_at_5": {"min": TARGETS["source_recall_at_5_min"],
                                   "r0": a0["source_recall_at_5"],
                                   "m2ref": am["source_recall_at_5"],
                                   "r10": ax["source_recall_at_5"],
                                   "met": target_src5},
            "query_drift_low": {"criterion": "valid >= 90% and <=1 case zero-valid",
                                "valid_fraction": round(n_valid / n_slots, 4),
                                "zero_valid_cases": len(zero_valid),
                                "met": drift_low},
        },
        "forensics": forensics,
        "improved_regressed": {
            "unit_improved_r10": unit_improved,
            "unit_regressed_r10": unit_regressed,
            "source_improved_r10": src_improved,
            "source_regressed_r10": src_regressed,
            "unit_improved_m2ref": m2_improved,
            "unit_regressed_m2ref": m2_regressed,
        },
        "failure_recovery": {
            "unit_zero_hit_r0": sorted(zero_r0),
            "unit_zero_hit_recovered_m2ref": sorted(zero_r0 - zero_m2),
            "unit_zero_hit_recovered_r10": sorted(zero_r0 - zero_r10),
            "unit_zero_hit_new_r10": sorted(zero_r10 - zero_r0),
            "ev0_r0": sorted(ev0_r0),
            "ev0_recovered_m2ref": sorted(ev0_r0 - ev0_m2),
            "ev0_recovered_r10": sorted(ev0_r0 - ev0_r10),
            "ev0_new_r10": sorted(ev0_r10 - ev0_r0),
            "ranking_miss_r0": a0["ranking_miss_cases"],
            "ranking_miss_recovered_r10": sorted(
                set(a0["ranking_miss_cases"])
                & {e for e in eids if urank("R10", e) < INF}),
        },
        "runtimes": runtimes,
        "decision_gate": {
            "all_met": decision,
            "recommend_query_expansion": decision,
            "criteria": {"unit_at_5_ge_0.46": target_unit5,
                         "ev0_le_12": target_ev0,
                         "source_at_5_ge_0.90": target_src5,
                         "drift_low": drift_low},
        },
        "post_hoc_m2ref_reference": {
            "source": "task72_metrics.json post_hoc_sensitivity.M2_K5_aggregate",
            "unit_recall_at_5": m2_expected["unit_recall_at_5"],
            "source_recall_at_5": m2_expected["source_recall_at_5"],
            "evidence_ceiling_mean": m2_expected["evidence_ceiling_mean"],
            "ev0_count": m2_expected["ev0_count"],
        },
    }

    OUT_RESULTS.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in results_rows),
        encoding="utf-8",
    )
    OUT_METRICS.write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print("== R0 / M2ref / R10 ==")
    for k in ("source_recall_at_5", "source_recall_at_10",
              "unit_recall_at_5", "unit_recall_at_10", "unit_mrr",
              "evidence_ceiling_mean", "evidence_ceiling_full", "ev0_count"):
        print(f"  {k}: {a0[k]} / {am[k]} / {ax[k]}")
    print("R10-R0:", json.dumps(metrics["deltas"]["R10_minus_R0"]))
    print("R10-M2ref:", json.dumps(metrics["deltas"]["R10_minus_M2ref"]))
    print("targets:", json.dumps(metrics["targets"]))
    print("unit improved r10:", unit_improved)
    print("unit regressed r10:", unit_regressed)
    print("source regressed r10:", src_regressed)
    print(f"drift: {n_valid}/{n_slots} valid, zero-valid {zero_valid}")
    print(f"runtimes: {json.dumps(runtimes)}")
    print(f"results sha: {t72.sha256_file(OUT_RESULTS)[:16]}…")
    print(f"metrics sha: {t72.sha256_file(OUT_METRICS)[:16]}…")
    print("PHASE4_6_WRITTEN")
    print("RESULT_JSON::" + json.dumps({
        "r0_unit_at_5": a0["unit_recall_at_5"],
        "m2ref_unit_at_5": am["unit_recall_at_5"],
        "r10_unit_at_5": ax["unit_recall_at_5"],
        "r0_ev0": a0["ev0_count"], "m2ref_ev0": am["ev0_count"],
        "r10_ev0": ax["ev0_count"],
        "r0_src_at_5": a0["source_recall_at_5"],
        "m2ref_src_at_5": am["source_recall_at_5"],
        "r10_src_at_5": ax["source_recall_at_5"],
        "r10_ceiling": ax["evidence_ceiling_mean"],
        "m2ref_ceiling": am["evidence_ceiling_mean"],
        "valid_variants": n_valid, "slots": n_slots,
        "decision": decision,
        "runtime_total_s": runtimes["experiment_total_seconds"],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

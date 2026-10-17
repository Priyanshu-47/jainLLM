"""Task 72 — POST-HOC sensitivity + bottleneck attribution (analysis only).

Two clearly-labelled post-hoc analyses (not part of the pre-registered
R0/R7/R8/R9 config set; do not use them for the primary verdict):

1. M2 score-order merge: top_k = global BM25 ranking filtered to the selected
   sources (score order == global order; within-source restricted BM25 is a
   re-indexing of the same scores), plus the same metadata fills policy as R8.
   Isolates "merge policy" (round-robin) from "within-source rank depth".

2. Attribution split of R0 ranking-miss expected units:
   within-source rank <= 10 (would fit a source-anchored window; blocked only
   by round-robin slot allocation) vs > 10 (lexical depth inside the already
   correct source — no 10-slot merge can surface them), and per-unit
   merge-blocking in the actual R8 output.

Writes results into data/evaluation/task72_metrics.json["post_hoc_sensitivity"].
Read-only with respect to all other artifacts.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import task72_experiment as t72  # noqa: E402  (helpers; main() guarded)
from svk_corpus.retrieval import BM25Index, RetrievalResult  # noqa: E402
from svk_corpus.retrieval.rerank import Reranker  # noqa: E402


def main() -> int:
    t0 = time.time()
    if t72.sha256_file(t72.CASES_PATH) != t72.FROZEN_SHA:
        print("STOP: frozen benchmark sha mismatch")
        return 3
    cases = t72.load_jsonl(t72.CASES_PATH)
    cards = t72.t69.load_manifest_cards(t72.MANIFEST_PATH)
    if len(cases) != 47:
        print("STOP: expected 47 cases")
        return 3

    docs = t72.load_corpus(t72.CORPUS_PATH, t72.MANIFEST_PATH)
    bm25 = BM25Index(docs, k1=1.5, b=0.75)
    sidx = t72.build_source_index(t72.MANIFEST_PATH)
    expander = t72.SourceUnitExpander(docs)
    diversify = Reranker(strategy="diversify", max_per_source=3)
    src_indices: dict[str, list[int]] = {}
    for i, d in enumerate(docs):
        src_indices.setdefault(d.source_id, []).append(i)

    cfg_k5 = dict(t72.CONFIGS["R0"], mode="score_order_merge", label="M2_K5")
    cfg_k10 = dict(t72.CONFIGS["R7"], mode="score_order_merge", label="M2_K10")
    per_case_k5: list[dict] = []
    per_case_k10: list[dict] = []
    violations: list[dict] = []

    for case in cases:
        eid = case["example_id"]
        query = case["question"]
        prov = case.get("provenance") or {}
        esrc = prov.get("source_id")
        eunits = prov.get("unit_ids") or []

        full = bm25.search(query, top_k=10**9)
        pool = full[: t72.POOL]
        pool_rank = {r.doc.text_id: r.rank for r in pool}
        global_rank = {r.doc.text_id: r.rank for r in full}
        unit_tier = diversify.rerank([
            RetrievalResult(doc=h.doc, score=h.score, rank=h.rank,
                            methods={"bm25": h.rank})
            for h in pool
        ])[: t72.TOP_K]
        unit_ids = {r.doc.text_id for r in unit_tier}
        unit_sids = {r.doc.source_id for r in unit_tier}
        smatches = sidx.search(query, top_k=t72.TOP_K)
        missing = [m for m in smatches if m.source_id not in unit_sids
                   and not m.identifier_only]
        n_fill = min(t72.MAX_METADATA_FILL, len(missing))
        fill = expander.expand(missing[:n_fill], top_k=n_fill)
        combined0 = list(unit_tier[: max(t72.TOP_K - len(fill), 0)]) + fill
        combined0 = combined0[: t72.TOP_K]
        sel: dict[str, int] = {}
        for r in combined0:
            sel.setdefault(r.doc.source_id, len(sel) + 1)

        within: dict[str, list] = {}
        for sid in sel:
            allowed = src_indices.get(sid, [])
            within[sid] = (bm25.search(query, top_k=len(allowed), allowed=allowed)
                           if allowed else [])

        lex = [(cr, sid) for sid, cr in sel.items() if within[sid]]
        fills_kept = [f for f in fill if not within.get(f.doc.source_id)]
        keep = max(t72.TOP_K - len(fills_kept), 0)
        # M2: global score order restricted to selected sources
        m2_units = [r for r in full if r.doc.source_id in sel][:keep]

        norm_tokens = tuple(t72.expand_query_text(query))
        results = []
        for i, r in enumerate(m2_units, 1):
            rr = RetrievalResult(doc=r.doc, score=r.score, rank=r.rank,
                                 methods={"bm25": r.rank})
            rr.extra = type("NS", (), {
                "bm25_rank": pool_rank.get(r.doc.text_id),
                "bm25_score": r.score,
            })()
            row, _ = t72.result_row(rr, eid, i, "unit_bm25", query, norm_tokens)
            results.append(row)
            if row["contract_violations"]:
                violations.append({"example_id": eid, "result_id": row["result_id"],
                                   "violations": row["contract_violations"]})
        for f in fills_kept:
            i = len(results) + 1
            row, _ = t72.result_row(f, eid, i, "source_metadata", query, norm_tokens)
            results.append(row)
            if row["contract_violations"]:
                violations.append({"example_id": eid, "result_id": row["result_id"],
                                   "violations": row["contract_violations"]})
        results = results[: t72.TOP_K]

        pool_in = any(pool_rank.get(u) is not None for u in eunits) if eunits else False
        for cfg, out in ((cfg_k5, per_case_k5), (cfg_k10, per_case_k10)):
            mb = t72.build_block_and_metrics(case, results, cards, cfg)
            first, uhit = t72.case_ranks(results, case)
            src_hits = [r for r in results if r["source_id"] == esrc] if esrc else []
            out.append({
                "example_id": eid,
                "category": case["category"],
                "language": case["language"],
                "expected_source": esrc,
                "expected_units": eunits,
                "source_first_rank": first,
                "unit_hit_rank": uhit,
                "results": results,
                **mb,
                "results_sources_hit": bool(src_hits),
                "results_sources_hit_only_metadata": bool(src_hits) and all(
                    r["retrieval_channel"] == "source_metadata" for r in src_hits),
                "expected_unit_in_candidate_set": pool_in,
            })

    agg_k5 = t72.aggregate(per_case_k5, cfg_k5)
    agg_k10 = t72.aggregate(per_case_k10, cfg_k10)
    m2_compact = [{
        "example_id": p["example_id"],
        "source_first_rank": p["source_first_rank"],
        "unit_hit_rank": p["unit_hit_rank"],
        "evidence_answer_score": p["evidence_answer_score"],
    } for p in per_case_k5]

    # ---------------- attribution split (from experiment outputs) -------------
    metrics_path = t72.OUT_METRICS
    metrics = json.loads(metrics_path.read_text())
    rows = t72.load_jsonl(t72.OUT_RESULTS)  # task72_retrieval_results.jsonl
    by_id = {r["example_id"]: r for r in rows}
    r0 = metrics["aggregate"]["R0"]
    r8 = metrics["aggregate"]["R8"]

    split_rows = []
    for eid in r0["ranking_miss_cases"]:
        r = by_id[eid]
        uw = r["configs"]["R8"].get("unit_within_source") or {}
        ranks = [(u, d.get("within_source_rank")) for u, d in uw.items()]
        known = [w for _, w in ranks if w is not None]
        split_rows.append({
            "example_id": eid,
            "within_source_ranks": {u: w for u, w in ranks},
            "min_within_rank": min(known) if known else None,
            "bucket": ("depth_blocked_gt10" if (not known or min(known) > 10)
                       else "fits_within_top10"),
        })
    n_depth = sum(1 for s in split_rows if s["bucket"] == "depth_blocked_gt10")
    n_fit = sum(1 for s in split_rows if s["bucket"] == "fits_within_top10")

    # per-unit merge blocking in actual R8 output (expected units with
    # within-rank <= 10 that are absent from the merged R8 top-10)
    merge_blocked = []
    width_pushed = []
    for r in rows:
        eid = r["example_id"]
        r8cfg = r["configs"]["R8"]
        r8_text_ids = {res["text_id"] for res in r8cfg["results"]}
        uhit = r8cfg["unit_hit_rank"]
        for u, d in (r8cfg.get("unit_within_source") or {}).items():
            w = d.get("within_source_rank")
            if w is None or w > 10:
                continue
            in_top10 = any(t72.unit_key(tid) == u for tid in r8_text_ids)
            if not in_top10:
                merge_blocked.append({"example_id": eid, "unit": u,
                                      "within_rank": w,
                                      "source_candidate_rank":
                                          r["selected_sources_r8"].get(
                                              u.split(":")[0])})
            elif uhit is not None and uhit > 5 and r8cfg["unit_hit_rank"] == uhit:
                # unit present but pushed past the k=5 evidence window
                hit_is_u = any(t72.unit_key(tid) == u
                               for tid, res in
                               ((res["text_id"], res) for res in r8cfg["results"])
                               if res["retrieval_rank"] == uhit)
                if hit_is_u and uhit > t72.CONFIGS["R8"]["evidence_k"]:
                    width_pushed.append({"example_id": eid, "unit": u,
                                         "within_rank": w, "r8_rank": uhit})

    # ev0 recovery accounting R0 -> R8 (from metrics aggregates)
    ev0_r0 = set(r0["ev0_cases"])
    ev0_r8 = set(r8["ev0_cases"])

    sensitivity = {
        "post_hoc": True,
        "purpose": ("isolate merge-policy effects (M2 score-order vs R8 "
                    "round-robin) and split residual ranking-miss into "
                    "within-source depth vs merge-blocking; NOT a "
                    "pre-registered config, NOT used for the primary verdict"),
        "M2_definition": ("top_k = global BM25 score order filtered to the "
                          "Task-69 selected sources + R8 fills policy (fills "
                          "kept only for zero-lexical sources); k5/500 and "
                          "k10/1000 scored like R0/R7"),
        "M2_K5_aggregate": agg_k5,
        "M2_K10_aggregate": agg_k10,
        "M2_K5_per_case_compact": m2_compact,
        "M2_K5_minus_R0": {
            k: round((agg_k5[k] or 0) - (r0[k] or 0), 4)
            for k in ("unit_recall_at_1", "unit_recall_at_3", "unit_recall_at_5",
                      "unit_recall_at_10", "unit_mrr", "source_recall_at_5",
                      "evidence_ceiling_mean")
        },
        "M2_K10_minus_R7": {
            k: round((agg_k10[k] or 0) - (metrics["aggregate"]["R7"][k] or 0), 4)
            for k in ("unit_recall_at_1", "unit_recall_at_3", "unit_recall_at_5",
                      "unit_recall_at_10", "unit_mrr", "source_recall_at_5",
                      "evidence_ceiling_mean")
        },
        "attribution_ranking_miss": {
            "n_ranking_miss_r0": len(split_rows),
            "n_depth_blocked_gt10": n_depth,
            "n_fits_within_top10": n_fit,
            "cases": split_rows,
        },
        "merge_blocked_units_r8": merge_blocked,
        "width_pushed_units_r8": width_pushed,
        "ev0_set_r0": sorted(ev0_r0),
        "ev0_set_r8": sorted(ev0_r8),
        "ev0_recovered_r8": sorted(ev0_r0 - ev0_r8),
        "ev0_new_r8": sorted(ev0_r8 - ev0_r0),
        "contract_violations_m2": violations,
        "runtime_seconds": round(time.time() - t0, 1),
    }
    metrics["post_hoc_sensitivity"] = sensitivity
    metrics_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n")

    print("== M2_K5 (score-order merge) vs R0 ==")
    print(json.dumps(sensitivity["M2_K5_minus_R0"], indent=1))
    print("== M2_K10 vs R7 ==")
    print(json.dumps(sensitivity["M2_K10_minus_R7"], indent=1))
    print("M2_K5 ceiling/ev0:", agg_k5["evidence_ceiling_mean"],
          agg_k5["evidence_ceiling_full"], "ev0:", agg_k5["ev0_count"])
    print("M2_K10 ceiling/ev0:", agg_k10["evidence_ceiling_mean"],
          agg_k10["evidence_ceiling_full"], "ev0:", agg_k10["ev0_count"])
    print(f"attribution: ranking-miss {len(split_rows)} = depth>10 {n_depth} "
          f"+ fits<=10 {n_fit}")
    print("merge_blocked:", json.dumps(merge_blocked))
    print("width_pushed:", json.dumps(width_pushed))
    print("ev0 recovered by R8:", sorted(ev0_r0 - ev0_r8),
          "new in R8:", sorted(ev0_r8 - ev0_r0))
    print("m2 violations:", len(violations))
    print(f"done in {time.time()-t0:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

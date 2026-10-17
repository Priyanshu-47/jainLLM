"""TASK 73 Phase 1 — reproduce the Task-69/R0 baseline retrieval, fresh.

Independently re-runs the exact Task-69 R0 pipeline (global BM25 -> pool 2000
-> diversify top-10 -> metadata fills -> combined top-10) over the frozen
corpus and gates against BOTH the frozen Task-69 evidence (byte-exact
text_ids/ranks/channels/context sha) and the published aggregate numbers:

  source R@5 = 0.913, source R@10 = 0.9783, unit MRR = 0.3333,
  evidence ceiling = 0.6318, Ev0 = 15

Exit 3 (STOP) on any mismatch. Never writes any artifact.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(REPO / "experiments" / "task72"))

import task72_experiment as t72  # noqa: E402  (shared frozen pipeline helpers)
from svk_corpus.retrieval import BM25Index, RetrievalResult  # noqa: E402
from svk_corpus.retrieval.rerank import Reranker  # noqa: E402

EXPECTED = {
    "source_recall_at_5": 0.913,
    "source_recall_at_10": 0.9783,
    "unit_mrr": 0.3333,
    "evidence_ceiling_mean": 0.6318,
    "evidence_ceiling_full": 26,
    "ev0_count": 15,
}


def build_r0_pipeline(cases: list[dict], cards: dict, bm25, sidx, expander,
                      diversify, verbose: bool = False):
    """Exact Task-69 R0 pipeline. Returns (per_case, byte_exact_ok)."""
    per_case: list[dict] = []
    frozen_rows = {r["example_id"]: r
                   for r in t72.load_jsonl(t72.FROZEN_EVIDENCE)}
    byte_exact = 0
    for case in cases:
        eid = case["example_id"]
        query = case["question"]
        prov = case.get("provenance") or {}
        esrc = prov.get("source_id")
        eunits = prov.get("unit_ids") or []

        full = bm25.search(query, top_k=10**9)
        pool = full[: t72.POOL]
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
        keep0 = max(t72.TOP_K - len(fill), 0)
        combined0 = (list(unit_tier[:keep0]) + fill)[: t72.TOP_K]
        norm_tokens = tuple(t72.expand_query_text(query))

        results0 = []
        for i, r in enumerate(combined0, 1):
            ch = t72.t69.channel_of(r, unit_ids)
            row, _ = t72.result_row(r, eid, i, ch, query, norm_tokens)
            results0.append(row)

        fr = frozen_rows[eid]
        gate_match = (
            [(r["text_id"], r["retrieval_rank"], r["retrieval_channel"])
             for r in results0]
            == [(r["text_id"], r["retrieval_rank"], r["retrieval_channel"])
                for r in fr["results"]]
        )
        m0 = t72.build_block_and_metrics(case, results0, cards,
                                         t72.CONFIGS["R0"])
        gate_match = gate_match and (
            m0["context_sha256"] == fr["evidence_context"]["sha256"])
        if gate_match:
            byte_exact += 1

        mb = m0
        first, uhit = t72.case_ranks(results0, case)
        src_hits = [r for r in results0 if r["source_id"] == esrc] if esrc else []
        per_case.append({
            "example_id": eid,
            "category": case["category"],
            "language": case["language"],
            "expected_source": esrc,
            "expected_units": eunits,
            "source_first_rank": first,
            "unit_hit_rank": uhit,
            "results": results0,
            **mb,
            "results_sources_hit": bool(src_hits),
            "results_sources_hit_only_metadata": bool(src_hits) and all(
                r["retrieval_channel"] == "source_metadata" for r in src_hits),
            "expected_unit_in_candidate_set": True,
        })
        if verbose:
            print(f"  {eid} exact={gate_match} src={first} unit={uhit} "
                  f"ev={mb['evidence_answer_score']}")
    return per_case, byte_exact


def build_retrieval_stack():
    docs = t72.load_corpus(t72.CORPUS_PATH, t72.MANIFEST_PATH)
    bm25 = BM25Index(docs, k1=1.5, b=0.75)
    sidx = t72.build_source_index(t72.MANIFEST_PATH)
    expander = t72.SourceUnitExpander(docs)
    diversify = Reranker(strategy="diversify", max_per_source=3)
    return docs, bm25, sidx, expander, diversify


def main() -> int:
    t0 = time.time()
    frozen_sha = t72.sha256_file(t72.CASES_PATH)
    if frozen_sha != t72.FROZEN_SHA:
        print(f"STOP: frozen benchmark sha mismatch {frozen_sha}")
        return 3
    print(f"frozen benchmark sha verified {frozen_sha[:16]}…")

    cases = t72.load_jsonl(t72.CASES_PATH)
    cards = t72.t69.load_manifest_cards(t72.MANIFEST_PATH)
    if len(cases) != 47:
        print(f"STOP: expected 47 cases, got {len(cases)}")
        return 3

    docs, bm25, sidx, expander, diversify = build_retrieval_stack()
    print(f"corpus {len(docs)} docs indexed")

    per_case, byte_exact = build_r0_pipeline(cases, cards, bm25, sidx,
                                             expander, diversify)
    agg = t72.aggregate(per_case, t72.CONFIGS["R0"])

    problems = []
    if byte_exact != 47:
        problems.append(f"byte-exact {byte_exact}/47 vs frozen Task-69 evidence")
    for key, want in EXPECTED.items():
        got = agg[key]
        if got != want:
            problems.append(f"{key}: {got} != {want}")

    print("gate values:", {k: agg[k] for k in EXPECTED})
    print(f"byte-exact vs frozen: {byte_exact}/47")
    if problems:
        print("PHASE1_BASELINE_GATE_FAIL")
        for p in problems:
            print("  -", p)
        return 3
    print(f"PHASE1_BASELINE_GATE_PASS ({time.time()-t0:.1f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

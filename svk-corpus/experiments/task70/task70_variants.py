"""TASK 70 Phase 5 — small controlled offline retrieval variants.

DOES NOT change production code, corpus, or benchmark. Variants only vary
analysis-side parameters through the shared instrumentation:

  R1  Mode-C baseline (top_k=10, ev_k=5, fill<=3)          [anchor]
  R2  EVIDENCE_K 5 -> 10 (same 10 candidates)
  R3  BM25/rerank depth top_k 10 -> 20, ev_k=5
  R4  metadata + BM25 candidate union (uncapped non-identifier
      fills) at top_k=20, ev_k=10
  R5  query normalization/alias expansion OFF (already present in R1;
      ablation measured via harness-level monkeypatch, index rebuilt)

No new embedding model, no dense retrieval, no reranker changes, no
downloads. RAG frozen scores: NOT_RUN (no local GPU; training-free offline
task judged by evidence-side metrics).

Output: data/evaluation/task70_variants.json
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from retrieval_stack import (  # noqa: E402
    CASES_PATH,
    PROMPTS_PATH,
    RetrievalConfig,
    load_jsonl,
    load_stack,
    retrieve,
)

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "data" / "evaluation" / "task70_variants.json"

VARIANTS = [
    RetrievalConfig(name="R1_baseline"),
    RetrievalConfig(name="R2_evidence_k10", ev_k=10),
    RetrievalConfig(name="R3_depth20", top_k=20),
    RetrievalConfig(name="R4_union_k20_ev10", top_k=20, ev_k=10, union_metadata=True),
    RetrievalConfig(name="R5_expansion_off", expand_on=False),
    # supplemental (existing config knobs only, no new machinery):
    RetrievalConfig(name="R6_trunc1000_k5", text_trunc=1000),
    RetrievalConfig(name="R7_k10_trunc1000", ev_k=10, text_trunc=1000),
]


def evaluate(cfg: RetrievalConfig, stack: dict, cases: list[dict], prompts: dict) -> dict:
    t0 = time.time()
    retr = {}
    for case in cases:
        retr[case["example_id"]] = retrieve(case, stack, cfg)

    src = [r for r in retr.values() if r["expected_source"]]
    unit = [r for r in retr.values() if r["expected_units"]]

    def recall(rows: list[dict], key: str, k: int) -> float:
        hits = [1.0 if (r[key] is not None and r[key] <= k) else 0.0 for r in rows]
        return round(sum(hits) / len(hits), 4) if hits else 0.0

    def mrr(rows: list[dict], key: str) -> float:
        vals = [(1.0 / r[key]) if r[key] else 0.0 for r in rows]
        return round(sum(vals) / len(vals), 4) if vals else 0.0

    ev_scores = [r["evidence_score"] for r in retr.values() if r["evidence_score"] is not None]
    abst = [r for r in retr.values() if r["abstention_case"]]
    pool_hits = sum(1 for r in unit if any(v is not None for v in r["unit_pool_ranks"].values()))

    sha_match = sum(
        1 for eid, r in retr.items() if r["block_sha256"] == prompts[eid]["context_sha256"]
    )
    return {
        "config": {
            "name": cfg.name,
            "top_k": cfg.top_k,
            "pool": cfg.pool,
            "max_fill": cfg.max_fill,
            "ev_k": cfg.ev_k,
            "text_trunc": cfg.text_trunc,
            "expand_on": cfg.expand_on,
            "union_metadata": cfg.union_metadata,
        },
        "source_recall_at_1": recall(src, "source_first_rank", 1),
        "source_recall_at_3": recall(src, "source_first_rank", 3),
        "source_recall_at_5": recall(src, "source_first_rank", 5),
        "source_recall_at_10": recall(src, "source_first_rank", 10),
        "source_mrr": mrr(src, "source_first_rank"),
        "source_zero_hits": [r["example_id"] for r in src if r["source_first_rank"] is None],
        "unit_recall_at_1": recall(unit, "unit_hit_rank", 1),
        "unit_recall_at_3": recall(unit, "unit_hit_rank", 3),
        "unit_recall_at_5": recall(unit, "unit_hit_rank", 5),
        "unit_recall_at_10": recall(unit, "unit_hit_rank", 10),
        "unit_mrr": mrr(unit, "unit_hit_rank"),
        "unit_in_pool_at_2000": f"{pool_hits}/{len(unit)}",
        "evidence_ceiling_mean": round(sum(ev_scores) / len(ev_scores), 4),
        "evidence_ceiling_full": sum(1 for s in ev_scores if s == 1.0),
        "ev0_count": sum(1 for s in ev_scores if s == 0.0),
        "ev0_cases": sorted(
            eid for eid, r in retr.items()
            if r["evidence_score"] == 0.0 and not r["abstention_case"]
        ),
        "abstention_forbidden_hit_count": sum(1 for r in abst if r["forbidden_hits"]),
        "contract_violations": sum(len(r["contract_violations"]) for r in retr.values()),
        "blocks_identical_to_task69": f"{sha_match}/47",
        "rag_frozen_score": "NOT_RUN (no local GPU; evidence-side metrics only)",
        "seconds": round(time.time() - t0, 1),
    }


def main() -> int:
    cases = load_jsonl(CASES_PATH)
    prompts = {r["example_id"]: r for r in load_jsonl(PROMPTS_PATH)}

    results = []
    stack_expanded = load_stack(RetrievalConfig(name="stack_expanded"))  # expansion ON
    for cfg in VARIANTS:
        if cfg.expand_on:
            stack = stack_expanded
        else:
            stack = load_stack(cfg)  # rebuild index with expansion off
        print(f"[{cfg.name}] running…", flush=True)
        res = evaluate(cfg, stack, cases, prompts)
        results.append(res)
        print(
            f"[{cfg.name}] srcR@5={res['source_recall_at_5']} "
            f"unitR@5={res['unit_recall_at_5']} ceiling={res['evidence_ceiling_mean']} "
            f"ev0={res['ev0_count']} sha_vs_task69={res['blocks_identical_to_task69']} "
            f"({res['seconds']}s)",
            flush=True,
        )

    payload = {
        "task": "TASK 70 Phase 5 — offline retrieval variants on frozen Task-60/69 queries",
        "frozen_sha256_verified": hashlib.sha256(
            CASES_PATH.read_bytes()
        ).hexdigest(),
        "variants": results,
        "notes": [
            "R1 must reproduce Task-69 blocks (blocks_identical_to_task69=47/47) — integrity anchor",
            "R3 is measured, not assumed: identical blocks to R1 would prove positional "
            "first-K selection makes depth-increase inert for evidence",
            "R5 ablates the repository's existing fold+alias expansion via harness-level "
            "monkeypatch only (svk_corpus source untouched, index rebuilt)",
            "RAG frozen score NOT_RUN for all variants (no local GPU; no training/inference "
            "spend authorized in this task)",
        ],
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""TASK 74 Phase 1 — reproduce the Task-69/R0 BM25 baseline, fresh.

Reuses the Task-73 Phase-1 gate code path (read-only import; no Task-69–73
artifact is modified): independent rerun of the exact Task-69 R0 pipeline
(global BM25 -> pool 2000 -> diversify top-10 -> metadata fills -> combined
top-10) over the frozen corpus, gated against BOTH the frozen Task-69
evidence (byte-exact) and the published aggregates:

  source R@5 = 0.913, source R@10 = 0.9783, unit MRR = 0.3333,
  evidence ceiling = 0.6318 (26 full), Ev0 = 15

Also verifies the frozen Task-60 SHA and, only after a PASS, writes the
47-row query input file for the dense embedding run:
  data/evaluation/task74_queries_input.jsonl

Exit 3 (STOP) on any mismatch.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "task73"))

import task73_phase1 as p1  # noqa: E402  (read-only reuse of the verified gate)
import task72_experiment as t72  # noqa: E402

QUERIES_OUT = REPO / "data" / "evaluation" / "task74_queries_input.jsonl"


def main() -> int:
    t0 = time.time()
    if t72.sha256_file(t72.CASES_PATH) != t72.FROZEN_SHA:
        print("STOP: frozen benchmark sha mismatch")
        return 3
    print(f"frozen benchmark sha verified {t72.FROZEN_SHA[:16]}…")

    cases = t72.load_jsonl(t72.CASES_PATH)
    cards = t72.t69.load_manifest_cards(t72.MANIFEST_PATH)
    if len(cases) != 47:
        print(f"STOP: expected 47 cases, got {len(cases)}")
        return 3

    docs, bm25, sidx, expander, diversify = p1.build_retrieval_stack()
    print(f"corpus {len(docs)} docs indexed")

    per_case, byte_exact = p1.build_r0_pipeline(cases, cards, bm25, sidx,
                                                expander, diversify)
    agg = t72.aggregate(per_case, t72.CONFIGS["R0"])

    problems = []
    if byte_exact != 47:
        problems.append(f"byte-exact {byte_exact}/47 vs frozen Task-69 evidence")
    for key, want in p1.EXPECTED.items():
        if agg[key] != want:
            problems.append(f"{key}: {agg[key]} != {want}")

    print("gate values:", {k: agg[k] for k in p1.EXPECTED})
    print(f"byte-exact vs frozen: {byte_exact}/47")
    if problems:
        print("PHASE1_BASELINE_GATE_FAIL")
        for p in problems:
            print("  -", p)
        return 3

    QUERIES_OUT.write_text(
        "".join(json.dumps({"example_id": c["example_id"],
                            "question": c["question"]}, ensure_ascii=False) + "\n"
                for c in cases),
        encoding="utf-8",
    )
    print(f"query input written: {QUERIES_OUT} "
          f"sha={t72.sha256_file(QUERIES_OUT)[:16]}…")
    print(f"PHASE1_BASELINE_GATE_PASS ({time.time()-t0:.1f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

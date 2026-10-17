"""TASK 72 Phase 1 — reconstruct the Task-69 baseline retrieval metrics.

Reads the FROZEN Task-69 artifacts only (never rewrites them) and recomputes:

  source Recall@5 / Recall@10
  unit MRR
  evidence ceiling (mean, full)
  Ev=0 count

both (a) from the recorded per-case metrics via the evaluate.py formulas and
(b) independently by re-scoring the stored evidence context blocks with the
frozen score_task60.group_pass scorer.

Expected (Task-69 / Task-70 measurements):
  source R@5 = 0.913, source R@10 = 0.9783, unit MRR = 0.3333,
  evidence ceiling = 0.6318 (full 26), Ev=0 = 15

Exit 3 (STOP) if any expected value does not reproduce.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "experiments" / "dapt_01" / "evaluation"))

import score_task60  # noqa: E402

CASES_PATH = REPO / "data" / "evaluation" / "dapt01_eval_cases.jsonl"
EVIDENCE_PATH = REPO / "data" / "evaluation" / "task69_rag_evidence.jsonl"
METRICS_PATH = REPO / "data" / "evaluation" / "task69_retrieval_metrics.json"

FROZEN_SHA = "06625f72190e3ae130447345afdc04342bd19cb76f842285706480cba7765b81"
EXPECTED = {
    "source_recall_at_5": 0.913,
    "source_recall_at_10": 0.9783,
    "unit_mrr": 0.3333,
    "evidence_answer_score_mean": 0.6318,
    "evidence_answer_score_full": 26,
    "ev0": 15,
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def main() -> int:
    problems: list[str] = []

    frozen_sha = sha256_file(CASES_PATH)
    if frozen_sha != FROZEN_SHA:
        print(f"STOP: frozen benchmark sha mismatch {frozen_sha}")
        return 3
    print(f"frozen benchmark sha verified {frozen_sha[:16]}…")

    metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    per_case = metrics["per_case"]
    agg = metrics["aggregate"]

    # ---- (a) recompute aggregates from per-case rows (evaluate.py formulas) ----
    src = [p for p in per_case if p["expected_source"]]
    unit = [p for p in per_case if p["expected_units"]]
    r5 = round(sum(1.0 if p["source_hit_at_5"] else 0.0 for p in src) / len(src), 4)
    r10 = round(sum(1.0 if p["source_hit_at_10"] else 0.0 for p in src) / len(src), 4)
    unit_mrr = round(sum(p["unit_reciprocal_rank"] for p in unit) / len(unit), 4)
    scores = [p["evidence_answer_score"] for p in per_case if p["evidence_answer_score"] is not None]
    ceil_mean = round(sum(scores) / len(scores), 4)
    ceil_full = sum(1 for s in scores if s == 1.0)
    ev0 = sum(1 for s in scores if s == 0.0)

    recomputed = {
        "source_recall_at_5": r5,
        "source_recall_at_10": r10,
        "unit_mrr": unit_mrr,
        "evidence_answer_score_mean": ceil_mean,
        "evidence_answer_score_full": ceil_full,
        "ev0": ev0,
    }

    # ---- (b) independent ceiling: re-score frozen evidence blocks ----
    cases = {c["example_id"]: c for c in load_jsonl(CASES_PATH)}
    evidence = load_jsonl(EVIDENCE_PATH)
    if len(evidence) != 47:
        problems.append(f"evidence rows {len(evidence)} != 47")
    blockscores = []
    for row in evidence:
        case = cases[row["example_id"]]
        block = row["evidence_context"]["text"]
        groups = case.get("scoring") or []
        if case.get("abstention_case"):
            continue
        passes = [score_task60.group_pass(g, block) for g in groups]
        blockscores.append(sum(passes) / len(passes) if passes else None)
    bs = [s for s in blockscores if s is not None]
    independent = {
        "evidence_answer_score_mean": round(sum(bs) / len(bs), 4),
        "evidence_answer_score_full": sum(1 for s in bs if s == 1.0),
        "ev0": sum(1 for s in bs if s == 0.0),
    }

    # ---- compare ----
    for key, want in EXPECTED.items():
        got = recomputed[key]
        ok = got == want
        print(f"  {key}: recomputed={got} expected={want} {'OK' if ok else 'MISMATCH'}")
        if not ok:
            problems.append(f"{key} recomputed {got} != {want}")
        if agg.get(key, "n/a") not in (want, "n/a"):
            # stored aggregate must also agree (skip keys absent from agg)
            if key in agg and agg[key] != want:
                problems.append(f"stored agg {key} {agg[key]} != {want}")
    for key, want in (("evidence_answer_score_mean", EXPECTED["evidence_answer_score_mean"]),
                      ("evidence_answer_score_full", EXPECTED["evidence_answer_score_full"]),
                      ("ev0", EXPECTED["ev0"])):
        got = independent[key]
        ok = got == want
        print(f"  independent block-rescore {key}: {got} expected {want} {'OK' if ok else 'MISMATCH'}")
        if not ok:
            problems.append(f"independent {key} {got} != {want}")

    if problems:
        print("PHASE1_BASELINE_GATE_FAIL")
        for p in problems:
            print("  -", p)
        return 3
    print("PHASE1_BASELINE_GATE_PASS — Task-69 baseline reproduces "
          "(R@5 0.913, R@10 0.9783, unit MRR 0.3333, ceiling 0.6318/26, Ev0 15)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

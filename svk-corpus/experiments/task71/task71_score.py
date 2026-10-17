"""TASK 71 Phase 5 — four-arm scorer (Task-60 frozen metric, Task-69 scorer reused).

Imports experiments/task69/score_task69_rag.py VERBATIM (score_task60
norm/group_pass/score_case + score_task68_4way behaviour detectors) and only
rebinds input/output paths so the R7 arms are scored with the identical
metric implementation:

  base            frozen Task-60  dapt01_base_results.jsonl
  dapt            frozen Task-60  dapt01_dapt_results.jsonl
  base_rag        new             task71_base_rag_results.jsonl     (R7)
  dapt_rag        new             task71_dapt_rag_results.jsonl     (R7)
  retrieval       new             task71_r7_metrics.json
  evidence        new             task71_r7_evidence.jsonl
  prompts         new             task71_r7_prompts.jsonl
  run metadata    new             task71_r7_run_metadata.json

Output
  data/evaluation/task71_r7_comparison.json  (relabelled Task-71)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
EVAL = REPO / "data" / "evaluation"
sys.path.insert(0, str(REPO / "experiments" / "task69"))

import score_task69_rag as s69  # noqa: E402

OUT_PATH = EVAL / "task71_r7_comparison.json"


def main() -> int:
    s69.ARMS_PATHS = {
        "base": EVAL / "dapt01_base_results.jsonl",
        "dapt": EVAL / "dapt01_dapt_results.jsonl",
        "base_rag": EVAL / "task71_base_rag_results.jsonl",
        "dapt_rag": EVAL / "task71_dapt_rag_results.jsonl",
    }
    s69.METRICS_PATH = EVAL / "task71_r7_metrics.json"
    s69.EVIDENCE_PATH = EVAL / "task71_r7_evidence.jsonl"
    s69.PROMPTS_PATH = EVAL / "task71_r7_prompts.jsonl"
    s69.RUNMETA_PATH = EVAL / "task71_r7_run_metadata.json"
    s69.OUT_PATH = OUT_PATH

    rc = s69.main()
    if rc != 0:
        raise SystemExit(f"score_task69_rag.main failed rc={rc}")

    payload = json.loads(OUT_PATH.read_text(encoding="utf-8"))
    payload["task"] = "TASK 71 — R7 GOVERNED RAG CONTROLLED EVALUATION"
    payload["design"]["retrieval_mode"] = (
        "unit_bm25 + source_metadata combined (evaluate.py mode C); "
        "R7 evidence window EVIDENCE_K=10, TEXT_TRUNC=1000"
    )
    payload["design"]["metric_source"] = (
        "score_task60 norm/group_pass/score_case imported verbatim via "
        "score_task69_rag (identical implementation as Task-69)"
    )
    payload["design"]["arms"]["base"] = "ARM C (frozen Task-60): no RAG — identical to Task-69"
    payload["design"]["arms"]["dapt"] = "ARM D (frozen Task-60): DAPT-01, no RAG — identical to Task-69"
    payload["design"]["arms"]["base_rag"] = "ARM A (new): BASE + R7 governed evidence"
    payload["design"]["arms"]["dapt_rag"] = "ARM B (new): DAPT-01 + R7 governed evidence"
    payload["task69_reference"] = {
        "comparison_file": "data/evaluation/task69_rag_comparison.json",
        "base_rag_macro": 0.5816, "base_rag_pass_all": 25,
        "dapt_rag_macro": 0.5603, "dapt_rag_pass_all": 23,
        "evidence_ceiling_mean": 0.6318, "evidence_ceiling_full": 15,
        "prompts_sha256": "00096f61a4a2aea525b2f1bfe71449b626bc17a60073e4b4e9dac05f6edd5b8e",
    }
    OUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    overall = payload["overall"]
    gains = payload["gains"]
    print(f"relabelled {OUT_PATH.relative_to(REPO)}")
    print("overall:", json.dumps(overall))
    print("gains:", json.dumps({k: v["delta"] for k, v in gains.items()}))
    ce = payload["evidence_ceiling"]
    print("ceiling:", ce["evidence_answer_score_mean"], "full:", ce["evidence_answer_score_full"])
    for arm in ("base_rag", "dapt_rag"):
        print(f"  {arm} failures:", json.dumps(payload["failure_classification"]["counts"][arm]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

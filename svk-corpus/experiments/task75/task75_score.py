"""TASK 75 scorer — four-arm (BASE/DAPT-01 × no-RAG/H3_RRF20-RAG).

Imports experiments/task69/score_task69_rag.py VERBATIM (score_task60
norm/group_pass/score_case + score_task68_4way behaviour detectors) and only
rebinds input/output paths so the four Task-75 arms are scored with the
identical metric implementation:

  base       fresh  task75_base_norag_results.jsonl
  dapt       fresh  task75_dapt_norag_results.jsonl
  base_rag   fresh  task75_base_rrf20_results.jsonl   (H3_RRF20)
  dapt_rag   fresh  task75_dapt_rrf20_results.jsonl   (H3_RRF20)
  retrieval  fresh  task75_retrieval_metrics.json
  evidence   fresh  task75_rag_evidence.jsonl
  prompts    fresh  task75_rag_prompts.jsonl
  runmeta    fresh  task75_rag_run_metadata.json

Output
  data/evaluation/task75_rag_comparison.json

Task-60/69/71 frozen aggregates are recorded as reference only (no re-score).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
EVAL = REPO / "data" / "evaluation"
sys.path.insert(0, str(REPO / "experiments" / "task69"))

import score_task69_rag as s69  # noqa: E402

OUT_PATH = EVAL / "task75_rag_comparison.json"


def main() -> int:
    s69.ARMS_PATHS = {
        "base": EVAL / "task75_base_norag_results.jsonl",
        "dapt": EVAL / "task75_dapt_norag_results.jsonl",
        "base_rag": EVAL / "task75_base_rrf20_results.jsonl",
        "dapt_rag": EVAL / "task75_dapt_rrf20_results.jsonl",
    }
    s69.METRICS_PATH = EVAL / "task75_retrieval_metrics.json"
    s69.EVIDENCE_PATH = EVAL / "task75_rag_evidence.jsonl"
    s69.PROMPTS_PATH = EVAL / "task75_rag_prompts.jsonl"
    s69.RUNMETA_PATH = EVAL / "task75_rag_run_metadata.json"
    s69.OUT_PATH = OUT_PATH

    rc = s69.main()
    if rc != 0:
        raise SystemExit(f"score_task69_rag.main failed rc={rc}")

    payload = json.loads(OUT_PATH.read_text(encoding="utf-8"))
    payload["task"] = "TASK 75 — FOUR-ARM RRF@20 RAG GENERATION GATE"
    payload["design"]["retrieval_mode"] = (
        "H3_RRF20: deterministic RRF(BM25 full, bge-m3 dense full) k=20; "
        "evidence window EVIDENCE_K=5, TEXT_TRUNC=500 (Task-69 width)"
    )
    payload["design"]["metric_source"] = (
        "score_task60 norm/group_pass/score_case imported verbatim via "
        "score_task69_rag (identical implementation as Task-69/71)"
    )
    payload["design"]["arms"] = {
        "base": "ARM A (fresh): Qwen3-8B-Base, no RAG",
        "dapt": "ARM B (fresh): DAPT-01 checkpoint-15248, no RAG",
        "base_rag": "ARM C (fresh): Qwen3-8B-Base + H3_RRF20 evidence",
        "dapt_rag": "ARM D (fresh): DAPT-01 + H3_RRF20 evidence (identical bytes to C)",
    }
    payload["prior_references"] = {
        "task60_frozen": {
            "base_macro": 0.2021, "base_pass_all": 6,
            "dapt_macro": 0.266, "dapt_pass_all": 8,
        },
        "task69_r0": {
            "base_rag_macro": 0.5816, "base_rag_pass_all": 25,
            "dapt_rag_macro": 0.5603, "dapt_rag_pass_all": 23,
            "evidence_ceiling_mean": 0.6318, "evidence_ceiling_full": 15,
            "ev0_count": 15,
            "prompts_sha256": "00096f61a4a2aea525b2f1bfe71449b626bc17a60073e4b4e9dac05f6edd5b8e",
        },
        "task71_r7": {
            "base_rag_macro": 0.6312, "base_rag_pass_all": 29,
            "dapt_rag_macro": 0.6702, "dapt_rag_pass_all": 29,
            "evidence_ceiling_mean": 0.7403, "evidence_ceiling_full": 31,
            "verdict": "DO_NOT_RECOMMEND (abstention regression + loops up)",
            "prompts_sha256": "8dd60723b03df16b2a20be2c43d6ab24fd09aeb73fcaa0b2c42536976d65ce11",
        },
        "task74_h3rrf20_retrieval": {
            "unit_recall_at_5": 0.5385, "source_recall_at_5": 0.9783,
            "evidence_ceiling_mean": 0.8372, "evidence_ceiling_full": 36,
            "ev0_count": 7,
        },
    }
    OUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False),
                        encoding="utf-8")

    overall = payload["overall"]
    gains = payload["gains"]
    print(f"scored {OUT_PATH.relative_to(REPO)}")
    print("overall:", json.dumps(overall))
    print("gains:", json.dumps({k: v["delta"] for k, v in gains.items()}))
    ce = payload["evidence_ceiling"]
    print("ceiling:", ce["evidence_answer_score_mean"],
          "full:", ce["evidence_answer_score_full"])
    for arm in ("base_rag", "dapt_rag"):
        print(f"  {arm} failures:",
              json.dumps(payload["failure_classification"]["counts"][arm]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

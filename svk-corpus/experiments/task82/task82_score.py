"""TASK 82 scorer — four-arm (BASE/DAPT-01 × no-RAG/optimized-H3_RRF20-RAG).

Imports experiments/task69/score_task69_rag.py VERBATIM (score_task60
norm/group_pass/score_case + score_task68_4way behaviour detectors) and only
rebinds input/output paths so the four Task-82 arms are scored with the
identical metric implementation used for Task-60/69/71/75:

  base       task82_base_norag_results.jsonl
  dapt       task82_dapt_norag_results.jsonl
  base_rag   task82_base_rrf250_results.jsonl   (optimized H3_RRF20 pool=250)
  dapt_rag   task82_dapt_rrf250_results.jsonl   (optimized H3_RRF20 pool=250)
  retrieval  task82_retrieval_metrics.json
  evidence   task82_rag_evidence.jsonl
  prompts    task82_rag_prompts.jsonl
  runmeta    task82_rag_run_metadata.json   (pulled from Kaggle)

Output
  data/evaluation/task82_rag_comparison.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
EVAL = REPO / "data" / "evaluation"
sys.path.insert(0, str(REPO / "experiments" / "task69"))

import score_task69_rag as s69  # noqa: E402

OUT_PATH = EVAL / "task82_rag_comparison.json"


def main() -> int:
    s69.ARMS_PATHS = {
        "base": EVAL / "task82_base_norag_results.jsonl",
        "dapt": EVAL / "task82_dapt_norag_results.jsonl",
        "base_rag": EVAL / "task82_base_rrf250_results.jsonl",
        "dapt_rag": EVAL / "task82_dapt_rrf250_results.jsonl",
    }
    s69.METRICS_PATH = EVAL / "task82_retrieval_metrics.json"
    s69.EVIDENCE_PATH = EVAL / "task82_rag_evidence.jsonl"
    s69.PROMPTS_PATH = EVAL / "task82_rag_prompts.jsonl"
    s69.RUNMETA_PATH = EVAL / "task82_rag_run_metadata.json"
    s69.OUT_PATH = OUT_PATH

    for p in list(s69.ARMS_PATHS.values()) + [
        s69.METRICS_PATH, s69.EVIDENCE_PATH, s69.PROMPTS_PATH
    ]:
        if not p.exists():
            raise SystemExit(f"missing input: {p}")

    rc = s69.main()
    if rc != 0:
        raise SystemExit(f"score_task69_rag.main failed rc={rc}")

    payload = json.loads(OUT_PATH.read_text(encoding="utf-8"))
    payload["task"] = "TASK 82 — FOUR-ARM OPTIMIZED H3_RRF20 (pool=250) GENERATION GATE"
    payload["design"]["retrieval_mode"] = (
        "optimized H3_RRF20: deterministic RRF(BM25 pool=250, bge-m3 dense full) "
        "k=20; evidence window EVIDENCE_K=5, TEXT_TRUNC=500 (Task-69/75 width); "
        "Task-81 best eligible pool"
    )
    payload["design"]["metric_source"] = (
        "score_task60 norm/group_pass/score_case imported verbatim via "
        "score_task69_rag (identical implementation as Task-69/71/75)"
    )
    payload["design"]["arms"] = {
        "base": "ARM A (fresh): Qwen3-8B-Base, no RAG",
        "dapt": "ARM B (fresh): DAPT-01 checkpoint-15248, no RAG",
        "base_rag": "ARM C (fresh): Qwen3-8B-Base + optimized H3_RRF20 (pool=250)",
        "dapt_rag": (
            "ARM D (fresh): DAPT-01 + optimized H3_RRF20 (pool=250) "
            "(identical bytes to C)"
        ),
    }
    payload["prior_references"] = {
        "task75_four_arms": {
            "base_macro": 0.2021, "base_pass_all": 6,
            "dapt_macro": 0.266, "dapt_pass_all": 8,
            "base_rag_macro": 0.695, "base_rag_pass_all": 32,
            "dapt_rag_macro": 0.695, "dapt_rag_pass_all": 31,
            "evidence_ceiling_mean": 0.8372, "evidence_ceiling_full": 36,
            "ev0_count": 7,
            "prompts_sha256": "302f6c917b538bb440d244eeeba9aba35756186bef04cb1cd89415f65a774409",
            "run_host": "Google Colab T4",
            "verdict": "RECOMMEND_H3_RRF20",
        },
        "task74_h3rrf20_retrieval_full_list": {
            "unit_recall_at_5": 0.5385, "source_recall_at_5": 0.9783,
            "evidence_ceiling_mean": 0.8372, "evidence_ceiling_full": 36,
            "ev0_count": 7,
        },
        "task81_pool250_retrieval": {
            "unit_recall_at_5": 0.5385, "source_recall_at_5": 0.9783,
            "evidence_ceiling_mean": 0.8372, "ev0_count": 7,
            "contexts_matching_task75": 35,
            "contexts_differing": 12,
            "all_ceiling_deltas_zero": True,
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

"""TASK 65 scorer: three-way BASE vs BASE+DAPT-01 vs BASE+DAPT-01+SFT-01.

Inputs
  data/evaluation/dapt01_eval_cases.jsonl   (frozen 47 cases, never modified)
  data/evaluation/dapt01_base_results.jsonl (Task-60 BASE arm, frozen)
  data/evaluation/dapt01_dapt_results.jsonl (Task-60 DAPT arm, frozen)
  data/evaluation/dapt01_sft_results.jsonl  (Task-65 SFT arm, new)
  optional: data/evaluation/dapt01_evaluator_review.jsonl (base/dapt only)

Output
  data/evaluation/sft01_3way_comparison.json   (does NOT overwrite
  dapt01_comparison.json; the Task-60 artifact stays untouched)

Metric definitions
  Identical to Task 60: this script imports score_task60 and applies its
  norm/group_pass/score_case functions verbatim to all three arms, so any
  delta is attributable to the adapter, not to a metric change.
  Evaluator-based fields (factual_error / unsupported_claims / sect_confusion /
  degenerate_loop) exist only for base and dapt in the frozen review file;
  the SFT arm is reported as NOT_MEASURED and never synthesised.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
EVAL = REPO / "data" / "evaluation"
sys.path.insert(0, str(EVAL.parent.parent / "experiments" / "dapt_01" / "evaluation"))
import score_task60 as s60  # noqa: E402

CASES_PATH = EVAL / "dapt01_eval_cases.jsonl"
BASE_PATH = EVAL / "dapt01_base_results.jsonl"
DAPT_PATH = EVAL / "dapt01_dapt_results.jsonl"
SFT_PATH = EVAL / "dapt01_sft_results.jsonl"
REVIEW_PATH = EVAL / "dapt01_evaluator_review.jsonl"
OUT_PATH = EVAL / "sft01_3way_comparison.json"


def main() -> int:
    cases = s60.load_jsonl(CASES_PATH)
    base_rows = {r["example_id"]: r for r in s60.load_jsonl(BASE_PATH)}
    dapt_rows = {r["example_id"]: r for r in s60.load_jsonl(DAPT_PATH)}
    sft_rows = {r["example_id"]: r for r in s60.load_jsonl(SFT_PATH)}
    review = {}
    if REVIEW_PATH.exists():
        review = {r["example_id"]: r for r in s60.load_jsonl(REVIEW_PATH)}

    case_ids = [c["example_id"] for c in cases]
    if not (len(cases) == len(base_rows) == len(dapt_rows) == len(sft_rows) == 47):
        raise SystemExit("expected 47 rows in every arm")
    for name, rows in (("base", base_rows), ("dapt", dapt_rows), ("sft", sft_rows)):
        missing = [i for i in case_ids if i not in rows]
        if missing:
            raise SystemExit(f"{name} arm missing {missing}")
        empty = [i for i in case_ids if not (rows[i].get("answer") or "").strip()]
        if empty:
            raise SystemExit(f"{name} arm has empty answers: {empty}")

    per_case = []
    for c in cases:
        eid = c["example_id"]
        sb = s60.score_case(c, base_rows[eid]["answer"])
        sd = s60.score_case(c, dapt_rows[eid]["answer"])
        ss = s60.score_case(c, sft_rows[eid]["answer"])
        rv = review.get(eid, {})

        def d(a, b):
            if a is None or b is None:
                return None
            return round(a - b, 4)

        delta_sft_dapt = d(ss["objective_score"], sd["objective_score"])
        delta_sft_base = d(ss["objective_score"], sb["objective_score"])
        per_case.append({
            "example_id": eid,
            "category": c["category"],
            "language": c["language"],
            "question": c["question"],
            "expected_answer_or_reference": c["expected_answer_or_reference"],
            "provenance": c["provenance"],
            "dapt_split": c["provenance"].get("dapt_split"),
            "abstention_case": c["abstention_case"],
            "base_answer": base_rows[eid]["answer"],
            "dapt_answer": dapt_rows[eid]["answer"],
            "sft_answer": sft_rows[eid]["answer"],
            "base_score": sb["objective_score"],
            "dapt_score": sd["objective_score"],
            "sft_score": ss["objective_score"],
            "base_groups_satisfied": sb["groups_satisfied"],
            "dapt_groups_satisfied": sd["groups_satisfied"],
            "sft_groups_satisfied": ss["groups_satisfied"],
            "abstention_correct_base": sb.get("abstention_correct"),
            "abstention_correct_dapt": sd.get("abstention_correct"),
            "abstention_correct_sft": ss.get("abstention_correct"),
            "sft_vs_dapt": delta_sft_dapt,
            "sft_vs_base": delta_sft_base,
            "verdict_vs_dapt": (
                "improved" if delta_sft_dapt and delta_sft_dapt > 0 else
                "regressed" if delta_sft_dapt and delta_sft_dapt < 0 else
                "same"
            ),
            "verdict_vs_base": (
                "improved" if delta_sft_base and delta_sft_base > 0 else
                "regressed" if delta_sft_base and delta_sft_base < 0 else
                "same"
            ),
            "evaluator_review": rv if rv else None,
            "notes": c.get("notes", ""),
        })

    def agg(rows, key):
        vals = [r[key] for r in rows if r[key] is not None]
        return round(sum(vals) / len(vals), 4) if vals else None

    def row3(rows, arm):
        return agg(rows, f"{arm}_score")

    categories = sorted({r["category"] for r in per_case})
    cat_table = []
    for cat in categories:
        rows = [r for r in per_case if r["category"] == cat]
        b, d_, s = row3(rows, "base"), row3(rows, "dapt"), row3(rows, "sft")
        cat_table.append({
            "category": cat,
            "n": len(rows),
            "base_mean_score": b,
            "dapt_mean_score": d_,
            "sft_mean_score": s,
            "sft_minus_dapt": round(s - d_, 4) if s is not None and d_ is not None else None,
            "sft_minus_base": round(s - b, 4) if s is not None and b is not None else None,
            "base_pass_all": sum(1 for r in rows if r["base_score"] == 1),
            "dapt_pass_all": sum(1 for r in rows if r["dapt_score"] == 1),
            "sft_pass_all": sum(1 for r in rows if r["sft_score"] == 1),
            "abstention_cases": sum(1 for r in rows if r["abstention_case"]),
        })

    language_table = []
    for lang in sorted({r["language"] for r in per_case}):
        rows = [r for r in per_case if r["language"] == lang]
        b, d_, s = row3(rows, "base"), row3(rows, "dapt"), row3(rows, "sft")
        language_table.append({
            "language": lang,
            "n": len(rows),
            "base_mean_score": b,
            "dapt_mean_score": d_,
            "sft_mean_score": s,
            "sft_minus_dapt": round(s - d_, 4) if s is not None and d_ is not None else None,
            "sft_minus_base": round(s - b, 4) if s is not None and b is not None else None,
        })

    split_table = []
    for split in ["train", "val", "test"]:
        rows = [r for r in per_case if r["dapt_split"] == split]
        if not rows:
            continue
        b, d_, s = row3(rows, "base"), row3(rows, "dapt"), row3(rows, "sft")
        split_table.append({
            "dapt_split": split,
            "n": len(rows),
            "base_mean_score": b,
            "dapt_mean_score": d_,
            "sft_mean_score": s,
            "sft_minus_dapt": round(s - d_, 4) if s is not None and d_ is not None else None,
            "sft_minus_base": round(s - b, 4) if s is not None and b is not None else None,
        })

    abst_rows = [r for r in per_case if r["abstention_case"]]
    improvements = [r["example_id"] for r in per_case if r["verdict_vs_dapt"] == "improved"]
    regressions = [r["example_id"] for r in per_case if r["verdict_vs_dapt"] == "regressed"]

    coverage = sum(1 for r in per_case if r["evaluator_review"])

    def ev_count(arm, field):
        out = []
        for r in per_case:
            rv = r.get("evaluator_review")
            if rv and arm in rv and isinstance(rv[arm].get(field), (int, bool)):
                out.append(int(rv[arm][field]))
        return sum(out) if out else None

    def ev_bool(arm, field):
        out = [
            rv[arm].get(field)
            for rv in (r.get("evaluator_review") for r in per_case)
            if rv and arm in rv and isinstance(rv[arm].get(field), bool)
        ]
        return sum(1 for v in out if v) if out else None

    comparison = {
        "task": "TASK 65 — SFT-01 THREE-WAY EVALUATION (BASE vs DAPT-01 vs DAPT-01+SFT-01)",
        "artifacts": {
            "cases": str(CASES_PATH.relative_to(REPO)),
            "cases_sha256": __import__("hashlib").sha256(CASES_PATH.read_bytes()).hexdigest(),
            "base_results": str(BASE_PATH.relative_to(REPO)),
            "dapt_results": str(DAPT_PATH.relative_to(REPO)),
            "sft_results": str(SFT_PATH.relative_to(REPO)),
            "evaluator_review": str(REVIEW_PATH.relative_to(REPO)) if REVIEW_PATH.exists() else None,
        },
        "design": {
            "model": "Qwen/Qwen3-8B-Base",
            "arms": {
                "base": "no adapter (Task-60 frozen results)",
                "dapt": "priyanshu471/dapt01-checkpoint-15248 (Task-60 frozen results)",
                "sft": "priyanshu471/sft01-output — DAPT-01 checkpoint-15248 continued by SFT-01 (Task-65)",
            },
            "quantization": "4bit-nf4-double, compute dtype fp16 (identical across arms)",
            "decoding": "greedy (do_sample=False)",
            "max_new_tokens": 192,
            "seed": 42,
            "identical_prompts_and_cases_all_arms": True,
            "env_parity_with_task60": (
                "task65_sft_infer_metadata.json env matches task60_run_metadata.json "
                "(transformers/torch/gpu/decoding/max_new_tokens/seed)"
            ),
            "n_cases": len(per_case),
        },
        "metric_definitions": s60.__doc__.strip() if s60.__doc__ else None,
        "n_cases": len(per_case),
        "category_table": cat_table,
        "language_table": language_table,
        "dapt_split_table": split_table,
        "overall_objective": {
            "base_mean_score": agg(per_case, "base_score"),
            "dapt_mean_score": agg(per_case, "dapt_score"),
            "sft_mean_score": agg(per_case, "sft_score"),
            "sft_minus_dapt": (
                round(agg(per_case, "sft_score") - agg(per_case, "dapt_score"), 4)
                if agg(per_case, "sft_score") is not None and agg(per_case, "dapt_score") is not None
                else None
            ),
            "sft_minus_base": (
                round(agg(per_case, "sft_score") - agg(per_case, "base_score"), 4)
                if agg(per_case, "sft_score") is not None and agg(per_case, "base_score") is not None
                else None
            ),
            "base_pass_all": sum(1 for r in per_case if r["base_score"] == 1),
            "dapt_pass_all": sum(1 for r in per_case if r["dapt_score"] == 1),
            "sft_pass_all": sum(1 for r in per_case if r["sft_score"] == 1),
            "note": "macro-average of per-case objective scores; category-level results are authoritative",
        },
        "abstention": {
            "n_cases": len(abst_rows),
            "base_correct": sum(1 for r in abst_rows if r["abstention_correct_base"]),
            "dapt_correct": sum(1 for r in abst_rows if r["abstention_correct_dapt"]),
            "sft_correct": sum(1 for r in abst_rows if r["abstention_correct_sft"]),
            "per_case": [
                {
                    "example_id": r["example_id"],
                    "base_correct": r["abstention_correct_base"],
                    "dapt_correct": r["abstention_correct_dapt"],
                    "sft_correct": r["abstention_correct_sft"],
                    "sft_answer": r["sft_answer"][:300],
                }
                for r in abst_rows
            ],
        },
        "improvements_vs_dapt": improvements,
        "regressions_vs_dapt": regressions,
        "improvement_count_vs_dapt": len(improvements),
        "regression_count_vs_dapt": len(regressions),
        "improvements_vs_base": [r["example_id"] for r in per_case if r["verdict_vs_base"] == "improved"],
        "regressions_vs_base": [r["example_id"] for r in per_case if r["verdict_vs_base"] == "regressed"],
        "evaluator_based_counts": {
            "review_coverage": f"{coverage}/{len(per_case)}",
            "base_factual_errors": ev_count("base", "factual_error"),
            "dapt_factual_errors": ev_count("dapt", "factual_error"),
            "sft_factual_errors": "NOT_MEASURED",
            "base_unsupported_claims": ev_count("base", "unsupported_claims"),
            "dapt_unsupported_claims": ev_count("dapt", "unsupported_claims"),
            "sft_unsupported_claims": "NOT_MEASURED",
            "base_sect_confusion_cases": ev_bool("base", "sect_confusion"),
            "dapt_sect_confusion_cases": ev_bool("dapt", "sect_confusion"),
            "sft_sect_confusion_cases": "NOT_MEASURED",
            "base_degenerate_loop_cases": ev_bool("base", "degenerate_loop"),
            "dapt_degenerate_loop_cases": ev_bool("dapt", "degenerate_loop"),
            "sft_degenerate_loop_cases": "NOT_MEASURED",
            "label": "evaluator_based for base/dapt only; SFT arm NOT_MEASURED (no evaluator pass was run for it)",
        },
        "not_measured": [
            "SFT-arm factual_error / unsupported_claims / sect_confusion / degenerate_loop: NOT_MEASURED (dapt01_evaluator_review.jsonl covers base and dapt arms only; no evaluator pass was run for the SFT arm and none is synthesised).",
            "No automated fluency/grammar score (NOT_MEASURED).",
            "No pairwise human preference study (NOT_MEASURED).",
            "sft_eval_v1 per-example generations are recorded in sft01_eval_results.jsonl but not keyterm-scoreed (the 9 rows carry no scoring rubric; eval_loss progression is the held-out numeric signal) — NOT_MEASURED as a score.",
        ],
        "per_case": per_case,
    }

    OUT_PATH.write_text(json.dumps(comparison, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT_PATH.relative_to(REPO)} ({len(per_case)} cases)")
    print("overall:", json.dumps(comparison["overall_objective"]))
    print("abstention:", json.dumps(comparison["abstention"], default=str)[:400])
    print("vs dapt: improvements", len(improvements), "regressions", len(regressions))
    for row in cat_table:
        print(
            f"  {row['category']:<26} n={row['n']} base={row['base_mean_score']} "
            f"dapt={row['dapt_mean_score']} sft={row['sft_mean_score']} "
            f"sft-dapt={row['sft_minus_dapt']} sft-base={row['sft_minus_base']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

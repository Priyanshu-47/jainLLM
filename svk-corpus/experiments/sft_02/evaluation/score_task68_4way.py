"""TASK 68 scorer: four-way BASE vs BASE+DAPT-01 vs +SFT-01 vs +SFT-02.

Inputs
  data/evaluation/dapt01_eval_cases.jsonl    (frozen 47 cases, never modified)
  data/evaluation/dapt01_base_results.jsonl  (Task-60 BASE arm, frozen)
  data/evaluation/dapt01_dapt_results.jsonl  (Task-60 DAPT arm, frozen)
  data/evaluation/dapt01_sft_results.jsonl   (Task-65 SFT-01 arm, frozen)
  data/evaluation/dapt01_sft02_results.jsonl (Task-68 SFT-02 arm, new)
  optional: data/evaluation/dapt01_evaluator_review.jsonl (base/dapt only)
  metadata: task60_run_metadata.json / task65_sft_infer_metadata.json /
            data/reports/task68_sft02_infer_metadata.json (env parity)

Output
  data/evaluation/sft02_4way_comparison.json   (does NOT overwrite
  dapt01_comparison.json or sft01_3way_comparison.json)

Metric definitions
  Identical to Task 60/65: this script imports score_task60 and applies its
  norm/group_pass/score_case functions verbatim to all four arms, so any
  delta is attributable to the adapter, not to a metric change.
  Evaluator-based fields exist only for base and dapt in the frozen review
  file; the SFT arms are reported as NOT_MEASURED and never synthesised.

Mechanical behaviour detectors (uniform across all four arms, documented):
  looped(answer)     — (a) a normalised sentence (>=4 words) repeats >=3 times,
                       OR (b) a token sequence of length 1..8 repeats 3x
                       back-to-back. Deterministic; Task-66's original loop
                       counts (0/2/28) used an unpreserved detector, so all
                       cross-arm loop numbers here come from this one detector.
  infringement_count — occurrences of the literal token INFRINGEMENT (the
                       Task-66 signature of SFT-01 generation instability).
  opener             — first sentence (lowercased, whitespace-normalised);
                       mode share = share of cases sharing the most common
                       opener string.
  answer_len_chars   — median/mean answer length (concision signal; SFT-01
                       median was 851 vs DAPT 330 vs BASE 199).
"""

from __future__ import annotations

import hashlib
import json
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
EVAL = REPO / "data" / "evaluation"
REPORTS = REPO / "data" / "reports"
sys.path.insert(0, str(EVAL.parent.parent / "experiments" / "dapt_01" / "evaluation"))
import score_task60 as s60  # noqa: E402

CASES_PATH = EVAL / "dapt01_eval_cases.jsonl"
BASE_PATH = EVAL / "dapt01_base_results.jsonl"
DAPT_PATH = EVAL / "dapt01_dapt_results.jsonl"
SFT01_PATH = EVAL / "dapt01_sft_results.jsonl"
SFT02_PATH = EVAL / "dapt01_sft02_results.jsonl"
REVIEW_PATH = EVAL / "dapt01_evaluator_review.jsonl"
META60 = EVAL / "task60_run_metadata.json"
META65 = EVAL / "task65_sft_infer_metadata.json"
META68 = REPORTS / "task68_sft02_infer_metadata.json"
OUT_PATH = EVAL / "sft02_4way_comparison.json"

ARMS = ("base", "dapt", "sft01", "sft02")


def looped(answer: str) -> bool:
    """Uniform mechanical degeneration detector (see module docstring)."""
    sents = [re.sub(r"\W+", " ", s).lower().strip()
             for s in re.split(r"[.!?।\n]", answer or "")]
    sents = [s for s in sents if len(s.split()) >= 4]
    if any(v >= 3 for v in Counter(sents).values()):
        return True
    toks = (answer or "").split()
    for k in range(1, 9):
        for i in range(len(toks) - k * 3 + 1):
            if toks[i:i + k] == toks[i + k:i + 2 * k] == toks[i + 2 * k:i + 3 * k]:
                if k > 1 or any(len(t) > 2 for t in toks[i:i + k]):
                    return True
    return False


def opener_of(answer: str) -> str:
    first = re.split(r"[.!?।\n]", answer or "", maxsplit=1)[0]
    return re.sub(r"\s+", " ", first).strip().lower()


def behaviour(answers: list[str]) -> dict:
    lens = [len(a or "") for a in answers]
    openers = [opener_of(a) for a in answers]
    mode_op, mode_n = Counter(openers).most_common(1)[0]
    return {
        "n": len(answers),
        "looped_cases": sum(1 for a in answers if looped(a)),
        "infringement_token_outputs": sum(1 for a in answers if "INFRINGEMENT" in (a or "")),
        "answer_len_median": int(statistics.median(lens)),
        "answer_len_mean": round(statistics.mean(lens), 1),
        "answer_len_max": max(lens),
        "mode_opener": mode_op,
        "mode_opener_count": mode_n,
        "mode_opener_share": round(mode_n / len(answers), 4),
        "distinct_openers": len(set(openers)),
    }


def main() -> int:
    cases = s60.load_jsonl(CASES_PATH)
    rows = {
        "base": {r["example_id"]: r for r in s60.load_jsonl(BASE_PATH)},
        "dapt": {r["example_id"]: r for r in s60.load_jsonl(DAPT_PATH)},
        "sft01": {r["example_id"]: r for r in s60.load_jsonl(SFT01_PATH)},
        "sft02": {r["example_id"]: r for r in s60.load_jsonl(SFT02_PATH)},
    }
    review = {}
    if REVIEW_PATH.exists():
        review = {r["example_id"]: r for r in s60.load_jsonl(REVIEW_PATH)}

    case_ids = [c["example_id"] for c in cases]
    for arm in ARMS:
        if len(rows[arm]) != 47:
            raise SystemExit(f"{arm}: expected 47 rows, got {len(rows[arm])}")
        missing = [i for i in case_ids if i not in rows[arm]]
        if missing:
            raise SystemExit(f"{arm} arm missing {missing}")
        empty = [i for i in case_ids if not (rows[arm][i].get("answer") or "").strip()]
        if empty:
            raise SystemExit(f"{arm} arm has empty answers: {empty}")

    def delta(a, b):
        if a is None or b is None:
            return None
        return round(a - b, 4)

    def verdict(x):
        return "improved" if x and x > 0 else "regressed" if x and x < 0 else "same"

    per_case = []
    for c in cases:
        eid = c["example_id"]
        sc = {a: s60.score_case(c, rows[a][eid]["answer"]) for a in ARMS}
        rv = review.get(eid, {})
        entry = {
            "example_id": eid,
            "category": c["category"],
            "language": c["language"],
            "question": c["question"],
            "expected_answer_or_reference": c["expected_answer_or_reference"],
            "provenance": c["provenance"],
            "dapt_split": c["provenance"].get("dapt_split"),
            "abstention_case": c["abstention_case"],
        }
        for a in ARMS:
            entry[f"{a}_answer"] = rows[a][eid]["answer"]
            entry[f"{a}_score"] = sc[a]["objective_score"]
            entry[f"{a}_groups_satisfied"] = sc[a]["groups_satisfied"]
            entry[f"abstention_correct_{a}"] = sc[a].get("abstention_correct")
            entry[f"{a}_looped"] = looped(rows[a][eid]["answer"])
        entry["sft02_vs_dapt"] = delta(entry["sft02_score"], entry["dapt_score"])
        entry["sft02_vs_base"] = delta(entry["sft02_score"], entry["base_score"])
        entry["sft02_vs_sft01"] = delta(entry["sft02_score"], entry["sft01_score"])
        entry["verdict_vs_dapt"] = verdict(entry["sft02_vs_dapt"])
        entry["verdict_vs_base"] = verdict(entry["sft02_vs_base"])
        entry["verdict_vs_sft01"] = verdict(entry["sft02_vs_sft01"])
        entry["evaluator_review"] = rv if rv else None
        entry["notes"] = c.get("notes", "")
        per_case.append(entry)

    def agg(subset, arm):
        vals = [r[f"{arm}_score"] for r in subset if r[f"{arm}_score"] is not None]
        return round(sum(vals) / len(vals), 4) if vals else None

    def group_table(key, values):
        out = []
        for v in values:
            sub = [r for r in per_case if r[key] == v]
            if not sub:
                continue
            b, d_, s1, s2 = (agg(sub, a) for a in ARMS)
            out.append({
                key: v,
                "n": len(sub),
                "base_mean_score": b, "dapt_mean_score": d_,
                "sft01_mean_score": s1, "sft02_mean_score": s2,
                "sft02_minus_dapt": delta(s2, d_),
                "sft02_minus_base": delta(s2, b),
                "sft02_minus_sft01": delta(s2, s1),
                "base_pass_all": sum(1 for r in sub if r["base_score"] == 1),
                "dapt_pass_all": sum(1 for r in sub if r["dapt_score"] == 1),
                "sft01_pass_all": sum(1 for r in sub if r["sft01_score"] == 1),
                "sft02_pass_all": sum(1 for r in sub if r["sft02_score"] == 1),
                "abstention_cases": sum(1 for r in sub if r["abstention_case"]),
            })
        return out

    cat_table = group_table("category", sorted({r["category"] for r in per_case}))
    language_table = group_table("language", sorted({r["language"] for r in per_case}))
    split_table = group_table("dapt_split", ["train", "val", "test"])

    abst_rows = [r for r in per_case if r["abstention_case"]]
    behav = {a: behaviour([rows[a][eid]["answer"] for eid in case_ids]) for a in ARMS}

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

    env = {}
    for label, path, keys in (
        ("task60", META60, ("model", "transformers", "torch", "gpu", "decoding",
                            "max_new_tokens", "seed")),
        ("task65", META65, ("model", "transformers", "torch", "gpu", "decoding",
                            "max_new_tokens", "seed")),
        ("task68", META68, ("model", "transformers", "torch", "gpu", "decoding",
                            "max_new_tokens", "seed")),
    ):
        if path.exists():
            m = json.loads(path.read_text(encoding="utf-8"))
            env[label] = {k: m.get(k) for k in keys}
    parity_fields = ("model", "transformers", "torch", "gpu", "decoding",
                     "max_new_tokens", "seed")
    env_parity = all(
        len({env[t].get(f) for t in env}) == 1 for f in parity_fields
    ) and len(env) == 3

    overall = {
        "base_mean_score": agg(per_case, "base"),
        "dapt_mean_score": agg(per_case, "dapt"),
        "sft01_mean_score": agg(per_case, "sft01"),
        "sft02_mean_score": agg(per_case, "sft02"),
        "sft02_minus_dapt": delta(agg(per_case, "sft02"), agg(per_case, "dapt")),
        "sft02_minus_base": delta(agg(per_case, "sft02"), agg(per_case, "base")),
        "sft02_minus_sft01": delta(agg(per_case, "sft02"), agg(per_case, "sft01")),
        "base_pass_all": sum(1 for r in per_case if r["base_score"] == 1),
        "dapt_pass_all": sum(1 for r in per_case if r["dapt_score"] == 1),
        "sft01_pass_all": sum(1 for r in per_case if r["sft01_score"] == 1),
        "sft02_pass_all": sum(1 for r in per_case if r["sft02_score"] == 1),
        "note": "macro-average of per-case objective scores; category-level results are authoritative",
    }

    comparison = {
        "task": "TASK 68 — SFT-02 FOUR-WAY EVALUATION "
                "(BASE vs DAPT-01 vs DAPT-01+SFT-01 vs DAPT-01+SFT-02)",
        "artifacts": {
            "cases": str(CASES_PATH.relative_to(REPO)),
            "cases_sha256": hashlib.sha256(CASES_PATH.read_bytes()).hexdigest(),
            "base_results": str(BASE_PATH.relative_to(REPO)),
            "dapt_results": str(DAPT_PATH.relative_to(REPO)),
            "sft01_results": str(SFT01_PATH.relative_to(REPO)),
            "sft02_results": str(SFT02_PATH.relative_to(REPO)),
            "evaluator_review": str(REVIEW_PATH.relative_to(REPO)) if REVIEW_PATH.exists() else None,
        },
        "design": {
            "model": "Qwen/Qwen3-8B-Base",
            "arms": {
                "base": "no adapter (Task-60 frozen results)",
                "dapt": "priyanshu471/dapt01-checkpoint-15248 (Task-60 frozen results)",
                "sft01": "DAPT-01 continued by SFT-01, lr=1e-4, 3 epochs (Task-65 frozen results)",
                "sft02": "DAPT-01 continued by SFT-02, lr=3e-5, 2 epochs (Task-68)",
            },
            "quantization": "4bit-nf4-double, compute dtype fp16 (identical across arms)",
            "decoding": "greedy (do_sample=False)",
            "max_new_tokens": 192,
            "seed": 42,
            "identical_prompts_and_cases_all_arms": True,
            "env_parity_with_tasks60_65": env_parity,
            "env_by_task": env,
            "n_cases": len(per_case),
        },
        "metric_definitions": s60.__doc__.strip() if s60.__doc__ else None,
        "behaviour_detectors": {
            "looped": "sentence (>=4w) repeats >=3 OR token-seq len 1..8 repeats 3x back-to-back",
            "infringement_token_outputs": "answer contains literal token INFRINGEMENT",
            "opener": "first sentence, lowercased; mode_opener_share = most common opener share",
            "answer_len": "characters; concision signal",
            "note": "uniform across all 4 arms; Task-66's 0/2/28 loop counts came from an "
                    "unpreserved detector and are NOT numerically comparable to these",
        },
        "n_cases": len(per_case),
        "category_table": cat_table,
        "language_table": language_table,
        "dapt_split_table": split_table,
        "overall_objective": overall,
        "behaviour": behav,
        "abstention": {
            "n_cases": len(abst_rows),
            "base_correct": sum(1 for r in abst_rows if r["abstention_correct_base"]),
            "dapt_correct": sum(1 for r in abst_rows if r["abstention_correct_dapt"]),
            "sft01_correct": sum(1 for r in abst_rows if r["abstention_correct_sft01"]),
            "sft02_correct": sum(1 for r in abst_rows if r["abstention_correct_sft02"]),
            "per_case": [
                {
                    "example_id": r["example_id"],
                    "base_correct": r["abstention_correct_base"],
                    "dapt_correct": r["abstention_correct_dapt"],
                    "sft01_correct": r["abstention_correct_sft01"],
                    "sft02_correct": r["abstention_correct_sft02"],
                    "sft02_answer": r["sft02_answer"][:300],
                }
                for r in abst_rows
            ],
        },
        "improvements_vs_dapt": [r["example_id"] for r in per_case if r["verdict_vs_dapt"] == "improved"],
        "regressions_vs_dapt": [r["example_id"] for r in per_case if r["verdict_vs_dapt"] == "regressed"],
        "improvements_vs_sft01": [r["example_id"] for r in per_case if r["verdict_vs_sft01"] == "improved"],
        "regressions_vs_sft01": [r["example_id"] for r in per_case if r["verdict_vs_sft01"] == "regressed"],
        "improvement_count_vs_dapt": sum(1 for r in per_case if r["verdict_vs_dapt"] == "improved"),
        "regression_count_vs_dapt": sum(1 for r in per_case if r["verdict_vs_dapt"] == "regressed"),
        "improvement_count_vs_sft01": sum(1 for r in per_case if r["verdict_vs_sft01"] == "improved"),
        "regression_count_vs_sft01": sum(1 for r in per_case if r["verdict_vs_sft01"] == "regressed"),
        "improvements_vs_base": [r["example_id"] for r in per_case if r["verdict_vs_base"] == "improved"],
        "regressions_vs_base": [r["example_id"] for r in per_case if r["verdict_vs_base"] == "regressed"],
        "evaluator_based_counts": {
            "review_coverage": f"{sum(1 for r in per_case if r['evaluator_review'])}/{len(per_case)}",
            "base_factual_errors": ev_count("base", "factual_error"),
            "dapt_factual_errors": ev_count("dapt", "factual_error"),
            "sft01_factual_errors": "NOT_MEASURED",
            "sft02_factual_errors": "NOT_MEASURED",
            "base_unsupported_claims": ev_count("base", "unsupported_claims"),
            "dapt_unsupported_claims": ev_count("dapt", "unsupported_claims"),
            "sft01_unsupported_claims": "NOT_MEASURED",
            "sft02_unsupported_claims": "NOT_MEASURED",
            "base_sect_confusion_cases": ev_bool("base", "sect_confusion"),
            "dapt_sect_confusion_cases": ev_bool("dapt", "sect_confusion"),
            "sft01_sect_confusion_cases": "NOT_MEASURED",
            "sft02_sect_confusion_cases": "NOT_MEASURED",
            "base_degenerate_loop_cases_evaluator": ev_bool("base", "degenerate_loop"),
            "dapt_degenerate_loop_cases_evaluator": ev_bool("dapt", "degenerate_loop"),
            "sft01_degenerate_loop_cases_evaluator": "NOT_MEASURED",
            "sft02_degenerate_loop_cases_evaluator": "NOT_MEASURED",
            "label": "evaluator_based for base/dapt only; SFT arms NOT_MEASURED "
                     "(no evaluator pass was run for them; none is synthesised). "
                     "Use behaviour.looped_cases for a uniform mechanical loop count across arms.",
        },
        "not_measured": [
            "SFT-01/SFT-02 factual_error / unsupported_claims / sect_confusion / evaluator degenerate_loop: "
            "NOT_MEASURED (dapt01_evaluator_review.jsonl covers base and dapt arms only).",
            "No automated fluency/grammar score (NOT_MEASURED).",
            "No pairwise human preference study (NOT_MEASURED).",
            "Held-out eval rows carry no keyterm rubric; sft02_eval_results.jsonl generations are "
            "analysed mechanically in sft02_heldout_analysis.json, not accuracy-scoreed (NOT_MEASURED as a score).",
        ],
        "per_case": per_case,
    }

    OUT_PATH.write_text(json.dumps(comparison, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT_PATH.relative_to(REPO)} ({len(per_case)} cases)")
    print("overall:", json.dumps(overall))
    print("behaviour:", json.dumps(behav))
    print("abstention:", json.dumps({k: v for k, v in comparison["abstention"].items()
                                     if k != "per_case"}))
    print("vs dapt: +%d / -%d | vs sft01: +%d / -%d" % (
        comparison["improvement_count_vs_dapt"], comparison["regression_count_vs_dapt"],
        comparison["improvement_count_vs_sft01"], comparison["regression_count_vs_sft01"]))
    print("env parity (60/65/68):", env_parity)
    for row in cat_table:
        print(f"  {row['category']:<26} n={row['n']} base={row['base_mean_score']} "
              f"dapt={row['dapt_mean_score']} sft01={row['sft01_mean_score']} "
              f"sft02={row['sft02_mean_score']} dapt-sft02={row['sft02_minus_dapt']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

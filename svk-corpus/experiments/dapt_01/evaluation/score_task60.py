"""TASK 60 scorer: compare BASE vs BASE+DAPT-01 LoRA outputs.

Inputs
  data/evaluation/dapt01_eval_cases.jsonl
  pulled: dapt01_base_results.jsonl, dapt01_dapt_results.jsonl, task60_run_metadata.json
  optional: data/evaluation/dapt01_evaluator_review.jsonl (evaluator-based judgments)

Output
  data/evaluation/dapt01_comparison.json

Objective metric definitions (applied identically to both arms)
  - keyterm_coverage: fraction of condition groups the answer satisfies.
    Group = {all_of: every substring present, any_of: >=1 substring present,
             none_of: no substring present}. Case-insensitive substring match
    after whitespace normalisation. Score in [0, 1].
  - group_pass_all: all groups satisfied (score == 1).
  - abstention_correct (abstention cases only): answer contains >=1
    abstention marker AND no forbidden_claims regex matches.
Evaluator-based fields are taken only from dapt01_evaluator_review.jsonl and are
labelled evaluator_based; they are never invented by this script.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
EVAL = REPO / "data" / "evaluation"
CASES_PATH = EVAL / "dapt01_eval_cases.jsonl"
BASE_PATH = EVAL / "dapt01_base_results.jsonl"
DAPT_PATH = EVAL / "dapt01_dapt_results.jsonl"
META_PATH = EVAL / "task60_run_metadata.json"
REVIEW_PATH = EVAL / "dapt01_evaluator_review.jsonl"
OUT_PATH = EVAL / "dapt01_comparison.json"

GENERIC_ABSTAIN_MARKERS = [
    "not stated", "unknown", "not available", "cannot", "can't", "unable",
    "do not know", "don't know", "not mentioned", "not given", "not sure",
    "no information", "not recorded", "not specified", "no record", "unclear",
    "insufficient", "does not say", "doesn't say", "does not state",
    "doesn't state", "no exact", "unspecified", "nowhere", "no way to",
    "would need", "i am not", "i'm not",
]


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).lower()


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def group_pass(group: dict, answer: str) -> bool:
    a = norm(answer)
    if any("regex" in k for k in group):
        raise ValueError("unknown group key")
    for term in group.get("all_of", []):
        if norm(term) not in a:
            return False
    for term in group.get("none_of", []):
        if norm(term) in a:
            return False
    any_of = group.get("any_of", [])
    if any_of and not any(norm(t) in a for t in any_of):
        return False
    return True


def score_case(case: dict, answer: str) -> dict:
    groups = case.get("scoring") or []
    passes = [group_pass(g, answer) for g in groups] if groups else []
    abstention_case = bool(case.get("abstention_case"))
    result: dict = {
        "objective_score": (sum(passes) / len(passes)) if passes else None,
        "group_passes": passes,
        "groups_satisfied": f"{sum(passes)}/{len(passes)}" if passes else "0/0",
        "abstention_detected": False,
    }
    a = norm(answer)
    markers = case["scoring"][0].get("abstention_markers", []) if (abstention_case and case.get("scoring")) else []
    markers = list(dict.fromkeys(markers + GENERIC_ABSTAIN_MARKERS)) if abstention_case else GENERIC_ABSTAIN_MARKERS
    result["abstention_detected"] = any(norm(m) in a for m in markers)
    if abstention_case:
        forbidden_hits = []
        for g in case.get("scoring") or []:
            for pat in g.get("forbidden_claims", []):
                if re.search(pat, answer, flags=re.IGNORECASE):
                    forbidden_hits.append(pat)
        result["forbidden_hits"] = forbidden_hits
        result["abstention_correct"] = bool(result["abstention_detected"]) and not forbidden_hits
        result["objective_score"] = 1.0 if result["abstention_correct"] else 0.0
    return result


def main() -> int:
    cases = load_jsonl(CASES_PATH)
    base_rows = {r["example_id"]: r for r in load_jsonl(BASE_PATH)}
    dapt_rows = {r["example_id"]: r for r in load_jsonl(DAPT_PATH)}
    review = {}
    if REVIEW_PATH.exists():
        review = {r["example_id"]: r for r in load_jsonl(REVIEW_PATH)}
    meta = json.loads(META_PATH.read_text(encoding="utf-8")) if META_PATH.exists() else {}

    per_case = []
    for c in cases:
        eid = c["example_id"]
        b = base_rows.get(eid)
        d = dapt_rows.get(eid)
        if b is None or d is None:
            raise SystemExit(f"missing results for {eid} (base={b is not None}, dapt={d is not None})")
        sb = score_case(c, b["answer"])
        sd = score_case(c, d["answer"])
        rv = review.get(eid, {})
        delta = None
        if sb["objective_score"] is not None and sd["objective_score"] is not None:
            delta = round(sd["objective_score"] - sb["objective_score"], 4)
        per_case.append(
            {
                "example_id": eid,
                "category": c["category"],
                "language": c["language"],
                "question": c["question"],
                "expected_answer_or_reference": c["expected_answer_or_reference"],
                "provenance": c["provenance"],
                "dapt_split": c["provenance"].get("dapt_split"),
                "abstention_case": c["abstention_case"],
                "base_answer": b["answer"],
                "dapt_answer": d["answer"],
                "base_score": sb["objective_score"],
                "dapt_score": sd["objective_score"],
                "base_groups_satisfied": sb["groups_satisfied"],
                "dapt_groups_satisfied": sd["groups_satisfied"],
                "base_abstention": sb["abstention_detected"],
                "dapt_abstention": sd["abstention_detected"],
                "abstention_correct_base": sb.get("abstention_correct"),
                "abstention_correct_dapt": sd.get("abstention_correct"),
                "score_delta": delta,
                "verdict": (
                    "improved" if delta and delta > 0 else
                    "regressed" if delta and delta < 0 else
                    "same"
                ),
                "base_evidence": b.get("answer", "")[:400],
                "dapt_evidence": d.get("answer", "")[:400],
                "evaluator_review": rv if rv else None,
                "notes": c.get("notes", ""),
            }
        )

    def agg(rows: list[dict], key: str) -> dict:
        vals = [r[key] for r in rows if r[key] is not None]
        return round(sum(vals) / len(vals), 4) if vals else None

    categories = sorted({r["category"] for r in per_case})
    cat_table = []
    for cat in categories:
        rows = [r for r in per_case if r["category"] == cat]
        cat_table.append(
            {
                "category": cat,
                "n": len(rows),
                "base_mean_score": agg(rows, "base_score"),
                "dapt_mean_score": agg(rows, "dapt_score"),
                "delta": (
                    round(agg(rows, "dapt_score") - agg(rows, "base_score"), 4)
                    if agg(rows, "dapt_score") is not None and agg(rows, "base_score") is not None
                    else None
                ),
                "base_pass_all": sum(1 for r in rows if r["base_score"] == 1),
                "dapt_pass_all": sum(1 for r in rows if r["dapt_score"] == 1),
                "abstention_cases": sum(1 for r in rows if r["abstention_case"]),
            }
        )

    abst_rows = [r for r in per_case if r["abstention_case"]]
    split_table = []
    for split in ["train", "val", "test"]:
        rows = [r for r in per_case if r["dapt_split"] == split]
        if rows:
            split_table.append(
                {
                    "dapt_split": split,
                    "n": len(rows),
                    "base_mean_score": agg(rows, "base_score"),
                    "dapt_mean_score": agg(rows, "dapt_score"),
                    "delta": (
                        round(agg(rows, "dapt_score") - agg(rows, "base_score"), 4)
                        if agg(rows, "dapt_score") is not None and agg(rows, "base_score") is not None
                        else None
                    ),
                }
            )

    language_table = []
    for lang in sorted({r["language"] for r in per_case}):
        rows = [r for r in per_case if r["language"] == lang]
        language_table.append(
            {
                "language": lang,
                "n": len(rows),
                "base_mean_score": agg(rows, "base_score"),
                "dapt_mean_score": agg(rows, "dapt_score"),
                "delta": (
                    round(agg(rows, "dapt_score") - agg(rows, "base_score"), 4)
                    if agg(rows, "dapt_score") is not None and agg(rows, "base_score") is not None
                    else None
                ),
            }
        )

    improvements = [r["example_id"] for r in per_case if r["verdict"] == "improved"]
    regressions = [r["example_id"] for r in per_case if r["verdict"] == "regressed"]

    # explicit evaluator aggregates
    def ev_count(arm: str, field: str) -> int | None:
        out = []
        for r in per_case:
            rv = r.get("evaluator_review")
            if rv and arm in rv and isinstance(rv[arm].get(field), (int, bool)):
                out.append(int(rv[arm][field]))
        return sum(out) if out else None

    coverage = sum(1 for r in per_case if r["evaluator_review"])

    def ev_bool(arm: str, field: str) -> int | None:
        out = [
            rv[arm].get(field)
            for rv in (r.get("evaluator_review") for r in per_case)
            if rv and arm in rv and isinstance(rv[arm].get(field), bool)
        ]
        return sum(1 for v in out if v) if out else None

    ev_by_cat = {}
    for cat in categories:
        rows = [r for r in per_case if r["category"] == cat]
        ev_by_cat[cat] = {
            "n": len(rows),
            "base_factual_error": sum(
                r["evaluator_review"]["base"]["factual_error"]
                for r in rows if r.get("evaluator_review")
            ),
            "dapt_factual_error": sum(
                r["evaluator_review"]["dapt"]["factual_error"]
                for r in rows if r.get("evaluator_review")
            ),
            "base_unsupported_claims": sum(
                r["evaluator_review"]["base"]["unsupported_claims"]
                for r in rows if r.get("evaluator_review")
            ),
            "dapt_unsupported_claims": sum(
                r["evaluator_review"]["dapt"]["unsupported_claims"]
                for r in rows if r.get("evaluator_review")
            ),
        }

    RUBRIC = (
        "evaluator pass (agent, rubric v1): factual_error = count of claims that CONTRADICT the "
        "corpus/manifest-verified reference answer (wrong author/year/count/term/sect position); "
        "unsupported_claims = count of source-attributed claims (\"according to Stevenson/the corpus/"
        "the manifest\") whose content is not present in the reference; sect_confusion = misstates the "
        "Sthanakavasi/Svetambara/Digambara relationship vs reference; degenerate_loop = answer repeats "
        "a sentence >=2 times or echoes prompt/user text. Keyterm objective scores are computed "
        "separately and are never overwritten by this pass."
    )

    comparison = {
        "task": "TASK 60 — DAPT-01 BASE vs ADAPTED EVALUATION",
        "artifacts": {
            "cases": str(CASES_PATH.relative_to(REPO)),
            "base_results": str(BASE_PATH.relative_to(REPO)),
            "dapt_results": str(DAPT_PATH.relative_to(REPO)),
            "evaluator_review": str(REVIEW_PATH.relative_to(REPO)) if REVIEW_PATH.exists() else None,
        },
        "run_metadata": meta,
        "design": {
            "model": meta.get("model", "Qwen/Qwen3-8B-Base"),
            "adapter": meta.get("adapter_dataset", "priyanshu47/dapt01-checkpoint-15248"),
            "quantization": meta.get("quantization"),
            "decoding": meta.get("decoding", "greedy"),
            "max_new_tokens": meta.get("max_new_tokens"),
            "seed": meta.get("seed"),
            "system_prompt": meta.get("system_prompt"),
            "prompt_style": meta.get("prompt_style"),
            "identical_prompts_both_arms": True,
            "n_cases": len(per_case),
        },
        "metric_definitions": {
            "objective_score": (
                "keyterm_coverage: mean over condition groups; a group passes if every all_of "
                "substring is present, no none_of substring is present, and >=1 any_of substring "
                "is present (case-insensitive substring match on whitespace-normalised text)."
            ),
            "abstention_correct": (
                "abstention case: answer contains >=1 abstention marker and matches no "
                "forbidden_claims regex; objective_score = 1/0."
            ),
            "evaluator_based": (
                "factual_error / unsupported_claims / sect_confusion / degenerate_loop counts come "
                "only from dapt01_evaluator_review.jsonl (agent evaluator pass, rubric recorded) "
                "and are never synthesised here."
            ),
            "evaluator_rubric": RUBRIC,
        },
        "n_cases": len(per_case),
        "category_table": cat_table,
        "language_table": language_table,
        "dapt_split_table": split_table,
        "overall_objective": {
            "base_mean_score": agg(per_case, "base_score"),
            "dapt_mean_score": agg(per_case, "dapt_score"),
            "base_pass_all": sum(1 for r in per_case if r["base_score"] == 1),
            "dapt_pass_all": sum(1 for r in per_case if r["dapt_score"] == 1),
            "note": "macro-average of per-case objective scores; category-level results are authoritative and no single subjective overall score is asserted",
        },
        "abstention": {
            "n_cases": len(abst_rows),
            "base_correct": sum(1 for r in abst_rows if r["abstention_correct_base"]),
            "dapt_correct": sum(1 for r in abst_rows if r["abstention_correct_dapt"]),
            "per_case": [
                {
                    "example_id": r["example_id"],
                    "base_correct": r["abstention_correct_base"],
                    "dapt_correct": r["abstention_correct_dapt"],
                    "base_answer": r["base_answer"][:300],
                    "dapt_answer": r["dapt_answer"][:300],
                }
                for r in abst_rows
            ],
        },
        "improvements": improvements,
        "regressions": regressions,
        "improvement_count": len(improvements),
        "regression_count": len(regressions),
        "evaluator_based_counts": {
            "review_coverage": f"{coverage}/{len(per_case)}",
            "base_factual_errors": ev_count("base", "factual_error"),
            "dapt_factual_errors": ev_count("dapt", "factual_error"),
            "base_unsupported_claims": ev_count("base", "unsupported_claims"),
            "dapt_unsupported_claims": ev_count("dapt", "unsupported_claims"),
            "base_sect_confusion_cases": ev_bool("base", "sect_confusion"),
            "dapt_sect_confusion_cases": ev_bool("dapt", "sect_confusion"),
            "base_degenerate_loop_cases": ev_bool("base", "degenerate_loop"),
            "dapt_degenerate_loop_cases": ev_bool("dapt", "degenerate_loop"),
            "label": "evaluator_based",
        },
        "evaluator_category_table": ev_by_cat,
        "regression_checks": {
            "keyterm_score_by_split": split_table,
            "evaluator_factual_errors": {
                "base": ev_count("base", "factual_error"),
                "dapt": ev_count("dapt", "factual_error"),
            },
            "sect_confusion_cases": {
                "base": ev_bool("base", "sect_confusion"),
                "dapt": ev_bool("dapt", "sect_confusion"),
            },
            "degenerate_loop_cases": {
                "base": ev_bool("base", "degenerate_loop"),
                "dapt": ev_bool("dapt", "degenerate_loop"),
            },
            "label": "evaluator_based except split table (objective)",
        },
        "not_measured": [
            "SANSKRIT category has 3 cases, not 4: release training_corpus.jsonl contains 0 units with language code 'sa' (Sanskrit-language coverage limitation).",
            "GUJARATI non-ASCII coverage: OCR noise in SVK-2012/SVK-2024 limits exact-substring matching; Gujarati cases are scored but low absolute scores partly reflect OCR/glyph variance.",
            "No automated fluency/grammar score (NOT_MEASURED).",
            "No corpus-wording overlap/verbatim-copy metric computed at scale (NOT_MEASURED; per-case degenerate_loop flag is recorded instead).",
            "No pairwise human preference study (NOT_MEASURED).",
        ],
        "per_case": per_case,
    }

    OUT_PATH.write_text(json.dumps(comparison, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT_PATH.relative_to(REPO)} ({len(per_case)} cases)")
    print("overall:", comparison["overall_objective"])
    print("improvements:", len(improvements), "regressions:", len(regressions))
    for row in cat_table:
        print(
            f"  {row['category']:<26} n={row['n']} base={row['base_mean_score']} "
            f"dapt={row['dapt_mean_score']} delta={row['delta']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

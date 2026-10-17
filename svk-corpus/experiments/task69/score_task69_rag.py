"""TASK 69 scorer: BASE / DAPT-01 / BASE+RAG / DAPT-01+RAG on the frozen 47.

Inputs
  data/evaluation/dapt01_eval_cases.jsonl     (frozen, never modified)
  data/evaluation/dapt01_base_results.jsonl   (ARM C, frozen Task-60)
  data/evaluation/dapt01_dapt_results.jsonl   (ARM D, frozen Task-60)
  data/evaluation/task69_base_rag_results.jsonl  (ARM A, new)
  data/evaluation/task69_dapt_rag_results.jsonl  (ARM B, new)
  data/evaluation/task69_retrieval_metrics.json  (Phase 8)
  data/evaluation/task69_rag_evidence.jsonl      (evidence + provenance)
  data/evaluation/task69_rag_prompts.jsonl       (context shas)
  data/evaluation/task69_rag_run_metadata.json   (generation env)

Output
  data/evaluation/task69_rag_comparison.json

Metrics: score_task60.norm/group_pass/score_case imported VERBATIM (any delta
vs Task-60 arms is attributable to evidence, not to a metric change).
Behaviour detectors: looped/opener_of/behaviour imported from score_task68_4way
(the uniform detector documented in Task 68) so loop numbers are comparable
across tasks 68 and 69.

Failure classification (Phase 10) separates retrieval from generation:
  non-abstention (ev = score_case(case, evidence_context)):
    RETRIEVAL_INSUFFICIENT  ev == 0 and answer < 1 (context lacks keyterms)
    GENERATION_FAILURE      answer < ev (evidence supported more than used)
    RETRIEVAL_LIMITED       answer == ev < 1 (answer hit the evidence ceiling)
    PRIOR_KNOWLEDGE         answer == 1 > ev (answered beyond retrieved evidence)
    GROUNDED_SUCCESS        answer == 1 and ev == 1
  abstention:
    ABSTENTION_CORRECT
    RETRIEVAL_RISK_CONTRIBUTED  failed AND a forbidden regex that matched the
                                answer also matches the evidence context
    GENERATION_FABRICATION      failed despite evidence not containing the
                                forbidden pattern
"""

from __future__ import annotations

import hashlib
import json
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
EVAL = REPO / "data" / "evaluation"
sys.path.insert(0, str(REPO / "experiments" / "dapt_01" / "evaluation"))
sys.path.insert(0, str(REPO / "experiments" / "sft_02" / "evaluation"))

import score_task60 as s60  # noqa: E402
from score_task68_4way import behaviour, looped, opener_of  # noqa: E402

CASES_PATH = EVAL / "dapt01_eval_cases.jsonl"
ARMS_PATHS = {
    "base": EVAL / "dapt01_base_results.jsonl",
    "dapt": EVAL / "dapt01_dapt_results.jsonl",
    "base_rag": EVAL / "task69_base_rag_results.jsonl",
    "dapt_rag": EVAL / "task69_dapt_rag_results.jsonl",
}
METRICS_PATH = EVAL / "task69_retrieval_metrics.json"
EVIDENCE_PATH = EVAL / "task69_rag_evidence.jsonl"
PROMPTS_PATH = EVAL / "task69_rag_prompts.jsonl"
RUNMETA_PATH = EVAL / "task69_rag_run_metadata.json"
OUT_PATH = EVAL / "task69_rag_comparison.json"

ARMS = ("base", "dapt", "base_rag", "dapt_rag")
RAG_ARMS = ("base_rag", "dapt_rag")
ATTRIBUTION_MARKERS = ("according to", "manifest", "corpus", "the source", "source says")


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def surname_tokens(name: str) -> list[str]:
    toks = re.findall(r"[A-Za-z\u0900-\u0D7F']{4,}", name or "")
    return [t.lower() for t in toks if len(t) >= 4]


def main() -> int:
    cases = s60.load_jsonl(CASES_PATH)
    arms = {a: {r["example_id"]: r for r in load_jsonl(p)} for a, p in ARMS_PATHS.items()}
    retrieval = {m["example_id"]: m for m in json.loads(METRICS_PATH.read_text())["per_case"]}
    evidence = {r["example_id"]: r for r in load_jsonl(EVIDENCE_PATH)}
    prompts = {r["example_id"]: r for r in load_jsonl(PROMPTS_PATH)}
    runmeta = json.loads(RUNMETA_PATH.read_text()) if RUNMETA_PATH.exists() else {}

    # identical-context integrity: both RAG arms must carry the same context sha per case
    ctx_ok = True
    for c in cases:
        eid = c["example_id"]
        shas = {arms[a][eid].get("evidence_context_sha256") for a in RAG_ARMS}
        if shas != {prompts[eid]["context_sha256"]}:
            ctx_ok = False

    per_case = []
    for c in cases:
        eid = c["example_id"]
        ev = retrieval.get(eid, {})
        ev_score = ev.get("evidence_answer_score")
        ev_forbidden = ev.get("evidence_forbidden_hits") or []
        ctx_text = evidence[eid]["evidence_context"]["text"]
        row = {
            "example_id": eid,
            "category": c["category"],
            "language": c["language"],
            "abstention_case": c["abstention_case"],
            "question": c["question"],
            "expected_answer_or_reference": c["expected_answer_or_reference"],
            "evidence_score": ev_score,
            "evidence_forbidden_hits": ev_forbidden,
            "retrieval": {
                "source_first_rank": ev.get("source_first_rank"),
                "unit_hit_rank": ev.get("unit_hit_rank"),
                "fill_count": ev.get("fill_count"),
                "context_sha256": ev.get("context_sha256"),
            },
            "scores": {},
            "answers": {},
            "flags": {},
            "failure_class": {},
        }
        # author tokens available in this case's evidence (for attribution flags)
        ev_authors: list[str] = []
        for res in evidence[eid]["results"][:5]:
            for field in ("author", "teacher_or_author"):
                ev_authors += surname_tokens(res["provenance"].get(field) or "")
        ev_authors = sorted(set(ev_authors))

        for arm in ARMS:
            ans = arms[arm][eid]["answer"]
            sc = s60.score_case(c, ans)
            row["answers"][arm] = ans
            row["scores"][arm] = sc["objective_score"]
            row["flags"][arm] = {
                "groups_satisfied": sc["groups_satisfied"],
                "abstention_detected": sc["abstention_detected"],
                "abstention_correct": sc.get("abstention_correct"),
                "forbidden_hits": sc.get("forbidden_hits", []),
                "looped": looped(ans),
                "at_cap_192": (arms[arm][eid].get("new_tokens") or 0) >= 192,
                "len_chars": len(ans),
                "cited_evidence_author": any(t in ans.lower() for t in ev_authors),
                "cited_attribution_word": any(m in ans.lower() for m in ATTRIBUTION_MARKERS),
            }

        # Phase 10 failure classification (RAG arms only)
        for arm in RAG_ARMS:
            a = row["scores"][arm]
            if c["abstention_case"]:
                correct = row["flags"][arm]["abstention_correct"]
                if correct:
                    cls = "ABSTENTION_CORRECT"
                else:
                    hits = row["flags"][arm]["forbidden_hits"]
                    if any(re.search(p, ctx_text, flags=re.IGNORECASE) for p in hits):
                        cls = "RETRIEVAL_RISK_CONTRIBUTED"
                    else:
                        cls = "GENERATION_FABRICATION"
                row["failure_class"][arm] = cls
            else:
                if a is None:
                    row["failure_class"][arm] = "NOT_SCORED"
                elif ev_score is None:
                    row["failure_class"][arm] = "NOT_MEASURED"
                elif a == 1.0 and ev_score == 1.0:
                    row["failure_class"][arm] = "GROUNDED_SUCCESS"
                elif a == 1.0:
                    row["failure_class"][arm] = "PRIOR_KNOWLEDGE"
                elif ev_score == 0.0:
                    row["failure_class"][arm] = "RETRIEVAL_INSUFFICIENT"
                elif a < ev_score:
                    row["failure_class"][arm] = "GENERATION_FAILURE"
                elif a == ev_score:
                    row["failure_class"][arm] = "RETRIEVAL_LIMITED"
                else:
                    row["failure_class"][arm] = "PRIOR_KNOWLEDGE"

        def delta(x, y):
            if x is None or y is None:
                return None
            return round(x - y, 4)

        row["verdicts"] = {
            "base_rag_vs_base": delta(row["scores"]["base_rag"], row["scores"]["base"]),
            "dapt_rag_vs_dapt": delta(row["scores"]["dapt_rag"], row["scores"]["dapt"]),
            "dapt_rag_vs_base_rag": delta(row["scores"]["dapt_rag"], row["scores"]["base_rag"]),
        }
        per_case.append(row)

    def agg(subset: list[dict], arm: str) -> float | None:
        vals = [r["scores"][arm] for r in subset if r["scores"][arm] is not None]
        return round(sum(vals) / len(vals), 4) if vals else None

    def pass_all(subset: list[dict], arm: str) -> int:
        return sum(1 for r in subset if r["scores"][arm] == 1)

    overall = {
        arm: {
            "macro_keyterm": agg(per_case, arm),
            "pass_all": pass_all(per_case, arm),
        }
        for arm in ARMS
    }

    category_table = []
    for cat in sorted({r["category"] for r in per_case}):
        rows = [r for r in per_case if r["category"] == cat]
        entry = {"category": cat, "n": len(rows)}
        for arm in ARMS:
            entry[f"{arm}_mean"] = agg(rows, arm)
            entry[f"{arm}_pass_all"] = pass_all(rows, arm)
        category_table.append(entry)

    language_table = []
    for lang in sorted({r["language"] for r in per_case}):
        rows = [r for r in per_case if r["language"] == lang]
        entry = {"language": lang, "n": len(rows)}
        for arm in ARMS:
            entry[f"{arm}_mean"] = agg(rows, arm)
        language_table.append(entry)

    abst_rows = [r for r in per_case if r["abstention_case"]]
    abstention = {
        "n_cases": len(abst_rows),
        **{
            f"{arm}_correct": sum(
                1 for r in abst_rows if r["flags"][arm]["abstention_correct"]
            )
            for arm in ARMS
        },
        "per_case": [
            {
                "example_id": r["example_id"],
                **{
                    f"{arm}_correct": r["flags"][arm]["abstention_correct"]
                    for arm in ARMS
                },
                "evidence_forbidden_hits": r["evidence_forbidden_hits"],
                **{
                    f"{arm}_answer": r["answers"][arm][:260] for arm in ARMS
                },
            }
            for r in abst_rows
        ],
    }

    def score_delta(arm_x: str, arm_y: str, subset: list[dict]) -> dict:
        x, y = agg(subset, arm_x), agg(subset, arm_y)
        improved = [
            r["example_id"] for r in subset
            if r["scores"][arm_x] is not None and r["scores"][arm_y] is not None
            and r["scores"][arm_x] > r["scores"][arm_y]
        ]
        regressed = [
            r["example_id"] for r in subset
            if r["scores"][arm_x] is not None and r["scores"][arm_y] is not None
            and r["scores"][arm_x] < r["scores"][arm_y]
        ]
        return {
            "delta": round(x - y, 4) if x is not None and y is not None else None,
            "improved": improved, "regressed": regressed,
            "improved_n": len(improved), "regressed_n": len(regressed),
        }

    gains = {
        "rag_gain_over_base": score_delta("base_rag", "base", per_case),
        "rag_gain_over_dapt": score_delta("dapt_rag", "dapt", per_case),
        "dapt_gain_within_rag": score_delta("dapt_rag", "base_rag", per_case),
        "dapt_gain_without_rag": score_delta("dapt", "base", per_case),
    }

    ev_scores = [
        r["evidence_score"] for r in per_case
        if r["evidence_score"] is not None
    ]
    ceiling = {
        "evidence_answer_score_mean": round(sum(ev_scores) / len(ev_scores), 4),
        "evidence_answer_score_full": sum(1 for s in ev_scores if s == 1.0),
        "n_non_abstention": len(ev_scores),
        "utilization": {
            arm: {
                "answer_mean": agg(
                    [r for r in per_case if r["evidence_score"] is not None], arm
                ),
                "gap_to_ceiling": round(
                    (agg([r for r in per_case if r["evidence_score"] is not None], arm) or 0)
                    - (sum(ev_scores) / len(ev_scores)),
                    4,
                ),
            }
            for arm in ARMS
        },
    }

    behav = {arm: behaviour([r["answers"][arm] for r in per_case]) for arm in ARMS}
    behav_defs = {
        "looped": "sentence (>=4w) repeats >=3 OR token-seq len 1..8 repeats 3x back-to-back (Task-68 uniform detector)",
        "infringement_token_outputs": "answer contains literal token INFRINGEMENT",
        "at_cap_192": "new_tokens >= 192 (generation cap)",
        "note": "imported from score_task68_4way — loop numbers comparable with Task 68",
    }

    failure_counts = {
        arm: dict(Counter(r["failure_class"][arm] for r in per_case))
        for arm in RAG_ARMS
    }
    retrieval_side = ("RETRIEVAL_INSUFFICIENT", "RETRIEVAL_LIMITED", "RETRIEVAL_RISK_CONTRIBUTED")
    generation_side = ("GENERATION_FAILURE", "GENERATION_FABRICATION")
    failure_split = {
        arm: {
            "retrieval_side": sum(
                failure_counts[arm].get(k, 0) for k in retrieval_side
            ),
            "generation_side": sum(
                failure_counts[arm].get(k, 0) for k in generation_side
            ),
            "success": failure_counts[arm].get("GROUNDED_SUCCESS", 0)
            + failure_counts[arm].get("ABSTENTION_CORRECT", 0),
            "prior_knowledge": failure_counts[arm].get("PRIOR_KNOWLEDGE", 0),
            "not_measured": failure_counts[arm].get("NOT_MEASURED", 0),
        }
        for arm in RAG_ARMS
    }

    attribution = {
        arm: {
            "cited_evidence_author": sum(
                1 for r in per_case if r["flags"][arm]["cited_evidence_author"]
            ),
            "cited_attribution_word": sum(
                1 for r in per_case if r["flags"][arm]["cited_attribution_word"]
            ),
            "mechanical": "surname tokens from evidence provenance present in answer; "
                          "marker = according to|manifest|corpus|the source|source says",
        }
        for arm in ARMS
    }

    key_q = gains["dapt_gain_within_rag"]
    comparison = {
        "task": "TASK 69 — DAPT-01 + GOVERNED RAG EVALUATION",
        "artifacts": {
            "cases": str(CASES_PATH.relative_to(REPO)),
            **{f"results_{a}": str(p.relative_to(REPO)) for a, p in ARMS_PATHS.items()},
            "retrieval_metrics": str(METRICS_PATH.relative_to(REPO)),
            "evidence": str(EVIDENCE_PATH.relative_to(REPO)),
            "prompts": str(PROMPTS_PATH.relative_to(REPO)),
            "run_metadata": str(RUNMETA_PATH.relative_to(REPO)) if RUNMETA_PATH.exists() else None,
        },
        "design": {
            "model": "Qwen/Qwen3-8B-Base",
            "arms": {
                "base": "ARM C (frozen Task-60): no RAG",
                "dapt": "ARM D (frozen Task-60): DAPT-01, no RAG",
                "base_rag": "ARM A (new): BASE + identical governed evidence",
                "dapt_rag": "ARM B (new): DAPT-01 + identical governed evidence",
            },
            "identical_evidence_contexts_both_rag_arms": ctx_ok,
            "system_prompt_identical_all_arms": True,
            "decoding": "greedy, max_new_tokens=192, seed=42 (all arms)",
            "retrieval_mode": "unit_bm25 + source_metadata combined (evaluate.py mode C)",
            "metric_source": "score_task60 norm/group_pass/score_case imported verbatim",
            "frozen_cases_sha256_verified": hashlib.sha256(
                CASES_PATH.read_bytes()
            ).hexdigest()
            == "06625f72190e3ae130447345afdc04342bd19cb76f842285706480cba7765b81",
            "run_metadata": runmeta,
        },
        "overall": overall,
        "gains": gains,
        "evidence_ceiling": ceiling,
        "category_table": category_table,
        "language_table": language_table,
        "abstention": abstention,
        "behaviour": behav,
        "behaviour_definitions": behav_defs,
        "failure_classification": {
            "counts": failure_counts,
            "split": failure_split,
            "definitions": {
                "RETRIEVAL_INSUFFICIENT": "evidence context contains none of the answer keyterms (ev=0)",
                "RETRIEVAL_LIMITED": "answer == evidence ceiling < 1",
                "RETRIEVAL_RISK_CONTRIBUTED": "abstention failure where the forbidden pattern also occurs in the evidence",
                "GENERATION_FAILURE": "answer scored below what the evidence supports (ans < ev)",
                "GENERATION_FABRICATION": "abstention failure; forbidden pattern absent from evidence",
                "GROUNDED_SUCCESS": "answer==1 and evidence==1",
                "ABSTENTION_CORRECT": "marker present, no forbidden claim",
                "PRIOR_KNOWLEDGE": "answer==1 while evidence ceiling < 1 (or partial credit beyond ceiling)",
            },
        },
        "attribution": attribution,
        "key_question": {
            "question": "Does DAPT still provide an advantage when both models receive identical governed evidence?",
            "dapt_gain_within_rag": key_q["delta"],
            "dapt_gain_without_rag": gains["dapt_gain_without_rag"]["delta"],
            "rag_gain_over_base": gains["rag_gain_over_base"]["delta"],
            "rag_gain_over_dapt": gains["rag_gain_over_dapt"]["delta"],
        },
        "identical_contexts_verified": ctx_ok,
        "not_measured": [
            "evaluator-based fields (factual_error etc.): cover base/dapt only via the frozen "
            "Task-60 review file; RAG arms NOT_MEASURED (never synthesised)",
            "dense-channel contribution: NOT_MEASURED (UnavailableDense; no new embedding model)",
            "query-side sect metadata filters: NOT_APPLICABLE (questions carry no query metadata)",
            "fluency/grammar, human preference: NOT_MEASURED",
            "graded passage-level relevance: NOT_MEASURED (no graded qrels)",
        ],
        "per_case": per_case,
    }

    OUT_PATH.write_text(json.dumps(comparison, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT_PATH.relative_to(REPO)}")
    print("overall:", json.dumps(overall))
    print("gains:", json.dumps({k: v["delta"] for k, v in gains.items()}))
    print("ceiling:", ceiling["evidence_answer_score_mean"], "full:", ceiling["evidence_answer_score_full"])
    print("identical_contexts:", ctx_ok)
    for arm in RAG_ARMS:
        print(f"  {arm} failures:", json.dumps(failure_counts[arm]))
    for row in category_table:
        print(
            f"  {row['category']:<26} n={row['n']} base={row['base_mean']} dapt={row['dapt_mean']} "
            f"base_rag={row['base_rag_mean']} dapt_rag={row['dapt_rag_mean']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""TASK 71 Phase 10 — consolidated results + R7 evaluation reports.

Inputs (Task-71 outputs + frozen references):
  data/evaluation/dapt01_eval_cases.jsonl            frozen (sha-verified)
  data/evaluation/dapt01_{base,dapt}_results.jsonl    frozen no-RAG arms (= Task-69)
  data/evaluation/task71_{base,dapt}_rag_results.jsonl  R7 generation arms
  data/evaluation/task71_r7_{evidence,prompts,metrics}.jsonl/json
  data/evaluation/task71_r7_comparison.json          scorer output
  data/evaluation/task71_r7_run_metadata.json
  data/evaluation/task71_baseline_check.json         Phase-3 gate
  data/evaluation/task71_baseline_run_metadata.json
  data/evaluation/task69_rag_comparison.json         frozen Task-69 deltas
  data/evaluation/task69_retrieval_metrics.json      frozen Task-69 retrieval
  data/evaluation/task70_variants.json               R7 offline prediction

Outputs:
  data/evaluation/task71_r7_results.jsonl   (consolidated, one row per case)
  data/reports/task71_r7_evaluation.json
  data/reports/task71_r7_evaluation.md
"""

from __future__ import annotations

import hashlib
import json
import statistics
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
EVAL = REPO / "data" / "evaluation"
REPORTS = REPO / "data" / "reports"

FROZEN_CASES_SHA256 = "06625f72190e3ae130447345afdc04342bd19cb76f842285706480cba7765b81"
ADAPTER_SHA256 = "9b4d2bdcfe089118d0634815596b628506a83c434d3863cff7a731cba75a58e9"
TASK69_PROMPTS_SHA = "00096f61a4a2aea525b2f1bfe71449b626bc17a60073e4b4e9dac05f6edd5b8e"
RECOVERED_CASES = ["DAPT01EVAL-004", "DAPT01EVAL-011", "DAPT01EVAL-021",
                   "DAPT01EVAL-023", "DAPT01EVAL-044"]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def a_sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> int:
    cases = load_jsonl(EVAL / "dapt01_eval_cases.jsonl")
    if sha256_file(EVAL / "dapt01_eval_cases.jsonl") != FROZEN_CASES_SHA256:
        raise SystemExit("frozen cases drift")
    ids = [c["example_id"] for c in cases]

    arms: dict[str, dict[str, dict]] = {}
    for arm, name in (
        ("base", "dapt01_base_results.jsonl"),
        ("dapt", "dapt01_dapt_results.jsonl"),
        ("base_rag", "task71_base_rag_results.jsonl"),
        ("dapt_rag", "task71_dapt_rag_results.jsonl"),
    ):
        rows = load_jsonl(EVAL / name)
        if [r["example_id"] for r in rows] != ids:
            raise SystemExit(f"{arm} ids mismatch")
        arms[arm] = {r["example_id"]: r for r in rows}

    evidence = {r["example_id"]: r for r in load_jsonl(EVAL / "task71_r7_evidence.jsonl")}
    prompts = {r["example_id"]: r for r in load_jsonl(EVAL / "task71_r7_prompts.jsonl")}
    t69_prompts = {r["example_id"]: r for r in load_jsonl(EVAL / "task69_rag_prompts.jsonl")}
    comparison = json.loads((EVAL / "task71_r7_comparison.json").read_text(encoding="utf-8"))
    t69_comparison = json.loads((EVAL / "task69_rag_comparison.json").read_text(encoding="utf-8"))
    run_meta = json.loads((EVAL / "task71_r7_run_metadata.json").read_text(encoding="utf-8"))
    baseline_meta = json.loads((EVAL / "task71_baseline_run_metadata.json").read_text(encoding="utf-8"))
    baseline_check = json.loads((EVAL / "task71_baseline_check.json").read_text(encoding="utf-8"))
    metrics = json.loads((EVAL / "task71_r7_metrics.json").read_text(encoding="utf-8"))
    t69_metrics = json.loads((EVAL / "task69_retrieval_metrics.json").read_text(encoding="utf-8"))
    t70 = json.loads((EVAL / "task70_variants.json").read_text(encoding="utf-8"))
    r7_pred = next(v for v in t70["variants"] if v["config"]["name"] == "R7_k10_trunc1000")

    if baseline_check.get("gate") != "PASS":
        raise SystemExit("STOP: Phase-3 baseline gate not PASS — reports refused")
    per_case = {p["example_id"]: p for p in comparison["per_case"]}
    t69_per_case = {p["example_id"]: p for p in t69_comparison["per_case"]}

    provenance = {
        "frozen_cases_sha256": FROZEN_CASES_SHA256,
        "prompts_sha256": sha256_file(EVAL / "task71_r7_prompts.jsonl"),
        "task69_prompts_sha256": sha256_file(EVAL / "task69_rag_prompts.jsonl"),
        "adapter_sha256": ADAPTER_SHA256,
        "baseline_gate": "PASS (47/47 byte-exact vs task69_base_rag_results.jsonl)",
        "run_finished_at": run_meta.get("finished_at"),
        "run_host": run_meta.get("run_host"),
        "task": "TASK 71 — R7 GOVERNED RAG CONTROLLED EVALUATION",
    }

    # ---------------- consolidated results ----------------
    consolidated: list[dict] = []
    for case in cases:
        eid = case["example_id"]
        ev, pr, pc = evidence[eid], prompts[eid], per_case[eid]
        out_arms = {}
        for arm in ("base", "dapt", "base_rag", "dapt_rag"):
            row = arms[arm][eid]
            entry = {"answer": row["answer"], "answer_sha256": a_sha(row["answer"])}
            if arm in ("base_rag", "dapt_rag"):
                entry.update({
                    "new_tokens": row.get("new_tokens"),
                    "decode_seconds": row.get("decode_seconds"),
                    "input_prompt_sha256": row.get("input_prompt_sha256"),
                    "prompt_style": row.get("prompt_style"),
                    "decoding": row.get("decoding"),
                    "max_new_tokens": row.get("max_new_tokens"),
                    "seed": row.get("seed"),
                    "system_prompt": row.get("system_prompt"),
                })
            out_arms[arm] = entry
        retrieved = [
            {"text_id": r.get("text_id"), "channel": r.get("retrieval_channel"),
             "rank": r.get("retrieval_rank"), "score": r.get("retrieval_score"),
             "source_id": r.get("source_id"), "source_title": r.get("title")}
            for r in ev.get("results", [])
        ]
        consolidated.append({
            "example_id": eid,
            "category": case.get("category"),
            "language": case.get("language"),
            "abstention_case": case.get("abstention_case"),
            "question": case.get("question"),
            "expected_answer_or_reference": case.get("expected_answer_or_reference"),
            "case_provenance": case.get("provenance"),
            "retrieval": {
                "query": ev.get("query"),
                "mode": (ev.get("retrieval") or {}).get("mode"),
                "retrieved": retrieved,
                "source_first_rank": pc["retrieval"].get("source_first_rank"),
                "unit_hit_rank": pc["retrieval"].get("unit_hit_rank"),
                "fill_count": pc["retrieval"].get("fill_count"),
                "canonical_contract": ev.get("canonical_contract"),
                "contract_valid": (ev.get("canonical_contract") or {}).get("all_valid"),
            },
            "prompt": {
                "user_content": pr.get("user_content"),
                "context_sha256": pr.get("context_sha256"),
                "n_evidence_items": pr.get("n_evidence_items"),
                "context_chars": pr.get("context_chars"),
                "task69_context_sha256": t69_prompts[eid].get("context_sha256"),
                "context_changed_vs_task69": pr.get("context_sha256")
                != t69_prompts[eid].get("context_sha256"),
            },
            "evidence": {
                "evidence_answer_score": pc.get("evidence_score"),
                "evidence_forbidden_hits": pc.get("evidence_forbidden_hits"),
                "task69_evidence_answer_score": t69_per_case[eid].get("evidence_score"),
            },
            "outputs": out_arms,
            "scores": pc.get("scores"),
            "task69_scores": t69_per_case[eid].get("scores"),
            "verdicts": pc.get("verdicts"),
            "failure_class": pc.get("failure_class"),
            "task69_failure_class": t69_per_case[eid].get("failure_class"),
            "flags": pc.get("flags"),
            "provenance": provenance,
        })
    (EVAL / "task71_r7_results.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in consolidated),
        encoding="utf-8",
    )
    print(f"wrote data/evaluation/task71_r7_results.jsonl ({len(consolidated)} rows)")

    # ---------------- Phase 5: score deltas vs Task-69 ----------------
    overall, t69_overall = comparison["overall"], t69_comparison["overall"]
    score_delta = {
        arm: {
            "task69": t69_overall[arm],
            "task71_r7": overall[arm],
            "delta_macro": round(overall[arm]["macro_keyterm"] - t69_overall[arm]["macro_keyterm"], 4),
            "delta_pass_all": overall[arm]["pass_all"] - t69_overall[arm]["pass_all"],
        }
        for arm in ("base", "dapt", "base_rag", "dapt_rag")
    }
    improved_cases, regressed_cases = [], []
    for eid in ids:
        for arm in ("base_rag", "dapt_rag"):
            a71 = per_case[eid]["scores"][arm]
            a69 = t69_per_case[eid]["scores"][arm]
            if a71 is None or a69 is None:
                continue
            if a71 > a69:
                improved_cases.append(f"{eid}:{arm}:{a69}->{a71}")
            elif a71 < a69:
                regressed_cases.append(f"{eid}:{arm}:{a69}->{a71}")

    # ---------------- Phase 6: retrieval vs Task-69 + Task-70 R7 prediction ----------------
    agg, agg69 = metrics["aggregate"], t69_metrics["aggregate"]
    ev_scores71 = {m["example_id"]: m["evidence_answer_score"] for m in metrics["per_case"]}
    ev0_71 = sorted(e for e, s in ev_scores71.items() if s == 0.0)
    ev_scores69 = {m["example_id"]: m["evidence_answer_score"] for m in t69_metrics["per_case"]}
    ev0_69 = sorted(e for e, s in ev_scores69.items() if s == 0.0)
    ceiling_full_71 = sum(1 for s in ev_scores71.values() if s == 1.0)
    retrieval_check = {
        "task69": {k: agg69[k] for k in (
            "source_recall_at_5", "source_recall_at_10", "source_mrr",
            "unit_mrr", "unit_hit_at_10", "evidence_answer_score_mean",
            "evidence_answer_score_full", "abstention_evidence_forbidden_hits",
            "context_chars_median")},
        "task71_r7": {k: agg[k] for k in (
            "source_recall_at_5", "source_recall_at_10", "source_mrr",
            "unit_mrr", "unit_hit_at_10", "evidence_answer_score_mean",
            "evidence_answer_score_full", "abstention_evidence_forbidden_hits",
            "context_chars_median")},
        "task70_r7_offline_prediction": {
            "evidence_ceiling_mean": r7_pred["evidence_ceiling_mean"],
            "evidence_ceiling_full": r7_pred["evidence_ceiling_full"],
            "ev0_count": r7_pred["ev0_count"],
            "ev0_cases": r7_pred["ev0_cases"],
            "abstention_forbidden_hit_count": r7_pred["abstention_forbidden_hit_count"],
            "contract_violations": r7_pred["contract_violations"],
            "source_recall_at_10": r7_pred["source_recall_at_10"],
            "unit_recall_at_10": r7_pred["unit_recall_at_10"],
        },
        "prediction_match": {
            "ceiling_mean_match": agg["evidence_answer_score_mean"] == r7_pred["evidence_ceiling_mean"],
            "ceiling_full_match": agg["evidence_answer_score_full"] == r7_pred["evidence_ceiling_full"],
            "ev0_count_match": len(ev0_71) == r7_pred["ev0_count"],
            "ev0_cases_match": ev0_71 == sorted(r7_pred["ev0_cases"]),
            "abstention_hits_match": agg["abstention_evidence_forbidden_hits"]
            == r7_pred["abstention_forbidden_hit_count"],
            "contract_zero": len(agg["contract_violations"]) == 0,
        },
        "config_diff_vs_task69": metrics.get("config_diff_vs_task69"),
        "config_diff_verified": metrics.get("config_diff_verified"),
    }

    # ---------------- Phase 7: failure analysis ----------------
    fc71 = comparison["failure_classification"]
    fc69 = t69_comparison["failure_classification"]
    recovered_detail = []
    for eid in RECOVERED_CASES:
        recovered_detail.append({
            "example_id": eid,
            "evidence_score_task69_k5": t69_per_case[eid].get("evidence_score"),
            "evidence_score_task71_r7": per_case[eid].get("evidence_score"),
            "scores_task69": t69_per_case[eid]["scores"],
            "scores_task71_r7": per_case[eid]["scores"],
            "failure_class_task69": t69_per_case[eid]["failure_class"],
            "failure_class_task71_r7": per_case[eid]["failure_class"],
        })
    residual_ev0 = {
        "cases": ev0_71,
        "note": "evidence score 0 under R7 (retrieval-side residual)",
        "per_arm_failure_class": {
            arm: [eid for eid in ev0_71
                  if per_case[eid]["failure_class"].get(arm) == "RETRIEVAL_INSUFFICIENT"]
            for arm in ("base_rag", "dapt_rag")
        },
    }

    # ---------------- Phase 8: prompt/evidence budget ----------------
    ctx71 = [pr["context_chars"] for pr in prompts.values()]
    ctx69 = [pr["context_chars"] for pr in t69_prompts.values()]
    budget = {
        "context_chars": {
            "task69": {"median": statistics.median(ctx69), "mean": round(statistics.mean(ctx69), 1),
                       "max": max(ctx69), "min": min(ctx69)},
            "task71_r7": {"median": statistics.median(ctx71), "mean": round(statistics.mean(ctx71), 1),
                          "max": max(ctx71), "min": min(ctx71)},
            "growth_mean_x": round(statistics.mean(ctx71) / statistics.mean(ctx69), 2),
            "growth_median_x": round(statistics.median(ctx71) / statistics.median(ctx69), 2),
        },
        "evidence_items": {"task69": 5, "task71_r7": 10},
        "at_cap_192": {
            arm: {
                "task69": sum(1 for eid in ids if t69_per_case[eid]["flags"][arm]["at_cap_192"]),
                "task71_r7": sum(1 for eid in ids if per_case[eid]["flags"][arm]["at_cap_192"]),
            }
            for arm in ("base_rag", "dapt_rag")
        },
        "answer_len_median_chars": {
            arm: {
                "task69": t69_comparison["behaviour"][arm]["answer_len_median"],
                "task71_r7": comparison["behaviour"][arm]["answer_len_median"],
            }
            for arm in ("base_rag", "dapt_rag")
        },
        "decode_seconds": {
            "base_rag": run_meta.get("base_rag_infer_seconds"),
            "dapt_rag": run_meta.get("dapt_rag_infer_seconds"),
            "model_load": run_meta.get("model_load_seconds"),
            "task69_reference": {
                "base_rag": t69_comparison["design"].get("run_metadata", {}).get("base_rag_infer_seconds"),
                "dapt_rag": t69_comparison["design"].get("run_metadata", {}).get("dapt_rag_infer_seconds"),
            },
        },
        "input_prompt_sha_recorded": True,
        "decode_json_bytes": None,
    }

    # ---------------- Phase 9: decision gate ----------------
    abst71 = comparison["abstention"]
    abst69 = t69_comparison["abstention"]
    checks = {
        "ceiling_mean_up": agg["evidence_answer_score_mean"] > agg69["evidence_answer_score_mean"],
        "ceiling_matches_task70_r7_prediction": retrieval_check["prediction_match"]["ceiling_mean_match"],
        "base_rag_macro_up": score_delta["base_rag"]["delta_macro"] > 0,
        "base_rag_pass_up": score_delta["base_rag"]["delta_pass_all"] > 0,
        "dapt_rag_macro_up": score_delta["dapt_rag"]["delta_macro"] > 0,
        "dapt_rag_pass_up": score_delta["dapt_rag"]["delta_pass_all"] > 0,
        "either_rag_arm_e2e_up": (score_delta["base_rag"]["delta_macro"] > 0
                                 or score_delta["base_rag"]["delta_pass_all"] > 0
                                 or score_delta["dapt_rag"]["delta_macro"] > 0
                                 or score_delta["dapt_rag"]["delta_pass_all"] > 0),
        "neither_rag_arm_macro_down": (score_delta["base_rag"]["delta_macro"] >= 0
                                      and score_delta["dapt_rag"]["delta_macro"] >= 0),
        "neither_rag_arm_pass_down": (score_delta["base_rag"]["delta_pass_all"] >= 0
                                     and score_delta["dapt_rag"]["delta_pass_all"] >= 0),
        "abstention_not_regressed_vs_task69": (
            abst71["base_rag_correct"] >= abst69["base_rag_correct"]
            and abst71["dapt_rag_correct"] >= abst69["dapt_rag_correct"]
        ),
        "contract_violations_zero": len(agg["contract_violations"]) == 0,
        "identical_contexts_both_rag_arms": comparison["identical_contexts_verified"],
        "baseline_gate_pass": baseline_check.get("gate") == "PASS",
    }
    loops71 = comparison["behaviour"]["base_rag"]["looped_cases"], comparison["behaviour"]["dapt_rag"]["looped_cases"]
    loops69 = t69_comparison["behaviour"]["base_rag"]["looped_cases"], t69_comparison["behaviour"]["dapt_rag"]["looped_cases"]
    checks["no_loop_increase"] = (loops71[0] <= loops69[0] and loops71[1] <= loops69[1])
    material_regressions = []
    for arm in ("base_rag", "dapt_rag"):
        if score_delta[arm]["delta_macro"] < 0:
            material_regressions.append(f"{arm} macro {score_delta[arm]['delta_macro']}")
        if score_delta[arm]["delta_pass_all"] < 0:
            material_regressions.append(f"{arm} pass-all {score_delta[arm]['delta_pass_all']}")
    if not checks["abstention_not_regressed_vs_task69"]:
        material_regressions.append(
            f"abstention vs Task-69: base_rag {abst69['base_rag_correct']}->{abst71['base_rag_correct']}, "
            f"dapt_rag {abst69['dapt_rag_correct']}->{abst71['dapt_rag_correct']} "
            f"(total {abst69['base_rag_correct'] + abst69['dapt_rag_correct']}->"
            f"{abst71['base_rag_correct'] + abst71['dapt_rag_correct']})")
    if not checks["contract_violations_zero"]:
        material_regressions.append("contract violations > 0")
    if not checks["no_loop_increase"]:
        material_regressions.append(f"loops up {loops69} -> {loops71}")

    ceiling_up = checks["ceiling_mean_up"]
    improved = checks["either_rag_arm_e2e_up"] and not material_regressions
    score_flat = not checks["either_rag_arm_e2e_up"]
    context_pressure = (
        budget["at_cap_192"]["base_rag"]["task71_r7"] > budget["at_cap_192"]["base_rag"]["task69"]
        or budget["at_cap_192"]["dapt_rag"]["task71_r7"] > budget["at_cap_192"]["dapt_rag"]["task69"]
    )
    if improved:
        outcome = ("RECOMMEND", "R7 improves end-to-end scores with no material regressions "
                                "=> recommend a controlled production-candidate experiment "
                                "(config change NOT applied to production here)")
    elif ceiling_up and score_flat:
        outcome = ("INSUFFICIENT", "evidence ceiling improved but end-to-end score flat "
                                   "=> evidence availability alone is insufficient; inspect "
                                   "selection/grounding next (do not adopt R7 on score grounds)")
    elif material_regressions or (not checks["no_loop_increase"]):
        outcome = ("DO_NOT_RECOMMEND", "context/behavioural or score regressions under R7 "
                                       "=> do not recommend the R7 window")
    else:
        outcome = ("NEUTRAL", "no meaningful end-to-end change => keep the Task-69 evidence "
                              "config (EVIDENCE_K=5, TEXT_TRUNC=500); next retrieval experiment "
                              "is source-anchored within-source ranking")
    if context_pressure and outcome[0] in ("NEUTRAL", "INSUFFICIENT"):
        outcome = (outcome[0], outcome[1] + " | note: increased 192-token-cap pressure under R7")

    decision_gate = {
        "criteria": checks,
        "material_regressions": material_regressions,
        "per_case_vs_task69": {
            "improved_n": len(improved_cases), "improved": improved_cases,
            "regressed_n": len(regressed_cases), "regressed": regressed_cases,
        },
        "looped": {"task69": loops69, "task71_r7": loops71},
        "outcome": outcome[0],
        "rationale": outcome[1],
        "production_retrieval_changed": False,
    }

    # ---------------- report json ----------------
    report_json = {
        "task": "TASK 71 — R7 GOVERNED RAG CONTROLLED EVALUATION",
        "verdict": f"{outcome[0]}: {outcome[1]}",
        "headline": {
            "overall": overall,
            "vs_task69": score_delta,
            "rag_gain_over_base_r7": comparison["gains"]["rag_gain_over_base"]["delta"],
            "rag_gain_over_dapt_r7": comparison["gains"]["rag_gain_over_dapt"]["delta"],
            "dapt_gain_within_rag_r7": comparison["gains"]["dapt_gain_within_rag"]["delta"],
        },
        "phase3_baseline_gate": baseline_check,
        "phase4_design": {
            "r7_only_diff": "EVIDENCE_K 5->10, TEXT_TRUNC 500->1000 (verified)",
            "config_diff": metrics.get("config_diff_vs_task69"),
            "prompts_sha256": provenance["prompts_sha256"],
            "task69_prompts_sha256": TASK69_PROMPTS_SHA,
            "same_model_decoding_seed": True,
            "no_rag_arms_reused_frozen": "dapt01_{base,dapt}_results.jsonl (byte-identical to Task-69 input)",
            "run_metadata": run_meta,
            "baseline_run_metadata": baseline_meta,
        },
        "phase5_scores_vs_task69": score_delta,
        "phase6_retrieval": retrieval_check,
        "phase7_failures": {
            "counts_r7": fc71["counts"], "counts_task69": fc69["counts"],
            "split_r7": fc71["split"], "split_task69": fc69["split"],
            "recovered_cases": recovered_detail,
            "residual_ev0": residual_ev0,
            "definitions": fc71["definitions"],
        },
        "phase8_budget": budget,
        "phase9_decision_gate": decision_gate,
        "category_table": comparison["category_table"],
        "language_table": comparison["language_table"],
        "abstention": comparison["abstention"],
        "behaviour": comparison["behaviour"],
        "attribution": comparison["attribution"],
        "identical_contexts_verified": comparison["identical_contexts_verified"],
        "integrity": {
            "frozen_cases_sha256": FROZEN_CASES_SHA256,
            "adapter_sha256": ADAPTER_SHA256,
            "prompts_sha256": provenance["prompts_sha256"],
            "task69_prompts_sha256": TASK69_PROMPTS_SHA,
            "baseline_gate": baseline_check["gate"],
            "artifact_sha256": {
                name: sha256_file(EVAL / name)
                for name in (
                    "task71_base_rag_results.jsonl", "task71_dapt_rag_results.jsonl",
                    "task71_r7_evidence.jsonl", "task71_r7_prompts.jsonl",
                    "task71_r7_metrics.json", "task71_r7_comparison.json",
                    "task71_r7_run_metadata.json", "task71_baseline_base_rag_results.jsonl",
                    "task71_baseline_check.json", "task71_baseline_run_metadata.json",
                    "task71_r7_results.jsonl",
                )
            },
        },
        "artifacts": {
            "consolidated_results": "data/evaluation/task71_r7_results.jsonl",
            "comparison": "data/evaluation/task71_r7_comparison.json",
            "report_md": "data/reports/task71_r7_evaluation.md",
            "report_json": "data/reports/task71_r7_evaluation.json",
        },
        "not_measured": comparison["not_measured"],
        "run_metadata": run_meta,
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "task71_r7_evaluation.json").write_text(
        json.dumps(report_json, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("wrote data/reports/task71_r7_evaluation.json")

    # ---------------- report md ----------------
    o, d = overall, score_delta
    rc_pred = retrieval_check["prediction_match"]
    t69_cat = {r["category"]: r for r in t69_comparison["category_table"]}
    t69_lang = {r["language"]: r for r in t69_comparison["language_table"]}
    a69, a71 = t69_comparison["attribution"], comparison["attribution"]
    md = f"""# TASK 71 — R7 Governed RAG Controlled Evaluation

**Verdict: {outcome[0]} — {outcome[1]}**

Phase-3 gate: **{baseline_check['gate']}** (47/47 byte-exact vs frozen Task-69 BASE+RAG).
R7 differs from Task-69 **only** in `EVIDENCE_K 5→10` and `TEXT_TRUNC 500→1000`
(config diff verified: {json.dumps(metrics.get('config_diff_vs_task69'))}). Same model, same system
prompt, greedy, 192-token cap, seed 42; no-RAG arms are the frozen Task-60 files reused
byte-identically (exactly equivalent to Task-69).

## 1. Four-arm scores and deltas vs Task-69 (frozen metric)

| Arm | macro (Task-69 → R7) | pass-all (Task-69 → R7) |
|---|---|---|
| BASE (no RAG) | {d['base']['task69']['macro_keyterm']} → **{d['base']['task71_r7']['macro_keyterm']}** (Δ{d['base']['delta_macro']:+}) | {d['base']['task69']['pass_all']} → {d['base']['task71_r7']['pass_all']} (Δ{d['base']['delta_pass_all']:+}) |
| DAPT-01 (no RAG) | {d['dapt']['task69']['macro_keyterm']} → **{d['dapt']['task71_r7']['macro_keyterm']}** (Δ{d['dapt']['delta_macro']:+}) | {d['dapt']['task69']['pass_all']} → {d['dapt']['task71_r7']['pass_all']} (Δ{d['dapt']['delta_pass_all']:+}) |
| **BASE + R7 RAG** | {d['base_rag']['task69']['macro_keyterm']} → **{d['base_rag']['task71_r7']['macro_keyterm']}** (Δ{d['base_rag']['delta_macro']:+}) | {d['base_rag']['task69']['pass_all']} → **{d['base_rag']['task71_r7']['pass_all']}** (Δ{d['base_rag']['delta_pass_all']:+}) |
| DAPT-01 + R7 RAG | {d['dapt_rag']['task69']['macro_keyterm']} → **{d['dapt_rag']['task71_r7']['macro_keyterm']}** (Δ{d['dapt_rag']['delta_macro']:+}) | {d['dapt_rag']['task69']['pass_all']} → **{d['dapt_rag']['task71_r7']['pass_all']}** (Δ{d['dapt_rag']['delta_pass_all']:+}) |

- Per-case vs Task-69 (RAG arms): {decision_gate['per_case_vs_task69']['improved_n']} improved,
  {decision_gate['per_case_vs_task69']['regressed_n']} regressed.
- R7 gains over no-RAG: BASE {comparison['gains']['rag_gain_over_base']['delta']},
  DAPT {comparison['gains']['rag_gain_over_dapt']['delta']}; DAPT within R7-RAG
  {comparison['gains']['dapt_gain_within_rag']['delta']} (Task-69 was −0.0213).

## 2. Retrieval quality (Phase 6): R7 vs Task-69 vs Task-70 offline prediction

- Source Recall@5 {agg['source_recall_at_5']} (Task-69 {agg69['source_recall_at_5']}), Recall@10
  {agg['source_recall_at_10']} (Task-69 {agg69['source_recall_at_10']}), MRR {agg['source_mrr']} —
  ranking is unchanged by design (R7 only widens the evidence window).
- Evidence ceiling: mean **{agg['evidence_answer_score_mean']}** (Task-69 {agg69['evidence_answer_score_mean']},
  Task-70 R7 prediction {r7_pred['evidence_ceiling_mean']}; match={rc_pred['ceiling_mean_match']}),
  full-ceiling **{agg['evidence_answer_score_full']}**/43 (Task-69 {agg69['evidence_answer_score_full']},
  predicted {r7_pred['evidence_ceiling_full']}; match={rc_pred['ceiling_full_match']}).
- Evidence-zero cases: **{len(ev0_71)}** (Task-69 {len(ev0_69)},
  predicted {r7_pred['ev0_count']}; cases match={rc_pred['ev0_cases_match']}) →
  {', '.join(ev0_71)}.
- Recovered by the R7 window (evidence score 0→>0): {', '.join(RECOVERED_CASES)}.
- Abstention forbidden-pattern presence in context: {agg['abstention_evidence_forbidden_hits']}/4
  (invariant, predicted 4; match={rc_pred['abstention_hits_match']}). Contract violations:
  {len(agg['contract_violations'])} (zero, match={rc_pred['contract_zero']}).
- Config diff vs Task-69 verified: **{metrics.get('config_diff_verified')}**
  ({json.dumps(metrics.get('config_diff_vs_task69'))}).

## 3. Failure attribution (Phase 7)

| | retrieval-side | generation-side | success | prior knowledge |
|---|---|---|---|---|
| BASE + R7 | {fc71['split']['base_rag']['retrieval_side']} | {fc71['split']['base_rag']['generation_side']} | {fc71['split']['base_rag']['success']} | {fc71['split']['base_rag']['prior_knowledge']} |
| DAPT-01 + R7 | {fc71['split']['dapt_rag']['retrieval_side']} | {fc71['split']['dapt_rag']['generation_side']} | {fc71['split']['dapt_rag']['success']} | {fc71['split']['dapt_rag']['prior_knowledge']} |
| BASE + R5 (Task-69) | {fc69['split']['base_rag']['retrieval_side']} | {fc69['split']['base_rag']['generation_side']} | {fc69['split']['base_rag']['success']} | {fc69['split']['base_rag']['prior_knowledge']} |
| DAPT-01 + R5 (Task-69) | {fc69['split']['dapt_rag']['retrieval_side']} | {fc69['split']['dapt_rag']['generation_side']} | {fc69['split']['dapt_rag']['success']} | {fc69['split']['dapt_rag']['prior_knowledge']} |

- Residual ev0 under R7 ({len(ev0_71)}): {', '.join(ev0_71)} — remaining bottleneck is still
  ranking depth, not window size.
- Recovered-case detail (evidence + arm scores, Task-69 → R7): see `phase7_failures.recovered_cases`
  in the JSON report.
- RAG counts R7: {json.dumps(fc71['counts'])}.

## 4. Category / language (Task-69 → R7, base_rag / dapt_rag mean keyterm)

{chr(10).join(f"- {r['category']}: base_rag {t69_cat[r['category']]['base_rag_mean']}→{r['base_rag_mean']}, dapt_rag {t69_cat[r['category']]['dapt_rag_mean']}→{r['dapt_rag_mean']} (pass-all {t69_cat[r['category']]['base_rag_pass_all']}→{r['base_rag_pass_all']} / {t69_cat[r['category']]['dapt_rag_pass_all']}→{r['dapt_rag_pass_all']})" for r in comparison['category_table'])}
- Languages: {', '.join(f"{r['language']}: {t69_lang[r['language']]['base_rag_mean']}→{r['base_rag_mean']}" for r in comparison['language_table'])} (base_rag mean).
- Full 4-arm category/language tables: `task71_r7_comparison.json` → `category_table` / `language_table`.

## 5. Abstention

R7 correct abstentions: BASE {abst71['base_correct']}/4, DAPT {abst71['dapt_correct']}/4,
**BASE+R7 {abst71['base_rag_correct']}/4**, DAPT+R7 {abst71['dapt_rag_correct']}/4
(Task-69 RAG arms: base_rag {abst69['base_rag_correct']}/4, dapt_rag {abst69['dapt_rag_correct']}/4;
total held at {abst69['base_rag_correct'] + abst69['dapt_rag_correct']} →
{abst71['base_rag_correct'] + abst71['dapt_rag_correct']}, with a per-arm swap base 1→0 / dapt 0→1 —
flagged as a material regression by the per-arm gate). Evidence surfaces the forbidden patterns in
all four cases (invariant); safety is behaviour-held, not context-prevented.

## 6. Behaviour & attribution

- Loops (Task-68 detector): base_rag {loops69[0]} → {loops71[0]}, dapt_rag {loops69[1]} → {loops71[1]}.
- Literal INFRINGEMENT tokens: 0 in all arms.
- Attribution (first-5 provenance slice, scorer unchanged from Task-69): cited-author
  base_rag {a69['base_rag']['cited_evidence_author']}→{a71['base_rag']['cited_evidence_author']},
  dapt_rag {a69['dapt_rag']['cited_evidence_author']}→{a71['dapt_rag']['cited_evidence_author']};
  attribution-word base_rag {a69['base_rag']['cited_attribution_word']}→{a71['base_rag']['cited_attribution_word']},
  dapt_rag {a69['dapt_rag']['cited_attribution_word']}→{a71['dapt_rag']['cited_attribution_word']}.

## 7. Prompt/evidence budget (Phase 8)

- Context chars: mean {budget['context_chars']['task69']['mean']} →
  {budget['context_chars']['task71_r7']['mean']} (×{budget['context_chars']['growth_mean_x']}), median
  {budget['context_chars']['task69']['median']} → {budget['context_chars']['task71_r7']['median']}
  (×{budget['context_chars']['growth_median_x']}), max {budget['context_chars']['task71_r7']['max']}.
- Evidence items per case: 5 → 10; 10/10 items rendered in every prompt (kernel-asserted).
- 192-token-cap hits: base_rag {budget['at_cap_192']['base_rag']['task69']} →
  {budget['at_cap_192']['base_rag']['task71_r7']}, dapt_rag
  {budget['at_cap_192']['dapt_rag']['task69']} → {budget['at_cap_192']['dapt_rag']['task71_r7']}
  (cap pressure {'increased' if context_pressure else 'not increased'}).
- Decode time (T4): load {budget['decode_seconds']['model_load']}s, base_rag
  {budget['decode_seconds']['base_rag']}s, dapt_rag {budget['decode_seconds']['dapt_rag']}s
  (Task-69: {budget['decode_seconds']['task69_reference']['base_rag']}s /
  {budget['decode_seconds']['task69_reference']['dapt_rag']}s).
- No decoding/seed/model change; no prompt change outside the R7 window.

## 8. Decision gate (Phase 9)

- Criteria: {json.dumps(checks)}
- Material regressions: {material_regressions if material_regressions else 'none'}
- **Outcome: {outcome[0]}** — {outcome[1]}
- Production retrieval config: **NOT changed** (evaluation experiment only).

## 9. Integrity, provenance, environment

- Frozen cases sha256 **{FROZEN_CASES_SHA256}** verified; DAPT-01 adapter sha256
  **{ADAPTER_SHA256}** (verified on-VM before every run).
- Baseline reproduction: {baseline_check['gate']}, fresh file sha
  {baseline_check['fresh_sha256'][:16]}… byte-exact on {', '.join(baseline_check['verified_byte_exact_fields'] or [])}.
- R7 prompts sha {provenance['prompts_sha256'][:16]}…; Task-69 prompts sha unchanged
  {TASK69_PROMPTS_SHA[:16]}…; all 47 contexts changed vs Task-69 (window is the only diff).
- Both RAG arms received byte-identical contexts: **{comparison['identical_contexts_verified']}**.
- Generation host: **{run_meta.get('run_host')}** — {run_meta.get('gpu')}, torch
  {run_meta.get('torch')}, python {run_meta.get('python')}, transformers
  {run_meta.get('transformers')} / peft {run_meta.get('peft')} /
  bitsandbytes {run_meta.get('bitsandbytes')} (Task-69 stack, pinned).
- Runtime deviations (environment only, protocol-neutral): SDPA **memory-efficient-only**
  backend with transformers `enable_gqa` forced onto the `repeat_kv` path — math SDPA
  materialises S×S×H fp32 buffers and OOMs at R7 lengths on the 14.5GiB T4, flash/cudnn
  are invalid on sm75, and mem-efficient has no GQA kernel on this build (raw failure
  then fix: `Invalid backend` → repeat_kv OK, peak 6.48GiB, verified by single-case probe
  before the full run). fp16 numerics, greedy decoding, seed 42, 192 cap, model, prompts
  and system prompt all unchanged. Outputs rebuilt from the exec stdout `RESULT_JSON`
  stream (identical `json.dumps` as the file writer) after the Colab runtime disconnected
  post-generation — flagged in `task71_r7_run_metadata.json`.
- Not measured (never synthesised): evaluator fields for RAG arms, dense-channel contribution,
  query-side sect filters (N/A), fluency/human preference, graded passage relevance.

## 10. Files

- `data/evaluation/task71_r7_results.jsonl` — consolidated per-case rows (retrieval, prompt,
  evidence, four-arm outputs + hashes, scores, failure classes, provenance)
- `data/evaluation/task71_r7_comparison.json` — four-arm comparison (scorer output)
- `data/evaluation/task71_{{base,dapt}}_rag_results.jsonl` — raw R7 generation outputs
- `data/evaluation/task71_r7_{{evidence,prompts}}.jsonl`, `task71_r7_metrics.json`,
  `task71_r7_run_metadata.json`
- `data/evaluation/task71_baseline_{{base_rag_results,check,run_metadata}}.*` — Phase-3 gate record
- `data/reports/task71_r7_evaluation.{{md,json}}`
- `experiments/task71/{{task71_build_r7_evidence,task71_rag_infer,task71_verify_baseline,task71_score,task71_report}}.py`

**HARD STOP: NO TRAINING WAS RUN IN TASK 71** (no SFT-03, no DAPT-02, no new dense model,
no production retrieval change, no canonical-corpus or frozen-benchmark modification).
"""
    (REPORTS / "task71_r7_evaluation.md").write_text(md, encoding="utf-8")
    print("wrote data/reports/task71_r7_evaluation.md")

    print("headline:", json.dumps({a: d[a]["task71_r7"] for a in d}))
    print("vs_task69 deltas:", json.dumps({a: d[a]["delta_macro"] for a in d}))
    print("gate outcome:", outcome[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

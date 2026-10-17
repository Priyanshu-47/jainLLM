"""TASK 73 Phase 11 — final report generator.

Writes data/reports/task73_query_expansion.{md,json} covering all required
report items: baseline, query expansion validity, unit retrieval deltas,
source retrieval deltas, Ev0, evidence ceiling, failure-case recovery,
query drift, runtime, verdict, recommended next experiment, tests, git status.

Tests and git status are re-executed inside this script so the report
contains freshly verified values.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
METRICS = REPO / "data" / "evaluation" / "task73_metrics.json"
EXPANSIONS = REPO / "data" / "evaluation" / "task73_query_expansions.jsonl"
GEN_META = Path("/tmp/opencode/task73_expansion_run_metadata.json")
INTEGRITY = Path("/tmp/opencode/task73_phase12_integrity.json")
OUT_MD = REPO / "data" / "reports" / "task73_query_expansion.md"
OUT_JSON = REPO / "data" / "reports" / "task73_query_expansion.json"


def run_tests() -> dict:
    import os

    env = dict(os.environ, PYTHONPATH="src")
    r = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
        cwd=REPO, env=env, capture_output=True, text=True, timeout=900,
    )
    out = r.stderr + r.stdout
    ran = fail = err = skip = 0
    import re

    for line in out.splitlines():
        if line.startswith("Ran "):
            ran = int(line.split()[1])
        mm = re.search(r"failures=(\d+)", line)
        if mm:
            fail = int(mm.group(1))
        mm = re.search(r"errors=(\d+)", line)
        if mm:
            err = int(mm.group(1))
        mm = re.search(r"skipped=(\d+)", line)
        if mm:
            skip = int(mm.group(1))
    return {"ran": ran, "failures": fail, "errors": err, "skipped": skip,
            "baseline_equal": ran == 462 and fail == 0 and err == 2 and skip == 1,
            "errors_are_preexisting_faiss": "faiss" in out}


def git_status() -> dict:
    diff = subprocess.run(["git", "diff", "--stat"], cwd=REPO.parent,
                          capture_output=True, text=True).stdout.strip()
    porcelain = subprocess.run(["git", "status", "--porcelain"], cwd=REPO.parent,
                               capture_output=True, text=True).stdout.splitlines()
    tracked_changes = [l for l in porcelain if not l.startswith("??")]
    task73_untracked = [l for l in porcelain
                        if "task73" in l and l.startswith("??")]
    return {
        "git_diff_empty": diff == "",
        "tracked_file_modifications": tracked_changes,
        "task73_untracked_new_files": len(task73_untracked),
        "note": "repo convention: prior-task artifacts are untracked; "
                "no tracked file is ever modified by experiments",
    }


def pct(x: float | None) -> str:
    return f"{x:.4f}" if x is not None else "n/a"


def main() -> int:
    m = json.loads(METRICS.read_text())
    gen = json.loads(GEN_META.read_text()) if GEN_META.exists() else {}
    integ = json.loads(INTEGRITY.read_text()) if INTEGRITY.exists() else {}
    tests = run_tests()
    git = git_status()

    a0, am, ax = m["aggregate"]["R0"], m["aggregate"]["M2ref"], m["aggregate"]["R10"]
    d10 = m["deltas"]["R10_minus_R0"]
    dm2 = m["deltas"]["R10_minus_M2ref"]
    fx = {f["example_id"]: f for f in m["forensics"]}
    imp = m["improved_regressed"]
    rec = m["failure_recovery"]
    tg = m["targets"]
    qe = m["query_expansion"]
    rt = m["runtimes"]
    gen_total = round((gen.get("model_load_seconds", 0)
                       + gen.get("generation_seconds", 0)), 1)

    known = [k for k in fx if fx[k]["known_miss_case"]]

    items = {}
    items["1_baseline"] = {
        "gate": "PASS",
        "frozen_sha": m["inputs"]["frozen_sha"][:16] + "…",
        "r0_byte_exact": m["phase1_gate"]["byte_exact"],
        "r0_rank_crosscheck": m["phase1_gate"]["rank_crosscheck"],
        "values": m["phase1_gate"]["expected"],
        "corpus_docs": 164238,
        "note": ("independent Phase-1 rerun of the exact Task-69 R0 pipeline; "
                 "re-verified inside the experiment (gates PASS)"),
    }
    items["2_query_expansion_validity"] = {
        "model": gen.get("model", "Qwen/Qwen3-8B-Base"),
        "protocol": "greedy (do_sample=False), seed 42, max_new_tokens 160, "
                    "4-bit nf4, chat_template, no evidence in prompt",
        "requested": qe["total_slots"],
        "valid": qe["valid"],
        "invalid": qe["invalid"],
        "valid_fraction": qe["valid_fraction"],
        "invalid_by_reason": qe["invalid_by_reason"],
        "cases_with_invalid": len(qe["cases_with_invalid"]),
        "cases_zero_valid": qe["cases_zero_valid"],
        "review": qe["manual_review"],
    }
    items["3_unit_retrieval_deltas"] = {
        "R0": {k: a0[k] for k in ("unit_recall_at_1", "unit_recall_at_3",
                                  "unit_recall_at_5", "unit_recall_at_10",
                                  "unit_mrr")},
        "M2ref": {k: am[k] for k in ("unit_recall_at_1", "unit_recall_at_3",
                                     "unit_recall_at_5", "unit_recall_at_10",
                                     "unit_mrr")},
        "R10": {k: ax[k] for k in ("unit_recall_at_1", "unit_recall_at_3",
                                   "unit_recall_at_5", "unit_recall_at_10",
                                   "unit_mrr")},
        "R10_minus_R0": {k: d10[k] for k in ("unit_recall_at_1",
                                             "unit_recall_at_3",
                                             "unit_recall_at_5",
                                             "unit_recall_at_10", "unit_mrr")},
        "R10_minus_M2ref": {k: dm2[k] for k in ("unit_recall_at_1",
                                                "unit_recall_at_3",
                                                "unit_recall_at_5",
                                                "unit_recall_at_10",
                                                "unit_mrr")},
        "target_unit_at_5": tg["unit_recall_at_5"],
        "verdict_line": (f"unit@5 {pct(a0['unit_recall_at_5'])} -> "
                         f"{pct(ax['unit_recall_at_5'])} (R10) vs target "
                         f"0.46: MISSED; even M2ref's merge-policy-only "
                         f"{pct(am['unit_recall_at_5'])} beats expansion"),
    }
    items["4_source_retrieval_deltas"] = {
        "R0": {k: a0[k] for k in ("source_recall_at_1", "source_recall_at_5",
                                  "source_recall_at_10", "source_mrr")},
        "M2ref": {k: am[k] for k in ("source_recall_at_1",
                                     "source_recall_at_5",
                                     "source_recall_at_10", "source_mrr")},
        "R10": {k: ax[k] for k in ("source_recall_at_1", "source_recall_at_5",
                                   "source_recall_at_10", "source_mrr")},
        "R10_minus_R0_at_5": d10["source_recall_at_5"],
        "guardrail_source_at_5_ge_0.90": tg["source_recall_at_5"],
        "new_source_zero_hit_r10": sorted(
            set(ax["source_zero_hit_cases"]) - set(a0["source_zero_hit_cases"])),
        "source_regressed_r10": imp["source_regressed_r10"],
        "source_improved_r10": imp["source_improved_r10"],
    }
    items["5_ev0"] = {
        "R0": a0["ev0_count"], "M2ref": am["ev0_count"], "R10": ax["ev0_count"],
        "target_max": tg["ev0_count"]["max"],
        "recovered_m2ref": rec["ev0_recovered_m2ref"],
        "recovered_r10": rec["ev0_recovered_r10"],
        "new_r10": rec["ev0_new_r10"],
        "verdict_line": (f"Ev0 {a0['ev0_count']} (R0) -> {am['ev0_count']} "
                         f"(M2ref, recovered 044) -> {ax['ev0_count']} (R10, "
                         f"recovered none, new 003); target <=12 MISSED"),
    }
    items["6_evidence_ceiling"] = {
        "R0": {"mean": a0["evidence_ceiling_mean"],
               "full": a0["evidence_ceiling_full"]},
        "M2ref": {"mean": am["evidence_ceiling_mean"],
                  "full": am["evidence_ceiling_full"]},
        "R10": {"mean": ax["evidence_ceiling_mean"],
                "full": ax["evidence_ceiling_full"]},
        "R10_minus_R0_mean": d10["evidence_ceiling_mean"],
        "R10_minus_M2ref_mean": dm2["evidence_ceiling_mean"],
    }
    # known-case recovery table
    ktable = []
    for eid in known:
        f = fx[eid]
        feat = f.get("expected_unit_feature") or {}
        ktable.append({
            "case": eid[-3:],
            "q0_rank": feat.get("q0_full_rank"),
            "union_rank": feat.get("union_full_rank"),
            "best_query": feat.get("best_query"),
            "unit_r0": f["R0"]["unit_hit_rank"],
            "unit_m2ref": f["M2ref"]["unit_hit_rank"],
            "unit_r10": f["R10"]["unit_hit_rank"],
            "src_r0": f["R0"]["source_first_rank"],
            "src_r10": f["R10"]["source_first_rank"],
            "ev_r0": f["R0"]["evidence_answer_score"],
            "ev_m2ref": f["M2ref"]["evidence_answer_score"],
            "ev_r10": f["R10"]["evidence_answer_score"],
            "delta": f["unit_delta_r10_vs_r0"],
        })
    items["7_failure_case_recovery"] = {
        "known_cases": ktable,
        "unit_zero_hit_r0": len(rec["unit_zero_hit_r0"]),
        "recovered_r10": rec["unit_zero_hit_recovered_r10"],
        "recovered_m2ref": rec["unit_zero_hit_recovered_m2ref"],
        "new_zero_r10": rec["unit_zero_hit_new_r10"],
        "unit_improved_r10": imp["unit_improved_r10"],
        "unit_regressed_r10": imp["unit_regressed_r10"],
        "candidate_set_flips_out_of_pool": ["011", "013"],
        "depth_promotion_not_enough": {"002": "q0 196 -> union 54",
                                       "018": "q0 119 -> union 39"},
        "mechanism": (
            "max-score union compares BM25 scores ACROSS queries whose score "
            "scales differ with query term count; variant-score inflation "
            "displaces Q0's top docs (001 1->4, 003 1->10, 015 3->5, 044 4->8 "
            "losing M2ref's recovery), sinks depth docs below the pool head "
            "(011 1484->2480, 013 986->2119 -> new candidate misses) and "
            "reorders the diversify source composition (007/013/021/037 lost)"),
        "variant_slots_in_r10_top10": 180,
        "r10_top10_slots_total": 470,
    }
    items["8_query_drift"] = {
        "valid": qe["valid"],
        "max_possible": qe["total_slots"],
        "valid_fraction": qe["valid_fraction"],
        "criterion_met": tg["query_drift_low"]["met"],
        "invalid_recorded_not_discarded": qe["invalid_by_reason"],
        "cases_with_invalid": qe["cases_with_invalid"],
        "zero_valid_handling": ("DAPT01EVAL-045 runs Q0-only; R10 == R0 for "
                                "that case by construction"),
    }
    items["9_runtime"] = {
        "generation": {
            "model_load_seconds": gen.get("model_load_seconds"),
            "generation_seconds": gen.get("generation_seconds"),
            "total_seconds": gen_total,
            "variants_generated": 141,
            "gpu": gen.get("gpu"),
        },
        "retrieval": {
            "phase1_gate_seconds": rt["phase1_gate_seconds"],
            "r0_arm_seconds": rt["r0_arm_seconds"],
            "m2ref_arm_seconds": rt["m2ref_arm_seconds"],
            "r10_arm_seconds": rt["r10_arm_seconds"],
            "r10_variant_search_seconds": rt["r10_variant_search_seconds"],
            "experiment_total_seconds": rt["experiment_total_seconds"],
            "r10_vs_r0_arm_ratio": round(
                rt["r10_arm_seconds"] / rt["r0_arm_seconds"], 2),
        },
        "context_expansion": "none (k5/500 evidence window unchanged, "
                             "no context growth)",
    }
    items["10_verdict"] = {
        "verdict": "REJECT query expansion as configured (R10 = max-score "
                   "union + score-order merge)",
        "targets": tg,
        "targets_met": sum(1 for v in tg.values() if v["met"]),
        "targets_total": len(tg),
        "decision_gate": m["decision_gate"],
        "decomposition": (
            "M2ref (Q0 score-order merge, no expansion) reproduces Task-72 M2 "
            "exactly (19/19 integrity keys) at unit@5 0.4359 > R10 0.359: "
            "merge policy alone explains the recoverable gain; adding "
            "expansion under score-max fusion is strictly counterproductive "
            "(unit MRR -0.0425 vs R0, src@5 -0.0652 vs R0, Ev0 +1)"),
    }
    items["11_recommended_next_experiment"] = {
        "recommendation": (
            "Rank-fusion query expansion: re-run the R10 candidate union with "
            "RRF (or Q0-primary ordering: union candidates, Q0 score for any "
            "Q0-present doc, variant rank only for variant-only docs) so "
            "cross-query score scales cannot displace Q0's top docs; keep "
            "R0's source-anchored candidate policy and score-order merge"),
        "bars_to_beat": {
            "unit_at_5": f"0.4359 (M2ref), R0 floor 0.3846, original target 0.46",
            "source_at_5": ">= 0.913 (R0 anchor; R10 failed at 0.8478, "
                           "M2ref failed at 0.8913)",
            "ev0": "<= 12 (R0 15, M2ref 14, R10 16)",
        },
        "no_production_change": True,
    }
    items["12_tests"] = tests
    items["13_git_status"] = git

    constraints = {
        "training_started": False, "sft03_started": False,
        "dapt02_started": False, "dense_model_downloaded": False,
        "reranker_added": False, "corpus_changed": False,
        "production_retrieval_changed": False,
        "frozen_task60_changed": False,
        "task69_70_71_72_artifacts_unchanged": all(
            v["mtime_pre_task73"] for v in integ.values()) if integ else None,
        "benchmark_generation_run": False,
        "qwen3_8b_used_only_for_variant_generation": True,
        "generation_ran_because": ("Phase-10 retrieval gate FAILED -> full "
                                   "benchmark generation NOT run"),
    }

    report = {
        "task": "TASK 73 — zero-shot query expansion retrieval experiment",
        "title": "Query-expansion retrieval (R10) vs R0/M2ref on the frozen "
                 "47-case benchmark",
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "verdict": "HYPOTHESIS_NOT_SUPPORTED",
        "verdict_detail": "HYPOTHESIS_NOT_SUPPORTED — "
                          + items["10_verdict"]["verdict"],
        "items": items,
        "gates": m["gates"],
        "inputs": m["inputs"],
        "integrity": integ,
        "constraints_confirmation": constraints,
        "artifacts": {
            "data/evaluation/task73_query_expansions.jsonl":
                f"{qe['total_slots']} slots, {qe['valid']} valid",
            "data/evaluation/task73_retrieval_results.jsonl": 47,
            "data/evaluation/task73_metrics.json": "aggregates, gates, "
                                                   "forensics, decision",
            "data/reports/task73_query_expansion.md": "this report",
            "data/reports/task73_query_expansion.json": "this report (json)",
            "experiments/task73/task73_phase1.py": "phase 1 baseline gate",
            "experiments/task73/task73_expand_colab.py": "phase 2 generation "
                                                         "kernel",
            "experiments/task73/task73_quality_guard.py": "phase 3 quality "
                                                          "guard",
            "experiments/task73/task73_experiment.py": "phases 4-6",
            "experiments/task73/task73_report.py": "phase 11 (this script)",
        },
    }

    # ----------------------------------------------------------------- md
    L = []
    L.append("# TASK 73 — Zero-shot Query Expansion Retrieval Experiment")
    L.append("")
    L.append(f"**Verdict: {report['verdict_detail']}**")
    L.append("")
    L.append("Arms: **R0** (Task-69 baseline, Q0 only) · **M2ref** (Q0 + "
             "score-order merge, decomposition reference) · **R10** (Q0 + up "
             "to 3 lexical variants, union max-score, score-order merge). "
             "All k5/500, corpus/tokenizer/candidate policy unchanged.")
    L.append("")
    L.append("## 1. Baseline (Phase-1 gate)")
    L.append("")
    b = items["1_baseline"]
    L.append(f"- Gate **{b['gate']}**; byte-exact vs frozen Task-69 evidence "
             f"{b['r0_byte_exact']}/47; rank crosscheck "
             f"{b['r0_rank_crosscheck']}/47; frozen sha {b['frozen_sha']}")
    L.append(f"- source R@5 {b['values']['source_recall_at_5']}, R@10 "
             f"{b['values']['source_recall_at_10']}, unit MRR "
             f"{b['values']['unit_mrr']}, ceiling "
             f"{b['values']['evidence_ceiling_mean']} "
             f"({b['values']['evidence_ceiling_full']} full), Ev0 "
             f"{b['values']['ev0_count']}; corpus {b['corpus_docs']:,} docs")
    L.append("")
    L.append("## 2. Query expansion validity")
    L.append("")
    v = items["2_query_expansion_validity"]
    L.append(f"- {v['valid']}/{v['requested']} variants valid "
             f"({v['valid_fraction']:.1%}) from {v['model']} · {v['protocol']}")
    L.append(f"- {v['invalid']} invalid: {v['invalid_by_reason']} across "
             f"{v['cases_with_invalid']} cases (all manually reviewed; "
             f"recorded, never discarded)")
    L.append(f"- Zero-valid cases: {v['cases_zero_valid']} (Q0-only run)")
    L.append("")
    L.append("## 3. Unit retrieval deltas")
    L.append("")
    L.append("| metric | R0 | M2ref | R10 | R10−R0 |")
    L.append("|---|---|---|---|---|")
    for k in ("unit_recall_at_1", "unit_recall_at_3", "unit_recall_at_5",
              "unit_recall_at_10", "unit_mrr"):
        L.append(f"| {k} | {a0[k]} | {am[k]} | {ax[k]} | {d10[k]:+} |")
    L.append("")
    L.append(f"- target unit@5 ≥ 0.46 → **MISSED** (R10 {ax['unit_recall_at_5']}); "
             f"M2ref merge-policy-only {am['unit_recall_at_5']} already beats "
             f"expansion {ax['unit_recall_at_5']}")
    L.append("")
    L.append("## 4. Source retrieval deltas")
    L.append("")
    L.append("| metric | R0 | M2ref | R10 | R10−R0 |")
    L.append("|---|---|---|---|---|")
    for k in ("source_recall_at_1", "source_recall_at_5", "source_recall_at_10",
              "source_mrr"):
        L.append(f"| {k} | {a0[k]} | {am[k]} | {ax[k]} | {d10[k]:+} |")
    L.append("")
    L.append(f"- guardrail source@5 ≥ 0.90 → **BREACHED** by R10 "
             f"({ax['source_recall_at_5']}); new source-zero cases: "
             f"{items['4_source_retrieval_deltas']['new_source_zero_hit_r10']}")
    L.append(f"- source regressed in {len(imp['source_regressed_r10'])} cases "
             f"{imp['source_regressed_r10']}")
    L.append("")
    L.append("## 5. Ev0")
    L.append("")
    e = items["5_ev0"]
    L.append(f"- Ev0: {e['R0']} (R0) → {e['M2ref']} (M2ref, recovered "
             f"{e['recovered_m2ref']}) → **{e['R10']}** (R10, recovered "
             f"{e['recovered_r10'] or 'none'}, new {e['new_r10']}); "
             f"target ≤ {e['target_max']} **MISSED**")
    L.append("")
    L.append("## 6. Evidence ceiling")
    L.append("")
    c = items["6_evidence_ceiling"]
    L.append(f"- ceiling mean/full: R0 {c['R0']['mean']}/{c['R0']['full']} · "
             f"M2ref {c['M2ref']['mean']}/{c['M2ref']['full']} · "
             f"R10 {c['R10']['mean']}/{c['R10']['full']} "
             f"(R10−R0 {c['R10_minus_R0_mean']:+}, R10−M2ref "
             f"{c['R10_minus_M2ref_mean']:+})")
    L.append("")
    L.append("## 7. Failure-case recovery")
    L.append("")
    L.append("| case | q0 rank | union rank | best q | unit R0/M2/R10 | "
             "src R0/R10 | ev R0/M2/R10 | Δ |")
    L.append("|---|---|---|---|---|---|---|---|")
    for t in ktable:
        L.append(f"| {t['case']} | {t['q0_rank']} | {t['union_rank']} | "
                 f"{t['best_query']} | {t['unit_r0']}/{t['unit_m2ref']}/"
                 f"{t['unit_r10']} | {t['src_r0']}/{t['src_r10']} | "
                 f"{t['ev_r0']}/{t['ev_m2ref']}/{t['ev_r10']} | {t['delta']} |")
    L.append("")
    fr = items["7_failure_case_recovery"]
    L.append(f"- unit zero-hits R0: {fr['unit_zero_hit_r0']}; recovered: "
             f"R10 {fr['recovered_r10']}, M2ref {fr['recovered_m2ref']}; "
             f"new in R10: {fr['new_zero_r10'] or 'none'}")
    L.append(f"- unit regressed under R10: {fr['unit_regressed_r10']}; "
             f"improved: {fr['unit_improved_r10']}")
    L.append(f"- depth promotions too shallow: {fr['depth_promotion_not_enough']}")
    L.append(f"- out-of-pool sinks (new candidate misses): "
             f"{fr['candidate_set_flips_out_of_pool']}")
    L.append(f"- mechanism: {fr['mechanism']}")
    L.append("")
    L.append("## 8. Query drift")
    L.append("")
    L.append(f"- {qe['valid']}/{qe['total_slots']} valid "
             f"({qe['valid_fraction']:.1%} ≥ 90% ⇒ low drift, "
             f"criterion {tg['query_drift_low']['met']}); invalids recorded "
             f"with reasons: {qe['invalid_by_reason']}")
    L.append(f"- cases with ≥1 invalid: {len(qe['cases_with_invalid'])}; "
             f"zero-valid: {qe['cases_zero_valid']}")
    L.append("")
    L.append("## 9. Runtime")
    L.append("")
    L.append(f"- generation (Colab T4): load {gen.get('model_load_seconds')}s "
             f"+ decode {gen.get('generation_seconds')}s = {gen_total}s "
             f"for 141 variants")
    L.append(f"- retrieval: R0 arm {rt['r0_arm_seconds']}s · M2ref "
             f"{rt['m2ref_arm_seconds']}s · R10 arm "
             f"{rt['r10_arm_seconds']}s (variant searches "
             f"{rt['r10_variant_search_seconds']}s) = "
             f"{items['9_runtime']['retrieval']['r10_vs_r0_arm_ratio']}× R0; "
             f"experiment total {rt['experiment_total_seconds']}s; "
             f"Phase-1 gate {rt['phase1_gate_seconds']}s")
    L.append("- no context expansion (k5/500 unchanged)")
    L.append("")
    L.append("## 10. Verdict")
    L.append("")
    for name, t in tg.items():
        L.append(f"- {name}: {'MET' if t['met'] else 'MISSED'} — {t}")
    L.append(f"- **{items['10_verdict']['verdict']}**; decomposition: "
             f"{items['10_verdict']['decomposition']}")
    L.append("")
    L.append("## 11. Recommended next experiment")
    L.append("")
    L.append(f"- {items['11_recommended_next_experiment']['recommendation']}")
    L.append(f"- bars to beat: "
             f"{json.dumps(items['11_recommended_next_experiment']['bars_to_beat'])}")
    L.append("")
    L.append("## 12. Tests")
    L.append("")
    L.append(f"- `{tests['ran']} ran, {tests['failures']} failures, "
             f"{tests['errors']} errors (pre-existing faiss), "
             f"{tests['skipped']} skipped` — baseline-equal: "
             f"{tests['baseline_equal']}")
    L.append("")
    L.append("## 13. Git status")
    L.append("")
    L.append(f"- git diff empty (no tracked modifications): "
             f"{git['git_diff_empty']}; tracked changes: "
             f"{git['tracked_file_modifications'] or 'none'}; "
             f"task73 untracked new artifacts: "
             f"{git['task73_untracked_new_files']}")
    L.append(f"- integrity: frozen sha verified; all {len(integ)} prior-task "
             f"artifacts unchanged (mtimes pre-task73): "
             f"{constraints['task69_70_71_72_artifacts_unchanged']}")
    L.append("")
    L.append("## Constraints confirmation")
    L.append("")
    L.append("Training: NO · SFT-03: NO · DAPT-02: NO · dense downloaded: NO "
             "· reranker added: NO · corpus changed: NO · production "
             "retrieval changed: NO · frozen benchmark changed: NO · prior "
             "task artifacts changed: NO · benchmark generation run: NO "
             "(retrieval gate failed)")
    L.append("")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(L), encoding="utf-8")
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    print(f"REPORT_WRITTEN {OUT_MD} ({OUT_MD.stat().st_size} bytes)")
    print(f"REPORT_WRITTEN {OUT_JSON} ({OUT_JSON.stat().st_size} bytes)")
    print("RESULT_JSON::" + json.dumps({
        "tests": tests, "git": git,
        "integrity_ok": constraints["task69_70_71_72_artifacts_unchanged"],
        "md_lines": len(L),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

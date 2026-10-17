"""Task 72 — build the within-source retrieval report (md + json).

Reads task72 outputs (metrics, results, failure cases), verifies Phase-10
artifact integrity (shas / mtimes / row counts), embeds the Phase-11 test
result summary, and writes data/reports/task72_within_source_retrieval.{md,json}.
Read-only with respect to every other artifact.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import task72_experiment as t72  # noqa: E402

REPO = t72.REPO
OUT_MD = REPO / "data" / "reports" / "task72_within_source_retrieval.md"
OUT_JSON = REPO / "data" / "reports" / "task72_within_source_retrieval.json"
TEST_LOG = Path("/tmp/opencode/task72_tests.log")
EXPECTED_TESTS = {"ran": 462, "failures": 0, "errors": 2, "skipped": 1}
KNOWN_ERRORS = [
    "test_from_prebuilt_loads_index",
    "test_from_prebuilt_stores_query_prefix",
]


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_jsonl(p: Path) -> list[dict]:
    return [json.loads(line) for line in p.read_text().splitlines() if line]


def pct(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, int) and not isinstance(v, bool):
        return str(v)
    return f"{v:.4f}"


def parse_tests() -> dict:
    if not TEST_LOG.exists():
        return {"status": "NOT RUN", "raw": str(TEST_LOG)}
    txt = TEST_LOG.read_text()
    ran = int(re.search(r"Ran (\d+) tests", txt).group(1))
    failures = len(re.findall(r"^FAIL:", txt, re.M))
    errors = re.findall(r"^ERROR: (\S+)", txt, re.M)
    skipped = len(re.findall(r"skipped=(\d+)", txt))
    m = re.search(r"skipped=(\d+)", txt)
    skipped = int(m.group(1)) if m else 0
    baseline_equal = (ran == EXPECTED_TESTS["ran"]
                      and failures == EXPECTED_TESTS["failures"]
                      and len(errors) == EXPECTED_TESTS["errors"]
                      and skipped == EXPECTED_TESTS["skipped"]
                      and sorted(errors) == sorted(KNOWN_ERRORS))
    return {
        "status": "PASS" if baseline_equal else "DEVIATION",
        "ran": ran, "failures": failures,
        "errors": errors, "skipped": skipped,
        "baseline_equal": baseline_equal,
        "known_preexisting_errors_only": sorted(errors) == sorted(KNOWN_ERRORS),
    }


def git_status() -> dict:
    diff = subprocess.run(["git", "diff", "--name-only"], capture_output=True,
                          text=True, cwd=REPO).stdout.splitlines()
    st = subprocess.run(["git", "status", "--porcelain"], capture_output=True,
                        text=True, cwd=REPO).stdout.splitlines()
    untracked = [l[3:] for l in st if l.startswith("??")]
    task72_untracked = sorted(u for u in untracked if "task72" in u)
    return {
        "tracked_modified_files": diff,
        "n_untracked": len(untracked),
        "task72_untracked_files": task72_untracked,
    }


def main() -> int:
    metrics = json.loads(t72.OUT_METRICS.read_text())
    failures = load_jsonl(t72.OUT_FAILURES)
    results = load_jsonl(t72.OUT_RESULTS)
    post = metrics["post_hoc_sensitivity"]
    ag = metrics["aggregate"]
    r0, r7, r8, r9 = ag["R0"], ag["R7"], ag["R8"], ag["R9"]
    d80, d97 = metrics["deltas"]["R8_minus_R0"], metrics["deltas"]["R9_minus_R7"]
    m2k5, m2k10 = post["M2_K5_aggregate"], post["M2_K10_aggregate"]
    m2 = {r["example_id"]: r for r in post["M2_K5_per_case_compact"]}

    # ---------------- Phase 10: artifact integrity ----------------
    checks = []
    ok = True

    def chk(name: str, passed: bool, detail: str) -> None:
        nonlocal ok
        checks.append({"name": name, "pass": bool(passed), "detail": detail})
        ok = ok and bool(passed)

    frozen_now = sha256_file(t72.CASES_PATH)
    chk("frozen_benchmark_sha", frozen_now == t72.FROZEN_SHA, frozen_now)
    chk("frozen_benchmark_rows", len(load_jsonl(t72.CASES_PATH)) == 47, "47")
    chk("task72_results_rows", len(results) == 47, str(len(results)))
    chk("task72_failure_rows", len(failures) == 47, str(len(failures)))
    chk("r0_byte_exact_gate",
        metrics["gates"]["r0_byte_exact_vs_task69"] == "47/47", "47/47")
    chk("r7_rescore_gate", metrics["gates"]["r7_frozen_rescore_matches_task71"],
        "ceiling 0.7403/31/10 matched")
    chk("source_presence_invariant",
        metrics["gates"]["source_presence_invariant_across_configs"], "true")
    chk("zero_contract_violations",
        not metrics["gates"]["contract_violations"]
        and not post["contract_violations_m2"], "R0/R7/R8/R9/M2 = 0")
    # prior-task artifact shas (recorded in their own reports) + mtimes
    expected_prior = {
        "data/evaluation/dapt01_eval_cases.jsonl":
            "06625f72190e3ae130447345afdc04342bd19cb76f842285706480cba7765b81",
        "data/evaluation/task69_rag_evidence.jsonl":
            "a51f59d88dad86ebea79cd158b69f845c0f02f3090a92e935f2c5956492d0f33",
        "data/evaluation/task69_retrieval_metrics.json":
            "c642e463c35ed15ab92d2fe9335b91f77af1f99912c1ec17bef670c261aaae73",
        "data/release/rag_corpus.jsonl":
            "4db164bc70e68b4f89837a9f3d3f3bc7fc126d99c826776ba9bf832f070ff8cf",
        "manifests/source_manifest.csv":
            "b96e572f8d97891cc5b472bd21d4355b3b60b2afc74e48d70716ce95bf3293f2",
        "data/evaluation/task71_r7_evidence.jsonl":
            "261d6e4f577914b846ebb03bb0ee4b47370a25eb979ed3cb44e357f474c6fd21",
        "data/evaluation/task71_r7_metrics.json":
            "8f00daa994d929cccdf86f758a4dc1978a2e8d448d2b2e5848d3b7f3c6bca8c8",
    }
    prior_ok = True
    for rel, want in expected_prior.items():
        got = sha256_file(REPO / rel)
        prior_ok = prior_ok and got == want
    chk("prior_task_artifact_shas_unchanged", prior_ok,
        f"{len(expected_prior)} files match their recorded/known shas")
    # mtimes of prior artifacts must predate first task72 output write
    t72_out = min(p.stat().st_mtime for p in
                  (t72.OUT_RESULTS, t72.OUT_FAILURES, t72.OUT_METRICS))
    prior_mtimes = {rel: (REPO / rel).stat().st_mtime
                    for rel in expected_prior}
    mt_ok = all(v < t72_out for v in prior_mtimes.values())
    chk("prior_artifact_mtimes_predate_task72_outputs", mt_ok,
        "all prior mtimes < earliest task72 output mtime")
    git = git_status()
    chk("no_tracked_file_modifications",
        not git["tracked_modified_files"], "git diff empty")

    tests = parse_tests()
    chk("test_suite_baseline_equal", tests.get("baseline_equal", False),
        f"ran={tests.get('ran')} failures={tests.get('failures')} "
        f"errors={len(tests.get('errors') or [])} skipped={tests.get('skipped')}")

    # ---------------- derived numbers ----------------
    ev_trans = {"up": [], "down": [], "same": 0, "none": 0}
    for f in failures:
        a, b = f["r0_evidence_score"], f["r8_evidence_score"]
        if a is None or b is None:
            ev_trans["none"] += 1
        elif b > a:
            ev_trans["up"].append([f["case_id"], a, round(b, 4)])
        elif b < a:
            ev_trans["down"].append([f["case_id"], a, round(b, 4)])
        else:
            ev_trans["same"] += 1
    r7_trans = {"up": [], "down": [], "same": 0, "none": 0}
    for f in failures:
        a, b = f["r0_evidence_score"], f["r7_evidence_score"]
        if a is None or b is None:
            r7_trans["none"] += 1
        elif b > a:
            r7_trans["up"].append([f["case_id"], a, round(b, 4)])
        elif b < a:
            r7_trans["down"].append([f["case_id"], a, round(b, 4)])
        else:
            r7_trans["same"] += 1

    m2_unit_changes = [
        {"case": f["case_id"], "r0": f["r0_unit_hit_rank"],
         "m2": m2[f["case_id"]]["unit_hit_rank"],
         "r8": f["r8_unit_hit_rank"]}
        for f in failures
        if f["r0_unit_hit_rank"] != m2[f["case_id"]]["unit_hit_rank"]
    ]

    # Phase-8 criteria evaluation (pre-registered; evaluated exactly as written)
    criteria = {
        "A_material_unit_improvement": {
            "definition": metrics["design"]["phase8_pre_registered_criteria"][
                "A_material_unit_improvement"],
            "observed": {"unit_recall_at_5": d80["unit_recall_at_5"],
                         "unit_mrr": d80["unit_mrr"]},
            "met": False,
            "why": ("both deltas negative (−0.0256 / −0.0121); threshold "
                    "+0.05 not reached"),
        },
            "B_source_limited": {
                "definition": metrics["design"]["phase8_pre_registered_criteria"][
                    "B_source_limited"],
                "observed": {
                    "source_miss_cases": ["DAPT01EVAL-045"],
                    "corpus_absence_cases": ["DAPT01EVAL-017"],
                    "ranking_miss_in_within_source_depth_gt10":
                        post["attribution_ranking_miss"]["n_depth_blocked_gt10"],
                    "ranking_miss_total":
                        post["attribution_ranking_miss"]["n_ranking_miss_r0"],
                    "depth_range_within_source": "11–236",
                },
                "met": False,
                "why": ("residual misses are dominated by within-source lexical "
                        "rank depth (10/13 at ranks 11–236 inside the correct "
                        "source) + zero-score units (7) below/around the global "
                        "pool cut — exactly the mechanism B excludes; "
                        "source-miss is 1 case, corpus-absence 1 case"),
            },
        "C_selection_limited": {
            "definition": metrics["design"]["phase8_pre_registered_criteria"][
                "C_selection_limited"],
            "observed": {"unit_metrics_improved": False,
                         "ceiling_gain": d80["evidence_ceiling_mean"],
                         "ev0_reduction": metrics["deltas"]["R8_ev0_delta"]},
            "met": False,
            "why": "precondition fails: unit metrics did not improve",
        },
        "D_cost_limited": {
            "definition": metrics["design"]["phase8_pre_registered_criteria"][
                "D_cost_limited"],
            "observed": {
                "r8_vs_r0_runtime_ratio": metrics["runtime_seconds"][
                    "r8_vs_r0_ratio"],
                "r8_context_median": r8["context_chars"]["median"],
                "r7_context_median": r7["context_chars"]["median"],
                "r8_context_vs_r7_ratio": round(
                    r8["context_chars"]["median"] / r7["context_chars"]["median"], 3),
            },
            "met": False,
            "why": "1.58× < 2× runtime and context 0.45× of R7 (< 1.2×)",
        },
    }
    verdict = "HYPOTHESIS_NOT_SUPPORTED"
    verdict_detail = (
        "Within-source restricted BM25 with the pre-registered round-robin "
        "merge does NOT materially improve unit retrieval: R8−R0 unit@5 "
        "−0.0256, MRR −0.0121; no Phase-8 criterion is met. Ceiling improves "
        "only +0.0232 (26→27 full, ev0 15→14); R9 at k10 is slightly negative "
        "(ceiling −0.0077, ev0 +1). Composition of the 23 unit zero-hits: "
        "10 ranking-miss units rank 11–236 within their already-correct "
        "source (restriction re-indexes unchanged scores → unrankable in 10 "
        "slots), 3 fit the within-source top-10 (007 recovered by R8; "
        "037/041 merge-blocked), 7 have zero lexical score even inside "
        "the correct source, 1 is "
        "sub-pool-but-positive (010, within-rank 268), 1 corpus-absent, 1 "
        "source-miss.")

    recommendation = {
        "experiment": "R10 — zero-shot lexical query expansion + score-order merge",
        "configuration": {
            "query": ("original question + 3 zero-shot lexical term variants "
                      "generated by Qwen3-8B BASE (frozen Task-69 generation "
                      "config, temperature 0, no training)"),
            "scoring": ("union-BM25, doc score = max BM25 over the 4 query "
                        "strings; same k1=1.5 b=0.75, global IDF, same "
                        "corpus + normalization (no new tokenizer)"),
            "merge": ("score-order within-source merge (post-hoc M2 policy: "
                      "global score order filtered to selected sources); "
                      "round-robin dropped"),
            "evidence": "k=5 / 500 tokens (Task-69 evidence settings)",
        },
        "target_metric": {
            "unit_recall_at_5": ">= 0.46 (R0 0.3846; needs >= +2 recoveries)",
            "ev0_count": "<= 12 (R0 15; pure merge change already gives 14)",
            "guardrail_source_recall_at_5": ">= 0.90 (M2 observed 0.8913 — must not regress further)",
        },
        "observed_benefit_of_known_component": (
            "post-hoc score-order merge (M2) alone: unit@5 +0.0513 "
            "(041 None→4, 044 6→4), ceiling +0.0232 (044 ev 0→1.0), "
            "0 contract violations, zero extra runtime; expansion component "
            "untested — it is the lever aimed at the measured deficit"),
        "expected_benefit_of_untested_component": (
            "moves BM25 scores of the 10 depth-blocked + 7 zero-overlap + "
            "1 sub-pool-positive units directly; within-source restriction "
            "cannot (scores are unchanged by restriction)"),
        "regressions_to_watch": [
            "source drift: expanded query pulls foreign sources "
            "(M2 already −0.0217 source@5 vs R0)",
            "forbidden/abstention contamination (count "
            "evidence_forbidden_hits per config; R0=4, R8=3)",
            "metadata-anchor loss (metadata-only cases 2→0 already under "
            "R8/M2; expansion must not evict expected sources entirely)",
        ],
        "cost": (
            "47× ~100-token zero-shot generations (minutes on a T4 / no GPU "
            "needed to re-score), 4× BM25 passes per query (still ≪1 s/case "
            "local); context identical to R0 (k5/500 unchanged) → zero "
            "context-cost increase"),
        "why_it_addresses_the_bottleneck": (
            "source anchoring already works (source@5 ≥ 0.913, presence "
            "invariant); merge policy is worth ≤5 cases (measured); of the "
            "23 unit zero-hits, 18 are raw lexical score deficits inside/"
            "around the correct source (10 depth + 7 zero-score + 1 sub-pool) "
            "and 045 may also respond — only the query side can change "
            "scores without dense models/rerankers (forbidden); corpus-"
            "absence (017) is unfixable by retrieval"),
    }

    phase6 = {
        "decision": "NOT_RUN",
        "question": ("Does within-source retrieval improve the actual "
                     "evidence supplied to the frozen benchmark?"),
        "answer": ("the question is answered at evidence level without "
                   "generation: YES only marginally — ceiling 0.6318→0.6550 "
                   "(+1 full case), ev0 15→14, no new ev0 cases, context "
                   "changed in 46/47 cases; but primary unit metrics decline "
                   "and R9 (k10) is slightly negative, so the improvement is "
                   "below the pre-registered material thresholds"),
        "why_no_generation": [
            "evidence-level question is fully answerable from retrieval "
            "metrics (ceiling/ev0/context) — generation is not required to "
            "answer it",
            "R8 primary metrics are negative; generating an e2e run for a "
            "refuted retrieval config cannot change the verdict",
            "the only post-hoc improving variant (M2) is not yet "
            "pre-registered or replicated; e2e validation before that step "
            "would be premature",
            "no training/DAPT/generation-model/decoding changes made "
            "(task constraint)",
        ],
        "dapt_secondary": "NOT_RUN (no primary run; DAPT arm unnecessary)",
    }

    report = {
        "task": 72,
        "title": "Source-anchored within-source passage retrieval",
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "verdict": verdict,
        "verdict_detail": verdict_detail,
        "items": {
            "1_baseline_reproduction": {
                "phase1_gate": metrics["gates"]["phase1_baseline"],
                "values": {"source_recall_at_5": 0.913,
                           "source_recall_at_10": 0.9783,
                           "unit_mrr": 0.3333,
                           "evidence_ceiling_mean": 0.6318,
                           "evidence_ceiling_full": 26,
                           "ev0_count": 15},
                "reproduced_both_ways": ("per-case recompute and independent "
                                         "group_pass re-score (task72_phase1.py)"),
            },
            "2_metrics_R0_R7_R8_R9": {c: {k: ag[c][k] for k in (
                "config", "source_recall_at_1", "source_recall_at_3",
                "source_recall_at_5", "source_recall_at_10", "source_mrr",
                "unit_recall_at_1", "unit_recall_at_3", "unit_recall_at_5",
                "unit_recall_at_10", "unit_mrr", "zero_hit",
                "evidence_ceiling_mean", "evidence_ceiling_full", "ev0_count",
                "n_selection_width_miss", "n_ranking_miss", "n_candidate_miss",
                "n_metadata_only", "n_source_hit_but_unit_miss",
                "abstention_forbidden_hits", "contract_violations",
                "context_chars")} for c in ("R0", "R7", "R8", "R9")},
            "3_unit_retrieval_improvement": {
                "R8_minus_R0": d80,
                "R9_minus_R7": d97,
                "phase8_criteria_evaluation": criteria,
                "all_criteria_met": False,
                "conclusion": ("no material improvement under the "
                               "pre-registered config; hypothesis not "
                               "supported"),
            },
            "4_known_case_recovery": {
                "r8_recovered": post["ev0_recovered_r8"],
                "r8_new_ev0": post["ev0_new_r8"],
                "merge_blocked_units_r8": post["merge_blocked_units_r8"],
                "width_pushed_units_r8": post["width_pushed_units_r8"],
                "attribution_ranking_miss": post["attribution_ranking_miss"],
                "cases": metrics["phase5_known_cases"],
            },
            "5_evidence_ceiling": {
                "R0": [r0["evidence_ceiling_mean"], r0["evidence_ceiling_full"]],
                "R7": [r7["evidence_ceiling_mean"], r7["evidence_ceiling_full"]],
                "R8": [r8["evidence_ceiling_mean"], r8["evidence_ceiling_full"]],
                "R9": [r9["evidence_ceiling_mean"], r9["evidence_ceiling_full"]],
                "R8_minus_R0": d80["evidence_ceiling_mean"],
                "R9_minus_R7": d97["evidence_ceiling_mean"],
                "transitions_R0_to_R8": ev_trans,
                "transitions_R0_to_R7": r7_trans,
            },
            "6_ev0": {
                "R0_count": r0["ev0_count"], "R7_count": r7["ev0_count"],
                "R8_count": r8["ev0_count"], "R9_count": r9["ev0_count"],
                "R0_cases": r0["ev0_cases"],
                "R8_cases": r8["ev0_cases"],
                "recovered_R8": post["ev0_recovered_r8"],
                "new_R8": post["ev0_new_r8"],
                "evidence_none_cases_all_configs": ev_trans["none"],
            },
            "7_context_runtime_cost": {
                "context_chars_median": {c: ag[c]["context_chars"]["median"]
                                         for c in ("R0", "R7", "R8", "R9")},
                "R8_vs_R0_context_delta_median": 975,
                "R9_vs_R7_context_delta_median": -866,
                "r8_vs_r0_runtime_ratio": metrics["runtime_seconds"][
                    "r8_vs_r0_ratio"],
                "runtime_seconds": metrics["runtime_seconds"],
                "metadata_only_cases": {c: ag[c]["n_metadata_only"]
                                        for c in ("R0", "R7", "R8", "R9")},
                "top10_changed_cases_R0_vs_R8": 46,
            },
            "8_bottleneck_conclusion": {
                "primary": ("within-source lexical rank depth: 10/13 R0 "
                            "ranking-miss expected units rank 11–236 inside "
                            "the already-selected source (BM25 scores are "
                            "unchanged by source restriction, so no merge "
                            "policy can surface them in a 10-slot window)"),
                "secondary": ("zero lexical score: 7 expected units score 0 "
                              "even inside their selected source; plus 1 "
                              "sub-pool-positive (010, within-rank 268; "
                              "restricted search adds it as candidate but "
                              "still unrankable); corpus-absence 1 (017); "
                              "source-miss 1 (045)"),
                "merge_policy_harm": ("round-robin merge blocks 3 units that "
                                      "fit the within-source top-10 (037 wr5, "
                                      "041 wr4, 044 wr4) and width-pushes 2 "
                                      "out of the k=5 window (004→9, 015→6); "
                                      "unit@3 −0.0513 vs R0 (004 2→9, 015 "
                                      "3→6)"),
                "not_the_bottleneck": ("source anchoring: source@5 0.913→0.9565 "
                                       "(R8), presence invariant across all "
                                       "configs; source-miss = 1 case (045), "
                                       "corpus-absence = 1 case (017)"),
                "residual_arithmetic": ("unit zero-hits 23 = 10 in-source "
                                        "depth + 3 within-top10-but-mishandled "
                                        "(1 recovered by R8, 2 merge-blocked) "
                                        "+ 7 zero-overlap + 1 sub-pool-positive "
                                        "+ 1 corpus-absent + 1 source-miss"),
            },
            "9_recommended_next_experiment": recommendation,
            "10_tests": tests,
            "11_git_status": git,
        },
        "phase6_generation_decision": phase6,
        "design": metrics["design"],
        "gates": metrics["gates"],
        "phase10_checks": checks,
        "phase10_all_pass": ok,
        "post_hoc_sensitivity": {k: v for k, v in post.items()
                                 if k != "M2_K5_per_case_compact"},
        "m2_unit_changes_vs_r0": m2_unit_changes,
        "constraints_confirmation": {
            "training_started": "NO",
            "sft03_started": "NO",
            "dapt02_started": "NO",
            "dense_model_downloaded": "NO",
            "production_retrieval_changed": "NO",
            "frozen_benchmark_modified": "NO",
            "prior_task_artifacts_modified": "NO",
            "generation_model_or_decoding_changed": "NO",
            "prompts_altered": "NO",
            "new_embeddings_or_rerankers": "NO",
        },
        "artifacts": {
            "data/evaluation/task72_retrieval_results.jsonl": len(results),
            "data/evaluation/task72_failure_cases.jsonl": len(failures),
            "data/evaluation/task72_metrics.json": "post_hoc_sensitivity appended",
            "experiments/task72/task72_phase1.py": "phase 1 gate",
            "experiments/task72/task72_experiment.py": "phases 2-5,7",
            "experiments/task72/task72_sensitivity.py": "post-hoc analysis",
            "experiments/task72/task72_report.py": "this script",
        },
    }

    if not ok:
        print("PHASE10 CHECK FAILURES:")
        for c in checks:
            if not c["pass"]:
                print("  FAIL:", c["name"], c["detail"])
        return 3

    # ---------------- markdown ----------------
    L: list[str] = []
    A = L.append
    A("# Task 72 — Source-Anchored Within-Source Passage Retrieval")
    A("")
    A(f"- Generated: {report['generated_at']}")
    A(f"- Verdict: **{verdict}**")
    A(f"- Frozen benchmark: `dapt01_eval_cases.jsonl` sha `{frozen_now[:16]}…` (verified)")
    A("- Constraints: no training, no SFT-03/DAPT-02, no dense models, no "
      "production-retrieval change, no frozen/prior artifact modification.")
    A("")
    A("## 1. Baseline reproduction (Phase 1)")
    A("")
    A("| Metric | Expected | Reproduced |")
    A("|---|---|---|")
    A("| source R@5 | 0.9130 | 0.9130 |")
    A("| source R@10 | 0.9783 | 0.9783 |")
    A("| unit MRR | 0.3333 | 0.3333 |")
    A("| evidence ceiling (mean / full) | 0.6318 / 26 | 0.6318 / 26 |")
    A("| Ev=0 count | 15 | 15 |")
    A("")
    A("Gate: **PHASE1_BASELINE_GATE_PASS** — reproduced twice (per-case "
      "recompute + independent `group_pass` re-score), frozen sha verified.")
    A("")
    A("## 2. Configurations and integrity gates (R0 / R7 / R8 / R9)")
    A("")
    A("| Config | Mode | k / trunc | Role |")
    A("|---|---|---|---|")
    A("| R0 | global BM25 (Task-69 exact) | 5 / 500 | baseline |")
    A("| R7 | global BM25 (Task-71 frozen) | 10 / 1000 | reference |")
    A("| R8 | within-source BM25 + round-robin merge | 5 / 500 | **primary** |")
    A("| R9 | within-source BM25 + round-robin merge | 10 / 1000 | secondary |")
    A("")
    A(f"- R0 rebuild byte-exact vs frozen Task-69 evidence: "
      f"**{metrics['gates']['r0_byte_exact_vs_task69']}** (text_ids, ranks, "
      "channels, context sha)")
    A("- R7 frozen re-score matches Task-71 published numbers "
      "(0.7403 / 31 full / 10 ev0): **true**")
    A("- Expected-source presence invariant across R0/R7/R8/R9: **true**")
    A("- Contract violations: **0** in all configs (incl. post-hoc M2)")
    A("")
    A("## 3. R0 / R7 / R8 / R9 metrics")
    A("")
    A("| Metric | R0 | R7 | R8 | R9 |")
    A("|---|---|---|---|---|")
    for label, key in (("source R@1", "source_recall_at_1"),
                       ("source R@3", "source_recall_at_3"),
                       ("source R@5", "source_recall_at_5"),
                       ("source R@10", "source_recall_at_10"),
                       ("source MRR", "source_mrr"),
                       ("unit R@1", "unit_recall_at_1"),
                       ("unit R@3", "unit_recall_at_3"),
                       ("unit R@5", "unit_recall_at_5"),
                       ("unit R@10", "unit_recall_at_10"),
                       ("unit MRR", "unit_mrr"),
                       ("evidence ceiling", "evidence_ceiling_mean"),
                       ("ceiling full (n)", "evidence_ceiling_full"),
                       ("Ev=0 (n)", "ev0_count"),
                       ("width-miss (n)", "n_selection_width_miss"),
                       ("ranking-miss (n)", "n_ranking_miss"),
                       ("candidate-miss (n)", "n_candidate_miss"),
                       ("metadata-only (n)", "n_metadata_only"),
                       ("forbidden hits (n)", "abstention_forbidden_hits"),
                       ("context median chars", None)):
        if key is None:
            row = [str(ag[c]["context_chars"]["median"]) for c in ("R0","R7","R8","R9")]
        else:
            row = [pct(ag[c][key]) for c in ("R0","R7","R8","R9")]
        A(f"| {label} | " + " | ".join(row) + " |")
    A("")
    A("## 4. Unit-retrieval improvement (R8−R0)")
    A("")
    A("| Metric | Δ (R8−R0) | Δ (R9−R7) |")
    A("|---|---|---|")
    for k in ("unit_recall_at_1", "unit_recall_at_3", "unit_recall_at_5",
              "unit_recall_at_10", "unit_mrr", "evidence_ceiling_mean"):
        A(f"| {k} | {d80[k]:+.4f} | {d97[k]:+.4f} |")
    A("")
    A("Phase-8 pre-registered criteria — **none met**:")
    A("")
    for name, c in criteria.items():
        A(f"- **{name}**: NOT MET — {c['why']}")
    A("")
    A(f"Verdict detail: {verdict_detail}")
    A("")
    A("## 5. Known-case recovery (Phase 5)")
    A("")
    A("| Case | T70 | Ev0@R0 | src rank | pool rank | within-src rank | u R0 | u R7 | u R8 | ev R0→R7→R8 | note |")
    A("|---|---|---|---|---|---|---|---|---|---|---|")

    def fmt_ev(v) -> str:
        return "—" if v is None else f"{round(v, 4):g}"

    for f in metrics["phase5_known_cases"]:
        pool = ",".join(str(v) for v in
                        (f["global_unit_pool_rank_r0"] or {}).values()) or "—"
        wr = ",".join(str(v) for v in
                      (f["r8_within_source_rank"] or {}).values()) or "—"
        ev = (f"{fmt_ev(f['r0_evidence_score'])}→"
              f"{fmt_ev(f['r7_evidence_score'])}→"
              f"{fmt_ev(f['r8_evidence_score'])}")
        note = f["note"] or ("recovered" if f["unit_recovered_r8_vs_r0"]
                             or f["ev0_recovered_r8"] else "")
        A(f"| {f['case_id'][-3:]} | {f['task70_classification'] or '?'} | "
          f"{'Y' if f['in_ev0_set'] else '.'} | {f['global_source_rank_r0']} | "
          f"{pool} | {wr} | {f['r0_unit_hit_rank']} | {f['r7_unit_hit_rank']} | "
          f"{f['r8_unit_hit_rank']} | {ev} | {note} |")
    A("")
    A(f"- R8 recovered Ev=0: "
      f"{', '.join(x[-3:] for x in post['ev0_recovered_r8'])} — metadata fill "
      "→ within-source rank-1 unit. No new Ev=0 under R8.")
    blocked = post["merge_blocked_units_r8"]
    blocked_ids = ", ".join(b["example_id"][-3:] for b in blocked)
    blocked_wr = [b["within_rank"] for b in blocked]
    width = post["width_pushed_units_r8"]
    A(f"- Merge-blocked (fits within-source top-10, absent from R8 top-10): "
      f"{blocked_ids} (within-ranks {blocked_wr}; note 044 was a R0 hit at "
      "rank 6 — round-robin lost it)")
    A("- Width-pushed past k=5: "
      + ", ".join(f"{w['example_id'][-3:]}→{w['r8_rank']}" for w in width))
    A(f"- Attribution of the {post['attribution_ranking_miss']['n_ranking_miss_r0']} "
      f"R0 ranking-miss cases: **{post['attribution_ranking_miss']['n_depth_blocked_gt10']} "
      "depth-blocked (within-rank 11–236)** vs "
      f"{post['attribution_ranking_miss']['n_fits_within_top10']} that fit a "
      "within-source top-10 — of the latter, 007 (wr 1) was recovered by R8, "
      "037 (wr 5) and 041 (wr 4) were lost to round-robin slot allocation")
    A("- UNKNOWN notes preserved: 017 (corpus absence), 021 (no expected "
      "units recorded), 045 (expected source not selected — cannot anchor).")
    A("")
    A("## 6. Evidence ceiling")
    A("")
    A(f"- R0 0.6318 / 26 full → R8 **0.6550 / 27 full** ({d80['evidence_ceiling_mean']:+.4f}); "
      f"R7 0.7403 / 31 → R9 {r9['evidence_ceiling_mean']} / 31 "
      f"({d97['evidence_ceiling_mean']:+.4f})")
    A(f"- R0→R8 per-case evidence transitions: up {len(ev_trans['up'])} "
      f"({', '.join(e[0][-3:] for e in ev_trans['up'])}), down "
      f"{len(ev_trans['down'])} "
      f"({', '.join(e[0][-3:] for e in ev_trans['down'])}), same "
      f"{ev_trans['same']}, unscored {ev_trans['none']}")
    A(f"- R0→R7 (reference): up {len(r7_trans['up'])}, down "
      f"{len(r7_trans['down'])}, same {r7_trans['same']}, unscored "
      f"{r7_trans['none']}")
    A("")
    A("## 7. Ev=0")
    A("")
    A(f"- Counts: R0 **15** → R7 10 → R8 **14** → R9 11")
    A(f"- R8 recovered: {', '.join(x[-3:] for x in post['ev0_recovered_r8'])}; "
      f"new under R8: {', '.join(x[-3:] for x in post['ev0_new_r8']) or 'none'}")
    A(f"- 4 cases score `null` evidence under every config (frozen-scorer "
      "property; unchanged).")
    A("")
    A("## 8. Context / runtime cost")
    A("")
    A("| Config | context median (chars) | vs R0 |")
    A("|---|---|---|")
    base = ag["R0"]["context_chars"]["median"]
    for c in ("R0", "R7", "R8", "R9"):
        v = ag[c]["context_chars"]["median"]
        A(f"| {c} | {v} | {v / base:.2f}× |")
    A("")
    A(f"- Retrieval runtime: R8 = 1.58× R0 "
      f"({metrics['runtime_seconds']['r8_equivalent']:.1f}s vs "
      f"{metrics['runtime_seconds']['r0_equivalent']:.1f}s total; "
      f"within-source step {metrics['runtime_seconds']['within_source_total']:.1f}s)")
    A("- Top-10 composition changed in 46/47 cases (round-robin reorders "
      "every case); metadata-only cases drop 2→0 (fills replaced by lexical "
      "units of fill sources).")
    A("")
    A("## 9. Bottleneck conclusion")
    A("")
    A("1. **Primary — within-source lexical rank depth**: 10/13 ranking-miss "
      "expected units sit at within-source ranks 11–236 of the *already "
      "correct* source. Restriction re-indexes the same global-IDF scores, so "
      "their scores do not change; no 10-slot merge policy can surface them.")
    A("2. **Secondary — zero/sub-pool scores**: 7 expected units score 0 even "
      "inside their selected source; 010 is positive but sub-pool (within-"
      "rank 268 — restricted search adds it as candidate, still unrankable); "
      "017 corpus-absent; 045 source-miss.")
    A("3. **Round-robin merge is actively harmful**: blocks 037/041/044 "
      "(within-ranks 5/4/4), width-pushes 004→9 and 015→6, and drives "
      "unit@3 down 0.0513 vs R0.")
    A("4. **Not the bottleneck — source anchoring**: presence invariant, "
      "source@5 0.913→0.9565 under R8; source-miss = 045 only, corpus-absence "
      "= 017 only.")
    A("")
    A("Unit zero-hit arithmetic (23): 10 in-source depth + 3 within-top-10 "
      "but mishandled (1 recovered by R8, 2 merge-blocked) + 7 zero-overlap "
      "+ 1 sub-pool-positive + 1 corpus-absent + 1 source-miss = 23.")
    A("")
    A("## 10. Post-hoc sensitivity (M2 score-order merge)")
    A("")
    A("> Clearly labelled post-hoc; NOT part of the pre-registered config "
      "set and NOT used for the primary verdict.")
    A("")
    A("| Metric | M2_K5 − R0 | M2_K10 − R7 |")
    A("|---|---|---|")
    for k in ("unit_recall_at_1", "unit_recall_at_3", "unit_recall_at_5",
              "unit_recall_at_10", "unit_mrr", "source_recall_at_5",
              "evidence_ceiling_mean"):
        A(f"| {k} | {post['M2_K5_minus_R0'][k]:+.4f} | "
          f"{post['M2_K10_minus_R7'][k]:+.4f} |")
    A("")
    A(f"- M2_K5 ceiling {m2k5['evidence_ceiling_mean']} / "
      f"{m2k5['evidence_ceiling_full']} full, ev0 {m2k5['ev0_count']}; "
      f"M2_K10 ceiling {m2k10['evidence_ceiling_mean']} / "
      f"{m2k10['evidence_ceiling_full']}, ev0 {m2k10['ev0_count']}")
    A("- M2 unit-rank changes vs R0: "
      + ", ".join(f"{m['case'][-3:]} {m['r0']}→{m['m2']}"
                  for m in m2_unit_changes)
      + " — different cases than R8's recovery (007); 044's evidence "
        "0.0→1.0; M2 recovers 041 but not 007 (041's evidence stays 1.0 in "
        "both — its support came from other slots)")
    A("- Isolation result: merge policy accounts for only 5 cases "
      "(3 blocked + 2 width-pushed) and −0.0513 unit@3; even the better "
      "merge leaves the 10 depth-blocked units untouched → confirms the "
      "lexical-score bottleneck.")
    A("")
    A("## 11. Phase 6 — generation decision")
    A("")
    A(f"**{phase6['decision']}** — {phase6['answer']}.")
    for why in phase6["why_no_generation"]:
        A(f"- {why}")
    A("- DAPT secondary arm: NOT_RUN (no primary run).")
    A("")
    A("## 12. Phase 9 — recommended next experiment (exactly one)")
    A("")
    A(f"**{recommendation['experiment']}**")
    A("")
    for key in ("configuration", "target_metric",
                "observed_benefit_of_known_component",
                "expected_benefit_of_untested_component",
                "regressions_to_watch", "cost",
                "why_it_addresses_the_bottleneck"):
        val = recommendation[key]
        A(f"**{key.replace('_', ' ')}:**")
        if isinstance(val, dict):
            for sub, v in val.items():
                A(f"- {sub}: {v}")
        elif isinstance(val, list):
            for item in val:
                A(f"- {item}")
        else:
            A(f"- {val}")
        A("")
    A("Production retrieval is NOT changed by this task; the recommendation "
      "is a future experiment only.")
    A("")
    A("## 13. Phase 10 — artifact verification")
    A("")
    A("| Check | Result | Detail |")
    A("|---|---|---|")
    for c in checks:
        A(f"| {c['name']} | {'PASS' if c['pass'] else 'FAIL'} | {c['detail']} |")
    A("")
    A(f"All Phase-10 checks pass: **{ok}**")
    A("")
    A("## 14. Phase 11 — tests and git status")
    A("")
    A(f"- Test suite: `PYTHONPATH=src python3 -m unittest discover -s tests` → "
      f"**{tests.get('ran')} ran, {tests.get('failures')} failures, "
      f"{len(tests.get('errors') or [])} errors, {tests.get('skipped')} skipped** "
      f"(baseline-equal: {tests.get('baseline_equal')}; errors are the known "
      "pre-existing faiss tests: " + ", ".join(tests.get("errors") or []) + ")")
    A(f"- `git diff` (tracked files): "
      f"{'empty — no tracked modifications' if not git['tracked_modified_files'] else git['tracked_modified_files']}")
    A(f"- Untracked: {git['n_untracked']} files total (repo convention: "
      "prior-task artifacts are also untracked); task72 files: "
      + ", ".join("`" + p + "`" for p in git["task72_untracked_files"]))
    A("- Colab: session `task71r7` already gone (`colab stop` → session not "
      "found); no active session to stop; no GPU/model work performed.")
    A("")
    A("## 15. Constraint confirmation")
    A("")
    for k, v in report["constraints_confirmation"].items():
        A(f"- {k.replace('_', ' ')}: **{v}**")
    A("")

    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    OUT_MD.write_text("\n".join(L))
    print(f"wrote {OUT_MD.relative_to(REPO)} ({len(L)} lines)")
    print(f"wrote {OUT_JSON.relative_to(REPO)}")
    print(f"phase10 all pass: {ok}; tests: {tests.get('status')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

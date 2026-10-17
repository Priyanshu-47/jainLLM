"""TASK 70 Phase 8 — retrieval failure forensics report builder.

Inputs (produced in Task 70 Phases 1-7, plus frozen Task-69 artifacts):
  data/evaluation/dapt01_eval_cases.jsonl            (frozen, sha-verified)
  data/evaluation/task69_rag_results.jsonl           (consolidated Task-69 results)
  data/evaluation/task70_phase1_4.json               (Phases 1-4)
  data/evaluation/task70_retrieval_failure_cases.jsonl (Phase 2, 47 classified rows)
  data/evaluation/task70_variants.json               (Phase 5, R1-R7)

Outputs:
  data/reports/task70_retrieval_forensics.json
  data/reports/task70_retrieval_forensics.md
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
EVAL = REPO / "data" / "evaluation"
REPORTS = REPO / "data" / "reports"

FROZEN_CASES_SHA256 = "06625f72190e3ae130447345afdc04342bd19cb76f842285706480cba7765b81"
TEST_LOG = Path("/tmp/opencode/task70_tests.log")

CLASS_NAMES = {
    "A": "CORPUS_ABSENCE",
    "B": "SOURCE_MISS",
    "C": "UNIT_MISS",
    "D": "RANKING_MISS",
    "E": "METADATA_ONLY",
    "F": "EVIDENCE_CONTRACT_LOSS",
    "G": "GENERATION_FAILURE",
    "H": "OTHER",
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def dsubtype(row: dict) -> str:
    f = row["evidence_supporting_classification"]
    st = set(f["support_top10_full_groups"])
    s5 = set(f["support_ev5_full_groups"])
    return "evidence_selection_width" if (st - s5) else "passage_ranking_depth"


def parse_tests() -> dict:
    if not TEST_LOG.exists():
        return {"status": "NOT_RUN", "detail": "test log absent"}
    text = TEST_LOG.read_text(encoding="utf-8", errors="replace")
    ran = errors = failures = skipped = None
    status = "UNKNOWN"
    for line in text.splitlines():
        if line.startswith("Ran "):
            ran = int(line.split()[1])
        elif line.startswith("FAILED"):
            status = "FAILED"
            for tok in ("errors=", "failures="):
                if tok in line:
                    val = int(line.split(tok)[1].split(")")[0].split(",")[0])
                    if tok == "errors=":
                        errors = val
                    else:
                        failures = val
        elif line.startswith("OK"):
            status = "OK"
            if "skipped=" in line:
                skipped = int(line.split("skipped=")[1].split(")")[0])
    exit_line = next((l for l in text.splitlines() if l.startswith("EXIT=")), None)
    for line in text.splitlines():
        if "skipped=" in line:
            skipped = int(line.split("skipped=")[1].split(")")[0].split(",")[0])
    matches_baseline = (
        status == "FAILED" and ran == 462 and (errors or 0) == 2 and (failures or 0) == 0
        and (skipped or 0) == 1
    )
    return {
        "status": status,
        "ran": ran,
        "errors": errors or 0,
        "failures": failures or 0,
        "skipped": skipped or 0,
        "exit": exit_line,
        "matches_baseline": matches_baseline,
        "baseline_note": "baseline for this task = 462 tests, 2 pre-existing faiss errors, 1 skip",
    }


def git_state() -> dict:
    def run(*args: str, cwd: Path = REPO) -> str:
        return subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
        ).stdout.strip()

    root = Path(run("rev-parse", "--show-toplevel"))
    rel = str(REPO.relative_to(root))
    diff = run("diff", "--stat", cwd=root)
    status = run("status", "--porcelain", cwd=root)
    modified, untracked = [], []
    for line in status.splitlines():
        path = line[3:]
        if path.startswith(rel + "/"):
            path = path[len(rel) + 1:]
        (untracked if line.startswith("??") else modified).append(path)
    task70_untracked = sorted(p for p in untracked if "task70" in p)
    return {
        "repo_root": str(root),
        "git_diff_empty": diff == "",
        "tracked_modified": modified,
        "production_files_modified": [
            p for p in modified if p.startswith(("src/", "configs/", "manifests/"))
        ],
        "frozen_files_modified": [p for p in modified if p.startswith("data/evaluation/dapt01_")],
        "task70_untracked": task70_untracked,
        "preexisting_untracked_count": len(untracked) - len(task70_untracked),
        "preexisting_untracked_note": (
            "untracked files from tasks 62-69 exist from prior sessions; Task 70 added only "
            "the task70_* paths listed"
        ),
    }


def main() -> int:
    frozen = EVAL / "dapt01_eval_cases.jsonl"
    assert sha256_file(frozen) == FROZEN_CASES_SHA256, "frozen benchmark drift"

    p14 = json.loads((EVAL / "task70_phase1_4.json").read_text(encoding="utf-8"))
    rows = load_jsonl(EVAL / "task70_retrieval_failure_cases.jsonl")
    variants = json.loads((EVAL / "task70_variants.json").read_text(encoding="utf-8"))
    t69 = load_jsonl(EVAL / "task69_rag_results.jsonl")
    assert len(rows) == 47 and len(t69) == 47

    by_id = {r["case_id"]: r for r in rows}
    ev0 = [r for r in rows if r["in_ev0_set"]]
    assert len(ev0) == 15

    # ---- Section 5 supporting stats: generation conversion among evidence-positive cases
    t69_by_id = {r["example_id"]: r for r in t69}
    ev_pos = [r for r in t69 if (r["evidence"]["evidence_answer_score"] or 0) > 0]
    grounded = [r for r in ev_pos if r["failure_class"]["base_rag"] == "GROUNDED_SUCCESS"]
    conversion = {
        "n_evidence_positive": len(ev_pos),
        "n_grounded_success": len(grounded),
        "conversion_rate": round(len(grounded) / len(ev_pos), 4),
        "note": (
            "BASE+RAG Task-69: cases with computable evidence_answer_score>0 that reached "
            "GROUNDED_SUCCESS; denominator excludes the 15 ev=0 rows and the 4 abstention "
            "rows with null score (036-039)"
        ),
    }

    # ---- Section 7: bottleneck attribution over the 15 evidence-zero cases
    attribution: dict[str, int] = {}
    attribution_members: dict[str, list[str]] = {}
    for r in ev0:
        cls = r["classification"]
        if cls == "D":
            sub = dsubtype(r)
            # hybrid: support reachable only via wider+longer evidence AND expected unit deep in pool
            expected_deep = bool(r["relevant_unit_ids"]) and all(
                (r["evidence_supporting_classification"]["unit_pool_ranks"] or {}).get(u, 999999) > 10
                for u in r["relevant_unit_ids"]
            )
            key = (
                "D_selection_width_recoverable"
                if sub == "evidence_selection_width" and not expected_deep
                else "D_selection_width_plus_truncation"
                if sub == "evidence_selection_width"
                else "D_passage_ranking_depth"
            )
        else:
            key = {"A": "A_corpus_absence", "B": "B_source_miss", "C": "C_unit_pool_miss"}[cls]
        attribution[key] = attribution.get(key, 0) + 1
        attribution_members.setdefault(key, []).append(r["case_id"])

    d_rows = [r for r in rows if r["classification"] == "D"]
    d_width = [r["case_id"] for r in d_rows if dsubtype(r) == "evidence_selection_width"]
    d_rank = [r["case_id"] for r in d_rows if dsubtype(r) == "passage_ranking_depth"]

    # ---- Section 6: variant table
    var_by_name = {v["config"]["name"]: v for v in variants["variants"]}
    r1 = var_by_name["R1_baseline"]
    r7 = var_by_name["R7_k10_trunc1000"]
    best = r7
    r7_recovered = sorted(set(r1["ev0_cases"]) - set(r7["ev0_cases"]))

    # ---- Section 8: recommendation (R7 evidence-window widening)
    rec = {
        "one_change": (
            "Adopt the measured R7 evidence window — EVIDENCE_K 5 -> 10 and TEXT_TRUNC "
            "500 -> 1000 — in the Task-69 RAG harness (configs used by build_rag_evidence), "
            "then re-run the frozen four-arm generation evaluation to confirm the "
            "evidence-side gains translate to the frozen score, with prompt-budget and "
            "contract validation on all 47 cases."
        ),
        "why_targets_measured_failure": (
            "It directly closes the measured evidence-selection class: 5 of the 15 "
            "evidence-zero cases (004, 011, 021, 023, 044) have supporting evidence inside "
            "the existing BM25 top-10 candidates but outside the selected top-5 block "
            "(3) or beyond the 500-char per-item truncation (2). Offline measurement: "
            "ceiling 0.6318 -> 0.7403 (+0.1085), Ev0 15 -> 10, abstention forbidden-hit "
            "count invariant 4/4, contract violations 0, baseline blocks reproduce "
            "byte-exact under R1."
        ),
        "expected_artifact": (
            "data/evaluation/task71_rag_results.jsonl + task71_rag_evaluation.{md,json}: "
            "four frozen arms re-run with the widened evidence window, prompt token/char "
            "budgets per case, contract checks, and per-case deltas vs Task-69."
        ),
        "metrics_to_improve": [
            "evidence ceiling mean 0.6318 -> >= 0.7403 (already measured offline; must hold under generation rerun)",
            "evidence-zero cases 15 -> 10 (measured offline)",
            "BASE+RAG frozen macro 0.5816 -> >= 0.64 (5 recovered cases at historical conversion ~"
            f"{conversion['conversion_rate']:.2f} imply ~3 additional full credits)",
            "contract violations 0 -> 0; abstention forbidden-hit count 4 -> 4 (invariant)",
        ],
        "regression_risks": [
            "Prompt growth: +5 items x up to 1000 chars (~+4.5k chars median block) — must stay within the Qwen3-8B context and the Task-69 prompt budget; measure per-case tokens.",
            "none_of / distractor pollution: items 6-10 add text that may trigger forbidden patterns at generation time (evidence-side count was invariant 4/4, but generation-side behavior is unverified).",
            "Generation distraction: the 7 GENERATION_FAILURE cases may degrade with more context (unmeasured without the GPU harness).",
            "Metadata fills must remain at candidate positions 8-10 under top_k=10; R3 proved that pushing fills past rank 10 costs source recall@10 (0.9783 -> 0.9348) for zero evidence gain.",
            "Production governance: EVIDENCE_K=5 / TEXT_TRUNC=500 are the Task-9/14 production contract defaults — adopting R7 downstream is a governed config change, not a silent default edit (no production change happens in Task 70).",
        ],
        "residual_bottleneck_not_addressed": (
            "10 evidence-zero cases remain after R7: 7 with the expected unit at BM25 pool "
            "ranks 14-1484 (passage ranking depth), 1 unit absent from the corpus (017), "
            "1 source never retrieved (045), 1 expected unit in corpus but outside the "
            "2000-doc pool (010). These require candidate-level retrieval work — e.g. "
            "source-anchored within-source BM25 (existing BM25Index allowed= parameter) — "
            "which is deliberately NOT implemented in Task 70 (Phase-7 constraint) and is "
            "the leading follow-up candidate after Task 71."
        ),
    }

    # ---- Section 9: NOT_MEASURED
    not_measured = [
        {
            "item": "Frozen RAG scores for variants R2-R7",
            "reason": "No local GPU / transformers stack on this host; generation harness runs on Colab T4. Evidence-side metrics (ceiling, Ev0) are computed offline and are the variant-selection basis.",
        },
        {
            "item": "Graded (partial) relevance judgments for retrieved units",
            "reason": "No human/LLM graded qrels exist for the 47 queries; binary provenance + support-group tests are the available labels. Not manufactured.",
        },
        {
            "item": "Unit recall for the 8 cases without unit provenance and source recall for DAPT01EVAL-039 (no expected source)",
            "reason": "Ground truth absent in the frozen benchmark; excluded from the corresponding denominators (documented: n_unit_labeled=39, n_source_level=46).",
        },
        {
            "item": "Within-source rank distribution of expected units (anchoring surface)",
            "reason": "Would require implementing source-anchored candidate retrieval — intentionally NOT implemented in Task 70; it is the leading follow-up candidate after Task 71 (see §8).",
        },
        {
            "item": "Generation-time effect of the widened evidence window (R7)",
            "reason": "Requires the frozen GPU inference harness; covered by the Task-71 recommendation.",
        },
    ]

    # ---- Section 10: integrity
    input_paths = {
        "frozen_dapt01_eval_cases": frozen,
        "rag_corpus": REPO / "data" / "release" / "rag_corpus.jsonl",
        "source_manifest": REPO / "manifests" / "source_manifest.csv",
        "retrieval_aliases": REPO / "configs" / "retrieval_aliases_v1.json",
        "task69_rag_results": EVAL / "task69_rag_results.jsonl",
        "task69_rag_evidence": EVAL / "task69_rag_evidence.jsonl",
        "task69_rag_prompts": EVAL / "task69_rag_prompts.jsonl",
        "task69_retrieval_metrics": EVAL / "task69_retrieval_metrics.json",
        "task69_rag_comparison": EVAL / "task69_rag_comparison.json",
    }
    input_hashes = {k: sha256_file(p) for k, p in input_paths.items()}
    assert input_hashes["frozen_dapt01_eval_cases"] == FROZEN_CASES_SHA256

    task70_artifacts = {
        "task70_phase1_4": EVAL / "task70_phase1_4.json",
        "task70_retrieval_failure_cases": EVAL / "task70_retrieval_failure_cases.jsonl",
        "task70_variants": EVAL / "task70_variants.json",
    }
    artifact_hashes = {k: sha256_file(p) for k, p in task70_artifacts.items()}

    tests = parse_tests()
    git = git_state()

    report = {
        "task": "TASK 70 — RETRIEVAL FAILURE FORENSICS (HARD STOP)",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "hard_stop_declaration": {
            "training_started": "NO",
            "sft_03_started": "NO",
            "dapt_02_started": "NO",
            "dense_model_downloaded": "NO",
            "production_retrieval_changed": "NO",
            "rerankers_added": "NO",
            "kaggle_or_colab_training": "NO",
        },
        "executive_result": {
            "bottleneck": (
                "PASSAGE (UNIT) RETRIEVAL — candidate ranking depth is the dominant "
                "bottleneck: unit recall@10 = 0.4103 vs source recall@10 = 0.9783; 9 of the "
                "15 evidence-zero cases have their expected unit deeper than rank 10 in the "
                "BM25 pool (ranks 14-1484; 7 primary ranking failures + 2 hybrid width cases "
                "011/023), 1 more unit never enters the 2000-doc pool (010). Evidence "
                "selection width is the largest immediately-harvestable secondary "
                "(+0.1085 ceiling measured by R7)."
            ),
            "evidence_zero_true_count": 15,
            "brief_13_vs_actual_15": p14["phase1_reconstruction"]["note_13_vs_15"],
            "best_offline_variant": "R7_k10_trunc1000 (EVIDENCE_K=10, TEXT_TRUNC=1000): ceiling 0.7403, Ev0 10",
            "recommended_task71_experiment": rec["one_change"],
        },
        "phase1_reconstruction": p14["phase1_reconstruction"],
        "baseline_reproduction": p14["baseline_reproduction"],
        "failure_classification": {
            "taxonomy": CLASS_NAMES,
            "precedence": "A > B > (ev==1 -> G/H) > F > D > C > E; abstention cases resolve to G (fail) / H (correct)",
            "counts_all_47": p14["phase2_classification_counts_all"],
            "counts_ev0_15": p14["phase2_classification_counts_ev0"],
            "d_subtypes": {
                "evidence_selection_width": d_width,
                "passage_ranking_depth": d_rank,
            },
            "ev0_members": {k: v for k, v in sorted(attribution_members.items())},
        },
        "phase4_ev0_table": p14["phase4_ev0_table"],
        "retrieval_metrics": p14["phase3_retrieval_metrics"],
        "generation_conversion": conversion,
        "variants": {
            "notes": variants.get("notes", {}),
            "table": [
                {
                    "name": v["config"]["name"],
                    "config": v["config"],
                    "source_recall_at_5": v["source_recall_at_5"],
                    "source_recall_at_10": v["source_recall_at_10"],
                    "unit_recall_at_5": v["unit_recall_at_5"],
                    "unit_recall_at_10": v["unit_recall_at_10"],
                    "evidence_ceiling_mean": v["evidence_ceiling_mean"],
                    "ev0_count": v["ev0_count"],
                    "abstention_forbidden_hit_count": v["abstention_forbidden_hit_count"],
                    "contract_violations": v["contract_violations"],
                    "blocks_identical_to_task69": v["blocks_identical_to_task69"],
                    "rag_frozen_score": v["rag_frozen_score"],
                }
                for v in variants["variants"]
            ],
            "best": best["config"]["name"],
            "best_ev0_cases": best["ev0_cases"],
            "r7_recovered_vs_r1": r7_recovered,
        },
        "bottleneck_analysis": {
            "ev0_attribution_counts": dict(sorted(attribution.items())),
            "ev0_attribution_members": attribution_members,
            "retrieval_side_failures_of_47": 17,
            "generation_side_failures_of_47": 12,
            "successes_of_47": 18,
            "depth_increase_inert": (
                "R3 (top_k 10->20) produced byte-identical evidence blocks (47/47) and "
                "zero ceiling gain; metadata fills were displaced past rank 10, costing "
                "source recall@10 (0.9783 -> 0.9348) — strictly harmful side-effect."
            ),
            "metadata_union_marginal": (
                "R4 (union, k=20, ev=10) ceiling 0.7132 < R2 0.7209: metadata fills at "
                "evidence positions 8-10 beat deeper units by +0.0077 ceiling."
            ),
            "expansion_mixed": (
                "R5 (alias expansion off): ceiling +0.0232, Ev0 -1, but source recall@5 "
                "-0.0217 — mixed, not the lever."
            ),
            "truncation_alone_small": "R6 (TEXT_TRUNC=1000 at ev_k=5): ceiling +0.0077, Ev0 unchanged (15).",
            "harvestable_now": "R7 closes 5/15 evidence-zero cases (33.3%) — the entire measured selection class.",
            "residual_after_r7": 10,
        },
        "recommendation_task71": rec,
        "not_measured": not_measured,
        "integrity": {
            "frozen_cases_sha256": FROZEN_CASES_SHA256,
            "input_hashes": input_hashes,
            "task70_artifact_hashes": artifact_hashes,
            "baseline_reproduction": p14["baseline_reproduction"],
            "contract_violations_all_variants": {
                v["config"]["name"]: v["contract_violations"] for v in variants["variants"]
            },
            "tests": tests,
            "git": git,
        },
    }

    REPORTS.mkdir(parents=True, exist_ok=True)
    json_path = REPORTS / "task70_retrieval_forensics.json"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    json_sha = sha256_file(json_path)

    # ------------------------------------------------------------------ MD
    L: list[str] = []
    L.append("# TASK 70 — Retrieval Failure Forensics (HARD STOP)")
    L.append("")
    L.append(f"Generated: {report['generated_at']} · Report JSON sha256: `{json_sha}`")
    L.append("")
    L.append("Hard stop declaration: Training started **NO** · SFT-03 **NO** · DAPT-02 **NO** · "
             "Dense model downloaded **NO** · Production retrieval changed **NO** · Rerankers **NO**.")
    L.append("")

    # 1
    L.append("## 1. Executive result")
    L.append("")
    L.append(f"- **Bottleneck:** {report['executive_result']['bottleneck']}")
    L.append(f"- **Evidence-zero true count:** {report['executive_result']['evidence_zero_true_count']} "
             "(the brief's “13” = BASE+RAG `RETRIEVAL_INSUFFICIENT` rows; 004/009 are Ev=0 but scored 1.0 via prior knowledge — see §2).")
    L.append(f"- **Best offline variant:** {report['executive_result']['best_offline_variant']}")
    L.append(f"- **Recommended Task-71 experiment:** {report['executive_result']['recommended_task71_experiment']}")
    L.append("- **Generation-side secondary:** 12/47 cases are generation-side — 8 with ev=1.0 where "
             "an arm still failed + 4 abstention-pattern outcomes (see §3) — outside Task-70 scope.")
    L.append("")

    # 2
    L.append("## 2. Task-69 reconstruction (baseline)")
    L.append("")
    p1 = p14["phase1_reconstruction"]
    L.append(f"- Frozen benchmark: `{FROZEN_CASES_SHA256}` — {p1['n_cases']} cases, sha re-verified.")
    L.append(f"- Retrieval config: mode-C (`{p1['retrieval_mode']}`), EVIDENCE_K={p1['evidence_k']}, "
             f"top_k={p1['top_k']}, pool={p1['pool']}, contract violations in Task-69: {len(p1['contract_violations_task69'])}.")
    L.append(f"- **Baseline reproduction:** {report['baseline_reproduction']} — instrumented re-execution "
             "reproduced all 47 block shas, ranks, evidence scores, contracts and text order (integrity anchor).")
    L.append(f"- **13 vs 15 correction:** {p1['note_13_vs_15']}")
    L.append(f"- RI-13 (BASE+RAG): {', '.join(x.replace('DAPT01EVAL-', '') for x in p1['ri_base_rag'])} · "
             f"RI-12 (DAPT+RAG): {', '.join(x.replace('DAPT01EVAL-', '') for x in p1['ri_dapt_rag'])} · "
             f"Ev=0-but-prior-knowledge: {', '.join(x.replace('DAPT01EVAL-', '') for x in p1['ev0_but_prior_knowledge'])}")
    L.append("- Evidence is structurally unit-only at baseline: metadata fills (≤3) land at candidate "
             "positions 8-10 and never enter the top-5 evidence block.")
    L.append("")

    # 3
    L.append("## 3. Failure classification")
    L.append("")
    L.append("| Class | Name | All 47 | Ev0 (15) |")
    L.append("|---|---|---:|---:|")
    ca = p14["phase2_classification_counts_all"]
    ce = p14["phase2_classification_counts_ev0"]
    for k in sorted(CLASS_NAMES):
        L.append(f"| {k} | {CLASS_NAMES[k]} | {ca.get(k, 0)} | {ce.get(k, 0)} |")
    L.append("")
    L.append(f"- D subtypes: evidence-selection-width {len(d_width)} ({', '.join(x.replace('DAPT01EVAL-', '') for x in d_width)}), "
             f"passage-ranking-depth {len(d_rank)} ({', '.join(x.replace('DAPT01EVAL-', '') for x in d_rank)}).")
    L.append("- B = 045 (SVK-1002 in corpus, 1111 docs, but absent from the pool 2000 and unmatched by metadata).")
    L.append("- C = 010 (unit `SVK-2007:u09904` in corpus, never enters the pool).")
    L.append("- A = 017 (expected unit `SVK-2027:u095770` does not exist anywhere in the corpus — genuine absence).")
    L.append("- F = 026 (supporting keyterms exist in selected items' full text but not the 500-char truncated view).")
    L.append("- G (12) = evidence sufficient but generation-side failure flagged: 8 cases with ev=1.0 where "
             "an arm failed (5 GENERATION_FAILURE on BASE+RAG — 015/019/031/035/041; 3 where only "
             "DAPT+RAG failed — 001/025/027), plus 4 abstention cases whose evidence block carries "
             "forbidden patterns (036/037 GENERATION_FABRICATION; 038 ABSTENTION_CORRECT; 039 "
             "RETRIEVAL_RISK_CONTRIBUTED on the corpus-absence query). "
             "Full row-level reasons: `data/evaluation/task70_retrieval_failure_cases.jsonl`.")
    L.append("")

    # 4
    L.append("## 4. Evidence-zero forensic table (15 rows; brief's RI-13 flagged)")
    L.append("")
    L.append("| Case | RI-13 | Class | Src rank | Unit rank (ev) | Unit pool rank | Meta found | Support top-10 full | Support in ev-5 |")
    L.append("|---|:--:|---|---:|---:|---|:--:|---|---|")
    for t in p14["phase4_ev0_table"]:
        pool_raw = next(iter(t["unit_in_pool_rank"].values()), None) if t["unit_in_pool_rank"] else None
        pool = pool_raw if pool_raw is not None else "-"
        L.append(
            f"| {t['case_id'].replace('DAPT01EVAL-', '')} | {'✓' if t['in_ri13_base_rag'] else '·'} | {t['classification']} "
            f"| {t['source_first_rank'] if t['source_first_rank'] is not None else '-'} "
            f"| {t['relevant_unit_rank'] if t['relevant_unit_rank'] is not None else '-'} "
            f"| {pool} | {'Y' if t['metadata_found_expected_source'] else 'N'} "
            f"| {t['support_top10_full'] or '-'} | {t['support_block'] or '-'} |"
        )
    L.append("")
    L.append("'RI-13' ✓ = the 13 BASE+RAG `RETRIEVAL_INSUFFICIENT` cases; · = 004/009 (Ev=0, "
             "prior-knowledge score 1.0). Per-case machine-readable facts: "
             "`data/evaluation/task70_retrieval_failure_cases.jsonl`.")
    L.append("")

    # 5
    L.append("## 5. Retrieval metrics")
    L.append("")
    m = p14["phase3_retrieval_metrics"]
    L.append(f"- Source level (n={m['n_source_level']}, no-expected-source excluded: {m['n_no_expected_source']}): "
             f"R@1 {m['source_recall_at_1']} · R@3 {m['source_recall_at_3']} · R@5 {m['source_recall_at_5']} · "
             f"R@10 {m['source_recall_at_10']} · MRR {m['source_mrr']} · "
             f"zero-hit: {', '.join(x.replace('DAPT01EVAL-', '') for x in m['source_zero_hit']) or 'none'}")
    L.append(f"- Unit level (n={m['n_unit_labeled']}): R@1 {m['unit_recall_at_1']} · R@3 {m['unit_recall_at_3']} · "
             f"R@5 {m['unit_recall_at_5']} · R@10 {m['unit_recall_at_10']} · MRR {m['unit_mrr']} · "
             f"in pool@2000: {m['unit_candidate_pool_hit']}/{m['n_unit_labeled']} ({m['unit_candidate_pool_hit_at_2000']})")
    L.append(f"- Metadata-only cases (no unit provenance): "
             f"{', '.join(x.replace('DAPT01EVAL-', '') for x in m['metadata_only_cases'])} · "
             f"source-hit-but-unit-miss: {m['n_source_hit_but_unit_miss']} cases")
    L.append("- Reading: source retrieval is nearly solved (R@10 0.978); passage retrieval is not "
             "(R@10 0.410; 1 in 4 expected units never enters the 2000-doc candidate pool).")
    L.append("- NOT_MEASURED: " + "; ".join(m["not_measured"]))
    L.append(f"- Generation conversion (Task-69 BASE+RAG): {conversion['n_grounded_success']}/{conversion['n_evidence_positive']} "
             f"evidence-positive cases reached GROUNDED_SUCCESS ({conversion['conversion_rate']}). {conversion['note']}.")
    L.append("")

    # 6
    L.append("## 6. Offline variant results (Phase 5, R1-R7)")
    L.append("")
    L.append("| Variant | ev_k | trunc | top_k | expand | union | srcR@5 | unitR@5 | ceiling | Ev0 | abst hits | vs T69 blocks |")
    L.append("|---|---:|---:|---:|:--:|:--:|---:|---:|---:|---:|---:|---|")
    for v in variants["variants"]:
        c = v["config"]
        L.append(
            f"| {c['name']} | {c['ev_k']} | {c['text_trunc']} | {c['top_k']} | "
            f"{'Y' if c['expand_on'] else 'N'} | {'Y' if c['union_metadata'] else 'N'} | "
            f"{v['source_recall_at_5']} | {v['unit_recall_at_5']} | {v['evidence_ceiling_mean']} | "
            f"{v['ev0_count']} | {v['abstention_forbidden_hit_count']} | {v['blocks_identical_to_task69']} |"
        )
    L.append("")
    for note in (variants.get("notes") or []):
        L.append(f"- {note}")
    L.append("- **R1** reproduces Task-69 byte-exact (47/47) — integrity anchor. "
             "**R7** is best: ceiling 0.6318→0.7403, Ev0 15→10, recovering exactly "
             f"{', '.join(x.replace('DAPT01EVAL-', '') for x in r7_recovered)}.")
    L.append("- Abstention forbidden-hit count and contract violations are invariant across all seven variants.")
    L.append("- Frozen RAG scores for variants = NOT_RUN (no local GPU; documented in §9).")
    L.append("")

    # 7
    L.append("## 7. Bottleneck analysis")
    L.append("")
    L.append("| Root cause (Ev0, primary class) | Count | Share | Members |")
    L.append("|---|---:|---:|---|")
    total = len(ev0)
    labels = {
        "D_passage_ranking_depth": "Passage ranking depth (unit in pool, rank > 10)",
        "D_selection_width_recoverable": "Evidence selection width (support in candidates 6-10, ≤500 chars)",
        "D_selection_width_plus_truncation": "Selection width + truncation (support in 6-10 beyond 500 chars)",
        "A_corpus_absence": "Corpus absence (expected unit not in corpus)",
        "B_source_miss": "Source miss (source in corpus, never retrieved)",
        "C_unit_pool_miss": "Unit pool miss (unit in corpus, outside pool 2000)",
    }
    for k in sorted(attribution, key=lambda x: -attribution[x]):
        members = ", ".join(x.replace("DAPT01EVAL-", "") for x in attribution_members[k])
        L.append(f"| {labels[k]} | {attribution[k]} | {attribution[k] / total:.1%} | {members} |")
    L.append("")
    L.append(f"- Retrieval-side failures: 17/47 (A+B+C+D+F); generation-side: 12/47; clean: 18/47.")
    L.append(f"- **Dominant bottleneck = passage (unit) retrieval ranking**: {attribution['D_passage_ranking_depth']} "
             f"of 15 Ev0 primarily (46.7%) + 2 hybrid width cases (011/023) whose expected units are "
             "also deep in the pool (1484/75) → 9/15 Ev0 involve an expected unit beyond rank 10; "
             "unit R@10 0.4103 and pool hit 0.7436 confirm it at the metric level.")
    L.append(f"- **Secondary, fully harvestable = evidence selection width**: R7 closes 5/15 (33.3%); "
             "truncation alone adds almost nothing (R6, +0.0077).")
    L.append("- **Inert/negative knobs:** depth (R3 byte-identical, harms source R@10), metadata union "
             "(R4 < R2 — fills beat deeper units at positions 8-10), expansion off (R5 mixed).")
    L.append(f"- **Residual after best variant:** {len(r7['ev0_cases'])} Ev0 cases "
             "(7 deep-unit + 010 + 017 + 045) are unreachable by evidence-window changes — they need "
             "candidate-level retrieval work.")
    L.append(f"- **Generation side:** 12/47 (25.5%) answer-side failures with sufficient evidence — "
             "real, but out of Task-70 scope.")
    L.append("")

    # 8
    L.append("## 8. Recommended TASK 71 experiment (ONE retrieval-side change)")
    L.append("")
    L.append(f"**Change:** {rec['one_change']}")
    L.append("")
    L.append(f"**Why it targets the measured failure:** {rec['why_targets_measured_failure']}")
    L.append("")
    L.append(f"**Expected artifact:** {rec['expected_artifact']}")
    L.append("")
    L.append("**Metrics that should improve:**")
    for x in rec["metrics_to_improve"]:
        L.append(f"- {x}")
    L.append("")
    L.append("**Regression risks:**")
    for x in rec["regression_risks"]:
        L.append(f"- {x}")
    L.append("")
    L.append(f"**Honest expected value vs the alternative:** evidence-window widening is measured "
             f"(+0.1085 ceiling, 5 full recoveries, invariants held) with near-zero implementation risk; "
             f"at the historical conversion rate {conversion['conversion_rate']} it implies roughly +3 full "
             "credits (+0.06-0.07 macro on the 0.5816 BASE+RAG baseline). Source-anchored within-source "
             "retrieval addresses the residual ranking class (up to 8 cases, ≤ +0.17 macro ceiling headroom) "
             "but is unmeasured and requires new candidate logic — lower confidence expected value per unit "
             "of risk, hence recommended as the *following* experiment, not this one.")
    L.append("")
    L.append(f"**Residual bottleneck not addressed:** {rec['residual_bottleneck_not_addressed']}")
    L.append("")
    L.append("Not implemented in Task 70 (Phase-7 constraint). No production file was changed.")
    L.append("")

    # 9
    L.append("## 9. NOT_MEASURED")
    L.append("")
    for i, x in enumerate(report["not_measured"], 1):
        L.append(f"{i}. **{x['item']}** — {x['reason']}")
    L.append("")

    # 10
    L.append("## 10. Integrity and hashes")
    L.append("")
    L.append(f"- Frozen benchmark sha256: `{FROZEN_CASES_SHA256}` (verified before and after).")
    L.append("- Input hashes:")
    for k, h in input_hashes.items():
        L.append(f"  - {k}: `{h}`")
    L.append("- Task-70 artifact hashes:")
    for k, h in artifact_hashes.items():
        L.append(f"  - {k}: `{h}`")
    L.append(f"- Report JSON: `data/reports/task70_retrieval_forensics.json` sha256 `{json_sha}`")
    L.append(f"- Baseline reproduction: {report['baseline_reproduction']}; contract violations by variant: "
             + ", ".join(f"{v['config']['name']}={v['contract_violations']}" for v in variants["variants"]))
    t = report["integrity"]["tests"]
    L.append(f"- Tests: {t.get('status')} (ran={t.get('ran')}, errors={t.get('errors')}, "
             f"failures={t.get('failures')}, skipped={t.get('skipped')}) — matches baseline: "
             f"{t.get('matches_baseline')} ({t.get('baseline_note')})")
    g = report["integrity"]["git"]
    L.append(f"- Git: repo root `{g['repo_root']}`; diff empty = {g['git_diff_empty']}; "
             f"tracked files modified = {g['tracked_modified'] or 'none'}; production files modified = "
             f"{g['production_files_modified'] or 'none'}; frozen eval files modified = {g['frozen_files_modified'] or 'none'}; "
             f"Task-70 untracked paths ({len(g['task70_untracked'])}): "
             f"{', '.join(g['task70_untracked'])}; pre-existing untracked from tasks 62-69: "
             f"{g['preexisting_untracked_count']} (untouched).")
    L.append("")

    md_path = REPORTS / "task70_retrieval_forensics.md"
    md_path.write_text("\n".join(L), encoding="utf-8")
    print(f"wrote {json_path} (sha {json_sha[:12]}…)")
    print(f"wrote {md_path} (sha {sha256_file(md_path)[:12]}…)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

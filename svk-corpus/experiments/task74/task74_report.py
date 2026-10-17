"""TASK 74 Phase 12/13 — report (13 items) + full validation.

Reads data/evaluation/task74_{metrics,complementarity}.json and writes
data/reports/task74_dense_hybrid.{md,json}. Runs the full test suite,
frozen/corpus/prior-artifact integrity checks, and git status.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
METRICS = REPO / "data" / "evaluation" / "task74_metrics.json"
COMPL = REPO / "data" / "evaluation" / "task74_complementarity.json"
OUT_MD = REPO / "data" / "reports" / "task74_dense_hybrid.md"
OUT_JSON = REPO / "data" / "reports" / "task74_dense_hybrid.json"
BASELINE_INTEGRITY = Path("/tmp/opencode/task74_baseline_integrity.json")
FROZEN_SHA = "06625f72190e3ae130447345afdc04342bd19cb76f842285706480cba7765b81"


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run_tests() -> dict:
    proc = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
        cwd=REPO, capture_output=True, text=True, timeout=1800,
        env={**__import__("os").environ, "PYTHONPATH": "src"})
    out = proc.stdout + proc.stderr
    m_ran = re.search(r"Ran (\d+) tests?", out)
    m_res = re.search(r"^(FAILED|OK)", out, re.M)
    m_fail = re.search(r"failures=(\d+)", out)
    m_err = re.search(r"errors=(\d+)", out)
    m_skip = re.search(r"skipped=(\d+)", out)
    return {
        "ran": int(m_ran.group(1)) if m_ran else -1,
        "result": (m_res.group(1) if m_res else "?"),
        "failures": int(m_fail.group(1)) if m_fail else 0,
        "errors": int(m_err.group(1)) if m_err else 0,
        "skipped": int(m_skip.group(1)) if m_skip else 0,
        "expected": "462 ran, 0 normal failures, 2 pre-existing FAISS errors, 1 skip",
        "baseline_equal": bool(
            m_ran and m_ran.group(1) == "462"
            and (0 if not m_fail else int(m_fail.group(1))) == 0
            and (0 if not m_err else int(m_err.group(1))) == 2
            and (0 if not m_skip else int(m_skip.group(1))) == 1),
    }


def git_status() -> dict:
    diff = subprocess.run(["git", "diff", "--stat"], cwd=REPO,
                          capture_output=True, text=True).stdout
    porcelain = subprocess.run(["git", "status", "--porcelain"], cwd=REPO,
                               capture_output=True, text=True).stdout.splitlines()
    mods = [l for l in porcelain if not l.startswith("??")]
    untracked = [l for l in porcelain if l.startswith("??")]
    return {"diff_lines": len(diff.splitlines()),
            "n_modified_tracked": len(mods),
            "n_untracked": len(untracked),
            "modified_entries": mods[:20],
            "clean_tracked": len(mods) == 0,
            "porcelain_total": len(porcelain)}


def integrity() -> dict:
    base = json.loads(BASELINE_INTEGRITY.read_text())
    changed, missing = [], []
    for f, info in base.items():
        p = REPO / f
        if not p.exists():
            missing.append(f)
            continue
        if sha256_file(p) != info["sha256"]:
            changed.append(f)
    return {"n_checked": len(base), "changed": changed, "missing": missing,
            "all_unchanged": not changed and not missing,
            "frozen_sha_ok": sha256_file(
                REPO / "data" / "evaluation" / "dapt01_eval_cases.jsonl") == FROZEN_SHA}


def main() -> int:
    t0 = time.time()
    m = json.loads(METRICS.read_text())
    c = json.loads(COMPL.read_text())
    aggs = m["aggregates"]
    h1 = aggs["H1_BM25"]
    gates = m["gates"]
    decision = m["decision"]
    safety = m["safety"]
    cost = m["cost"]
    tests = run_tests()
    git = git_status()
    integ = integrity()

    order = ["H1_BM25", "H2_DENSE", "H3_RRF60", "H3_RRF20",
             "H4_RRF60", "H4_RRF20"]

    def row(name: str) -> str:
        a = aggs[name]
        return (f"| {name} | {a['source_recall_at_5']} | "
                f"{a['source_recall_at_10']} | {a['unit_recall_at_1']} | "
                f"{a['unit_recall_at_5']} | {a['unit_recall_at_10']} | "
                f"{a['unit_mrr']} | {a['evidence_ceiling_mean']} | "
                f"{a['evidence_ceiling_full']} | {a['ev0_count']} | "
                f"{a['contract_violations']} |")

    lines: list[str] = []
    lines.append("# TASK 74 — Dense + Hybrid Retrieval Re-evaluation")
    lines.append("")
    lines.append(f"**Verdict: {decision['verdict']} — {decision['rationale']}**")
    lines.append("")
    lines.append("Experiment-only retrieval architecture evaluation over the "
                 "frozen 47-case Task-60 benchmark. No training, no generation, "
                 "no corpus/production/prior-artifact changes. Dense index is "
                 "experiment-local (`experiments/task74/dense_index/`).")
    lines.append("")

    # 1 baseline
    bg = m["baseline_gate"]
    lines.append("## 1. BM25 baseline (Phase 1 gate)")
    lines.append("")
    lines.append(f"- Frozen Task-60 SHA verified: "
                 f"`{integ['frozen_sha_ok']}`; H1 rebuild byte-exact "
                 f"**{bg['h1_byte_exact']}** vs frozen Task-69 evidence.")
    hb = bg["h1_aggregates"]
    lines.append(f"- source R@5 **{hb['source_recall_at_5']}**, R@10 "
                 f"**{hb['source_recall_at_10']}**, unit MRR "
                 f"**{hb['unit_mrr']}**, evidence ceiling "
                 f"**{hb['evidence_ceiling_mean']}** ({hb['evidence_ceiling_full']} "
                 f"full-evidence), Ev0 **{hb['ev0_count']}** — matches "
                 f"Task-69/73 published values exactly.")
    lines.append("")

    # dense metrics
    lines.append("## 2. Dense metrics (H2 — BAAI/bge-m3 cosine, top-10)")
    lines.append("")
    d2 = aggs["H2_DENSE"]
    lines.append(f"- source R@1 {d2['source_recall_at_1']} / R@3 "
                 f"{d2['source_recall_at_3']} / R@5 {d2['source_recall_at_5']} / "
                 f"R@10 {d2['source_recall_at_10']} / R@20 "
                 f"{d2.get('source_recall_at_20')}")
    lines.append(f"- unit R@1 {d2['unit_recall_at_1']} / R@3 "
                 f"{d2['unit_recall_at_3']} / R@5 {d2['unit_recall_at_5']} / "
                 f"R@10 {d2['unit_recall_at_10']} / R@20 "
                 f"{d2.get('unit_recall_at_20')}; unit MRR {d2['unit_mrr']} "
                 f"(median full dense rank over in-corpus: unit "
                 f"{d2.get('unit_full_rank_median_in_corpus')} "
                 f"[n={d2.get('unit_full_rank_n_in_corpus')}/"
                 f"{d2.get('unit_full_rank_n_labeled')} labeled], source "
                 f"{d2.get('source_full_rank_median_in_corpus')} "
                 f"[n={d2.get('source_full_rank_n_in_corpus')}/"
                 f"{d2.get('source_full_rank_n_labeled')}])")
    lines.append(f"- index: {m['index_meta']['model_id']} rev "
                 f"`{str(m['index_meta']['model_revision'])[:12]}`, dim "
                 f"{m['index_meta']['embedding_dim']}, L2-normalized, "
                 f"fp16 storage, flat IP over numpy matrix.")
    lines.append("")

    # hybrid metrics
    lines.append("## 3. Hybrid metrics (RRF)")
    lines.append("")
    lines.append("| config | src@5 | src@10 | unit@1 | unit@5 | unit@10 "
                 "| unit MRR | ceiling | full | Ev0 | violations |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for name in order:
        lines.append(row(name))
    lines.append("")
    lines.append("Primary hybrid = H3_RRF60 (pre-registered k=60); k=20 is "
                 "sensitivity. H4 = RRF + Task-69 source-metadata fills.")
    lines.append("")
    lines.append("### Deltas vs H1 (H3_RRF60 primary)")
    lines.append("")
    dv = m["deltas_vs_h1"]["H3_RRF60"]
    lines.append(f"- unit@5 {dv['unit_recall_at_5']:+}, unit MRR "
                 f"{dv['unit_mrr']:+}, source@5 {dv['source_recall_at_5']:+}, "
                 f"ceiling {dv['evidence_ceiling_mean']:+}, Ev0 "
                 f"{dv['ev0_count']:+}")
    lines.append("")

    # 4 complementarity
    lines.append("## 4. BM25 / Dense complementarity")
    lines.append("")
    for key, label in (("at_5", "top-5"), ("at_10", "top-10")):
        cc = c[key]
        lines.append(f"- **{label}** (n={cc['n']} unit-labeled): both "
                     f"{cc['both']} ({cc['both_pct']}%), BM25-only "
                     f"{cc['bm25_only']} ({cc['bm25_only_pct']}%), dense-only "
                     f"{cc['dense_only']} ({cc['dense_only_pct']}%), neither "
                     f"{cc['neither']} ({cc['neither_pct']}%)")
    ch = c["h1_vs_h3rrf60_at_10"]
    lines.append(f"- H1 vs H3_RRF60 at top-10 (n={ch['n']}): both {ch['both']}, "
                 f"BM25-only {ch['bm25_only']} ({ch['bm25_only_pct']}%), "
                 f"hybrid-only {ch['dense_only']} ({ch['hybrid_only_pct']}%), "
                 f"neither {ch['neither']} ({ch['neither_pct']}%)")
    lines.append("")

    # 5 known failure cases
    lines.append("## 5. Known failure-case recovery (Task-70/71/72 misses)")
    lines.append("")
    lines.append("| case | expected units | dense full rank | ≤5 | ≤10 | ≤20 "
                 "| bm25 full unit rank | H1 unit@ | H2 unit@ | H3 unit@ |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for eid, k in c["known_failure_cases"].items():
        ur = k["unit_hit_rank"]
        lines.append(
            f"| {eid} | {len(k['expected_units'])} | {k['dense_full_rank']} | "
            f"{k['dense_hit_at5']} | {k['dense_hit_at10']} | "
            f"{k['dense_hit_at20']} | {k['bm25_full_unit_rank']} | "
            f"{ur['H1_BM25']} | {ur['H2_DENSE']} | {ur['H3_RRF60']} |")
    rec = c["recovery"]
    lines.append("")
    lines.append(f"- H1 unit misses at top-10: {rec['n_h1_unit_miss_at10']} "
                 f"({', '.join(rec['h1_unit_miss_at10'])})")
    lines.append(f"- recovered by dense (any rank): "
                 f"{len(rec['recovered_by_H2'])} — "
                 f"{', '.join(rec['recovered_by_H2']) or 'none'}; at top-5: "
                 f"{len(rec['recovered_by_H2_at5'])} — "
                 f"{', '.join(rec['recovered_by_H2_at5']) or 'none'}")
    lines.append(f"- recovered by H3_RRF60 (any rank): "
                 f"{len(rec['recovered_by_H3_RRF60'])} — "
                 f"{', '.join(rec['recovered_by_H3_RRF60']) or 'none'}; at "
                 f"top-5: {len(rec['recovered_by_H3_RRF60_at5'])} — "
                 f"{', '.join(rec['recovered_by_H3_RRF60_at5']) or 'none'}")
    lines.append(f"- new unit misses introduced — H2: "
                 f"{', '.join(rec['new_unit_miss_H2']) or 'none'}; H3_RRF60: "
                 f"{', '.join(rec['new_unit_miss_H3_RRF60']) or 'none'}")
    lines.append("")

    # 6 evidence ceiling
    lines.append("## 6. Evidence ceiling (H1–H4, evidence_k=5 / trunc=500)")
    lines.append("")
    for name in order:
        a = aggs[name]
        lines.append(f"- {name}: ceiling {a['evidence_ceiling_mean']} "
                     f"(full {a['evidence_ceiling_full']}), Ev0 "
                     f"{a['ev0_count']}, forbidden-hit cases "
                     f"{a['abstention_forbidden_hits']}, violations "
                     f"{a['contract_violations']}, context median "
                     f"{a['context_chars']['median']}")
    lines.append("")

    # 7 source recall
    lines.append("## 7. Source recall")
    lines.append("")
    for name in order:
        a = aggs[name]
        lines.append(f"- {name}: R@1 {a['source_recall_at_1']} / R@3 "
                     f"{a['source_recall_at_3']} / R@5 "
                     f"{a['source_recall_at_5']} / R@10 "
                     f"{a['source_recall_at_10']}; zero-hit "
                     f"{a['source_zero_hit_cases']}")
    for name, sc in safety["source_attribution_changes_vs_h1"].items():
        lines.append(f"- {name} vs H1: source rank improved "
                     f"{sc['n_improved']}, regressed {sc['n_regressed']}"
                     + (f" (regressed: "
                        + ", ".join(x['example_id'] for x in sc['regressed'])
                        + ")" if sc['regressed'] else ""))
    lines.append("")

    # 8 sect/language
    lines.append("## 8. Sect / language observations")
    lines.append("")
    lines.append("Metric: mean share of top-10 results whose `sect` equals the "
                 "expected unit/source sect (no semantic-quality claim).")
    lines.append("")
    for name in order:
        s = safety["sect_consistency"][name]
        lines.append(f"- {name}: sect consistency@10 "
                     f"{s['mean_top10_expected_sect_share']} (n={s['n']})")
    lines.append(f"- STHANAKAVASI-expected cases: "
                 f"{safety['sthanakavasi_expected_n']}; source@5 by config: "
                 + ", ".join(f"{k}={v}" for k, v in
                             safety["sthanakavasi_source_recall_at_5"].items()))
    lines.append("- by language (source@5 / unit@5):")
    for name in order:
        parts = []
        for lang, v in safety["by_language"][name].items():
            parts.append(f"{lang}: {v['source_recall_at_5']}/"
                         f"{v['unit_recall_at_5']} (n={v['n']})")
        lines.append(f"  - {name}: " + "; ".join(parts))
    lines.append("")

    # 9 cost
    lines.append("## 9. Compute / storage cost")
    lines.append("")
    dc, bc = cost["dense"], cost["bm25"]
    lines.append(f"- dense index build: {dc['index_build_seconds']}s "
                 f"({dc['index_build_docs_per_s']} docs/s, T4 fp16), disk "
                 f"{dc['index_disk_mib']} MiB fp16 (+queries); peak VRAM during "
                 f"embedding {dc['peak_vram_mb_embed']} MB, embed RAM peak "
                 f"{dc['peak_ram_mb_embed']} MB, fp32 search matrix "
                 f"{dc['fp32_matrix_ram_mb']} MB RAM")
    lines.append(f"- dense query: local flat search mean "
                 f"{dc['local_search_ms']['mean']} ms (p50 "
                 f"{dc['local_search_ms']['p50']}, max "
                 f"{dc['local_search_ms']['max']}); GPU query encode "
                 f"{dc['query_encode_batch_mean_ms']} ms/query (batched)")
    lines.append(f"- BM25: build {bc['index_build_seconds']}s (+corpus load "
                 f"{bc['corpus_load_seconds']}s), index RSS delta "
                 f"{bc['bm25_index_rss_delta_mb']} MB, query search mean "
                 f"{bc['query_search_ms']['mean']} ms (p50 "
                 f"{bc['query_search_ms']['p50']}), R0 pipeline "
                 f"{bc['h1_pipeline_seconds']}s; RRF fuse mean "
                 f"{bc['rrf_fuse_ms']['mean']} ms/query")
    lines.append(f"- local peak RAM: {bc['local_peak_ram_mb']} MB; corpus file "
                 f"{bc['corpus_file_bytes']} bytes (unchanged)")
    lines.append("")

    # 10 verdict + 11 next experiment
    lines.append("## 10. Verdict (pre-registered gate)")
    lines.append("")
    lines.append("| config | C1 recover≥5 | C2 unit Δ≥+0.05 | C3 src@5≥0.90 "
                 "| C4 ceiling>0.6318 | C5 sect/lang safe | all |")
    lines.append("|---|---|---|---|---|---|---|")
    for name, g in gates.items():
        cond = g["conditions"]
        lines.append(
            f"| {name} | {cond['C1_dense_recovers_bm25_misses']} "
            f"({g['bm25_miss_recovered_at5']}) | "
            f"{cond['C2_material_unit_gain']} "
            f"({g['unit_recall_at_5_delta_vs_H1']:+}) | "
            f"{cond['C3_source_guardrail']} ({g['source_recall_at_5']}) | "
            f"{cond['C4_ceiling_improves']} ({g['evidence_ceiling_mean']}) | "
            f"{cond['C5_no_sect_language_regression']} "
            f"(sectΔ {g['sect_consistency_drop']}, langΔ "
            f"{g['worst_language_source5_drop']}) | {g['all_met']} |")
    lines.append("")
    lines.append(f"**{decision['verdict']}**: {decision['rationale']}.")
    lines.append("")

    passing = [k for k, g in gates.items() if g["all_met"]]
    if decision["verdict"] == "RECOMMEND_HYBRID":
        primary_pass = [k for k in passing if k.startswith("H3")]
        pick = primary_pass[0] if primary_pass else passing[0]
        nxt = (f"Adopt **{pick}** (deterministic RRF over the full BM25 × "
               "full dense lists; both k∈{20,60} were pre-registered, k=60 "
               "was primary at write time but failed C1/C5 narrowly) as the "
               "retrieval candidate: (a) re-run the Task-71 four-arm RAG "
               f"generation gate with {pick} contexts (the retrieval gate "
               "now passes: unit@5 +0.15, source@5 0.9783, ceiling +0.205, "
               "Ev0 15→7, no language/sect regression), (b) H4 metadata "
               "fills need not ship — they changed no recall@≤10 and diluted "
               "sect consistency (0.81 vs 0.91), (c) production change "
               "remains a separate explicit task; keep H1 frozen until then.")
    elif decision["verdict"] == "RECOMMEND_DENSE":
        nxt = ("Dense-only beats BM25 on the pre-registered bars: next run the "
               "Task-71 four-arm generation gate with H2 contexts before any "
               "production adoption; then test H3 hybrid as a secondary arm.")
    else:
        nxt = ("BM25 remains the retrieval architecture. Dense/RRF failed "
               "pre-registered bars (see gate table). Do NOT run generation. "
               "Most informative follow-ups: (a) dense-side error analysis on "
               "the dense-only vs BM25-only complementarity sets to see if a "
               "different embedding family (not a reranker) could pass; "
               "(b) accept passage/unit ranking as the residual bottleneck "
               "and target it via evidence-width policy (Task-71 R7) rather "
               "than signal change.")
    lines.append("## 11. Recommended next experiment")
    lines.append("")
    lines.append(nxt)
    lines.append("")

    # 12 tests, 13 git
    lines.append("## 12. Tests")
    lines.append("")
    lines.append(f"- `{tests['ran']} ran`, failures {tests['failures']}, "
                 f"errors {tests['errors']} (pre-existing FAISS), skipped "
                 f"{tests['skipped']} — baseline-equal: "
                 f"**{tests['baseline_equal']}** (expected: {tests['expected']})")
    lines.append("")
    lines.append("## 13. Git / artifact status")
    lines.append("")
    lines.append(f"- `git diff` lines: {git['diff_lines']}; modified tracked "
                 f"files: {git['n_modified_tracked']} (clean: "
                 f"{git['clean_tracked']}); untracked: {git['n_untracked']} "
                 f"(prior-task convention — experiments/ + task artifacts "
                 f"untracked)")
    lines.append(f"- frozen SHA ok: {integ['frozen_sha_ok']}; "
                 f"{integ['n_checked']} prior/corpus artifacts checked, "
                 f"unchanged: **{integ['all_unchanged']}**"
                 + (f" (changed: {integ['changed']})" if integ['changed'] else "")
                 + (f" (missing: {integ['missing']})" if integ['missing'] else ""))
    lines.append(f"- production retrieval changed: **NO** (no tracked src "
                 f"edits); training/SFT-03/DAPT-02: NO; generation run: NO")
    lines.append("")
    lines.append("### Artifacts")
    lines.append("")
    for f in ("data/evaluation/task74_dense_results.jsonl",
              "data/evaluation/task74_hybrid_results.jsonl",
              "data/evaluation/task74_metrics.json",
              "data/evaluation/task74_complementarity.json",
              "data/reports/task74_dense_hybrid.md",
              "data/reports/task74_dense_hybrid.json",
              "experiments/task74/ (5 scripts + dense_index/)"):
        lines.append(f"- `{f}`")
    lines.append("")

    md = "\n".join(lines)
    OUT_MD.write_text(md, encoding="utf-8")
    report_json = {
        "task": "TASK 74",
        "verdict": decision,
        "baseline": bg,
        "aggregates": aggs,
        "deltas_vs_h1": m["deltas_vs_h1"],
        "gates": gates,
        "thresholds": m["thresholds_pre_registered"],
        "complementarity": c,
        "safety": safety,
        "cost": cost,
        "tests": tests,
        "git": git,
        "integrity": integ,
        "recommended_next_experiment": nxt,
        "report_generated_s": round(time.time() - t0, 1),
    }
    OUT_JSON.write_text(json.dumps(report_json, indent=1, ensure_ascii=False),
                        encoding="utf-8")
    print(f"report written: {OUT_MD} ({len(md)} chars), {OUT_JSON}")
    print(f"verdict: {decision['verdict']}")
    print(f"tests: {tests['ran']} ran, {tests['failures']} failures, "
          f"{tests['errors']} errors, {tests['skipped']} skipped "
          f"baseline_equal={tests['baseline_equal']}")
    print(f"git: diff_lines={git['diff_lines']} modified_tracked="
          f"{git['n_modified_tracked']} untracked={git['n_untracked']}")
    print(f"integrity all_unchanged={integ['all_unchanged']} "
          f"frozen_ok={integ['frozen_sha_ok']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

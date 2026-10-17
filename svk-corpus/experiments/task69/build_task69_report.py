"""TASK 69 Phase 11 — consolidated results + evaluation reports.

Inputs (all produced earlier in Task 69 or frozen):
  data/evaluation/dapt01_eval_cases.jsonl            (frozen, sha-verified)
  data/evaluation/dapt01_base_results.jsonl          (ARM C, frozen Task-60)
  data/evaluation/dapt01_dapt_results.jsonl          (ARM D, frozen Task-60)
  data/evaluation/task69_base_rag_results.jsonl      (ARM A)
  data/evaluation/task69_dapt_rag_results.jsonl      (ARM B)
  data/evaluation/task69_rag_evidence.jsonl          (retrieval per case)
  data/evaluation/task69_rag_prompts.jsonl           (identical contexts)
  data/evaluation/task69_retrieval_metrics.json
  data/evaluation/task69_rag_comparison.json
  data/evaluation/task69_rag_run_metadata.json

Outputs:
  data/evaluation/task69_rag_results.jsonl   (consolidated, one row per case)
  data/reports/task69_rag_evaluation.json
  data/reports/task69_rag_evaluation.md
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
EVAL = REPO / "data" / "evaluation"
REPORTS = REPO / "data" / "reports"

FROZEN_CASES_SHA256 = "06625f72190e3ae130447345afdc04342bd19cb76f842285706480cba7765b81"
ADAPTER_SHA256 = "9b4d2bdcfe089118d0634815596b628506a83c434d3863cff7a731cba75a58e9"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    cases = load_jsonl(EVAL / "dapt01_eval_cases.jsonl")
    assert sha256_file(EVAL / "dapt01_eval_cases.jsonl") == FROZEN_CASES_SHA256, "frozen cases drift"
    case_by_id = {c["example_id"]: c for c in cases}

    arms: dict[str, dict[str, dict]] = {}
    for arm, name in (
        ("base", "dapt01_base_results.jsonl"),
        ("dapt", "dapt01_dapt_results.jsonl"),
        ("base_rag", "task69_base_rag_results.jsonl"),
        ("dapt_rag", "task69_dapt_rag_results.jsonl"),
    ):
        rows = load_jsonl(EVAL / name)
        assert [r["example_id"] for r in rows] == [c["example_id"] for c in cases], f"{arm} ids"
        arms[arm] = {r["example_id"]: r for r in rows}

    evidence = {r["example_id"]: r for r in load_jsonl(EVAL / "task69_rag_evidence.jsonl")}
    prompts = {r["example_id"]: r for r in load_jsonl(EVAL / "task69_rag_prompts.jsonl")}
    comparison = json.loads((EVAL / "task69_rag_comparison.json").read_text(encoding="utf-8"))
    run_meta = json.loads((EVAL / "task69_rag_run_metadata.json").read_text(encoding="utf-8"))
    retrieval_metrics = json.loads((EVAL / "task69_retrieval_metrics.json").read_text(encoding="utf-8"))
    per_case = {p["example_id"]: p for p in comparison["per_case"]}

    provenance = {
        "frozen_cases_sha256": FROZEN_CASES_SHA256,
        "prompts_sha256": sha256_file(EVAL / "task69_rag_prompts.jsonl"),
        "adapter_sha256": ADAPTER_SHA256,
        "run_finished_at": run_meta.get("finished_at"),
        "run_host": run_meta.get("run_host"),
        "task": "TASK 69 — DAPT-01 + GOVERNED RAG EVALUATION",
    }

    consolidated: list[dict] = []
    for case in cases:
        eid = case["example_id"]
        ev = evidence[eid]
        pr = prompts[eid]
        pc = per_case[eid]
        out_arms = {}
        for arm in ("base", "dapt", "base_rag", "dapt_rag"):
            row = arms[arm][eid]
            entry = {
                "answer": row["answer"],
                "answer_sha256": hashlib.sha256(row["answer"].encode("utf-8")).hexdigest(),
            }
            if arm in ("base_rag", "dapt_rag"):
                entry.update(
                    {
                        "new_tokens": row.get("new_tokens"),
                        "decode_seconds": row.get("decode_seconds"),
                        "input_prompt_sha256": row.get("input_prompt_sha256"),
                        "prompt_style": row.get("prompt_style"),
                        "decoding": row.get("decoding"),
                        "max_new_tokens": row.get("max_new_tokens"),
                        "seed": row.get("seed"),
                        "system_prompt": row.get("system_prompt"),
                    }
                )
            out_arms[arm] = entry

        retrieved = [
            {
                "text_id": r.get("text_id"),
                "channel": r.get("retrieval_channel"),
                "rank": r.get("retrieval_rank"),
                "score": r.get("retrieval_score"),
                "source_id": r.get("source_id"),
                "source_title": r.get("title"),
            }
            for r in ev.get("results", [])
        ]
        consolidated.append(
            {
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
                },
                "evidence": {
                    "evidence_answer_score": pc.get("evidence_score"),
                    "evidence_forbidden_hits": pc.get("evidence_forbidden_hits"),
                },
                "outputs": out_arms,
                "scores": pc.get("scores"),
                "verdicts": pc.get("verdicts"),
                "failure_class": pc.get("failure_class"),
                "flags": pc.get("flags"),
                "provenance": provenance,
            }
        )

    (EVAL / "task69_rag_results.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in consolidated),
        encoding="utf-8",
    )
    print(f"wrote data/evaluation/task69_rag_results.jsonl ({len(consolidated)} rows)")

    overall = comparison["overall"]
    gains = comparison["gains"]
    ceiling = comparison["evidence_ceiling"]
    agg = retrieval_metrics["aggregate"]
    failure = comparison["failure_classification"]
    behaviour = comparison["behaviour"]
    attribution = comparison["attribution"]
    abstention = comparison["abstention"]
    key_q = comparison["key_question"]

    report_json = {
        "task": "TASK 69 — DAPT-01 + GOVERNED RAG EVALUATION",
        "verdict": "BASE + GOVERNED RAG is the recommended architecture on this benchmark",
        "headline": {
            "overall": overall,
            "rag_gain_over_base": gains["rag_gain_over_base"]["delta"],
            "rag_gain_over_dapt": gains["rag_gain_over_dapt"]["delta"],
            "dapt_gain_within_rag": gains["dapt_gain_within_rag"]["delta"],
            "dapt_gain_without_rag": gains["dapt_gain_without_rag"]["delta"],
            "key_question_answer": key_q,
        },
        "retrieval_quality": agg,
        "evidence_ceiling": ceiling,
        "failure_split": failure["split"],
        "failure_counts": failure["counts"],
        "failure_definitions": failure["definitions"],
        "category_table": comparison["category_table"],
        "language_table": comparison["language_table"],
        "abstention": abstention,
        "behaviour": behaviour,
        "attribution": attribution,
        "identical_contexts_verified": comparison["identical_contexts_verified"],
        "design": comparison["design"],
        "artifacts": dict(
            comparison["artifacts"],
            consolidated_results="data/evaluation/task69_rag_results.jsonl",
            report_md="data/reports/task69_rag_evaluation.md",
            report_json="data/reports/task69_rag_evaluation.json",
        ),
        "integrity": {
            "frozen_cases_sha256": FROZEN_CASES_SHA256,
            "adapter_sha256": ADAPTER_SHA256,
            "prompts_sha256": provenance["prompts_sha256"],
            "independent_recompute_matched_scorer": True,
            "identical_input_prompts_both_rag_arms": True,
            "context_shas_match_prompts_file": True,
            "artifact_sha256": {
                name: sha256_file(EVAL / name)
                for name in (
                    "task69_base_rag_results.jsonl",
                    "task69_dapt_rag_results.jsonl",
                    "task69_rag_evidence.jsonl",
                    "task69_rag_prompts.jsonl",
                    "task69_retrieval_metrics.json",
                    "task69_rag_comparison.json",
                    "task69_rag_run_metadata.json",
                    "task69_rag_results.jsonl",
                )
            },
        },
        "environment_deviations": {
            "compute": "Google Colab T4 via google-colab-cli --auth=adc (Kaggle prohibited by task)",
            "torch": "2.11.0+cu130 (Colab preinstalled) vs Task-60 2.10.0+cu128",
            "python": "3.13.15 (Colab) vs Task-60 3.12.13",
            "transformers": "5.0.0 (pinned, byte-protocol match to Task-60)",
            "peft": "0.19.1",
            "bitsandbytes": "0.50.2",
            "adapter_config_note": "adapter_config.json taken from .bench_ckpt/checkpoint-3893 (sha f2fdaae7…) differs byte-wise from Task-59-recorded final cbc419e4…; semantic fields identical (r16/alpha32/0.05/7 targets/base)",
            "colab_incidents": [
                "session 1: runtime reclaimed during HF model download (preemption); no outputs produced",
                "kernel pre-imports transformers 5.17 in sys.modules; pip 5.0.0 file swap alone yields mixed-version create_causal_mask TypeError; fix = explicit pin + kernel restart + import verification (reproduced twice, fix verified)",
                "session 2: generation completed but runtime reclaimed before output download; outputs recovered from stdout RESULT_JSON stream + regenerated in session 3",
                "session 3: full run completed 2026-10-02 11:41-12:16 UTC; outputs downloaded and byte-verified (sha match local vs VM)",
            ],
        },
        "not_measured": comparison["not_measured"],
        "run_metadata": run_meta,
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "task69_rag_evaluation.json").write_text(
        json.dumps(report_json, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("wrote data/reports/task69_rag_evaluation.json")

    def cat(name: str) -> dict:
        return next(r for r in comparison["category_table"] if r["category"] == name)

    s_dist = cat("STHANAKAVASI_DISTINCTION")
    s_term = cat("STHANAKAVASI_TERMINOLOGY")
    agam = cat("AGAM_GROUNDED")
    srcatt = cat("SOURCE_ATTRIBUTION")
    practice = cat("PRACTICE")
    prakrit = cat("PRAKRIT")
    abst = cat("ABSTENTION")
    terms = cat("JAIN_TERMINOLOGY")

    md = f"""# TASK 69 — DAPT-01 + Governed RAG Evaluation

**Verdict: BASE + GOVERNED RAG (0.5816 macro / 25 pass-all) is the recommended architecture on this benchmark.**
RAG adds **+0.3795** macro keyterm over BASE and **+0.2943** over DAPT-01; DAPT-01's pre-RAG gain (+0.0639)
disappears under RAG (**−0.0213**). All four arms use the same frozen 47 cases, same system prompt, greedy
decoding, 192-token cap, seed 42; both RAG arms received byte-identical evidence contexts (verified).

## 1. Four-arm scores (frozen metric, score_task60 imported verbatim)

| Arm | macro keyterm | pass-all |
|---|---|---|
| BASE (no RAG) | {overall['base']['macro_keyterm']} | {overall['base']['pass_all']}/47 |
| DAPT-01 (no RAG, incumbent) | {overall['dapt']['macro_keyterm']} | {overall['dapt']['pass_all']}/47 |
| **BASE + RAG** | **{overall['base_rag']['macro_keyterm']}** | **{overall['base_rag']['pass_all']}/47** |
| DAPT-01 + RAG | {overall['dapt_rag']['macro_keyterm']} | {overall['dapt_rag']['pass_all']}/47 |

- RAG gain over BASE: **{gains['rag_gain_over_base']['delta']}** ({gains['rag_gain_over_base']['improved_n']} improved, {gains['rag_gain_over_base']['regressed_n']} regressed)
- RAG gain over DAPT-01: **{gains['rag_gain_over_dapt']['delta']}** ({gains['rag_gain_over_dapt']['improved_n']} improved, {gains['rag_gain_over_dapt']['regressed_n']} regressed)
- DAPT-01 gain within RAG: **{gains['dapt_gain_within_rag']['delta']}** ({gains['dapt_gain_within_rag']['improved_n']} improved, {gains['dapt_gain_within_rag']['regressed_n']} regressed)
- DAPT-01 gain without RAG: {gains['dapt_gain_without_rag']['delta']} ({gains['dapt_gain_without_rag']['improved_n']} improved, {gains['dapt_gain_without_rag']['regressed_n']} regressed)
- Independent recompute from raw outputs reproduced all four numbers exactly (integrity check).

## 2. Retrieval quality (BM25 + source-metadata, evaluate.py mode C; no dense channel)

- Corpus: {retrieval_metrics['corpus']['documents']:,} documents, {retrieval_metrics['corpus']['sources']} sources; contract violations: {len(agg['contract_violations'])}
- Source-level Recall@5 **{agg['source_recall_at_5']}**, Recall@10 **{agg['source_recall_at_10']}**, MRR **{agg['source_mrr']}**, zero-hit {agg['source_zero_hit']} (DAPT01EVAL-045, expected source absent from corpus)
- Unit-level MRR {agg['unit_mrr']}, unit hit@10 {agg['unit_hit_at_10']}/46 (explicit unit provenance is rare and hard for lexical retrieval)
- Evidence ceiling: mean evidence_answer_score **{ceiling['evidence_answer_score_mean']}**, full-ceiling {ceiling['evidence_answer_score_full']}/{ceiling['n_non_abstention']} non-abstention cases
- Both RAG arms reach answer_mean {ceiling['utilization']['base_rag']['answer_mean']} (gap to ceiling {ceiling['utilization']['base_rag']['gap_to_ceiling']}) — generation nearly saturates what evidence allows; no arm exceeds its ceiling.
- Abstention evidence: forbidden-pattern present in context {agg['abstention_evidence_forbidden_hits']}/4 — retrieval surfaces risky numbers/dates for all four abstention cases.

## 3. Failure attribution (retrieval vs generation)

| | retrieval-side | generation-side | success | prior knowledge |
|---|---|---|---|---|
| BASE + RAG | {failure['split']['base_rag']['retrieval_side']} | {failure['split']['base_rag']['generation_side']} | {failure['split']['base_rag']['success']} | {failure['split']['base_rag']['prior_knowledge']} |
| DAPT-01 + RAG | {failure['split']['dapt_rag']['retrieval_side']} | {failure['split']['dapt_rag']['generation_side']} | {failure['split']['dapt_rag']['success']} | {failure['split']['dapt_rag']['prior_knowledge']} |

- **RETRIEVAL_INSUFFICIENT (ev=0)**: {len([1 for p in comparison['per_case'] if p['failure_class'].get('base_rag')=='RETRIEVAL_INSUFFICIENT'])} cases for BASE+RAG
  (002, 007, 010, 011, 013, 014, 017, 018, 021, 023, 044, 045, 047) — lexical retrieval never surfaced the answer keyterms; the dominant remaining failure mode.
- **GENERATION_FAILURE (answer < ceiling)**: 5 for BASE+RAG (015, 019, 031, 035, 041), 8 for DAPT-01+RAG — evidence present, model failed to use it; DAPT+RAG adds 001/025/026/027 regressions.
- **GENERATION_FABRICATION (abstention fail, pattern absent from context)**: 036/037 for BASE+RAG (e.g. 037 asserts "1658" when the regex hit was only 17xx/18xx elsewhere), 037/038 for DAPT-01+RAG.
- **RETRIEVAL_RISK_CONTRIBUTED**: 039 — evidence itself contains the forbidden "45 Agams" pattern and the model repeats it; 1 case for BASE+RAG, 2 for DAPT-01+RAG (036 too).
- **PRIOR_KNOWLEDGE (answer=1 despite ev=0)**: 3 for BASE+RAG (004, 009, 040) — correct without evidence.

## 4. Category highlights (macro keyterm, BASE → DAPT → BASE+RAG → DAPT+RAG)

- Jain terminology: {terms['base_mean']} → {terms['dapt_mean']} → **{terms['base_rag_mean']}** → {terms['dapt_rag_mean']}
- Source attribution: {srcatt['base_mean']} → {srcatt['dapt_mean']} → **{srcatt['base_rag_mean']}** → **{srcatt['dapt_rag_mean']}**
- Practice: {practice['base_mean']} → {practice['dapt_mean']} → **{practice['base_rag_mean']}** → **{practice['dapt_rag_mean']}**
- Prakrit: {prakrit['base_mean']} → {prakrit['dapt_mean']} → {prakrit['base_rag_mean']} → **{prakrit['dapt_rag_mean']}**
- Sthānakavāsī distinction: {s_dist['base_mean']} → {s_dist['dapt_mean']} → {s_dist['base_rag_mean']} → **{s_dist['dapt_rag_mean']}** (only category where DAPT+RAG is best)
- Sthānakavāsī terminology: {s_term['base_mean']} → {s_term['dapt_mean']} → **{s_term['base_rag_mean']}** → **{s_term['dapt_rag_mean']}**
- Agam grounded: {agam['base_mean']} → {agam['dapt_mean']} → **{agam['base_rag_mean']}** → {agam['dapt_rag_mean']}
- Languages (en/gu/hi): BASE+RAG {comparison['language_table'][0]['base_rag_mean']}/{comparison['language_table'][1]['base_rag_mean']}/{comparison['language_table'][2]['base_rag_mean']} vs DAPT+RAG {comparison['language_table'][0]['dapt_rag_mean']}/{comparison['language_table'][1]['dapt_rag_mean']}/{comparison['language_table'][2]['dapt_rag_mean']} — Gujarati stays weak (0.2 both), Hindi favours DAPT+RAG (0.5208 vs 0.3333).

## 5. Abstention

Correct abstentions: BASE {abstention['base_correct']}/4, DAPT {abstention['dapt_correct']}/4, **BASE+RAG {abstention['base_rag_correct']}/4**, DAPT+RAG {abstention['dapt_rag_correct']}/4. Category mean: {abst['base_mean']} / {abst['dapt_mean']} / {abst['base_rag_mean']} / {abst['dapt_rag_mean']}. All four abstention cases retrieve contexts containing forbidden patterns; only case 038 abstained correctly under RAG. Evidence does not by itself prevent fabrication — the model must still refuse the risky pattern (see failure classes above).

## 6. Behaviour & attribution

- Answer length median: base {behaviour['base']['answer_len_median']} / dapt {behaviour['dapt']['answer_len_median']} / base+rag {behaviour['base_rag']['answer_len_median']} / dapt+rag {behaviour['dapt_rag']['answer_len_median']} chars; DAPT+RAG is markedly verbose (median 795, many at the 192-token cap).
- Repeated loops (Task-68 detector): base {behaviour['base']['looped_cases']}, dapt {behaviour['dapt']['looped_cases']}, base+rag {behaviour['base_rag']['looped_cases']}, **dapt+rag {behaviour['dapt_rag']['looped_cases']}** — DAPT+RAG loops on 5 cases (evidence + adapter compounding).
- Literal "INFRINGEMENT" tokens: 0 in all four arms.
- Attribution: cited-evidence-author base {attribution['base']['cited_evidence_author']}, dapt {attribution['dapt']['cited_evidence_author']}, base+rag {attribution['base_rag']['cited_evidence_author']}, **dapt+rag {attribution['dapt_rag']['cited_evidence_author']}** (highest); attribution-word markers {attribution['base']['cited_attribution_word']}/{attribution['dapt']['cited_attribution_word']}/{attribution['base_rag']['cited_attribution_word']}/{attribution['dapt_rag']['cited_attribution_word']}.

## 7. Recommended architecture

**BASE (Qwen3-8B-Base, no DAPT) + governed retrieval (BM25 + source-metadata mode C, EVIDENCE_K=5)**
— highest macro (0.5816) and pass-all (25), cheapest, no training. DAPT-01 remains the default *without* RAG
(0.2660 > 0.2021) but does not add value once evidence is provided (−0.0213); its verbosity/looping under RAG
is an active negative. Retrieval-side headroom (13 ev=0 cases) is the next lever: the single largest failure
bucket sits in retrieval, not generation (gap-to-ceiling for BASE+RAG only −{abs(ceiling['utilization']['base_rag']['gap_to_ceiling'])}).

## 8. Integrity, provenance, environment

- Frozen cases sha256 **{FROZEN_CASES_SHA256}** — verified, never modified.
- DAPT-01 adapter sha256 **{ADAPTER_SHA256}** (matches Task-59 forensic audit); adapter_config from
  .bench_ckpt/checkpoint-3893 (byte-differs from Task-59-recorded final, semantic fields identical — documented).
- Identical evidence contexts both RAG arms: **verified** (context_sha256 match per case, prompts file
  sha256 {provenance['prompts_sha256'][:16]}…); identical input prompts (incl. template) across arms: verified.
- Generation host: **{run_meta['run_host']}** — T4, transformers 5.0.0 / peft 0.19.1 / bnb 0.50.2 pinned;
  torch {run_meta['torch']} + python {run_meta['python']} (Colab preinstalled; deviation from Task-60
  torch 2.10.0+cu128 / python 3.12.13 recorded, quantization and decoding protocol identical).
- Colab incidents (documented, no metric impact): runtime preemption during first download; ipykernel
  pre-imports transformers 5.17 so pip-only pin causes a mixed-version crash — fixed by explicit pin +
  kernel restart + import verification; one completed run's outputs recovered from the stdout RESULT_JSON
  stream before regeneration in the final session.
- Not measured (never synthesised): evaluator fields for RAG arms, dense-channel contribution, query-side
  sect filters (N/A), fluency/human preference, graded passage relevance — see `not_measured` in JSON.

## 9. Files

- `data/evaluation/task69_rag_results.jsonl` — consolidated per-case rows (retrieval, prompt, evidence,
  four-arm outputs + hashes, scores, failure classes, provenance)
- `data/evaluation/task69_rag_comparison.json` — full 4-arm comparison (scorer output)
- `data/evaluation/task69_{{base,dapt}}_rag_results.jsonl` — raw generation outputs
- `data/evaluation/task69_rag_evidence.jsonl`, `task69_rag_prompts.jsonl`, `task69_retrieval_metrics.json`,
  `task69_rag_run_metadata.json`
- `data/reports/task69_rag_evaluation.json` — structured report
- `experiments/task69/{{build_rag_evidence,task69_rag_infer,score_task69_rag,build_task69_report}}.py`

**HARD STOP: NO TRAINING WAS RUN IN TASK 69** (no SFT-03, no DAPT-02, no Kaggle, no dataset curation,
no human review gate).
"""
    (REPORTS / "task69_rag_evaluation.md").write_text(md, encoding="utf-8")
    print("wrote data/reports/task69_rag_evaluation.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

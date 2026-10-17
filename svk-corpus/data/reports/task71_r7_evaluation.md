# TASK 71 — R7 Governed RAG Controlled Evaluation

**Verdict: DO_NOT_RECOMMEND — context/behavioural or score regressions under R7 => do not recommend the R7 window**

Phase-3 gate: **PASS** (47/47 byte-exact vs frozen Task-69 BASE+RAG).
R7 differs from Task-69 **only** in `EVIDENCE_K 5→10` and `TEXT_TRUNC 500→1000`
(config diff verified: {"evidence_k": {"task69": 5, "task71": 10}, "text_trunc": {"task69": 500, "task71": 1000}}). Same model, same system
prompt, greedy, 192-token cap, seed 42; no-RAG arms are the frozen Task-60 files reused
byte-identically (exactly equivalent to Task-69).

## 1. Four-arm scores and deltas vs Task-69 (frozen metric)

| Arm | macro (Task-69 → R7) | pass-all (Task-69 → R7) |
|---|---|---|
| BASE (no RAG) | 0.2021 → **0.2021** (Δ+0.0) | 6 → 6 (Δ+0) |
| DAPT-01 (no RAG) | 0.266 → **0.266** (Δ+0.0) | 8 → 8 (Δ+0) |
| **BASE + R7 RAG** | 0.5816 → **0.6312** (Δ+0.0496) | 25 → **29** (Δ+4) |
| DAPT-01 + R7 RAG | 0.5603 → **0.6702** (Δ+0.1099) | 23 → **29** (Δ+6) |

- Per-case vs Task-69 (RAG arms): 13 improved,
  3 regressed.
- R7 gains over no-RAG: BASE 0.4291,
  DAPT 0.4042; DAPT within R7-RAG
  0.039 (Task-69 was −0.0213).

## 2. Retrieval quality (Phase 6): R7 vs Task-69 vs Task-70 offline prediction

- Source Recall@5 0.913 (Task-69 0.913), Recall@10
  0.9783 (Task-69 0.9783), MRR 0.804 —
  ranking is unchanged by design (R7 only widens the evidence window).
- Evidence ceiling: mean **0.7403** (Task-69 0.6318,
  Task-70 R7 prediction 0.7403; match=True),
  full-ceiling **31**/43 (Task-69 26,
  predicted 31; match=True).
- Evidence-zero cases: **10** (Task-69 15,
  predicted 10; cases match=True) →
  DAPT01EVAL-002, DAPT01EVAL-007, DAPT01EVAL-009, DAPT01EVAL-010, DAPT01EVAL-013, DAPT01EVAL-014, DAPT01EVAL-017, DAPT01EVAL-018, DAPT01EVAL-045, DAPT01EVAL-047.
- Recovered by the R7 window (evidence score 0→>0): DAPT01EVAL-004, DAPT01EVAL-011, DAPT01EVAL-021, DAPT01EVAL-023, DAPT01EVAL-044.
- Abstention forbidden-pattern presence in context: 4/4
  (invariant, predicted 4; match=True). Contract violations:
  0 (zero, match=True).
- Config diff vs Task-69 verified: **True**
  ({"evidence_k": {"task69": 5, "task71": 10}, "text_trunc": {"task69": 500, "task71": 1000}}).

## 3. Failure attribution (Phase 7)

| | retrieval-side | generation-side | success | prior knowledge |
|---|---|---|---|---|
| BASE + R7 | 9 | 9 | 27 | 2 |
| DAPT-01 + R7 | 10 | 7 | 26 | 4 |
| BASE + R5 (Task-69) | 15 | 7 | 22 | 3 |
| DAPT-01 + R5 (Task-69) | 14 | 10 | 19 | 4 |

- Residual ev0 under R7 (10): DAPT01EVAL-002, DAPT01EVAL-007, DAPT01EVAL-009, DAPT01EVAL-010, DAPT01EVAL-013, DAPT01EVAL-014, DAPT01EVAL-017, DAPT01EVAL-018, DAPT01EVAL-045, DAPT01EVAL-047 — remaining bottleneck is still
  ranking depth, not window size.
- Recovered-case detail (evidence + arm scores, Task-69 → R7): see `phase7_failures.recovered_cases`
  in the JSON report.
- RAG counts R7: {"base_rag": {"GROUNDED_SUCCESS": 27, "RETRIEVAL_INSUFFICIENT": 8, "PRIOR_KNOWLEDGE": 2, "GENERATION_FAILURE": 6, "GENERATION_FABRICATION": 3, "RETRIEVAL_RISK_CONTRIBUTED": 1}, "dapt_rag": {"GROUNDED_SUCCESS": 25, "RETRIEVAL_INSUFFICIENT": 8, "PRIOR_KNOWLEDGE": 4, "GENERATION_FAILURE": 6, "RETRIEVAL_RISK_CONTRIBUTED": 2, "GENERATION_FABRICATION": 1, "ABSTENTION_CORRECT": 1}}.

## 4. Category / language (Task-69 → R7, base_rag / dapt_rag mean keyterm)

- ABSTENTION: base_rag 0.25→0.0, dapt_rag 0.0→0.25 (pass-all 1→0 / 0→1)
- AGAM_GROUNDED: base_rag 0.9167→1.0, dapt_rag 0.5→1.0 (pass-all 3→4 / 1→4)
- GUJARATI: base_rag 0.25→0.25, dapt_rag 0.25→0.0 (pass-all 1→1 / 1→0)
- HINDI: base_rag 0.4167→0.4167, dapt_rag 0.4167→0.3333 (pass-all 1→1 / 1→0)
- JAIN_TERMINOLOGY: base_rag 0.75→0.75, dapt_rag 0.5→0.75 (pass-all 3→3 / 2→3)
- MULTILINGUAL_MAPPING: base_rag 0.25→0.75, dapt_rag 0.5→0.75 (pass-all 1→3 / 2→3)
- PRACTICE: base_rag 0.875→1.0, dapt_rag 0.875→0.875 (pass-all 3→4 / 3→3)
- PRAKRIT: base_rag 0.5→0.5, dapt_rag 0.625→0.75 (pass-all 2→2 / 2→3)
- SANSKRIT: base_rag 0.3333→0.3333, dapt_rag 0.5556→0.5556 (pass-all 1→1 / 1→1)
- SOURCE_ATTRIBUTION: base_rag 0.75→0.75, dapt_rag 0.75→1.0 (pass-all 3→3 / 3→4)
- STHANAKAVASI_DISTINCTION: base_rag 0.875→1.0, dapt_rag 1.0→1.0 (pass-all 3→4 / 4→4)
- STHANAKAVASI_TERMINOLOGY: base_rag 0.75→0.75, dapt_rag 0.75→0.75 (pass-all 3→3 / 3→3)
- Languages: en: 0.6961→0.7353, gu: 0.2→0.2, hi: 0.3333→0.4583 (base_rag mean).
- Full 4-arm category/language tables: `task71_r7_comparison.json` → `category_table` / `language_table`.

## 5. Abstention

R7 correct abstentions: BASE 0/4, DAPT 0/4,
**BASE+R7 0/4**, DAPT+R7 1/4
(Task-69 RAG arms: base_rag 1/4, dapt_rag 0/4;
total held at 1 →
1, with a per-arm swap base 1→0 / dapt 0→1 —
flagged as a material regression by the per-arm gate). Evidence surfaces the forbidden patterns in
all four cases (invariant); safety is behaviour-held, not context-prevented.

## 6. Behaviour & attribution

- Loops (Task-68 detector): base_rag 1 → 0, dapt_rag 5 → 8.
- Literal INFRINGEMENT tokens: 0 in all arms.
- Attribution (first-5 provenance slice, scorer unchanged from Task-69): cited-author
  base_rag 7→9,
  dapt_rag 16→12;
  attribution-word base_rag 10→9,
  dapt_rag 13→12.

## 7. Prompt/evidence budget (Phase 8)

- Context chars: mean 4348.7 →
  11710.3 (×2.69), median
  4198 → 11602
  (×2.76), max 15375.
- Evidence items per case: 5 → 10; 10/10 items rendered in every prompt (kernel-asserted).
- 192-token-cap hits: base_rag 9 →
  12, dapt_rag
  39 → 42
  (cap pressure increased).
- Decode time (T4): load 69.0s, base_rag
  685.3s, dapt_rag 1554.5s
  (Task-69: 556.6s /
  1436.6s).
- No decoding/seed/model change; no prompt change outside the R7 window.

## 8. Decision gate (Phase 9)

- Criteria: {"ceiling_mean_up": true, "ceiling_matches_task70_r7_prediction": true, "base_rag_macro_up": true, "base_rag_pass_up": true, "dapt_rag_macro_up": true, "dapt_rag_pass_up": true, "either_rag_arm_e2e_up": true, "neither_rag_arm_macro_down": true, "neither_rag_arm_pass_down": true, "abstention_not_regressed_vs_task69": false, "contract_violations_zero": true, "identical_contexts_both_rag_arms": true, "baseline_gate_pass": true, "no_loop_increase": false}
- Material regressions: ['abstention vs Task-69: base_rag 1->0, dapt_rag 0->1 (total 1->1)', 'loops up (1, 5) -> (0, 8)']
- **Outcome: DO_NOT_RECOMMEND** — context/behavioural or score regressions under R7 => do not recommend the R7 window
- Production retrieval config: **NOT changed** (evaluation experiment only).

## 9. Integrity, provenance, environment

- Frozen cases sha256 **06625f72190e3ae130447345afdc04342bd19cb76f842285706480cba7765b81** verified; DAPT-01 adapter sha256
  **9b4d2bdcfe089118d0634815596b628506a83c434d3863cff7a731cba75a58e9** (verified on-VM before every run).
- Baseline reproduction: PASS, fresh file sha
  af9c851844bc27e3… byte-exact on answer, input_prompt_sha256, evidence_context_sha256, new_tokens, prompt_style, decoding, seed, system_prompt, n_evidence_items.
- R7 prompts sha 8dd60723b03df16b…; Task-69 prompts sha unchanged
  00096f61a4a2aea5…; all 47 contexts changed vs Task-69 (window is the only diff).
- Both RAG arms received byte-identical contexts: **True**.
- Generation host: **Google Colab T4 (google-colab-cli; NOT Kaggle)** — Tesla T4, torch
  2.11.0+cu130, python 3.13.15, transformers
  5.0.0 / peft 0.19.1 /
  bitsandbytes 0.50.2 (Task-69 stack, pinned).
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
- `data/evaluation/task71_{base,dapt}_rag_results.jsonl` — raw R7 generation outputs
- `data/evaluation/task71_r7_{evidence,prompts}.jsonl`, `task71_r7_metrics.json`,
  `task71_r7_run_metadata.json`
- `data/evaluation/task71_baseline_{base_rag_results,check,run_metadata}.*` — Phase-3 gate record
- `data/reports/task71_r7_evaluation.{md,json}`
- `experiments/task71/{task71_build_r7_evidence,task71_rag_infer,task71_verify_baseline,task71_score,task71_report}.py`

**HARD STOP: NO TRAINING WAS RUN IN TASK 71** (no SFT-03, no DAPT-02, no new dense model,
no production retrieval change, no canonical-corpus or frozen-benchmark modification).

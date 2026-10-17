# TASK 75 — Four-Arm H3_RRF20 RAG Generation Gate

## 1. Executive summary / verdict

**RECOMMEND_H3_RRF20** — H3_RRF20 four-arm gate passes all recovered Task-71 criteria (vs Task-69 R0 baseline) with no material regressions => H3_RRF20 is the recommended RAG retrieval candidate; production change remains a separate explicit task

| Arm | macro_keyterm | pass_all |
|---|---|---|
| A BASE no-RAG | 0.2021 | 6 |
| B DAPT-01 no-RAG | 0.266 | 8 |
| C BASE + H3_RRF20 | 0.695 | 32 |
| D DAPT-01 + H3_RRF20 | 0.695 | 31 |

RAG gain over no-RAG (same model): BASE +0.4929, DAPT-01 +0.429.
DAPT value under H3_RRF20 RAG (D−C): **+0.0** macro
(2 improved / 3 regressed).
DAPT value without RAG (B−A): +0.0639 macro.

Evidence ceiling (H3_RRF20): **0.8372**
(36/43 non-abstention full; Ev0=7)
vs Task-69 R0 0.6318 and
Task-71 R7 0.7403.

## 2. Verified setup, hashes, frozen benchmark

- Frozen benchmark sha256 `06625f72190e3ae130447345afdc04342bd19cb76f842285706480cba7765b81` verified: **True**
- DAPT-01 adapter sha256 `9b4d2bdcfe089118d0634815596b628506a83c434d3863cff7a731cba75a58e9` verified on-VM: **True**
- H3_RRF20 retrieval reproduction vs Task-74 aggregates: **PASS**
  (expected {'unit_recall_at_5': 0.5385, 'source_recall_at_5': 0.9783, 'evidence_ceiling_mean': 0.8372, 'ev0_count': 7}; observed {'unit_recall_at_5': 0.5385, 'source_recall_at_5': 0.9783, 'evidence_ceiling_mean': 0.8372, 'ev0_count': 7})
- Generation: Tesla T4, torch 2.11.0+cu130,
  transformers 5.0.0, peft 0.19.1,
  bitsandbytes 0.50.2, seed 42,
  greedy, max_new_tokens=192, 4-bit NF4 double / fp16.
- Prompts sha256 (H3_RRF20 evidence): `302f6c917b538bb440d244eeeba9aba35756186bef04cb1cd89415f65a774409`
- Identical evidence contexts both RAG arms: **True**
- Evidence window: EVIDENCE_K=5, TEXT_TRUNC=500 (Task-69 width); RRF k=20 over full BM25 × full bge-m3 dense lists.
- Prior artifacts unchanged (sha recorded in json `integrity.prior_artifacts`): all exist.
- Production retrieval changed: **NO**. Training started: **NO**.

## 3. Four-arm aggregate scores

See §1 table. Raw per-case scores and flags: `data/evaluation/task75_rag_comparison.json`.

## 4. Per-case results

47 cases scored; per-case rows (scores, flags, failure classes, verdicts)
in `task75_rag_comparison.json` `per_case` and the four results jsonl files.

Improved vs Task-69 R0 (RAG arms): 53 arm-case pairs;
regressed: 4.

## 5. Failure attribution (retrieval vs generation)

| Arm | GROUNDED_SUCCESS | RETRIEVAL_INSUFFICIENT | GENERATION_FAILURE | RETRIEVAL_LIMITED | PRIOR_KNOWLEDGE | ABSTENTION_CORRECT | FABRICATION | RETRIEVAL_RISK |
|---|---|---|---|---|---|---|---|---|
| BASE+H3_RRF20 | 31 | 6 | 5 | 0 | 1 | 0 | 2 | 2 |
| DAPT-01+H3_RRF20 | 29 | 6 | 7 | 0 | 1 | 1 | 1 | 2 |

## 6. Religious / provenance / abstention / loops

- Abstention (4 cases): Task-75 base_rag 0, dapt_rag 1
  (Task-69: 1/0;
   Task-71: 0/1).
- Loops: base_rag 0, dapt_rag 4 (Task-69: 1/5).
- Attribution flags: {"base": {"cited_evidence_author": 13, "cited_attribution_word": 16, "mechanical": "surname tokens from evidence provenance present in answer; marker = according to|manifest|corpus|the source|source says"}, "dapt": {"cited_evidence_author": 13, "cited_attribution_word": 11, "mechanical": "surname tokens from evidence provenance present in answer; marker = according to|manifest|corpus|the source|so.

## 7. Comparison to Task-69/71

| Metric | Task-69 R0 | Task-71 R7 | Task-75 H3_RRF20 (best RAG arm) |
|---|---|---|---|
| ceiling_mean | 0.6318 | 0.7403 | 0.8372 |
| ceiling_full | 26 | 31 | 36 |
| base_rag macro/pass | 0.5816/25 | 0.6312/29 | 0.695/32 |
| dapt_rag macro/pass | 0.5603/23 | 0.6702/29 | 0.695/31 |
| unit recall@5 (retrieval) | 0.3846 | n/a (same R0 retrieval) | 0.5385 |
| prior verdict | RECOMMEND baseline RAG | DO_NOT_RECOMMEND R7 | RECOMMEND_H3_RRF20 |

Task-71 R7 raised scores but failed abstention/loop gates. H3_RRF20 raises the
*retrieval* ceiling (unit@5 +0.15, Ev0 15→7) at the Task-69 evidence width;
whether that converts to end-to-end score is measured by the §1 gates.

## 8. Acceptance gate table (Task-71 criteria recovered)

| Criterion | Met |
|---|---|
| ceiling_mean_up_vs_task69 | PASS |
| ceiling_matches_task74_h3rrf20 | PASS |
| base_rag_macro_up_vs_task69 | PASS |
| base_rag_pass_up_vs_task69 | PASS |
| dapt_rag_macro_up_vs_task69 | PASS |
| dapt_rag_pass_up_vs_task69 | PASS |
| either_rag_arm_e2e_up_vs_task69 | PASS |
| neither_rag_arm_macro_down_vs_task69 | PASS |
| neither_rag_arm_pass_down_vs_task69 | PASS |
| abstention_not_regressed_vs_task69 | PASS |
| contract_violations_zero | PASS |
| identical_contexts_both_rag_arms | PASS |
| baseline_gate_h3rrf20_reproduction_pass | PASS |
| frozen_benchmark_sha_ok | PASS |
| no_loop_increase_vs_task69 | PASS |

All met: **True**. Material regressions: none.
Outcome: **RECOMMEND_H3_RRF20**.

## 9. Limitations, reproducibility, raw artifacts

- n=47; no statistical-significance claims; raw counts alongside percentages.
- Keyterm scorer is substring-based (Task-60 frozen); no human preference study.
- 4-bit quantization and greedy decoding are frozen from Task-60/69/71; not re-tuned.
- Artifacts: comparison, retrieval metrics, evidence, prompts, run metadata, four
  results jsonl files under `data/evaluation/task75_*` (see json `artifacts`).

## 10. Explicit recommendation

- **Retrieval candidate**: H3_RRF20 (deterministic RRF k=20 over full BM25 × full
  bge-m3 lists, evidence window k=5/500). Gate outcome: **RECOMMEND_H3_RRF20**.
- **Production retrieval changed**: NO (no tracked src edits; H1 BM25 remains).
- **Training / SFT / DAPT-02 started**: NO.
- **Next (if RECOMMEND)**: separate explicit production-candidate task wiring
  H3_RRF20 into the serving path behind config, with the same contract checks;
  this task does not change production.

# TASK 73 — Zero-shot Query Expansion Retrieval Experiment

**Verdict: HYPOTHESIS_NOT_SUPPORTED — REJECT query expansion as configured (R10 = max-score union + score-order merge)**

Arms: **R0** (Task-69 baseline, Q0 only) · **M2ref** (Q0 + score-order merge, decomposition reference) · **R10** (Q0 + up to 3 lexical variants, union max-score, score-order merge). All k5/500, corpus/tokenizer/candidate policy unchanged.

## 1. Baseline (Phase-1 gate)

- Gate **PASS**; byte-exact vs frozen Task-69 evidence 47/47; rank crosscheck 47/47; frozen sha 06625f72190e3ae1…
- source R@5 0.913, R@10 0.9783, unit MRR 0.3333, ceiling 0.6318 (26 full), Ev0 15; corpus 164,238 docs

## 2. Query expansion validity

- 127/141 variants valid (90.1%) from Qwen/Qwen3-8B-Base · greedy (do_sample=False), seed 42, max_new_tokens 160, 4-bit nf4, chat_template, no evidence in prompt
- 14 invalid: {'truncated_at_cap': 10, 'empty_after_truncation': 4} across 10 cases (all manually reviewed; recorded, never discarded)
- Zero-valid cases: ['DAPT01EVAL-045'] (Q0-only run)

## 3. Unit retrieval deltas

| metric | R0 | M2ref | R10 | R10−R0 |
|---|---|---|---|---|
| unit_recall_at_1 | 0.2821 | 0.2821 | 0.2308 | -0.0513 |
| unit_recall_at_3 | 0.3846 | 0.3846 | 0.3077 | -0.0769 |
| unit_recall_at_5 | 0.3846 | 0.4359 | 0.359 | -0.0256 |
| unit_recall_at_10 | 0.4103 | 0.4359 | 0.4359 | +0.0256 |
| unit_mrr | 0.3333 | 0.3419 | 0.2908 | -0.0425 |

- target unit@5 ≥ 0.46 → **MISSED** (R10 0.359); M2ref merge-policy-only 0.4359 already beats expansion 0.359

## 4. Source retrieval deltas

| metric | R0 | M2ref | R10 | R10−R0 |
|---|---|---|---|---|
| source_recall_at_1 | 0.7174 | 0.7174 | 0.6522 | -0.0652 |
| source_recall_at_5 | 0.913 | 0.8913 | 0.8478 | -0.0652 |
| source_recall_at_10 | 0.9783 | 0.913 | 0.8913 | -0.087 |
| source_mrr | 0.804 | 0.7944 | 0.7413 | -0.0627 |

- guardrail source@5 ≥ 0.90 → **BREACHED** by R10 (0.8478); new source-zero cases: ['DAPT01EVAL-007', 'DAPT01EVAL-013', 'DAPT01EVAL-021', 'DAPT01EVAL-037']
- source regressed in 9 cases ['DAPT01EVAL-003', 'DAPT01EVAL-007', 'DAPT01EVAL-011', 'DAPT01EVAL-013', 'DAPT01EVAL-014', 'DAPT01EVAL-016', 'DAPT01EVAL-017', 'DAPT01EVAL-021', 'DAPT01EVAL-037']

## 5. Ev0

- Ev0: 15 (R0) → 14 (M2ref, recovered ['DAPT01EVAL-044']) → **16** (R10, recovered none, new ['DAPT01EVAL-003']); target ≤ 12 **MISSED**

## 6. Evidence ceiling

- ceiling mean/full: R0 0.6318/26 · M2ref 0.655/27 · R10 0.6202/26 (R10−R0 -0.0116, R10−M2ref -0.0348)

## 7. Failure-case recovery

| case | q0 rank | union rank | best q | unit R0/M2/R10 | src R0/R10 | ev R0/M2/R10 | Δ |
|---|---|---|---|---|---|---|---|
| 002 | 196 | 54 | Q1 | None/None/None | 1/1 | 0.0/0.0/0.0 | unchanged |
| 007 | 14 | 14 | Q0 | None/None/None | 8/None | 0.0/0.0/0.0 | unchanged |
| 010 | 2335 | 2358 | Q0 | None/None/None | 1/1 | 0.0/0.0/0.0 | unchanged |
| 011 | 1484 | 2480 | Q0 | None/None/None | 3/4 | 0.0/0.0/0.0 | unchanged |
| 013 | 986 | 2119 | Q0 | None/None/None | 6/None | 0.0/0.0/0.0 | unchanged |
| 014 | 186 | 186 | Q0 | None/None/None | 5/8 | 0.0/0.0/0.0 | unchanged |
| 018 | 119 | 39 | Q1 | None/None/None | 1/1 | 0.0/0.0/0.0 | unchanged |
| 021 | None | None | None | None/None/None | 8/None | 0.0/0.0/0.0 | unchanged |
| 023 | 75 | 75 | Q0 | None/None/None | 5/4 | 0.0/0.0/0.0 | unchanged |
| 044 | 4 | 8 | Q0 | 6/4/8 | 1/1 | 0.0/1.0/0.0 | regressed |
| 047 | 873 | 1001 | Q0 | None/None/None | 1/1 | 0.0/0.0/0.0 | unchanged |

- unit zero-hits R0: 23; recovered: R10 ['DAPT01EVAL-041'], M2ref ['DAPT01EVAL-041']; new in R10: none
- unit regressed under R10: ['DAPT01EVAL-001', 'DAPT01EVAL-003', 'DAPT01EVAL-015', 'DAPT01EVAL-044']; improved: ['DAPT01EVAL-041']
- depth promotions too shallow: {'002': 'q0 196 -> union 54', '018': 'q0 119 -> union 39'}
- out-of-pool sinks (new candidate misses): ['011', '013']
- mechanism: max-score union compares BM25 scores ACROSS queries whose score scales differ with query term count; variant-score inflation displaces Q0's top docs (001 1->4, 003 1->10, 015 3->5, 044 4->8 losing M2ref's recovery), sinks depth docs below the pool head (011 1484->2480, 013 986->2119 -> new candidate misses) and reorders the diversify source composition (007/013/021/037 lost)

## 8. Query drift

- 127/141 valid (90.1% ≥ 90% ⇒ low drift, criterion True); invalids recorded with reasons: {'truncated_at_cap': 10, 'empty_after_truncation': 4}
- cases with ≥1 invalid: 10; zero-valid: ['DAPT01EVAL-045']

## 9. Runtime

- generation (Colab T4): load 274.4s + decode 412.0s = 686.4s for 141 variants
- retrieval: R0 arm 13.3s · M2ref 5.7s · R10 arm 53.3s (variant searches 28.7s) = 4.01× R0; experiment total 130.4s; Phase-1 gate 72.1s
- no context expansion (k5/500 unchanged)

## 10. Verdict

- unit_recall_at_5: MISSED — {'target': 0.46, 'r0': 0.3846, 'm2ref': 0.4359, 'r10': 0.359, 'met': False}
- ev0_count: MISSED — {'max': 12, 'r0': 15, 'm2ref': 14, 'r10': 16, 'met': False}
- source_recall_at_5: MISSED — {'min': 0.9, 'r0': 0.913, 'm2ref': 0.8913, 'r10': 0.8478, 'met': False}
- query_drift_low: MET — {'criterion': 'valid >= 90% and <=1 case zero-valid', 'valid_fraction': 0.9007, 'zero_valid_cases': 1, 'met': True}
- **REJECT query expansion as configured (R10 = max-score union + score-order merge)**; decomposition: M2ref (Q0 score-order merge, no expansion) reproduces Task-72 M2 exactly (19/19 integrity keys) at unit@5 0.4359 > R10 0.359: merge policy alone explains the recoverable gain; adding expansion under score-max fusion is strictly counterproductive (unit MRR -0.0425 vs R0, src@5 -0.0652 vs R0, Ev0 +1)

## 11. Recommended next experiment

- Rank-fusion query expansion: re-run the R10 candidate union with RRF (or Q0-primary ordering: union candidates, Q0 score for any Q0-present doc, variant rank only for variant-only docs) so cross-query score scales cannot displace Q0's top docs; keep R0's source-anchored candidate policy and score-order merge
- bars to beat: {"unit_at_5": "0.4359 (M2ref), R0 floor 0.3846, original target 0.46", "source_at_5": ">= 0.913 (R0 anchor; R10 failed at 0.8478, M2ref failed at 0.8913)", "ev0": "<= 12 (R0 15, M2ref 14, R10 16)"}

## 12. Tests

- `462 ran, 0 failures, 2 errors (pre-existing faiss), 1 skipped` — baseline-equal: True

## 13. Git status

- git diff empty (no tracked modifications): True; tracked changes: none; task73 untracked new artifacts: 7
- integrity: frozen sha verified; all 11 prior-task artifacts unchanged (mtimes pre-task73): True

## Constraints confirmation

Training: NO · SFT-03: NO · DAPT-02: NO · dense downloaded: NO · reranker added: NO · corpus changed: NO · production retrieval changed: NO · frozen benchmark changed: NO · prior task artifacts changed: NO · benchmark generation run: NO (retrieval gate failed)

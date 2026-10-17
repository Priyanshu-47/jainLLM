# Task 72 — Source-Anchored Within-Source Passage Retrieval

- Generated: 2026-10-02 16:44:33 UTC
- Verdict: **HYPOTHESIS_NOT_SUPPORTED**
- Frozen benchmark: `dapt01_eval_cases.jsonl` sha `06625f72190e3ae1…` (verified)
- Constraints: no training, no SFT-03/DAPT-02, no dense models, no production-retrieval change, no frozen/prior artifact modification.

## 1. Baseline reproduction (Phase 1)

| Metric | Expected | Reproduced |
|---|---|---|
| source R@5 | 0.9130 | 0.9130 |
| source R@10 | 0.9783 | 0.9783 |
| unit MRR | 0.3333 | 0.3333 |
| evidence ceiling (mean / full) | 0.6318 / 26 | 0.6318 / 26 |
| Ev=0 count | 15 | 15 |

Gate: **PHASE1_BASELINE_GATE_PASS** — reproduced twice (per-case recompute + independent `group_pass` re-score), frozen sha verified.

## 2. Configurations and integrity gates (R0 / R7 / R8 / R9)

| Config | Mode | k / trunc | Role |
|---|---|---|---|
| R0 | global BM25 (Task-69 exact) | 5 / 500 | baseline |
| R7 | global BM25 (Task-71 frozen) | 10 / 1000 | reference |
| R8 | within-source BM25 + round-robin merge | 5 / 500 | **primary** |
| R9 | within-source BM25 + round-robin merge | 10 / 1000 | secondary |

- R0 rebuild byte-exact vs frozen Task-69 evidence: **47/47** (text_ids, ranks, channels, context sha)
- R7 frozen re-score matches Task-71 published numbers (0.7403 / 31 full / 10 ev0): **true**
- Expected-source presence invariant across R0/R7/R8/R9: **true**
- Contract violations: **0** in all configs (incl. post-hoc M2)

## 3. R0 / R7 / R8 / R9 metrics

| Metric | R0 | R7 | R8 | R9 |
|---|---|---|---|---|
| source R@1 | 0.7174 | 0.7174 | 0.7174 | 0.7174 |
| source R@3 | 0.8696 | 0.8696 | 0.8913 | 0.8913 |
| source R@5 | 0.9130 | 0.9130 | 0.9565 | 0.9565 |
| source R@10 | 0.9783 | 0.9783 | 0.9783 | 0.9783 |
| source MRR | 0.8040 | 0.8040 | 0.8159 | 0.8159 |
| unit R@1 | 0.2821 | 0.2821 | 0.2821 | 0.2821 |
| unit R@3 | 0.3846 | 0.3846 | 0.3333 | 0.3333 |
| unit R@5 | 0.3846 | 0.3846 | 0.3590 | 0.3590 |
| unit R@10 | 0.4103 | 0.4103 | 0.4103 | 0.4103 |
| unit MRR | 0.3333 | 0.3333 | 0.3212 | 0.3212 |
| evidence ceiling | 0.6318 | 0.7403 | 0.6550 | 0.7326 |
| ceiling full (n) | 26 | 31 | 27 | 31 |
| Ev=0 (n) | 15 | 10 | 14 | 11 |
| width-miss (n) | 1 | 0 | 2 | 0 |
| ranking-miss (n) | 13 | 13 | 14 | 14 |
| candidate-miss (n) | 10 | 10 | 9 | 9 |
| metadata-only (n) | 2 | 2 | 0 | 0 |
| forbidden hits (n) | 4 | 4 | 3 | 4 |
| context median chars | 4198 | 11602 | 5273 | 10315 |

## 4. Unit-retrieval improvement (R8−R0)

| Metric | Δ (R8−R0) | Δ (R9−R7) |
|---|---|---|
| unit_recall_at_1 | +0.0000 | +0.0000 |
| unit_recall_at_3 | -0.0513 | -0.0513 |
| unit_recall_at_5 | -0.0256 | -0.0256 |
| unit_recall_at_10 | +0.0000 | +0.0000 |
| unit_mrr | -0.0121 | -0.0121 |
| evidence_ceiling_mean | +0.0232 | -0.0077 |

Phase-8 pre-registered criteria — **none met**:

- **A_material_unit_improvement**: NOT MET — both deltas negative (−0.0256 / −0.0121); threshold +0.05 not reached
- **B_source_limited**: NOT MET — residual misses are dominated by within-source lexical rank depth (10/13 at ranks 11–236 inside the correct source) + zero-score units (7) below/around the global pool cut — exactly the mechanism B excludes; source-miss is 1 case, corpus-absence 1 case
- **C_selection_limited**: NOT MET — precondition fails: unit metrics did not improve
- **D_cost_limited**: NOT MET — 1.58× < 2× runtime and context 0.45× of R7 (< 1.2×)

Verdict detail: Within-source restricted BM25 with the pre-registered round-robin merge does NOT materially improve unit retrieval: R8−R0 unit@5 −0.0256, MRR −0.0121; no Phase-8 criterion is met. Ceiling improves only +0.0232 (26→27 full, ev0 15→14); R9 at k10 is slightly negative (ceiling −0.0077, ev0 +1). Composition of the 23 unit zero-hits: 10 ranking-miss units rank 11–236 within their already-correct source (restriction re-indexes unchanged scores → unrankable in 10 slots), 3 fit the within-source top-10 (007 recovered by R8; 037/041 merge-blocked), 7 have zero lexical score even inside the correct source, 1 is sub-pool-but-positive (010, within-rank 268), 1 corpus-absent, 1 source-miss.

## 5. Known-case recovery (Phase 5)

| Case | T70 | Ev0@R0 | src rank | pool rank | within-src rank | u R0 | u R7 | u R8 | ev R0→R7→R8 | note |
|---|---|---|---|---|---|---|---|---|---|---|
| 002 | D | Y | 1 | 196 | 196 | None | None | None | 0→0→0 |  |
| 004 | D | Y | 1 | 2,1004 | 2,495 | 2 | 2 | 9 | 0→1→0 |  |
| 007 | D | Y | 8 | 14 | 1 | None | None | 4 | 0→0→1 | recovered |
| 009 | D | Y | 2 | 886 | 193 | None | None | None | 0→0→0 |  |
| 010 | C | Y | 1 | None | 268 | None | None | None | 0→0→0 |  |
| 011 | D | Y | 3 | 1484 | 236 | None | None | None | 0→0.5→0 |  |
| 013 | D | Y | 6 | 986 | 45 | None | None | None | 0→0→0 |  |
| 014 | D | Y | 5 | 186 | 48 | None | None | None | 0→0→0 |  |
| 017 | A | Y | 1 | None | None | None | None | None | 0→0→0 | UNKNOWN — expected unit not present in corpus (corpus absence) |
| 018 | D | Y | 1 | 119 | 41 | None | None | None | 0→0→0 |  |
| 021 | D | Y | 8 | — | — | None | None | None | 0→1→0 | UNKNOWN — no expected units recorded in frozen benchmark |
| 023 | D | Y | 5 | 75 | 11 | None | None | None | 0→0.3333→0 |  |
| 040 | D | . | 1 | 1 | 1 | 1 | 1 | 1 | 0.5→1→1 |  |
| 044 | D | Y | 1 | 4 | 4 | 6 | 6 | None | 0→1→0 |  |
| 045 | B | Y | None | None | None | None | None | None | 0→0→0 | expected source not in selected set (cannot anchor within-source) |
| 047 | D | Y | 1 | 873 | 173 | None | None | None | 0→0→0 |  |

- R8 recovered Ev=0: 007 — metadata fill → within-source rank-1 unit. No new Ev=0 under R8.
- Merge-blocked (fits within-source top-10, absent from R8 top-10): 037, 041, 044 (within-ranks [5, 4, 4]; note 044 was a R0 hit at rank 6 — round-robin lost it)
- Width-pushed past k=5: 004→9, 015→6
- Attribution of the 13 R0 ranking-miss cases: **10 depth-blocked (within-rank 11–236)** vs 3 that fit a within-source top-10 — of the latter, 007 (wr 1) was recovered by R8, 037 (wr 5) and 041 (wr 4) were lost to round-robin slot allocation
- UNKNOWN notes preserved: 017 (corpus absence), 021 (no expected units recorded), 045 (expected source not selected — cannot anchor).

## 6. Evidence ceiling

- R0 0.6318 / 26 full → R8 **0.6550 / 27 full** (+0.0232); R7 0.7403 / 31 → R9 0.7326 / 31 (-0.0077)
- R0→R8 per-case evidence transitions: up 3 (007, 026, 040), down 2 (016, 043), same 38, unscored 4
- R0→R7 (reference): up 7, down 0, same 36, unscored 4

## 7. Ev=0

- Counts: R0 **15** → R7 10 → R8 **14** → R9 11
- R8 recovered: 007; new under R8: none
- 4 cases score `null` evidence under every config (frozen-scorer property; unchanged).

## 8. Context / runtime cost

| Config | context median (chars) | vs R0 |
|---|---|---|
| R0 | 4198 | 1.00× |
| R7 | 11602 | 2.76× |
| R8 | 5273 | 1.26× |
| R9 | 10315 | 2.46× |

- Retrieval runtime: R8 = 1.58× R0 (20.9s vs 13.2s total; within-source step 7.7s)
- Top-10 composition changed in 46/47 cases (round-robin reorders every case); metadata-only cases drop 2→0 (fills replaced by lexical units of fill sources).

## 9. Bottleneck conclusion

1. **Primary — within-source lexical rank depth**: 10/13 ranking-miss expected units sit at within-source ranks 11–236 of the *already correct* source. Restriction re-indexes the same global-IDF scores, so their scores do not change; no 10-slot merge policy can surface them.
2. **Secondary — zero/sub-pool scores**: 7 expected units score 0 even inside their selected source; 010 is positive but sub-pool (within-rank 268 — restricted search adds it as candidate, still unrankable); 017 corpus-absent; 045 source-miss.
3. **Round-robin merge is actively harmful**: blocks 037/041/044 (within-ranks 5/4/4), width-pushes 004→9 and 015→6, and drives unit@3 down 0.0513 vs R0.
4. **Not the bottleneck — source anchoring**: presence invariant, source@5 0.913→0.9565 under R8; source-miss = 045 only, corpus-absence = 017 only.

Unit zero-hit arithmetic (23): 10 in-source depth + 3 within-top-10 but mishandled (1 recovered by R8, 2 merge-blocked) + 7 zero-overlap + 1 sub-pool-positive + 1 corpus-absent + 1 source-miss = 23.

## 10. Post-hoc sensitivity (M2 score-order merge)

> Clearly labelled post-hoc; NOT part of the pre-registered config set and NOT used for the primary verdict.

| Metric | M2_K5 − R0 | M2_K10 − R7 |
|---|---|---|
| unit_recall_at_1 | +0.0000 | +0.0000 |
| unit_recall_at_3 | +0.0000 | +0.0000 |
| unit_recall_at_5 | +0.0513 | +0.0513 |
| unit_recall_at_10 | +0.0256 | +0.0256 |
| unit_mrr | +0.0086 | +0.0086 |
| source_recall_at_5 | -0.0217 | -0.0217 |
| evidence_ceiling_mean | +0.0232 | -0.0194 |

- M2_K5 ceiling 0.655 / 27 full, ev0 14; M2_K10 ceiling 0.7209 / 30, ev0 11
- M2 unit-rank changes vs R0: 041 None→4, 044 6→4 — different cases than R8's recovery (007); 044's evidence 0.0→1.0; M2 recovers 041 but not 007 (041's evidence stays 1.0 in both — its support came from other slots)
- Isolation result: merge policy accounts for only 5 cases (3 blocked + 2 width-pushed) and −0.0513 unit@3; even the better merge leaves the 10 depth-blocked units untouched → confirms the lexical-score bottleneck.

## 11. Phase 6 — generation decision

**NOT_RUN** — the question is answered at evidence level without generation: YES only marginally — ceiling 0.6318→0.6550 (+1 full case), ev0 15→14, no new ev0 cases, context changed in 46/47 cases; but primary unit metrics decline and R9 (k10) is slightly negative, so the improvement is below the pre-registered material thresholds.
- evidence-level question is fully answerable from retrieval metrics (ceiling/ev0/context) — generation is not required to answer it
- R8 primary metrics are negative; generating an e2e run for a refuted retrieval config cannot change the verdict
- the only post-hoc improving variant (M2) is not yet pre-registered or replicated; e2e validation before that step would be premature
- no training/DAPT/generation-model/decoding changes made (task constraint)
- DAPT secondary arm: NOT_RUN (no primary run).

## 12. Phase 9 — recommended next experiment (exactly one)

**R10 — zero-shot lexical query expansion + score-order merge**

**configuration:**
- query: original question + 3 zero-shot lexical term variants generated by Qwen3-8B BASE (frozen Task-69 generation config, temperature 0, no training)
- scoring: union-BM25, doc score = max BM25 over the 4 query strings; same k1=1.5 b=0.75, global IDF, same corpus + normalization (no new tokenizer)
- merge: score-order within-source merge (post-hoc M2 policy: global score order filtered to selected sources); round-robin dropped
- evidence: k=5 / 500 tokens (Task-69 evidence settings)

**target metric:**
- unit_recall_at_5: >= 0.46 (R0 0.3846; needs >= +2 recoveries)
- ev0_count: <= 12 (R0 15; pure merge change already gives 14)
- guardrail_source_recall_at_5: >= 0.90 (M2 observed 0.8913 — must not regress further)

**observed benefit of known component:**
- post-hoc score-order merge (M2) alone: unit@5 +0.0513 (041 None→4, 044 6→4), ceiling +0.0232 (044 ev 0→1.0), 0 contract violations, zero extra runtime; expansion component untested — it is the lever aimed at the measured deficit

**expected benefit of untested component:**
- moves BM25 scores of the 10 depth-blocked + 7 zero-overlap + 1 sub-pool-positive units directly; within-source restriction cannot (scores are unchanged by restriction)

**regressions to watch:**
- source drift: expanded query pulls foreign sources (M2 already −0.0217 source@5 vs R0)
- forbidden/abstention contamination (count evidence_forbidden_hits per config; R0=4, R8=3)
- metadata-anchor loss (metadata-only cases 2→0 already under R8/M2; expansion must not evict expected sources entirely)

**cost:**
- 47× ~100-token zero-shot generations (minutes on a T4 / no GPU needed to re-score), 4× BM25 passes per query (still ≪1 s/case local); context identical to R0 (k5/500 unchanged) → zero context-cost increase

**why it addresses the bottleneck:**
- source anchoring already works (source@5 ≥ 0.913, presence invariant); merge policy is worth ≤5 cases (measured); of the 23 unit zero-hits, 18 are raw lexical score deficits inside/around the correct source (10 depth + 7 zero-score + 1 sub-pool) and 045 may also respond — only the query side can change scores without dense models/rerankers (forbidden); corpus-absence (017) is unfixable by retrieval

Production retrieval is NOT changed by this task; the recommendation is a future experiment only.

## 13. Phase 10 — artifact verification

| Check | Result | Detail |
|---|---|---|
| frozen_benchmark_sha | PASS | 06625f72190e3ae130447345afdc04342bd19cb76f842285706480cba7765b81 |
| frozen_benchmark_rows | PASS | 47 |
| task72_results_rows | PASS | 47 |
| task72_failure_rows | PASS | 47 |
| r0_byte_exact_gate | PASS | 47/47 |
| r7_rescore_gate | PASS | ceiling 0.7403/31/10 matched |
| source_presence_invariant | PASS | true |
| zero_contract_violations | PASS | R0/R7/R8/R9/M2 = 0 |
| prior_task_artifact_shas_unchanged | PASS | 7 files match their recorded/known shas |
| prior_artifact_mtimes_predate_task72_outputs | PASS | all prior mtimes < earliest task72 output mtime |
| no_tracked_file_modifications | PASS | git diff empty |
| test_suite_baseline_equal | PASS | ran=462 failures=0 errors=2 skipped=1 |

All Phase-10 checks pass: **True**

## 14. Phase 11 — tests and git status

- Test suite: `PYTHONPATH=src python3 -m unittest discover -s tests` → **462 ran, 0 failures, 2 errors, 1 skipped** (baseline-equal: True; errors are the known pre-existing faiss tests: test_from_prebuilt_loads_index, test_from_prebuilt_stores_query_prefix)
- `git diff` (tracked files): empty — no tracked modifications
- Untracked: 89 files total (repo convention: prior-task artifacts are also untracked); task72 files: `svk-corpus/data/evaluation/task72_failure_cases.jsonl`, `svk-corpus/data/evaluation/task72_metrics.json`, `svk-corpus/data/evaluation/task72_retrieval_results.jsonl`, `svk-corpus/data/reports/task72_within_source_retrieval.json`, `svk-corpus/data/reports/task72_within_source_retrieval.md`, `svk-corpus/experiments/task72/`
- Colab: session `task71r7` already gone (`colab stop` → session not found); no active session to stop; no GPU/model work performed.

## 15. Constraint confirmation

- training started: **NO**
- sft03 started: **NO**
- dapt02 started: **NO**
- dense model downloaded: **NO**
- production retrieval changed: **NO**
- frozen benchmark modified: **NO**
- prior task artifacts modified: **NO**
- generation model or decoding changed: **NO**
- prompts altered: **NO**
- new embeddings or rerankers: **NO**

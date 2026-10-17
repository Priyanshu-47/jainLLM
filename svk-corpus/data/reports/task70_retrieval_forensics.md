# TASK 70 — Retrieval Failure Forensics (HARD STOP)

Generated: 2026-10-02 13:35:29 UTC · Report JSON sha256: `739f69d98c9f1e9403ef92792b992011c0187805707c1b569ddb5093fa527215`

Hard stop declaration: Training started **NO** · SFT-03 **NO** · DAPT-02 **NO** · Dense model downloaded **NO** · Production retrieval changed **NO** · Rerankers **NO**.

## 1. Executive result

- **Bottleneck:** PASSAGE (UNIT) RETRIEVAL — candidate ranking depth is the dominant bottleneck: unit recall@10 = 0.4103 vs source recall@10 = 0.9783; 9 of the 15 evidence-zero cases have their expected unit deeper than rank 10 in the BM25 pool (ranks 14-1484; 7 primary ranking failures + 2 hybrid width cases 011/023), 1 more unit never enters the 2000-doc pool (010). Evidence selection width is the largest immediately-harvestable secondary (+0.1085 ceiling measured by R7).
- **Evidence-zero true count:** 15 (the brief's “13” = BASE+RAG `RETRIEVAL_INSUFFICIENT` rows; 004/009 are Ev=0 but scored 1.0 via prior knowledge — see §2).
- **Best offline variant:** R7_k10_trunc1000 (EVIDENCE_K=10, TEXT_TRUNC=1000): ceiling 0.7403, Ev0 10
- **Recommended Task-71 experiment:** Adopt the measured R7 evidence window — EVIDENCE_K 5 -> 10 and TEXT_TRUNC 500 -> 1000 — in the Task-69 RAG harness (configs used by build_rag_evidence), then re-run the frozen four-arm generation evaluation to confirm the evidence-side gains translate to the frozen score, with prompt-budget and contract validation on all 47 cases.
- **Generation-side secondary:** 12/47 cases are generation-side — 8 with ev=1.0 where an arm still failed + 4 abstention-pattern outcomes (see §3) — outside Task-70 scope.

## 2. Task-69 reconstruction (baseline)

- Frozen benchmark: `06625f72190e3ae130447345afdc04342bd19cb76f842285706480cba7765b81` — 47 cases, sha re-verified.
- Retrieval config: mode-C (`unit_bm25+source_metadata combined (evaluate.py mode C, validated baseline)`), EVIDENCE_K=5, top_k=10, pool=2000, contract violations in Task-69: 0.
- **Baseline reproduction:** verified (block sha, ranks, ev scores, contracts, text order) — instrumented re-execution reproduced all 47 block shas, ranks, evidence scores, contracts and text order (integrity anchor).
- **13 vs 15 correction:** Task-70 brief cites 13 Ev=0; raw artifacts show 15 evidence-zero cases. 13 = BASE+RAG RETRIEVAL_INSUFFICIENT count; DAPT01EVAL-004 and -009 are evidence-zero too but scored 1.0 from prior knowledge in BASE+RAG (047 likewise in DAPT+RAG), so they leave the failure bucket.
- RI-13 (BASE+RAG): 002, 007, 010, 011, 013, 014, 017, 018, 021, 023, 044, 045, 047 · RI-12 (DAPT+RAG): 002, 007, 010, 011, 013, 014, 017, 018, 021, 023, 044, 045 · Ev=0-but-prior-knowledge: 004, 009
- Evidence is structurally unit-only at baseline: metadata fills (≤3) land at candidate positions 8-10 and never enter the top-5 evidence block.

## 3. Failure classification

| Class | Name | All 47 | Ev0 (15) |
|---|---|---:|---:|
| A | CORPUS_ABSENCE | 1 | 1 |
| B | SOURCE_MISS | 1 | 1 |
| C | UNIT_MISS | 1 | 1 |
| D | RANKING_MISS | 13 | 12 |
| E | METADATA_ONLY | 0 | 0 |
| F | EVIDENCE_CONTRACT_LOSS | 1 | 0 |
| G | GENERATION_FAILURE | 12 | 0 |
| H | OTHER | 18 | 0 |

- D subtypes: evidence-selection-width 6 (004, 011, 021, 023, 040, 044), passage-ranking-depth 7 (002, 007, 009, 013, 014, 018, 047).
- B = 045 (SVK-1002 in corpus, 1111 docs, but absent from the pool 2000 and unmatched by metadata).
- C = 010 (unit `SVK-2007:u09904` in corpus, never enters the pool).
- A = 017 (expected unit `SVK-2027:u095770` does not exist anywhere in the corpus — genuine absence).
- F = 026 (supporting keyterms exist in selected items' full text but not the 500-char truncated view).
- G (12) = evidence sufficient but generation-side failure flagged: 8 cases with ev=1.0 where an arm failed (5 GENERATION_FAILURE on BASE+RAG — 015/019/031/035/041; 3 where only DAPT+RAG failed — 001/025/027), plus 4 abstention cases whose evidence block carries forbidden patterns (036/037 GENERATION_FABRICATION; 038 ABSTENTION_CORRECT; 039 RETRIEVAL_RISK_CONTRIBUTED on the corpus-absence query). Full row-level reasons: `data/evaluation/task70_retrieval_failure_cases.jsonl`.

## 4. Evidence-zero forensic table (15 rows; brief's RI-13 flagged)

| Case | RI-13 | Class | Src rank | Unit rank (ev) | Unit pool rank | Meta found | Support top-10 full | Support in ev-5 |
|---|:--:|---|---:|---:|---|:--:|---|---|
| 002 | ✓ | D | 1 | - | 196 | Y | - | - |
| 004 | · | D | 1 | 2 | 2 | Y | [0] | - |
| 007 | ✓ | D | 8 | - | 14 | Y | - | - |
| 009 | · | D | 2 | - | 886 | N | - | - |
| 010 | ✓ | C | 1 | - | - | N | - | - |
| 011 | ✓ | D | 3 | - | 1484 | N | [1] | - |
| 013 | ✓ | D | 6 | - | 986 | N | - | - |
| 014 | ✓ | D | 5 | - | 186 | N | - | - |
| 017 | ✓ | A | 1 | - | - | N | - | - |
| 018 | ✓ | D | 1 | - | 119 | N | - | - |
| 021 | ✓ | D | 8 | - | - | Y | [0] | - |
| 023 | ✓ | D | 5 | - | 75 | Y | [1] | - |
| 044 | ✓ | D | 1 | 6 | 4 | Y | [0] | - |
| 045 | ✓ | B | - | - | - | N | - | - |
| 047 | ✓ | D | 1 | - | 873 | N | - | - |

'RI-13' ✓ = the 13 BASE+RAG `RETRIEVAL_INSUFFICIENT` cases; · = 004/009 (Ev=0, prior-knowledge score 1.0). Per-case machine-readable facts: `data/evaluation/task70_retrieval_failure_cases.jsonl`.

## 5. Retrieval metrics

- Source level (n=46, no-expected-source excluded: 1): R@1 0.7174 · R@3 0.8696 · R@5 0.913 · R@10 0.9783 · MRR 0.804 · zero-hit: 045
- Unit level (n=39): R@1 0.2821 · R@3 0.3846 · R@5 0.3846 · R@10 0.4103 · MRR 0.3333 · in pool@2000: 29/39 (0.7436)
- Metadata-only cases (no unit provenance): 007, 021 · source-hit-but-unit-miss: 22 cases
- Reading: source retrieval is nearly solved (R@10 0.978); passage retrieval is not (R@10 0.410; 1 in 4 expected units never enters the 2000-doc candidate pool).
- NOT_MEASURED: graded/passage-level relevance: NOT_MEASURED (no graded qrels exist); recall@k for the 1 corpus-absence case: NOT_APPLICABLE (no expected source); unit recall for the 8 cases without unit_ids provenance: NOT_MEASURED
- Generation conversion (Task-69 BASE+RAG): 21/28 evidence-positive cases reached GROUNDED_SUCCESS (0.75). BASE+RAG Task-69: cases with computable evidence_answer_score>0 that reached GROUNDED_SUCCESS; denominator excludes the 15 ev=0 rows and the 4 abstention rows with null score (036-039).

## 6. Offline variant results (Phase 5, R1-R7)

| Variant | ev_k | trunc | top_k | expand | union | srcR@5 | unitR@5 | ceiling | Ev0 | abst hits | vs T69 blocks |
|---|---:|---:|---:|:--:|:--:|---:|---:|---:|---:|---:|---|
| R1_baseline | 5 | 500 | 10 | Y | N | 0.913 | 0.3846 | 0.6318 | 15 | 4 | 47/47 |
| R2_evidence_k10 | 10 | 500 | 10 | Y | N | 0.913 | 0.3846 | 0.7209 | 12 | 4 | 0/47 |
| R3_depth20 | 5 | 500 | 20 | Y | N | 0.913 | 0.3846 | 0.6318 | 15 | 4 | 47/47 |
| R4_union_k20_ev10 | 10 | 500 | 20 | Y | Y | 0.913 | 0.3846 | 0.7132 | 12 | 4 | 0/47 |
| R5_expansion_off | 5 | 500 | 10 | N | N | 0.8913 | 0.4103 | 0.655 | 14 | 4 | 0/47 |
| R6_trunc1000_k5 | 5 | 1000 | 10 | Y | N | 0.913 | 0.3846 | 0.6395 | 15 | 4 | 11/47 |
| R7_k10_trunc1000 | 10 | 1000 | 10 | Y | N | 0.913 | 0.3846 | 0.7403 | 10 | 4 | 0/47 |

- R1 must reproduce Task-69 blocks (blocks_identical_to_task69=47/47) — integrity anchor
- R3 is measured, not assumed: identical blocks to R1 would prove positional first-K selection makes depth-increase inert for evidence
- R5 ablates the repository's existing fold+alias expansion via harness-level monkeypatch only (svk_corpus source untouched, index rebuilt)
- RAG frozen score NOT_RUN for all variants (no local GPU; no training/inference spend authorized in this task)
- **R1** reproduces Task-69 byte-exact (47/47) — integrity anchor. **R7** is best: ceiling 0.6318→0.7403, Ev0 15→10, recovering exactly 004, 011, 021, 023, 044.
- Abstention forbidden-hit count and contract violations are invariant across all seven variants.
- Frozen RAG scores for variants = NOT_RUN (no local GPU; documented in §9).

## 7. Bottleneck analysis

| Root cause (Ev0, primary class) | Count | Share | Members |
|---|---:|---:|---|
| Passage ranking depth (unit in pool, rank > 10) | 7 | 46.7% | 002, 007, 009, 013, 014, 018, 047 |
| Evidence selection width (support in candidates 6-10, ≤500 chars) | 3 | 20.0% | 004, 021, 044 |
| Selection width + truncation (support in 6-10 beyond 500 chars) | 2 | 13.3% | 011, 023 |
| Unit pool miss (unit in corpus, outside pool 2000) | 1 | 6.7% | 010 |
| Corpus absence (expected unit not in corpus) | 1 | 6.7% | 017 |
| Source miss (source in corpus, never retrieved) | 1 | 6.7% | 045 |

- Retrieval-side failures: 17/47 (A+B+C+D+F); generation-side: 12/47; clean: 18/47.
- **Dominant bottleneck = passage (unit) retrieval ranking**: 7 of 15 Ev0 primarily (46.7%) + 2 hybrid width cases (011/023) whose expected units are also deep in the pool (1484/75) → 9/15 Ev0 involve an expected unit beyond rank 10; unit R@10 0.4103 and pool hit 0.7436 confirm it at the metric level.
- **Secondary, fully harvestable = evidence selection width**: R7 closes 5/15 (33.3%); truncation alone adds almost nothing (R6, +0.0077).
- **Inert/negative knobs:** depth (R3 byte-identical, harms source R@10), metadata union (R4 < R2 — fills beat deeper units at positions 8-10), expansion off (R5 mixed).
- **Residual after best variant:** 10 Ev0 cases (7 deep-unit + 010 + 017 + 045) are unreachable by evidence-window changes — they need candidate-level retrieval work.
- **Generation side:** 12/47 (25.5%) answer-side failures with sufficient evidence — real, but out of Task-70 scope.

## 8. Recommended TASK 71 experiment (ONE retrieval-side change)

**Change:** Adopt the measured R7 evidence window — EVIDENCE_K 5 -> 10 and TEXT_TRUNC 500 -> 1000 — in the Task-69 RAG harness (configs used by build_rag_evidence), then re-run the frozen four-arm generation evaluation to confirm the evidence-side gains translate to the frozen score, with prompt-budget and contract validation on all 47 cases.

**Why it targets the measured failure:** It directly closes the measured evidence-selection class: 5 of the 15 evidence-zero cases (004, 011, 021, 023, 044) have supporting evidence inside the existing BM25 top-10 candidates but outside the selected top-5 block (3) or beyond the 500-char per-item truncation (2). Offline measurement: ceiling 0.6318 -> 0.7403 (+0.1085), Ev0 15 -> 10, abstention forbidden-hit count invariant 4/4, contract violations 0, baseline blocks reproduce byte-exact under R1.

**Expected artifact:** data/evaluation/task71_rag_results.jsonl + task71_rag_evaluation.{md,json}: four frozen arms re-run with the widened evidence window, prompt token/char budgets per case, contract checks, and per-case deltas vs Task-69.

**Metrics that should improve:**
- evidence ceiling mean 0.6318 -> >= 0.7403 (already measured offline; must hold under generation rerun)
- evidence-zero cases 15 -> 10 (measured offline)
- BASE+RAG frozen macro 0.5816 -> >= 0.64 (5 recovered cases at historical conversion ~0.75 imply ~3 additional full credits)
- contract violations 0 -> 0; abstention forbidden-hit count 4 -> 4 (invariant)

**Regression risks:**
- Prompt growth: +5 items x up to 1000 chars (~+4.5k chars median block) — must stay within the Qwen3-8B context and the Task-69 prompt budget; measure per-case tokens.
- none_of / distractor pollution: items 6-10 add text that may trigger forbidden patterns at generation time (evidence-side count was invariant 4/4, but generation-side behavior is unverified).
- Generation distraction: the 7 GENERATION_FAILURE cases may degrade with more context (unmeasured without the GPU harness).
- Metadata fills must remain at candidate positions 8-10 under top_k=10; R3 proved that pushing fills past rank 10 costs source recall@10 (0.9783 -> 0.9348) for zero evidence gain.
- Production governance: EVIDENCE_K=5 / TEXT_TRUNC=500 are the Task-9/14 production contract defaults — adopting R7 downstream is a governed config change, not a silent default edit (no production change happens in Task 70).

**Honest expected value vs the alternative:** evidence-window widening is measured (+0.1085 ceiling, 5 full recoveries, invariants held) with near-zero implementation risk; at the historical conversion rate 0.75 it implies roughly +3 full credits (+0.06-0.07 macro on the 0.5816 BASE+RAG baseline). Source-anchored within-source retrieval addresses the residual ranking class (up to 8 cases, ≤ +0.17 macro ceiling headroom) but is unmeasured and requires new candidate logic — lower confidence expected value per unit of risk, hence recommended as the *following* experiment, not this one.

**Residual bottleneck not addressed:** 10 evidence-zero cases remain after R7: 7 with the expected unit at BM25 pool ranks 14-1484 (passage ranking depth), 1 unit absent from the corpus (017), 1 source never retrieved (045), 1 expected unit in corpus but outside the 2000-doc pool (010). These require candidate-level retrieval work — e.g. source-anchored within-source BM25 (existing BM25Index allowed= parameter) — which is deliberately NOT implemented in Task 70 (Phase-7 constraint) and is the leading follow-up candidate after Task 71.

Not implemented in Task 70 (Phase-7 constraint). No production file was changed.

## 9. NOT_MEASURED

1. **Frozen RAG scores for variants R2-R7** — No local GPU / transformers stack on this host; generation harness runs on Colab T4. Evidence-side metrics (ceiling, Ev0) are computed offline and are the variant-selection basis.
2. **Graded (partial) relevance judgments for retrieved units** — No human/LLM graded qrels exist for the 47 queries; binary provenance + support-group tests are the available labels. Not manufactured.
3. **Unit recall for the 8 cases without unit provenance and source recall for DAPT01EVAL-039 (no expected source)** — Ground truth absent in the frozen benchmark; excluded from the corresponding denominators (documented: n_unit_labeled=39, n_source_level=46).
4. **Within-source rank distribution of expected units (anchoring surface)** — Would require implementing source-anchored candidate retrieval — intentionally NOT implemented in Task 70; it is the leading follow-up candidate after Task 71 (see §8).
5. **Generation-time effect of the widened evidence window (R7)** — Requires the frozen GPU inference harness; covered by the Task-71 recommendation.

## 10. Integrity and hashes

- Frozen benchmark sha256: `06625f72190e3ae130447345afdc04342bd19cb76f842285706480cba7765b81` (verified before and after).
- Input hashes:
  - frozen_dapt01_eval_cases: `06625f72190e3ae130447345afdc04342bd19cb76f842285706480cba7765b81`
  - rag_corpus: `4db164bc70e68b4f89837a9f3d3f3bc7fc126d99c826776ba9bf832f070ff8cf`
  - source_manifest: `b96e572f8d97891cc5b472bd21d4355b3b60b2afc74e48d70716ce95bf3293f2`
  - retrieval_aliases: `3fc7f3894bb5377bda9a5058e01363f0025382b9900efeb919c8d6a1a819df7a`
  - task69_rag_results: `84a96f243c2b9b093edaff4acee8ea7a5111ecbee44356b72b7cab4386424709`
  - task69_rag_evidence: `a51f59d88dad86ebea79cd158b69f845c0f02f3090a92e935f2c5956492d0f33`
  - task69_rag_prompts: `00096f61a4a2aea525b2f1bfe71449b626bc17a60073e4b4e9dac05f6edd5b8e`
  - task69_retrieval_metrics: `c642e463c35ed15ab92d2fe9335b91f77af1f99912c1ec17bef670c261aaae73`
  - task69_rag_comparison: `a9732eb9fd4acf3ca0210a177b9a751f5e494ead7b43f9d901dfe8e7d013d1f9`
- Task-70 artifact hashes:
  - task70_phase1_4: `c9c3de0f58bf2b21177d6d068004586a0e88b4e01b52a0af1d7cbcca1a0002e6`
  - task70_retrieval_failure_cases: `c6024bd8a89b2fd6004a3f11fdf3257b545e18004f639d5ac1ac9feab0810a59`
  - task70_variants: `41a90f1ad608f6719221261e53a0728c1e7eed894094dd3b73bd0b7ebe60772f`
- Report JSON: `data/reports/task70_retrieval_forensics.json` sha256 `739f69d98c9f1e9403ef92792b992011c0187805707c1b569ddb5093fa527215`
- Baseline reproduction: verified (block sha, ranks, ev scores, contracts, text order); contract violations by variant: R1_baseline=0, R2_evidence_k10=0, R3_depth20=0, R4_union_k20_ev10=0, R5_expansion_off=0, R6_trunc1000_k5=0, R7_k10_trunc1000=0
- Tests: FAILED (ran=462, errors=2, failures=0, skipped=1) — matches baseline: True (baseline for this task = 462 tests, 2 pre-existing faiss errors, 1 skip)
- Git: repo root `/home/azureuser/jainLLM`; diff empty = True; tracked files modified = none; production files modified = none; frozen eval files modified = none; Task-70 untracked paths (6): data/evaluation/task70_phase1_4.json, data/evaluation/task70_retrieval_failure_cases.jsonl, data/evaluation/task70_variants.json, data/reports/task70_retrieval_forensics.json, data/reports/task70_retrieval_forensics.md, experiments/task70/; pre-existing untracked from tasks 62-69: 63 (untouched).

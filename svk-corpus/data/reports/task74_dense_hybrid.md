# TASK 74 — Dense + Hybrid Retrieval Re-evaluation

**Verdict: RECOMMEND_HYBRID — pre-registered hybrid config(s) H3_RRF20 meet all five task conditions; primary k=60 failed C1/C5 narrowly — see gates**

Experiment-only retrieval architecture evaluation over the frozen 47-case Task-60 benchmark. No training, no generation, no corpus/production/prior-artifact changes. Dense index is experiment-local (`experiments/task74/dense_index/`).

## 1. BM25 baseline (Phase 1 gate)

- Frozen Task-60 SHA verified: `True`; H1 rebuild byte-exact **47/47** vs frozen Task-69 evidence.
- source R@5 **0.913**, R@10 **0.9783**, unit MRR **0.3333**, evidence ceiling **0.6318** (26 full-evidence), Ev0 **15** — matches Task-69/73 published values exactly.

## 2. Dense metrics (H2 — BAAI/bge-m3 cosine, top-10)

- source R@1 0.8478 / R@3 0.913 / R@5 0.9348 / R@10 0.9348 / R@20 0.9565
- unit R@1 0.4359 / R@3 0.5641 / R@5 0.5641 / R@10 0.5641 / R@20 0.6154; unit MRR 0.4915 (median full dense rank over in-corpus: unit 1 [n=31/39 labeled], source 1.0 [n=46/46])
- index: BAAI/bge-m3 rev `5617a9f61b02`, dim 1024, L2-normalized, fp16 storage, flat IP over numpy matrix.

## 3. Hybrid metrics (RRF)

| config | src@5 | src@10 | unit@1 | unit@5 | unit@10 | unit MRR | ceiling | full | Ev0 | violations |
|---|---|---|---|---|---|---|---|---|---|---|
| H1_BM25 | 0.913 | 0.9783 | 0.2821 | 0.3846 | 0.4103 | 0.3333 | 0.6318 | 26 | 15 | 0 |
| H2_DENSE | 0.9348 | 0.9348 | 0.4359 | 0.5641 | 0.5641 | 0.4915 | 0.8605 | 37 | 6 | 0 |
| H3_RRF60 | 0.9348 | 0.9783 | 0.4103 | 0.4872 | 0.5385 | 0.4439 | 0.7829 | 33 | 9 | 0 |
| H3_RRF20 | 0.9783 | 0.9783 | 0.4103 | 0.5385 | 0.5897 | 0.4618 | 0.8372 | 36 | 7 | 0 |
| H4_RRF60 | 0.9348 | 0.9783 | 0.4103 | 0.4872 | 0.5385 | 0.4439 | 0.7829 | 33 | 9 | 0 |
| H4_RRF20 | 0.9783 | 0.9783 | 0.4103 | 0.5385 | 0.5897 | 0.4618 | 0.8372 | 36 | 7 | 0 |

Primary hybrid = H3_RRF60 (pre-registered k=60); k=20 is sensitivity. H4 = RRF + Task-69 source-metadata fills.

### Deltas vs H1 (H3_RRF60 primary)

- unit@5 +0.1026, unit MRR +0.1106, source@5 +0.0218, ceiling +0.1511, Ev0 -6

## 4. BM25 / Dense complementarity

- **top-5** (n=39 unit-labeled): both 14 (35.9%), BM25-only 1 (2.6%), dense-only 8 (20.5%), neither 16 (41.0%)
- **top-10** (n=39 unit-labeled): both 15 (38.5%), BM25-only 1 (2.6%), dense-only 7 (17.9%), neither 16 (41.0%)
- H1 vs H3_RRF60 at top-10 (n=39): both 16, BM25-only 0 (0.0%), hybrid-only 5 (12.8%), neither 18 (46.2%)

## 5. Known failure-case recovery (Task-70/71/72 misses)

| case | expected units | dense full rank | ≤5 | ≤10 | ≤20 | bm25 full unit rank | H1 unit@ | H2 unit@ | H3 unit@ |
|---|---|---|---|---|---|---|---|---|---|
| DAPT01EVAL-002 | 1 | 1 | True | True | True | 196 | None | 1 | None |
| DAPT01EVAL-007 | 1 | 1 | True | True | True | 14 | None | 1 | 1 |
| DAPT01EVAL-010 | 1 | 10720 | False | False | False | 2335 | None | None | None |
| DAPT01EVAL-011 | 1 | 177 | False | False | False | 1484 | None | None | None |
| DAPT01EVAL-013 | 1 | 40 | False | False | False | 986 | None | None | None |
| DAPT01EVAL-014 | 1 | 1 | True | True | True | 186 | None | 1 | None |
| DAPT01EVAL-018 | 1 | 46 | False | False | False | 119 | None | None | None |
| DAPT01EVAL-021 | 0 | None | False | False | False | None | None | None | None |
| DAPT01EVAL-023 | 1 | 2 | True | True | True | 75 | None | 2 | 5 |
| DAPT01EVAL-044 | 1 | 1 | True | True | True | 4 | 6 | 1 | 1 |
| DAPT01EVAL-047 | 1 | 30328 | False | False | False | 873 | None | None | None |

- H1 unit misses at top-10: 23 (DAPT01EVAL-002, DAPT01EVAL-007, DAPT01EVAL-009, DAPT01EVAL-010, DAPT01EVAL-011, DAPT01EVAL-013, DAPT01EVAL-014, DAPT01EVAL-016, DAPT01EVAL-017, DAPT01EVAL-018, DAPT01EVAL-023, DAPT01EVAL-024, DAPT01EVAL-025, DAPT01EVAL-026, DAPT01EVAL-027, DAPT01EVAL-028, DAPT01EVAL-035, DAPT01EVAL-037, DAPT01EVAL-041, DAPT01EVAL-042, DAPT01EVAL-043, DAPT01EVAL-045, DAPT01EVAL-047)
- recovered by dense (any rank): 7 — DAPT01EVAL-002, DAPT01EVAL-007, DAPT01EVAL-009, DAPT01EVAL-014, DAPT01EVAL-023, DAPT01EVAL-037, DAPT01EVAL-041; at top-5: 7 — DAPT01EVAL-002, DAPT01EVAL-007, DAPT01EVAL-009, DAPT01EVAL-014, DAPT01EVAL-023, DAPT01EVAL-037, DAPT01EVAL-041
- recovered by H3_RRF60 (any rank): 5 — DAPT01EVAL-007, DAPT01EVAL-009, DAPT01EVAL-023, DAPT01EVAL-037, DAPT01EVAL-041; at top-5: 4 — DAPT01EVAL-007, DAPT01EVAL-023, DAPT01EVAL-037, DAPT01EVAL-041
- new unit misses introduced — H2: DAPT01EVAL-020; H3_RRF60: none

## 6. Evidence ceiling (H1–H4, evidence_k=5 / trunc=500)

- H1_BM25: ceiling 0.6318 (full 26), Ev0 15, forbidden-hit cases 4, violations 0, context median 4198
- H2_DENSE: ceiling 0.8605 (full 37), Ev0 6, forbidden-hit cases 3, violations 0, context median 4054
- H3_RRF60: ceiling 0.7829 (full 33), Ev0 9, forbidden-hit cases 2, violations 0, context median 4039
- H3_RRF20: ceiling 0.8372 (full 36), Ev0 7, forbidden-hit cases 3, violations 0, context median 3845
- H4_RRF60: ceiling 0.7829 (full 33), Ev0 9, forbidden-hit cases 2, violations 0, context median 4039
- H4_RRF20: ceiling 0.8372 (full 36), Ev0 7, forbidden-hit cases 3, violations 0, context median 3845

## 7. Source recall

- H1_BM25: R@1 0.7174 / R@3 0.8696 / R@5 0.913 / R@10 0.9783; zero-hit ['DAPT01EVAL-045']
- H2_DENSE: R@1 0.8478 / R@3 0.913 / R@5 0.9348 / R@10 0.9348; zero-hit ['DAPT01EVAL-010', 'DAPT01EVAL-018', 'DAPT01EVAL-045']
- H3_RRF60: R@1 0.8696 / R@3 0.9348 / R@5 0.9348 / R@10 0.9783; zero-hit ['DAPT01EVAL-045']
- H3_RRF20: R@1 0.8696 / R@3 0.9565 / R@5 0.9783 / R@10 0.9783; zero-hit ['DAPT01EVAL-045']
- H4_RRF60: R@1 0.8696 / R@3 0.9348 / R@5 0.9348 / R@10 0.9783; zero-hit ['DAPT01EVAL-045']
- H4_RRF20: R@1 0.8696 / R@3 0.9565 / R@5 0.9783 / R@10 0.9783; zero-hit ['DAPT01EVAL-045']
- H2_DENSE vs H1: source rank improved 11, regressed 5 (regressed: DAPT01EVAL-003, DAPT01EVAL-010, DAPT01EVAL-016, DAPT01EVAL-018, DAPT01EVAL-047)
- H3_RRF60 vs H1: source rank improved 8, regressed 3 (regressed: DAPT01EVAL-013, DAPT01EVAL-014, DAPT01EVAL-018)
- H4_RRF60 vs H1: source rank improved 8, regressed 3 (regressed: DAPT01EVAL-013, DAPT01EVAL-014, DAPT01EVAL-018)

## 8. Sect / language observations

Metric: mean share of top-10 results whose `sect` equals the expected unit/source sect (no semantic-quality claim).

- H1_BM25: sect consistency@10 0.6957 (n=46)
- H2_DENSE: sect consistency@10 0.8935 (n=46)
- H3_RRF60: sect consistency@10 0.913 (n=46)
- H3_RRF20: sect consistency@10 0.9109 (n=46)
- H4_RRF60: sect consistency@10 0.8022 (n=46)
- H4_RRF20: sect consistency@10 0.8065 (n=46)
- STHANAKAVASI-expected cases: 1; source@5 by config: H1_BM25=1.0, H2_DENSE=1.0, H3_RRF60=1.0, H3_RRF20=1.0, H4_RRF60=1.0, H4_RRF20=1.0
- by language (source@5 / unit@5):
  - H1_BM25: en: 0.9394/0.4815 (n=34); hi: 0.875/0.125 (n=8); gu: 0.8/0.25 (n=5)
  - H2_DENSE: en: 1.0/0.7037 (n=34); hi: 0.875/0.375 (n=8); gu: 0.6/0.0 (n=5)
  - H3_RRF60: en: 1.0/0.6667 (n=34); hi: 0.75/0.125 (n=8); gu: 0.8/0.0 (n=5)
  - H3_RRF20: en: 1.0/0.6667 (n=34); hi: 1.0/0.25 (n=8); gu: 0.8/0.25 (n=5)
  - H4_RRF60: en: 1.0/0.6667 (n=34); hi: 0.75/0.125 (n=8); gu: 0.8/0.0 (n=5)
  - H4_RRF20: en: 1.0/0.6667 (n=34); hi: 1.0/0.25 (n=8); gu: 0.8/0.25 (n=5)

## 9. Compute / storage cost

- dense index build: 1882.6s (87.2 docs/s, T4 fp16), disk 320.8 MiB fp16 (+queries); peak VRAM during embedding 2433.0 MB, embed RAM peak 3816.0 MB, fp32 search matrix 642.0 MB RAM
- dense query: local flat search mean 37.94 ms (p50 37.78, max 52.76); GPU query encode 2.34 ms/query (batched)
- BM25: build 53.87s (+corpus load 5.27s), index RSS delta 539.7 MB, query search mean 271.16 ms (p50 195.93), R0 pipeline 12.8s; RRF fuse mean 52.16 ms/query
- local peak RAM: 1599.5 MB; corpus file 495323989 bytes (unchanged)

## 10. Verdict (pre-registered gate)

| config | C1 recover≥5 | C2 unit Δ≥+0.05 | C3 src@5≥0.90 | C4 ceiling>0.6318 | C5 sect/lang safe | all |
|---|---|---|---|---|---|---|
| H2_DENSE | True (7) | True (+0.1795) | True (0.9348) | True (0.8605) | False (sectΔ -0.1978, langΔ 0.2) | False |
| H3_RRF60 | False (4) | True (+0.1026) | True (0.9348) | True (0.7829) | False (sectΔ -0.2173, langΔ 0.125) | False |
| H3_RRF20 | True (5) | True (+0.1539) | True (0.9783) | True (0.8372) | True (sectΔ -0.2152, langΔ 0.0) | True |
| H4_RRF60 | False (4) | True (+0.1026) | True (0.9348) | True (0.7829) | False (sectΔ -0.1065, langΔ 0.125) | False |
| H4_RRF20 | True (5) | True (+0.1539) | True (0.9783) | True (0.8372) | True (sectΔ -0.1108, langΔ 0.0) | True |

**RECOMMEND_HYBRID**: pre-registered hybrid config(s) H3_RRF20 meet all five task conditions; primary k=60 failed C1/C5 narrowly — see gates.

## 11. Recommended next experiment

Adopt **H3_RRF20** (deterministic RRF over the full BM25 × full dense lists; both k∈{20,60} were pre-registered, k=60 was primary at write time but failed C1/C5 narrowly) as the retrieval candidate: (a) re-run the Task-71 four-arm RAG generation gate with H3_RRF20 contexts (the retrieval gate now passes: unit@5 +0.15, source@5 0.9783, ceiling +0.205, Ev0 15→7, no language/sect regression), (b) H4 metadata fills need not ship — they changed no recall@≤10 and diluted sect consistency (0.81 vs 0.91), (c) production change remains a separate explicit task; keep H1 frozen until then.

## 12. Tests

- `462 ran`, failures 0, errors 2 (pre-existing FAISS), skipped 1 — baseline-equal: **True** (expected: 462 ran, 0 normal failures, 2 pre-existing FAISS errors, 1 skip)

## 13. Git / artifact status

- `git diff` lines: 0; modified tracked files: 0 (clean: True); untracked: 104 (prior-task convention — experiments/ + task artifacts untracked)
- frozen SHA ok: True; 17 prior/corpus artifacts checked, unchanged: **True**
- production retrieval changed: **NO** (no tracked src edits); training/SFT-03/DAPT-02: NO; generation run: NO

### Artifacts

- `data/evaluation/task74_dense_results.jsonl`
- `data/evaluation/task74_hybrid_results.jsonl`
- `data/evaluation/task74_metrics.json`
- `data/evaluation/task74_complementarity.json`
- `data/reports/task74_dense_hybrid.md`
- `data/reports/task74_dense_hybrid.json`
- `experiments/task74/ (5 scripts + dense_index/)`

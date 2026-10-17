# TASK 69 — DAPT-01 + Governed RAG Evaluation

**Verdict: BASE + GOVERNED RAG (0.5816 macro / 25 pass-all) is the recommended architecture on this benchmark.**
RAG adds **+0.3795** macro keyterm over BASE and **+0.2943** over DAPT-01; DAPT-01's pre-RAG gain (+0.0639)
disappears under RAG (**−0.0213**). All four arms use the same frozen 47 cases, same system prompt, greedy
decoding, 192-token cap, seed 42; both RAG arms received byte-identical evidence contexts (verified).

## 1. Four-arm scores (frozen metric, score_task60 imported verbatim)

| Arm | macro keyterm | pass-all |
|---|---|---|
| BASE (no RAG) | 0.2021 | 6/47 |
| DAPT-01 (no RAG, incumbent) | 0.266 | 8/47 |
| **BASE + RAG** | **0.5816** | **25/47** |
| DAPT-01 + RAG | 0.5603 | 23/47 |

- RAG gain over BASE: **0.3795** (22 improved, 3 regressed)
- RAG gain over DAPT-01: **0.2943** (18 improved, 0 regressed)
- DAPT-01 gain within RAG: **-0.0213** (4 improved, 5 regressed)
- DAPT-01 gain without RAG: 0.0639 (8 improved, 2 regressed)
- Independent recompute from raw outputs reproduced all four numbers exactly (integrity check).

## 2. Retrieval quality (BM25 + source-metadata, evaluate.py mode C; no dense channel)

- Corpus: 164,238 documents, 85 sources; contract violations: 0
- Source-level Recall@5 **0.913**, Recall@10 **0.9783**, MRR **0.804**, zero-hit 1 (DAPT01EVAL-045, expected source absent from corpus)
- Unit-level MRR 0.3333, unit hit@10 16/46 (explicit unit provenance is rare and hard for lexical retrieval)
- Evidence ceiling: mean evidence_answer_score **0.6318**, full-ceiling 26/43 non-abstention cases
- Both RAG arms reach answer_mean 0.6124 (gap to ceiling -0.0194) — generation nearly saturates what evidence allows; no arm exceeds its ceiling.
- Abstention evidence: forbidden-pattern present in context 4/4 — retrieval surfaces risky numbers/dates for all four abstention cases.

## 3. Failure attribution (retrieval vs generation)

| | retrieval-side | generation-side | success | prior knowledge |
|---|---|---|---|---|
| BASE + RAG | 15 | 7 | 22 | 3 |
| DAPT-01 + RAG | 14 | 10 | 19 | 4 |

- **RETRIEVAL_INSUFFICIENT (ev=0)**: 13 cases for BASE+RAG
  (002, 007, 010, 011, 013, 014, 017, 018, 021, 023, 044, 045, 047) — lexical retrieval never surfaced the answer keyterms; the dominant remaining failure mode.
- **GENERATION_FAILURE (answer < ceiling)**: 5 for BASE+RAG (015, 019, 031, 035, 041), 8 for DAPT-01+RAG — evidence present, model failed to use it; DAPT+RAG adds 001/025/026/027 regressions.
- **GENERATION_FABRICATION (abstention fail, pattern absent from context)**: 036/037 for BASE+RAG (e.g. 037 asserts "1658" when the regex hit was only 17xx/18xx elsewhere), 037/038 for DAPT-01+RAG.
- **RETRIEVAL_RISK_CONTRIBUTED**: 039 — evidence itself contains the forbidden "45 Agams" pattern and the model repeats it; 1 case for BASE+RAG, 2 for DAPT-01+RAG (036 too).
- **PRIOR_KNOWLEDGE (answer=1 despite ev=0)**: 3 for BASE+RAG (004, 009, 040) — correct without evidence.

## 4. Category highlights (macro keyterm, BASE → DAPT → BASE+RAG → DAPT+RAG)

- Jain terminology: 0.0 → 0.0 → **0.75** → 0.5
- Source attribution: 0.0 → 0.125 → **0.75** → **0.75**
- Practice: 0.375 → 0.625 → **0.875** → **0.875**
- Prakrit: 0.0 → 0.375 → 0.5 → **0.625**
- Sthānakavāsī distinction: 1.0 → 0.75 → 0.875 → **1.0** (only category where DAPT+RAG is best)
- Sthānakavāsī terminology: 0.0 → 0.25 → **0.75** → **0.75**
- Agam grounded: 0.25 → 0.0833 → **0.9167** → 0.5
- Languages (en/gu/hi): BASE+RAG 0.6961/0.2/0.3333 vs DAPT+RAG 0.6225/0.2/0.5208 — Gujarati stays weak (0.2 both), Hindi favours DAPT+RAG (0.5208 vs 0.3333).

## 5. Abstention

Correct abstentions: BASE 0/4, DAPT 0/4, **BASE+RAG 1/4**, DAPT+RAG 0/4. Category mean: 0.0 / 0.0 / 0.25 / 0.0. All four abstention cases retrieve contexts containing forbidden patterns; only case 038 abstained correctly under RAG. Evidence does not by itself prevent fabrication — the model must still refuse the risky pattern (see failure classes above).

## 6. Behaviour & attribution

- Answer length median: base 199 / dapt 330 / base+rag 162 / dapt+rag 795 chars; DAPT+RAG is markedly verbose (median 795, many at the 192-token cap).
- Repeated loops (Task-68 detector): base 0, dapt 1, base+rag 1, **dapt+rag 5** — DAPT+RAG loops on 5 cases (evidence + adapter compounding).
- Literal "INFRINGEMENT" tokens: 0 in all four arms.
- Attribution: cited-evidence-author base 13, dapt 13, base+rag 7, **dapt+rag 16** (highest); attribution-word markers 16/11/10/13.

## 7. Recommended architecture

**BASE (Qwen3-8B-Base, no DAPT) + governed retrieval (BM25 + source-metadata mode C, EVIDENCE_K=5)**
— highest macro (0.5816) and pass-all (25), cheapest, no training. DAPT-01 remains the default *without* RAG
(0.2660 > 0.2021) but does not add value once evidence is provided (−0.0213); its verbosity/looping under RAG
is an active negative. Retrieval-side headroom (13 ev=0 cases) is the next lever: the single largest failure
bucket sits in retrieval, not generation (gap-to-ceiling for BASE+RAG only −0.0194).

## 8. Integrity, provenance, environment

- Frozen cases sha256 **06625f72190e3ae130447345afdc04342bd19cb76f842285706480cba7765b81** — verified, never modified.
- DAPT-01 adapter sha256 **9b4d2bdcfe089118d0634815596b628506a83c434d3863cff7a731cba75a58e9** (matches Task-59 forensic audit); adapter_config from
  .bench_ckpt/checkpoint-3893 (byte-differs from Task-59-recorded final, semantic fields identical — documented).
- Identical evidence contexts both RAG arms: **verified** (context_sha256 match per case, prompts file
  sha256 00096f61a4a2aea5…); identical input prompts (incl. template) across arms: verified.
- Generation host: **Google Colab T4 (google-colab-cli; NOT Kaggle)** — T4, transformers 5.0.0 / peft 0.19.1 / bnb 0.50.2 pinned;
  torch 2.11.0+cu130 + python 3.13.15 (Colab preinstalled; deviation from Task-60
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
- `data/evaluation/task69_{base,dapt}_rag_results.jsonl` — raw generation outputs
- `data/evaluation/task69_rag_evidence.jsonl`, `task69_rag_prompts.jsonl`, `task69_retrieval_metrics.json`,
  `task69_rag_run_metadata.json`
- `data/reports/task69_rag_evaluation.json` — structured report
- `experiments/task69/{build_rag_evidence,task69_rag_infer,score_task69_rag,build_task69_report}.py`

**HARD STOP: NO TRAINING WAS RUN IN TASK 69** (no SFT-03, no DAPT-02, no Kaggle, no dataset curation,
no human review gate).

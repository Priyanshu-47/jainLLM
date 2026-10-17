# TASK 82 — Four-Arm Generation Gate (Optimized H3_RRF20, BM25 pool=250)

**Verdict: `GENERATION_GATE_FAIL`**

**Final status:**

- Four-arm evaluation complete: **YES**
- Optimized BASE + RAG: macro **0.695**, pass-all **32**
- Optimized DAPT + RAG: macro **0.6738**, pass-all **30**
- Generation-quality regressions: **1** (DAPT01EVAL-037)
- Abstention gate: **FAIL**; loop gate: **PASS**
- DAPT value under optimized RAG: **NO** (adds no positive value; equality-tolerance gate FAIL)
- Frozen benchmark integrity: **PASS**; production default changed: **NO**; training started: **NO**

## 1. Executive summary

| Arm | macro key-term | pass-all | Δ vs Task-75 macro | Δ vs Task-75 pass |
|---|---|---|---|---|
| A BASE no-RAG | 0.2021 | 6 | +0.0 | +0 |
| B DAPT-01 no-RAG | 0.266 | 8 | +0.0 | +0 |
| C BASE + optimized RAG | 0.695 | 32 | +0.0 | +0 |
| D DAPT-01 + optimized RAG | 0.6738 | 30 | -0.0212 | -1 |

- RAG gain (C−A): **+0.4929** macro; (D−B): **+0.4078**.
- DAPT value under optimized RAG (D−C): **-0.0212** macro ([] improved / 1 regressed) → NO — DAPT still adds no positive value under optimized RAG (D−C = -0.0212 macro, driven entirely by the single regressed case 037); the registered equality-tolerance gate (|D−C| <= 0.02) FAILED, so numeric parity with Task-75 is not confirmed.
- Evidence ceiling: **0.8372** (36/43 non-abstention full; Ev0=7) — identical to Task-75.

## 2. Verified setup and hashes

- Frozen benchmark sha ok: **True** (06625f72…)
- DAPT-01 adapter sha ok: **True** (9b4d2bdcfe089118…)
- Task-81 pool-250 reproduction: **PASS** (unit@5=0.5385 src@5=0.9783 ceiling=0.8372 Ev0=7)
- Evidence contexts identical to Task-75: **35/47** (breakdown: {'reorder_same_set': 6, 'one_item_swap': 4, 'channel_header_only': 2}; all ceiling deltas zero: True)
- Generation protocol identical to Task-75 (greedy/192/seed42/4-bit-nf4/fp16): **True**
- Prompts sha (Task-82): `6d8d40cfeaad7f868fdc4b405fd460630e342c68e13ae936458b95cc763393c0`; (Task-75): `302f6c917b538bb440d244eeeba9aba35756186bef04cb1cd89415f65a774409` — differ only by the 12 characterized evidence contexts + an inert metadata field
- Identical contexts both RAG arms: **True**
- Run host Task-82: Kaggle T4 (established safe execution method; Colab token expired); Task-75: Google Colab T4
- Production retrieval changed: **NO**. Training started: **NO**.

## 3. Acceptance gates (registered BEFORE generation)

| Criterion | Met |
|---|---|
| arms_ab_reproduce_task75 | PASS |
| arm_c_macro_not_down | PASS |
| arm_c_pass_not_down | PASS |
| arm_d_macro_not_down | FAIL |
| arm_d_pass_not_down | PASS |
| abstention_not_regressed | FAIL |
| no_loop_increase | PASS |
| contract_violations_zero | PASS |
| identical_contexts_both_rag_arms | PASS |
| fabrication_not_up | FAIL |
| dapt_value_under_rag_still_zero | FAIL |
| every_new_regression_investigated | PASS |

All met: **False**.

## 4. Per-case comparison vs Task-75

| Arm | improved | unchanged | regressed |
|---|---|---|---|
| base | 0 | 47 | 0 |
| dapt | 0 | 47 | 0 |
| base_rag | 0 | 47 | 0 |
| dapt_rag | 0 | 46 | 1 |

Investigated regressions:

- `DAPT01EVAL-037` (dapt_rag): 1.0 → 0.0 — cause: **retrieval_evidence_differs**
  - Task-75 failure class: ABSTENTION_CORRECT; Task-82: GENERATION_FABRICATION
  - Task-75 answer: 'The Terapanth was founded in 1583 by Kundakunda Acharya. This date is based on the information provided in the source SVK-0038, which states that the sect was founded by a Sthânaka'
  - Task-82 answer: 'The Terapanth was founded in 1658 by Birbhan. This information is derived from the source SVK-1005, which provides a detailed account of the religious literature of India, includin'
  - flags t75: {"groups_satisfied": "1/1", "abstention_detected": true, "abstention_correct": true, "forbidden_hits": [], "looped": false, "at_cap_192": false, "len_chars": 648, "cited_evidence_author": false, "cited_attribution_word": true}
  - flags t82: {"groups_satisfied": "1/1", "abstention_detected": false, "abstention_correct": false, "forbidden_hits": [], "looped": false, "at_cap_192": true, "len_chars": 997, "cited_evidence_author": false, "cited_attribution_word": true}

**Single-case attribution:** all failing gates trace to ['DAPT01EVAL-037']; base arms unaffected: True; arms A/B exact reproduction: True; arm C exact reproduction: True.

## 5. Retrieval vs generation failure attribution

| Arm | GENERATION_FABRICATION | GENERATION_FAILURE | GROUNDED_SUCCESS | PRIOR_KNOWLEDGE | RETRIEVAL_INSUFFICIENT | RETRIEVAL_RISK_CONTRIBUTED |
| base_rag | 2 | 5 | 31 | 1 | 6 | 2 |
| dapt_rag | 2 | 7 | 29 | 1 | 6 | 2 |


## 6. Abstention, loops, languages, categories

- Abstention (4 cases): base_rag 0, dapt_rag 0 (Task-75: 0 / 1). Gate: FAIL
- Loops: base_rag 0, dapt_rag 4 (Task-75: 0 / 4). Gate: PASS
- Fabrication: base_rag 2, dapt_rag 2 (Task-75: 2 / 1). Gate: FAIL
- Sect-term scan (mechanical, RAG arms): {"base_rag": {"sthanakvasi": 9, "shvetambara": 0, "digambara": 4, "agam": 3}, "dapt_rag": {"sthanakvasi": 9, "shvetambara": 0, "digambara": 4, "agam": 2}}

Language means:

| lang | n | base | dapt | base_rag | dapt_rag |
|---|---|---|---|---|---|
| en | 34 | 0.2304 | 0.2647 | 0.7843 | 0.7843 |
| gu | 5 | 0.0 | 0.0 | 0.2 | 0.4 |
| hi | 8 | 0.2083 | 0.4375 | 0.625 | 0.375 |

## 7. Recommendation

- **Do not adopt pool=250 evidence for the generation path without explicit review.** The base retrieval arm and BASE+RAG arm are unaffected and reproduce Task-75 exactly, but the BM25 pool=250 cap changed the evidence composition in 12/47 cases and flipped one DAPT+RAG case (037) from a hedged abstention-correct answer to a bare-year fabrication, regressing 4 registered gates.
- **DAPT value under optimized RAG**: the −0.0212 macro delta is entirely that single case; the Task-75 qualitative conclusion (DAPT adds no reliable value under RAG) is not contradicted, but the registered numeric tolerance was breached, so the gate is FAIL.
- **Options for the next explicit task**: (a) use a larger pool (e.g. 1000 or full-list) for any generation-facing evidence while keeping pool=250 for retrieval-only serving latency; (b) explicitly review and accept the 1-case regression; or (c) run a targeted mini-gate over the 12 differing contexts before deciding. This task makes no production change.

## 8. Runtime deviations and reproducibility

- run host: Google Colab T4 (Task-75) -> Kaggle T4 (Task-82); Colab CLI OAuth token expired 2026-10-09 05:57 UTC and re-auth requires interactive browser consent
  - impact: arms A/B reproduced Task-75 macro/pass_all EXACTLY (0.2021/6, 0.266/8) and arm C exactly (0.695/32), so run-host numerics did not move any scored outcome
- torch build: 2.11.0+cu130 (Task-75 Colab) -> 2.11.0+cu128 (Kaggle image); same torch/transformers/peft/bitsandbytes versions (5.0.0 / 0.19.1 / 0.50.2)
  - impact: none observed (exact A/B/C reproduction)
- kernel attempt 1 failed: Kaggle pre-imports transformers 5.16.1 into sys.modules, shadowing the pip pin to 5.0.0 (mixed-stack guard tripped at 52 s)
  - resolution: kernel v2 purges transformers/peft/bitsandbytes/tokenizers/accelerate/huggingface_hub/safetensors from sys.modules after the pin, then re-imports; guard verified 5.0.0 in-run
  - impact: none on results (attempt 1 produced no outputs)
- prompts file sha differs from Task-75 (6d8d40cf… vs 302f6c91…): 12 evidence contexts differ (characterized) plus one inert metadata field (context_matches_task75) added to each row
  - impact: user_content bytes are identical for 35/47 cases; the 12 differing contexts are the experimental variable under test

Reproduce: build evidence (`experiments/task82/task82_build_evidence.py`), rebuild+push the Kaggle kernel (`task82_make_kernel.py`, `kaggle kernels push -p experiments/task82/kaggle`), pull (`kaggle kernels output priyanshu471/task82-four-arm-optimized-h3-rrf20-pool250-gate -p /tmp/task82_out`), score (`task82_score.py`), report (`task82_report.py`).

## 9. Artifacts

- comparison: `data/evaluation/task82_rag_comparison.json`
- task75_comparison: `data/evaluation/task75_rag_comparison.json`
- preflight: `data/evaluation/task82_preflight.json`
- retrieval_metrics: `data/evaluation/task82_retrieval_metrics.json`
- evidence: `data/evaluation/task82_rag_evidence.jsonl`
- prompts: `data/evaluation/task82_rag_prompts.jsonl`
- results: `['data/evaluation/task82_base_norag_results.jsonl', 'data/evaluation/task82_dapt_norag_results.jsonl', 'data/evaluation/task82_base_rrf250_results.jsonl', 'data/evaluation/task82_dapt_rrf250_results.jsonl']`
- run_metadata_path: `data/evaluation/task82_rag_run_metadata.json`

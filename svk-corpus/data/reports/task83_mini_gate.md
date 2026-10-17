# TASK 83 — Targeted Evidence-Composition Mini-Gate

**Verdict: `MINI_GATE_PASS`**  (selected generation-facing pool: **pfull**)

**Final status:**

- Differing cases evaluated: **12/12** covered (fresh generation: 9 for P500, 8 for P1000, union 9; verified-reuse: 3 / 4; + 2 same-host control reruns)
- DAPT01EVAL-037 resolved: **P500 NO / P1000 NO / PFULL YES** — `SVK-1005:u02684` BM25 rank **1110** > 1000, so no bounded pool ≤1000 restores the context
- Best eligible generation-facing pool: **pfull**
  - p250: gates **FAIL** (failed: case037_context_restored, all_12_contexts_restored, case037_dapt_outcome_restored, projected_dapt_rag_macro_not_down, projected_abstention_not_regressed, projected_fabrication_not_up, projected_dapt_value_under_rag_still_zero)
  - p500: gates **FAIL** (failed: case037_context_restored, all_12_contexts_restored, case037_dapt_outcome_restored, projected_dapt_rag_macro_not_down, projected_abstention_not_regressed, projected_fabrication_not_up, projected_dapt_value_under_rag_still_zero)
  - p1000: gates **FAIL** (failed: case037_context_restored, all_12_contexts_restored, case037_dapt_outcome_restored, projected_dapt_rag_macro_not_down, projected_abstention_not_regressed, projected_fabrication_not_up, projected_dapt_value_under_rag_still_zero)
  - pfull: gates **PASS**
- Retrieval p95/p99 for the selected pool (full): **831.06 / 1124.01 ms** (n=141; targets ≤2000 / ≤3000) — MEETS
- Final 47-case confirmation required: **NO** (selected pool is the already-completed Task-75 full benchmark)
- Production default changed: **NO**; training started: **NO**

## 1. The 12 differing cases and context differences

Recovered byte-exactly from `task82_preflight.json` (Task-82 P250-vs-PFULL diff):

| case | P250 kind | restored @P500 | restored @P1000 | restored @PFULL |
|---|---|---|---|---|
| DAPT01EVAL-001 | one_item_swap | YES | YES | YES |
| DAPT01EVAL-007 | channel_header_only | no | no | YES |
| DAPT01EVAL-010 | channel_header_only | no | no | YES |
| DAPT01EVAL-011 | reorder_same_set | no | no | YES |
| DAPT01EVAL-012 | reorder_same_set | no | no | YES |
| DAPT01EVAL-013 | reorder_same_set | no | no | YES |
| DAPT01EVAL-017 | reorder_same_set | YES | YES | YES |
| DAPT01EVAL-021 | reorder_same_set | no | no | YES |
| DAPT01EVAL-033 | one_item_swap | no | no | YES |
| DAPT01EVAL-034 | reorder_same_set | no | YES | YES |
| DAPT01EVAL-037 | one_item_swap | no | no | YES |
| DAPT01EVAL-039 | one_item_swap | YES | YES | YES |

P500 still differs from PFULL on 9 cases ['DAPT01EVAL-007', 'DAPT01EVAL-010', 'DAPT01EVAL-011', 'DAPT01EVAL-012', 'DAPT01EVAL-013', 'DAPT01EVAL-021', 'DAPT01EVAL-033', 'DAPT01EVAL-034', 'DAPT01EVAL-037']; P1000 on 8 ['DAPT01EVAL-007', 'DAPT01EVAL-010', 'DAPT01EVAL-011', 'DAPT01EVAL-012', 'DAPT01EVAL-013', 'DAPT01EVAL-021', 'DAPT01EVAL-033', 'DAPT01EVAL-037']. All remaining diffs are byte-identical to the P250 contexts, so their greedy outputs reproduce Task-82's answers exactly (verified: all fresh runs byte-identical).

## 2. Configuration-by-configuration results

| config | pool | contexts=PFULL (of 12) | DAPT 037 | projected base_rag | projected dapt_rag | ΔD−C | gates | p95/p99 ms |
|---|---|---|---|---|---|---|---|---|
| p250 | 250 | 0/12 | GENERATION_FABRICATION (score 0.0) | 0.695/32 | 0.6738/30 | -0.0212 | **FAIL** | 692.83/748.05 |
| p500 | 500 | 3/12 | GENERATION_FABRICATION (score 0.0) | 0.695/32 | 0.6738/30 | -0.0212 | **FAIL** | 708.54/742.66 |
| p1000 | 1000 | 4/12 | GENERATION_FABRICATION (score 0.0) | 0.695/32 | 0.6738/30 | -0.0212 | **FAIL** | 693.57/754.95 |
| pfull | full | 12/12 | ABSTENTION_CORRECT (score 1.0) | 0.695/32 | 0.695/31 | +0.0 | **PASS** | 831.06/1124.01 |

No-RAG arms A/B are pool-independent and unchanged (recorded Task-75/82: base 0.2021/6, dapt 0.266/8).

## 3. DAPT01EVAL-037 — evidence and output comparison

Question: *In which year exactly was the Terapanth founded?*

| config | context sha (16) | item 5 | item 5 channel | == PFULL |
|---|---|---|---|---|
| pfull_task75 | 9b28cfb693c1d7d3 | `SVK-1005:u02684:2ab2a5c5c4027c26` | unit_bm25 | YES |
| p250_task82 | f5035285236ccc7d | `SVK-0038:u00170:6f241b7d634d1e02` | unit_bm25 | no |
| p500 | f5035285236ccc7d | `SVK-0038:u00170:6f241b7d634d1e02` | unit_bm25 | no |
| p1000 | f5035285236ccc7d | `SVK-0038:u00170:6f241b7d634d1e02` | unit_bm25 | no |

`SVK-1005:u02684` exact BM25 rank for this query: **1110** (score 10.3009) — above every bounded candidate pool; only the full list includes it. Items 1–4 (incl. the Birbhan/1658 sentence at item 2) are identical in all four configurations.

DAPT-arm outputs:

- PFULL (Task-75, recorded): 'The Terapanth was founded in 1583 by Kundakunda Acharya. This date is based on the information provided in the source SVK-0038, which states that the sect was founded by a Sthânaka'…
- P250 (Task-82, recorded): 'The Terapanth was founded in 1658 by Birbhan. This information is derived from the source SVK-1005, which provides a detailed account of the religious literature of India, includin'…
- P500 fresh: 'The Terapanth was founded in 1658 by Birbhan. This information is derived from the source SVK-1005, which provides a det'…
- P1000 fresh: 'The Terapanth was founded in 1658 by Birbhan. This information is derived from the source SVK-1005, which provides a det'…
- P250-context control rerun (same host): 'The Terapanth was founded in 1658 by Birbhan. This information is derived from the source SVK-1005, which provides a det'…
- PFULL-context control rerun (same host): 'The Terapanth was founded in 1583 by Kundakunda Acharya. This date is based on the information provided in the source SV'…

Determinism: P250-ctrl vs Task-82 byte-identical (base=True, dapt=True); PFULL-ctrl vs Task-75 byte-identical (base=True, dapt=True, cross-host). 
=> The outcome is **evidence-composition-driven and stable**: the same context always yields the same answer under the frozen protocol; the PFULL context restores the abstention-correct outcome even across run hosts. Flags: PFULL DAPT = abstention_detected/abstention_correct true, not at cap; P250 DAPT = no abstention marker, at_cap_192 true with tail degeneration, class GENERATION_FABRICATION.

## 4. Per-case scores on the 12-case set

| case | t75 b/d | t82 b/d | p500 b/d | p1000 b/d | ctx p500=PFULL | ctx p1000=PFULL |
|---|---|---|---|---|---|---|
| DAPT01EVAL-001 | 1.0/1.0 | 1.0/1.0 | 1.0/1.0 | 1.0/1.0 | YES | YES |
| DAPT01EVAL-007 | 0.0/0.0 | 0.0/0.0 | 0.0/0.0 | 0.0/0.0 | no | no |
| DAPT01EVAL-010 | 0.0/0.0 | 0.0/0.0 | 0.0/0.0 | 0.0/0.0 | no | no |
| DAPT01EVAL-011 | 0.0/0.0 | 0.0/0.0 | 0.0/0.0 | 0.0/0.0 | no | no |
| DAPT01EVAL-012 | 1.0/1.0 | 1.0/1.0 | 1.0/1.0 | 1.0/1.0 | no | no |
| DAPT01EVAL-013 | 1.0/0.0 | 1.0/0.0 | 1.0/0.0 | 1.0/0.0 | no | no |
| DAPT01EVAL-017 | 0.0/1.0 | 0.0/1.0 | 0.0/1.0 | 0.0/1.0 | YES | YES |
| DAPT01EVAL-021 | 1.0/1.0 | 1.0/1.0 | 1.0/1.0 | 1.0/1.0 | no | no |
| DAPT01EVAL-033 | 1.0/1.0 | 1.0/1.0 | 1.0/1.0 | 1.0/1.0 | no | no |
| DAPT01EVAL-034 | 1.0/1.0 | 1.0/1.0 | 1.0/1.0 | 1.0/1.0 | no | YES |
| DAPT01EVAL-037 | 0.0/1.0 | 0.0/0.0 | 0.0/0.0 | 0.0/0.0 | no | no |
| DAPT01EVAL-039 | 0.0/0.0 | 0.0/0.0 | 0.0/0.0 | 0.0/0.0 | YES | YES |

Recoveries vs Task-82: P500 restores 3 contexts (DAPT01EVAL-001, DAPT01EVAL-017, DAPT01EVAL-039), P1000 restores 4 (DAPT01EVAL-001, DAPT01EVAL-017, DAPT01EVAL-034, DAPT01EVAL-039); their scores were already equal to Task-75, so no score changes anywhere except the persistent 037 DAPT regression under P500/P1000.

## 5. Registered gate results

Criteria registered in `task83_preflight.json` BEFORE generation (recovered Task-82 thresholds applied to the projected full-47, plus reference-derived case/subset gates).

| gate | p250 | p500 | p1000 | pfull |
|---|---|---|---|---|
| case037_context_restored | FAIL | FAIL | FAIL | PASS |
| all_12_contexts_restored | FAIL | FAIL | FAIL | PASS |
| case037_dapt_outcome_restored | FAIL | FAIL | FAIL | PASS |
| case037_base_outcome_preserved | PASS | PASS | PASS | PASS |
| projected_base_rag_macro_not_down | PASS | PASS | PASS | PASS |
| projected_base_rag_pass_not_down | PASS | PASS | PASS | PASS |
| projected_dapt_rag_macro_not_down | FAIL | FAIL | FAIL | PASS |
| projected_dapt_rag_pass_not_down | PASS | PASS | PASS | PASS |
| projected_abstention_not_regressed | FAIL | FAIL | FAIL | PASS |
| projected_no_loop_increase | PASS | PASS | PASS | PASS |
| projected_fabrication_not_up | FAIL | FAIL | FAIL | PASS |
| projected_dapt_value_under_rag_still_zero | FAIL | FAIL | FAIL | PASS |
| contract_violations_zero | PASS | PASS | PASS | PASS |
| identical_contexts_both_rag_arms | PASS | PASS | PASS | PASS |
| attribution_not_worse_on_12 | PASS | PASS | PASS | PASS |
| sect_term_counts_not_up_on_12 | PASS | PASS | PASS | PASS |
| every_new_regression_investigated | PASS | PASS | PASS | PASS |

All gates met: p250=False, p500=False, p1000=False, pfull=True.

## 6. Retrieval latency and memory trade-offs

Task-81 verified measurements (real BGE-M3 encoder, `search_ranks`, heap top-k; 47 queries × 3 iters = n=141 per pool; Azure VM, torch 2.14.1+cpu, 2 threads):

| pool | p50 ms | p95 ms | p99 ms | meets ≤2000/≤3000 |
|---|---|---|---|---|
| 250 | 480.86 | 692.83 | 748.05 | YES |
| 500 | 492.87 | 708.54 | 742.66 | YES |
| 1000 | 486.31 | 693.57 | 754.95 | YES |
| full | 538.4 | 831.06 | 1124.01 | YES |

Peak RSS 3449.4 MB — identical across pools (dense embeddings dominate; the pool cap does not move peak memory). Pool 250 remains the latency floor (p95 693 ms); full-list p95 831 ms is +138 ms and still 2.4× under the p95 target.

## 7. Recommendation

- **Generation-facing pool: full list (PFULL).** It is the only candidate that restores case 037's evidence composition and passes every registered gate, and its measured latency meets the registered targets.
- **P500/P1000 do not resolve the regression**: their 037 contexts are byte-identical to P250 (`SVK-1005:u02684` BM25 rank 1110 is above both pools); they restore 3/4 of the other differing contexts but change no scores.
- **Retrieval-only pool 250 remains separable**: the cap is an experiment-local knob; production stays `mode = "bm25"` unchanged. A future explicit adoption task could configure generation-facing evidence with the full list while keeping pool=250 for retrieval-only serving (both meet the latency targets).
- **Intermediate pool option** (outside the registered set): any pool ≥ 1110 would restore 037's context; evaluating e.g. 1500/2000 requires a new pre-registered mini-gate + 47-case confirmation.
- **Final 47-case confirmation**: not required for PFULL (it is the completed Task-75 benchmark, re-verified by Task-82 for arms A/B/C).

## 8. Reproducibility and artifacts

```bash
PYTHONPATH=src python3 experiments/task83/task83_build_evidence.py
python3 experiments/task83/task83_make_kernel.py
kaggle kernels push -p experiments/task83/kaggle
kaggle kernels output priyanshu471/task83-mini-gate-p500-p1000-targeted-generation -p /tmp/task83_out
# copy task83_*_results.jsonl + task83_run_metadata.json -> data/evaluation/
PYTHONPATH=src python3 experiments/task83/task83_score.py
PYTHONPATH=src python3 experiments/task83/task83_report.py
```

Key artifact hashes:

- `data/evaluation/task83_preflight.json` sha256 `5f9bc5b5043b23a6b59f96eb32a2567ae471fa4a8f60d1218aac90e2342ef30c`
- `data/evaluation/task83_kernel_payload.json` sha256 `5d2bf840a0d8f5d03899d58b63698111a9673b0330b0d9e7487e411598262641`
- `data/evaluation/task83_rag_prompts_p500.jsonl` sha256 `a77ae90984b9b092454fbbaff5da5d39858bbc4bfd75c6b17e85d33d1a1b5add`
- `data/evaluation/task83_rag_prompts_p1000.jsonl` sha256 `f7bd3de7e177ed23f5fe4466004b072ad40455d8dfb0b1877355b6557e4bdfa8`
- `data/evaluation/task83_mini_gate_results.json` sha256 `15d1ccdd1943cf9c0081e97aca821bd260e18a01c31ccf0f1432e3186fe65be4`
- frozen benchmark sha256 `06625f72190e3ae130447345afdc04342bd19cb76f842285706480cba7765b81` (verified)
- DAPT-01 adapter sha256 `9b4d2bdcfe089118d0634815596b628506a83c434d3863cff7a731cba75a58e9` (verified)

Generation environment (Task-83 kernel): 2.11.0+cu128 / transformers 5.0.0 / peft 0.19.1 / bnb 0.50.2, GPU Tesla T4; protocol identical to Task-75/82.

Limitations: targeted mini-gate: only differing cases freshly generated for P500/P1000; full-47 numbers for those pools are PROJECTED (fresh differing-case rows + recorded Task-75 rows elsewhere) — a projection, not a fresh full run; P250 and PFULL results are the recorded Task-82 and Task-75 full-47 runs (verified exact prompt/model/context/settings); an intermediate pool (>=1110) was outside the registered candidate set and remains unevaluated.

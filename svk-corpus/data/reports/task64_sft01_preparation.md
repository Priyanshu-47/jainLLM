# Task 64 — SFT-01 Dataset Finalization + Training Preparation

**Status:** preparation complete — **training NOT started**, Kaggle NOT launched.
**Date:** 2026-10-01 · **Base:** `Qwen/Qwen3-8B-Base` · **Lineage:** DAPT-01 adapter @ step 15,248
**Strategy:** human review is not a blocking dependency; no new human-review gate was introduced.

---

## 1. Input candidates

| Input | Count | Source file |
|---|---:|---|
| Task-63 APPROVE candidates | 54 | `data/training/sft_gold_v4_candidates.jsonl` |
| Existing HUMAN_VERIFIED rows | 8 | `data/training/sft_reconciled_v1.jsonl` |
| **Total inputs** | **62** | |

Verified from the actual files (not assumed). Related Task 62/63 artifacts re-counted and
matching: `sft_candidates_v2.jsonl` 249 · `task62_adjudication_v1.jsonl` 252 ·
approve 54 / revise 104 / reject 94 · consolidated.md 405 lines · stats.json 667 lines.

## 2. Selected candidates

**59** (54 Task-63 APPROVE + 5 HUMAN_VERIFIED). Every selected row passed all gates in §11.

## 3. Excluded candidates and exact reasons

**3 excluded**, all from the HUMAN_VERIFIED pool — an explicit input conflict:

| original_id | code | Task-63 review_id | Task-63 reason |
|---|---|---|---|
| `SFT-SEED-CAND-SVK-2025-SVK-2025` | TASK63_REJECT | `T61-RECON-SFT-SEED-CAND-SVK-2025-SVK-2025` | "The answer is a boilerplate 'The concept of X is central to Jain philosophy' wrapper around an unrelated source quotation; it does not answer the question and the quotation is a raw passage dump, not an explanation." |
| `SFT-SEED-CAND-SVK-2029-SVK-2029` | TASK63_REJECT | `T61-RECON-SFT-SEED-CAND-SVK-2029-SVK-2029` | same |
| `SFT-SEED-CAND-SVK-0038-unknown` | TASK63_REJECT | `T61-RECON-SFT-SEED-CAND-SVK-0038-unknown` | same |

**Conflict resolution (documented):** these 3 rows are HUMAN_VERIFIED *and* are byte-identical
(question + answer) to records Task 63 adjudicated REJECT. The Task-63 spec's
"Do NOT include: Task 63 REJECT" is an explicit hard exclusion, so it wins over the earlier
human verification (which predates the evidence-grounding review). No decision was rewritten;
the prior `HUMAN_VERIFIED` status in `sft_reconciled_v1.jsonl` is untouched.

Exclusions that did **not** fire (0 rows each): TASK63_REVISE, RIGHTS_NOT_CLEARED,
PROVENANCE_OR_MANIFEST_MISSING, METADATA_INCONSISTENT, NOT_GROUNDED,
ATTRIBUTION_UNSUPPORTED, ANSWER_QUALITY, duplicate/near-duplicate.

**Dedup:** 1,711 question pairs checked (shingle Jaccard ≥ 0.80), 0 near-duplicates,
0 exact duplicate question/answer pairs, 0 duplicate example_ids → 0 removed.

**Mechanical normalization (8 human rows, no substantive text changes):**
`example_id_reformatted_to_schema_pattern` (schema pattern `^[a-z0-9_-]+:[a-z0-9_-]+:[a-f0-9]{8}$`,
original id preserved in `sft01.original_id`), `source_quality_UNMEASURED→UNKNOWN`,
`quality_flags_non_enum_moved_to_quality_flags_notes`, `messages_reformatted_from_question_answer`.
Question/answer text was never rewritten.

## 4. Category distribution (59 selected)

| task_category | total | train | eval |
|---|---:|---:|---:|
| source_citation (attribution) | 37 | 30 | 7 |
| canonical_commentary_distinction | 10 | 8 | 2 |
| abstention | 7 | 7 | 0 |
| general_qa (HUMAN_VERIFIED) | 5 | 5 | 0 |

Maps directly to the Task-60 DAPT weaknesses: 47/59 rows are attribution, canonical-vs-
commentary or abstention behaviour; 5 rows are human-verified general practice/concept QA.

## 5. Source distribution

38 distinct sources; all present in `manifests/source_manifest.csv`.
Per-source counts: SVK-2022/2023/2024/2027 ×3 · SVK-0007/0027/0037/0038/1006/1010/
2002/2003/2004/2005/2007/2025/2026 ×2 · the remaining 22 sources ×1.
Train sources (32): SVK-0007, 0016, 0026, 0027, 0037, 1002, 1003, 1005, 1006, 1007,
1008, 1009, 1010, 2002–2007, 2009, 2011–2013, 2016, 2019–2025, 2027, 2029.
Eval sources (6): SVK-0038, SVK-2007, SVK-2008, SVK-2010, SVK-2014, SVK-2026.

## 6. Sect / tradition distribution

| sect | count | | tradition | count |
|---|---:|---|---|---:|
| STHANAKAVASI | 27 | | UNKNOWN | 55 |
| UNKNOWN | 27 | | SHWETAMBAR | 4 |
| MULTI_TRADITION | 2 | | | |
| SVETAMBARA | 2 | | | |
| GENERIC_JAIN | 1 | | | |

Religious scope: CORE_STHANAKAVASI 13 · CONTEXTUAL_JAIN 13 · HIGH_STHANAKAVASI_RELEVANCE 4 ·
COMPARATIVE_OTHER_TRADITION 1 · UNKNOWN 28. All values verified consistent with
source-manifest metadata (§11); no Sthānakavāsī claim was invented — rows carry only the
sect/scope recorded by the corpus.

## 7. Knowledge-layer distribution

MIXED 17 · CANONICAL_SCRIPTURE 16 · LEXICON 15 · SECONDARY_SCHOLARSHIP 6 · REFERENCE 5.
Preserved from source metadata (checked against `map_knowledge_layer(manifest)`).

## 8. HUMAN_VERIFIED count

- Input: **8** · Selected: **5** · Excluded: **3** (Task-63 REJECT, §3) · **Newly created: 0**
- Selected ids: `svk-2022:qa:23bb2ae8`, `svk-2022:qa:e3a4db5c`, `svk-2023:qa:c58c0314`,
  `svk-2023:qa:f8c0ac79`, `svk-2024:qa:a9cea037` (originals: `SFT-SEED-CAND-SVK-2022/2023/2024`,
  `REV-EX-000001`, `REV-EX-000003`).
- All 5 landed in **train** (source-level split). No row was upgraded to HUMAN_VERIFIED;
  the 54 APPROVE rows keep `human_review_status=HUMAN_REVIEW_REQUIRED`.

## 9. Train/eval split

| file | rows | schema `split` |
|---|---:|---|
| `data/training/sft_train_v1.jsonl` | **50** | `train` |
| `data/evaluation/sft_eval_v1.jsonl` | **9** | `validation` |

Method: **deterministic source-level split** — sources ordered by
`sha256("42|source_id")`, sources that appear in the frozen 47-case eval preferred into eval
first (so they are never trained on while the eval budget lasts), then whole sources added
until ≥ 15% of rows (target 9). Same source never appears in both files. Re-running the
builder reproduces byte-identical files (verified: rebuild → SHA256 match).
Eval = 15% of rows (not artificially large).

## 10. Leakage result

**CLEAN.** shared sources: 0 · shared example_ids: 0 · shared questions: 0 ·
shared answers: 0 · near-dup questions across split: 0.
Frozen-eval source overlap: 26 selected rows sit on sources that appear in the frozen
47-case set → 9 in eval (never trained), **17 remain in train** — reported as a known
limitation (§17), partially mitigated by the eval-preference rule.

## 11. Validation result

`python3 experiments/sft_01/validate_sft01_dataset.py` → **16/16 PASS**:

schema validity · example_id uniqueness · no exact dups · no near-dups ·
provenance + source manifest · rights (recorded **and** recomputed via `rights_for`) ·
source-level split separation · deterministic split reproducibility ·
no Task-63 REJECT/REVISE record · messages match question/answer ·
answer quality + no raw URLs/IDs · metadata consistency vs manifest ·
HUMAN_VERIFIED integrity · frozen 47-case eval untouched (sha256
`06625f72190e3ae1…` unchanged) · stats JSON consistency · grounding + attribution re-verified.

Phase-3 gate outcomes per selected row: rights = 42 `TRAINING_ALLOWED` +
17 `TRAINING_ALLOWED_WITH_PERMISSION_EVIDENCE` (0 downgrades, 0 upgrades);
grounding = 51 `manifest_grounded_metadata` + 3 `quote_in_unit_text` +
4 `corpus_linked_units` + 1 `corpus_source_units` (human-row quotes verified against
`data/release/training_corpus.jsonl` unit text); attribution traced to row/manifest
metadata for all 59; sect/knowledge-layer/tradition/scope consistent for all 59.

Entrypoint preflight `python3 tools/train_sft_01.py` → **16/16 PASS**
(model lineage, quantization, LoRA geometry, adapter id, hyperparameters, file existence,
row counts, chat format, rights allowlist, uniqueness, file hashes vs build stats,
frozen eval hash, kaggle script/metadata existence, no credentials in config).

## 12. SFT configuration

`configs/sft_qwen3_8b_v1.yaml` (mirrors DAPT-01 locked settings unless a reason is recorded):

- **Model:** `Qwen/Qwen3-8B-Base` (NOT Instruct) + adapter `priyanshu471/dapt01-checkpoint-15248`
  loaded `is_trainable=True` — SFT continues the DAPT-01 lineage instead of re-init.
- **Quantization:** 4-bit NF4, double quant, fp16 compute (identical to DAPT-01).
- **LoRA:** r=16, alpha=32, dropout=0.05, targets q/k/v/o/gate/up/down_proj (inherited, locked).
- **Training:** lr `1e-4` (reason: DAPT used 2e-4 for 15,248 steps over ~16k chunks; SFT sees
  ~50 rows × 3 epochs ≈ 150 optimizer steps — lower LR prevents catastrophic forgetting),
  cosine + warmup_ratio 0.03, batch 1 × grad-accum 8 (effective 8), max_seq_length 2048,
  fp16, seed 42, save/eval per epoch, save_total_limit 3.
- **Data format:** chat `messages`, rendered with `tokenizer.apply_chat_template`
  (explicit fallback if absent); **assistant-only loss** (user/system tokens → label `-100`);
  pad-token collator.
- **Eval:** held-out `sft_eval_v1.jsonl` per epoch (eval_loss); the frozen 47-case Task-60 set
  remains the behavioural benchmark and is never touched by training.
- **Objective:** behaviour (grounded answering, attribution, sect/canonical distinction,
  abstention) — RAG remains the factual authority; no memorization of unsupported claims.

## 13. Starting checkpoint

`priyanshu471/dapt01-checkpoint-15248` (DAPT-01 final, global step 15,248; mirror
`priyanshu47/dapt01-checkpoint-15248` as fallback), attached read-only as a Kaggle input
dataset and verified at startup: `adapter_config.json` r/alpha/dropout/target_modules must
match the locked geometry or the run aborts.

## 14. Expected GPU/runtime requirements

- GPU: 1× NVIDIA Tesla T4 (Kaggle `machine_shape: NvidiaTeslaT4`), min ~12 GB VRAM
  (4-bit 8B + LoRA fits a T4 with gradient checkpointing).
- Runtime: ~10–25 minutes for 50 rows × 3 epochs (≈150 optimizer steps) — well within a
  single Kaggle session; status/log files `sft01_train_status.json`, `sft01_train_worker.log`.

## 15. Required installs / model downloads

- **Pip (auto-installed by the session script, `ensure_deps()`):** `transformers`, `peft`,
  `datasets`, `accelerate`, `bitsandbytes` (any not preinstalled on the Kaggle image).
- **Model weights:** `Qwen/Qwen3-8B-Base` (already used by DAPT-01; downloaded once per
  session or cached).
- **Datasets attached (no download if attached):** `priyanshu471/dapt01-checkpoint-15248`,
  `priyanshu47/jainllm-sft01-train` (needs one-time upload, §16 step 1).
- Nothing was downloaded by Task 64 (no local GPU/torch environment).

## 16. Exact command to launch SFT-01 on Kaggle

Run from the repo root. **These commands were NOT executed by Task 64.**

```bash
# 1) one-time: publish the SFT dataset
mkdir -p /tmp/sft01_data && \
  cp data/training/sft_train_v1.jsonl /tmp/sft01_data/train.jsonl && \
  cp data/evaluation/sft_eval_v1.jsonl /tmp/sft01_data/eval.jsonl && \
  printf '{"id":"priyanshu47/jainllm-sft01-train","title":"SFT-01 train/eval (Task 64)","licenses":[{"name":"CC0-1.0"}]}' \
    > /tmp/sft01_data/dataset-metadata.json && \
  kaggle datasets create -p /tmp/sft01_data --public

# 2) push the SFT-01 kernel (GPU T4; attaches train data + DAPT-01 adapter)
kaggle kernels push -p experiments/sft_01/kaggle

# 3) monitor
kaggle kernels status priyanshu47/sft01-qlora-dapt01-lineage
kaggle kernels output priyanshu47/sft01-qlora-dapt01-lineage -p /tmp/sft01_out
```

Equivalent helper: `python3 tools/train_sft_01.py --launch` (preflight + prints these
commands), `python3 tools/train_sft_01.py --emit` (writes `scripts/run_sft_01.sh`).
The kernel writes `sft01_train_report.json` (losses, steps, config echo, data hashes) and
uploads the final adapter to `priyanshu471/sft01-output`. No credentials are stored anywhere
in the repo; the Kaggle API authenticates from the environment Kaggle provides.

## 17. Known limitations

1. **Small dataset (59 rows).** Deliberate — SFT-01 is a first experiment; no examples were
   manufactured. Statistical power for behaviour claims is limited; the frozen 47-case
   comparison (BASE vs DAPT-01 vs DAPT-01+SFT-01) is the measuring instrument.
2. **Eval split is citation/distinction-heavy** (7 source_citation + 2 distinction; no
   abstention/general_qa rows in eval) — a consequence of preferring frozen-eval sources
   into eval for decontamination. Abstention/general behaviour is judged on the frozen set,
   not on `sft_eval_v1` loss.
3. **17 train rows share sources with the frozen 47-case eval** (residual contamination
   risk shared with DAPT-01, which saw the whole corpus). Reported honestly; reduces the
   strength of any SFT-vs-DAPT attribution claim on those cases.
4. **3 HUMAN_VERIFIED rows excluded** by the Task-63 REJECT conflict rule (§3) — a judgement
   call that trades 3 human-reviewed rows for consistency with the explicit exclusion list.
5. **HUMAN_VERIFIED ≠ Task-63 APPROVE:** the 54 APPROVE rows remain
   `HUMAN_REVIEW_REQUIRED`; no new human status was created (per instruction).
6. **Non-overlap only:** dataset covers 38 of 85 manifest sources; sect UNKNOWN dominates
   (27) because the corpus itself often does not record sect — nothing was inferred.
7. **Training not run** — no loss/metric claims are made anywhere in this task.

---

**Frozen-eval compatibility (Phase 9):** `data/evaluation/dapt01_eval_cases.jsonl` sha256
`06625f72190e3ae130447345afdc04342bd19cb76f842285706480cba7765b81` unchanged (verified by
validator + git status). The eventual comparison remains BASE vs DAPT-01 vs DAPT-01+SFT-01
under the same protocol (`experiments/dapt_01/evaluation/score_task60.py`).

**Files created (Task 64):**
`data/training/sft_train_v1.jsonl`, `data/evaluation/sft_eval_v1.jsonl`,
`data/reports/task64_sft01_build_stats.json`, `data/reports/task64_sft01_preparation.md`,
`experiments/sft_01/build_sft01_dataset.py`, `experiments/sft_01/validate_sft01_dataset.py`,
`experiments/sft_01/kaggle/train.py`, `experiments/sft_01/kaggle/kernel-metadata.json`,
`configs/sft_qwen3_8b_v1.yaml`, `tools/train_sft_01.py`, `tests/test_sft01_dataset.py`.
**Modified tracked files: none.**

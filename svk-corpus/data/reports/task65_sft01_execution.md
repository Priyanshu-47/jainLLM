# Task 65 — SFT-01 Execution on Kaggle (train + evaluate, then hard stop)

Date: 2026-10-01 · Status: **COMPLETE (trained, evaluated, persisted)** ·
GPU: Kaggle T4 · Owner namespace: `priyanshu471`

---

## 1. Result in brief (honest; no winner declared for SFT-01)

Held-out training signal: **clean and monotone** — `sft_eval_v1` (9 rows)
eval_loss 2.745 → 2.135 → 1.992 across 3 epochs; train loss 4.47 → 1.56.

Frozen 47-case Task-60 behavioural benchmark (identical cases, prompts,
greedy/192/42 decoding, identical T4/transformers-5.0.0 environment):

| arm | macro keyterm score | pass-all (of 47) | abstention correct (of 4) |
|---|---|---|---|
| BASE | 0.2021 | 6 | 0 |
| BASE + DAPT-01 | **0.2660** | **8** | 0 |
| BASE + DAPT-01 + **SFT-01** | 0.2305 | 7 | **1** |

- **SFT-01 lands BETWEEN BASE and DAPT-01**: −0.0355 vs DAPT-01, +0.0284 vs BASE.
  SFT-01 does **not** beat the DAPT-01 checkpoint on this benchmark.
- Category wins for SFT-01: **ABSTENTION 0 → 1 correct** (DAPT01EVAL-036), and
  the **DAPT-unseen (test) split improves vs both arms** (0.1905 vs dapt 0.0476,
  base 0.1429) while DAPT-seen (train) cases regress vs DAPT-01 (−0.0586).
- vs DAPT-01: 1 improvement, **5 regressions** (DAPT01EVAL-008, -016, -023,
  -040, -043 — mainly PRACTICE and STHANAKAVASI_TERMINOLOGY).
- Evaluator-based metrics (factual_error, unsupported_claims, sect_confusion,
  degenerate_loop): **NOT_MEASURED for the SFT arm** — the frozen evaluator
  review covers base/dapt only and no evaluator pass was run for SFT-01;
  nothing is synthesised.

Training ran (see §5). No next training run was started (§17).

## 2. Phase-1 pre-flight (all PASS, re-run after infra edits)

- `git status` / `git pull --ff-only` → "Already up to date"; `git diff` empty
  (0 tracked-file modifications; all task-64/65 files remain untracked until
  the project chooses to commit).
- `sha256(sft_train_v1.jsonl) = 77bd61ff…b053615d` (50 rows),
  `sha256(sft_eval_v1.jsonl) = 4ef9d814…52722cb` (9 rows) — match
  `task64_sft01_build_stats.json`.
- `python3 tools/train_sft_01.py` → preflight **16/16 PASS**
  (Qwen3-8B-Base not Instruct, NF4, LoRA r16/α32/d0.05 + 7 targets,
  continues checkpoint-15248, rights, hashes, frozen eval untouched, no creds).
- `experiments/sft_01/validate_sft01_dataset.py` → **16/16 PASS**.
- Frozen `dapt01_eval_cases.jsonl` sha256 `06625f72…7765b81` before and after
  every stage — never modified.
- Verification detail: 50 train / 9 eval records, source-level split,
  zero leakage, 0 REVISE and 0 REJECT rows, provenance + rights gates present
  (validator checks 1–16), DAPT checkpoint = step 15248 — all PASS.

### 2.1 Software / GPU environment (Phase 2 record)

| component | value |
|---|---|
| GPU | Tesla T4, 15.6 GB total (15.5 GB free at start, logged) — not CPU, not TPU |
| peak VRAM | **NOT_RECORDED** (kernel logs free-at-start only; run completed without OOM) |
| torch | 2.10.0+cu128 (CUDA available, verified in-kernel) |
| transformers | 5.0.0 |
| peft | 0.19.1 |
| bitsandbytes | 0.50.2 (only package installed at runtime, pre-5.0 requirement check) |
| python | 3.12.13 |
| accelerate | import verified by `ensure_deps`; **version NOT_RECORDED** (preinstalled, not dumped) |
| kaggle CLI / API | 2.2.4, authenticated via existing secure config; no token/username/env var was printed |

Versions captured from `task65_sft_infer_metadata.json` (same image/date as the
training session; both sessions ran on Kaggle batch T4).


## 3. Environment and namespace correction (infra only, no hyperparameter change)

The authenticated Kaggle account is `priyanshu471` (verified without printing
credentials). The Task-64 launch plan referenced `priyanshu47/...` ids, which
this account cannot push to (create failed with the API's misleading
"slugs and hashlink are all null" error). Corrected to `priyanshu471` in
`kernel-metadata.json`, `configs/sft_qwen3_8b_v1.yaml` (kaggle: section),
`tools/train_sft_01.py` and the kernel script — **infrastructure ids only;
locked hyperparameters, data and protocol untouched**. The dual adapter slug
list (`priyanshu471` primary, `priyanshu47` public mirror) was already correct
and is retained. Kernel id resolved to the title-derived slug
`priyanshu471/sft-01-qlora-on-dapt-01-lineage-task-64` (metadata updated to
match).

## 4. Dataset upload + SHA256 round-trip

- Created `priyanshu471/jainllm-sft01-train` (public, CC0-1.0) with
  `train.jsonl` + `eval.jsonl` via the python API (`convert_to_csv=False`,
  description present — the bare `kaggle datasets create` CLI path failed).
- Downloaded the dataset back and re-hashed:
  `train = 77bd61ff…b053615d`, `eval = 4ef9d814…52722cb` — **byte-identical**.

## 5. Training run (attempt 1 crash → fix → attempt 2 canonical)

Kernel `priyanshu471/sft-01-qlora-on-dapt-01-lineage-task-64`, T4 (15.5 GB),
internet on, attached `jainllm-sft01-train` + `dapt01-checkpoint-15248`
(verified `adapter_config.json` geometry at startup, lr=1e-4, epochs=3,
seed=42, fp16, 4-bit NF4).

- **Attempt 1 (kernel v1)** — training itself completed (21 steps, 3 epochs,
  train_runtime 147 s, losses identical to v2), but `save_outputs` crashed
  with `TypeError: cannot convert dictionary update sequence element #0` while
  embedding `trainer.train()`'s `TrainOutput` into the report
  (`dict(result)` on a non-mapping). Adapter + checkpoints were saved on the
  worker; nothing was uploaded. Status preserved at
  `data/reports/task65_sft01_attempt1_error.json`.
- **Fix (kernel v2)** — robust metric embedding (dict / `metrics` / `_asdict` /
  `__dict__`, skip on any conversion error) plus a status-checked
  `dataset_create_new` → `dataset_create_version` upload fallback (the API
  returns `status:"Error"` instead of raising). `python3 -m py_compile` then
  push v2.
- **Attempt 2 (canonical)** — **COMPLETE** in 354.6 s:
  - train_loss 2.713 (mean), starting 4.471 → ending 1.555
  - eval_loss epoch 1/2/3 = **2.745 → 2.135 → 1.992** (monotone)
  - `global_step = 21`, report hashes = locked hashes, `state = done`,
    `upload create ok`, `SFT01 COMPLETE uploaded=priyanshu471/sft01-output`.
- **Checkpoints (resumable, save per epoch as locked):** worker paths
  `/kaggle/working/sft-01-output/checkpoint-7`, `checkpoint-14`,
  `checkpoint-21` plus `/kaggle/working/sft-01-output/sft-01-final/` — each
  checkpoint carries adapter weights, tokenizer, `training_args.bin`,
  `trainer_state.json`, `optimizer.pt`, `scheduler.pt`, `scaler.pt`,
  `rng_state.pth`. `checkpoint-21` adapter is byte-identical to `sft-01-final`
  (sha `65ad9595…c81f8`). Resume machinery: `SFT01_RESUME` env var or
  auto-detect of latest `checkpoint-*`; **no runtime interruption occurred in
  attempt 2**, so no resume event was needed — the only interruption-like
  event was the attempt-1 post-training crash (§5, recorded, checkpoints left
  intact and verified against v2 by identical metrics).
- **Recorded run facts:** global steps 21 · epochs 3 · final (mean) loss
  2.713 · last train-log loss 1.555 · final lr 6.16e-07 (cosine end) ·
  runtime 354.6 s (training sub-run 147.2 s) · GPU Tesla T4 · checkpoint
  paths above · artifact names: kernel `sft-01-qlora-on-dapt-01-lineage-task-64`,
  output dataset `sft01-output`, status/log files `sft01_train_status.json` /
  `sft01_train_worker.log`.
- **Determinism note:** v1 and v2 produced identical metrics but
  bitwise-different adapter weights (fp16 GPU nondeterminism). The v2 adapter
  (the uploaded, fully-reported one) is canonical.

## 6. Final adapter artifact

- Uploaded dataset `priyanshu471/sft01-output` (7 files; adapter
  **174,655,536 B**); downloaded file-by-file (zip endpoint 404s right after
  create — known Kaggle quirk) and verified against the kernel's own output:
  dataset == `sft-01-final` == `checkpoint-21`.
- `adapter_model.safetensors` sha256 **`65ad9595…407c81f8`**; report sha256
  `1186b47c…ce6a087`.
- Lineage: DAPT-01 start adapter sha256 `9b4d2bdc…31cba75a58e9` ≠ final
  (**weights genuinely changed**), same LoRA geometry.
- Geometry parsed from the safetensors header (no torch needed): 504 tensors
  = 36 layers × 7 modules × (A+B); shapes r=16 on Qwen3-8B dims
  (q/k/v/o + gate/up/down), `lora_alpha=32`, `dropout=0.05`,
  `base_model_name_or_path = Qwen/Qwen3-8B-Base` — matches the locked config.
- Local persistence: `experiments/sft_01/checkpoints/sft-01-final/` (weights
  are **not** committed; Kaggle dataset + hashes are the durable record).

## 7. Held-out `sft_eval_v1` evaluation (9 rows)

- Numeric: eval_loss progression in §5 (the held-out signal the config locked
  on; the model improved every epoch, no epoch-count tuning was performed).
- Per-example greedy generations persisted to
  `data/evaluation/sft01_eval_results.jsonl` (9 rows, non-empty, prompt built
  exactly like training: user+assistant messages, no system prompt,
  `add_generation_prompt=True`).
- **Score: NOT_MEASURED** — the 9 rows carry no scoring rubric by design
  (Task 64 §12); generation evidence is recorded, no metric is invented.

### 7.1 Per-example behaviour on `sft_eval_v1` (observations, not a metric)

The held-out rows are manifest-attribution questions (7 SOURCE_ATTRIBUTION +
2 CANONICAL_VS_COMMENTARY) from sources never seen in training; RAG is not in
the loop, so this probes parametric behaviour directly. Descriptive
per-example record (read from `sft01_eval_results.jsonl`; no aggregate score
is asserted):

| example | behaviour observed |
|---|---|
| 0c412c5f (Agam 29 authors/publisher) | **wrong** — collapsed to "authored/published by Sthanakvasi"; output ended in an "INFRINGEMENT" token-repetition loop |
| e355a8ac (provenance, Notes on Modern Jainism) | **fabricated** — invents "Gift of the Librarian, University of California, Berkeley, 1970" (not in reference) |
| 8a4d2b6e (publisher/year, Paia-Sadda) | **correct** — Motilal Banarsidass, 1928 |
| b84e9cbd (tradition/sect, Woolner) | **sect assertion vs UNKNOWN reference** — states "sect of Digambara"; also ended in "INFRINGEMENT" repetition loop |
| 27687711 (provenance, Jain Sathan Kavasi) | under-confident — repeated "unknown/not known" where the reference records Internet Archive provenance; no fabrication |
| e24370cf (tradition/sect, Sajjhaimala) | **sect assertion vs UNKNOWN reference** — "Digambara tradition and the Sthanakavasi" |
| 7009447a (canonical?, Agam 29) | **correct** — canonical scripture |
| ec775818 (classification, Notes on Modern Jainism) | appropriately uncertain — declines the four categories (reference status UNKNOWN) |
| 8c483765 (classification, Paia-Sadda) | **correct** — "an edition"; but output ended in a CJK "这个地图" repetition loop |

Observed descriptively: 3/9 outputs ended in token-repetition loops
(0c412c5f, b84e9cbd, 8c483765); 2/9 asserted a sect not present in the
reference (b84e9cbd, e24370cf); 1/9 fabricated a provenance fact
(e355a8ac); 3/9 clearly correct (8a4d2b6e, 7009447a, 8c483765 answer before
the loop). These are recordings of behaviour, **not** rubric scores; the
evaluator-based fields for this set remain NOT_MEASURED.

Behaviours named in Phase 6 that this set cannot probe
(Sthānakavāsī distinction, abstention, Prakrit terminology, practice
explanation) are covered by the frozen 47-case set in §9–§12; the eval set
itself contains no such cases.

## 8. Frozen-set inference design (protocol parity)

New kernel `priyanshu471/sft-01-infer-task65` (v1, COMPLETE):

- Cases packed from `data/evaluation/dapt01_eval_cases.jsonl` by
  `build_infer_kernel.py`, which asserts packed bytes == frozen file bytes;
  the kernel re-hashes the payload in-session against `06625f72…7765b81` and
  aborts on mismatch.
- The 47-case arm mirrors `task60_infer_kaggle.py` verbatim: same
  SYSTEM_PROMPT, chat-template-if-available prompt, greedy decoding,
  max_new_tokens=192, seed=42, 4-bit NF4 load, unmerged `PeftModel`
  (`is_trainable=False`).
- The kernel also aborts unless the adapter hashes to `65ad9595…c81f8` and
  `eval.jsonl` hashes to `4ef9d814…722cb`.
- Environment parity with Task 60 confirmed from both run-metadata files:
  transformers 5.0.0, torch 2.10.0+cu128, Tesla T4, greedy, 192, seed 42.
- Outputs: `dapt01_sft_results.jsonl` (47 rows, same id order as the frozen
  base/dapt files), `sft01_eval_results.jsonl` (9),
  `task65_sft_infer_metadata.json`. BASE and DAPT arms were **not** re-run;
  the frozen Task-60 result files are used as-is.
- Frozen 47-case sha256 re-checked after scoring: unchanged.

## 9. Three-way results — overall and by category

Scorer `experiments/sft_01/evaluation/score_task65_3way.py` imports
`score_task60` and applies its metric functions verbatim to all three arms
(no metric drift possible); writes
`data/evaluation/sft01_3way_comparison.json` (Task-60's
`dapt01_comparison.json` untouched).

Overall macro: base 0.2021 · dapt 0.2660 · sft 0.2305
(sft−dapt **−0.0355**, sft−base **+0.0284**); pass-all 6 / 8 / 7.

| category | n | base | dapt | sft | sft−dapt | sft−base |
|---|---|---|---|---|---|---|
| ABSTENTION | 4 | 0.0 | 0.0 | **0.25** | +0.25 | +0.25 |
| AGAM_GROUNDED | 4 | 0.25 | 0.0833 | 0.0833 | 0.0 | −0.1667 |
| GUJARATI | 4 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| HINDI | 4 | 0.1667 | 0.25 | 0.1667 | −0.0833 | 0.0 |
| JAIN_TERMINOLOGY | 4 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| MULTILINGUAL_MAPPING | 4 | 0.5 | 0.5 | 0.5 | 0.0 | 0.0 |
| PRACTICE | 4 | 0.375 | **0.625** | 0.375 | −0.25 | 0.0 |
| PRAKRIT | 4 | 0.0 | 0.375 | 0.375 | 0.0 | +0.375 |
| SANSKRIT | 3 | 0.1111 | 0.2222 | 0.1111 | −0.1111 | 0.0 |
| SOURCE_ATTRIBUTION | 4 | 0.0 | 0.125 | 0.125 | 0.0 | +0.125 |
| STHANAKAVASI_DISTINCTION | 4 | **1.0** | 0.75 | 0.75 | 0.0 | −0.25 |
| STHANAKAVASI_TERMINOLOGY | 4 | 0.0 | 0.25 | 0.0 | −0.25 | 0.0 |

## 10. Split and language views

By DAPT split (seen-ness):

| split | n | base | dapt | sft | sft−dapt |
|---|---|---|---|---|---|
| train (seen by DAPT) | 37 | 0.2162 | **0.3018** | 0.2432 | −0.0586 |
| val | 3 | 0.1667 | 0.3333 | 0.1667 | −0.1666 |
| test (unseen by DAPT) | 7 | 0.1429 | 0.0476 | **0.1905** | **+0.1429** |

By language: en 34 (sft 0.2255 vs dapt 0.2647), hi 8 (sft 0.3958 vs dapt
0.4375, still +0.1875 over base), gu 5 (0.0 all arms — OCR/substrings, same
as Task 60).

## 11. Abstention (4 cases)

| case | base | dapt | sft |
|---|---|---|---|
| DAPT01EVAL-036 (publication year, manifest absent) | ✗ | ✗ | **✓** ("does not provide… cannot provide") |
| DAPT01EVAL-037 (exact Terapanth founding year) | ✗ | ✗ | ✗ |
| DAPT01EVAL-038 (publisher absent) | ✗ | ✗ | ✗ |
| DAPT01EVAL-039 (Digambara Agam count absent) | ✗ | ✗ | ✗ |

0/4 → 0/4 → **1/4**. Abstention was the one Task-60-identified weakness where
SFT-01 shows a clear, mechanically-scored gain.

## 12. Improvements and regressions (objective keyterm deltas)

vs **DAPT-01** — improved: DAPT01EVAL-036 (abstention).
Regressed: 008 (Terapanthi accept Sthanakavasi scriptures, −1.0),
016 (Hindi avinīta śiṣya, −0.33), 023 (first vow, −0.33),
040 (Samayika 48 minutes, −0.5), 043 (Sarvatobhadra directions, −0.5).

vs **BASE** — improved: 009, 011 (Prakrit retained), 015 (Hindi),
034 (Stevenson attribution), 036 (abstention).
Regressed: 016, 026 (Agam counts, test split), 030 (Digambara reject canon).

## 13. Evaluator-based totals (label: `evaluator_based`, frozen review)

| metric | base | dapt | sft |
|---|---|---|---|
| factual_error (sum) | 41 | 47 | **NOT_MEASURED** |
| unsupported_claims (sum) | 6 | 20 | **NOT_MEASURED** |
| sect_confusion (cases) | 1 | 4 | **NOT_MEASURED** |
| degenerate_loop (cases) | 1 | 8 | **NOT_MEASURED** |

Coverage 47/47 for base/dapt from `dapt01_evaluator_review.jsonl` (rubric
preserved there). No evaluator pass was run for the SFT arm and none was
invented; these cells stay `NOT_MEASURED`.

## 14. Against the known DAPT-01 weaknesses (Task 60 list)

| known weakness | SFT-01 outcome |
|---|---|
| source attribution needs improvement | **retained DAPT gain only** (0 → 0.125 vs base); not improved beyond DAPT-01 |
| Sthānakavāsī distinction regressed (1.0 → 0.75) | **not fixed** (still 0.75) |
| factual-error flags up (41 → 47) | NOT_MEASURED |
| unsupported source-attributed claims up (6 → 20) | NOT_MEASURED |
| sect confusion up (1 → 4) | NOT_MEASURED |
| abstention unchanged (0/4) | **improved to 1/4** |
| Prakrit / practice / Sthānakavāsī terminology improved | Prakrit gain retained (0.375); **PRACTICE lost** (0.625 → 0.375); **STHANAKAVASI_TERMINOLOGY lost** (0.25 → 0.0) |

## 15. Limitations and threats to validity

1. **SFT-01 does not beat DAPT-01 on the frozen benchmark** — reported as-is;
   no metric was selected to flatter the result.
2. 17 of the 50 train rows share sources with the frozen 47-case eval
   (inherited from Task 64; DAPT-01 saw the whole corpus anyway) — weakens
   attribution claims in both directions.
3. Evaluator-based metrics are NOT_MEASURED for the SFT arm (§13).
4. `sft_eval_v1` generations have no score (§7); eval_loss is the only
   held-out numeric signal.
5. Adapter weights are not bitwise-reproducible across runs (fp16); metrics
   were identical, but only one canonical adapter exists.
6. Category cells are n=3–4 — deltas of ±1 case move them by 0.08–1.0;
   category-level results are directional, not statistically powered.
7. Guajarati/Jain-terminology absolute scores stay 0 for all arms
   (substring sensitivity on OCR text, same as Task 60).

## 16. Artifacts (all SHA256'd in `data/reports/task65_sft01_manifest.json`)

Kaggle:
- dataset `priyanshu471/jainllm-sft01-train` (50/9, round-trip verified)
- dataset `priyanshu471/sft01-output` (final adapter + report, round-trip verified)
- kernel `priyanshu471/sft-01-qlora-on-dapt-01-lineage-task-64` (v2, COMPLETE)
- kernel `priyanshu471/sft-01-infer-task65` (v1, COMPLETE)

Repository:
- `data/evaluation/dapt01_sft_results.jsonl`, `sft01_eval_results.jsonl`,
  `task65_sft_infer_metadata.json`, `sft01_3way_comparison.json`
- `data/reports/task65_sft01_metrics.json`, `task65_sft01_manifest.json`,
  `task65_sft01_train_status.json`, `task65_sft01_attempt1_error.json`,
  `task65_sft01_kaggle_run.log`, `task65_sft01_worker.log`,
  `task65_sft01_infer.log`, this report
- `experiments/sft_01/kaggle/train.py` (v2 fix),
  `experiments/sft_01/kaggle_infer/{infer.py, build_infer_kernel.py,
  kernel-metadata.json}`, `experiments/sft_01/evaluation/score_task65_3way.py`
- `experiments/sft_01/checkpoints/sft-01-final/` (local copy; not committed)

Commands executed (in order):
```bash
PYTHONPATH=src python3 tools/train_sft_01.py                # preflight 16/16
python3 experiments/sft_01/validate_sft01_dataset.py        # 16/16
python3 - <<'PY'  # dataset_create_new priyanshu471/jainllm-sft01-train ...
kaggle kernels push -p experiments/sft_01/kaggle            # v1 -> crash, v2 -> COMPLETE
kaggle kernels output priyanshu471/sft-01-qlora-on-dapt-01-lineage-task-64 -p /tmp/sft01_out2
python3 experiments/sft_01/kaggle_infer/build_infer_kernel.py
kaggle kernels push -p experiments/sft_01/kaggle_infer      # COMPLETE
kaggle kernels output priyanshu471/sft-01-infer-task65 -p /tmp/sft01_infer
python3 experiments/sft_01/evaluation/score_task65_3way.py
```

## 17. Readiness for next-stage evaluation + RECOMMENDED_NEXT_STEP (not executed — hard stop)

**Is the model ready for next-stage evaluation? CONDITIONALLY YES for
evaluation, NO for promotion.** The artifact is complete, hash-verified and
reproducible (adapter + tokenizer + config + trainer state recoverable from
`priyanshu471/sft01-output`), so it can be carried into any next-stage
*evaluation* (e.g. an evaluator pass to fill the NOT_MEASURED cells, or a
RAG-integrated probe). It must **not** be treated as an improvement over
DAPT-01: on the frozen benchmark it scores below DAPT-01 overall (§1) and the
held-out set shows fabrications, sect assertions against UNKNOWN references,
and repetition loops (§7.1). Promotion to any serving/training stage would
require (a) the missing evaluator pass and (b) a decision by the project on
the §1 regressions.

Any of the following would require a new task and explicit approval:
(a) a human/evaluator pass over the SFT-arm answers to fill the
`NOT_MEASURED` cells; (b) diagnosis of the PRACTICE /
STHANAKAVASI_TERMINOLOGY regressions (e.g. whether the 50-row mix pulled the
model away from DAPT-01 behaviour) and of the §7.1 repetition loops;
(c) only after (a)–(b), a redesigned SFT-02 mix or a DAPT-02 continuation.
**None of these was started.**
Training data was not expanded, the DAPT checkpoint was not retrained, the
frozen set was not touched, no metric was fabricated, no credentials were
printed.

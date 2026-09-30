# TASK 59 — DAPT-01 Final Forensic Audit (read/verify/report only)

- **Experiment**: DAPT-01 — QLoRA domain adaptation of `Qwen/Qwen3-8B-Base` on Jain (Sthanakavasi) domain corpus
- **Target run**: global_step 15,248 (complete), final checkpoint `priyanshu471/dapt01-checkpoint-15248`
- **Audit date**: 2026-09-29
- **Mode**: READ-ONLY. No training, no resume, no LoRA merge, no dataset/checkpoint modification, no artifact deletion. Unknowns are reported as `NOT_VERIFIED`, never guessed.
- **Audit environment**: `/tmp/audit_venv` — torch 2.14.0+cpu, transformers 5.17.0, peft 0.21.0, accelerate 1.15.0, safetensors 0.8.0; **no bitsandbytes, no GPU** (`nvidia-smi` absent), 13 GB free RAM, 64 GB free disk.

---

## 1. Artifact inventory (paths verified to exist on 2026-09-29)

| Category | Path / reference | Notes |
|---|---|---|
| Locked DAPT config (in code) | `experiments/dapt_01/kaggle/train.py:19-33` (`LOCKED` dict) | Authoritative locked hyperparameters |
| Planned config (original plan) | `configs/dapt_qwen3_8b.yaml` (2,214 B, 2026-09-21) | Plan-time YAML; superseded by `LOCKED` (see §7) |
| Experiment config | `experiments/dapt_01/config.yaml` (912 B) | status `CONFIGURED_NOT_STARTED`, blocker `GPU_NOT_AVAILABLE` |
| Training script (executed) | `experiments/dapt_01/kaggle/train.py` (29,483 B, 2026-09-28) | QLoRA trainer + callbacks; `TRAIN_DS = priyanshu47/jainllm-domain-train` (line 35) |
| Original notebook | `experiments/dapt_01/kaggle/dapt_01_kaggle.ipynb` | references older slug `priyanshu47/jain-domain-train` |
| Dataset (canonical) | `data/domain_train/{train,val,test}.jsonl`, `manifest.json` | 243,957 / 11,188 / 6,856 records (wc -l verified) |
| Base model cache | `.hf_cache/hub/models--Qwen--Qwen3-8B-Base/snapshots/49e3418fbbbca6ecbdf9608b4d22e5a407081db4/` | 5 safetensors shards, index total_size 16,383,567,872 B |
| Final checkpoint (local source) | `/tmp/kaggle_out_13781/dapt-01-output/checkpoint-15248/` | 11 files (no README.md) |
| Final checkpoint (verified copy) | `/tmp/ck15248/` | fresh download from `priyanshu471/dapt01-checkpoint-15248`; SHA256 table below |
| Final checkpoint (cloud, original) | `priyanshu471/dapt01-checkpoint-15248` | uploaded 2026-09-29 05:44:55 |
| Final checkpoint (cloud, mirror) | `priyanshu47/dapt01-checkpoint-15248` | uploaded 2026-09-29 08:49:10 |
| Other local checkpoints | `.bench_ckpt/checkpoint-3893`; `/tmp/audit_ck4500` (4500); `/tmp/kk12388/dapt-01-output/{13200,13400,13600}`; `/tmp/kaggle_out_13781/dapt-01-output/{14800,15000,15200,15248}`; `/tmp/kaggle_out_13781/ck13781_dl/` (13781); `dapt_known_good/known_good_step_{13800…15248}` (adapter+trainer_state) | |
| trainer_state / optimizer / scheduler / args | `/tmp/ck15248/{trainer_state.json,optimizer.pt,scheduler.pt,training_args.bin,scaler.pt,rng_state.pth}` | sizes in §2 |
| adapter files | `/tmp/ck15248/{adapter_config.json,adapter_model.safetensors}` | |
| tokenizer files | `/tmp/ck15248/{tokenizer.json,tokenizer_config.json,chat_template.jinja}` | bundled in every checkpoint |
| Session logs (final session) | `/tmp/kaggle_out_13781/dapt_train_worker.log` (5,430 B), `/tmp/kaggle_out_13781/dapt01-qlora-13781-to-15248.log` (320,562 B) | |
| Session logs (sessions ≤ 13781) | **not retained locally** | recorded as MISSING_INFORMATION |
| Session status/manifests | `/tmp/kaggle_out_13781/dapt_train_status.json`; `/tmp/kaggle_out_13781/dapt-01-output/RESUME13781_FINAL_REPORT.json`; `/tmp/kk12388/dapt-01-output/RESUME12388_FINAL_REPORT.json` | both reports: `final_integrity: ok`, `final_ckpt_errors: []` |
| Dataset cache actually consumed (final session) | `/tmp/kaggle_out_13781/domain_train/train.jsonl`, `/tmp/kaggle_out_13781/domain_train_textonly.jsonl` | see §6 |
| Transfer scripts/logs | `/tmp/transfer_ckpts_47.sh`, `/tmp/transfer_ckpts.log`, `/tmp/transfer_done.txt` (52 lines) | |
| Prior reports | `data/reports/task54_dapt01_report.md`, `task55_*`, `task55c_*`, `task56_*`, `task57_*` | earlier run-stage reports |

---

## 2. Final checkpoint integrity — `priyanshu471/dapt01-checkpoint-15248`

Verified by downloading the dataset (ZIP assembly) to `/tmp/ck15248` and hashing all files.

| Item | Status | Evidence |
|---|---|---|
| adapter model exists | **PASS** | `adapter_model.safetensors` 174,655,536 B, sha256 `9b4d2bdcfe089118d0634815596b628506a83c434d3863cff7a731cba75a58e9` |
| adapter config exists | **PASS** | `adapter_config.json` 1,097 B, sha256 `cbc419e464352259590dd01d09ec4cf8c8be7d0ea334754e7042c1684311e04c` |
| tokenizer exists | **PASS** | `tokenizer.json` 11,422,650 B (`be756060…`), `tokenizer_config.json` 667 B (`0fe2ab47…`), `chat_template.jinja` 4,116 B (`87a2728c…`) — self-contained bundle |
| trainer_state exists | **PASS** | 285,757 B, sha256 `1d3f52ed96ae84683de45c6ea93c706953da832f8953df7b5e34d00f49e1b9e1` |
| optimizer state exists | **PASS** | `optimizer.pt` 349,608,907 B, sha256 `19ae8830d9e47921c53d72036ca5a8b31b21660e686e126cdee4d9cd8bb611fa` |
| scheduler state exists | **PASS** | `scheduler.pt` 1,465 B, sha256 `e628794aae2635192cd552e1e610bdf4f73b7f2d38344ff08386f1be1d3430e9` |
| training args saved | **PASS** | `training_args.bin` 5,201 B, sha256 `4325ad157abf9191424c128dc8a2dbb48b60c86f3b7678fadd43774f131ce573` |
| fp16 GradScaler + RNG state | **PASS** | `scaler.pt` 1,383 B (`5df72c3c…`), `rng_state.pth` 14,645 B (`aea761d1…`) |
| global_step is actually 15248 | **PASS** | `trainer_state.global_step = 15248 = max_steps`; `epoch = 1.0`; 1,524 loss entries, steps 10→15240, all gaps = 10 |
| loadable / structurally valid | **PASS** (structural) | meta-device load of Qwen3-8B-Base + PeftModel wrapper + adapter state load: 504/504 keys match, 0 shape mismatches, 0 unexpected keys, all 504 tensors materialize byte-equal (§11). Full 4-bit materialized load = **NOT_VERIFIED** (no bitsandbytes/GPU/RAM) |
| adapter references `Qwen/Qwen3-8B-Base` | **PASS** | `adapter_config.base_model_name_or_path = "Qwen/Qwen3-8B-Base"` |
| LoRA configuration matches locked | **PASS** | r=16, α=32, dropout=0.05, bias=none, task_type=CAUSAL_LM, use_dora=false — equals `LOCKED` |
| target modules match | **PASS** | `["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"]` (7 modules × 36 layers) |
| r/alpha/dropout match | **PASS** | 16 / 32 / 0.05 exactly |
| quantization configuration consistent | **PASS** (code evidence) | `train.py:419-423` `BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True)`; checkpoint contains adapter-only weights (no full-precision model copy), consistent with 4-bit training. Runtime 4-bit load = **NOT_VERIFIED** (§11) |
| no unexpected architecture change | **PASS** | checkpoint tensors = exactly 504 LoRA tensors (36 layers × 7 modules × {lora_A,lora_B}); structural model has 903 param tensors (399 base + 504 LoRA); no added/removed modules |

Local source `/tmp/kaggle_out_13781/dapt-01-output/checkpoint-15248` vs downloaded `/tmp/ck15248`: **all 11 files SHA256 ALL_MATCH** (local source additionally has `README.md`, excluded by the uploader).

**FINAL_CHECKPOINT = VERIFIED.**

---

## 3. Transferred main copy — `priyanshu47/dapt01-checkpoint-15248`

Transfer job: `/tmp/transfer_ckpts_47.sh` (priyanshu471 → priyanshu47), run twice (first pass completed 08:49:12 UTC, retry pass completed 09:25:13 UTC).

- **52 of 53** checkpoints transferred (`/tmp/transfer_done.txt`, 52 lines).
- **Per-dataset verification of all 52** on `priyanshu47` via `kaggle datasets files`: every dataset contains `adapter_model.safetensors` (174,655,536 B) + `trainer_state.json` (>10,000 B) + `optimizer.pt` — **VERIFIED_OK=52, BAD=0**.
- **Step 15248 (the deliverable), hash-level comparison** — files pulled individually from `priyanshu47/dapt01-checkpoint-15248` and compared with the local source:

| File | priyanshu47 sha256 | Result |
|---|---|---|
| adapter_config.json | `cbc419e4…` | MATCH |
| adapter_model.safetensors | `9b4d2bdc…` | MATCH |
| trainer_state.json | `1d3f52ed…` | MATCH |
| optimizer.pt | `19ae8830…` | MATCH |
| scheduler.pt | `e628794a…` | MATCH |
| training_args.bin | `4325ad15…` | MATCH |
| tokenizer.json, tokenizer_config.json, chat_template.jinja, rng_state.pth, scaler.pt | — | filename+size exact match (11/11 files listed) |

- **Failure: step 9600.** `priyanshu471/dapt01-checkpoint-9600` lists files (created 2026-09-26 15:15) but `DownloadDataset` returns **404** on every attempt (both passes); dataset is empty/broken at source. No local copy exists anywhere. `priyanshu47/dapt01-checkpoint-9600` does not exist. Neighbours 9400 and 9800 are transferred and verified → the checkpoint chain remains continuous; the gap is immaterial for resume/reproduction (any later step ≥14800 supersedes it).
- Full-ZIP download of `priyanshu47/dapt01-checkpoint-15248` currently 404s (zip assembly pending/failed on Kaggle side) although single-file downloads succeed — see WARNINGS.

**TRANSFER_STATUS = PARTIAL** (52/53; the required final checkpoint 15248 is **COMPLETE and hash-verified**; 9600 unrecoverable at source).

---

## 4. Trainer state forensics (answer to the scheduler question)

### 4.1 Recorded fields

| Field | Value |
|---|---|
| global_step / max_steps | 15,248 / 15,248 |
| epoch (top-level) | 1.0 |
| num_train_epochs (state) / (args) | 1 / 3.0 (inert — `max_steps > 0` overrides epochs) |
| total_flos | 8.085123272706048e+17 |
| num_input_tokens_seen | 0 (not tracked by this transformers build) |
| best_metric / best_global_step | 3.0743370056152344 / 500 |
| best_model_checkpoint | `/kaggle/working/dapt-01-output/checkpoint-500` (stale early-session pointer; rotated away — do not use; the trained artifact is step 15248) |
| eval entries in log_history | exactly 2: step 500 (eval_loss 3.0743, runtime 7421 s), step 1000 (eval_loss 3.1643) — from an early session only |
| logging_steps / save_steps / eval_steps (state) | 10 / 200 / 500 |
| trainer version metadata | **NOT_RECORDED** (transformers does not persist its version in `trainer_state.json`) |

### 4.2 Session map (reconstructed from training_args of successive checkpoints + LR fits + resume reports)

| # | Range | Session args (from that session's checkpoints) | LR regime |
|---|---|---|---|
| S1 | 0 → 3893 | `max_steps=-1, num_train_epochs=1` → 15248; warmup_ratio 0.03 → W=458; save 5000; log 10; optim ADAMW_TORCH_FUSED; workers 2; report_to tensorboard; metric eval_loss | A: cosine(T=15248, W=458) |
| S2 | 3893 → 4500 | `max_steps=5500, warmup_steps=0 (ratio None)`; save 500; log 10 (ck-4500 args) | B: cosine(T=5500, W=0) |
| S3 | 4500 → 5500 | `max_steps=5500, warmup 0.03` → W=165; save 200; log 20 (ck-5000 args) | C: cosine(T=5500, W=165) |
| S4 | 5500 → 7658 | `max_steps=15248` restored, warmup 0.03 → W=458; save 200; log 20 (ck-13200+ args identical) | D: cosine(T=15248, W=458) |
| S5 | 7658 → 9977 | same as S4 | D |
| S6 | 9977 → 12388 | same as S4 | D |
| S7 | 12388 → 13781 | same as S4 (RESUME12388_FINAL_REPORT: 1,393 steps, session_limit, final_integrity ok) | D |
| S8 | 13781 → 15248 | same as S4 (RESUME13781_FINAL_REPORT: 1,467 steps, completed_session_target, final_integrity ok) | D |

### 4.3 LR history — exact fits (acos-space; observed vs model, float64)

Logged LR at step *s* equals `λ(s−1−k)` where `k` = number of skipped optimizer steps so far, λ = cosine with the session's (T, W).

| Region | Steps | Fitted λ | Exact matches |
|---|---|---|---|
| A | 460–3890 | T=15248, W=458, k=0 | 344/344 (bit-exact) |
| B | 3900–4500 | T=5500, W=0, k=0 | 61/61 (bit-exact) |
| C | 4510–5490 | T=5500, W=165, k=0 | 99/99 (bit-exact) |
| D1 | 5510–8500 | T=15248, W=458, k=0 | exact |
| D2 | 8510–10130 | T=15248, W=458, k=1 | exact |
| D3 | 10140–12410 | T=15248, W=458, k=2 | exact |
| D4/E | 12420–15240 | T=15248, W=458, k=3 | exact |

Discontinuities (observed vs previous-model counterfactual):

- **3890 → 3900**: 1.7460e-04 (A) → **3.8980e-05** (B exact; A would predict 1.7446e-04). LR *dropped* because S2 ran with `max_steps=5500, warmup=0`.
- **4500 → 4510**: 1.5906e-05 (B exact) → **1.6550e-05** (C exact). Warmup 0.03 re-enabled at resume (W=165).
- **5500 → 5510**: 1.7338e-11 (C exact, end of its cosine) → **1.4776e-04** (D exact; C would predict ≈1.4e-09). **This is the "LR re-leap when max_steps fixed to 15248"** — confirmed: at the resume from ck-5500 the session's `TrainingArguments.max_steps` was restored from 5500 to 15248, so a freshly-constructed cosine(15248, W=458) restarted at 74% of its curve value. Loss did not spike (block mean 5000–5999 = 1.9193; 5510 loss 1.9534) — the re-leap behaved like a controlled warm restart.
- **No discontinuity** at resumes 7658, 9977, 12388, 13781 (λ constant, k unchanged across all four).

### 4.4 Optimizer / scheduler state continuity

Optimizer `state` was **never reset**:

| ckpt | gs | optimizer `step` | scheduler `last_epoch` | k (= gs − sched) |
|---|---|---|---|---|
| 3893 | 3893 | 3892 | 3893 | 0 |
| 4500 | 4500 | 4499 | 4500 | 0 |
| 5000 | 5000 | 4999 | 5000 | 0 |
| 13200 | 13200 | 13196 | 13197 | **3** |
| 13400 | 13400 | 13396 | 13397 | 3 |
| 13600 | 13600 | 13596 | 13597 | 3 |
| 13781 | 13781 | 13777 | 13778 | 3 |
| 14800 | 14800 | 14796 | 14797 | 3 |
| 15000 | 15000 | 14996 | 14997 | 3 |
| **15248** | **15248** | **15244** | **15245** | **3** |

- Adam moments magnitudes are continuous across every inspected checkpoint (`|exp_avg|` 2.6–3.3e-3, `|exp_avg_sq|` 7.1–7.6e-7, 504 entries each), step counters monotonically increasing 3892 → 15244 → **no optimizer reset ever**.
- Scheduler `last_epoch` and optimizer `step` keep a constant +1 offset from the first checkpoint onward (bookkeeping offset, constant → immaterial).
- `k` grows 0 → 3 at exactly the steps where the LR lag grows (k=1 first visible at 8510, k=2 at 10140, k=3 at 12420) → **three global steps advanced without an optimizer or scheduler step** (final: 15,248 global steps = 15,245 successful updates + 3 skipped attempts).
- Mechanism (code evidence): `transformers/trainer.py:1874-1880` (5.17.0) does
  `optimizer.step()` → read LR → `if not accelerator.optimizer_step_was_skipped: lr_scheduler.step()` → `state.global_step += 1`.
  The **only** in-loop path with this signature (gs +1, Adam +0, scheduler +0) is an fp16 GradScaler overflow skip.
- Supporting checks: all 1,524 logged `grad_norm` values are finite (min 0.329, median 0.880, max 1.957 — no inf/nan); the three skip windows (8501–8509, 10131–10139, 12411–12419) fall entirely on *unlogged* steps (logging every 10), and `grad_norm` at the first logged step after each window is finite (8510: 0.923, 10140: 1.088, 12420: 1.202); `loss_scale` is not logged at all.
- Therefore: skip mechanism = **strongly supported inference, not directly observed** (no `loss_scale` series, run's transformers version not recorded) → recorded as a WARNING, not a proven fact.

### 4.5 Answer to §4 (A / B / C)

**B — the scheduler was recreated/reconfigured during resumed sessions** (optimizer state was preserved throughout).

Concrete evidence (not loss-based):
1. `training_args.bin` differs between checkpoints: `max_steps` −1 (ck-3893) → 5500 (ck-4500, ck-5000) → 15248 (ck-13200 … ck-15248); `warmup_steps/ratio` 0.03 (ck-3893) → 0/None (ck-4500) → 0.03 (ck-5000 … ck-15248). A new session constructs a new `LambdaLR` from its own args; only `last_epoch` is restored from `scheduler.pt`.
2. Logged LR fits each session's λ bit-exactly (§4.3 table) with hard discontinuities exactly at the three arg-changing boundaries (3893, 4500, 5500).
3. The observed "LR re-leap" at 5510 (1.73e-11 → 1.48e-4) is impossible under a single continuous schedule; it matches `cosine(T=15248, W=458)` at `s−1` bit-exactly.
4. Counter-evidence for full recreation/reset: optimizer moments + step counters continuous → **optimizer was carried forward, scheduler step count was carried forward, only the schedule function was rebuilt**.
5. At the four clean resumes (7658, 9977, 12388, 13781) the schedule continued unchanged — resumes *could* preserve λ; the three changes are attributable to changed `max_steps`/`warmup` args in those sessions, not to data loss.

---

## 5. Sample-count investigation (243,957 vs 243,968)

- **DATASET_RECORDS** = 243,957 (`wc -l data/domain_train/train.jsonl`, also Kaggle `train.jsonl` line count, also text-only cache line count)
- **EFFECTIVE_SAMPLE_POSITIONS** = 243,968 = 15,248 × 16 (batch 1 × grad-accum 16)
- **DIFFERENCE** = 11
- **EXPLANATION** = final incomplete gradient-accumulation window. `max_steps` was set to `ceil(243,957 / 16) = 15,248`. After 15,247 optimizer steps, 15,247 × 16 = 243,952 micro-batches are consumed; the 15,248th step consumes the remaining **5** micro-batches, leaving **16 − 5 = 11** unfilled positions in that last nominal 16-wide window. This is arithmetic from `ceil`, not an error.
  Ruled out: padding (no padding is applied to the dataset; tokenization pads only within batches at the tokenizer level with `padding=False`), repeated samples (HF sampler, no wrapping: top-level `epoch = 1.0`, never >1.0; no duplicate steps in log_history; `ignore_data_skip` not set), dataloader dropout (`drop_last` not used by HF trainer for this path), resume accounting (all 8 sessions consume 16 micro-batches/step: the recorded `epoch` of **every one of the 1,524 log entries** equals `min(1.0, step × 16 / 243,957)` with **0 mismatches**).
- **CONFIDENCE** = HIGH for the arithmetic/tail-window explanation (deterministic, reproduced from `max_steps` and counts); the "each record seen exactly once" claim is inferred from HF's standard sampler plus exact one-epoch accounting (replaying the dataloader would require re-running training → not done).

---

## 6. Dataset fingerprint

| Item | Value |
|---|---|
| Canonical file | `data/domain_train/train.jsonl` — 757,616,666 B, **243,957 lines**, sha256 `120eca4b671da4814f230493ac19eb7599ce846e999e2b2a5ec3894ec1a2cb7c` |
| manifest | `data/domain_train/manifest.json` — sha256 `f38a91ef1850cce3934b8f6de2aedadcc6dbac321bbe97ae5c98c3e7a6313880`; 40 documents (32/4/4), document-level 80/10/10 split; train 243,957 / val 11,188 / test 6,856 (all wc -l verified) |
| val / test | `750fcc1b…` (11,188 lines) / `1f0c682e…` (6,856 lines) |
| text field | column `text` (required by `train.py:442-447`; every record has it — 0 records skipped during text-only re-extraction) |
| preprocessing | tokenization-only: `tok(text, truncation=True, max_length=2048, padding=False)` (`train.py:463`); no filtering, no dedup, no reshuffling at train time |
| Kaggle dataset (final sessions) | `priyanshu47/jainllm-domain-train` — files created **2026-09-23 17:47**, `lastUpdated` = same (single version, unchanged since); `train.jsonl` size 757,616,666 (identical size) |
| Kaggle dataset (original sessions) | `priyanshu47/jain-domain-train` — files created 2026-09-21 15:24; downloaded during this audit: **byte-identical to the repo copy** (`train.jsonl` sha `120eca4b…`, `manifest.json` sha `f38a91ef…`, `cmp` clean) |
| Byte identity chain | repo copy = Kaggle `jain-domain-train` copy (downloaded+hashed now) = Kaggle `jainllm-domain-train` copy (downloaded by the final session to `/tmp/kaggle_out_13781/domain_train/train.jsonl`, sha `120eca4b…`) |
| What the model actually consumed (final session) | `load_dataset("json")` failed → train.py fell back to `domain_train_textonly.jsonl` (243,957 lines, 76,771,742 B, sha256 `ae9d5f5c5b385ad732b671b22437487ef65c877434bf561d141e1795ff161b4d`). Re-running train.py's exact text-only extraction on the repo copy reproduces that cache **byte-for-byte (sha identical)** |
| Records changed after training? | **No.** Both Kaggle dataset versions are byte-identical to the repo file, and `jainllm-domain-train` has had no version since 2026-09-23 (before the final session started 2026-09-28). Kaggle does not expose per-version hashes via the CLI → the comparison is file-level byte identity of the current remote, which is what the sessions downloaded |

**DATASET = VERIFIED.**

---

## 7. Actual training config vs locked configuration

Expected = `LOCKED` dict (`experiments/dapt_01/kaggle/train.py:19-33`), which the script itself asserts at runtime (`train.py:329-331`). Actual = `training_args.bin` of ck-15248 + code evidence.

| SETTING | EXPECTED (LOCKED) | ACTUAL (ckpt-15248) | STATUS |
|---|---|---|---|
| base model | Qwen/Qwen3-8B-Base | Qwen/Qwen3-8B-Base (`base_model_name_or_path`) | MATCH |
| quantization | 4-bit NF4 | `load_in_4bit=True` (train.py:419-420) | MATCH (code evidence; runtime load NOT_VERIFIED) |
| NF4 | yes | `bnb_4bit_quant_type="nf4"` | MATCH |
| double quant | yes | `bnb_4bit_use_double_quant=True` | MATCH |
| LoRA rank | 16 | 16 | MATCH |
| LoRA alpha | 32 | 32 | MATCH |
| LoRA dropout | 0.05 | 0.05 | MATCH |
| target modules | q,k,v,o,gate,up,down (7) | identical set, 252 LoRA modules / 504 tensors | MATCH |
| learning rate | 2e-4 | 2e-4 | MATCH |
| scheduler | cosine | cosine | MATCH |
| warmup | ratio 0.03 | `warmup_ratio=0.03`, `warmup_steps=0.03` → ceil(15248×0.03)=**458** | MATCH (final session; **deviated in S2 (0) and S3 (165 of 5500)** — see §4, intentional session-level arg changes) |
| weight decay | (not in LOCKED; plan yaml 0.01) | 0.01 | MATCH plan |
| batch size | 1 | 1 (`per_device_train_batch_size`) | MATCH |
| gradient accumulation | 16 | 16 | MATCH |
| effective batch | 16 | 16 | MATCH |
| sequence length | 2048 | 2048 (tokenization uses `LOCKED["max_seq_length"]`) | MATCH |
| precision | fp16 | `fp16=True, bf16=False` | MATCH |
| seed | 42 | 42 (`data_seed=None` → follows seed) | MATCH |
| max steps | (LOCKED: none; plan: 1 epoch) | 15,248 = ceil(243,957/16) = exactly 1 epoch | MATCH |
| epoch | 1 | state `num_train_epochs=1`, top-level `epoch=1.0` (args field `num_train_epochs=3.0` is **inert** because `max_steps>0`) | MATCH (inert-args note) |
| evaluation strategy | (LOCKED: none; plan yaml: steps/500, load_best_model_at_end) | `eval_strategy=NO`, `do_eval=False`, `load_best_model_at_end=False` — only 2 evals at steps 500/1000 from an early session | **MISMATCH vs plan yaml** (intentional/known: DAPT-01 ran without evaluation) — potentially important, see WARNINGS |

Secondary deviations of the executed run from the **plan YAML** `configs/dapt_qwen3_8b.yaml` (all deliberate; `LOCKED` supersedes the YAML):

| Plan YAML | Executed | Impact |
|---|---|---|
| bf16 | fp16 (+ GradScaler) | intentional (`LOCKED.precision=fp16`); contributes to §4.4 skip risk |
| per_device 2 × ga 8 | 1 × 16 | harmless (same effective batch 16; smaller per-step memory) |
| save_steps 500 | 5000 (S1) → 500 → 200 (final; forced by callback `train.py:511-517`) | intentional (finer checkpointing for short sessions) |
| logging_steps 10 | 10 effective (args say 20, state says 10 → log warning `logging_steps: 20 (args) != 10 (trainer_state)`) | harmless |
| attn_implementation flash_attention_2 | default (SDPA/eager) | harmless on T4 |
| dataloader_num_workers 4 | 2 (S1) → 0 (final) | harmless |
| report_to tensorboard | [] (final) | harmless (no TB curves; log_history retained) |
| load_best_model_at_end true | false | see WARNINGS (no validation-driven selection) |

---

## 8. Loss curve forensics

All values read from `/tmp/ck15248/trainer_state.json` log_history (1,524 entries, every 10 steps, 10→15,240). Claimed values from prior reports vs actual:

| Step | Claimed | Actual | Status |
|---|---|---|---|
| 10 | 2.78 | **2.7784** | OK |
| 5500 | ≈1.99 | **1.9919** | OK |
| 7650 | 2.00 | **1.9987** | OK |
| 9970 | 1.78 | **1.7785** | OK |
| 12380 | 1.69 | **1.6851** | OK |
| 13780 | 1.75 | **1.7495** | OK |
| 15240 (final logged) | 1.57 | **1.5740** | OK |

- First measured loss: **2.7784** @ step 10. Minimum: **1.5159** @ step 10520. Mean of first 100 logs: **2.2197**; mean of last 100: **1.7676**.
- Block means (monotone decline, no session-boundary jumps): 0–999: 2.2217 → 3000–3999: 1.9613 → 5000–5999: 1.9193 → 7000–7999: 1.8742 → 9000–9999: 1.8199 → 11000–11999: 1.8076 → 13000–13999: 1.7721 → 15000–15248: 1.7628.
- **13,780 "uptick"**: 12380 (1.6851) vs 13780 (1.7495) is a comparison across a plateau, not a step change. Evidence: mean loss 13000–13780 = **1.7637**, mean 13790–14570 = **1.7646** (identical); 13770 = 1.7962, 13780 = 1.7495, 13790 = 1.6882 (already falling after the resume); no LR change at the 13781 resume (§4.3) → the uptick is **normal minibatch noise within a flat region**, not a training regression or resume artifact.
- Interpretation guard: falling training loss does **not** demonstrate improved Jain knowledge — no evaluation was run after step 1000 (see §12 / NEXT_RECOMMENDED_STEP).

---

## 9. Trainable parameters / adapter size

| Quantity | Value | How determined |
|---|---|---|
| Base model parameters | **8,190,735,360** (exact) | meta-device instantiation of `Qwen3ForCausalLM(config)`; 399 tensors, matches safetensors index (16,383,567,872 B ÷ 2 ≈ 8.19B bf16) |
| Trainable LoRA parameters | **43,646,976** | 504 tensors: lora_A 21,233,664 + lora_B 22,413,312; attention 15,335,392 + MLP 28,311,584; all fp32 |
| Percentage trainable | **0.5329 %** of base (0.5299 % of base+adapter) | computed |
| Adapter file size | 174,655,536 B (~166.6 MiB) | sha256 `9b4d2bdc…` |
| LoRA modules | 252 (36 layers × 7 modules) → 504 weight tensors | verified against structural model |
| Only LoRA trained? | **Yes** | checkpoint contains only LoRA tensors; structural load leaves the other 399 base tensors untouched (meta); no `modules_to_save`, `bias=none`, no head/embedding tuning |

---

## 10. Reproducibility audit

**REPRODUCIBLE = PARTIAL**

Present: locked config in code (`LOCKED`) + plan YAML + executed `training_args.bin`; exact dataset bytes (§6, reproducible text-only cache sha); base model revision pinned by snapshot `49e3418fbbbca6ecbdf9608b4d22e5a407081db4`; seed 42; full code (`train.py`); complete final checkpoint incl. optimizer/scheduler/RNG; session reports.

Missing pieces:
1. **Dependency versions of the run environment — NOT_VERIFIED.** `train.py` pip-installs whatever is latest at session start; `trainer_state.json` records no versions; no requirements lock exists in the repo; no session log prints installed versions.
2. Exact Kaggle GPU image / driver / CUDA of each session — not recorded.
3. `loss_scale` series and overflow warnings were not persisted (limits §4.4 verification).
4. Session logs for S1–S7 not retained locally (only S8 logs + two resume JSONs).
5. Bitwise determinism not guaranteed (fp16 + no `torch.use_deterministic_algorithms`, plan's `deterministic: true / benchmark: false` were not applied in the executed args).
6. Checkpoint `dapt01-checkpoint-9600` unrecoverable (broken source upload) — immaterial (§3).

---

## 11. Final checkpoint load test

Environment lacks GPU/bitsandbytes/RAM for a full 4-bit materialization (model bf16 would need 16.4 GB > 13 GB free RAM). Per spec, a lightweight structural load-only verification was performed (no training, no weight modification):

- Built `Qwen3ForCausalLM` from the base config **on the meta device** (0 bytes RAM) and wrapped it with `get_peft_model(LoraConfig(r=16, α=32, dropout=0.05, target_modules=7, bias=none, task_type=CAUSAL_LM))`.
- Loaded `/tmp/ck15248/adapter_model.safetensors` (with peft's `.default` adapter-name key mapping) via `load_state_dict(..., strict=False, assign=True)`.
- Result: **504/504 adapter keys matched**, 0 missing, 0 unexpected, 0 shape mismatches; all 504 tensors materialized on CPU and are **byte-equal to the file**; 399 base tensors remain meta (untouched); `requires_grad` set on exactly 504 tensors = 43,646,976 params.

**LOAD_TEST = PASS (structural + adapter materialization).** Full 4-bit end-to-end load = **NOT_VERIFIED** (no bitsandbytes, no GPU, insufficient RAM) — allowed by spec to be reported as such.

---

## 12. Final audit verdict

```
DAPT01_AUDIT_STATUS:      PASS_WITH_WARNINGS
FINAL_CHECKPOINT:         VERIFIED
TRANSFER:                 PARTIAL            (52/53; checkpoint-15248 COMPLETE & hash-verified; 9600 broken at source)
CONFIG:                   MATCHED            (vs LOCKED; plan-YAML deviations listed in §7, all known/intentional)
SCHEDULER:                RESUMED_WITH_CHANGE   (answer B — optimizer state preserved; schedule lambda rebuilt at 3 arg-change boundaries)
DATASET:                  VERIFIED
REPRODUCIBILITY:          PARTIAL
TRAINING_COMPLETION:      VERIFIED           (global_step 15248 = max_steps, epoch 1.0, final ckpt complete + uploaded)
```

**CRITICAL_FINDINGS**
1. Training completed: `global_step = 15,248 = max_steps`, `epoch = 1.0`, final checkpoint complete, uploaded to both accounts, hash-verified end-to-end.
2. **Scheduler recreated with changed args in 3 sessions** (S2: `max_steps` −1→5500 + warmup→0; S3: warmup→0.03; S4: `max_steps` 5500→15248) producing the confirmed LR re-leap at step 5510 (1.73e-11 → 1.48e-4, bit-exact fits on both sides). Loss stayed smooth — treated as a controlled warm restart, not a failure.
3. **3 global steps (≈8505, ≈10135, ≈12415) advanced without an optimizer/scheduler step** → 15,245 successful updates for 15,248 logged steps; signature exactly matches transformers' fp16 `optimizer_step_was_skipped` path (trainer.py:1874-1880). Immaterial to results (0.02 % of steps) but recorded.
4. `priyanshu471/dapt01-checkpoint-9600` is a broken/empty upload (404 on download) — cannot be mirrored; not needed for resume.

**WARNINGS**
1. No evaluation after step 1000; `best_model_checkpoint=checkpoint-500` is a stale pointer — **no validation evidence exists that step 15248 beats the base model** (this is the point of the next task).
2. Dependency versions of the training sessions are unpinned/unrecorded (§10.1).
3. Full 4-bit runtime load of the final adapter is NOT_VERIFIED in this environment.
4. fp16 (not bf16) was used vs the plan YAML; combined with the 3 observed step-skips, fp16 overflow is the best-supported explanation (not directly proven — `loss_scale` not logged).
5. `kaggle datasets download` (full ZIP) of `priyanshu47/dapt01-checkpoint-15248` currently 404s while single-file downloads work — the copy is intact (all 11 files listed, 6 hash-verified) but the ZIP endpoint should be re-checked before relying on bulk download.
6. `warmup_ratio` is deprecated in transformers 5.x (log warning) and `logging_steps 20 (args) != 10 (trainer_state)` — cosmetic.
7. `num_train_epochs=3.0` stored in final `training_args.bin` is inert but misleading; effective epochs = 1.

**NON-ISSUES**
- The 11-sample difference (§5): final partial accumulation window — arithmetic, not an error.
- The 13,780 loss "uptick": plateau noise; means before/after the 13781 resume are 1.7637 vs 1.7646.
- `save_total_limit=4` rotation (13800–14600 no longer in local output): all were uploaded before rotation (session report).
- Constant scheduler-vs-optimizer +1 bookkeeping offset: constant from the first checkpoint → immaterial.

**MISSING_INFORMATION**
- Run-time dependency versions; S1–S7 session logs; `loss_scale` series; Kaggle per-version file hashes (file-level byte identity used instead); full 4-bit load test.

---

## Compliance

No training/resume launched, no model/LoRA/dataset/checkpoint modification, no deletions, no fabricated metrics; unknowns reported as `NOT_VERIFIED`. Audit used read-only inspection plus a meta-device structural load test.

**NEXT_RECOMMENDED_STEP = BASE_VS_DAPT_EVALUATION**

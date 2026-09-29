# Task 56: CPU-only feasibility + optimization gate for DAPT-01 continuation

**Date:** 2026-09-23  
**Author:** opencode / mimo-v2.6-flash-free  
**Status:** COMPLETE — **CPU_DAPT_CONTINUATION = NOT_RECOMMENDED**  
**Full run:** NOT started (gate decision only)

---

## 1. Executive verdict

**`CPU_DAPT_CONTINUATION = NOT_RECOMMENDED`**

Continuing DAPT-01 from checkpoint-3893 on this Azure VM (B4as_v2, 4 logical / 2 physical cores, 15 GB RAM) would require **~168–171 days** of continuous wall time and **~$605–617** at B4as_v2 Linux PAYG westus2 (~$0.15/hr) — roughly **70× longer** than the Kaggle GPU pace (57.7 GPU-hours / 2.4 days) for the remaining 11,355 steps. Hardware/threading optimizations do not help: threads=4 is statistically no better than threads=2 (actually ~2% slower within noise).

**Do not start the full CPU DAPT run.** Resume only when a GPU (Kaggle quota reset or Azure GPU quota) is available.

---

## 2. Task scope & constraints (as executed)

- Short, conclusive CPU micro-benchmark (not a full training run).
- Never risk/modify original `checkpoint-3893` (work on isolated copy).
- Separate hardware/runtime optimizations from training-design changes.
- Do **not** change hyperparameters merely for speed; preserve experimental design.
- Stop after benchmark + recommendation.

**Locked DAPT-01 design (unchanged):** Qwen3-8B-Base, 4-bit QLoRA (nf4 + double_quant), LoRA r=16/α=32/dropout=0.05 on q/k/v/o + gate/up/down, lr=2e-4 cosine, warmup 0.03, max_seq=2048, effective batch 16 (batch=1 × grad_accum=16), seed 42, 15,248 total steps, optimizer AdamW (0.9, 0.999), weight_decay 0.01. Remaining steps: **11,355** (3893 → 15248).

---

## 3. VM / stack audit (Phase 1–3 summary)

| Item | Value |
|------|-------|
| SKU | Azure `Standard_B4as_v2` (westus2, JainVM) |
| CPU | 4 logical = 2 physical × 2 SMT (AMD EPYC 7763 ~3.24 GHz) |
| ISA | avx/avx2/fma; **no AVX512 / AMX** → fp32 compute on CPU (no AVX512-BF16) |
| RAM | 15 GB total, **no swap** |
| Disk | 123 GB total, ~80 GB free at end |
| Kernel | 6.17.0-1022-azure |
| Stack | torch 2.14.0+cpu, transformers 5.17.0, peft 0.21.0, bnb 0.50.2, datasets 5.0.1, accelerate 1.15.0 |
| Model cache | Qwen3-8B-Base 16.39 GB snapshot `49e3418f...` offline in `.hf_cache` |
| Pricing | B4as_v2 Linux PAYG westus2 ≈ **$0.15/hr** (~$110/mo); cheapest region $0.0984/hr |

**transformers 5.17 API notes:** `TrainingArguments` has no `warmup_ratio` (use `warmup_steps`); original run’s `training_args.bin` recorded warmup_ratio=0.03 / warmup_steps=0 / fp16 / ADAMW_TORCH_FUSED / batch=1 / grad_accum=16.

---

## 4. Benchmark methodology (Phase 4)

Script: `experiments/dapt_01/bench/cpu_qlora_microbench.py`

- **Isolated copy** of checkpoint-3893 under `.bench_ckpt/`; original path read-only (`-r--r--r--`), md5 `18281ffefb6ad93b28d4770a571fd43d` verified unchanged after runs.
- Manual timed loop (no HF Trainer `resume_from_checkpoint` — that path OOMs by reloading model+optimizer and fast-forwarding epoch=778 on a 68-sample set).
- Load Qwen3-8B-Base 4-bit + PEFT LoRA from checkpoint; restore 504 AdamW moment states from `optimizer.pt`.
- Pre-tokenize 64 short texts (mean ~99 non-pad tokens, max 1243); pad each microbatch to its longest (**not** to 2048 — padding all to 2048 caused OOM).
- Timed: **warmup=1 + 3 timed optimizer steps**, each = 16 microbatches (grad_accum=16), clip_grad=1.0, lr schedule as locked.
- fp32 compute (CPU), gradient_checkpointing=True, threads configurable (2 vs 4).
- Environment: `HF_HOME=.hf_cache`, `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, drop_caches before runs.

**Attempt history:**
1. Attempt 1: TypeError `warmup_ratio` → fixed to `warmup_steps=457`.
2. Attempt 2: HF Trainer resume → OOM at 11:32 (anon-rss ~10.6 GB).
3. Attempt 3: manual loop, pad-to-2048 → OOM at 13:42 (anon-rss **14.4 GB** during first step).
4. Attempt 4 (t2): dynamic padding → **SUCCESS**.
5. Attempt 5 (t4): threads=4, same design → **SUCCESS**.

---

## 5. Measured results

### threads=2 (primary)

| Metric | Value |
|--------|-------|
| Mean sec/optimizer step (3 timed) | **1279.4 s** (min 1170.3, max 1413.7) |
| Warmup step | 1080.6 s |
| tokens/step | 19,888 |
| tokens/sec | 15.55 |
| Model load | 197.5 s |
| RSS after load / peak | 10.25 GB / **13.58 GB** |
| CPU util mean | 193% |
| **Est. remaining (11,355 steps)** | **4,035 h ≈ 168.1 days** |
| **Cost @ $0.15/hr** | **~$605** |
| Cost @ $0.0984/hr (cheapest) | ~$397 |

Raw: `outputs/cpu_bench/result_t2.json`, log `bench_t2.log`.

### threads=4 (comparison)

| Metric | Value |
|--------|-------|
| Mean sec/optimizer step | **1304.2 s** (min 1184.4, max 1438.9) |
| Model load | 166.3 s |
| RSS after load / peak | 10.25 GB / **13.55 GB** |
| CPU util mean | 292% |
| **Est. remaining** | **4,114 h ≈ 171.4 days** |
| **Cost @ $0.15/hr** | **~$617** |

Raw: `outputs/cpu_bench/result_t4.json`, log `bench_t4.log`.

### Comparison

- t4 vs t2 mean: **+2.0% slower** (within run-to-run noise / SMT contention).  
- **threads=4 provides no speedup** on this 2-physical-core burstable VM.  
- Both runs stable: no OOM after dynamic-padding fix; peak RSS ~13.55 GB with ~2.5–3 GiB available throughout.

### Reference points

| Path | s/step (approx) | Remaining 11,355 steps |
|------|-----------------|------------------------|
| Kaggle T4 (authoritative) | 18.3 | **57.7 h ≈ 2.4 days** |
| CPU threads=2 (this bench) | 1279 | **168 days / $605** |
| CPU threads=4 (this bench) | 1304 | **171 days / $617** |
| CPU vs Kaggle | **~70× slower** | — |

Precomputed SKU table (from Phase 1 planning): even at 60 s/step → 189 h ≈ 7.9 days; our measured rate is ~21 min/step, far beyond any acceptable CPU budget.

---

## 6. Failure modes observed (documented, fixed)

1. **transformers 5.17 `warmup_ratio` TypeError** → use `warmup_steps=457` (0.03 × 15248).
2. **HF Trainer resume OOM** → abandon resume path for micro-bench; manual loop only.
3. **Pad-to-2048 OOM** (anon-rss 14.4 GB) → dynamic pad per microbatch (mean ~99 tokens).
4. **Historical OOMs** in `/var/log/kern.log` (4 events): opencode RSS spike + pad-to-2048 + no swap. Mitigations: offline env, drop_caches, stop competing processes, dynamic padding.

---

## 7. Hardware/runtime optimizations evaluated

| Optimization | Effect | Design change? |
|--------------|--------|----------------|
| Offline HF cache | Avoid re-fetch; load works | No |
| Dynamic padding (longest vs 2048) | Avoids OOM; matches Kaggle collator | No (runtime/I/O only; real training uses longest) |
| Drop page cache before run | Frees RAM headroom | No |
| Manual loop vs HF Trainer resume | Avoids resume-path OOM + epoch FF | No (benchmark harness only) |
| **threads=4 vs threads=2** | **No gain (+2% noise)** | No (runtime) |
| fp32 (no bf16 on this CPU) | Forced by ISA | Runtime adaptation |

**No hyperparameters, model, dataset, LoRA config, batch, lr, or schedule were changed for speed.**

---

## 8. Risks if someone forced a full CPU run

- **Time:** ~7 months continuous on one VM.
- **Cost:** ~$600+ on B4as_v2; cheaper regions ~$400 — still month-scale.
- **Stability:** Burstable B-series CPU credits; sustained 200–300% CPU may throttle after baseline credits → real wall time **longer** than bench estimate.
- **Memory:** Peak 13.6 GB / 15 GB with zero swap — any co-tenant (e.g. opencode RSS) can OOM-kill mid-run; checkpoints every N steps would risk corruption on kill.
- **Disk:** ~512 MB per adapter checkpoint × many saves fits in 80 GB free, but irrelevant given time verdict.
- **Experiment integrity:** Not a training-design change, but running 5 months of non-reproducible CPU wall-clock while Kaggle returns would risk desynced artifacts.

---

## 9. Decision gate & next command

### Decision

```
CPU_DAPT_CONTINUATION = NOT_RECOMMENDED
```

**Rationale:** Measured 1279–1304 s/step → 168–171 days / ~$605 for remaining 11,355 steps; threads=4 does not help; memory is tight (13.6 GB peak / 15 GB, no swap); Kaggle GPU path remains ~70× faster and cheaper in wall-clock.

### When GPU returns (do not run on CPU)

Resume from immutable checkpoint-3893 with the **original Kaggle notebook / locked config** (no hyperparameter drift). Authoritative path remains Tasks 52–55c Kaggle runs; dataset and LoRA config unchanged.

### If forced to re-bench later (not recommended)

```bash
# Only for re-validation after hardware change — NOT for full training
tmux new-session -d -s cpu_bench "source /home/azureuser/jainLLM/svk-corpus/.venv-cpu-bench/bin/activate && \
  HF_HOME=/home/azureuser/jainLLM/svk-corpus/.hf_cache HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  python /home/azureuser/jainLLM/svk-corpus/experiments/dapt_01/bench/cpu_qlora_microbench.py \
  --threads 2 --warmup 1 --steps 3 \
  --out /home/azureuser/jainLLM/svk-corpus/outputs/cpu_bench/result_t2.json 2>&1 | \
  tee /home/azureuser/jainLLM/svk-corpus/outputs/cpu_bench/bench_t2.log"
```

**STOP after this report. Do not start the full DAPT-01 continuation on CPU.**

---

## 10. Artifacts

| Path | Role |
|------|------|
| `experiments/dapt_01/bench/cpu_qlora_microbench.py` | Micro-benchmark harness |
| `outputs/cpu_bench/result_t2.json` | threads=2 results |
| `outputs/cpu_bench/result_t4.json` | threads=4 results |
| `outputs/cpu_bench/bench_t2.log`, `bench_t4.log` | Run logs |
| `outputs/cpu_bench/bench_texts.json` | 64 sample texts |
| `.bench_ckpt/checkpoint-3893/` | Isolated working copy (md5 verified) |
| `/tmp/kaggle_55c_final/dapt-01-output/checkpoint-3893/` | Original (read-only, untouched) |
| `/var/log/kern.log` | OOM-kill history |

**Checkpoint-3893 safety:** original mode `-r--r--r--`; working-copy md5 `18281ffefb6ad93b28d4770a571fd43d` unchanged after all benchmark runs.

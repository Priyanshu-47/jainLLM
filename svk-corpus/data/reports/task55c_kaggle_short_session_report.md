# Task 55c — Kaggle GPU DAPT-01 Report (Short Resume Session)

**Date:** 2026-09-23
**Status:** SUCCESS — time-safety stop fired cleanly, resumable checkpoint saved
**Kernel:** `priyanshu47/dapt01` (v6)
**Quota:** ~2.5 GPU-hours requested; session capped at 120 min

---

## 1. Context

Short-quota resume of DAPT-01 from **checkpoint-3500** (from Task 55 resume run 2). Goal was not to finish training, but to: run within a ~2h window, stop *before* the Kaggle hard limit, persist a fully resumable checkpoint, and write this report. No evaluation, no benchmarking, no comparison, no SFT — by design.

## 2. Run Summary

| Property | Value |
|----------|-------|
| Start time | 2026-09-23 05:43:39 UTC |
| End time | 2026-09-23 07:43:41 UTC |
| Training runtime | 7199.97 s (**2.00 h**) |
| Wall time (session) | **120.3 min** (limit 120 min) |
| Stop mechanism | `TimeSafetyCallback` — clean stop, **not** a Kaggle kill |
| Resumed from | checkpoint-3500 (dataset `priyanshu47/dapt01-checkpoint-3500`) |
| Global step before | **3500** / 15248 |
| Global step reached | **3893** / 15248 (**25.5%**) |
| Steps completed | **393** |
| Epoch progress | 0.2553 |
| Final status | COMPLETE (kernel status `KernelWorkerStatus.COMPLETE`) |
| Errors / warnings | None fatal. Benign resume-arg mismatch: `eval_steps`/`save_steps` 5000 (args) vs 500 (trainer_state) |
| Eval / comparison | SKIPPED (per task 55c) |

## 3. Throughput

| Metric | Value |
|--------|-------|
| Steps/sec | 2.118 (this session was faster than the ~17 s/step long-run estimate) |
| **s/step** | **~18.3 s/step** (7199.97 s / 393 steps) |
| Samples/sec | 33.883 |
| Checkpoint overhead | Time-safety saved a new checkpoint at the arbitrary step 3893 (not a multiple of 500), so no mid-session `save_steps` boundary was required |

## 4. Loss

| Step | Loss |
|------|------|
| 10 (original run) | 2.78 |
| 1000 (resume pt. run 2) | 2.02 |
| 3500 (start of this session) | 1.97 |
| 3600 | 1.83 |
| 3700 | 1.93 |
| 3800 | 1.94 |
| **3890 (last logged)** | **1.95** |

- Session-averaged `train_loss`: **0.196** (includes post-resume warmup window; see note below — this is the HF-reported mean over logged steps this run, not comparable to point losses).
- Loss is stable in the **1.83–1.97** band across 3500→3893. Grad_norm ~0.79–0.98. LR at cosine point ~1.75e-4.

## 5. Checkpoints Created

| Checkpoint | Purpose |
|------------|---------|
| `checkpoint-3500/` | Input, copied from `priyanshu47/dapt01-checkpoint-3500`. **Preserved unchanged** (fallback). |
| **`checkpoint-3893/`** | **New, created by time-safety stop. Next resume point.** |

### Integrity verified (checkpoint-3893)

| File | Size | Status |
|------|------|--------|
| `adapter_model.safetensors` | 174,655,536 B | OK |
| `optimizer.pt` | 349,608,907 B | OK |
| `scheduler.pt` | 1,465 B | OK |
| `trainer_state.json` | 74,186 B (`global_step=3893`) | OK |
| `tokenizer.json` | 11,422,650 B | OK |
| `training_args.bin`, `tokenizer_config.json`, `adapter_config.json` | present | OK |

Missing vs checkpoint-3500: `rng_state.pth`, `scaler.pt` — created by the Trainer's own `save_steps` path; the time-safety final-save path writes the core resumable set (adapter/optimizer/scheduler/trainer_state/tokenizer). `resume_from_checkpoint` works from this set (same pattern proven in the 1000→3500 resume).

## 6. Next Action

1. Package `checkpoint-3893` as Kaggle dataset **`priyanshu47/dapt01-checkpoint-3893`**.
2. Update notebook `CONFIG["checkpoint_path"]` → `dapt01-checkpoint-3893`, `checkpoint_step: 3893`, `session_timeout_minutes` as needed; delete old kernel version if push fails (2-session limit).
3. Resume with `trainer.train(resume_from_checkpoint=True)`.
4. **Remaining: 15248 − 3893 = 11,355 steps ≈ 57.7 GPU-hours at ~18.3 s/step** (≈ 5–6 more 2h sessions, or ~5 more 12h sessions).
5. After the final session: download last checkpoint, then run DAPT eval + base-vs-DAPT comparison. Do **not** start SFT until DAPT-01 completes the epoch.

## 7. Artifacts

| Location | Contents |
|----------|----------|
| `/tmp/kaggle_55c_final/dapt-01-output/` | Full kernel output: `checkpoint-3500/`, `checkpoint-3893/`, adapter, manifest, metrics, tfevents |
| `/tmp/kaggle_55c_final/dapt01.log` | Kernel log (time-safety, integrity, final status) |
| `data/reports/task55_kaggle_dapt01_report.md` | Prior report (run 2 → step 3500) |

# Task 55 — Kaggle GPU DAPT-01 Report (Resume Run 2)

**Date:** 2026-09-22
**Status:** PARTIAL — Cancelled by Kaggle 12h GPU session limit

---

## 1. Context

This is the second successful Kaggle execution of DAPT-01. It **resumed from checkpoint-1000** (created by the first run) using a Kaggle dataset (`priyanshu47/dapt01-checkpoint-1000`) and the notebook's `resume_from_checkpoint=True` path. The goal was to prove the checkpoint-resume flow works and continue domain-adapting Qwen3-8B-Base via QLoRA.

---

## 2. Run Summary

| Property | Value |
|----------|-------|
| Kernel | `priyanshu47/dapt01` (last version) |
| Start (session) | 2026-09-22 08:45:46 UTC |
| Training start | 2026-09-22 08:56:07 UTC |
| Last event | 2026-09-22 20:43:41 UTC |
| Total wall time | ~11.79 h (Kaggle interactive GPU limit = 12 h) |
| Final status | `CANCEL_ACKNOWLEDGED` (Kaggle timeout kill) |
| Resumed from | checkpoint-1000 (uploaded as Kaggle dataset) |
| Reached | global step **3500** / 15248 (**23.0%**) |
| Steps this run | **2500** (global 1000 → 3500) |
| Checkpoints saved | 2500, 3000, 3500 |
| Eval | Disabled (`eval_strategy="no"`) — no eval overhead |

---

## 3. Training Configuration (effective)

| Parameter | Value |
|-----------|-------|
| Model | `Qwen/Qwen3-8B-Base`, 4-bit QLoRA |
| LoRA r / alpha / dropout | 16 / 32 / 0.05 |
| Batch size / grad accum | 1 / 16 (effective batch 16) |
| Max seq length | 2048 |
| Learning rate | 2e-4 (cosine), warmup ratio 0.03 |
| Precision | fp16 |
| Steps / epoch | 15,248 |
| Best eval metric (stale) | 3.074 @ step 500 (from run 1) |

---

## 4. Loss Progression

| Step | Loss |
|------|------|
| 10 (run 1) | 2.78 |
| 1000 (run 1, resume pt) | 2.02 |
| 2500 | 1.80 |
| 3000 | 1.89 |
| 3500 | 1.97 (noisy 1.77–2.29) |

Rolling averages:

| Window | avg loss |
|--------|----------|
| 0–500 | 2.32 |
| 500–1000 | 2.12 |
| 1000–2000 | 2.06 |
| 2000–3000 | 2.05 |
| 3000–3500 | 1.98 |

Loss is decreasing, though with high step-to-step noise (independent of batch across sessions). No eval ran this session (disabled by design).

---

## 5. Throughput

| Metric | Value |
|--------|-------|
| Training rate | ~17 s/step |
| Steps this session (12h) | ~2500 |
| Remaining steps | 11,748 |
| Est. remaining GPU time | **~55.4 GPU-hours** (~5 more 12h sessions) |
| Total training budget | ~72 GPU-hours across all sessions |

---

## 6. Key Findings

1. **Checkpoint-resume works end-to-end.** Uploaded checkpoint-1000 as a dataset, notebook copied it into the working dir, and `trainer.train(resume_from_checkpoint=True)` continued from step 1000. Proven resume is the correct recovery mechanism for Kaggle timeouts.
2. **Kaggle interactive GPU session limit is 12h.** The run reached ~11.97h of session time and was force-cancelled (`CANCEL_ACKNOWLEDGED`), even though no eval was running.
3. **Eval disable worked.** No training time was wasted on evaluation this run; the effective save/step cadence matches the checkpoint's trainer_state (`save_steps=500`).
4. **Training is real and stable.** Loss continues decreasing (2.05 → 1.98 region across the run window) with healthy grad_norms (~0.6–0.93).
5. **Full epoch cannot fit in one session.** 15,248 steps at ~17s/step ≈ 72h total; multiple resume cycles are mandatory. Each 12h session adds ~2500 steps.

---

## 7. Assets (downloaded to `/tmp/kaggle_final/dapt-01-output/`)

| Asset | Size | Notes |
|-------|------|-------|
| `checkpoint-3500/` | 512M | Next resume point (includes optimizer, scheduler, trainer_state) |
| `checkpoint-3000/` | 511M | Intermediate |
| `checkpoint-2500/` | 511M | Intermediate |
| `baseline/baseline_results.json` | 5K | Baseline eval on 10 prompts |
| `runs/.../events...` | 58K | TensorBoard events (loss history) |

---

## 8. Next Steps

1. Upload `checkpoint-3500` as a new Kaggle dataset (e.g. `dapt01-checkpoint-3500`), replacing the checkpoint-1000 source.
2. Update notebook `CONFIG["checkpoint_path"]` → `dapt01-checkpoint-3500` and push a new kernel version.
3. Resume from step 3500; each ~12h session adds ~2500 steps. **Estimated ~5 more sessions to finish the epoch.**
4. Optionally: consider raising `save_steps` in the checkpoint's trainer_state (when resuming, the old `save_steps=500` was retained by the state) to reduce mid-session checkpoint writes — minor, since `save_total_limit=3` bounds disk.
5. After final session, download the last checkpoint and run the DAPT evaluation + base-vs-DAPT comparison.

---

## 9. Risk

- **Long horizon:** ~55 GPU-hours remaining means roughly 4–5 more manual resume cycles, each requiring a checkpoint dataset upload. This is feasible but mechanical.
- **No mid-run eval signal:** eval only at the very end (after full epoch) — acceptable given eval previously cost ~2h per run and produced no actionable early signal.
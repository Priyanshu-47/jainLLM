# DAPT-01 long run handoff (3893 → 5500)

## Status: TRAINING (relaunch #5)
- Session: `dapt57` endpoint `gpu-t4-s-kkb-usw1b0-1kkqjwhy6iyym`
- Notebook: `/content/dapt01_train.ipynb` (ran OK 08:49 UTC)
- Worker PID: **2015**
- Status pusher PID: **2066**
- TRAIN start: 2026-09-24 08:49:46
- Target **5500**; save every **500**
- First expected ckpt: **4000** ~09:22 UTC

## Browser UI
`colab --auth=adc url -s dapt57`

## Dual backup
1. Kaggle: `Priyanshu47/dapt01-checkpoint-<step>` (SaveUploadCallback)
2. Azure VM: `experiments/dapt_01/checkpoints_vm_backup/checkpoint-<step>/`
   - poller: `/tmp/colab_xfer/vm_ckpt_backup.pid`

## Status dataset
`Priyanshu47/dapt01-train-status` (60s heartbeat)

## History of deaths
- Free Colab keep-alive 404 → prune (recurring ~20–45 min)
- Watchdog restarts KA; if prune happens before first save, no progress

## Safety
- Source 3893 md5 `18281ffefb6ad93b28d4770a571fd43d`
- No tokens in repo; sessions.json never scrubbed

## 2026-09-24 pivot (after 09:10)
- Abandoned Kaggle CLI training: new account `priyanshu471` needs phone verification (already used by first account).
- Back on Colab notebook path: session `dapt57` endpoint `gpu-t4-s-kkb-usw1b0-2yqe1qmujeyoz`.
- Run via `colab exec -f dapt01_train.ipynb` (not Kaggle kernels).
- Kaggle downloads use public `priyanshu47/*` datasets; uploads of new ckpts may go to `priyanshu471/*` if token allows, else rely on VM backup poller.
- Keep-alive + watchdog + vm_ckpt_backup restarted.

## 2026-09-24 Kaggle TPU attempt
- Colab dapt57 recycled before step 4000 (still at 3893 on disk).
- Kaggle quota: GPU 30h, TPU 20h remaining (refresh 2026-09-26).
- New kernel: `priyanshu471/dapt01-tpu-3893-5500` (TpuV5E8, bf16 LoRA, no bitsandbytes).
- Old public inputs: `priyanshu47/jainllm-domain-train`, `priyanshu47/dapt01-checkpoint-3893`.

### TPU probe result (2026-09-24 15:27 UTC)
- `enable_tpu: true` + `machine_shape TpuV5E8` + `--accelerator tpu` did NOT attach a TPU.
- Probe kernel saw: torch 2.10.0+cpu, jax CpuDevice only, no torch_xla, no /dev/accel*, no TPU_* env.
- TPU quota still 0/20h. Path switched to GPU T4 QLoRA (locked bitsandbytes config).
- Leftover Colab procs 21008/21035 killed.

## 2026-09-25 TASK 58 — resume from 4500, save_steps=200
- Durable checkpoint: priyanshu471/dapt01-checkpoint-4500 (global_step=4500).
- Prior GPU session cancelled at ~12h wall after uploading 4000+4500; steps 4501–4724 lost intentionally.
- New kernel: priyanshu471/dapt01-qlora-4500-to-5500 (T4, save_steps=200, save_total_limit=4, fp16, warmup_ratio=0.03, session cap 11.25h).
- Locked config unchanged; no TPU.

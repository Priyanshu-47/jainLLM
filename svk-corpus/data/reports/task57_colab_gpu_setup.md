# Task 57 — Google Colab GPU Automation Setup (DAPT-01)

**Status:** COMPLETE — setup + verification only. **DAPT training NOT started.**  
**Date:** 2026-09-23  
**Account (Colab):** priyanshulodha4747474747@gmail.com  
**Kaggle owner for transfer datasets:** Priyanshu47  

---

## Verdict

| Question | Answer |
|----------|--------|
| Official Colab CLI usable from Azure VM? | **YES** — `google-colab-cli` 0.7.2 via pipx |
| Free T4 GPU allocatable? | **YES** — multiple successful `colab new --gpu T4` |
| CUDA/PyTorch ready on Colab? | **YES** — Tesla T4, 14.56 GB, torch 2.11.0+cu130, CUDA 13.0 |
| Dataset + checkpoint transferable? | **YES** — public Kaggle datasets (preferred over multi-GB colab upload) |
| checkpoint-3893 loadable for resume? | **YES** — full load test `ok: true` on Colab |
| Resume runner ready (no training)? | **YES** — dry-run detects step 3893/15248 |
| Training started this task? | **NO** (by design) |
| checkpoint-3893 modified? | **NO** — md5 `18281ffefb6ad93b28d4770a571fd43d`, mode `-r--r--r--` |

---

## Phases completed

### Phase 1–4 — Environment + Auth
- Official `google-colab-cli` **0.7.2** installed via pipx → `~/.local/bin/colab`
- Google Cloud SDK **586.0.0** → `~/google-cloud-sdk/bin/gcloud`
- ADC login completed by user; `colab --auth=adc whoami` → `priyanshulodha4747474747@gmail.com`
- Dependency fix: `jupyter-kernel-client` 0.8 → **0.9.0** (needs `JupyterSubprotocol`); fallback import patched in `runtime.py`

### Phase 5–6 — GPU session + CUDA test
- T4 allocation: `colab new -s dapt57 --gpu T4` → READY / IDLE
- GPU test **PASS**:
  - device: Tesla T4 (7.5), total_memory_gb **14.56**
  - torch 2.11.0+cu130, cuda_available True, matmul OK

### Phase 7 — Transfer path (smallest practical)
**Chosen: public Kaggle datasets** (Colab large `upload` unreliable: 461MB SSL EOF; 40MB parts OK but clunky).

| Asset | Path | Size | Notes |
|-------|------|------|-------|
| domain_train | `priyanshu47/jainllm-domain-train` | 777 MB | **public**, CC0; create ~25s |
| checkpoint-3893 | `priyanshu47/dapt01-checkpoint-3893` | ~511 MB zip | **public**; full ckpt incl. optimizer |
| Base model | HF `Qwen/Qwen3-8B-Base` | ~16 GB | Colab pulls from HF; not uploaded |

Scripts staged under `experiments/dapt_01/colab/` (no secrets).

### Phase 8 — checkpoint-3893 LOAD TEST (Colab) — **PASS (`ok: true`)**
Ran on Colab T4 after Kaggle download:

| Check | Result |
|-------|--------|
| files_present | PASS |
| base_model = Qwen/Qwen3-8B-Base | PASS |
| lora r=16 / alpha=32 / dropout=0.05 | PASS |
| target_modules (q/k/v/o/gate/up/down) | PASS |
| peft_type LORA | PASS |
| global_step **3893** / max_steps **15248** | PASS |
| CUDA Tesla T4 | PASS |
| torch 2.11.0+cu130 / transformers 5.17.0 / peft 0.21.0 | PASS |
| tokenizer_load Qwen2Tokenizer | PASS |
| adapter_load PeftModelForCausalLM | PASS |
| optimizer_state / scheduler_state | PASS |
| forward_smoke shape=(1,2,151936) | PASS |
| full_load BitsAndBytes 4bit + PeftModel | PASS |

**Colab env notes for future runs:**
- transformers 5.x: use `BitsAndBytesConfig(load_in_4bit=True, ...)` — **not** `load_in_4bit=` kwarg to `from_pretrained`
- Need `pip install -U 'bitsandbytes>=0.46.1'` (installed 0.50.2 during test)
- Prefer `dtype=` over deprecated `torch_dtype=` where supported

### Phase 9–10 — Resume-ready runner (NO training)
- `experiments/dapt_01/colab/resume_dapt_colab.py`
  - Default **dry-run**; `--execute` required to train
  - Auto-detects `global_step` from `trainer_state.json` (never hardcodes)
  - Locks hyperparameters (model, LoRA, lr, seq len, batch, seed, total_steps)
  - Snapshots known-good checkpoint before any write
  - Session-bounded `max_steps` via `--max-steps-in-session`
- Colab dry-run: `global_step=3893`, `remaining=11355`, locked config matches DAPT-01

### Phase 11 — This report
`data/reports/task57_colab_gpu_setup.md`

---

## Operational lessons (important)

1. **Never run multiple `colab` session mutations in parallel** — races wipe `~/.config/colab-cli/sessions.json` and orphan server assignments.
2. `colab upload` of multi-hundred-MB single files is unreliable (SSL EOF); use **Kaggle** for bulk, or 40MB splits for small adapters.
3. Stale local session entries: `colab sessions` prunes; stop cleanly with `colab stop -s NAME` before recreate.
4. Kaggle CLI 2.2.4: `kaggle.json` key must be a current Kaggle API token (write auth); create fails 401 if expired/invalid.
5. Secrets: Kaggle token passed only via `colab exec --env` for the run; scrubbed from `history/*.jsonl` and `colab.log` after accidental injection into exec source. **Not** in git/repo.

---

## Resume workflow (when ready to train — NOT this task)

```bash
# 1) Ensure session
colab --auth=adc new -s dapt57 --gpu T4

# 2) Pull public datasets (token via env only)
#    priyanshu47/jainllm-domain-train → /content/domain_train
#    priyanshu47/dapt01-checkpoint-3893 → /content/checkpoint-3893

# 3) Dry-run first
python /content/resume_dapt_colab.py --dry-run

# 4) Only then (future task): bounded execute
# python /content/resume_dapt_colab.py --execute --max-steps-in-session <N>

# 5) Download results; stop session
colab --auth=adc stop -s dapt57
```

---

## Safety confirmations

- [x] DAPT training not started  
- [x] checkpoint-3893 original untouched (md5 + permissions)  
- [x] No tokens in source, git, notebooks, dataset files, or this report  
- [x] Session stopped after verification  
- [x] Official Colab CLI only (no forks)  
- [x] Hyperparameters / dataset / objective unchanged  

---

## Artifacts

| Path | Purpose |
|------|---------|
| `experiments/dapt_01/colab/checkpoint_load_test.py` | Load-test script |
| `experiments/dapt_01/colab/resume_dapt_colab.py` | Resume runner (dry-run default) |
| `experiments/dapt_01/colab/colab_kaggle_loadtest.py` | Kaggle download + load test orchestration |
| `experiments/dapt_01/colab/session_helpers.sh` | Sequential session lifecycle helpers |
| `experiments/dapt_01/colab/TRANSFER_PLAN.md` | Transfer strategy |
| `experiments/dapt_01/colab/setup_auth.sh` | ADC login helper |
| `data/reports/task57_colab_gpu_setup.md` | This report |

**Kaggle (public):**
- https://www.kaggle.com/datasets/priyanshu47/jainllm-domain-train
- https://www.kaggle.com/datasets/priyanshu47/dapt01-checkpoint-3893

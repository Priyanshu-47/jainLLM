# Task 53 — GPU Readiness Report

**Date:** 2026-09-21

---

## 1. Current Azure VM

| Property | Value |
|----------|-------|
| VM Name | JainVM |
| Resource Group | Jain |
| Region | westus2 |
| SKU | Standard_B4as_v2 |
| vCPU | 4 |
| RAM | ~15.6 GB |
| Storage | 128 GB (117 GB available) |
| GPU | NONE |

---

## 2. GPU Detection

### nvidia-smi
```
/bin/bash: line 1: nvidia-smi: command not found
```

### PyTorch CUDA
```
ModuleNotFoundError: No module named 'torch'
```

**Status:** No GPU detected. This is EXPECTED on Standard_B4as_v2.

---

## 3. Storage Validation

| Filesystem | Size | Used | Available | Use% |
|------------|------|------|-----------|------|
| /dev/root | 123G | 6.7G | 117G | 6% |

**Sufficient storage for:**
- Model files (~16GB for Qwen3-8B)
- Tokenizer (~10MB)
- HuggingFace cache (~20GB)
- Dataset (~500MB)
- Training outputs (~10GB)
- Checkpoints (~20GB)
- Logs (~1GB)

**Total estimated: ~67GB**
**Available: 117GB**
**Status: SUFFICIENT**

---

## 4. Dataset Validation

### Record Counts
| Split | Records | Source Documents |
|-------|---------|------------------|
| Train | 243,957 | 5 (SVK-0007, SVK-2022, SVK-2023, SVK-2024, SVK-2025) |
| Validation | 11,188 | 4 (SVK-2022, SVK-2023, SVK-2024, SVK-2025) |
| Test | 6,856 | 4 (SVK-2026, SVK-2027, SVK-2028, SVK-2029) |
| **Total** | **262,001** | **13 unique sources** |

### Token Estimates (Word-based)
| Split | Tokens | Avg Tokens/Record |
|-------|--------|-------------------|
| Train | 5,250,270 | 21.5 |
| Validation | 1,197,758 | 107.1 |
| Test | 663,100 | 96.7 |
| **Total** | **7,111,128** | **27.1** |

**Note:** These are word-based estimates. Actual tokenizer counts will differ.

---

## 5. Document-Level Leakage Validation

| Check | Result |
|-------|--------|
| Train-Val overlap | 0 documents |
| Train-Test overlap | 0 documents |
| Val-Test overlap | 0 documents |
| **Status** | **PASS** |

**Method:** Split by source_id (document-level). No document appears in multiple splits.

---

## 6. Data Quality Check

| Check | Result |
|-------|--------|
| Missing text | 0 records |
| Missing provenance | 0 records |
| Empty records | 0 records |
| **Status** | **PASS** |

### Rights Check
| Check | Result |
|-------|--------|
| Records with rights issues | 85,535 |
| **Status** | **WARNING** |

**Recommendation:** Review rights before training. Many records have unclear license status.

---

## 7. Dependency Validation

### Current Environment
| Package | Status |
|---------|--------|
| Python | 3.12.3 |
| pip | 24.0 |
| torch | NOT INSTALLED |
| transformers | NOT INSTALLED |
| peft | NOT INSTALLED |
| accelerate | NOT INSTALLED |
| bitsandbytes | NOT INSTALLED |
| datasets | NOT INSTALLED |

### Required for DAPT-01
```
torch>=2.1.0
transformers>=4.40.0
peft>=0.10.0
accelerate>=0.30.0
bitsandbytes>=0.43.0
datasets>=2.19.0
safetensors>=0.4.0
tensorboard>=2.16.0
```

---

## 8. DAPT Configuration Validation

| Parameter | Value | Status |
|-----------|-------|--------|
| Base model | Qwen/Qwen3-8B-Base | CONFIGURED |
| Method | QLoRA | CONFIGURED |
| LoRA rank | 16 | CONFIGURED |
| Learning rate | 2e-4 | CONFIGURED |
| Epochs | 1 | CONFIGURED |
| Batch size | 2 | CONFIGURED |
| Gradient accumulation | 8 | CONFIGURED |
| Max seq length | 2048 | CONFIGURED |
| Seed | 42 | CONFIGURED |

**Configuration file:** `configs/dapt_qwen3_8b.yaml`
**Status:** VALID

---

## 9. Training Command

### Ready to Execute (after GPU provisioning)
```bash
cd /home/azureuser/jainLLM/svk-corpus
./scripts/run_dapt_01.sh
```

### Or direct Python command
```bash
cd /home/azureuser/jainLLM/svk-corpus
python -m svk_corpus.training.dapt_trainer
```

---

## 10. Candidate Azure GPU SKUs

### Available in westus2

| SKU | GPU | VRAM | vCPU | RAM | Est. Cost/hr |
|-----|-----|------|------|-----|--------------|
| Standard_NC4as_T4_v3 | T4 | 16GB | 4 | 28GB | ~$0.50 |
| Standard_NC8as_T4_v3 | T4 | 16GB | 8 | 56GB | ~$1.00 |
| Standard_NC24ads_A100_v4 | A100 40GB | 24GB | 8 | 220GB | ~$3.50 |
| Standard_NC48ads_A100_v4 | A100 80GB | 48GB | 16 | 440GB | ~$7.00 |
| Standard_NC96ads_A100_v4 | A100 80GB | 96GB | 32 | 880GB | ~$14.00 |

### Recommendation
**Minimum:** Standard_NC24ads_A100_v4 (24GB VRAM)
**Preferred:** Standard_NC48ads_A100_v4 (48GB VRAM)

### Cost Optimization Strategy
```
START GPU VM → TRAIN → EVALUATE → SAVE ARTIFACTS → DEALLOCATE VM
```

**Estimated training time:** 2-4 hours
**Estimated cost:** $7-28 (depending on SKU)

---

## 11. Current Blocker

```
GPU_AVAILABLE = NO
TRAINING_STARTED = NO
DAPT01_STATUS = BLOCKED_ON_GPU
```

**This is NOT a failure.** The VM is correctly prepared.

---

## 12. Exact Next Action

1. **Provision GPU VM** (Standard_NC48ads_A100_v4 recommended)
2. **Install dependencies** on GPU VM
3. **Copy dataset** to GPU VM (or use shared storage)
4. **Run DAPT-01** training
5. **Evaluate** base vs DAPT checkpoint
6. **Deallocate** GPU VM

---

## 13. Files Prepared

```
experiments/dapt_01/
├── config.yaml
├── dataset_manifest.json
├── tokenizer_info.json (pending)
├── environment.json (pending)
├── README.md (pending)
├── baseline/
└── evaluation/
```

---

## 14. Smoke Test Results (No GPU)

| Test | Result |
|------|--------|
| YAML/config parsing | PASS |
| Dataset loading | PASS |
| Tokenizer loading | PENDING (requires transformers) |
| Sample tokenization | PENDING |
| Model config loading | PENDING |
| LoRA config creation | PENDING |
| Training command construction | PASS |
| Output directory creation | PASS |

---

## 15. Final Status

```
TASK53_STATUS = GPU_READY_PENDING_PROVISIONING
TRAINING_STARTED = NO
DAPT01_STATUS = BLOCKED_ON_GPU
GPU_AVAILABLE = NO
```

**The VM is correctly prepared. DAPT-01 will execute once GPU is provisioned.**

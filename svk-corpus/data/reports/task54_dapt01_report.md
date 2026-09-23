# Task 54 — DAPT-01 Training Report

**Date:** 2026-09-21
**Status:** BLOCKED_ON_GPU_QUOTA

---

## 1. Objective

Execute the first real Jain domain model training run:
- Qwen3-8B-Base
- QLoRA domain adaptation
- DAPT-01 Jain domain checkpoint
- Baseline vs DAPT evaluation

---

## 2. Azure GPU

### Current Subscription
- **Subscription:** Azure subscription 1
- **Tenant:** Default Directory
- **Region:** westus2

### GPU Quota Status

| GPU Family | Current Usage | Limit | Status |
|------------|---------------|-------|--------|
| Standard NCADS_A100_v4 Family vCPUs | 0 | 0 | **BLOCKED** |
| Standard NC Family vCPUs | 0 | 6 | Available (T4) |
| Standard NCSv3 Family vCPUs | 0 | 0 | BLOCKED |
| Standard NDAMSv4_A100Family vCPUs | 0 | 0 | BLOCKED |

### Problem

**GPU quota is 0 for A100-class GPUs.**

To provision Standard_NC48ads_A100_v4 (A100 80GB, 48GB VRAM):
- Required quota: 16 vCPUs (NCADS_A100_v4 Family)
- Current quota: 0 vCPUs
- **Quota increase required**

---

## 3. Hardware

### Current VM (JainVM)
- **SKU:** Standard_B4as_v2
- **vCPU:** 4
- **RAM:** ~15.6 GB
- **Storage:** 128 GB (117 GB available)
- **GPU:** NONE

### Required GPU VM
- **SKU:** Standard_NC48ads_A100_v4
- **GPU:** A100 80GB
- **VRAM:** 48GB
- **vCPU:** 16
- **RAM:** 440 GB
- **Storage:** >= 150 GB

---

## 4. Dataset

| Split | Records | Tokens (est) | Sources |
|-------|---------|--------------|---------|
| Train | 243,957 | 5,250,270 | 5 |
| Validation | 11,188 | 1,197,758 | 4 |
| Test | 6,856 | 663,100 | 4 |
| **Total** | **262,001** | **7,111,128** | **13** |

### Document-Level Split
- Train-Val overlap: 0 documents
- Train-Test overlap: 0 documents
- Val-Test overlap: 0 documents
- **Status:** PASS

---

## 5. Training Configuration

| Parameter | Value |
|-----------|-------|
| Base model | Qwen/Qwen3-8B-Base |
| Method | QLoRA |
| LoRA rank | 16 |
| LoRA alpha | 32 |
| Learning rate | 2e-4 |
| Epochs | 1 |
| Batch size | 2 |
| Gradient accumulation | 8 |
| Max seq length | 2048 |
| Seed | 42 |

**Configuration file:** `configs/dapt_qwen3_8b.yaml`

---

## 6. Blocker

```
TASK54_STATUS = BLOCKED_ON_GPU_QUOTA
TRAINING_STARTED = NO
DAPT01_STATUS = BLOCKED_ON_GPU_QUOTA
```

### Required Azure Action

1. **Request GPU quota increase** for:
   - **Family:** Standard NCADS_A100_v4 Family vCPUs
   - **Region:** westus2
   - **Required:** 16 vCPUs
   - **Purpose:** DAPT-01 Jain domain model training
   - **Azure Resource Name:** `StandardNCADSA100v4Family`

2. **MFA Required:** Quota requests need Multi-Factor Authentication enabled on the account.

3. **After quota approved:**
   - Provision Standard_NC48ads_A100_v4
   - Install dependencies
   - Run DAPT-01
   - Evaluate

### How to Request Quota Increase

**Option A: Azure Portal (Recommended)**
1. Go to https://portal.azure.com
2. Navigate to Subscriptions → Azure subscription 1 → Usage + quotas
3. Search for "Standard NCADS_A100_v4 Family vCPUs"
4. Click "Request increase"
5. Set new limit to 16
6. Submit request

**Option B: Azure CLI (requires MFA enabled)**
```bash
az quota create \
  --resource-name "StandardNCADSA100v4Family" \
  --scope "/subscriptions/7f3a13ca-4b50-43b0-bc44-163b14396b8f/providers/Microsoft.Compute/locations/westus2" \
  --limit-object value=16 \
  --resource-type "dedicated"
```

---

## 7. Files Prepared

```
experiments/dapt_01/
├── config.yaml
├── dataset_manifest.json
├── baseline/
└── evaluation/

configs/
└── dapt_qwen3_8b.yaml

scripts/
└── run_dapt_01.sh

data/reports/
└── task54_dapt01_report.md
```

---

## 8. Test Results

```
377 run, 375 passed, 2 pre-existing errors, 1 skip
No regressions
```

---

## 9. Recommendation for Task 55

1. **Request Azure GPU quota increase** for NCADS_A100_v4 Family
2. **After approval:** Provision GPU VM
3. **Execute DAPT-01** training
4. **Evaluate** baseline vs DAPT
5. **Deallocate** GPU VM

---

## 10. Cost Estimate

| Item | Cost |
|------|------|
| GPU VM (NC48ads_A100_v4) | ~$7/hr |
| Training time | 2-4 hours |
| Evaluation time | 1-2 hours |
| **Total estimated** | **$21-42** |

**Cost control:** Deallocate GPU immediately after experiment completes.

# Task 55 — CPU DAPT-01 Report

**Date:** 2026-09-21
**Status:** BLOCKED_ON_RESOURCES

---

## 1. Objective

Execute DAPT-01 QLoRA/domain-adaptation on CPU using JainVM.

---

## 2. Current VM

| Property | Value |
|----------|-------|
| VM Name | JainVM |
| CPU | 4 vCPU (AMD EPYC 7763) |
| RAM | 15 GB |
| Disk | 117 GB available |
| GPU | NONE |
| OS | Ubuntu 22.04 |

---

## 3. Memory Analysis

### Qwen3-8B Memory Requirements

| Precision | Model Size | Training Overhead | Total Required |
|-----------|------------|-------------------|----------------|
| float32 | 32 GB | ~4 GB | ~36 GB |
| float16 | 16 GB | ~4 GB | ~20 GB |
| 4-bit (QLoRA) | 4 GB | ~4 GB | ~8 GB |

### Available RAM

| Resource | Available |
|----------|-----------|
| Total RAM | 15 GB |
| Available RAM | ~14 GB |
| Model (float16) | 16 GB |
| **Deficit** | **~2 GB** |

---

## 4. Blocker

```
TASK55_STATUS = BLOCKED_ON_RESOURCES
```

**Cannot load Qwen3-8B in any precision that fits 15GB RAM.**

- float32: 32GB > 15GB → OOM
- float16: 16GB > 15GB → OOM
- 4-bit: 4GB fits, but bitsandbytes (QLoRA) is GPU-only

No CPU-compatible 4-bit quantization backend exists for training.

---

## 5. What Would Be Required

| Requirement | Current | Needed |
|-------------|---------|--------|
| RAM | 15 GB | >= 32 GB |
| vCPU | 4 | >= 8 |
| GPU | None | Optional but recommended |

### Viable Alternatives

1. **Increase VM RAM to 32GB+** → Run float16 LoRA on CPU
2. **Provision GPU VM** → Run QLoRA on GPU (original plan)
3. **Use smaller model** → Not approved (Qwen3-8B required)

---

## 6. Recommendation

The user's stated priority is:

> Execute the real DAPT-01 experiment now, even if CPU execution takes many hours.

To fulfill this, the VM must be upgraded to >= 32GB RAM.

Alternatively, the original GPU plan (A100) remains the correct path.

---

## 7. Test Results

```
377 run, 375 passed, 2 pre-existing errors, 1 skip
No regressions
```

---

## 8. CPU Execution Note

```
DAPT-01 was attempted on CPU because Azure GPU quota was unavailable.
The attempt was blocked by insufficient RAM (15GB vs 32GB required).
This was an intentional execution decision approved by the user.
```

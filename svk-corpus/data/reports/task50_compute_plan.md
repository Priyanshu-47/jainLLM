# Task 50: Compute Plan

**Date:** 2026-09-21

---

## 1. Current Environment

- Azure VM used for corpus engineering
- No GPU currently available for training

---

## 2. Training Requirements

### Domain Adaptation (QLoRA)

| Component | Requirement |
|-----------|-------------|
| Model | Qwen2.5-3B |
| VRAM | ~6GB |
| Training time | ~2-4 hours |
| Data | ~10M tokens |

### SFT (QLoRA)

| Component | Requirement |
|-----------|-------------|
| Model | Qwen2.5-3B |
| VRAM | ~6GB |
| Training time | ~1-2 hours |
| Data | ~50-100 examples |

### Inference

| Component | Requirement |
|-----------|-------------|
| Model | Qwen2.5-3B |
| VRAM | ~4GB |
| Latency | <1s per response |

---

## 3. GPU Requirements

| Task | Minimum GPU | Recommended GPU |
|------|-------------|-----------------|
| Domain Adaptation | 8GB VRAM | 16GB+ VRAM |
| SFT | 8GB VRAM | 16GB+ VRAM |
| Inference | 4GB VRAM | 8GB+ VRAM |

**GPU_REQUIRED = YES**

---

## 4. Cloud GPU Options

| Provider | GPU | VRAM | Approx Cost/hr |
|----------|-----|------|-----------------|
| Azure | NC6 | 12GB | ~$0.90 |
| Azure | NC12 | 24GB | ~$1.80 |
| AWS | g4dn.xlarge | 16GB | ~$0.50 |
| GCP | T4 | 16GB | ~$0.35 |

---

## 5. Recommended Setup

For first experiment:
- **GPU:** 16GB VRAM (T4 or equivalent)
- **Duration:** 4-6 hours
- **Estimated cost:** $1-3

---

## 6. Dataset Preprocessing

| Task | Compute |
|------|---------|
| Corpus preprocessing | CPU (current VM) |
| Tokenization | CPU |
| Quality filtering | CPU |
| Deduplication | CPU |

**Preprocessing can be done on current VM.**

---

## 7. Next Steps

1. Complete SFT review (Task 50)
2. Select base model
3. Provision GPU (when ready)
4. Run preprocessing on current VM
5. Transfer to GPU for training

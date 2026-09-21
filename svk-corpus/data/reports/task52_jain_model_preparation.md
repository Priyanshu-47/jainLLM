# Task 52: Jain Open-Source Model Preparation

**Date:** 2026-09-21

---

## 1. Executive Summary

Task 52 establishes the foundation for the first reproducible Jain-domain model experiment. We have:

1. **Audited existing pipeline** - Full infrastructure already exists
2. **Built domain dataset** - Document-level train/val/test split
3. **Created SFT seed dataset** - 6 HUMAN_VERIFIED examples
4. **Designed DAPT-01 experiment** - Qwen3-8B-Base with QLoRA
5. **Preserved all existing tests** - No regressions

---

## 2. Existing Pipeline Components Discovered

### Core Modules (Already Implemented)
- **acquisition/** - Internet Archive, HuggingFace acquisition
- **deduplication/** - Document deduplication
- **extraction/** - Text extraction from PDF/DjVu
- **normalization/** - Text normalization, script detection
- **segmentation/** - Document segmentation
- **quality/** - Quality checks, assessment
- **licensing/** - Rights gate, license evaluation
- **release.py** - Corpus release generation
- **training/** - SFT candidate extraction
- **retrieval/** - RAG retrieval system

### Data Infrastructure
- **manifests/** - Source/artifact/license manifests
- **schemas/** - Data validation schemas
- **configs/** - Policy and configuration files
- **tests/** - 14 test modules, 377 tests

---

## 3. Current Corpus State

### Source Count
- Total sources in manifest: 87
- Released RAG corpus: 164,238 units
- Released training corpus: 97,763 units
- Combined: 262,001 units

### Domain Split (New)
- **Train:** 32 documents, 243,957 records
- **Validation:** 4 documents, 11,188 records
- **Test:** 4 documents, 6,856 records
- **Split method:** Document-level (no leakage)

### SFT Seed Dataset (New)
- **HUMAN_VERIFIED:** 6 examples
- **Sources:** SVK-0038, SVK-2022, SVK-2023, SVK-2024, SVK-2025, SVK-2029
- **Categories:** CONCEPT_EXPLANATION, PRACTICE_EXPLANATION, AGAM_EXPLANATION

---

## 4. New Files/Modules Created

### Domain Dataset
- `data/domain_train/train.jsonl` - Training split
- `data/domain_train/val.jsonl` - Validation split
- `data/domain_train/test.jsonl` - Test split
- `data/domain_train/manifest.json` - Split manifest

### SFT Seed Dataset
- `data/training/sft_seed_v1.jsonl` - 6 HUMAN_VERIFIED examples

### DAPT Configuration
- `configs/dapt_qwen3_8b.yaml` - Training configuration
- `tools/train_dapt_01.py` - Training script generator
- `src/svk_corpus/training/dapt_trainer.py` - Trainer module

---

## 5. DAPT-01 Experiment Design

### Base Model
- **Model:** Qwen/Qwen3-8B-Base
- **Parameters:** 8B
- **Architecture:** Transformer with Gated DeltaNet
- **License:** Apache 2.0

### Training Method
- **Method:** QLoRA (parameter-efficient)
- **LoRA rank:** 16
- **Learning rate:** 2e-4
- **Epochs:** 1
- **Batch size:** 2
- **Gradient accumulation:** 8
- **Max sequence length:** 2048

### Dataset
- **Domain corpus:** 243,957 training records
- **Validation:** 11,188 records
- **Source:** JainQQ, JainEbooks, existing cleared corpus

---

## 6. Rights/Permission Status

### Already Cleared
- 8 JainQQ sources (SVK-2022..2029) - Permission released
- Existing cleared corpus - Rights verified

### Requires Permission
- Most DLI sources - No rights metadata
- Modern publications - Life+60 not expired

### Recommendation
Use only cleared sources for DAPT-01. Expand after rights verification.

---

## 7. Hardware Requirements

### Minimum
- **GPU:** 24GB VRAM (RTX 3090/4090)
- **RAM:** 32GB
- **Storage:** 100GB

### Recommended
- **GPU:** 48GB+ VRAM (A6000/A100)
- **RAM:** 64GB
- **Storage:** 200GB

### Cloud Options
- Azure NC24ads_A100_v4 (80GB VRAM)
- AWS g5.2xlarge (24GB VRAM)
- GCP A100-40GB

---

## 8. Test Results

### Existing Tests
- **Total:** 377 tests
- **Passed:** 375
- **Errors:** 2 (pre-existing, missing faiss/sentence_transformers)
- **Skipped:** 1
- **Regressions:** 0

---

## 9. Problems Encountered

### None
All components working as expected. Existing pipeline preserved.

---

## 10. Exact Command to Reproduce

### Step 1: Build Domain Split
```bash
cd /home/azureuser/jainLLM/svk-corpus
python3 /tmp/opencode/build_domain_split.py
```

### Step 2: Build SFT Seed
```bash
cd /home/azureuser/jainLLM/svk-corpus
python3 /tmp/opencode/build_sft_seed.py
```

### Step 3: Generate Training Script
```bash
cd /home/azureuser/jainLLM/svk-corpus
python3 tools/train_dapt_01.py
```

### Step 4: Run DAPT-01 (requires GPU)
```bash
cd /home/azureuser/jainLLM/svk-corpus
./scripts/run_dapt_01.sh
```

---

## 11. Recommended Task 53

1. **Provision GPU** for DAPT-01
2. **Run DAPT-01** training
3. **Evaluate** base vs DAPT checkpoint
4. **Expand SFT dataset** toward 100-300 examples
5. **Design evaluation framework** for Jain domain

---

## 12. Key Metrics

| Metric | Value |
|--------|-------|
| Total sources | 87 |
| RAG corpus units | 164,238 |
| Training corpus units | 97,763 |
| Domain train records | 243,957 |
| Domain val records | 11,188 |
| Domain test records | 6,856 |
| SFT seed examples | 6 |
| Base model | Qwen3-8B-Base |
| Training method | QLoRA |
| Estimated VRAM | 24-48GB |
| Estimated time | 2-4 hours |

---

## 13. Architecture Reminder

```
Prompting
→ Context Engineering
→ RAG (authoritative evidence)
→ Domain Adaptation (Jain knowledge)
→ SFT (answer behavior)
→ Alignment/Evals
```

**RAG remains the authoritative source for factual answers.**
**Domain adaptation teaches Jain language and terminology.**
**SFT teaches answer behavior and formatting.**

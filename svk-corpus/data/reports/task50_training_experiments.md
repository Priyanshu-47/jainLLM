# Task 50: Training Experiment Design

**Date:** 2026-09-21

---

## 1. Experiment Overview

Design controlled experiments to compare training approaches before actual training.

---

## 2. Experiments

### EXPERIMENT 0: Base Model + RAG

**Configuration:**
- Base model: Qwen2.5-3B (base checkpoint)
- No fine-tuning
- RAG retrieval for evidence

**Purpose:** Baseline for comparison

**Evaluation:**
- Jain factual understanding
- Source grounding accuracy
- Hallucination rate

### EXPERIMENT 1: Base Model + SFT + RAG

**Configuration:**
- Base model: Qwen2.5-3B (base checkpoint)
- SFT on human-reviewed examples
- RAG retrieval

**Purpose:** Test SFT impact on behavior

**Evaluation:**
- Answer quality
- Attribution accuracy
- Abstention correctness

### EXPERIMENT 2: Domain-Adapted Model + RAG

**Configuration:**
- Base model: Qwen2.5-3B
- Domain adaptation on Jain corpus
- RAG retrieval

**Purpose:** Test domain adaptation impact

**Evaluation:**
- Jain vocabulary improvement
- Terminology understanding
- General language regression

### EXPERIMENT 3: Domain-Adapted + SFT + RAG

**Configuration:**
- Base model: Qwen2.5-3B
- Domain adaptation + SFT
- RAG retrieval

**Purpose:** Combined approach

**Evaluation:**
- All metrics

---

## 3. Data Mix

| Dataset | Source | Purpose |
|---------|--------|---------|
| DOMAIN_TRAIN | JainQQ + JainEbooks + cleared corpus | Domain adaptation |
| SFT_TRAIN | HUMAN_VERIFIED examples only | Behavior training |
| RAG | Full retrieval corpus | Evidence grounding |
| EVAL | Held-out JainBench | Evaluation |

---

## 4. Domain Adaptation Design

**Current corpus:** ~10.57M tokens

**Approach:** Parameter-efficient adaptation (QLoRA)

**Parameters to test:**
- Learning rate: 1e-4 to 5e-5
- Epochs: 1-3
- Sequence length: 2048-4096
- LoRA rank: 8-32

**Evaluation:**
- Jain domain improvement
- General language regression
- Catastrophic forgetting

---

## 5. SFT Design

**Dataset:** HUMAN_VERIFIED examples only

**Approach:** QLoRA SFT

**Parameters:**
- Learning rate: 1e-5 to 5e-5
- Epochs: 2-5
- Batch size: 4-8
- Sequence length: 2048

---

## 6. Evaluation Metrics

| Metric | Description |
|--------|-------------|
| answer_correctness | Factual accuracy |
| source_grounding_accuracy | Citation correctness |
| attribution_accuracy | Teacher/Agam attribution |
| abstention_correctness | Proper abstention |
| language_quality | Readability |
| hallucination_rate | Unsupported claims |

---

## 7. Expected Outcomes

| Experiment | Expected Improvement | Risk |
|------------|---------------------|------|
| EXP 0 | Baseline | None |
| EXP 1 | Better behavior | Overfitting |
| EXP 2 | Better knowledge | Forgetting |
| EXP 3 | Best overall | Complex |

---

## 8. Next Steps

1. Complete SFT review (Task 50)
2. Select base model
3. Prepare domain training data
4. Run EXPERIMENT 0 (baseline)
5. Compare results

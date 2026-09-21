# Task 51: Experiment Matrix

**Date:** 2026-09-21

---

## 1. Experiment Overview

Four controlled experiments to compare training approaches.

---

## 2. Experiments

### E0: Base Model + RAG

**Configuration:**
- Base model: Qwen3.5-4B (base checkpoint)
- No fine-tuning
- RAG retrieval for evidence

**Dataset:**
- No training data
- RAG corpus: 164K units

**Trainable Parameters:** 0

**Expected VRAM:** ~3GB (inference only)

**Evaluation:**
- Jain factual understanding
- Source grounding accuracy
- Hallucination rate

**Success Criteria:**
- Baseline for comparison
- No regression on general tasks

**Risks:**
- May lack Jain domain knowledge
- May hallucinate without domain training

---

### E1: Base Model + SFT + RAG

**Configuration:**
- Base model: Qwen3.5-4B (base checkpoint)
- SFT on human-reviewed examples
- RAG retrieval

**Dataset:**
- SFT: HUMAN_VERIFIED examples only (currently 2)
- RAG: 164K units

**Trainable Parameters:** Low-rank adapters (QLoRA)

**Expected VRAM:** ~6GB

**Evaluation:**
- Answer quality
- Attribution accuracy
- Abstention correctness

**Success Criteria:**
- Improved answer behavior
- Better source grounding
- Proper attribution

**Risks:**
- Overfitting with limited examples
- May not generalize

---

### E2: Base Model + Domain LoRA + RAG

**Configuration:**
- Base model: Qwen3.5-4B (base checkpoint)
- Domain adaptation via LoRA on Jain corpus
- RAG retrieval

**Dataset:**
- Domain: ~10.57M tokens (JainQQ + JainEbooks + cleared corpus)
- RAG: 164K units

**Trainable Parameters:** Low-rank adapters (LoRA)

**Expected VRAM:** ~6GB

**Evaluation:**
- Jain vocabulary improvement
- Terminology understanding
- General language regression

**Success Criteria:**
- Improved Jain domain knowledge
- No catastrophic forgetting
- General language preservation

**Risks:**
- Forgetting general knowledge
- Domain shift issues

---

### E3: Base Model + Domain LoRA + SFT + RAG

**Configuration:**
- Base model: Qwen3.5-4B (base checkpoint)
- Domain adaptation via LoRA
- SFT on human-reviewed examples
- RAG retrieval

**Dataset:**
- Domain: ~10.57M tokens
- SFT: HUMAN_VERIFIED examples
- RAG: 164K units

**Trainable Parameters:** Low-rank adapters (LoRA)

**Expected VRAM:** ~8GB

**Evaluation:**
- All metrics from E0, E1, E2
- Combined improvement

**Success Criteria:**
- Best overall performance
- Domain knowledge + behavior

**Risks:**
- Complex training pipeline
- May not improve over E1 or E2

---

## 3. Training Sequence

1. **E0** (Baseline) - No training required
2. **E1** (SFT only) - Quick experiment
3. **E2** (Domain LoRA only) - Domain adaptation test
4. **E3** (Domain LoRA + SFT) - Combined approach

---

## 4. Data Separation

| Dataset | Purpose | Excludes |
|---------|---------|----------|
| DOMAIN_TRAIN | Domain adaptation | Evaluation data |
| SFT_TRAIN | Behavior training | Evaluation data |
| RAG | Evidence grounding | - |
| EVAL | Evaluation | All training data |

---

## 5. Evaluation Metrics

| Metric | Type | Description |
|--------|------|-------------|
| answer_correctness | Binary | Factual accuracy |
| source_grounding_accuracy | Binary | Citation correctness |
| attribution_accuracy | Binary | Teacher/Agam attribution |
| abstention_correctness | Binary | Proper abstention |
| language_quality | Likert | Readability (1-5) |
| hallucination_rate | Rate | Unsupported claims |

---

## 6. Expected Outcomes

| Experiment | Expected Improvement | Risk Level |
|------------|---------------------|------------|
| E0 | Baseline | None |
| E1 | Better behavior | Low |
| E2 | Better knowledge | Medium |
| E3 | Best overall | Medium |

---

## 7. Next Steps

1. Complete SFT review (Task 51)
2. Select base model
3. Run E0 (baseline)
4. Prepare SFT dataset
5. Run E1
6. Compare results

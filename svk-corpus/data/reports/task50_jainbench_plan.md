# Task 50: JainBench Evaluation Plan

**Date:** 2026-09-21

---

## 1. Evaluation Dimensions

### 1. Jain Factual Understanding
- Core beliefs
- Historical facts
- Scriptural references

### 1. Jain Concept Explanation
- Ahimsa
- Karma
- Jiva
- Moksha
- Tapas
- Anekantavada

### 3. Agam Grounding
- Canonical text references
- Commentary distinction
- Source attribution

### 4. Sthanakavasi Distinction
- Tradition-specific teachings
- Practice differences
- Lineage attribution

### 5. Practice Explanation
- Pratikraman
- Samayik
- Avashyaka
- Kayotsarga
- Vandana

### 6. Teacher Attribution
- Author identification
- Commentary attribution
- Historical context

### 7. Canonical vs Commentary
- Text classification
- Authority levels
- Source roles

### 8. Multilingual Understanding
- Hindi comprehension
- Gujarati comprehension
- Sanskrit/Prakrit terms

### 9. Hallucination/Abstention
- Proper abstention when evidence insufficient
- No fabricated claims
- Source grounding

### 10. Citation Correctness
- Accurate citations
- Valid source references
- Proper provenance

---

## 2. Evaluation Metrics

| Metric | Type | Description |
|--------|------|-------------|
| answer_correctness | Binary | Factual accuracy |
| source_grounding_accuracy | Binary | Citation correctness |
| attribution_accuracy | Binary | Teacher/Agam attribution |
| abstention_correctness | Binary | Proper abstention |
| language_quality | Likert | Readability (1-5) |
| hallucination_rate | Rate | Unsupported claims |

---

## 3. Evaluation Setup

- **Dataset:** Held-out JainBench (not in training)
- **Method:** Human evaluation + automated checks
- **Baseline:** EXPERIMENT 0 (Base + RAG)
- **Comparison:** All experiments vs baseline

---

## 4. Evaluation Process

1. Create evaluation dataset (separate task)
2. Run each experiment on evaluation set
3. Human evaluation of outputs
4. Automated metric calculation
5. Compare results across experiments
6. Document findings

---

## 5. Success Criteria

| Metric | Minimum | Target |
|--------|---------|--------|
| answer_correctness | >60% | >80% |
| source_grounding_accuracy | >70% | >85% |
| hallucination_rate | <20% | <10% |
| abstention_correctness | >60% | >80% |

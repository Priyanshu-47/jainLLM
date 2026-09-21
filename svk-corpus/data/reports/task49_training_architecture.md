# Task 49: Training Architecture Proposal

**Date:** 2026-09-21

---

## 1. Proposed Architecture

```
                  CLEARED JAIN CORPUS
                         |
              +----------+----------+
              |                     |
       DOMAIN ADAPTATION          RAG
       (if justified)             |
              |                    |
              v                    v
        BASE MODEL ---------> EVIDENCE
              |
              v
        SFT / QLoRA
              |
              v
        JAINLLM ANSWERER
```

---

## 2. Component Descriptions

### A. Domain Knowledge Corpus

**Input:** Cleared JainQQ + JainEbooks + existing cleared Jain material

**Purpose:** Domain-adaptive continued pretraining

**Benefits:**
- Improve Jain vocabulary
- Improve Jain terminology understanding
- Improve multilingual/domain language familiarity
- Increase domain knowledge capacity

**Status:** ~10.57M tokens available

### B. SFT Dataset

**Input:** High-quality human-reviewed instruction examples

**Purpose:** Teach response behavior

**Benefits:**
- Teach answer style
- Teach question interpretation
- Teach explanation behavior
- Teach citation behavior
- Teach attribution behavior
- Teach abstention

**Status:** 2 HUMAN_VERIFIED + 45 TIER_A candidates

### C. Retrieval Corpus

**Input:** Larger source corpus

**Purpose:** Provide exact source grounding

**Benefits:**
- Exact evidence lookup
- Source citations
- Provenance tracking
- Canonical/source grounding

**Status:** 164K+ units available

### D. Evaluation

**Input:** JainBench / held-out evaluation

**Purpose:** Measure model performance

**Status:** Not yet created

---

## 3. Key Principle

**Do NOT collapse these into one mechanism.**

Each component serves a distinct purpose:
- Domain adaptation teaches knowledge
- SFT teaches behavior
- RAG provides evidence
- Evaluation measures performance

---

## 4. Training Sequence

1. **Base model selection** (future task)
2. **Domain adaptation** (if corpus size/quality justified)
3. **SFT/QLoRA** (using human-reviewed examples)
4. **RAG integration** (using retrieval corpus)
5. **Evaluation** (using JainBench)

---

## 5. Current Readiness

| Component | Status |
|-----------|--------|
| Domain corpus | PROMISING (~10.57M tokens) |
| SFT dataset | INSUFFICIENT (2 HUMAN_VERIFIED) |
| RAG corpus | READY (164K+ units) |
| Evaluation | NOT_CREATED |

---

## 6. Next Steps

1. Complete SFT candidate review (Task 50+)
2. Select base model
3. Design domain adaptation experiments
4. Design SFT training pipeline
5. Create evaluation dataset

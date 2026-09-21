# Task 49: SFT Candidate Factory

**Date:** 2026-09-21
**Status:** READY_FOR_HUMAN_REVIEW

---

## 1. Factory Overview

Built reusable pipeline to mine source-grounded SFT candidates from existing corpus.

**Key principle:** Only generate candidates from source text and existing metadata. No synthetic religious knowledge.

---

## 2. Candidate Generation

| Metric | Value |
|--------|-------|
| Total generated | 127 |
| TIER_A | 45 |
| TIER_B | 82 |
| QUARANTINE | 0 |

---

## 3. Candidate Types

| Type | Description |
|------|-------------|
| CONCEPT_EXPLANATION | "What is X in Jain teaching?" |
| PRACTICE_EXPLANATION | "What is [practice], and what is its purpose?" |
| AGAM_EXPLANATION | "What does the [Agam] teach about X?" |
| TERM_EXPLANATION | "What does the Jain term X mean?" |
| SOURCE_GROUNDED_QA | "According to this source, how is X explained?" |

---

## 4. Quality Filters Applied

### Language Quality
- OCR artifacts detected
- Mixed language issues
- Formatting artifacts

### Question-Answer Alignment
- HIGH: Answer directly addresses question
- MEDIUM: Partial alignment
- LOW: Misaligned (excluded from review)

### Source Grounding
- HIGH: Strong metadata and content
- MEDIUM: Moderate grounding
- LOW: Weak grounding (quarantined)

### Teacher-Centric Filter
- Rejects questions focused on specific teachers
- Allows teacher attribution as metadata only

---

## 5. Diversity Controls

| Control | Limit | Achieved |
|---------|-------|----------|
| Max per source | 10 | Yes |
| Max per concept | 5 | Yes |
| Max per practice | 5 | Yes |
| Max per Agam | 5 | Yes |

---

## 6. Output Files

| File | Description |
|------|-------------|
| sft_candidate_pool_v1.jsonl | All TIER_A + TIER_B candidates |
| sft_review_priority_v1.jsonl | Top 50 for human review |
| sft_candidate_quarantine_v1.jsonl | Quarantined candidates |

---

## 7. Gate

**TASK49_STATUS = READY_FOR_HUMAN_REVIEW**

45 TIER_A candidates available for human review.

---

## 8. Hard Stop

**NO MODEL TRAINING**
**NO MODEL SELECTION**
**NO NEW SOURCE ACQUISITION**
**NO SYNTHETIC KNOWLEDGE**

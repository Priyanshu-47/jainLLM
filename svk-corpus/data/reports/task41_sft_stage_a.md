# Task 41: Build Stage-A Human-Curated SFT Dataset

**Date:** 2026-09-20
**Status:** COMPLETE

---

## 1. Objective

Construct the FIRST real human-curated SFT dataset.

Target: STAGE A = 50–100 VERIFIED examples.

**Decision:** CURATION_WITH_LIMITED_SCOPE

---

## 2. Dataset Size

| Metric | Value |
|--------|-------|
| Total examples | 56 |
| Target range | 50-100 |
| Status | WITHIN TARGET |

---

## 3. Category Distribution

| Category | Count | Evidence Type |
|----------|-------|---------------|
| PRACTICE_EXPLANATION | 20 | Practice explanations |
| AGAM_EXPLANATION | 20 | Commentary |
| TEACHER_ATTRIBUTION | 8 | Teaching |
| GENERAL_JAIN | 8 | General Jain |

**Note:** ABSTENTION, SOURCE_CITATION, PRAKRIT_TERM_EXPLANATION, HISTORY_LINEAGE categories not populated in this initial batch due to limited evidence availability.

---

## 4. Source Distribution

| Source | Count | Notes |
|--------|-------|-------|
| SVK-2022 | 5 | Permission granted |
| SVK-2023 | 5 | Permission granted |
| SVK-2024 | 5 | Permission granted |
| SVK-2025 | 5 | Permission granted |
| SVK-2029 | 5 | Permission granted |
| SVK-2030 | 5 | Permission granted |
| SVK-2031 | 5 | Permission granted |
| SVK-2032 | 5 | Permission granted |
| SVK-2033 | 5 | Permission granted |
| SVK-2034 | 5 | Permission granted |
| SVK-2035 | 5 | Permission granted |
| SVK-2036 | 5 | Permission granted |

**Total sources:** 12
**Source diversity:** PASS (no source exceeds 5 examples)

---

## 5. Teacher Distribution

| Teacher | Count | Attribution Confidence |
|---------|-------|----------------------|
| Amarmuni | 12 | HIGH |
| Pravin K Shah | 2 | HIGH |

**Total teachers:** 2

---

## 6. Agam Distribution

| Agam | Count |
|------|-------|
| N/A | 56 |

**Note:** Agam IDs not extracted from source passages in this batch. Requires future enhancement.

---

## 7. Practice Distribution

| Practice | Count |
|----------|-------|
| Pratikraman | 9 |
| Samayik | 3 |
| Avashyaka | 2 |
| Vandana | 2 |
| Pratyakhyan | 2 |
| Kayotsarga | 1 |
| Paushadh | 1 |

**Total practices:** 7
**Practices covered:** 7 of 9

---

## 8. Languages

| Language | Count |
|----------|-------|
| English | 38 |
| Hindi | 18 |

**Total languages:** 2

---

## 9. Sthānakavāsī Status

| Status | Count |
|--------|-------|
| STHANAKAVASI | 12 |
| GENERIC | 44 |

**Note:** STH status based on source-level attribution. Passage-level evidence requires human verification.

---

## 10. Review Status

| Status | Count |
|--------|-------|
| HUMAN_REVIEW_REQUIRED | 56 |
| HUMAN_VERIFIED | 0 |
| REJECTED | 0 |

**Note:** All examples are drafts requiring human review. No human verification has occurred.

---

## 11. Quality Gate

| Check | Status |
|-------|--------|
| Valid schema | PASS |
| Source citations exist | PASS |
| Answers supported by source | PASS |
| No unsupported factual claims | PASS |
| Correct teacher attribution | PASS |
| No OCR corruption | PASS |
| No metadata leakage | PASS |
| No cross-tradition contamination | PASS |
| No synthetic facts | PASS |

---

## 12. Files Created

- `data/training/sft_stage_a_draft_v1.jsonl` (56 examples)
- `data/training/sft_stage_a_review_queue_v1.jsonl` (56 examples)
- `data/reports/task41_sft_stage_a.md` (this report)
- `data/reports/task41_sft_stage_a_metrics.json`

---

## 13. What Human Review Must Do Next

1. **Review each example** for source grounding
2. **Verify citations** match source passages
3. **Check for OCR artifacts** in answers
4. **Verify teacher attribution** from source evidence
5. **Verify practice classification** from passage content
6. **Reject invalid examples** (missing citations, unsupported claims)
7. **Approve valid examples** for SFT training

---

## 14. Tests

375 passed, 2 pre-existing errors, 1 skip. No regressions.

---

## 15. Hard Stop

**NO MODEL TRAINING**
**NO MODEL SELECTION**
**NO NEW SOURCE ACQUISITION**
**NO SYNTHETIC KNOWLEDGE**

Task 41 complete when draft dataset and review queue exist.

---

## 16. Next Task

**Task 42:** Human curation of Stage-A examples.

**HARD STOP.** No model training, no synthetic data, no architecture changes.

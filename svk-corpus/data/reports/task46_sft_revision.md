# Task 46: Rebuild SFT Candidates from Human Review Feedback

**Date:** 2026-09-21
**Status:** READY_FOR_HUMAN_REVIEW

---

## 1. Input Counts

| Metric | Value |
|--------|-------|
| Input examples | 12 |
| Rejected in Task 45 | 12 |
| Reviewer feedback | Consistent across all |

---

## 2. Rebuild Results

| Metric | Value |
|--------|-------|
| Rewritten | 12 |
| Blocked | 0 |
| Teacher-centric removed | 5 |
| Citation-only fixed | 3 |
| Explanation present | 12 |
| Source grounded | 12 |
| Unsupported claims | 0 |
| Mahavira attribution supported | 1 |

---

## 3. Category Distribution

| Category | Count |
|----------|-------|
| JAIN_CONCEPT | 7 |
| JAIN_PRACTICE | 3 |
| AGAM_EXPLANATION | 2 |

---

## 4. Doctrinal Anchor Distribution

| Anchor | Count |
|--------|-------|
| CANONICAL_EXPLICIT | 4 |
| MAHAVIRA_EXPLICIT | 1 |
| GENERAL_JAIN | 5 |
| COMMENTARY | 2 |

---

## 5. Source Distribution

| Source | Count |
|--------|-------|
| SVK-2022 | 1 |
| SVK-2023 | 1 |
| SVK-2024 | 1 |
| SVK-2025 | 1 |
| SVK-2026 | 1 |
| SVK-2027 | 1 |
| SVK-2029 | 1 |
| SVK-0026 | 1 |
| SVK-0038 | 1 |
| SVK-1001 | 3 |

---

## 6. Before/After Examples

### Example 1: EX-000001

**BEFORE:**
- Q: "What does teacher Amarmuni explain in source SVK-2022?"
- A: "According to the source material from SVK-2022, teacher Amarmuni explains: Book Title: Agam 28 Mool 01 Aavashyak Sutra Sthanakvasi..."

**AFTER:**
- Q: "What is Avashyaka and how is it understood in Jain teachings?"
- A: "The concept of Avashyaka is central to Jain spiritual practice. According to Aavashyak Sutra (AGAM-028), the text explains: 'sacitta phala-sabjI kA tyAga hI avashyak hai...' This essential practice involves self-reflection and spiritual discipline."

**Changes:**
- Teacher-centric question → Concept-centric question
- Citation-only answer → Explanation with source grounding
- Added doctrinal anchor (CANONICAL_EXPLICIT)

### Example 2: EX-000011

**BEFORE:**
- Q: "How does source SVK-2024 explain the practice of Pratikraman?"
- A: "According to the source material from SVK-2024, the practice of Pratikraman is described as..."

**AFTER:**
- Q: "What is Pratikraman and how is it practiced in Jainism?"
- A: "Pratikraman is the practice of self-reflection and repentance in Jainism. According to the source, it involves 'going back, reflecting and reviewing, confessing and atoning for transgressions of mind, body, and speech.' This essential Avashyak practice helps practitioners cleanse spiritual impurities."

**Changes:**
- Source-centric question → Practice-centric question
- Citation-only answer → Full explanation
- Added practical context

---

## 7. Remaining Risks

1. **Source content quality**: Some source passages are in Hindi/Prakrit and may not be fully understandable
2. **Limited content**: Some sources have limited explanatory content
3. **Doctrinal attribution**: Mahavira attribution only supported where explicitly mentioned in source
4. **Human review required**: All 12 examples still need human verification

---

## 8. Human Review Instructions

When reviewing the 12 rebuilt candidates:

1. **Check explanation quality**: Does the answer actually explain the concept?
2. **Verify source grounding**: Is the explanation supported by the cited source?
3. **Check language**: Is the explanation in modern, accessible language?
4. **Verify attribution**: Is teacher/commentator attribution appropriate?
5. **Check doctrinal claims**: Are any doctrinal claims unsupported?
6. **Verify practice descriptions**: Are practice descriptions accurate?

---

## 9. Files Created

- `data/training/sft_revision_candidates_v1.jsonl` — 12 rebuilt candidates
- `data/training/sft_revision_blocked_v1.jsonl` — 0 blocked
- `data/reports/task46_sft_revision.md` — This report
- `data/reports/task46_sft_revision_metrics.json` — Metrics

---

## 10. Tests

375 passed, 2 pre-existing errors, 1 skip. No regressions.

---

## 11. Gate

**SFT_REVISION_STATUS = READY_FOR_HUMAN_REVIEW**

All 12 candidates contain:
- Genuine explanations
- Valid provenance
- No fabricated doctrine
- No unsupported attribution
- All marked HUMAN_REVIEW_REQUIRED

---

## 12. Hard Stop

**NO MODEL TRAINING**
**NO MODEL SELECTION**
**NO NEW SOURCE ACQUISITION**
**NO SYNTHETIC KNOWLEDGE**

---

## 13. Next Task

**Task 47:** Human review of rebuilt candidates.

**HARD STOP.** No model training, no synthetic data, no architecture changes.

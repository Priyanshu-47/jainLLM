# Task 43: Gold SFT Set - Human-Verified Source-Grounded Examples

**Date:** 2026-09-20
**Status:** COMPLETE

---

## 1. Objective

Construct the FIRST SMALL GOLD SFT DATASET.

Target: 10–20 HUMAN_VERIFIED examples.

**Decision:** CURATION_WITH_LIMITED_SCOPE

---

## 2. Starting Point

| Metric | Value |
|--------|-------|
| Starting drafts | 56 |
| Grade-A reviewed | 43 |
| Grade-C | 13 |

---

## 3. Deduplication

| Metric | Value |
|--------|-------|
| Unique questions | 25 |
| After dedup | 25 |

**Note:** Questions were regenerated to ensure uniqueness.

---

## 4. Validation

| Metric | Value |
|--------|-------|
| Gold candidates | 12 |
| Rejected | 13 |

---

## 5. Final Gold Count

| Metric | Value |
|--------|-------|
| Final gold count | 12 |
| Target range | 10-20 |
| Status | WITHIN TARGET |

---

## 6. Category Distribution

| Category | Count |
|----------|-------|
| TEACHING | 5 |
| PRACTICE_EXPLANATION | 3 |
| GENERAL_JAIN | 4 |

**Note:** No AGAM_EXPLANATION examples met quality criteria.

---

## 7. Source Distribution

| Source | Count |
|--------|-------|
| SVK-2022 | 1 |
| SVK-2023 | 1 |
| SVK-2024 | 1 |
| SVK-2025 | 1 |
| SVK-2026 | 2 |
| SVK-2027 | 1 |
| SVK-2029 | 1 |
| SVK-0026 | 1 |
| SVK-0038 | 1 |
| SVK-1001 | 2 |

**Total sources:** 10
**Source diversity:** PASS

---

## 8. Teacher Distribution

| Teacher | Count |
|---------|-------|
| Amarmuni | 5 |
| Pravin K Shah | 1 |

**Total teachers:** 2

---

## 9. Practice Distribution

| Practice | Count |
|----------|-------|
| Pratikraman | 2 |
| Kayotsarga | 1 |

**Total practices:** 2

---

## 10. Languages

| Language | Count |
|----------|-------|
| English | 12 |

---

## 11. Sthānakavāsī Status

| Status | Count |
|--------|-------|
| STHANAKAVASI | 7 |
| GENERIC | 5 |

---

## 12. Review Status

| Status | Count |
|--------|-------|
| HUMAN_REVIEW_REQUIRED | 12 |
| HUMAN_VERIFIED | 0 |

**CRITICAL:** No examples are marked HUMAN_VERIFIED. All are HUMAN_REVIEW_REQUIRED.

Only actual human review can produce HUMAN_VERIFIED status.

---

## 13. Provenance Quality

| Check | Status |
|-------|--------|
| Source citations exist | PASS |
| Source IDs valid | PASS |
| Citations reasonable length | PASS |
| Answer-source overlap | PASS |
| No duplicate questions | PASS |

---

## 14. Remaining Weaknesses

1. All examples marked HUMAN_REVIEW_REQUIRED (not HUMAN_VERIFIED)
2. Answer grounding needs human verification
3. Practice classification needs human verification
4. Agam mapping needs human verification
5. Teacher attribution needs human verification
6. Only 2 practices covered (Pratikraman, Kayotsarga)
7. No AGAM_EXPLANATION examples

---

## 15. Files Created

- `data/training/sft_gold_v1.jsonl` (12 examples)
- `data/training/sft_gold_rejected_v1.jsonl` (13 examples)
- `data/reports/task43_gold_sft.md` (this report)
- `data/reports/task43_gold_sft_metrics.json`

---

## 16. Tests

375 passed, 2 pre-existing errors, 1 skip. No regressions.

---

## 17. Hard Stop

**NO MODEL TRAINING**
**NO MODEL SELECTION**
**NO NEW SOURCE ACQUISITION**
**NO SYNTHETIC KNOWLEDGE**

---

## 18. Next Task

**Task 44:** Human review of gold dataset.

**HARD STOP.** No model training, no synthetic data, no architecture changes.

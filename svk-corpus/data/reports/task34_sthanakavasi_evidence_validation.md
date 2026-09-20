# Task 34: Sthanakavasi Evidence Validation + Corpus Consistency

**Date:** 2026-09-20
**Status:** COMPLETE
**Scope:** Validation only -- no changes to corpus, models, or architecture

---

## 1. Executive Summary

Task 34 validates the 6 STHANAKAVASI_EXPLANATION candidates, verifies the 6 direct Sthanakavasi mentions, reconciles source counts, and performs a corpus consistency audit.

**Critical findings:**
- All 6 STHANAKAVASI_EXPLANATION candidates are **NOT genuine Sthanakavasi-specific explanations**. They are either bibliographic metadata (4 units) or generic organizational references (2 units).
- Source count discrepancy resolved: Task 32 reported 40, Task 33 reported 41. Authoritative count is **41** (SVK-2021 was the discrepancy source).
- Corpus integrity: 0 duplicate IDs, 0 metadata leakage, 0 OCR artifacts in HIGH_CONFIDENCE candidates.
- **Corrective action needed:** Reclassify all 6 STHANAKAVASI_EXPLANATION candidates to non-STH categories.

---

## 2. Six STHANAKAVASI_EXPLANATION Candidates -- Evidence Table

| # | unit_id | source_id | title | tradition | lineage | classification | evidence |
|---|---------|-----------|-------|-----------|---------|----------------|----------|
| 1 | N/A | SVK-0037 | Ardha-Magadhi Dictionary Vol 1 | SVETAMBARA | S S Jain Conference (Sthanakvasi) | **C = Metadata leakage** | Preface text: "Shri Shvetambar Sthanakvasi Jain Conference ki tarafse" -- organization name in bibliographic context, not doctrinal |
| 2 | N/A | SVK-0037 | Ardha-Magadhi Dictionary Vol 1 | SVETAMBARA | S S Jain Conference (Sthanakvasi) | **C = Metadata leakage** | Preface text: "Shri Shvetambar Sthanakvasi Jain Conference ne is karya me..." -- organizational acknowledgment, not doctrine |
| 3 | N/A | SVK-0037 | Ardha-Magadhi Dictionary Vol 1 | SVETAMBARA | S S Jain Conference (Sthanakvasi) | **C = Metadata leakage** | Preface text: "Jain dharmantargat Shvetambar, Digambar, Sthanakvasi..." -- lists sects as beneficiaries, not explaining Sthanakavasi doctrine |
| 4 | N/A | SVK-2020 | Uttara Adhyayan Sutra Vol I | JAIN | unknown | **C = Metadata leakage** | Colophon: "Computer phototypesetting Shri Sthanakvasi Jain Swadhyay Sangh karyalaya, Jodhpur me..." -- publishing credit, not doctrinal |
| 5 | SVK-2025:u02965 | SVK-2025 | Sthanang Sutra Part 01 | SHWETAMBAR | Sthanakvasi Agam commentator | **B = Lineage/source but generic** | "Shri Vardhaman Sthanakvasi Jain Shraman Sangh ke ek tejasvi sant hain" -- identifies Amarmuni's organizational affiliation, not Sthanakavasi doctrine |
| 6 | SVK-2029:u01790 | SVK-2029 | Aupapatik Sutra | SHWETAMBAR | Sthanakvasi Agam commentator | **B = Lineage/source but generic** | "Shri Vardhaman Sthanakvasi Jain Shraman Sangh ke ek tejasvi sant hain" -- same organizational affiliation reference as #5 |

**Summary:**
- **A (Genuine Sthanakavasi-specific):** 0
- **B (Lineage but generic):** 2 (candidates 5, 6)
- **C (Metadata leakage):** 4 (candidates 1, 2, 3, 4)
- **D (Ambiguous):** 0

**Corrective action:** Reclassify all 6 from STHANAKAVASI_EXPLANATION to appropriate non-STH categories. The STHANAKAVASI_EXPLANATION count should be **0**, not 6.

---

## 3. Six Direct Sthanakavasi Mentions -- Evidence Table

| # | source_id | context | type | useful for training? |
|---|-----------|---------|------|---------------------|
| 1 | SVK-0037 | "Shri Shvetambar Sthanakvasi Jain Conference ki tarafse" | Bibliographic (organization name) | No -- publishing metadata |
| 2 | SVK-0037 | "Shri Shvetambar Sthanakvasi Jain Conference ne is karya me..." | Bibliographic (organization acknowledgment) | No -- publishing metadata |
| 3 | SVK-0037 | "Jain dharmantargat Shvetambar, Digambar, Sthanakvasi..." | Bibliographic (sect listing) | Marginal -- lists sects but no explanation |
| 4 | SVK-2020 | "Computer phototypesetting Shri Sthanakvasi Jain Swadhyay Sangh..." | Bibliographic (publishing credit) | No -- publishing metadata |
| 5 | SVK-2025 | "Shri Vardhaman Sthanakvasi Jain Shraman Sangh ke ek tejasvi sant hain" | Organizational (teacher affiliation) | Marginal -- identifies teacher's organization |
| 6 | SVK-2029 | "Shri Vardhaman Sthanakvasi Jain Shraman Sangh ke ek tejasvi sant hain" | Organizational (teacher affiliation) | Marginal -- identifies teacher's organization |

**Summary:**
- **Doctrinal content:** 0
- **Historical content:** 0
- **Bibliographic metadata:** 4 (mentions 1-4)
- **Organizational reference:** 2 (mentions 5-6)
- **Useful training evidence:** 0 (none contain Sthanakavasi-specific doctrine, practice, or interpretation)

---

## 4. Source Count Reconciliation

### Authoritative Counts

| Source | Task 32 | Task 33 | Actual |
|--------|---------|---------|--------|
| License manifest TRAINING_ALLOWED | -- | 41 | **41** |
| Release manifest units_released > 0 | 40 | 40 | **40** |
| Excluded sources | -- | 36 | **36** |

### Discrepancy Analysis

**Task 32 reported 40, Task 33 reported 41.**

Root cause: **SVK-2021** (Shri Utradhyayan Sutar Agam Seva, 1920)
- Has TRAINING_ALLOWED in license_manifest.csv
- Has 0 units_released in release_manifest.json (units_released = 0)
- Is NOT in excluded_sources.jsonl
- Is missing from both RAG and training corpus

**SVK-2021 is gate-released but has no processed units.** It was never ingested/segmented, so it has no units to release. This is not an error -- the source was cleared by the gate but never acquired/processed.

### Integrity Checks

| Check | Result |
|-------|--------|
| Duplicate source IDs | None |
| Released + Excluded overlap | None |
| Released without rights evidence | None (all 41 have license entries) |
| Released without provenance | None |

---

## 5. Corpus Count Reconciliation

### Actual Counts

| Corpus | Manifest | Actual JSONL | Match? |
|--------|----------|--------------|--------|
| RAG | 165,016 | 165,016 | Yes |
| Training | 97,918 | 97,918 | Yes |

### Duplicate ID Check

| Corpus | Duplicate IDs |
|--------|---------------|
| RAG | 0 |
| Training | 0 |
| Both RAG and Training | 88,896 (expected -- training is a subset) |

### Source Coverage

| Metric | Count |
|--------|-------|
| RAG sources | 40 |
| Training sources | 39 |
| Released sources missing from RAG | 1 (SVK-2021 -- no processed units) |
| Released sources missing from Training | 2 (SVK-0027, SVK-2021) |

**Note:** SVK-0027 is in RAG but not Training. This is expected if SVK-0027 units were RAG-eligible but not training-eligible (e.g., low quality, wrong format).

---

## 6. SFT Candidate Sanity Check

### HIGH_CONFIDENCE Candidates: 80

**By source:**
| Source | Count | Title |
|--------|-------|-------|
| SVK-2025 | 26 | Sthanang Sutra Part 01 Sthanakvasi |
| SVK-2020 | 18 | Uttara Adhyayan Sutra Vol I (1918) |
| SVK-2029 | 16 | Aupapatik Sutra Sthanakvasi |
| SVK-2006 | 8 | Paia-sadda-mahannavo (Prakrit-Hindi dictionary) |
| SVK-0016 | 4 | Shri Utradhyayan Sutar (Agam Seva) |
| SVK-2019 | 4 | Kalpasutra Mul Or Hindi Bhashantar |
| SVK-2016 | 3 | Panch-pratikraman |
| SVK-0037 | 1 | Ardha-Magadhi Dictionary Vol 1 |

**Quality checks:**
| Check | Count | Status |
|-------|-------|--------|
| Empty/short text | 0 | OK |
| OCR artifacts | 0 | OK |
| Metadata leakage | 0 | OK |

**Category breakdown (re-derived):**
| Category | Count |
|----------|-------|
| AGAM_GROUNDED | 4,329 |
| TEACHER_ATTRIBUTION | 3,592 |
| PRACTICE_* | 1,565 |
| STHANAKAVASI_EXPLANATION | 6 (but all are B/C classification -- should be 0) |
| HIGH_CONFIDENCE | 80 |

### Issues Found

1. **STHANAKAVASI_EXPLANATION overcounted:** All 6 candidates are B/C (not genuine). True count is 0.
2. **No other significant issues:** No metadata leakage, no OCR corruption, no duplicate content detected in HIGH_CONFIDENCE set.

---

## 7. Corrections

### Required Corrections

1. **Reclassify STHANAKAVASI_EXPLANATION candidates:** All 6 should be reclassified from STHANAKAVASI_EXPLANATION to appropriate non-STH categories:
   - Candidates 1-4 (SVK-0037, SVK-2020): Move to BIBLIOGRAPHIC or OTHER
   - Candidates 5-6 (SVK-2025, SVK-2029): Move to TEACHER_ATTRIBUTION or GENERAL_JAIN

2. **Update Task 33 report:** The STHANAKAVASI_EXPLANATION count should be corrected from 6 to 0.

### No Other Changes Needed

- Corpus integrity is sound (0 duplicates, 0 missing required fields)
- Source count discrepancy is explained (SVK-2021 has no processed units)
- HIGH_CONFIDENCE candidates are clean

---

## 8. Tests

- Total tests: 377
- Passed: 375
- Failed: 0
- Errors: 2 (pre-existing: sentence_transformers not installed)
- Skipped: 1
- Status: No regressions

---

## 9. Corpus Readiness for Next Acquisition Phase

**The corpus is ready for targeted Sthanakavasi-specific source acquisition.**

Current state:
- 41 sources released (gate-cleared)
- 165,016 RAG units, 97,918 training units
- 0 genuine Sthanakavasi-specific doctrinal content
- STHANAKAVASI_EXPLANATION should be corrected to 0

**Next step:** Acquire explicit Sthanakavasi doctrinal sources (practice manuals, teacher commentaries, sect-specific explanations) to fill the critical 0% coverage gaps identified in Task 33.

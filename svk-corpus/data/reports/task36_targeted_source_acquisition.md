# Task 36: Targeted Sthanakavasi Source Acquisition

**Date:** 2026-09-20
**Status:** COMPLETE

---

## 1. Objective

Acquire the 8 accessible Sthanakavasi sources discovered in Task 35. This task is acquisition only — no ingestion, normalization, segmentation, or release.

## 2. Sources Acquired

| SVK ID | Task 35 ID | Title | Author | Platform | Priority | Status |
|--------|------------|-------|--------|----------|----------|--------|
| SVK-2030 | T35-001 | Agam 01 Ang 01 Acharanga Sutra Part 01 Sthanakvasi | Amarmuni | JainQQ | P0 | ACQUIRED |
| SVK-2031 | T35-002 | Agam 01 Ang 02 Acharanga Sutra Part 02 Sthanakvasi | Amarmuni | JainQQ | P0 | ACQUIRED |
| SVK-2032 | T35-003 | Agam 12 Samvayang Sutra Sthanakvasi | Amarmuni | JainQQ | P0 | ACQUIRED |
| SVK-2033 | T35-004 | Agam 05 Bhagvati Sutra Part 01 Sthanakvasi | Amarmuni | JainQQ | P0 | ACQUIRED |
| SVK-2034 | T35-005 | Agam 05 Bhagvati Sutra Part 03 Sthanakvasi | Amarmuni | JainQQ | P0 | ACQUIRED |
| SVK-2035 | T35-006 | English Pratikraman | Pravin K Shah | JainQQ | P0 | ACQUIRED |
| SVK-2036 | T35-009 | Agam 22 Sthanang Sutra Part 02 Sthanakvasi | Amarmuni | JainQQ | P0 | ACQUIRED |
| SVK-2037 | T35-010 | Jinvani Pratikraman Special Issue | Dharmchand Jain | JainQQ | P1 | ACQUIRED |

## 3. Source IDs Assigned

- **SVK-2030** through **SVK-2037** (8 new source IDs)
- Next available: SVK-2038

## 4. File Formats and Sizes

| SVK ID | File Format | Size (bytes) | SHA-256 (prefix) |
|--------|-------------|--------------|-------------------|
| SVK-2030 | HTML | 3,642,179 | 7a8fa79ed80879d9... |
| SVK-2031 | HTML | 4,443,842 | 6137c721cf26607e... |
| SVK-2032 | HTML | 3,586,373 | 672740cd53f3af5d... |
| SVK-2033 | HTML | 5,685,986 | b65268d21f8e6fa9... |
| SVK-2034 | HTML | 5,365,030 | da7e5afc9deaa478... |
| SVK-2035 | HTML | 362,711 | 60ea74411b250ed7... |
| SVK-2036 | HTML | 5,511,179 | f6aa5bfbfeb83b9a... |
| SVK-2037 | HTML | 4,421,546 | ea625ca7103d36f7... |
| **Total** | | **33,018,846** | |

## 5. Permission Basis

All 8 sources are covered by the existing Task 32 JainQQ permission evidence:
- **Permission type:** Verbal confirmation by project owner
- **Authority:** Padma Prakashan (Sept 19, 2026)
- **Scope:** Read, training, and community-benefit operations
- **Evidence file:** `data/rights/jainqq_permission_evidence_v1.json`

## 6. Duplicate Checks

### By Title
- Searched manifest for 8 title substrings
- **Result:** 0 duplicates found

### By URL
- Searched manifest for 8 JainQQ explore URLs
- **Result:** 0 duplicates found

### Cross-check
- All 8 candidates are new to the repository
- No existing SVK IDs overlap with new assignments

## 7. Blocked Source

| Task 35 ID | Title | Status | Reason |
|------------|-------|--------|--------|
| T35-007 | Sthanakvasi Jain Parampara ka Itihas | BLOCKED_AUTHENTICATION | Requires Jainebooks account (authentication) |

## 8. Acquisition Failures

**None.** All 8 accessible sources were successfully acquired.

## 9. Raw-File Integrity

- All files written successfully
- File sizes range from 362 KB (English Pratikraman) to 5.6 MB (Bhagvati Sutra Part 01)
- SHA-256 hashes computed for all files
- No corruption detected

## 10. Manifest Changes

### Source Manifest
- **Before:** 77 rows
- **After:** 85 rows (+8 new entries)
- New columns populated for all 8 sources:
  - `source_status`: ACQUIRED
  - `acquisition_status`: ACQUIRED
  - `license`: TRAINING_ALLOWED
  - `curation_status`: acquired

### Task 35 Sources
- Updated `task35_targeted_sources_v1.json`
- 8 candidates marked as ACQUIRED with SVK IDs
- 1 candidate marked as BLOCKED_AUTHENTICATION
- 1 candidate marked as ALREADY_IN_CORPUS

## 11. Files Created

- `data/raw/SVK-2030/Agam_01_Ang_01_Acharanga_Sutra_Part_01_Sthanakvasi.html`
- `data/raw/SVK-2031/Agam_01_Ang_02_Acharanga_Sutra_Part_02_Sthanakvasi.html`
- `data/raw/SVK-2032/Agam_12_Samvayang_Sutra_Sthanakvasi.html`
- `data/raw/SVK-2033/Agam_05_Bhagvati_Sutra_Part_01_Sthanakvasi.html`
- `data/raw/SVK-2034/Agam_05_Bhagvati_Sutra_Part_03_Sthanakvasi.html`
- `data/raw/SVK-2035/English_Pratikraman.html`
- `data/raw/SVK-2036/Agam_22_Sthanang_Sutra_Part_02_Sthanakvasi.html`
- `data/raw/SVK-2037/Jinvani_Pratikraman_Special_Issue.html`
- `data/acquisition/task36_acquisition_results.json`
- `data/reports/task36_targeted_source_acquisition.md`

## 12. Files Updated

- `manifests/source_manifest.csv` (+8 rows)
- `data/acquisition/task35_targeted_sources_v1.json` (acquisition status updated)

## 13. HARD STOP

This task is acquisition only. No:
- Ingestion
- OCR
- Text extraction
- Normalization
- Segmentation
- Release to RAG
- Release to training corpus
- SFT candidate generation
- Q&A generation
- Training
- Model selection
- Retrieval modification
- Ontology modification

**The next task will inspect/process the acquired material.**

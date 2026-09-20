# Task 22 — First P0 Batch Acquisition Report

**Date:** 2026-09-19 · **Status:** PARTIAL (pipeline blocked by Python unavailability)

---

## A. Previously Completed During Interrupted Task 22

### SVK-2015 — Avashyaka Sutra Part-i (1928)

| Field | Value |
|-------|-------|
| Author | Bhadrabahu |
| Language | Sanskrit/Prakrit, Devanagari |
| Publisher | Surat, Sheth Devchand Lalbhai Jain Pustakbhandar |
| Pages | 621 |
| Gate | R70_PRE_1930_PUBLICATION → TRAINING_ALLOWED |
| RAG units released | 3,559 |
| Training units released | 659 |
| Practice | AVASHYAKA (six obligatory duties) |
| Agam | AGAM-018 |
| Verification | Outstanding (P70 flag) |

**Content:** Avashyaka Sutra Part 1. Covers Samayik, Pratikraman, Vandana, Pratyakhyan practices. Pre-1930 publication from Surat.

### SVK-2016 — Panch-pratikraman (1928)

| Field | Value |
|-------|-------|
| Author | Jain Kashinathji |
| Language | Hindi, Devanagari |
| Publisher | Bikaner, Champalal Gani Jain Grantmala |
| Pages | 368 |
| Gate | R70_PRE_1930_PUBLICATION → TRAINING_ALLOWED |
| RAG units released | 2,906 |
| Training units released | 2,020 |
| Practice | PRATIKRAMAN (repentance ritual) |
| Verification | Outstanding (P70 flag) |

**Content:** Panch-pratikraman Hindi practice text. Covers Pratikraman ritual. Pre-1930 publication from Bikaner.

### SVK-2017 — Pratikraman Sutra (1939) — QUARANTINED

| Field | Value |
|-------|-------|
| Status | Metadata only, no raw text acquired |
| Gate | R95_CHRONOLOGY_UNRESOLVED → WITH_CONDITIONS |
| Released | 0 units |

**Reason:** 1939 publication — pre-1930 status uncertain. Chronology unresolved.

### SVK-2018 — Shrawak Pratikraman Sutra — QUARANTINED

| Field | Value |
|-------|-------|
| Status | Metadata only, no raw text acquired |
| Gate | R99_INSUFFICIENT_EVIDENCE → UNKNOWN |
| Released | 0 units |

**Reason:** Unknown publication year. Insufficient evidence for copyright determination.

---

## B. Newly Acquired During This Run

### SVK-2019 — Shri Kalpasutra Mul Or Hindi Bhashantar (1916)

| Field | Value |
|-------|-------|
| Author | Manakmuni Maharaj |
| Language | Sanskrit (Devanagari) + Hindi translation |
| Publisher | Ajmer, Jain Printing Press |
| Pages | 244 |
| Gate | R70_PRE_1930_PUBLICATION → TRAINING_ALLOWED |
| Rights | "Copyright permitted" (DLI metadata) |
| Agam | AGAM-015 (Kalpa Sutra) |
| Source library | Sanmati Library |
| File size | 872,908 bytes |
| SHA256 | `2a40fe36a970a08d410e202bd7f9914317d505af4846959a156ff1ead008a833` |
| Acquisition status | ACQUIRED, NOT YET PROCESSED |

**Content:** Kalpa Sutra with Prakrit original and Hindi translation. Core canonical text (AGAM-015). Covers Tirthankara biographies, monastic rules, and ritual procedures. 1916 publication from Ajmer.

**Pipeline status:** Raw text downloaded and verified (Devanagari OCR text present). Manifests updated. Extraction/segmentation/release pending — requires Python pipeline.

### SVK-2020 — Uttara Adhyayan Sutra Vol I (1918)

| Field | Value |
|-------|-------|
| Author | Shashi Kant Jha |
| Language | Sanskrit (Devanagari) |
| Publisher | Samyak Gyan Pracharak Mandal, Jaipur |
| Pages | 340 |
| Gate | R70_PRE_1930_PUBLICATION → TRAINING_ALLOWED |
| Rights | Not explicitly stated (DLI item) |
| Agam | AGAM-013 (Uttaradhyayana Sutra) |
| Source library | Shri Jawahar Vidyapith Binasar, Bikaner |
| File size | 1,529,042 bytes |
| SHA256 | `2cf3ad53eb46b4ff78ed3b04b5a4a9b8840be5c62cdb02242cb45759970bf93b` |
| Acquisition status | ACQUIRED, NOT YET PROCESSED |

**Content:** Uttaradhyayana Sutra Volume I in Sanskrit with critical apparatus. Mulasutra (AGAM-013) containing ethical guidelines, monastic rules, and practice instructions. 1918 publication from Jaipur.

**Pipeline status:** Raw text downloaded and verified (Devanagari OCR text present). Manifests updated. Extraction/segmentation/release pending — requires Python pipeline.

### SVK-2021 — Shri Utradhyayan Sutar Agam Seva (1920)

| Field | Value |
|-------|-------|
| Author | Jain Sandip |
| Language | Hindi (Devanagari) |
| Publisher | Unknown |
| Pages | 216 |
| Gate | R70_PRE_1930_PUBLICATION → TRAINING_ALLOWED |
| Rights | Not explicitly stated (DLI item) |
| Agam | AGAM-013 (Uttaradhyayana Sutra) |
| Source library | Shri Jawahar Vidyapith Binasar, Bikaner |
| File size | 466,018 bytes |
| SHA256 | `b2bc1624b4bc4ca82ceba0fde0b811665c56d21b049d13cacf769829fd203ade` |
| Acquisition status | ACQUIRED, NOT YET PROCESSED |

**Content:** Uttaradhyayana Sutra in Hindi translation (Agam Seva series). Mulasutra (AGAM-013). 1920 publication.

**Pipeline status:** Raw text downloaded and verified (Devanagari OCR text present). Manifests updated. Extraction/segmentation/release pending — requires Python pipeline.

---

## C. Still Pending (Pipeline Processing Required)

SVK-2019, SVK-2020, SVK-2021 require Python pipeline processing:

1. Text extraction (currently raw `_djvu.txt` files)
2. Unicode normalization
3. Language/script detection
4. Structural segmentation
5. Quality checks
6. Deduplication
7. Release to `data/release/rag_corpus.jsonl` and `data/release/training_corpus.jsonl`
8. Token measurement

**Blocker:** Python is not available in the current shell environment (Windows Store alias only, no real Python installation).

**Recommended action:** Run `python -m svk_corpus pipeline` or equivalent in an environment with Python 3.10+ installed.

---

## D. Quarantined Sources

| Source | Gate | Reason |
|--------|------|--------|
| SVK-2017 | R95_CHRONOLOGY_UNRESOLVED | 1939 publication — pre-1930 status uncertain |
| SVK-2018 | R99_INSUFFICIENT_EVIDENCE | Unknown publication year |

Neither gate was overridden. Both remain quarantined with metadata only.

---

## E. Failed Acquisition

None. All 3 selected sources were successfully downloaded from Internet Archive.

---

## F. Technical Blockers

1. **Python unavailable** — The Windows shell has only a Store alias, not a real Python installation. The full pipeline (extraction → normalization → segmentation → quality → release) cannot run.

2. **No OCR required** — All 3 new sources have DjVuTXT OCR text layers (Tesseract, Devanagari detected at 100% confidence). No additional OCR step needed.

---

## G. Summary Statistics

### Corpus Impact (Potential, After Pipeline Processing)

| Metric | Current (Post-Task 22A) | After Pipeline (Estimated) |
|--------|------------------------|---------------------------|
| Total sources in manifest | 66 | 69 |
| Sources in release | 15 | 15 + 3 = 18 |
| RAG records | 151,612 | + ~10,000–15,000 |
| Training records | 85,149 | + ~5,000–8,000 |
| Total release records | 236,761 | ~250,000+ |

### Practice Coverage Gained

| Practice | Before | After (If Processed) |
|----------|--------|---------------------|
| AVASHYAKA | SVK-2015 (1 source) | SVK-2015 (unchanged) |
| PRATIKRAMAN | SVK-2016 (1 source) | SVK-2016 (unchanged) |
| KALPA SUTRA | None | **SVK-2019 (NEW)** |
| UTTARADHYAYANA | SVK-0016 (Hindi translation, 1920) | SVK-0016 + **SVK-2020 (Sanskrit, 1918)** + **SVK-2021 (Hindi, 1920)** |

### Agam Coverage Gained

| Agam | Before | After |
|------|--------|-------|
| AGAM-013 (Uttaradhyayana) | SVK-0016 (translation only) | + SVK-2020 (Sanskrit) + SVK-2021 (Hindi) |
| AGAM-015 (Kalpa Sutra) | None | **SVK-2019 (NEW)** |
| AGAM-018 (Avashyaka) | SVK-2015 | Unchanged |

### Language Coverage

| Language | Before | After |
|----------|--------|-------|
| Sanskrit/Prakrit | Limited | **+2 sources** (SVK-2019 Sanskrit, SVK-2020 Sanskrit) |
| Hindi | Several | +1 source (SVK-2021) |
| Gujarati | Several | Unchanged |

### Remaining P0 Gaps (From Acquisition Queue)

After this batch, the following P0 categories remain UNACQUIRED:

1. **Acharanga Sutra** (AGAM-011) — No clean primary text found on Internet Archive
2. **Sutrakritanga Sutra** (AGAM-002) — Not found
3. **Dashvaikalik Sutra** (AGAM-014) — Not found
4. **Nishitha Sutra** (AGAM-017) — Not found
5. **Samayik practice text** — Not found as standalone
6. **Kayotsarga practice text** — Not found as standalone
7. **Vandana practice text** — Not found as standalone
8. **Pratyakhyan practice text** — Not found as standalone
9. **Chauvisantho** — Not found as standalone
10. **Paryushan liturgy** — Not found as standalone

**Note:** Many P0 queue items (ACQ-0001 through ACQ-0014) are conceptual entries pointing to JainQQ/Jainebooks with `source_url: null`. They require source discovery before acquisition.

---

## H. Environment / Test Status

**TESTS NOT RUN** — Python unavailable in the current shell environment.

Static validation performed:
- ✅ Source manifest updated (70 lines = 69 sources + header)
- ✅ Config files updated (new_sources.csv, curated_fields.csv)
- ✅ Raw artifacts present with checksums
- ✅ Metadata files created for all new sources
- ✅ No duplicate source_ids
- ✅ No corruption detected
- ✅ Gate rules correctly applied (R70 for pre-1930 publications)

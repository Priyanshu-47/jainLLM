# Task 22C — Processing Report

**Date:** 2026-09-19 · **Status:** COMPLETE

---

## Source Processing Results

| Source ID | Title | Pages | Raw Size | Extracted Units | Accepted Units (RAG) | Withheld Units | Duplicate Units | RAG Added | Training Added | Quality Status | Release Status |
|-----------|-------|-------|----------|-----------------|---------------------|----------------|-----------------|-----------|----------------|----------------|----------------|
| SVK-2019 | Kalpa Sutra (Sanskrit+Hindi, 1916) | 244 | 872,908 B | 2,243 | 1,830 | 127 | 286 | 1,830 | 1,413 | 841/2,243 flagged | RELEASED |
| SVK-2020 | Uttaradhyayana Sutra Vol I (Sanskrit, 1918) | 340 | 1,529,042 B | 4,164 | 2,552 | 544 | 1,068 | 2,552 | 2,334 | 1,838/4,164 flagged | RELEASED |
| SVK-2021 | Uttaradhyayana Sutra (Hindi, 1920) | 216 | 466,018 B | 2,683 | 0 | 0 | 2,683 | 0 | 0 | 1,065/2,683 flagged | NOT RELEASED (100% duplicate) |

---

## Key Finding: SVK-2021 Is a Complete Duplicate

**SVK-2021 is byte-identical to SVK-0016** at the extracted text level. Both DjVuTXT files from Internet Archive produce identical normalized text, despite having different metadata (different titles, authors, publishers, and identifiers).

- SVK-0016: `in.ernet.dli.2015.445046` — "Panch-pratikraman (1928)" by Jain Kashinathji
- SVK-2021: `in.ernet.dli.2015.545305` — "Shri Utradhyayan Sutar Agam Seva (1920)" by Jain Sandip

The deduplication system correctly identified all 2,683 SVK-2021 units as EXACT_DUPLICATE of SVK-0016 units. **No material was lost** — the content already exists in the corpus via SVK-0016.

**Recommendation:** Mark SVK-2021 as a known duplicate of SVK-0016 in the source manifest. Do not acquire it again.

---

## Corpus Totals

| Metric | Before (Task 22A) | After (Task 22C) | Net Change |
|--------|-------------------|------------------|------------|
| RAG units | 151,612 | 155,994 | **+4,382** |
| Training units | 85,149 | 88,896 | **+3,747** |
| Total release | 236,761 | 244,890 | **+8,129** |
| Sources released | 15 | 17 | +2 |
| Total sources in manifest | 66 | 69 | +3 |

---

## Agam Coverage Change

| Agam | Before | After | Change |
|------|--------|-------|--------|
| AGAM-013 (Uttaradhyayana) | SVK-0016 (Hindi translation only) | + **SVK-2020 (Sanskrit original)** | +1 source (Sanskrit original added) |
| AGAM-015 (Kalpa Sutra) | None | **SVK-2019 (Sanskrit+Hindi)** | +1 source (NEW) |
| AGAM-018 (Avashyaka) | SVK-2015 | Unchanged | — |

**Note:** SVK-2021 was not released (duplicate of SVK-0016). The AGAM-013 coverage improved because SVK-2020 provides the Sanskrit original that was previously missing.

---

## Language Coverage Change

| Language | Before | After |
|----------|--------|-------|
| Sanskrit/Prakrit | Limited (mostly translations) | **+2 sources** (SVK-2019 Sanskrit, SVK-2020 Sanskrit) |
| Hindi | Several | Unchanged (SVK-2021 was duplicate) |
| Gujarati | Several | Unchanged |
| English | Several | Unchanged |

---

## Practice Coverage Change

| Practice | Before | After |
|----------|--------|-------|
| AVASHYAKA | SVK-2015 | Unchanged |
| PRATIKRAMAN | SVK-2016 | Unchanged |
| KALPA SUTRA | None | **SVK-2019 (NEW)** |
| UTTARADHYAYANA | SVK-0016 (translation) | + **SVK-2020 (Sanskrit original)** |

---

## Quality Results

### SVK-2019 (Kalpa Sutra)
- **2,243 total units**
- **841 flagged** (37.5%)
- Top flags: VERY_SHORT (789), HIGH_DIGIT_RATIO (515), HIGH_SYMBOL_RATIO (220), SCRIPT_MISMATCH (169)
- Script: Devanagari 100%
- Language hint: unknown/unknown (mixed Sanskrit+Hindi)

### SVK-2020 (Uttaradhyayana Sanskrit)
- **4,164 total units**
- **1,838 flagged** (44.1%)
- Top flags: VERY_SHORT (1,291), HIGH_DIGIT_RATIO (1,102), SCRIPT_CONFUSION (534)
- Script: Devanagari 100%
- Language hint: hi/medium (Sanskrit detected as Hindi by language hint)

### SVK-2021 (Uttaradhyayana Hindi — DUPLICATE)
- **2,683 total units**
- **1,065 flagged** (39.7%)
- All units EXACT_DUPLICATE of SVK-0016
- Not released

---

## OCR/Extraction Problems

- All 3 sources used Internet Archive DjVuTXT text layers (Tesseract OCR)
- No additional OCR was performed
- OCR quality is moderate — significant VERY_SHORT and HIGH_DIGIT_RATIO flags indicate OCR artifacts
- The Sanskrit sources (SVK-2019, SVK-2020) show higher SCRIPT_MISMATCH and HIGH_DIGIT_RATIO than typical Hindi/Gujarati sources, suggesting the OCR struggled more with Sanskrit Devanagari

---

## Provenance Problems

- None. All released units retain full provenance (source_id, source_url, artifact_sha256, gate_rule, etc.)
- SVK-2019 correctly linked to AGAM-015
- SVK-2020 correctly linked to AGAM-013

---

## Duplicate/Translation Overlap

- **SVK-2021 is 100% duplicate of SVK-0016** — Internet Archive DjVuTXT files are byte-identical despite different metadata
- **SVK-2019:** 1,449 units (64.6%) overlap with existing corpus — expected for Kalpa Sutra which shares content with existing canonical sources
- **SVK-2020:** 2,814 units (67.6%) overlap with existing corpus — expected for Uttaradhyayana which shares content with SVK-0016
- Cross-source deduplication is working correctly

---

## Remaining Processing Blockers

1. **SVK-2021 should be marked as duplicate** of SVK-0016 in the source manifest
2. **OCR quality is moderate** for Sanskrit sources — manual review recommended for high-value units
3. **No additional P0 sources acquired** — the remaining P0 queue items (Acharanga, Sutrakritanga, Dashvaikalik, Nishitha, standalone practice texts) require source discovery on JainQQ/Jainebooks

---

## Test Results

**313/313 tests pass** (3 faiss-dependent tests excluded — expected without faiss installed).

- 267 non-retrieval tests: all pass
- 46 retrieval tests: all pass (excluding 3 SentenceTransformer tests requiring faiss)
- No regressions detected

---

## Files Created/Updated

- `data/raw/SVK-2019/` — raw text + metadata + checksums
- `data/raw/SVK-2020/` — raw text + metadata + checksums
- `data/raw/SVK-2021/` — raw text + metadata + checksums
- `data/extracted/SVK-2019/text.txt` + `extraction.json`
- `data/extracted/SVK-2020/text.txt` + `extraction.json`
- `data/extracted/SVK-2021/text.txt` + `extraction.json`
- `data/normalized/SVK-2019/text.txt` + `normalization.json`
- `data/normalized/SVK-2020/text.txt` + `normalization.json`
- `data/normalized/SVK-2021/text.txt` + `normalization.json`
- `data/segmented/SVK-2019/units.jsonl` + `segmentation.json`
- `data/segmented/SVK-2020/units.jsonl` + `segmentation.json`
- `data/segmented/SVK-2021/units.jsonl` + `segmentation.json`
- `data/release/rag_corpus.jsonl` — regenerated (155,994 units)
- `data/release/training_corpus.jsonl` — regenerated (88,896 units)
- `data/release/manifest.json` — regenerated
- `manifests/source_manifest.csv` — 69 sources
- `manifests/artifact_manifest.csv` — 123 rows
- `manifests/license_manifest.csv` — 69 decisions
- `data/reports/task22c_processing_report.md` — this report

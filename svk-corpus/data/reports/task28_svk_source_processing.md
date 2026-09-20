# Task 28 — Processing Report for Newly Acquired Sthānakavāsī Sources

**Date:** 2026-09-19 · **Status:** COMPLETE

---

## 1. Sources Processed

| Source | Title | Units | Chars | Status |
|--------|-------|-------|-------|--------|
| SVK-2022 | Avashyak Sutra Sthanakvasi | 1,293 | 1,544,765 | EXTRACTED + SEGMENTED |
| SVK-2023 | Uttaradhyayana Sutra Sthanakvasi | 2,606 | 3,081,510 | EXTRACTED + SEGMENTED |
| SVK-2024 | Pratikraman - Self Reflection | 26 | 26,856 | EXTRACTED + SEGMENTED |
| SVK-2025 | Sthanang Sutra Sthanakvasi | 4,068 | 3,405,441 | EXTRACTED + SEGMENTED |
| SVK-2026 | Dasvaikalik Sutra Sthanakvasi | 1,584 | 1,717,208 | EXTRACTED + SEGMENTED |
| SVK-2027 | Sthanakvasi Jain Itihas | 376 | 322,312 | EXTRACTED + SEGMENTED |
| SVK-2028 | Inner Journey Part 01 | 372 | 473,265 | EXTRACTED + SEGMENTED |
| SVK-2029 | Aupapatik Sutra Sthanakvasi | 2,454 | 1,877,807 | EXTRACTED + SEGMENTED |
| **TOTAL** | | **12,779** | **12,449,164** | |

---

## 2. Extraction Success/Failure

| Source | Status | Method | Characters | Pages |
|--------|--------|--------|------------|-------|
| SVK-2022 | OK | HOCR | 1,547,916 | 1 |
| SVK-2023 | OK | HOCR | 3,100,529 | 1 |
| SVK-2024 | OK | HOCR | 26,952 | 1 |
| SVK-2025 | OK | HOCR | 3,413,690 | 1 |
| SVK-2026 | OK | HOCR | 1,721,881 | 1 |
| SVK-2027 | OK | HOCR | 323,232 | 1 |
| SVK-2028 | OK | HOCR | 473,879 | 1 |
| SVK-2029 | OK | HOCR | 1,883,062 | 1 |

**All 8 sources extracted successfully.**

---

## 3. Unit Counts

| Source | Units | Verse | Paragraph | Chunk | Structure |
|--------|-------|-------|-----------|-------|-----------|
| SVK-2022 | 1,293 | 0 | 63 | 1,230 | unknown |
| SVK-2023 | 2,606 | 0 | 150 | 2,456 | unknown |
| SVK-2024 | 26 | 0 | 5 | 21 | unknown |
| SVK-2025 | 4,068 | 211 | 1,182 | 2,636 | medium |
| SVK-2026 | 1,584 | 0 | 94 | 1,490 | unknown |
| SVK-2027 | 376 | 1 | 245 | 130 | medium |
| SVK-2028 | 372 | 0 | 177 | 195 | unknown |
| SVK-2029 | 2,454 | 126 | 735 | 1,474 | medium |
| **TOTAL** | **12,779** | **338** | **2,651** | **9,632** | |

---

## 4. Quality Statistics

| Source | Units | REPEATED_CHARACTER_RUN | HIGH_SYMBOL_RATIO | SCRIPT_MISMATCH | VERY_SHORT | HIGH_DIGIT_RATIO |
|--------|-------|----------------------|-------------------|-----------------|------------|------------------|
| SVK-2022 | 1,293 | 736 | 8 | 0 | 0 | 0 |
| SVK-2023 | 2,606 | 1,393 | 63 | 0 | 0 | 3 |
| SVK-2024 | 26 | 8 | 4 | 0 | 0 | 0 |
| SVK-2025 | 4,068 | 2,141 | 730 | 730 | 229 | 153 |
| SVK-2026 | 1,584 | 964 | 26 | 0 | 0 | 1 |
| SVK-2027 | 376 | 240 | 122 | 133 | 0 | 0 |
| SVK-2028 | 372 | 355 | 10 | 0 | 0 | 0 |
| SVK-2029 | 2,454 | 864 | 589 | 539 | 322 | 221 |

**Key findings:**
- REPEATED_CHARACTER_RUN is the dominant flag (Romanized Prakrit artifacts)
- SCRIPT_MISMATCH appears in SVK-2025, SVK-2027, SVK-2029 (mixed scripts)
- VERY_SHORT appears in SVK-2025, SVK-2029 (short segments)
- HIGH_DIGIT_RATIO appears in SVK-2025, SVK-2029 (page numbers, etc.)

---

## 5. Language/Script Statistics

| Source | Detected Script | Detected Language | Confidence |
|--------|-----------------|-------------------|------------|
| SVK-2022 | Latin (100%) | en | medium |
| SVK-2023 | Latin (100%) | en | medium |
| SVK-2024 | Latin (100%) | en | medium |
| SVK-2025 | Latin (52%) | en | low |
| SVK-2026 | Latin (100%) | en | medium |
| SVK-2027 | Gujarati (81%) | gu | medium |
| SVK-2028 | Latin (100%) | en | medium |
| SVK-2029 | Latin (56%) | en | low |

**Note:** Most sources are Romanized Prakrit/Hindi, detected as "Latin/en" by the language detector. The actual content is Prakrit/Hindi in Roman script.

---

## 6. Rights Status

| Source | Gate Decision | Rule | Training Allowed | Released |
|--------|---------------|------|------------------|----------|
| SVK-2022 | UNKNOWN | R99_INSUFFICIENT_EVIDENCE | NO | NO |
| SVK-2023 | UNKNOWN | R99_INSUFFICIENT_EVIDENCE | NO | NO |
| SVK-2024 | UNKNOWN | R99_INSUFFICIENT_EVIDENCE | NO | NO |
| SVK-2025 | UNKNOWN | R99_INSUFFICIENT_EVIDENCE | NO | NO |
| SVK-2026 | UNKNOWN | R99_INSUFFICIENT_EVIDENCE | NO | NO |
| SVK-2027 | UNKNOWN | R99_INSUFFICIENT_EVIDENCE | NO | NO |
| SVK-2028 | UNKNOWN | R99_INSUFFICIENT_EVIDENCE | NO | NO |
| SVK-2029 | UNKNOWN | R99_INSUFFICIENT_EVIDENCE | NO | NO |

**All 8 sources are quarantined. No text released to corpus.**

---

## 7. RAG Impact

**No change.** All 8 sources are excluded from the release corpus due to UNKNOWN rights status.

---

## 8. Training Impact

**No change.** All 8 sources are excluded from the training corpus.

---

## 9. Sthānakavāsī Contextual Content

### Confirmed Sthanakvasi Sources (7):

| Source | Evidence | Practice Coverage |
|--------|----------|-------------------|
| SVK-2022 | Title + Author + Publisher all confirm Sthanakvasi | AVASHYAKA, SAMAYIK, PRATIKRAMAN, KAYOTSARGA, VANDANA, PRATYAKHYAN |
| SVK-2023 | Title + Author + Publisher confirm Sthanakvasi | Uttaradhyayana commentary |
| SVK-2025 | Title + Author + Publisher confirm Sthanakvasi | Sthanang Sutra |
| SVK-2026 | Title + Author + Publisher confirm Sthanakvasi | Dasvaikalik Sutra |
| SVK-2027 | Title + Publisher confirm Sthanakvasi | Sthanakvasi history |
| SVK-2028 | Author is confirmed Sthanakvasi Muni | Modern teaching |
| SVK-2029 | Title + Author + Publisher confirm Sthanakvasi | Aupapatik Sutra |

### Unknown Tradition (1):

| Source | Evidence |
|--------|----------|
| SVK-2024 | Author Pravin K Shah / JAINA Education Committee (multi-tradition) |

---

## 10. Practice Coverage

| Practice | Before Task 28 | After Task 28 | Source |
|----------|----------------|---------------|--------|
| AVASHYAKA | 1 source | **2 sources** | +SVK-2022 |
| SAMAYIK | 1 source | **2 sources** | +SVK-2022 |
| PRATIKRAMAN | 1 source | **3 sources** | +SVK-2022, SVK-2024 |
| KAYOTSARGA | 0 sources | **1 source** | +SVK-2022 |
| VANDANA | 0 sources | **1 source** | +SVK-2022 |
| PRATYAKHYAN | 0 sources | **1 source** | +SVK-2022 |
| CHAUVISANTHO | 0 sources | 0 sources | Still missing |
| PARYUSHAN | 0 sources | 0 sources | Still missing |
| PAUSHADH | 0 sources | 0 sources | Still missing |

---

## 11. Agam Coverage

| Agam | Before Task 28 | After Task 28 | Source |
|------|----------------|---------------|--------|
| AGAM-003 (Sthanang) | 0 | **1** | +SVK-2025 |
| AGAM-012 (Aupapatik) | 0 | **1** | +SVK-2029 |
| AGAM-028 (Avashyak) | 0 | **1** | +SVK-2022 |
| AGAM-029 (Dasvaikalik) | 0 | **1** | +SVK-2026 |
| AGAM-030 (Uttaradhyayana) | 1 | **2** | +SVK-2023 |

---

## 12. Teacher Attribution

| Teacher | Before Task 28 | After Task 28 | Sources |
|---------|----------------|---------------|---------|
| Amarmuni | 0 | **5** | SVK-2022, SVK-2023, SVK-2025, SVK-2026, SVK-2029 |
| Namramuni | 0 | **1** | SVK-2028 |
| Shreechand Surana | 0 | **3** | SVK-2025, SVK-2026, SVK-2029 |
| Pravin K Shah | 0 | **1** | SVK-2024 |
| Kesrichand Bhandari | 0 | **1** | SVK-2027 |

---

## 13. Before/After Task 24 Comparison

| Metric | Task 24 Baseline | Task 28 (predicted) | Change |
|--------|------------------|---------------------|--------|
| Total units processed | 88,896 | 88,896 + 12,779 = **101,675** | +14.4% |
| Confirmed Sthanakvasi sources | 17 | **24** | +7 |
| Agam editions | 5 | **10** | +5 |
| Teacher-attributed sources | 0 | **11** | +11 |
| Practice coverage | 3 practices | **6 practices** | +3 |

**Note:** These units are NOT in the released corpus (rights UNKNOWN). They are processed but quarantined.

---

## 14. Problems Encountered

1. **Romanized Prakrit** — Most sources are Romanized Prakrit/Hindi, detected as "Latin/en" by language detector
2. **REPEATED_CHARACTER_RUN** — Dominant quality flag (Romanized text artifacts)
3. **SCRIPT_MISMATCH** — Mixed scripts in SVK-2025, SVK-2027, SVK-2029
4. **Rights UNKNOWN** — All sources quarantined, not released
5. **No pipeline release** — Sources processed but not in final corpus

---

## 15. Recommended Next Step

1. **Resolve rights status** for JainQQ sources (JAIN EDUCATION INTERNATIONAL terms)
2. **Run tokenizer measurement** on quarantined units to measure actual token counts
3. **Search for remaining gaps:** CHAUVISANTHO, PARYUSHAN, PAUSHADH
4. **Acquire Jainebooks sources** if account access established
5. **Process SFT candidate extraction** on quarantined units to measure training potential

---

## Files Updated

- `manifests/source_manifest.csv` — 8 new source rows
- `manifests/artifact_manifest.csv` — 8 new artifact rows
- `manifests/license_manifest.csv` — 8 new gate decisions (all UNKNOWN)
- `data/raw/SVK-2022/` through `data/raw/SVK-2029/` — source files
- `data/extracted/SVK-2022/` through `data/extracted/SVK-2029/` — extracted text
- `data/normalized/SVK-2022/` through `data/normalized/SVK-2029/` — normalized text
- `data/segmented/SVK-2022/` through `data/segmented/SVK-2029/` — segmented units
- `data/quality/units_quality.jsonl` — quality assessments
- `data/release/excluded_sources.jsonl` — 8 new excluded sources

**Corpus/gate/release changed:** YES — manifests updated, but release corpus unchanged (sources quarantined)

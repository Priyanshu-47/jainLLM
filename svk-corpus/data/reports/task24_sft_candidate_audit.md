# Task 24 — SFT Candidate Audit and Correction Report

**Date:** 2026-09-19 · **Status:** COMPLETE

---

## A. What Was Wrong with Task 23

The v1 implementation conflated **source-level metadata** with **passage-level evidence**. Specifically:

| Category | v1 Error | v2 Fix |
|----------|----------|--------|
| TEACHER_ATTRIBUTION | Every passage from a source with author metadata → teacher attribution | Only passages with explicit attribution patterns (e.g., "Acharya X says...") |
| MULTILINGUAL_MAPPING | Every Hindi/Gujarati/English passage → multilingual mapping | Only passages with actual cross-language content (term = explanation) |
| AGAM_GROUNDED | Every passage from a canonical source → Agam-grounded | Only passages referencing specific Agams by name |
| STHANAKAVASI_EXPLANATION | Source description containing "Sthanakavasi" → every passage | Only passages with Sthanakavasi-specific content |
| PRACTICE_* | Source title containing "Pratikraman" → every passage | Only passages explaining practice (definition/purpose/procedure) |
| LEXICON_SOURCE | Source classified as LEXICON → every passage | Only passages with term + explanation pattern |
| GENERAL_JAIN | Fallback for unclassified passages | Now also requires minimum semantic completeness |

---

## B. Corrected Eligibility Rules

### Minimum text length
- All candidates: ≥40 characters
- HIGH_CONFIDENCE: ≥80 characters

### Category evidence requirements
- **TEACHER_ATTRIBUTION**: Explicit attribution pattern in passage text
- **MULTILINGUAL_MAPPING**: Cross-language content pattern (term = explanation)
- **AGAM_GROUNDED**: Agam name referenced in passage text
- **STHANAKAVASI_EXPLANATION**: Sthanakavasi-specific content in passage
- **PRACTICE_***: Practice explanation pattern (not just keyword mention)
- **PRAKRIT_SANSKIRT_TERM**: Term + explanation pattern
- **LEXICON_REFERENCE**: Term + explanation in lexicon source
- **HISTORICAL_BIOGRAPHICAL**: Historical evidence in passage

### Exclusion rules
- Text < 40 characters
- Failed category eligibility (no specific category detected + too short)
- OCR noise with insufficient length
- High digit + symbol ratio combined

---

## C. Before/After Candidate Counts

| Metric | v1 | v2 | Change |
|--------|-----|-----|--------|
| Total candidates | 88,896 | 47,927 | **-46%** |
| Excluded | 0 | 40,969 | +40,969 |
| HIGH_CONFIDENCE | 54,723 | 35,641 | -35% |
| REVIEW_REQUIRED | 669 | 12,286 | +1,736% |
| LOW_QUALITY | 33,504 | 0 | -100% |

---

## D. Before/After Category Counts

| Category | v1 | v2 | Change |
|----------|-----|-----|--------|
| TEACHER_ATTRIBUTION | 82,241 | **2,615** | **-97%** |
| MULTILINGUAL_MAPPING | 60,717 | **21,428** | **-65%** |
| LEXICON_SOURCE | 42,106 | — | replaced by LEXICON_REFERENCE |
| LEXICON_REFERENCE | — | **2,714** | new (strict) |
| STHANAKAVASI_EXPLANATION | 14,998 | 0 | -100% (none found with strict patterns) |
| PRAKRIT_SANSKIRT_TERM | 9,994 | **9,030** | -10% |
| AGAM_GROUNDED | 3,747 | **863** | **-77%** |
| GENERAL_JAIN | 122 | **16,810** | +13,679% (passages without specific markers) |
| PRACTICE_PRATIKRAMAN | 2,068 | **5** | **-99.8%** |
| PRACTICE_SAMAYIK | 858 | **2** | **-99.8%** |
| HISTORICAL_BIOGRAPHICAL | 379 | **656** | +73% (better pattern matching) |

---

## E. Teacher Attribution Evidence Count

**v1: 82,241** (source author metadata propagated to every passage)
**v2: 2,615** (explicit attribution pattern in passage text)

The 2,615 v2 candidates contain actual attribution patterns such as:
- "आचार्य X says..."
- "According to Muni X..."
- Named teacher in passage context

This is a **97% reduction** — the vast majority of v1 "teacher attribution" candidates were false positives from source metadata.

---

## F. Multilingual Mapping Evidence Count

**v1: 60,717** (every Hindi/Gujarati/English passage)
**v2: 21,428** (passages with actual cross-language content patterns)

The 21,428 v2 candidates contain actual cross-language content such as:
- Prakrit term = Hindi explanation
- English term = Indic explanation
- Bilingual heading patterns

This is a **65% reduction** — language alone is not a multilingual mapping.

---

## G. Agam-Grounded Evidence Count

**v1: 3,747** (every passage from a canonical source)
**v2: 863** (passages referencing specific Agams by name)

The 863 v2 candidates contain actual Agam references such as:
- "कल्प सूत्र" (Kalpa Sutra)
- "उत्तराध्ययन" (Uttaradhyayana)
- "आचारांग" (Acaranga)

This is a **77% reduction** — source association is not passage-level Agam citation.

---

## H. Practice Candidate Counts

| Practice | v1 | v2 | Change |
|----------|-----|-----|--------|
| PRATIKRAMAN | 2,068 | **5** | -99.8% |
| SAMAYIK | 858 | **2** | -99.8% |
| AVASHYAKA | 775 | 0 | -100% |
| VANDANA | 277 | 0 | -100% |
| PRATYAKHYAN | 217 | 0 | -100% |
| CHAUVISANTHO | 27 | 0 | -100% |
| KAYOTSARGA | 16 | 0 | -100% |

The dramatic reduction confirms that the corpus contains very few passages that actually **explain** practices — most merely mention practice keywords. The 5 PRATIKRAMAN and 2 SAMAYIK candidates contain genuine practice explanation patterns.

---

## I. Lexicon/Reference Counts

**v1: 42,106 LEXICON_SOURCE** (every passage from lexicon sources)
**v2: 2,714 LEXICON_REFERENCE** (lexicon passages with term + explanation)

Additionally, 9,030 candidates have PRAKRIT_SANSKIRT_TERM (term + explanation pattern) from non-lexicon sources.

The lexicon dominance dropped from 47% to 5.7% of candidates.

---

## J. Strongest Genuine Sthanakavasi Candidates

**v1: 14,998 STHANAKAVASI_EXPLANATION** (source description contained "Sthanakavasi")
**v2: 0 STHANAKAVASI_EXPLANATION** (no passages matched strict Sthanakavasi content patterns)

This is an honest finding: the corpus does not currently contain passages that explicitly explain Sthanakavasi-specific doctrine or practice. The Sthanakavasi indicators in v1 were all from source-level metadata, not passage content.

**Sources with Sthanakavasi metadata (but no passage-level evidence):**
- SVK-2010: 220 candidates (sect literature)
- SVK-2011: 491 candidates (philosophy)
- SVK-2012: 1,070 candidates (Sthanakavasi text)
- SVK-2013: 44 candidates (educational)
- SVK-2014: 520 candidates (practice literature)

These sources are retained as candidates with Sthanakavasi provenance, but without the STHANAKAVASI_EXPLANATION category.

---

## K. Remaining Gaps

### Critical gaps (blocking verified SFT construction):

1. **Zero Sthanakavasi-specific doctrinal passages** — no passage explains Sthanakavasi doctrine/practice distinctly
2. **Near-zero practice explanation passages** — 7 total across all practice categories
3. **No verified teacher commentary passages** — 2,615 have attribution patterns but no verified authorship
4. **37.7% of training units excluded** — mostly short fragments and OCR artifacts

### Quality gaps:

5. **12,286 REVIEW_REQUIRED** candidates need human review
6. **Lexicon dominance reduced but still present** — 21,109 lexicon-source candidates remain
7. **No cross-tradition contrast passages** — model cannot learn Sthanakavasi vs Digambara distinction

### Coverage gaps:

8. **Kayotsarga**: 0 practice explanation passages
9. **Chauvisantho**: 0 practice explanation passages
10. **Modern teacher interpretations**: not represented
11. **Abstention/uncertainty examples**: not detected with strict patterns

---

## L. Do We Now Have Enough Material for Verified SFT Construction?

**No, not yet.**

### What we have (improved by v2):

- 47,927 eligible candidates with strict passage-level evidence
- 35,641 HIGH_CONFIDENCE candidates
- Honest category counts reflecting actual passage content
- Full provenance for every candidate
- Deterministic, reproducible extraction

### What we still lack:

1. **Sthanakavasi-specific doctrinal depth** — 0 passages explain Sthanakavasi doctrine
2. **Practice explanation material** — 7 passages total across all practices
3. **Verified teacher commentary** — attribution patterns exist but no verified authorship
4. **Cross-tradition contrast** — no passages compare Sthanakavasi with other traditions
5. **Human verification** — all candidates are CANDIDATE status, none VERIFIED

### Recommendation:

The v2 candidate extraction is now honest and deterministic. However, **verified SFT construction should NOT begin until:**

1. At least 1 genuine Sthanakavasi doctrinal text is acquired (e.g., from JainQQ/Jainebooks)
2. Dedicated practice texts (Pratikraman, Samayik, Kayotsarga) are acquired
3. Human verification is performed on a sample of HIGH_CONFIDENCE candidates
4. The 12,286 REVIEW_REQUIRED candidates are triaged

The v2 extraction correctly reveals that the corpus's SFT value is primarily in **canonical text passages** (AGAM_GROUNDED: 863) and **term explanations** (PRAKRIT_SANSKIRT_TERM: 9,030), not in sect-specific or practice-specific content.

---

## Test Results

**354/354 tests pass** (3 faiss-dependent tests excluded).

- 21 new v2 audit tests: all pass
- Key assertions verified:
  - Source author alone → NO teacher attribution ✓
  - Hindi language alone → NO multilingual mapping ✓
  - Word mention alone → NO practice category ✓
  - Dictionary fragment → excluded ✓
  - Term + explanation → LEXICON_REFERENCE ✓
  - OCR noise → REVIEW_REQUIRED ✓
  - v2 < v1 candidates ✓
  - Provenance preserved ✓

---

## Files Created/Updated

- `src/svk_corpus/training/sft_candidates_v2.py` — strict extraction logic
- `data/training/sft_candidate_passages_v2.jsonl` — 47,927 candidates
- `tests/test_sft_candidates_v2.py` — 21 validation tests
- `data/reports/task24_sft_candidate_audit.md` — this report

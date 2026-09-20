# Task 23 — SFT Candidate Passage Extraction Report

**Date:** 2026-09-19 · **Status:** COMPLETE

---

## 1. Total Candidates

| Metric | Count |
|--------|-------|
| Total candidates | **88,896** |
| HIGH_CONFIDENCE_CANDIDATE | **54,723** (61.6%) |
| REVIEW_REQUIRED | **669** (0.8%) |
| LOW_QUALITY | **33,504** (37.7%) |
| Duplicate candidates | **0** |
| High-priority (from prioritized sources) | **10,717** |

---

## 2. Candidates by Source

| Source | Count | Category |
|--------|-------|----------|
| SVK-2006 | 18,115 | Lexicon (Prakrit dictionary) |
| SVK-1007 | 8,481 | Reference (bibliography) |
| SVK-2007 | 6,641 | Lexicon |
| SVK-1005 | 5,010 | Secondary scholarship |
| SVK-2002 | 4,476 | Lexicon (Gujarati) |
| SVK-2005 | 3,121 | Lexicon (Devanagari) |
| SVK-2004 | 3,111 | Lexicon (Gujarati) |
| SVK-2009 | 3,088 | Grammar (Prakrit) |
| SVK-2008 | 3,056 | Grammar (Prakrit) |
| SVK-0026 | 3,635 | Lexicon |
| SVK-1010 | 3,694 | Secondary scholarship |
| SVK-1001 | 3,770 | Primary canon (Anga) |
| SVK-2003 | 2,575 | Lexicon (Gujarati) |
| SVK-0007 | 2,574 | Lexicon |
| SVK-2016 | 2,020 | Practice (Pratikraman) |
| SVK-2020 | 2,334 | Canonical (Uttaradhyayana Sanskrit) |
| SVK-2019 | 1,413 | Canonical (Kalpa Sutra) |
| SVK-2012 | 1,464 | Sthanakavasi text |
| SVK-2014 | 1,286 | Practice literature |
| SVK-0038 | 1,188 | History |
| SVK-0037 | 1,493 | Lexicon |
| SVK-2011 | 903 | Philosophy (Gujarati) |
| SVK-0016 | 1,570 | Primary canon (Mulasutra) |
| SVK-1009 | 768 | Secondary scholarship |
| SVK-1002 | 755 | Primary canon (Kalpasutra) |
| SVK-2015 | 659 | Canonical (Avashyaka) |
| SVK-1003 | 557 | Primary canon |
| SVK-2010 | 516 | Sect literature (Sthanakavasi) |
| SVK-1006 | 240 | Secondary scholarship |
| SVK-2013 | 122 | Educational |
| SVK-1008 | 261 | Secondary scholarship |

---

## 3. Candidates by Category

| Category | Count | Description |
|----------|-------|-------------|
| MULTILINGUAL_MAPPING | 60,717 | Hindi/Gujarati/English sources |
| TEACHER_ATTRIBUTION | 82,241 | Source has author/teacher metadata |
| LEXICON_SOURCE | 42,106 | Lexicon/dictionary sources |
| STHANAKAVASI_EXPLANATION | 14,998 | Sthanakavasi indicators found |
| PRAKRIT_SANSKIRT_TERM | 9,994 | Sanskrit/Prakrit language sources |
| AGAM_GROUNDED | 3,747 | Linked to specific Agam |
| CANONICAL_SOURCE | 3,747 | Classified as canonical |
| PRACTICE_PRATIKRAMAN | 2,068 | Pratikraman practice indicators |
| CROSS_TRADITION | 1,570 | Multi-tradition sources |
| PRACTICE_SAMAYIK | 858 | Samayik practice indicators |
| PRACTICE_AVASHYAKA | 775 | Avashyaka practice indicators |
| ABSTENTION_EVIDENCE | 637 | Text shows uncertainty/qualification |
| HISTORICAL_BIOGRAPHICAL | 379 | History/biography indicators |
| PRACTICE_VANDANA | 277 | Vandana practice indicators |
| PRACTICE_PRATYAKHYAN | 217 | Pratyakhyan practice indicators |
| GENERAL_JAIN | 122 | Fallback classification |
| PRACTICE_CHAUVISANTHO | 27 | Chauvisantho indicators |
| PRACTICE_KAYOTSARGA | 16 | Kayotsarga indicators |

---

## 4. Candidates by Language

| Language | Count | Percentage |
|----------|-------|------------|
| English | 34,503 | 38.8% |
| unknown (mixed/Sanskrit) | 30,895 | 34.8% |
| Gujarati | 14,453 | 16.3% |
| Hindi | 9,045 | 10.2% |

---

## 5. Candidates by Knowledge Layer

| Knowledge Layer | Count | SFT Value |
|----------------|-------|-----------|
| Lexicon | 42,106 | Moderate — term definitions |
| Primary canon (Anga) | 3,770 | HIGH — canonical scripture |
| Canonical | 3,747 | HIGH — canonical text |
| Grammar (Prakrit) | 6,144 | HIGH — language structure |
| Sect literature (Sthanakavasi) | 516 | HIGH — sect-specific |
| Practice literature (sajjhaya) | 1,286 | HIGH — practice guidance |
| Philosophy (Gujarati) | 903 | HIGH — doctrinal exposition |
| Primary canon (Mulasutra) | 1,570 | HIGH — core scripture |
| Primary canon (Kalpasutra) | 557 | HIGH — core scripture |
| Secondary scholarship | 7,743 | Moderate — Western analysis |
| Reference (bibliography) | 8,481 | Low — citations only |
| Educational | 122 | Moderate — pedagogical |
| (empty/unclassified) | 11,951 | Variable |

---

## 6. Candidates by Tradition

| Tradition | Count |
|-----------|-------|
| JAIN (generic) | 64,886 |
| SVETAMBARA | 7,761 |
| JAIN;BIBLIOGRAPHY | 8,481 |
| JAIN plus other traditions | 5,010 |
| MULTI_TRADITION | 1,570 |
| JAIN;WESTERN SCHOLARSHIP | 1,188 |

---

## 7. Quality Distribution

| Quality Status | Count | Percentage |
|----------------|-------|------------|
| HIGH_CONFIDENCE_CANDIDATE | 54,723 | 61.6% |
| LOW_QUALITY | 33,504 | 37.7% |
| REVIEW_REQUIRED | 669 | 0.8% |

**LOW_QUALITY breakdown:** Most low-quality units are very short (<50 chars) — typically verse refrains, page numbers, or OCR fragments. They are preserved in the candidate list but marked for review.

---

## 8. Strongest Sthanakavasi Coverage

**14,998 candidates** have Sthanakavasi indicators (from text or metadata).

Sources with Sthanakavasi content:
- SVK-2010: 516 units — sect literature (Sthanakavasi)
- SVK-2011: 903 units — philosophy (Gujarati)
- SVK-2012: 1,464 units — Sthanakavasi text
- SVK-2013: 122 units — educational
- SVK-2014: 1,286 units — practice literature

**Gap:** Only 1 source (SVK-2010) is explicitly classified as Sthanakavasi sect literature. The others are generic Jain texts that happen to contain Sthanakavasi indicators.

---

## 9. Strongest Practice Coverage

| Practice | Candidates | Sources |
|----------|-----------|---------|
| PRATIKRAMAN | 2,068 | SVK-2016 (Panch-pratikraman), SVK-2015 (Avashyaka) |
| SAMAYIK | 858 | SVK-2015 (Avashyaka) |
| AVASHYAKA | 775 | SVK-2015 (Avashyaka) |
| VANDANA | 277 | SVK-2015 (Avashyaka) |
| PRATYAKHYAN | 217 | SVK-2015 (Avashyaka) |
| CHAUVISANTHO | 27 | Limited |
| KAYOTSARGA | 16 | Very limited |

**Gap:** Kayotsarga and Chauvisantho have minimal coverage. Standalone practice texts for these categories are not yet in the corpus.

---

## 10. Remaining SFT Gaps

### Critical gaps:

1. **No verified SFT examples exist** — this task only extracts CANDIDATE passages, not verified Q&A pairs
2. **Sthanakavasi-specific doctrinal content is thin** — only 1 source (SVK-2010) is explicitly Sthanakavasi sect literature
3. **Kayotsarga practice coverage** — only 16 candidates, none from dedicated practice texts
4. **Chauvisantho practice coverage** — only 27 candidates
5. **No modern Sthanakavasi teacher material** — Anand Rishi, Praveen Rishi Maharasaheb not represented
6. **Cross-tradition distinction** — only 1,570 candidates from multi-tradition sources
7. **Abstention/uncertainty examples** — only 637 candidates with explicit uncertainty markers

### Quality gaps:

- **37.7% LOW_QUALITY** candidates need review before SFT use
- **OCR quality** is moderate for Sanskrit sources (SVK-2019, SVK-2020)
- **No human-verified passages** exist yet

---

## 11. Do We Have Enough Material for Verified SFT Construction?

**Partially, but with significant caveats.**

### What we have:

- **54,723 HIGH_CONFIDENCE_CANDIDATE passages** with provenance
- Coverage of 3 canonical texts (Kalpa Sutra, Uttaradhyayana, Avashyaka)
- Practice coverage for Pratikraman, Samayik, Avashyaka, Vandana, Pratyakhyan
- Sthanakavasi indicators in ~15,000 candidates
- Full provenance metadata for every candidate

### What we lack:

- **No verified SFT examples** — every candidate needs human verification before use
- **No Sthanakavasi-specific doctrinal depth** — generic Jain material dominates
- **No modern teacher interpretations** — the model would have no contemporary Sthanakavasi voice
- **No cross-tradition contrast** — the model cannot learn to distinguish Sthanakavasi from Digambara views
- **Limited abstention training** — only 637 candidates demonstrate uncertainty
- **OCR quality concerns** — 37.7% of candidates need review

### Recommendation:

The candidate extraction layer is complete and deterministic. However, **verified SFT construction should NOT begin until:**

1. At least 1 genuine Sthanakavasi doctrinal text is acquired and processed
2. Human verification is performed on a sample of HIGH_CONFIDENCE_CANDIDATE passages
3. The 37.7% LOW_QUALITY candidates are reviewed and either promoted or excluded
4. Abstention/uncertainty examples are expanded beyond 637 candidates

The current candidate set is a **necessary prerequisite** but not a **sufficient condition** for verified SFT construction.

---

## 12. Test Results

**333/333 tests pass** (3 faiss-dependent tests excluded).

- 20 new SFT candidate tests: all pass
- Validation covers: required fields, unique candidate_id, valid source_id, sft_status, provenance presence, categories as lists
- Full test suite: no regressions

---

## 13. Files Created/Updated

- `src/svk_corpus/training/sft_candidates.py` — extraction logic (deterministic, metadata-based)
- `data/training/sft_candidate_passages_v1.jsonl` — 88,896 candidate records
- `tests/test_sft_candidates.py` — 20 validation tests
- `data/reports/task23_sft_candidate_extraction.md` — this report

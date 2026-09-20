# Task 39: Sthanakavasi Knowledge Mining + Dataset Readiness Sprint

**Date:** 2026-09-20
**Status:** COMPLETE

---

## 1. Corpus Delta After Release

| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| RAG units | 165,016 | 210,798 | +45,782 |
| Training units | 97,918 | 144,323 | +46,405 |

**Note:** Minor difference due to deduplication during release.

---

## 2. Corpus-Wide Knowledge Distribution

| Category | Count | % |
|----------|-------|---|
| CANONICAL_TEXT | 78,773 | 41.2% |
| TRANSLATION | 75,256 | 39.4% |
| GENERAL_JAIN | 20,600 | 10.8% |
| COMMENTARY | 15,070 | 7.9% |
| PRACTICE_EXPLANATION | 1,123 | 0.6% |
| TEACHING | 216 | 0.1% |

### STH Status Distribution

| Status | Count | % |
|--------|-------|---|
| GENERIC_SVETAMBARA | 105,720 | 55.3% |
| PROBABLE_STHANAKAVASI | 85,222 | 44.6% |
| VERIFIED_STHANAKAVASI | 91 | 0.05% |
| CROSS_TRADITION | 5 | <0.01% |

---

## 3. Deep Sthanakavasi Mining Results

### Verified STH Passages: 91

- **SVK-2037 (Jinvani Pratikraman):** 13 passages (ambiguous content)
- **Other sources:** 78 passages (metadata/affiliation references)

### Teacher-Attributed Units: 227

| Teacher | Units |
|---------|-------|
| Amarmuni | 174 |
| Shreechand Surana | 34 |
| Namramuni | 6 |
| Pravin K Shah | 6 |
| Anand Rishi | 4 |
| Dharmchand Jain | 2 |
| Kesrichand Bhandari | 1 |

---

## 4. Practice Knowledge Matrix

| Practice | Word Occurrences | Contextual | Explanations | STH-Specific | Teacher-Attributed |
|----------|------------------|------------|--------------|--------------|-------------------|
| Pratikraman | 608 | 379 | 379 | 0 | 2 |
| Samayik | 301 | 191 | 191 | 0 | 0 |
| Pratyakhyan | 318 | 150 | 150 | 0 | 0 |
| Avashyaka | 12 | 193 | 193 | 0 | 3 |
| Vandana | 133 | 84 | 84 | 0 | 0 |
| Kayotsarga | 83 | 65 | 65 | 0 | 1 |
| Paryushan | 72 | 48 | 48 | 0 | 2 |
| Paushadh | 48 | 11 | 11 | 0 | 0 |
| Chauvisantho | 4 | 2 | 2 | 0 | 0 |

**Total practice explanations: 1,123**
**STH-specific practice explanations: 0**

---

## 5. Agam Knowledge Matrix

| Agam ID | Name | Units | Canonical | Commentary | Translation | Teacher | STH |
|---------|------|-------|-----------|------------|-------------|---------|-----|
| AGAM-001 | Acharanga | 20,268 | 8,906 | 2,064 | 8,974 | 28 | 8 |
| AGAM-005 | Bhagvati | 38,166 | 13,176 | 4,798 | 15,910 | 60 | 14 |
| AGAM-012 | Samvayang | 9,496 | 4,526 | 902 | 3,280 | 28 | 8 |
| AGAM-022 | Sthanang | 17,330 | 6,836 | 1,628 | 6,818 | 34 | 8 |

---

## 6. SFT Candidate Impact

| Category | Count |
|----------|-------|
| Total candidates | 16,409 |
| VERIFIED_SOURCE_GROUNDED | 11 |
| HUMAN_REVIEW_REQUIRED | 16,398 |

---

## 7. Human Review Queue

| Priority | Count |
|----------|-------|
| P0 | 99 |
| P1 | 16,379 |
| P2 | 174,560 |
| **Total** | **191,038** |

---

## 8. SFT Readiness Decision

**Status: NOT_READY**

### Criteria Evaluation

| Criterion | Met | Evidence |
|-----------|-----|----------|
| Source-grounded material | YES | 16,409 candidates |
| Distinct knowledge categories | YES | 6 categories with >100 units |
| Teacher attribution | YES | 7 teachers, 227 units |
| Practice explanations | YES | 1,123 explanations |
| STH-specific evidence | NO | 0 verified STH explanations |
| Provenance | YES | All units have provenance |
| Human curatable | YES | 16,409 candidates |

### Reason for NOT_READY

**Insufficient source-grounded material** — Only 11 units classified as VERIFIED_SOURCE_GROUNDED. The remaining 16,398 require human review.

---

## 9. Information Gaps

| Priority | Gap | Evidence Missing | Current Corpus Can Solve | New Source Required | Human Curation Can Solve |
|----------|-----|------------------|-------------------------|---------------------|-------------------------|
| P0 | STH-specific doctrinal interpretation | 0 verified STH doctrinal passages | No | Yes | No |
| P0 | STH-specific practice explanation | 0 verified STH practice explanations | No | Yes | No |
| P1 | STH/Terapanth distinction material | Minimal cross-tradition comparison | Yes | No | Yes |
| P1 | STH lineage/history detailed | 13 ambiguous STH passages | Yes | No | Yes |
| P2 | More practice explanations | 1,123 practice explanation passages | Yes | No | Yes |

---

## 10. Commentary Separation Experiment

### Deterministic Heuristics Tested

1. **Language transitions:** Hindi/English boundaries reliable for separating translation from commentary
2. **Heading markers:** Chapter/section headings present in all Amarmuni sources
3. **Sutra length:** Original sutras tend to be shorter, formulaic sentences
4. **Commentary markers:** Words like "vivaran", "vyakhya", "arth" indicate commentary

### Assessment

- **Macro-level separation (chapter/section):** RELIABLE
- **Line-level separation (sentence):** UNRELIABLE
- **Recommendation:** Mark Amarmuni commentary attribution as "requires review" for SFT provenance

---

## 11. Files Created

- `data/training/sthanakavasi_review_queue_v1.jsonl`
- `data/training/sft_verified_candidate_pool_v1.jsonl`
- `data/reports/task39_knowledge_mining.md`
- `data/reports/task39_knowledge_mining_metrics.json`
- `data/reports/task39_sft_readiness.json`
- `data/reports/task39_information_gaps.json`

---

## 12. Tests

375 passed, 2 pre-existing errors, 1 skip. No regressions.

---

## 13. Recommended Next Engineering Task

**Task 40:** Focus on acquiring STH-specific sources that can fill the P0 gaps:

1. **STH-specific doctrinal interpretation** — Need sources with genuine STH interpretive content
2. **STH-specific practice explanation** — Need sources explaining STH-specific practices

The current corpus has strong generic Jain and Agam content but lacks genuine STH-specific material.

**HARD STOP.** No model training, no synthetic data, no architecture changes.

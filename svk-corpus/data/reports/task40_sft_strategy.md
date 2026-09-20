# Task 40: SFT Strategy Checkpoint + Human Curation Framework

**Date:** 2026-09-20
**Status:** COMPLETE

---

## 1. Analysis of 11 Verified Examples

| # | Source | Layer | Practice | Teacher | Lineage |
|---|--------|-------|----------|---------|---------|
| 1 | SVK-2022 | PRACTICE | Kayotsarga | Amarmuni | - |
| 2 | SVK-2022 | PRACTICE | Avashyaka | Amarmuni | - |
| 3 | SVK-2022 | PRACTICE | Avashyaka | Amarmuni | - |
| 4 | SVK-2022 | PRACTICE | Avashyaka | Amarmuni | - |
| 5 | SVK-2024 | PRACTICE | Pratikraman | Pravin K Shah | - |
| 6 | SVK-2024 | PRACTICE | Pratikraman | Pravin K Shah | - |
| 7 | SVK-2029 | COMMENTARY | - | Amarmuni | - |
| 8 | SVK-2029 | COMMENTARY | - | Amarmuni | - |
| 9 | SVK-2029 | COMMENTARY | - | Amarmuni | - |
| 10 | SVK-2036 | PRACTICE | Paryushan | Amarmuni | STH |
| 11 | SVK-2036 | PRACTICE | Paryushan | Amarmuni | STH |

**Validity:** All HIGH quality, teacher-attributed, practice-associated.

**Issues:** No language field, no unit_id, no provenance, raw text with OCR artifacts.

---

## 2. SFT Example Contract

See `data/training/sft_curation_contract_v1.json`

Required: example_id, messages, question_type, source_ids, source_units, citations, tradition, lineage, knowledge_layer, content_role, teacher, agam_id, practice, language, verification_status, reviewer_status.

---

## 3. SFT Categories

| Code | Category | Current Evidence |
|------|----------|------------------|
| A | STHANAKAVASI_DOCTRINE | INSUFFICIENT |
| B | AGAM_EXPLANATION | AVAILABLE |
| C | PRACTICE_EXPLANATION | AVAILABLE |
| D | TEACHER_ATTRIBUTION | AVAILABLE |
| E | PRAKRIT_TERM_EXPLANATION | POSSIBLE |
| F | TRADITION_DISTINCTION | LIMITED |
| G | HISTORY_LINEAGE | POSSIBLE |
| H | SOURCE_CITATION | AVAILABLE |
| I | ABSTENTION | AVAILABLE |
| J | GENERAL_JAIN | AVAILABLE |

---

## 4. Curation Rules

See `data/training/sft_curation_guidelines_v1.md`

12 strict rules including: source grounding, no model memory, no silent tradition merging, evidence-based abstention, teacher attribution with provenance, STH classification requires evidence.

---

## 5. Stage A/B/C Targets

| Stage | Target | Categories | Sources | Teachers | Timeline |
|-------|--------|------------|---------|----------|----------|
| A | 50-100 | 10 categories | 5+ | 3+ | 2-4 weeks |
| B | 250-500 | 10 categories | 10+ | 5+ | 6-8 weeks |
| C | 1000+ | 10 categories | 20+ | 8+ | 3-6 months |

---

## 6. Current Corpus Capability for Stage A

| Category | Status | Evidence |
|----------|--------|----------|
| STHANAKAVASI_DOCTRINE | INSUFFICIENT | 0 verified |
| AGAM_EXPLANATION | AVAILABLE | 78K+ units |
| PRACTICE_EXPLANATION | AVAILABLE | 1,123 units |
| TEACHER_ATTRIBUTION | AVAILABLE | 227 units |
| PRAKRIT_TERM_EXPLANATION | POSSIBLE | Need human review |
| TRADITION_DISTINCTION | LIMITED | 5 cross-tradition |
| HISTORY_LINEAGE | POSSIBLE | Need human review |
| SOURCE_CITATION | AVAILABLE | Strong provenance |
| ABSTENTION | AVAILABLE | Can construct |
| GENERAL_JAIN | AVAILABLE | 20K+ units |

**Stage A Capability:** PARTIALLY_CAPABLE

---

## 7. Source-to-SFT Map

| Source | Usable Knowledge | SFT Category | Example Potential | Provenance |
|--------|------------------|--------------|-------------------|------------|
| SVK-2022 | Practice explanations | C, D | HIGH | HIGH |
| SVK-2024 | Pratikraman | C, D | HIGH | HIGH |
| SVK-2029 | Commentary | B, D | HIGH | HIGH |
| SVK-2030-2036 | Agam commentary | B, C, D | HIGH | HIGH |
| SVK-2037 | STH references | A, F, G | MEDIUM | HIGH |

---

## 8. Curation Tooling

**Workflow:** Source passage → Proposed question → Human answer → Citation → Validation → Approval

**Format:** JSONL with strict schema (see contract)

---

## 9. Evaluation Separation

**Training SFT data ≠ JainBench evaluation data**

- Evaluation examples held out
- No source leakage
- 20% minimum held out for evaluation

---

## 10. Decision

**CURATION_WITH_LIMITED_SCOPE**

**Categories that can start:**
- B: AGAM_EXPLANATION (strong evidence)
- C: PRACTICE_EXPLANATION (strong evidence)
- D: TEACHER_ATTRIBUTION (strong evidence)
- H: SOURCE_CITATION (strong evidence)
- I: ABSTENTION (can construct)
- J: GENERAL_JAIN (strong evidence)

**Categories requiring more sources:**
- A: STHANAKAVASI_DOCTRINE (0 verified)
- F: TRADITION_DISTINCTION (minimal evidence)

---

## 11. Tests

375 passed, 2 pre-existing errors, 1 skip. No regressions.

---

## 12. Files Created

- `data/training/sft_curation_contract_v1.json`
- `data/training/sft_curation_guidelines_v1.md`
- `data/training/sft_stage_targets_v1.json`
- `data/reports/task40_sft_strategy.md`
- `data/reports/task40_sft_strategy_metrics.json`

---

## 13. Recommended Next Task

**Task 41:** Begin human curation of Stage A examples in categories B, C, D, H, I, J.

**HARD STOP.** No model training, no synthetic data, no architecture changes.

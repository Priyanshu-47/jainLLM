# Task 49: Domain Corpus Audit

**Date:** 2026-09-21

---

## 1. Corpus Statistics

### Training Corpus

| Metric | Value |
|--------|-------|
| Units | 97,763 |
| Estimated Tokens | ~5.16M |
| Unique Sources | 39 |

### RAG Corpus

| Metric | Value |
|--------|-------|
| Units | 164,238 |
| Estimated Tokens | ~5.41M |
| Unique Sources | 40 |

### Combined

| Metric | Value |
|--------|-------|
| Total Tokens | ~10.57M |

---

## 2. Language Distribution

| Language | Status |
|----------|--------|
| Hindi | Present |
| English | Present |
| Mixed | Present |

---

## 3. Content Types

| Type | Available |
|------|-----------|
| Canonical texts | Yes (SVK-2022, 2023, 2025, 2026, 2029) |
| Commentary | Yes |
| Practice guides | Yes (SVK-2024) |
| Historical | Yes (SVK-1001, 0038, 2027) |
| Educational | Yes (SVK-0026) |

---

## 4. Sthanakavasi Content

| Metric | Value |
|--------|-------|
| VERIFIED_STHANAKAVASI | 91 units |
| PROBABLE_STHANAKAVASI | 85,222 units |
| GENERIC_SVETAMBARA | 105,720 units |

---

## 5. Training Strategy Readiness

**DOMAIN_ADAPTATION_STATUS = PROMISING**

Combined corpus of ~10.57M tokens is sufficient for domain adaptation experiments.

---

## 6. Recommendation

The domain corpus is ready for:
1. Domain-adaptive continued pretraining
2. Vocabulary expansion
3. Terminology understanding
4. Multilingual capability

**Do NOT make training decision yet.** This is evidence for the decision.

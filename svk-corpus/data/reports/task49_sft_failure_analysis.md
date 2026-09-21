# Task 49: SFT Failure Analysis

**Date:** 2026-09-21

---

## 1. Current SFT Data Status

| Dataset | Count |
|---------|-------|
| Gold v3 (HUMAN_VERIFIED) | 2 |
| Remaining v3 | 10 |
| Revision candidates | 12 |

---

## 2. Failure Patterns

### 2.1 Task 45 Failures (12 examples)

All 12 examples received REVISE decisions.

**Key feedback:**
- "Same again its just giving the citation and sources not the explanation of question"
- "we should not focus on questions like what maarmuni they should not be considered its Lord Mahaveer the source of truth"

**Root causes:**
1. Teacher-centric questions
2. Citation-only answers
3. No actual explanation

### 2.2 Task 47 Failures (12 rebuilt examples)

| Decision | Count |
|----------|-------|
| APPROVE | 2 |
| REVISE | 7 |
| REJECT | 3 |

**Key feedback:**
- "answer is most of correct but misaligned with questions"
- "need explanation general language and it will be increase based on further training"
- "language misconfig", "not understandable"

**Root causes:**
1. Question-answer misalignment
2. Language quality issues
3. Explanation depth insufficient

---

## 3. Common Failure Categories

| Category | Count |
|----------|-------|
| QUESTION_ANSWER_ALIGNMENT | 6 |
| LANGUAGE | 5 |
| EXPLANATION_DEPTH | 5 |
| OTHER | 11 |

---

## 4. Lessons Learned

1. **Do not make teachers the question focus** unless specifically about attribution
2. **Answers must explain concepts**, not just cite sources
3. **Language must be understandable** to modern readers
4. **Question and answer must be aligned** on the same concept
5. **SFT examples teach behavior**, not just knowledge
6. **Source grounding is essential**, but citation alone is insufficient

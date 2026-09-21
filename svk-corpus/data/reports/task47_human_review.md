# Task 47: Human Review of Rebuilt SFT Candidates

**Date:** 2026-09-21
**Status:** REVIEW_INCOMPLETE

---

## 1. Current Status

| Metric | Value |
|--------|-------|
| Total candidates | 12 |
| Reviewed | 0 |
| Pending | 12 |
| APPROVE | 0 |
| REVISE | 0 |
| REJECT | 0 |

**TASK47_STATUS = REVIEW_INCOMPLETE**

---

## 2. Review Infrastructure

Created Task 47 review server:

```bash
cd /home/azureuser/jainLLM/svk-corpus/tools
python3 sft_review_server_task47.py
```

- **URL:** http://localhost:8081
- **Dashboard:** http://localhost:8081/dashboard
- Separate from Task 45 review (port 8080)
- Loads Task 46 rebuilt candidates
- Saves to separate review output file

---

## 3. Review Criteria

### Question Quality
- PASS: Asks about Jain concept, practice, teaching, terminology
- FAIL: Teacher-centric or source-centric question

### Explanation Quality
- PASS: Answer genuinely explains the concept
- FAIL: Answer primarily gives citations or metadata

### Source Grounding
- PASS: Explanation traceable to source material
- FAIL: Introduces unsupported doctrine

### Doctrinal Attribution
- PASS: Authority represented correctly
- FAIL: Modern teacher treated as Mahavira, or commentary treated as canonical

### Language Quality
- PASS: Understandable to modern reader
- FAIL: OCR artifacts, citation dumps, unclear

### Overall SFT Value
- "Would this teach the desired LLM behavior?"

---

## 4. Decision Rules

### APPROVE
- Question is concept/practice/source focused
- Answer genuinely explains
- Explanation is understandable
- Source grounding valid
- Attribution accurate
- No fabricated doctrine
- Would teach desired behavior

### REVISE
- Concept is good
- Source is valid
- But wording/answer needs human correction

### REJECT
- Source doesn't support question/answer
- Unsupported doctrine
- Wrong attribution
- Too ambiguous
- Insufficient source quality

---

## 5. Files Created

- `tools/sft_review_server_task47.py` — Review server
- `data/training/sft_revision_human_review_v1.jsonl` — Review output (empty)
- `data/reports/task47_human_review.md` — This report

---

## 6. How to Run Review Server

```bash
cd /home/azureuser/jainLLM/svk-corpus/tools
python3 sft_review_server_task47.py
```

Then open http://localhost:8081 in a browser.

---

## 7. After Review

When review is complete, run:

```bash
cd /home/azureuser/jainLLM/svk-corpus
python3 tools/sft_gold_generator_task47.py
```

This will:
- Process Task 47 review results
- Create final gold dataset from APPROVE decisions
- Mark as HUMAN_VERIFIED

---

## 8. Tests

375 passed, 2 pre-existing errors, 1 skip. No regressions.

---

## 9. Hard Stop

**NO MODEL TRAINING**
**NO MODEL SELECTION**
**NO NEW SOURCE ACQUISITION**
**NO SYNTHETIC KNOWLEDGE**

---

## 10. Next Phase Gate

When APPROVED_COUNT >= 8:

**NEXT_GATE = READY_FOR_GOLD_DATASET_FINALIZATION**

When APPROVED_COUNT < 8:

**NEXT_GATE = NEED_MORE_SFT_CURATED_EXAMPLES**

---

## 11. Important Notes

1. **Do NOT assume Task 46 candidates are correct** — They need human validation
2. **Do NOT create HUMAN_VERIFIED records yet** — Wait for review completion
3. **Do NOT generate final gold dataset in this task** — Separate task
4. **Do NOT select a model** — Separate task
5. **Task 45 review data is preserved** — Separate files

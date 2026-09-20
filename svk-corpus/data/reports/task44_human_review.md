# Task 44: Human Review Interface + Final Gold Dataset

**Date:** 2026-09-20
**Status:** AWAITING_HUMAN_REVIEW

---

## 1. Objective

Create a practical human-review workflow for 12 gold examples.

---

## 2. Current Status

| Metric | Value |
|--------|-------|
| Gold candidates | 12 |
| Reviewed | 0 |
| Pending | 12 |
| Approved | 0 |
| Revised | 0 |
| Rejected | 0 |
| HUMAN_VERIFIED | 0 |

**Status: AWAITING_HUMAN_REVIEW**

---

## 3. Review Interface

Created a lightweight local web UI:

```
python tools/sft_review_server.py
```

- **URL:** http://localhost:8080
- **Dashboard:** http://localhost:8080/dashboard
- No external dependencies
- No authentication required
- Runs on localhost

---

## 4. Review Workflow

1. Open http://localhost:8080
2. View each example (question, answer, source, metadata)
3. Read review rules
4. Select APPROVE / REVISE / REJECT
5. Add notes and required changes
6. Check verification boxes
7. Submit review

---

## 5. Review Rules

### APPROVE if:
1. Cited passage supports the answer
2. No factual claim exceeds source evidence
3. Citation points to correct source/unit
4. Teacher attribution supported
5. Agam attribution supported
6. Practice attribution supported
7. Sthanakavasi claim supported
8. No generic Jain claim incorrectly labeled STH
9. No metadata treated as doctrine
10. Answer is clear and faithful to source

### REVISE if:
- Source supports concept but wording inaccurate
- Answer needs narrowing
- Citation correct but answer needs correction
- Metadata/provenance needs correction

### REJECT if:
- Source does not support answer
- Answer depends on outside knowledge
- Source attribution unreliable
- STH claim unsupported
- Citation wrong
- Passage unusable
- Example fundamentally redundant

---

## 6. Review Storage

Created: `data/training/sft_human_review_results_v1.jsonl`

Each record contains:
- example_id
- reviewer
- review_timestamp
- decision (APPROVE/REVISE/REJECT)
- original_example
- review_notes
- required_changes
- source_verified
- answer_grounded
- citation_verified
- teacher_verified
- agam_verified
- practice_verified
- sthanakavasi_verified
- provenance_verified

---

## 7. Final Gold Dataset

Created: `data/training/sft_gold_v2.jsonl`

Rules:
- Only APPROVE examples enter final gold
- review_status = HUMAN_VERIFIED (only from human review)
- HUMAN_VERIFIED cannot be produced by automated pipeline

---

## 8. Files Created

- `tools/sft_review_server.py` — Review web server
- `tools/sft_review_html.py` — HTML templates
- `tools/sft_gold_generator.py` — Final gold generator
- `data/training/sft_human_review_results_v1.jsonl` — Review results (empty)
- `data/reports/task44_human_review.md` — This report

---

## 9. Tests

375 passed, 2 pre-existing errors, 1 skip. No regressions.

---

## 10. Next Phase Readiness

**Status: AWAITING_HUMAN_REVIEW**

The gold dataset is not ready for model selection until human review is complete.

When 8+ examples are HUMAN_VERIFIED, the project may proceed to:
- Model selection and baseline planning

---

## 11. Hard Stop

**NO MODEL TRAINING**
**NO MODEL SELECTION**
**NO NEW SOURCE ACQUISITION**
**NO SYNTHETIC KNOWLEDGE**

---

## 12. How to Run Review Server

```bash
cd /home/azureuser/jainLLM/svk-corpus/tools
python3 sft_review_server.py
```

Then open http://localhost:8080 in a browser.

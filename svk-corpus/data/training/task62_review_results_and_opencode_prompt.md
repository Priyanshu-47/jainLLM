# Task 62 — SFT Human-Review Results & OpenCode Handoff

Date: 2026-10-01

## Scope

Reviewed the supplied Task 62 review queues as a single candidate pool:

- Queue A — SOURCE_ATTRIBUTION: 39 candidates
- Queue B — STHANAKAVASI_DISTINCTION: 20 candidates
- Queue C — ABSTENTION: 22 candidates
- Queue D — mixed: 168 candidates across 6 parts
- Queue R — re-adjudication: 3 candidates

Total: **252 candidate records**

The review standard is the Task 62 rubric:
1. qa_alignment
2. source_grounding
3. attribution
4. sect_distinction
5. knowledge_layer
6. abstention
7. practice
8. language
9. language_quality
10. no_fabrication
11. pedagogy

High-priority failures are source grounding, attribution, and fabrication.

## Review findings

### Queue A — Source attribution

Assessment: **generally the strongest queue**.

Keep/revise examples that directly answer metadata questions from explicit manifest/catalog evidence. Examples include author, publisher, source type, tradition/sect classification, and provenance questions.

Typical revision:
- keep the answer tied to the manifest/catalog wording;
- distinguish a manifest classification from a doctrinal judgment;
- do not infer missing publication years or authors;
- do not let stale rights metadata override the project's recorded permission evidence.

Do not turn metadata into theological claims.

### Queue B — Sthānakavāsī distinction

Assessment: **do not directly approve the current generated answers as gold**.

The major failure is that many answers quote only a short fragment instead of answering the actual question.

Example:
T61-CAND-0041 asks about Chedagrantha differences, while its answer only quotes “all Svetambara and Sthanakavasi practically agree.” The surrounding evidence is needed to explain what the source actually says.

Example:
T61-CAND-0043 asks about Mūlagrantha, but the answer stops at “Of these four the Sthanakavasi accept only the first.” The surrounding source provides the actual distinction.

Decision pattern:
- evidence useful + answer incomplete => REVISE
- wrong sect/tradition attribution => REJECT
- evidence itself does not establish the asked distinction => REJECT or REVISE into an evidence-limited answer
- never convert an old secondary source into an unconditional universal doctrinal claim.

### Queue C — Abstention

Assessment: **valuable queue and should be preserved where the evidence gap is genuine**.

Good pattern:
- explicitly state that the supplied corpus/source does not establish the requested fact;
- do not invent dates, founders, doctrinal positions, or sect claims;
- optionally identify what source/evidence would be needed.

However, remove irrelevant quotations from abstention answers. The abstention must be supported by an evidence check, not by an unrelated passage.

### Queue D — Mixed

Assessment: **highly mixed; substantial REVISE/REJECT population**.

Common REVISE cases:
- answer is only an OCR/source fragment;
- question is broader than the cited evidence;
- answer needs explicit attribution;
- canonical text, commentary, translation, or secondary scholarship is blurred;
- Gujarati/Prakrit OCR needs cleanup before it is usable as training text.

Common REJECT cases:
- evidence is from the wrong subject/tradition;
- answer does not address the question at all;
- OCR is too corrupted to recover reliably;
- source fragment is being presented as an explanation when it does not contain one;
- fabricated or unsupported attribution.

Examples:
- T61-CAND-0181 contains visibly corrupted Gujarati OCR and should not be directly promoted to SFT.
- T61-CAND-0082-type cases where evidence concerns a different tradition/topic should be rejected rather than “fixed” using outside knowledge.
- T61-CAND-0214 and similar rows provide only truncated source fragments about Tīrthaṅkaras; these need a real answer or should be rejected.

### Queue R — Re-adjudication

The three supplied re-adjudication examples should be **REJECTED**:

1. T61-RECON-SFT-SEED-CAND-SVK-2025-SVK-2025
   - malformed/nonsensical answer.
2. T61-RECON-SFT-SEED-CAND-SVK-2029-SVK-2029
   - question/answer mismatch.
3. T61-RECON-SFT-SEED-CAND-SVK-0038-unknown
   - malformed/meaningless question-answer pair.

Do not carry these into the SFT gold set.

## Important project-level conclusion

Do **not** convert all 252 candidates into gold data.

The desired SFT example should look like:

**Question → evidence → correctly scoped answer → attribution → knowledge-layer/sect boundary**

not:

**keyword → OCR fragment → “According to source…”**

This is particularly important because Task 60 already showed regressions in:
- factual error rate,
- unsupported source-attributed claims,
- sect confusion,
- degenerate responses,
- abstention behavior.

SFT should target those failure modes rather than teach the model to reproduce retrieval fragments.

## OpenCode task

Copy the following prompt to OpenCode.

---

# TASK 63 — CONSOLIDATE TASK 62 HUMAN REVIEW INTO SFT GOLD V4

## OBJECTIVE

Take the complete Task 62 human-review candidate pool and convert it into a **single auditable adjudication dataset**.

Do NOT train a model.

Do NOT change the domain corpus.

Do NOT silently rewrite previously HUMAN_VERIFIED examples.

Do NOT invent factual corrections from general model knowledge.

The source evidence and existing project provenance are authoritative.

## INPUTS

Use the existing Task 62 review files in the repository:

- Queue A
- Queue B
- Queue C
- Queue D parts 1–6
- Queue R / re-adjudication

Also inspect the existing:
- SFT schemas
- provenance/source registry
- Task 61 reconciliation ledger
- existing HUMAN_VERIFIED records
- `sft_candidates_v2.jsonl`
- previous SFT gold versions
- Task 60 evaluation report

First locate the exact filenames instead of assuming paths.

## REQUIRED WORK

### 1. Inventory

Build a deterministic inventory of every Task 62 candidate.

For every candidate retain:

- review_id
- source candidate ID
- queue
- category
- question
- original answer
- evidence
- source
- provenance
- existing split
- rights status
- prior review status if present

Verify the expected pool size and report discrepancies.

### 2. Apply the review decisions

For each candidate assign exactly one:

- APPROVE
- REVISE
- REJECT

Use the Task 62 rubric:

- qa_alignment
- source_grounding
- attribution
- sect_distinction
- knowledge_layer
- abstention
- practice
- language
- language_quality
- no_fabrication
- pedagogy

Rules:

APPROVE:
- all HIGH-priority criteria pass;
- answer actually answers the question;
- evidence supports the claims;
- attribution is correct;
- no fabricated information;
- language is usable;
- no material unresolved issue.

REVISE:
- underlying candidate is potentially useful;
- problem is fixable without inventing facts;
- produce a revised answer only when the supplied evidence supports the revision.

REJECT:
- wrong source/topic/tradition;
- fabricated claim;
- wrong attribution;
- unusable OCR;
- malformed question;
- answer cannot be repaired without adding unsupported knowledge;
- duplicate with no distinct training value.

### 3. Special rule for source fragments

Never treat a quotation fragment as a complete answer unless it actually answers the question.

If a source contains enough surrounding evidence to construct a supported answer, mark REVISE and build the answer from that evidence.

If the source does not support the requested answer, REJECT or convert to an explicit abstention example only when that abstention itself is supported by the evidence.

### 4. Sect isolation

Be strict.

Do not turn:
- a Sthānakavāsī-specific statement into a universal Jain statement;
- a Śvetāmbara statement into a Sthānakavāsī statement;
- a secondary scholar's description into canonical doctrine;
- commentary into canonical teaching;
- Digambara/Terapanthi/Mūrtipūjaka material into Sthānakavāsī material.

If the source itself is historical/secondary, preserve that framing.

### 5. Attribution

Preserve:

- canonical source vs commentator;
- teacher/author vs Mahāvīra;
- source author vs publisher;
- catalog metadata vs doctrinal claim.

Do not attribute a commentator's interpretation to Mahāvīra or to Jain canonical scripture.

### 6. Abstention

Preserve strong abstention examples.

An abstention should say, in substance:

> The available evidence does not establish X, so I should not assert X as fact.

Do not manufacture an answer merely because the question sounds answerable.

### 7. Language/OCR

Do not silently repair uncertain Prakrit/Sanskrit/Gujarati terminology from general knowledge.

For clearly corrupted OCR:
- REJECT if meaning cannot be recovered reliably;
- REVISE only if the supplied surrounding evidence unambiguously supports the corrected text.

### 8. Deduplication

After adjudication, detect:
- exact duplicate questions;
- near-duplicate questions;
- same evidence + same answer;
- same training behavior expressed repeatedly.

Keep the strongest representative.

Do not remove distinct examples merely because they share a source.

## OUTPUT FILES

Create:

```text
data/evaluation/task62_adjudication_v1.jsonl
data/evaluation/task62_revise_v1.jsonl
data/evaluation/task62_reject_v1.jsonl
data/evaluation/task62_approve_v1.jsonl

data/reports/task62_human_review_consolidated.md
data/reports/task62_human_review_stats.json
```

If the project already has a canonical review/output directory, follow the existing convention instead of creating a conflicting structure.

## APPROVED RECORD RULE

An APPROVE record is not automatically allowed into training.

Create:

```text
data/training/sft_gold_v4_candidates.jsonl
```

containing only candidates that:

1. passed adjudication;
2. passed schema validation;
3. passed provenance validation;
4. passed rights validation;
5. passed duplicate/near-duplicate checks;
6. contain an answer rather than a source fragment;
7. contain no unsupported factual claims.

Every record must remain traceable to its original candidate and evidence.

## REVISE RECORD RULE

For every REVISE candidate include:

```json
{
  "review_id": "...",
  "decision": "REVISE",
  "failed_criteria": [],
  "original_question": "...",
  "original_answer": "...",
  "evidence": "...",
  "revised_answer": "...",
  "revision_basis": "...",
  "source_id": "...",
  "human_review_required": true
}
```

Do not mark a revised record HUMAN_VERIFIED.

## REJECT RECORD RULE

Keep rejected records for auditability.

Never delete them.

Include:

```json
{
  "review_id": "...",
  "decision": "REJECT",
  "failed_criteria": [],
  "reason": "...",
  "source_id": "..."
}
```

## HUMAN VERIFICATION

The resulting files are an adjudication layer, not automatic human approval.

Do not change:

```text
human_verified = true
```

unless that status already exists from the project's prior human review.

Newly revised/approved candidates must remain:

```text
HUMAN_REVIEW_REQUIRED
```

unless an existing explicit human-review record says otherwise.

## VALIDATION

Run all existing SFT schema/provenance tests.

Add tests for:

- every candidate has exactly one decision;
- no candidate disappears;
- no duplicate review IDs;
- APPROVE/REVISE/REJECT counts sum to total;
- rejected candidates are retained;
- revised answers have revision_basis;
- no raw URLs inside answer text if the schema prohibits them;
- no unsupported source attribution;
- no cross-sect contamination;
- no HUMAN_VERIFIED status is fabricated;
- gold candidates are traceable to evidence.

## REPORT

`data/reports/task62_human_review_consolidated.md` must contain:

1. total candidates
2. counts by queue
3. APPROVE / REVISE / REJECT
4. counts by category
5. failed-criterion frequencies
6. rejection reasons
7. revision patterns
8. duplicate/near-duplicate counts
9. resulting SFT-gold candidate count
10. HUMAN_VERIFIED count before and after
11. rights/provenance blockers
12. examples of each major failure pattern
13. explicit limitations
14. confirmation that no training was performed

## CRITICAL HARD STOP

STOP after producing the adjudication and validation artifacts.

Do NOT:

- train SFT;
- launch Kaggle;
- download a model;
- modify DAPT;
- modify the domain corpus;
- merge LoRA adapters;
- create a new model checkpoint;
- publish anything.

Return only:

```text
TASK 63 COMPLETE

Candidates:
APPROVE = X
REVISE = X
REJECT = X

SFT gold candidates = X
HUMAN_VERIFIED = X
HUMAN_REVIEW_REQUIRED = X

Validation:
PASS/FAIL

Files created:
...

Training started:
NO

Hard stop:
YES
```


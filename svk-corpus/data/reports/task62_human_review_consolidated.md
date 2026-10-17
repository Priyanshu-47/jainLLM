# Task 62 human review consolidated - adjudication report (Task 63)


- Generated: `2026-10-01T07:10:12.163688+00:00`
- Adjudication layer: `task63_adjudication_layer` (evidence-based rules over the supplied candidate evidence; not a human reviewer)
- Input pool: `data/training/sft_task62_review_queue_v1.jsonl` (252 rows)
- Adjudication file: `data/evaluation/task62_adjudication_v1.jsonl`
- Machine-readable stats: `data/reports/task62_human_review_stats.json`
- Human review status: **every record remains `HUMAN_REVIEW_REQUIRED` / `human_verified = false`**

## 1. Total candidates


**252 candidates**, exactly the expected Task 62 pool size (expected 252, observed 252, discrepancy 0).

| inventory | value |
|---|---|
| review queue rows | 252 |
| unique review IDs | 252 |
| answer shapes | abstention = 22, concept = 3, fragment = 168, manifest = 59 |
| distinct source IDs | 40 |
| rights cleared | 252 / 252 |
| provenance complete | 252 / 252 |

The queue was read only; no candidate source record was modified.

## 2. Counts by queue


| queue | size | APPROVE | REVISE | REJECT |
|---|---|---|---|---|
| A | 39 | 37 | 2 | 0 |
| B | 20 | 0 | 13 | 7 |
| C | 22 | 7 | 15 | 0 |
| D | 168 | 10 | 74 | 84 |
| R | 3 | 0 | 0 | 3 |
| **total** | **252** | **54** | **104** | **94** |

Queue guidance from the Task 62 review notes, and how it landed:

- **Queue A** - Strongest queue: keep or lightly revise; the answers are direct quotations with intact attributions. Result: APPROVE = 37, REVISE = 2.
- **Queue B** - Fragment failures: REVISE when the source supports a full answer (named: T61-CAND-0041, T61-CAND-0043), REJECT wrong sect attribution and rows with no source text. Result: REJECT = 7, REVISE = 13.
- **Queue C** - Preserve strong abstention examples; remove irrelevant quotations from abstention answers. Result: APPROVE = 7, REVISE = 15.
- **Queue D** - Highly mixed regression pool; substantial REVISE and REJECT, including the corrupt-OCR dictionary rows. Result: APPROVE = 10, REJECT = 84, REVISE = 74.
- **Queue R** - Reconciliation residuals: the review notes require all three to be rejected. Result: REJECT = 3.

## 3. APPROVE / REVISE / REJECT


| decision | count | share |
|---|---|---|
| APPROVE | 54 | 21.4% |
| REVISE | 104 | 41.3% |
| REJECT | 94 | 37.3% |
| **total** | **252** | 100% |

Decision rules applied, in safety order:

1. **APPROVE** only when every high-priority rubric criterion is satisfied from the supplied evidence: the answer answers the question, the evidence supports each claim, attribution matches the recorded source, nothing was fabricated, and the language is usable.
2. **REVISE** when the candidate is worth keeping and the repair is possible *without inventing facts* - a bracket repair, an added manifest field the question asked for, a rebuilt sentence from a supplied source passage, or removal of a quotation that does not bear on an otherwise sound abstention.
3. **REJECT** when the answer cannot be repaired from the supplied evidence alone: wrong source or tradition, unusable OCR, no source text, an answer that does not answer the question, or a duplicate with no distinct training value.

Named candidates called out in the Task 62 review notes:

| review_id | decision | why it was called out |
|---|---|---|
| T61-CAND-0041 | REVISE | Queue B fragment with a usable source sentence |
| T61-CAND-0043 | REVISE | Queue B fragment with a usable source sentence |
| T61-CAND-0051 | REVISE | Queue B fragment with a usable source sentence |
| T61-CAND-0053 | REVISE | Queue B fragment with a usable source sentence |
| T61-CAND-0082 | REJECT | wrong-tradition quotation (Pāśupata/Śaiva material answering a Jain question) |
| T61-CAND-0181 | REJECT | corrupt OCR dictionary row |
| T61-CAND-0214 | REVISE | needed a real answer rather than a fragment |
| T61-CAND-0060 | REJECT | evidence quote only, no source text |
| T61-CAND-0102 | REJECT | evidence quote only, no source text |
| T61-CAND-0117 | REJECT | evidence quote only, no source text |

All three Queue R reconciliation rows were rejected, as the review notes require.

## 4. Counts by category


| category | n | APPROVE | REVISE | REJECT |
|---|---|---|---|---|
| ABSTENTION/INSUFFICIENT_EVIDENCE | 22 | 7 | 15 | 0 |
| AGAM_EXPLANATION | 1 | 0 | 0 | 1 |
| AGAM_GROUNDED | 13 | 0 | 10 | 3 |
| CANONICAL_VS_COMMENTARY | 12 | 10 | 2 | 0 |
| CONCEPT_EXPLANATION | 2 | 0 | 0 | 2 |
| GENERAL_JAIN_CONCEPT | 12 | 0 | 5 | 7 |
| GUJARATI | 20 | 0 | 3 | 17 |
| HINDI | 30 | 0 | 14 | 16 |
| PRACTICE_EXPLANATION | 29 | 0 | 13 | 16 |
| PRAKRIT | 25 | 0 | 14 | 11 |
| SANSKRIT | 12 | 0 | 7 | 5 |
| SOURCE_ATTRIBUTION | 39 | 37 | 2 | 0 |
| STHANAKAVASI_DISTINCTION | 20 | 0 | 13 | 7 |
| STHANAKAVASI_TERMINOLOGY | 15 | 0 | 6 | 9 |

Answer shape, which drives which decision rule fires:

| shape | n | APPROVE | REVISE | REJECT |
|---|---|---|---|---|
| abstention | 22 | 7 | 15 | 0 |
| concept | 3 | 0 | 0 | 3 |
| fragment | 168 | 0 | 77 | 91 |
| manifest | 59 | 47 | 12 | 0 |

The `manifest` shape covers catalog/metadata answers whose every claim is checked against the supplied manifest row; `fragment` is a source quotation used as an answer; `abstention` is an explicit evidence-gap answer; `concept` is a boilerplate wrapper. No `fragment`-shaped candidate was approved: a quotation fragment is never treated as a complete answer.

## 5. Failed-criterion frequencies


A candidate can fail more than one criterion; APPROVE rows fail none.

| failed criterion | candidates |
|---|---|
| source_grounding | 184 |
| qa_alignment | 163 |
| language_quality | 34 |
| language | 28 |
| sect_distinction | 19 |
| no_fabrication | 3 |
| attribution | 1 |

`qa_alignment` and `source_grounding` dominate because they are the two gates that decide whether the supplied evidence can carry the answer at all. `language` / `language_quality` are the OCR gates, and `sect_distinction` marks rows where the proposed answer would blur a Sthanakavasi-specific statement into a universal one. `attribution` appears once, for the wrong-tradition quotation. The `knowledge_layer` and `abstention` criteria did not have to fire: the canonical-versus-commentary rows failed on alignment first, and every abstention judged sound was left intact.

## 6. Rejection reasons


| rejection reason | count | example review IDs |
|---|---|---|
| source is on topic but has no complete usable sentence | 53 | `T61-CAND-0044`, `T61-CAND-0046`, `T61-CAND-0048`, `T61-CAND-0052` |
| no source text supplied with the candidate | 3 | `T61-CAND-0060`, `T61-CAND-0102`, `T61-CAND-0117` |
| answer does not answer the question (boilerplate wrapper) | 3 | `T61-RECON-SFT-SEED-CAND-SVK-2025-SVK-2025`, `T61-RECON-SFT-SEED-CAND-SVK-2029-SVK-2029`, `T61-RECON-SFT-SEED-CAND-SVK-0038-unknown` |
| wrong source/topic/tradition for the question | 5 | `T61-CAND-0080`, `T61-CAND-0081`, `T61-CAND-0082`, `T61-CAND-0083` |
| unusable OCR: meaning cannot be recovered from the source | 28 | `T61-CAND-0084`, `T61-CAND-0113`, `T61-CAND-0114`, `T61-CAND-0163` |
| duplicate with no distinct training value | 2 | `T61-CAND-0125`, `T61-CAND-0126` |

94 candidates were rejected; every one is retained in `data/evaluation/task62_reject_v1.jsonl` with its reason - nothing was deleted.


## 7. Revision patterns


| revision pattern | count |
|---|---|
| manifest wording repair (bracket/truncation) | 12 |
| rebuild a complete answer from the supplied source sentence | 77 |
| drop non-evidentiary quotation, keep the gap statement | 15 |

Revision confidence, i.e. how strongly the supplied source pins down the proposed wording:

| revision confidence | count |
|---|---|
| high | 28 |
| medium | 67 |
| low | 9 |

`high` = the question's subject is matched by at least two exact source tokens (or the revision is a mechanical manifest-field insertion); `medium` = one exact token or several partial matches; `low` = a single substring-only match. `low` rows are the ones a human should read first.


One example of each pattern (original answer -> proposed revision):

| pattern | review_id | queue | original answer | revised answer |
|---|---|---|---|---|
| manifest wording repair (bracket/truncation) | T61-CAND-0006 | A | The manifest records Shri Utradhyayan Sutar (Agam Seva) (1920) as PRIMARY CANON (Mulasutra material. Its canon | The manifest records Shri Utradhyayan Sutar (Agam Seva) (1920) as PRIMARY CANON (Mulasutra material. Its canonical status is derived as CANONICAL.) |
| rebuild a complete answer from the supplied source sentence | T61-CAND-0041 | B | On chedagrantha, Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910) states: "but all Svetambara an | According to Notes on Modern Jainism (1910), "Various sects and sub-sects differ very much with regard to the Chedagrantha, Mulagrantha and Payanna, b |
| drop non-evidentiary quotation, keep the gap statement | T61-CAND-0232 | C | What the corpus does say: "They are recruited from all three sei-ts, though their founder was a Sthfinakavasi, | The corpus does not record a founding year for Terapanth, so this question cannot be answered from the available sources. Evidence needed first: a dat |

Every REVISE record carries `revised_answer` **and** `revision_basis` describing exactly what was taken from the supplied evidence. No revised answer introduces a fact that is not in the candidate's own source text, evidence quote, or manifest row.

## 8. Duplicate / near-duplicate counts


| duplicate measure | value |
|---|---|
| exact duplicate questions (normalized) | 0 |
| duplicates that differ only by spacing/punctuation | 2 |
| near-duplicate question pairs (char-trigram Jaccard >= 0.85) | 119 |
| ... of those, pairs inside the same queue | 119 |
| same evidence + same answer groups | 0 |
| near-duplicate pairs where both rows are APPROVE | 0 |
| rows removed from the SFT pool by duplication | 0 |
| rows demoted to REJECT as duplicates | 2 |

Handling:

- Two question pairs were identical once spaces and punctuation are folded (`Ardha Magadhi` vs `Ardhamagadhi`). Both rows in each pair trained the same input to different quotations, so the weaker representative of each pair was REJECTED as *duplicate with no distinct training value* (`T61-CAND-0125` -> kept `T61-CAND-0128`, `T61-CAND-0126` -> kept `T61-CAND-0129`). The full original adjudication is still in the adjudication file under `original_notes`.
- The remaining 119 near-duplicate pairs are annotated on both rows (`near_duplicates` and `near_duplicate_of` fields) and reported here. None of them involves an APPROVE row, so nothing left the SFT pool for this reason.
- Sharing a source is **not** treated as duplication: 40 sources supply many distinct questions and all of them were judged on their own merits.
- Gold candidates are re-checked after the pass: no two gold questions reach Jaccard >= 0.85.

## 9. Resulting SFT-gold candidate count


**54 SFT gold candidates** in `data/training/sft_gold_v4_candidates.jsonl`.

An APPROVE decision is not by itself admission to training. Each candidate had to clear seven gates:

| gate | check |
|---|---|
| 1. passed adjudication | decision = APPROVE |
| 2. schema validation | validates against `data/training/sft_schema_v1.json` |
| 3. provenance validation | source_id, text_id, knowledge layer and religious scope present and consistent |
| 4. rights validation | rights status is `TRAINING_ALLOWED` or `TRAINING_ALLOWED_WITH_PERMISSION_EVIDENCE` |
| 5. duplicate / near-duplicate checks | unique normalized question; no gold pair at Jaccard >= 0.85 |
| 6. answer rather than source fragment | complete, closed answer text (not a truncated quotation) |
| 7. no unsupported factual claims | no raw URL, no raw source ID, attribution traceable to the recorded source, evidence quote or manifest row |

Gate failures: **0**. Gold rows span **38 source IDs**.

| gold category | rows |
|---|---|
| ABSTENTION/INSUFFICIENT_EVIDENCE | 7 |
| CANONICAL_VS_COMMENTARY | 10 |
| SOURCE_ATTRIBUTION | 37 |

Each gold row keeps its traceability block: `example_id`, `provenance.source_id`, `provenance.text_id`, the evidence quote and `review.review_id` pointing back at the adjudication record that approved it.

## 10. HUMAN_VERIFIED count before and after


| measure | count | detail |
|---|---|---|
| before this task | 8 | 8 distinct examples across: data/training/sft_reconciled_v1.jsonl = 8 rows, data/training/sft_seed_v1.jsonl = 6 rows |
| after this task | 8 | unchanged |
| newly marked HUMAN_VERIFIED by this task | 0 | 0 |
| records emitted with `HUMAN_REVIEW_REQUIRED` | 252 | all adjudicated candidates |

No file was edited to change a review status. The eight verified examples are the pre-existing rows in `data/training/sft_reconciled_v1.jsonl` (six SFT seed candidates plus two revision examples); `data/training/sft_seed_v1.jsonl` repeats the same six seed candidates.

### Task 51 -> SFT seed discrepancy: RESOLVED


Earlier work recorded a discrepancy between 18 human decision rows in `data/training/sft_task51_human_review_v1.jsonl` and 6 rows in `data/training/sft_seed_v1.jsonl`. It is a counting difference, not a data loss:

- 18 decision rows cover 8 distinct candidates (CAND-SVK-0038 appears 5 times, 2023/2025/2029 three times each).
- 6 candidates received at least one APPROVE, and those 6 are exactly the 6 rows in `sft_seed_v1.jsonl` (set equality in both directions).
- The remaining 2 candidates were never approved, so they never entered the seed.
- Reproduced by `tests/test_task63_adjudication.py::TestPriorStateUntouched::test_task51_review_to_seed_set_is_resolved`.

## 11. Rights / provenance blockers


| rights status | candidates |
|---|---|
| TRAINING_ALLOWED | 227 |
| TRAINING_ALLOWED_WITH_PERMISSION_EVIDENCE | 25 |

| blocker measure | count |
|---|---|
| rights blockers (status outside the cleared set) | 0 |
| provenance blockers (missing text_id) | 0 |
| rows carrying the `MANIFEST_RIGHTS_STALE` flag | 23 |
| ... of those, in the gold candidate set | 12 |

`MANIFEST_RIGHTS_STALE` means the manifest row still says `NEEDS_PERMISSION (R93_RESTRICTIVE_TERMS)` while the permission evidence file reports `PERMISSION_GRANTED`; the queue records `rights_basis = jainqq_permission_evidence:PERMISSION_GRANTED`. Those rows clear the mechanical rights gate on recorded permission evidence, but the stale manifest value should be confirmed by a human before training use - this is listed as a limitation below.

No candidate was rejected on rights grounds.

## 12. Examples of each major failure pattern


### source is on topic but has no complete usable sentence (53)


the passage names the subject but never states the asked fact in a complete sentence, so repairing it would mean importing outside knowledge


| review_id | decision | pattern | question | reason |
|---|---|---|---|---|
| T61-CAND-0044 | REJECT | source is on topic but has no complete usable sentence | How do Sthanakavasi Jains differ from Svetambara Jains on ascetics according to Notes on M | The supplied source passage mentions the subject (sthanakavasi, ascetics) but no complete, readable sentence in it answers the question, so the eviden |
| T61-CAND-0046 | REJECT | source is on topic but has no complete usable sentence | In Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910), what is said about new  | The supplied source passage mentions the subject (new, name, sthanakavasi, digambara) but no complete, readable sentence in it answers the question, s |

### unusable OCR: meaning cannot be recovered from the source (28)


the quoted scan is glyph soup, digit-laden noise or broken conjuncts; the intended wording cannot be recovered from the supplied text alone


| review_id | decision | pattern | question | reason |
|---|---|---|---|---|
| T61-CAND-0084 | REJECT | unusable OCR: meaning cannot be recovered from the source | According to Notes on the Religious Literature of India (1920) (J. N. Farquhar, 1920), how | The quoted source text is visibly corrupted OCR (stray technical characters / broken glyph sequences / line-break hyphens) and the supplied evidence o |
| T61-CAND-0113 | REJECT | unusable OCR: meaning cannot be recovered from the source | How does Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910) explain the term ' | The quoted source text is visibly corrupted OCR (stray technical characters / broken glyph sequences / line-break hyphens) and the supplied evidence o |

### wrong source/topic/tradition for the question (5)


the supplied passage belongs to another topic or another tradition and cannot be quoted back as an answer to the question asked


| review_id | decision | pattern | question | reason |
|---|---|---|---|---|
| T61-CAND-0080 | REJECT | wrong source/topic/tradition for the question | According to Notes on the Religious Literature of India (1920) (J. N. Farquhar, 1920), how | The supplied source passage does not bear on the question: the supplied text (891 characters) contains none of the question's subject terms (subject t |
| T61-CAND-0081 | REJECT | wrong source/topic/tradition for the question | How does Notes on the Religious Literature of India (1920) (J. N. Farquhar, 1920) describe | The supplied source passage does not bear on the question: the supplied text (780 characters) contains none of the question's subject terms (subject t |

### no source text supplied with the candidate (3)


the row carries an evidence quote but no surrounding source text, so no claim in it can be checked


| review_id | decision | pattern | question | reason |
|---|---|---|---|---|
| T61-CAND-0060 | REJECT | no source text supplied with the candidate | What difference between Sthanakavasi and Svetambara practice regarding worship does Agam 2 | The candidate supplies no source text to check it against (evidence quote only: 'zut Acharya Pravartak Shri Amar Muni jjuvAsAmi matthaeNa vedAmi The e |
| T61-CAND-0102 | REJECT | no source text supplied with the candidate | What does Agam 29 Mool 02 Dasvaikalik Sutra Sthanakvasi (Shayyambhavsuri, Amarmuni, Shreec | The candidate supplies no source text to check it against (evidence quote only: 'Dwadashangi is the oldest name and it means--The twelve angas (parts) |

### answer does not answer the question (boilerplate wrapper) (3)


a 'the concept of X is central to Jain philosophy' wrapper around an unrelated quotation; it answers a different question


| review_id | decision | pattern | question | reason |
|---|---|---|---|---|
| T61-RECON-SFT-SEED-CAND-SVK-2025-SVK-2025 | REJECT | answer does not answer the question (boilerplate wrapper) | What does the Sthanang Sutra teach about Allustrated? | The answer is a boilerplate 'The concept of X is central to Jain philosophy' wrapper around an unrelated source quotation; it does not answer the ques |
| T61-RECON-SFT-SEED-CAND-SVK-2029-SVK-2029 | REJECT | answer does not answer the question (boilerplate wrapper) | What is Karma in Jain teaching? | The answer is a boilerplate 'The concept of X is central to Jain philosophy' wrapper around an unrelated source quotation; it does not answer the ques |

### duplicate with no distinct training value (2)


the question is identical, after normalization, to a stronger representative row kept in its place


| review_id | decision | pattern | question | reason |
|---|---|---|---|---|
| T61-CAND-0125 | REJECT | duplicate with no distinct training value | What does Woolner's Introduction To Prakrit (1917) (Alfred C. Woolner, 1917) say about 'Ar | Duplicate with no distinct training value: this question is identical (after normalization) to T61-CAND-0128, which is kept as the strongest represent |
| T61-CAND-0126 | REJECT | duplicate with no distinct training value | In Woolner's Introduction To Prakrit (1917) (Alfred C. Woolner, 1917), how is 'Ardhamagadh | Duplicate with no distinct training value: this question is identical (after normalization) to T61-CAND-0129, which is kept as the strongest represent |

### Named failures recorded by the Task 62 reviewer


| review_id | decision | why it was called out |
|---|---|---|
| T61-CAND-0041 | REVISE | Queue B fragment with a usable source sentence |
| T61-CAND-0043 | REVISE | Queue B fragment with a usable source sentence |
| T61-CAND-0051 | REVISE | Queue B fragment with a usable source sentence |
| T61-CAND-0053 | REVISE | Queue B fragment with a usable source sentence |
| T61-CAND-0082 | REJECT | wrong-tradition quotation (Pāśupata/Śaiva material answering a Jain question) |
| T61-CAND-0181 | REJECT | corrupt OCR dictionary row |
| T61-CAND-0214 | REVISE | needed a real answer rather than a fragment |
| T61-CAND-0060 | REJECT | evidence quote only, no source text |
| T61-CAND-0102 | REJECT | evidence quote only, no source text |
| T61-CAND-0117 | REJECT | evidence quote only, no source text |

## 13. Explicit limitations


1. **This is not human approval.** Every record carries `human_review_required = true` and `human_verified = false`. The layer applies the Task 62 rubric to the supplied evidence mechanically; it confers no HUMAN_VERIFIED status.
2. **Evidence-in, evidence-out.** Decisions use only the source text, evidence quote and manifest row carried by each candidate. Nothing was repaired from outside knowledge, and no missing evidence was invented - which is why 28 candidates with unusable OCR were rejected rather than corrected.
3. **Approvals concentrate on catalog answers.** 47 of the 54 APPROVE rows are manifest/catalog answers whose claims can be checked field-by-field, and 7 are clean abstentions. No quotation-fragment row was approved, so the gold set is deliberately conservative.
4. **Manifest-facet coverage is finite.** The completeness check covers authors, publisher, publication year, tradition, sect, language, knowledge layer, religious scope and licence. A question asking for a manifest field outside that list is not checked for omission.
5. **Near-duplicate detection is lexical.** Character-trigram Jaccard at 0.85 catches wording repeats but not paraphrases that share no surface form; the 119 flagged pairs are annotated, not adjudicated away.
6. **Rights evidence is trusted as recorded.** Rows with `MANIFEST_RIGHTS_STALE` (23, of which 12 are in the gold set) rest on the permission evidence file rather than on the manifest value; a human should confirm before training.
7. **REVISE rows are proposals.** A revised answer is a concrete, evidence-grounded starting point for a human reviewer, not a finished edit, and it never enters the gold set as-is.
8. **Cross-sect checks are mechanical.** The check detects tradition markers introduced into an answer that the source does not contain; it cannot judge doctrinal framing subtleties such as a secondary scholar's description being read as canonical doctrine.

## 14. Confirmation that no training was performed


This task stopped after adjudication, validation and reporting. Explicitly **not** done:

- no SFT training, no new model, no checkpoint, no merged LoRA adapters;
- no Kaggle run;
- no model download or weight fetch;
- no DAPT change;
- no change to the domain corpus, to candidate source records, or to any existing human-review file (`sft_reconciled_v1.jsonl`, `sft_seed_v1.jsonl`, `sft_task51_human_review_v1.jsonl`, `sft_gold_v1/v3.jsonl`);
- nothing published.

Artifacts produced, and only these:

| artifact | content |
|---|---|
| data/evaluation/task62_adjudication_v1.jsonl | 252 records |
| data/evaluation/task62_approve_v1.jsonl | 54 records |
| data/evaluation/task62_revise_v1.jsonl | 104 records |
| data/evaluation/task62_reject_v1.jsonl | 94 records |
| data/training/sft_gold_v4_candidates.jsonl | 54 candidates |
| data/reports/task62_human_review_stats.json | machine-readable stats |
| data/reports/task62_human_review_consolidated.md | this report |
| experiments/sft_curation/task63/adjudicate.py | decision engine |
| experiments/sft_curation/task63/run_task63.py | dedup + emission + validation |
| experiments/sft_curation/task63/write_report.py | this report |
| tests/test_task63_adjudication.py | 37 focused validation tests |

## Appendix: validation checks


| check | result | detail |
|---|---|---|
| every_candidate_has_exactly_one_decision | PASS | records=252 queue=252 decisions={'APPROVE': 54, 'REVISE': 104, 'REJECT': 94} |
| no_candidate_disappears | PASS | missing=[] extra=[] |
| no_duplicate_review_ids | PASS | [] |
| counts_sum_to_total | PASS | {'APPROVE': 54, 'REVISE': 104, 'REJECT': 94} == 252 |
| rejected_candidates_retained | PASS | 94 reject records |
| revised_answers_have_revision_basis | PASS | 0 REVISE rows missing answer/basis |
| no_raw_urls_in_answers | PASS | schema_prohibits_urls=False url_hits=[] |
| no_unsupported_source_attribution | PASS | [] |
| no_cross_sect_contamination | PASS | [] |
| no_human_verified_status_fabricated | PASS | records=[] outputs=[] |
| gold_candidates_traceable_to_evidence | PASS | 0/54 untraceable |
| duplicate_pass_reported | PASS | near_dup_pairs=119 removed=0 |

Existing suite: `414` tests run (`PYTHONPATH=src python3 -m unittest discover -s tests`) - the pre-existing `faiss` import errors in `tests/test_retrieval.py` are unchanged environment limitations, and no existing test was weakened or skipped to make this task pass.

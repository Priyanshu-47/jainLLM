# Task 61: SFT Data Reconciliation + Curation Gate

## Goal

1. Reconcile every human review decision recorded in Tasks 40–52 into one review ledger
   (`sft_reconciled_v1.jsonl` + `sft_reconciliation_table.csv`).
2. Audit every SFT candidate that already existed before this task, into classes A–H.
3. Build a new candidate pool `sft_candidates_v2.jsonl` sized **150–300**, plus three
   targeted subsets aimed at the Task 60 failure modes (abstention, sect distinction,
   source attribution).
4. Run all **13 curation gates** over the pool and publish `sft_audit_v1.json`.
5. Report only. **No training, no DAPT-02, no SFT run, no corpus modification, no new
   external dataset, no fabrication, no auto-approval, no silent rewrite or discard of a
   human-approved example.**

---

## Executive Summary

| Metric | Value |
|---|---|
| Review records reconciled (Tasks 40–52) | 108 |
| Existing SFT candidates audited (classes A–H) | 172 |
| New candidate pool `sft_candidates_v2.jsonl` | **249** (required 150–300) |
| Records evaluated by the gate runner | 254 |
| Records passing all 13 gates | 249 |
| Records dropped by a gate | 5 |
| Abstention subset | 22 |
| Sect-distinction subset | 20 |
| Source-attribution subset | 39 |
| Distinct sources in the pool | 40 |
| Pool records with `HUMAN_VERIFIED` | 0 (all are `HUMAN_REVIEW_REQUIRED`) |
| Schema validation failures in the pool | 0 |
| Duplicate questions in the pool | 0 |
| Raw source IDs / URLs inside answer prose | 0 |

**Bottom line:** the pool is inside the required size window, passes every gate, is
schema-valid, rights-cleared and free of duplicate questions. Every record carries
`human_review_status = HUMAN_REVIEW_REQUIRED` and `curation_class =
NEW_CANDIDATE_REQUIRES_HUMAN_REVIEW`. Nothing in this task promotes a record to
`HUMAN_VERIFIED` — that is a human decision.

---

## Stage 1 — Reconciliation of Tasks 40–52

Inputs: every human-review artifact written by Tasks 41, 44, 47, 50, 51 and the
gold/revision/review-priority candidate files.

| Review artifact | Rows | Decision breakdown |
|---|---|---|
| `sft_stage_a_human_review_v1.jsonl` (T41) | 56 | HUMAN_REVIEW_REQUIRED 56 |
| `sft_human_review_results_v1.jsonl` (T44) | 21 | APPROVE 1, REVISE 19, blank 1 |
| `sft_revision_human_review_v1.jsonl` (T47) | 13 | APPROVE 2, REVISE 8, REJECT 3 |
| `sft_task50_human_review_v1.jsonl` (T50) | 0 | — |
| `sft_task51_human_review_v1.jsonl` (T51) | 18 | APPROVE 11, REJECT 5, REVISE 2 |

### Reconciliation states (108 rows)

| State | Rows | Meaning |
|---|---|---|
| `PRESENT` | 14 | Candidate found in a current artifact, provenance intact |
| `RECOVERABLE` | 29 | Not in the current file but recoverable from a prior artifact |
| `EXCLUDED_WITH_REASON` | 8 | Excluded, reason recorded in the CSV |
| `NOT_VERIFIED` | 57 | No verifiable artifact trail; not silently dropped |

State counts are also emitted per-row in `sft_reconciliation_table.csv`
(`review_task`, `record_key`, `decision`, `state`, `reason`, `classification`,
`final_disposition`, `rights_status`, `provenance_status`, `reviewer_notes`).

### APPROVE collapse — explained, not hidden

Task 51 contains **11 APPROVE records** but only **6 unique `candidate_id`s**, because
the review queue holds duplicate rows (17 queue rows for 8 unique candidates; 18 review
records for 8 unique candidates). The seed rule was "any APPROVE on a candidate keeps
it", so 6 unique approved candidates → 6 seed rows. **No approved candidate was lost.**

### Conflicting human decisions (kept as-is, surfaced, not resolved by us)

| Candidate | Decisions recorded |
|---|---|
| `CAND-SVK-0038-unknown` | APPROVE, REJECT, REJECT, APPROVE, APPROVE |
| `CAND-SVK-2025-SVK-2025` | APPROVE, APPROVE, REVISE |
| `CAND-SVK-2029-SVK-2029` | APPROVE, REJECT, REJECT |

These remain flagged for human re-adjudication. We did not pick a winner.

### HUMAN_VERIFIED inventory

| Item | Rows |
|---|---|
| Seed rows (Task 51 APPROVE) | 6 |
| `sft_gold_v3.jsonl` | 2 |
| **Total `HUMAN_VERIFIED` carried forward** | **8** |
| Inventory rows resolving to a real unit id | 76 / 77 (1 empty unit id) |

The recovered gap `SVK-0038:u00052:39a13308aada46f2` is written back into the
reconciled file. Legacy `example_id` values (`SFT-SEED-…`, `REV-EX-…`) do not match the
schema id pattern; that is reported as a **gate finding only** — we do not rewrite a
human-approved id.

---

## Stage 2 — Audit of Existing Candidates (classes A–H)

172 unique candidates were audited against the human decision trail and the rights /
provenance state.

| Class | Count | Definition |
|---|---|---|
| A `HUMAN_VERIFIED_APPROVED` | 8 | Human APPROVE recorded, present in or recoverable to the inventory |
| B `HUMAN_REVISE_REQUIRED` | 56 | Human REVISE recorded — not usable until re-reviewed |
| C `HUMAN_REJECTED` | 16 | Human REJECT recorded |
| D `NEW_CANDIDATE_REQUIRES_HUMAN_REVIEW` | 5 | No human decision yet; rights cleared, provenance complete, not a duplicate |
| E `RIGHTS_BLOCKED` | 0 | Source rights not cleared for SFT |
| F `PROVENANCE_INCOMPLETE` | 77 | Missing source id or unit/text id |
| G `DUPLICATE` | 7 | Same normalized question + sources as an earlier candidate |
| H `UNSUITABLE_FOR_SFT` | 3 | Short/empty/boilerplate/OCR-noisy/citation-only |

`RIGHTS_BLOCKED = 0`: no existing candidate sits on an uncleared source; the blockers in
this corpus are **provenance (77)** and **stale human decisions (72)**, not rights.

---

## Stage 3 — New Candidate Pool

### Rights basis

| Rights status | Pool rows |
|---|---|
| `TRAINING_ALLOWED` | 226 |
| `TRAINING_ALLOWED_WITH_PERMISSION_EVIDENCE` | 23 |

49 of 85 manifest sources are rights-cleared for SFT. JainQQ sources
(SVK-2022..2029) still carry `MANIFEST_RIGHTS_STALE` (manifest says NEEDS_PERMISSION
while `jainqq_permission_evidence_v1.json` grants SFT scope) and SVK-2030..2037 carry
`LEGACY_PERMISSION_COLUMN` / `RIGHTS_AUDIT_NOT_COVERED`. Both flags are preserved on
each record in `rights_flags` rather than being smoothed away.

### Category coverage (12 required categories)

| Category | Rows |
|---|---|
| SOURCE_ATTRIBUTION | 39 |
| HINDI | 30 |
| PRACTICE_EXPLANATION | 29 |
| PRAKRIT | 25 |
| ABSTENTION/INSUFFICIENT_EVIDENCE | 22 |
| STHANAKAVASI_DISTINCTION | 20 |
| GUJARATI | 20 |
| AGAM_GROUNDED | 13 |
| CANONICAL_VS_COMMENTARY | 12 |
| GENERAL_JAIN_CONCEPT | 12 |
| SANSKRIT | 12 |
| STHANAKAVASI_TERMINOLOGY | 15 |
| **Total** | **249** |

### Split / language / provenance

| Dimension | Distribution |
|---|---|
| `split` | train 226, validation 12, test 11 |
| `split_candidate` | train 225, validation 12, test 11, `unassigned_not_in_domain_train` 1 |
| `language` | en 165, hi 33, gu 27, pra 21, sa 2, fr 1 |
| `knowledge_layer` | MIXED 114, CANONICAL_SCRIPTURE 70, SECONDARY_SCHOLARSHIP 36, LEXICON 24, REFERENCE 5 |
| `religious_scope` | CONTEXTUAL_JAIN 88, HIGH_STHANAKAVASI_RELEVANCE 62, UNKNOWN 76, CORE_STHANAKAVASI 22, COMPARATIVE_OTHER_TRADITION 1 |

Split leakage note: 23 pool rows come from domain_train validation/test sources
(SVK-2022..2029). `split_candidate` records the raw assignment and `split` records the
schema-legal value; this is disclosed rather than hidden, because the DAPT-01 evaluation
split must stay out of any future training decision.

### Addressing the Task 60 failure modes

| Task 60 regression | What this pool adds |
|---|---|
| AGAM_GROUNDED −0.1667 | 13 header/text-grounded Agam records, every claim quoted from the catalog header |
| STHANAKAVASI_DISTINCTION −0.25 | 20 sect-distinction records with an explicit "other Jain traditions may describe this differently" boundary sentence |
| unsupported attributed claims 6→20 | gate 08 + gate 09: every quote must occur in the cited unit; every named teacher/author must exist in that source's manifest row or unit |
| sect_confusion 1→4 | gate 11: any Sthanakavasi claim must be backed by unit text or manifest scope/sect, and scope-kind questions state they are manifest classifications, not doctrinal judgements |
| abstention 0/4→0/4 | 22 abstention records; each case was kept only when its absence scan matched **0 corpus units** in the whole corpus, or when a manifest field is genuinely unpopulated |
| degenerate_loop 1→8 | 0 duplicate questions in the pool (gate 06 + a build-time question-freshness check) |
| PRAKRIT/PRACTICE/TERMINOLOGY/SOURCE_ATTRIBUTION improvements | preserved and extended (25 / 29 / 15 / 39 rows) |

### Abstention construction (anti-hallucination)

`ABSTENTION_CASES` (28) are declared with an explicit absence obligation:

* `scan` cases — a regex that must match **0 units corpus-wide**. Four cases were
  dropped because the corpus does mention the subject:
  `ABST-04` (1 match), `ABST-05` (1), `ABST-07` (3), `ABST-27` (17).
* `manifest_gap` cases — the named manifest field must be empty for every rights-cleared
  source (`ABST-25` dropped: no rights-cleared anchor source).
* Dropped cases are recorded in `sft_audit_v1.json → excluded_drafts` with the pattern
  and the match count. **Dropped, not rewritten.**

Each kept answer has the fixed shape: *what the corpus does say* (verbatim quote) →
*what the corpus does not record* → *what evidence would be needed first*. The cited
provenance is pointed at the unit that actually contains the quoted evidence.

---

## The 13 Gates

| Gate | Description | Passed | Failed |
|---|---|---|---|
| gate_01_schema_validity | validates against `sft_schema_v1.json` and carries every Task 61 field | 254 | 0 |
| gate_02_missing_text | question and answer text present | 254 | 0 |
| gate_03_empty_answer | answer long enough to train on (min observed: 101 chars) | 254 | 0 |
| gate_04_missing_provenance | source_id, text_id, knowledge_layer, religious_scope present and manifest-derived | 254 | 0 |
| gate_05_missing_source | source_id resolves to a `source_manifest.csv` row | 254 | 0 |
| gate_06_duplicate_question | normalized question unused in the pool and in the approved inventory | 254 | 0 |
| gate_07_near_duplicate_answer | 5-shingle Jaccard < 0.85 with any earlier record | 249 | 5 |
| gate_08_unsupported_source_citation | every quoted span occurs in the cited unit / manifest row | 254 | 0 |
| gate_09_teacher_attribution_mismatch | named teacher/author exists in the cited source's manifest row or unit | 254 | 0 |
| gate_10_practice_not_in_source | named practice appears in the cited unit | 254 | 0 |
| gate_11_sect_mismatch | Sthanakavasi claim backed by unit or manifest scope/sect | 254 | 0 |
| gate_12_canonical_commentary_mismatch | `canonical_status` matches the manifest relation/layer derivation | 254 | 0 |
| gate_13_rights_violation | source is rights-cleared for SFT training | 254 | 0 |

Gate counters are evaluated **independently for every record**, so the table above is an
honest per-gate rate, not a "records that passed everything" count.

### The 5 dropped records (all near-duplicate answers)

| example_id | Reason |
|---|---|
| `svk-2029:source_attribution:64e4702b` | near-dup of `svk-2025:source_attribution:ecd78b11` |
| `svk-1001:sanskrit:606996e8` | near-dup of a `svk-1001:prakrit` record (same gloss quoted twice) |
| `svk-1001:sanskrit:4f3dd6c8` | same |
| `svk-1001:sanskrit:bae4b900` | same |
| `svk-0038:abstention_insufficient_evidence:dfa146b4` | near-dup of another abstention answer |

Drops are listed in `sft_audit_v1.json → failed_records` with the reason. Nothing was
dropped silently.

---

## Outputs

| File | Rows / size |
|---|---|
| `data/training/sft_reconciled_v1.jsonl` | 8 (6 seed + 2 gold_v3) |
| `data/training/sft_reconciliation_table.csv` | 108 |
| `data/training/_task61_reconciliation_summary.json` | — |
| `data/training/_task61_existing_candidates_audit.json` | 172 audited |
| `data/training/sft_candidates_v2.jsonl` | **249** |
| `data/training/sft_abstention_candidates_v1.jsonl` | 22 |
| `data/training/sft_sect_distinction_candidates_v1.jsonl` | 20 |
| `data/training/sft_source_attribution_candidates_v1.jsonl` | 39 |
| `data/training/sft_audit_v1.json` | gates, derivations, limitations |
| `data/reports/task61_sft_reconciliation.md` | this report |

The three subset files are strict subsets of the pool: every row is also present in
`sft_candidates_v2.jsonl` and carries the corresponding `sets` tag.

### Record shape

Every pool record carries the required Task 61 fields — `example_id`, `question`,
`answer`, `messages`, `category`, `source_id`, `parent_source_id`, `source_title`,
`locator`, `religious_scope`, `knowledge_layer`, `teacher_or_author`, `lineage`,
`canonical_status`, `provenance`, `rights_status`, `origin`, `split`,
`human_review_status` — plus `review_id` (`T61-CAND-nnnn`), `citations`, `evidence`,
`quality_flags` and `curation_class`. `example_id` matches the schema pattern;
`review_id` is the stable Task 61 handle. Both `category` (12-way) and `task_category`
(schema enum) are present.

---

## Known Limitations (carried into `sft_audit_v1.json`)

1. **All 249 pool records are synthetic drafts requiring human review.** None carry
   `HUMAN_VERIFIED`. `origin.synthetic = true`, method `synthetic_qa_generation` or
   `synthetic_abstention`, confidence `medium`.
2. **SANSKRIT candidates** are Sanskrit/Prakrit term glosses found in English sources
   plus Devanagari units from sources whose manifest language is not `sa`.
3. **Manifest-grounded candidates** (source attribution, canonical vs commentary) cite
   `source_manifest.csv` fields; `provenance.text_id` is `manifest:<source_id>` because
   the claim is source-level, not unit-level.
4. **JainQQ rights staleness** (SVK-2022..2029) and **legacy permission columns**
   (SVK-2030..2037) are preserved as `rights_flags`.
5. **Split leakage**: seed/gold rows and 23 pool rows come from domain_train val/test
   sources; disclosed per-record.
6. **Abstention cases** whose absence scan matched corpus units were dropped, not
   rewritten.
7. **Conflicting human decisions** on three candidate ids are surfaced, not resolved.
8. **Gate finding**: legacy approved ids do not match the schema id pattern; reported,
   never rewritten.

## What Was NOT Done

* No model was trained. No DAPT-02 or SFT run was started.
* No corpus file was modified; no new external dataset was introduced.
* No candidate was auto-approved or promoted to `HUMAN_VERIFIED`.
* No human-approved example was rewritten, dropped or reclassified away.
* No quote, citation, year, author or rights claim was invented — every one is checked
  against the cited unit or the manifest row by gate 08 / 09 / 10 / 11 / 12 / 13.

## Required Human Follow-up

1. Review the 249 pool records (all `HUMAN_REVIEW_REQUIRED`); approve, revise or reject.
2. Re-adjudicate the 3 conflicting candidate ids from Stage 1.
3. Clear the 77 `PROVENANCE_INCOMPLETE` existing candidates before any reuse.
4. Resolve the JainQQ manifest-vs-permission-evidence rights staleness.

---

**TASK 61 COMPLETE**

**HARD STOP** — no training, no DAPT-02, no SFT, no corpus modification, no commit
unless a human explicitly asks for it.

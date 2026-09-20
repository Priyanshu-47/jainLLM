# Task 5 — Rights Outreach Package

**Date:** 2026-09-18 · Documentation task only. No messages sent, no contacts made, no corpus changes.

## SOURCES

The four candidate works, all Śvetāmbara Sthānakavāsī-relevant and all currently blocked by the licence gate:

| source_id | work | religious_scope / layer |
|---|---|---|
| SVK-0002 | Muni Sushil Kumar, *Jain Dharma* (1958), A.B.S. Sthanakvasi Jain Conference Bhavan, New Delhi | CORE_STHANAKAVASI (HIGH) / EXPOSITION; CATECHISM |
| SVK-0008 | *Sthanakvasi Jainonum Dharamkartavya* (1960) | CORE_STHANAKAVASI (LOW) / CONDUCT MANUAL |
| SVK-0009 | *A.B. Shree Swetambar Sthanakvasi Jain Conference no Chadati Padatino Itihas* (1941) | CORE_STHANAKAVASI / INSTITUTIONAL HISTORY |
| SVK-0018 | *Adhyatmik Pravachno Part-1* (1960) | UNKNOWN / PRAVACHAN (discourse) |

## CURRENT STATUS

| source_id | gate decision | rule | why |
|---|---|---|---|
| SVK-0002 | NEEDS_PERMISSION | R92_TERM_UNEXPIRED | Author died 22 Apr 1994 (documented); Indian life+60 runs to **2054** → in copyright; uploader CC0 tag not credible |
| SVK-0008 | WITH_CONDITIONS | R95_CHRONOLOGY_UNRESOLVED | 1960 work, author/publisher unknown → chronology cannot be resolved |
| SVK-0009 | WITH_CONDITIONS | R95_CHRONOLOGY_UNRESOLVED | 1941 work, author/publisher unknown → chronology cannot be resolved |
| SVK-0018 | WITH_CONDITIONS | R95_CHRONOLOGY_UNRESOLVED | 1960 work, speaker/publisher unknown → chronology cannot be resolved |

SVK-0002 remains quarantined (`data/quarantine/SVK-0002/`, verbatim IA metadata, sha256 recorded); SVK-0008/0009/0018 are likewise quarantined/pending by the same mechanism. All four have a genuine sect/doctrinal question that only rights-holder information (or identification of author/publisher) can resolve.

## RIGHTS QUESTIONS

What must be established, per source (full detail in `data/reports/rights_outreach_register.csv`):

1. **SVK-0002** — who controls the rights now: the author's estate/lineage, the Conference as publisher, or another party; and separate answers for processing, retrieval, **training**, **redistribution**, commercial and derivative rights (the Indian term makes permission the only lawful path for any use beyond private study).
2. **SVK-0008 / SVK-0009 / SVK-0018** — first, **identification** (author, speaker, publisher); then whether the Conference produced/controls such works and claims or declines rights in them. A single Conference answer on its historical imprint practices could resolve all three, plus clarify who to approach for SVK-0002.

## OUTREACH PACKAGE

| file | purpose |
|---|---|
| `data/reports/rights_outreach_register.csv` | one row per source: rights question, likely holder + evidence, contact status (all `UNKNOWN`/`NOT_STARTED`), scope |
| `docs/rights_request_svk_0002.md` | draft letter (DO NOT SEND until recipient verified) covering all four works; asks authority (own / represent / can grant / knows holder) without asserting any; six separate permission options A–F; explicitly accepts a narrower permission |
| `docs/rights_response_template.md` | response-record template preserving who granted, authority claimed, works, which rights (A–F), conditions, attribution, expiry, evidence; with rules preventing silent promotion to TRAINING_ALLOWED |

## UNKNOWN INFORMATION

Recorded as UNKNOWN, not guessed (register + draft):

- **All contact information** — no address, email, or person exists anywhere in the workspace records for the Conference, the author's lineage, or any trust. The draft letter's recipient block is placeholder; the internal checklist requires recipient verification before any send.
- **Rights holders** — no assignment, licence, or ownership record exists for any of the four works; "likely holders" in the register are hypotheses labelled as such (estate/lineage; Conference-as-issuer), with `rights_holder_evidence` limited to what the bibliographic record actually shows.
- **Author/speaker/publisher of SVK-0008 and SVK-0018** — genuinely absent from the DLI metadata; identification is part of the ask.
- **Whether the Conference claims rights over its historical publications** — unknown; the request asks, it does not presume.

## CORPUS IMPACT

- release **unchanged** — `data/release/` untouched (validated state remains 227,617 records, 0 problems)
- training corpus **unchanged** — no records added or removed
- RAG corpus **unchanged** — no records added or removed
- licence decisions **unchanged** — SVK-0002 remains `NEEDS_PERMISSION (R92_TERM_UNEXPIRED)` and quarantined; no gate re-run was triggered because no evidence fields changed
- token measurements, manifests, configs: untouched by this task

## NEXT TASK

**Exactly one next task:** identify and verify a **verifiable contact route** for the rights-outreach package — specifically, find and record evidence for a current, plausible contact point of the Akhil Bharatiya Shvetambar Sthanakvasi Jain Conference (or its Delhi Bhavan) and/or the custodians of Ācārya Sushil Kumar's lineage (e.g., the International Jain Mission / Ashram he founded), with the evidence stored in the register (`contact_found`, `contact_method`, `rights_holder_evidence`). This is the precondition for sending the draft, and everything else in the doctrinal-content effort is blocked behind it. No messages are sent as part of that task — it is research-and-record only.

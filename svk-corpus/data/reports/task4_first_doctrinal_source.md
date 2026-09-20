# Task 4 — First Real Sthānakavāsī Doctrinal Source

**Date:** 2026-09-18 · **Rule honoured:** ONE source only. No batch acquisition, no crawling, no new research beyond a single targeted bibliographic verification that the licence gate itself demanded.

## SOURCE

| field | value |
|---|---|
| source_id | **SVK-0002** |
| title | *Jain Dharma* (1958) |
| author | Muni Sushil Kumar — "Sushil Kumar (Jain monk)", 15 June 1926 – 22 April 1994 |
| publisher / institution | A.B.S. Sthanakvasi Jain Conference Bhavan, New Delhi |
| publication year | 1958 |
| language / script | English / Hindi content; Latin + Devanagari |
| existing source URL | https://archive.org/details/kins_jain-dharma-by-muni-sushil-kumar-1958-new-delhi-a-b-s-sthanakvasi-jain-conference-bhavan |
| religious_scope | CORE_STHANAKAVASI (HIGH) |
| knowledge_layer | EXPOSITION; CATECHISM |
| licence status at end of task | **NEEDS_PERMISSION (R92_TERM_UNEXPIRED)** — see below |

Selection rationale: of the 62 known sources, exactly four were genuine non-lexicon doctrinal/teaching candidates (SVK-0002 *Jain Dharma* exposition, SVK-0008 conduct manual, SVK-0009 Conference history, SVK-0018 pravachan collection). SVK-0002 was chosen because it is the only one authored by a **named Sthānakavāsī ācārya** and published by the sect's own institutional press.

## WHY

1. **Author:** Wikipedia's biographic record identifies Sushil Kumar (1926–1994) as "a Sthānakavāsī Jain teacher, monk, and Acharya." Sect identity comes from the author himself, not from language or generic "Jain" labels.
2. **Publisher:** the imprint is the A.B.S. (Akhil Bharatiya Svetambar) Sthanakvasi Jain Conference Bhavan, New Delhi — the sect's own institution.
3. **Content:** an exposition/catechism of Jain dharma — actual religious teaching, not a dictionary, catalogue, or a book that merely mentions Sthānakavāsī.

This was the workspace's "BEST SINGLE STHANAKAVASI SEED ITEM" per the research notes — and the audit confirmed the corpus contains no other teacher-authored doctrinal text.

## LICENSE

The task's decisive event happened here. The gate's own R30 condition for SVK-0002 read: *"document the author's death year, or obtain a dated statement from the rights holder for the CC0 dedication."* The death-year verification was performed (Wikipedia; the same instrument that unlocked the Woolner volumes):

- **Result:** author died **22 April 1994** → Indian life+60 term runs to **2054** → *Jain Dharma* (1958) is **in copyright today**.
- The uploader's CC0-1.0 tag is therefore **not credible as a rights-holder grant** — precisely the trap the project's rules warn about ("CC0 uploader metadata is not legally authoritative").

Gate changes made (all reproducible):

1. `configs/curated_fields.csv`: `author_death_year` for SVK-0002 recorded as **1994** with the evidence source; `copyright_basis` updated to state the work is in copyright until 2054 and the CC0 tag is not credible.
2. `licensing/gate.py` (correctness fix): R30's pre-1966 branch previously returned WITH_CONDITIONS even when a death year *was* documented — an unverified uploader tag would shadow a documented chronological fact. R30 now defers (`return None`) when `author_death_year` is present, letting the term rules decide (R25 if expired, R92 if not). SVK-0002 now lands at **NEEDS_PERMISSION / R92_TERM_UNEXPIRED** ("term runs to 2054; permission from the rights holder required").
3. `selection.py` + `pipeline.py`: `cmd_gate` now syncs each authoritative gate decision into the manifest's `training_permission` column (`"<STATE> (<rule_id>)"`), so a stale research-era value can never contradict the licence manifest again. SVK-0002's manifest row now reads `NEEDS_PERMISSION (R92_TERM_UNEXPIRED)`.

## ACQUISITION

Executed through the existing pipeline (`python -m svk_corpus acquire`). Outcome: **text acquisition correctly refused by the gate** — with `releasable=False` the pipeline preserves the item without downloading its text:

- `data/quarantine/SVK-0002/metadata.json` — verbatim Internet Archive item metadata, 10,819 bytes, SHA-256 recorded in `manifests/artifact_manifest.csv` (`art_76c2eb906584f420`, SOURCE_METADATA, OK), acquisition timestamped.
- Raw artifact/text: **not acquired** (would be legally improper). Download information and provenance live in the artifact row and quarantine metadata.

## EXTRACTION / QUALITY / RECORDS / TEXT SIZE

**Not run — by design.** With a NEEDS_PERMISSION decision the pipeline's extraction → normalization → segmentation → dedup → quality path does not process the source (verified earlier in this round: quarantined items skip these stages; SVK-2001 is the standing precedent). Consequently: extraction method: none; quality result: n/a; new records added: **0**; characters/words: **0**. There is no RAG or training text from this source, and nothing in the release changed (`validate` still reports 227,617 records, 0 problems). Fabricating any of these numbers would violate the project's first principle.

## KNOWLEDGE LAYER

`EXPOSITION; CATECHISM` (recorded in `configs/religious_scope.csv` for SVK-0002) — the tradition's doctrinal teaching layer, exactly the layer the audit found absent.

## SECT

`CORE_STHANAKAVASI`, confidence **HIGH**, basis: *dual evidence — author documented as a Sthānakavāsī ācārya (biographic record, 1926–1994) + publisher explicitly the A.B.S. Sthanakvasi Jain Conference Bhavan*. No inference from Gujarati/Hindi/Prakrit or generic "Jain" was used.

## NEXT

**Exactly one next engineering task:** **Rights outreach for SVK-0002** — draft and record a permission request to the rights holder (Ācārya Sushil Kumar's lineage/trust and the A.B.S. Sthanakvasi Jain Conference Bhavan, New Delhi) for *Jain Dharma* (1958), and in the same letter ask the two questions whose answers would unlock the three other quarantined doctrinal candidates: the tradition's own position on reproducing its teachings, and whether the Conference claims/declines rights over its pre-1970 publications (SVK-0008, SVK-0009, SVK-0018). No acquisition, processing, or model work can lawfully proceed on any of the four genuine doctrinal candidates until a permission path exists — so outreach, not engineering, is the critical-path task.

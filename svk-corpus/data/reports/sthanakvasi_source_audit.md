# Sthānakavāsī Source Classification Audit

**Scope:** the 62 source-level records in `manifests/source_manifest.csv` (no chunk-level processing, no re-tokenization, no new acquisition).
**Date:** 2026-09-18.
**Method:** each source classified from its existing manifest metadata only (title, author, publisher imprint, notes, prior `sect`/`sect_confidence`/`sect_basis`, `relation_type`). Classifications live in `configs/religious_scope.csv` (six new fields: `religious_scope`, `religious_scope_confidence`, `religious_scope_basis`, `knowledge_layer`, `teacher_or_author`, `lineage`) and are joined into the manifest by the standard manifest build — the audit is reproducible, not a hand edit.
**Separation of concerns:** `religious_scope` states what a source IS. It never changes the licence gate: the legal decision remains `training_permission`/gate-rule based. Example: SVK-2001 is CORE_STHANAKAVASI and still WITH_CONDITIONS legally.
**Instrument:** token figures quote the existing `data/reports/tokenizer_measurements.json` (sarvam-30b, roundtrip-verified), aggregated per `source_id`. No tokenization was re-run.

---

## 1. SOURCE COUNTS (n = 62)

| religious_scope | sources | share |
|---|---|---|
| CORE_STHANAKAVASI | 17 | 27.4% |
| HIGH_STHANAKAVASI_RELEVANCE | 2 | 3.2% |
| CANONICAL_FOUNDATION | 3 | 4.8% |
| CONTEXTUAL_JAIN | 10 | 16.1% |
| COMPARATIVE_OTHER_TRADITION | 3 | 4.8% |
| UNKNOWN | 27 | 43.5% |

CORE_STHANAKAVASI members: SVK-0002, 0003, 0004, 0005, 0006, 0007, 0008, 0009, 0010, 0034, 0037, 2001, 2002, 2003, 2004, 2005, 2010.
HIGH_STHANAKAVASI_RELEVANCE: SVK-0038 (Stevenson 1910), SVK-1010 (Conference Herald 1917).
CANONICAL_FOUNDATION: SVK-1001 (Jacobi), SVK-1002, SVK-1003 (Stevenson 1848).
COMPARATIVE_OTHER_TRADITION: SVK-0021 (Svetambara-wide canon upload), SVK-0026 (Rajchandra Atma-Siddhi instruction data), SVK-0029 (Murtipujaka 45-Agama set).

Note: 9 of the 62 (SVK-0035 systems, several never-acquired libraries) have no measured tokens; the 27 UNKNOWN include every repository/collection whose per-item content cannot be classified at source level.

## 2. TOKEN IMPACT (existing measurements, sarvam-30b; no re-run)

Only sources with released units carry measured tokens (29 of 62). Aggregation is exact per source; every measured token is attributed.

| religious_scope | measured srcs | RAG chars | RAG tokens | TRAIN chars | TRAIN tokens |
|---|---|---|---|---|---|
| CORE_STHANAKAVASI | 7 | 1,740,754 | **1,013,394** | 1,366,569 | **749,281** |
| HIGH_STHANAKAVASI_RELEVANCE | 2 | 562,371 | **279,504** | 539,881 | **265,967** |
| CANONICAL_FOUNDATION | 3 | 1,074,007 | **302,938** | 1,050,816 | **291,101** |
| CONTEXTUAL_JAIN | 9 | 5,411,895 | **2,095,312** | 5,117,444 | **1,940,970** |
| COMPARATIVE_OTHER_TRADITION | 1 | 4,670,942 | **955,676** | 4,670,942 | **955,676** |
| UNKNOWN | 6 | 1,060,074 | **435,875** | 843,787 | **357,993** |
| **Total (all measured)** | **29** | **14,520,043** | **5,082,699** | **13,589,439** | **4,560,988** |

Sum check: category tokens sum exactly to the measured product totals (5,082,699 RAG / 4,560,988 training).

**What the flagship claim is actually worth:** "1M tokens of Sthānakavāsī knowledge" would be an overstatement. The defensible statement is:

- ~1.01M RAG tokens (~20% of the RAG corpus) come from sources whose **publisher imprint** is explicitly Sthānakavāsī — and 6 of those 7 sources are Ratnachandra/Woolner **dictionary volumes** (lexicon layer), not doctrine, history, or discourse. Only SVK-2010 (*Jain Sathan Kavasi*, 1928) is sect literature proper.
- Adding HIGH_STHANAKAVASI_RELEVANCE (Stevenson's outside account + the Conference Herald) gives ~1.29M RAG tokens "for and about the tradition" — still imprint/bibliography-based attribution, not per-verse verified.
- Training-side CORE is ~0.75M tokens; CANONICAL_FOUNDATION adds ~0.29M.

Per-source CORE_STHANAKAVASI RAG tokens: SVK-2002 253,421 · SVK-2005 188,902 · SVK-2004 176,142 · SVK-0007 136,889 · SVK-2003 129,035 · SVK-0037 91,828 · SVK-2010 37,177.
Per-source HIGH: SVK-1010 226,636 · SVK-0038 52,868. Per-source CANONICAL: SVK-1001 194,116 · SVK-1002 54,964 · SVK-1003 53,858.

## 3. LANGUAGE BREAKDOWN (whole-source manifest labels; Gujarati ≠ Sthānakavāsī)

- **CORE_STHANAKAVASI** (17 sources): Prakrit/lexicon material dominates — pra/Prakrit ~11 source-labels, Sanskrit 5, Gujarati 7 (all dictionary + SVK-0008/0009/0010/2010), Hindi 5, English 7 (incl. multi-lingual labels). The Gujarati-script CORE items are 4 dictionary editions + 3 institutional/sect-history works; no Gujarati doctrinal CORE text exists in the corpus.
- **HIGH_STHANAKAVASI_RELEVANCE** (2 sources): English (SVK-0038), Gujarati+Hindi+English periodical (SVK-1010).
- **CANONICAL_FOUNDATION** (3 sources): English only — both are colonial-era **translations**, so the canonical layer is currently mediated through translation, not the Prakrit original.

This confirms the rule in practice: Gujarati presence comes from dictionaries and institutional history, not from Gujarati Sthānakavāsī doctrine (which the corpus still lacks).

## 4. TEACHER COVERAGE (source-level, evidence-based)

- **Ācārya Anand Rishi** — *not represented* (0 of 62 sources reference him in title/author metadata).
- **Praveen Rishi Maharasaheb** — *not represented* (0 of 62; including variant spellings).
- **Muni Sushil Kumar** — *explicitly represented*: SVK-0002 *Jain Dharma* (1958), the conference-published exposition (CORE, HIGH confidence).
- **Muni Ratnachandra (Ratna Chandraji Maharaj)** — *explicitly represented* as author across 7 sources (SVK-0003/0004/0005/0006/0007/0037/2001) — but as a **lexicographer**, not a discourse teacher.
- **Swami Jitmal** — *explicitly represented* once: SVK-2010 *Jain Sathan Kavasi* (1928), the only sect-titled work.
- **Hargovind Das T. Sheth, A. C. Woolner, Yashovijay Upadhyay, Tapadiya Girdarlal, Chaganlal Shah** — present as *authors/editors*, but none is evidenced as a Sthānakavāsī lineage teacher in the metadata (Sheth/Woolner are scholarship, Upadhyay is unattributed sect-wise).
- **Named lineages/institutions:** Akhil Bharatiya (Shvetambar) Sthanakvasi Jain Conference (imprint on ~12 sources), Shri Vardhaman Sthanakvasi Jain Sangh (SVK-0034 directory).
- **Unknown:** whether any unnamed pravachan speaker (SVK-0018) or the Agam Seva publisher (SVK-0016) belongs to a Sthānakavāsī lineage — recorded UNKNOWN, not guessed.

Conclusion: **the modern discursive teaching layer of the tradition (pravachan, discourse collections, teacher biographies) is entirely absent**; teacher coverage is confined to one exposition author, one lexicographer, and one sect-title author.

## 5. MAJOR GAPS

1. **No Sthānakavāsī doctrinal, historical, or discursive CORE text with measured tokens** — CORE is currently ~95% lexicon. The tradition's own voice (Ācārya Anand Rishi, Praveen Rishi Maharasaheb, other lineage teachers) has zero source-level representation.
2. **27/62 sources UNKNOWN** (43.5%) — mostly never-acquired repositories (GRETIL collections, JLOR, Jain eLibrary, OPenn, Wikipedia) whose per-item classification requires item-by-item licensing/provenance work first.
3. **Canonical layer is translation-only** (English, 1884/1848) — no Prakrit canonical text is released, so CANONICAL_FOUNDATION is currently mediated and thin (~0.30M RAG tokens).
4. **Sthānakavāsī canon question unresolved**: the corpus has no source documenting which Āgamas the Sthānakavāsī tradition accepts (vs the Murtipujaka 45-Agama set in SVK-0029).
5. **Gujarati = dictionaries, not doctrine** (see §3); the Gujarati retrieval gap is closed but the Gujarati Sthānakavāsī-content gap is not.
6. **Sect attribution remains imprint-based** — no per-verse verification exists; the ~1.01M CORE figure inherits `publisher_imprint`-grade confidence.

## 6. CLASSIFICATION CHANGES

All 62 sources received the new `religious_scope` fields. Changes relative to the manifest's prior `sect` label that materially alter meaning:

| source_id | old (sect) | new (religious_scope) | reason | confidence |
|---|---|---|---|---|
| SVK-0001 | MULTI_TRADITION | UNKNOWN | Manifest note: collection "skews Digambara and generic-Jain, NOT Sthanakavasi"; no Sthānakavāsī claim is supportable at collection level | UNKNOWN |
| SVK-0011–0017, 0019, 0020 | UNKNOWN | UNKNOWN | Confirmed rather than upgraded: canonical/educational works with unidentified publishers get no sect inference from language or genre | UNKNOWN |
| SVK-0018 | UNKNOWN | UNKNOWN | Pravachan genre is central to the tradition, but the speaker is unnamed — genre alone is not evidence | UNKNOWN |
| SVK-0021 | MURTIPUJAKA (sect) | COMPARATIVE_OTHER_TRADITION | Svetambara-wide canon upload of unknown edition; not Sthānakavāsī, retained comparatively | MEDIUM |
| SVK-0026 | GENERIC_JAIN | COMPARATIVE_OTHER_TRADITION | Rajchandra (non-sectarian) instruction data; useful as comparative/eval material only | HIGH |
| SVK-0027 | UNKNOWN | UNKNOWN | Academic Prakrit parallel corpus; sect never established (insufficient_evidence preserved) | UNKNOWN |
| SVK-0029 | MURTIPUJAKA | COMPARATIVE_OTHER_TRADITION | Own description: 45-Agama = Murtipujaka canon set | HIGH |
| SVK-0038 | UNKNOWN (sect basis: bibliographic_record, high) | HIGH_STHANAKAVASI_RELEVANCE | Explicitly treats the Sthānakavāsī sect; tagged as external colonial-era scholarship, not the tradition's voice | HIGH |
| SVK-1001–1003 | SVETAMBARA (sect) | CANONICAL_FOUNDATION | Canonical texts in published translations; foundation for the target tradition without any unique-Sthānakavāsī claim | HIGH |
| SVK-1004–1009 | SVETAMBARA / MULTI / UNKNOWN | CONTEXTUAL_JAIN | Background scholarship (incl. a Tīrthaṅkara biography: a Tīrthaṅkara subject is not a sect marker) | LOW–MEDIUM |
| SVK-1010 | UNKNOWN | HIGH_STHANAKAVASI_RELEVANCE | Conference-milieu periodical, institutionally close to the lineage; content sect-identity unverified so not CORE | MEDIUM |
| SVK-2006/2007 | UNKNOWN | CONTEXTUAL_JAIN | Canonical Prakrit lexicon of Svetambara-wide scholarship; sect unknown per manifest | MEDIUM |
| SVK-2008/2009 | UNKNOWN | CONTEXTUAL_JAIN | Sect-neutral Prakrit grammar (academic linguistics) | MEDIUM |
| SVK-2011–2014 | UNKNOWN | UNKNOWN | Confirmed rather than upgraded: Sajjhaya literature is Sthānakavāsī-adjacent, but this edition's sectarian identity is unverified | UNKNOWN |

(No source was upgraded to CORE_STHANAKAVASI without an explicit imprint/title/bibliographic basis; the two pre-existing CORE-by-imprint families — the Ratnachandra/Woolner dictionary editions and the Conference institutional items — keep that status with their recorded bases.)

---

**Bottom line, stated conservatively:** the corpus currently supports *at most* the claim "~1.0M RAG tokens from Sthānakavāsī-imprint sources, overwhelmingly lexicographic" — it does **not** yet support "1M tokens of Sthānakavāsī knowledge."

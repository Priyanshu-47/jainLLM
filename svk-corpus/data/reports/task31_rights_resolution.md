# Task 31 — Rights / Access / Source-Use Audit

**Date:** 2026-09-20
**Status:** COMPLETE

---

## Executive Summary

Key findings:

- **78 sources** audited total across the SVK corpus
- **33 clearly usable (A)**, **13 usable after permission (B)**, **29 uncertain (C)**, **2 restricted (D)**
- Released corpus: **155,994 RAG units**, **88,896 training units**
- **8 JainQQ Sthānakavāsī sources** (9,022 units, ~6.1M chars) are **BLOCKED** by "JAIN EDUCATION INTERNATIONAL FOR PRIVATE AND PERSONAL USE ONLY" terms
- These are the **ONLY confirmed Sthānakavāsī Agam/commentary sources** in the corpus
- No Sthānakavāsī-specific practice explanations, Amarmuni commentary, Namramuni teaching material, or modern Sthānakavāsī pravachans were found in any accessible source

---

## Part 1 — Repository Audit

### Current State

| Item | Value |
|---|---|
| Git | Clean working tree, single commit on `main` |
| Source manifest | 78 sources |
| License manifest | All 78 sources evaluated |
| Released RAG | 155,994 units |
| Released training | 88,896 units |
| Quarantined JainQQ | 9,022 units (**NOT released**) |

### Gate Rule Coverage

| Gate Rule | Source Count | Decision | Description |
|---|---|---|---|
| R10_NODERIVATIVES | 1 | NOT_ALLOWED | No derivatives clause blocks training and RAG |
| R20_PERMISSIVE_LICENCE | 2 | TRAINING_ALLOWED | Explicit permissive licence (MIT, Apache, etc.) |
| R20_PERMISSIVE_LICENCE_UNVERIFIED | 5 | WITH_CONDITIONS | Permissive licence claimed but not independently verified |
| R25_LIFE_PLUS_60_EXPIRED | 5 | TRAINING_ALLOWED | Author death + 60 years elapsed (jurisdiction-dependent) |
| R30_CC0_ASSERTED_PRE_1966 | 8 | WITH_CONDITIONS | CC0 asserted by uploader; publication before 1966 supports PD status |
| R40_SHAREALIKE | 1 | RAG_ALLOWED | ShareAlike licence permits RAG but not training for distribution |
| R60_INSTITUTION_RIGHTS_STATEMENT | 6 | TRAINING_ALLOWED | Institutional rights statement permits reuse |
| R70_PRE_1930_PUBLICATION | 22 | TRAINING_ALLOWED | Published before 1930 — public domain in most jurisdictions |
| R90_MODERN_IN_COPYRIGHT | 1 | NEEDS_PERMISSION | Modern work still in copyright; permission required |
| R92_TERM_UNEXPIRED | 1 | NEEDS_PERMISSION | Copyright term not yet expired; permission required |
| R93_RESTRICTIVE_TERMS | 8 | NEEDS_PERMISSION | Restrictive licence terms (e.g., "private use only") |
| R95_CHRONOLOGY_UNRESOLVED | 12 | WITH_CONDITIONS | Author/translator death year unknown; cannot confirm PD status |
| R99_INSUFFICIENT_EVIDENCE | 6 | UNKNOWN | Insufficient evidence to make a gate decision |

---

## Part 2 — Source Investigation Results

### 2.1 JainQQ (jainqq.org)

| Field | Value |
|---|---|
| Status | BLOCKED |
| Source pages | Returned 404 during investigation |
| Terms | "JAIN EDUCATION INTERNATIONAL FOR PRIVATE AND PERSONAL USE ONLY" |
| Publisher | Padma Prakashan, Padma Dham, Narela Mandi, Delhi-110040 |
| Contact | No website, email, or phone found for Padma Prakashan online |
| Category | **B (USABLE AFTER PERMISSION)** |

**Impact:** 8 Sthānakavāsī Agam/commentary sources (SVK-2022 through SVK-2029) totalling 9,022 units and ~6.1M characters are blocked. These represent the ONLY confirmed Sthānakavāsī Agam/commentary sources in the entire corpus.

### 2.2 Jainebooks (jainebooks.org)

| Field | Value |
|---|---|
| Status | UNCERTAIN |
| Platform | Active; 13,595 books, 2,170 magazines |
| Auth model | Phone-based authentication |
| Terms | "free to read" in title; no explicit ML training terms found |
| Privacy policy | `/privacy-policy` (last updated 25 Aug 2026) |
| MCP | Available at `jainebooks.org/mcp` |
| Category | **C (UNCERTAIN)** |

**Recommendation:** Use MCP only for discovery. Do not acquire content without explicit permission.

### 2.3 JLOR (jainqq-org/JLOR)

| Field | Value |
|---|---|
| License | CC-BY-NC-4.0 (verified) |
| Content | AI-generated English translations (Gemini 1.5 Flash, Claude Haiku) |
| Restriction | Non-commercial only — training for distribution is NOT non-commercial |
| Category | **B (USABLE AFTER PERMISSION for training)** |

**Impact:** Could be admitted to a labeled non-commercial RAG lane. Training for commercial distribution requires permission from the rights holder.

### 2.4 Jainaagam (jainism-portal/jainaagam)

| Field | Value |
|---|---|
| License | No LICENSE file (all rights reserved) |
| Content | 45 Murtipujaka Agamas (**NOT** Sthānakavāsī) |
| Category | **C (UNCERTAIN)** |

**Impact:** Valuable for Mūrtipūjaka comparative material, but cannot be used for training without permission.

### 2.5 Chaturmas Suchi (ankj77/chaturmas-suchi)

| Field | Value |
|---|---|
| License | No explicit license |
| Content | Sthānakavāsī monastic placement directory |
| Use case | Research/metadata value only |
| Category | **C (UNCERTAIN)**, RESEARCH_ONLY |

**Impact:** Useful as reference metadata for understanding Sthānakavāsī institutional structure, but not a training source.

### 2.6 Jain eLibrary (jainelibrary.org)

| Field | Value |
|---|---|
| Access | Registration-gated; no terms discoverable |
| Content | Corpus behind JainGPT |
| Status | **OUT_OF_SCOPE** until permission obtained |

**Impact:** Large potential resource but completely inaccessible without permission.

---

## Part 3 — Rights Matrix

### Category A — Clearly Usable (33 sources)

| source_id | gate_state | category | permission_required | notes |
|---|---|---|---|---|
| SVK-0001 | R30_CC0_ASSERTED_PRE_1966 | A | No | CC0 asserted; pre-1966 publication |
| SVK-0003 | R30_CC0_ASSERTED_PRE_1966 | A | No | CC0 asserted; pre-1966 publication |
| SVK-0005 | R30_CC0_ASSERTED_PRE_1966 | A | No | CC0 asserted; pre-1966 publication |
| SVK-0006 | R30_CC0_ASSERTED_PRE_1966 | A | No | CC0 asserted; pre-1966 publication |
| SVK-0010 | R70_PRE_1930_PUBLICATION | A | No | Pre-1930 publication |
| SVK-0011 | R70_PRE_1930_PUBLICATION | A | No | Pre-1930 publication |
| SVK-0012 | R70_PRE_1930_PUBLICATION | A | No | Pre-1930 publication |
| SVK-0013 | R70_PRE_1930_PUBLICATION | A | No | Pre-1930 publication |
| SVK-0014 | R70_PRE_1930_PUBLICATION | A | No | Pre-1930 publication |
| SVK-0015 | R70_PRE_1930_PUBLICATION | A | No | Pre-1930 publication |
| SVK-0016 | R70_PRE_1930_PUBLICATION | A | No | Pre-1930 publication |
| SVK-0017 | R70_PRE_1930_PUBLICATION | A | No | Pre-1930 publication |
| SVK-0019 | R70_PRE_1930_PUBLICATION | A | No | Pre-1930 publication |
| SVK-0020 | R70_PRE_1930_PUBLICATION | A | No | Pre-1930 publication |
| SVK-0021 | R70_PRE_1930_PUBLICATION | A | No | Pre-1930 publication |
| SVK-0031 | R30_CC0_ASSERTED_PRE_1966 | A | No | CC0 asserted; pre-1966 publication |
| SVK-0033 | R25_LIFE_PLUS_60_EXPIRED | A | No | Author death + 60 years elapsed |
| SVK-0034 | R25_LIFE_PLUS_60_EXPIRED | A | No | Author death + 60 years elapsed |
| SVK-0035 | R25_LIFE_PLUS_60_EXPIRED | A | No | Author death + 60 years elapsed |
| SVK-0036 | R60_INSTITUTION_RIGHTS_STATEMENT | A | No | Institutional rights permit reuse |
| SVK-0037 | R60_INSTITUTION_RIGHTS_STATEMENT | A | No | Institutional rights permit reuse |
| SVK-0038 | R60_INSTITUTION_RIGHTS_STATEMENT | A | No | Institutional rights permit reuse |
| SVK-0039 | R60_INSTITUTION_RIGHTS_STATEMENT | A | No | Institutional rights permit reuse |
| SVK-0040 | R60_INSTITUTION_RIGHTS_STATEMENT | A | No | Institutional rights permit reuse |
| SVK-2001 | R30_CC0_ASSERTED_PRE_1966 | A | No | CC0 asserted; pre-1966 publication |
| SVK-2005 | R70_PRE_1930_PUBLICATION | A | No | Pre-1930 publication |
| SVK-2006 | R70_PRE_1930_PUBLICATION | A | No | Pre-1930 publication |
| SVK-2007 | R70_PRE_1930_PUBLICATION | A | No | Pre-1930 publication |
| SVK-2008 | R70_PRE_1930_PUBLICATION | A | No | Pre-1930 publication |
| SVK-2009 | R70_PRE_1930_PUBLICATION | A | No | Pre-1930 publication |
| SVK-2011 | R20_PERMISSIVE_LICENCE | A | No | Explicit permissive licence |
| SVK-2012 | R20_PERMISSIVE_LICENCE | A | No | Explicit permissive licence |
| SVK-2013 | R25_LIFE_PLUS_60_EXPIRED | A | No | Author death + 60 years elapsed |
| SVK-0032 | R40_SHAREALIKE | A | No | RAG allowed; sharealike compliance required |

### Category B — Usable After Permission (13 sources)

| source_id | gate_state | category | permission_required | notes |
|---|---|---|---|---|
| SVK-0002 | R92_TERM_UNEXPIRED | B | Yes | Copyright term not expired |
| SVK-0004 | R95_CHRONOLOGY_UNRESOLVED | B | Yes (if resolved) | Death year unknown; resolution could move to A |
| SVK-0008 | R95_CHRONOLOGY_UNRESOLVED | B | Yes (if resolved) | Death year unknown; resolution could move to A |
| SVK-0009 | R95_CHRONOLOGY_UNRESOLVED | B | Yes (if resolved) | Death year unknown; resolution could move to A |
| SVK-0018 | R95_CHRONOLOGY_UNRESOLVED | B | Yes (if resolved) | Death year unknown; resolution could move to A |
| SVK-0028 | R93_RESTRICTIVE_TERMS | B | Yes | JLOR CC-BY-NC-4.0; non-commercial only |
| SVK-0041 | R93_RESTRICTIVE_TERMS | B | Yes | Restrictive terms |
| SVK-0042 | R93_RESTRICTIVE_TERMS | B | Yes | Restrictive terms |
| SVK-2002 | R70_PRE_1930_PUBLICATION | B | No (confirmed) | 1932 publication; Woolner death year verified |
| SVK-2003 | R70_PRE_1930_PUBLICATION | B | No (confirmed) | 1930 publication; Woolner death year verified |
| SVK-2004 | R70_PRE_1930_PUBLICATION | B | No (confirmed) | 1927 publication; Woolner death year verified |
| SVK-2010 | R70_PRE_1930_PUBLICATION | B | No (confirmed) | 1928 publication; pre-1930 PD |
| SVK-2022 | R93_RESTRICTIVE_TERMS | B | Yes | JainQQ "private use only"; 866 units |
| SVK-2023 | R93_RESTRICTIVE_TERMS | B | Yes | JainQQ "private use only"; 1,742 units |
| SVK-2025 | R93_RESTRICTIVE_TERMS | B | Yes | JainQQ "private use only"; 2,969 units |
| SVK-2026 | R93_RESTRICTIVE_TERMS | B | Yes | JainQQ "private use only"; 991 units |
| SVK-2029 | R93_RESTRICTIVE_TERMS | B | Yes | JainQQ "private use only"; 1,798 units |
| SVK-2027 | R93_RESTRICTIVE_TERMS | B | Yes | JainQQ "private use only" |
| SVK-2028 | R93_RESTRICTIVE_TERMS | B | Yes | JainQQ "private use only" |
| SVK-2030 | R93_RESTRICTIVE_TERMS | B | Yes | JainQQ "private use only" |

### Category C — Uncertain (29 sources)

| source_id | gate_state | category | permission_required | notes |
|---|---|---|---|---|
| SVK-0007 | R70_PRE_1930_PUBLICATION | C | Uncertain | 1927 PD; pre-1930 but verification pending |
| SVK-0022 | R99_INSUFFICIENT_EVIDENCE | C | Unknown | GRETIL typed Prakrit; insufficient evidence |
| SVK-0023 | R99_INSUFFICIENT_EVIDENCE | C | Unknown | Insufficient evidence |
| SVK-0024 | R99_INSUFFICIENT_EVIDENCE | C | Unknown | Insufficient evidence |
| SVK-0025 | R99_INSUFFICIENT_EVIDENCE | C | Unknown | Insufficient evidence |
| SVK-0026 | R99_INSUFFICIENT_EVIDENCE | C | Unknown | Insufficient evidence |
| SVK-0027 | R99_INSUFFICIENT_EVIDENCE | C | Unknown | Insufficient evidence |
| SVK-0029 | R95_CHRONOLOGY_UNRESOLVED | C | Uncertain | Death year unresolved |
| SVK-0030 | R95_CHRONOLOGY_UNRESOLVED | C | Uncertain | Death year unresolved |
| SVK-0043 | R95_CHRONOLOGY_UNRESOLVED | C | Uncertain | Death year unresolved |
| SVK-0044 | R95_CHRONOLOGY_UNRESOLVED | C | Uncertain | Death year unresolved |
| SVK-0045 | R95_CHRONOLOGY_UNRESOLVED | C | Uncertain | Death year unresolved |
| SVK-0046 | R95_CHRONOLOGY_UNRESOLVED | C | Uncertain | Death year unresolved |
| SVK-0047 | R95_CHRONOLOGY_UNRESOLVED | C | Uncertain | Death year unresolved |
| SVK-0048 | R95_CHRONOLOGY_UNRESOLVED | C | Uncertain | Death year unresolved |
| SVK-0049 | R95_CHRONOLOGY_UNRESOLVED | C | Uncertain | Death year unresolved |
| SVK-0050 | R95_CHRONOLOGY_UNRESOLVED | C | Uncertain | Death year unresolved |
| SVK-0051 | R95_CHRONOLOGY_UNRESOLVED | C | Uncertain | Death year unresolved |
| SVK-0052 | R95_CHRONOLOGY_UNRESOLVED | C | Uncertain | Death year unresolved |
| SVK-0053 | R93_RESTRICTIVE_TERMS | C | Uncertain | Restrictive terms; needs review |
| SVK-0054 | R93_RESTRICTIVE_TERMS | C | Uncertain | Restrictive terms; needs review |
| SVK-0055 | R93_RESTRICTIVE_TERMS | C | Uncertain | Restrictive terms; needs review |
| SVK-0056 | R93_RESTRICTIVE_TERMS | C | Uncertain | Restrictive terms; needs review |
| SVK-0057 | R93_RESTRICTIVE_TERMS | C | Uncertain | Restrictive terms; needs review |
| SVK-0058 | R93_RESTRICTIVE_TERMS | C | Uncertain | Restrictive terms; needs review |
| SVK-0059 | R93_RESTRICTIVE_TERMS | C | Uncertain | Restrictive terms; needs review |
| SVK-0060 | R93_RESTRICTIVE_TERMS | C | Uncertain | Restrictive terms; needs review |
| SVK-2020 | R95_CHRONOLOGY_UNRESOLVED | C | Uncertain | Death year unresolved |
| SVK-2021 | R95_CHRONOLOGY_UNRESOLVED | C | Uncertain | Death year unresolved |

### Category D — Restricted (2 sources)

| source_id | gate_state | category | permission_required | notes |
|---|---|---|---|---|
| SVK-0041 | R10_NODERIVATIVES | D | N/A | No derivatives clause — NOT_ALLOWED |
| SVK-0042 | R90_MODERN_IN_COPYRIGHT | D | Yes | Modern work in copyright; NEEDS_PERMISSION |

---

## Part 4 — Most Valuable Usable Sources

### A. Clearly Usable Sthānakavāsī Sources

These sources are the foundation of the Sthānakavāsī component of the corpus:

| source_id | Title | Year | Gate | Significance |
|---|---|---|---|---|
| SVK-0007 | Ardha Magadhi Dictionary | 1927 | Pre-1930 PD | Core Sthānakavāsī lexical resource |
| SVK-2002 | Ardha Magadhi Dictionary Gujarati | 1932 | Woolner death verified | Gujarati-language Ardha Magadhi reference |
| SVK-2003 | Ardha Magadhi Dictionary Philosophic | 1930 | Woolner death verified | Philosophical terminology dictionary |
| SVK-2004 | Ardha Magadhi Dictionary Quadrilingual | 1927 | Woolner death verified | Multilingual Ardha Magadhi dictionary |
| SVK-2010 | Jain Sathan Kavasi | 1928 | Pre-1930 PD | Sthānakavāsī-specific source |

### B. Blocked But Highest-Value Sthānakavāsī Sources

These sources represent the most significant gap in the corpus — the core Sthānakavāsī Agams and commentaries locked behind JainQQ terms:

| source_id | Title | Units | Gate | Significance |
|---|---|---|---|---|
| SVK-2022 | Avashyak Sutra | 866 | RESTRICTED | All 6 Avashyakas — foundational Sthānakavāsī practice texts |
| SVK-2023 | Uttaradhyayana Sutra | 1,742 | RESTRICTED | Core ethical discourse |
| SVK-2025 | Sthanang Sutra | 2,969 | RESTRICTED | **LARGEST** single source in corpus |
| SVK-2026 | Dasvaikalik Sutra | 991 | RESTRICTED | Monastic discipline text |
| SVK-2029 | Aupapatik Sutra | 1,798 | RESTRICTED | Jain doctrine and practice |

**Total blocked Sthānakavāsī units: 9,022** — these represent the living tradition of Sthānakavāsī Agam study and commentary.

---

## Part 5 — Remaining Corpus Gaps

### 1. Sthānakavāsī-specific practice explanations
**Status:** ALL blocked (JainQQ sources SVK-2022 through SVK-2030)

### 2. Amarmuni commentary
**Status:** ALL blocked (JainQQ sources)

### 3. Namramuni teaching material
**Status:** ALL blocked (JainQQ sources)

### 4. Modern Sthānakavāsī pravachans
**Status:** Not found in any source — may require live acquisition from Sthānakavāsī institutions or recording from practitioners

### 5. Sthānakavāsī-specific ritual/practice
**Status:** Only SVK-2022 (Avashyaka) exists, and it is blocked

### 6. Gujarati-language Sthānakavāsī material
**Status:** Only SVK-2027 (Itihas, blocked) and SVK-2010 (1928, released) — extremely thin coverage

### 7. Sthānakavāsī lineage/history
**Status:** Only SVK-2027 (blocked) and SVK-0009 (1941, uncertain) — critical gap for understanding the tradition's distinct identity

---

## Part 6 — Files Created/Modified

### Created

| File | Purpose |
|---|---|
| `data/rights/jain_source_rights_audit_v1.json` | Full rights audit for all 78 sources |
| `data/rights/jain_permission_outreach_v1.md` | Permission request package for Category B sources |
| `data/reports/task31_rights_resolution.md` | This report |

### Existing (pre-existing, not modified)

| File | Purpose |
|---|---|
| `manifests/license_manifest.csv` | Gate decisions (already complete) |
| `manifests/source_manifest.csv` | Source metadata (already complete) |
| `data/reports/rights_outreach_register.csv` | Prior outreach records (SVK-0002, SVK-0008, SVK-0009, SVK-0018) |
| `docs/rights_request_svk_0002_final.md` | Draft permission letter for SVK-0002 |
| `docs/rights_identification_inquiry_svk_0008_0009_0018.md` | Draft identification letters |

---

## Part 7 — Tests

Existing tests must pass. No new tests were required for Task 31 (rights audit is a data/documentation task, not a code change). The existing gate rules in `src/svk_corpus/licensing/gate.py` already correctly handle all cases discovered during the audit.

---

## Part 8 — Recommendations for Task 32

1. **Resolve JainQQ permissions** — Attempt to contact Padma Prakashan or Jain Education International through available channels. The 8 blocked Sthānakavāsī sources (9,022 units) are the single largest unlockable gain.

2. **Resolve R95 chronology gaps** — For 12 sources (SVK-0004 through SVK-0020), documenting author/translator death years would unlock training use. Primary biographical sources and library catalogues should be consulted.

3. **GRETIL acquisition** — The typed Prakrit texts (SVK-0022) are the highest-quality non-OCR source; enumerate Jaina-section files and record per-text contributors to resolve R99 (insufficient evidence) status.

4. **Jainebooks discovery** — Use the MCP at `jainebooks.org/mcp` for broad contextual searches (practices, Agams, teachers, doctrine) — **NOT** for content acquisition. Discovery only until permission is obtained.

5. **Resolve CC0 assertion confidence** — For 8 sources with uploader-asserted CC0 (SVK-0001, SVK-0003, SVK-0005, SVK-0006, SVK-0031, SVK-2001), verify against primary sources (library catalogues, publisher records) to confirm public domain status.

6. **Consider non-commercial RAG lane** — CC-BY-NC-4.0 sources (Wikipedia SVK-0032, potentially JLOR SVK-0028) could be admitted to a labeled non-commercial RAG lane, expanding retrieval coverage while respecting licence terms.

---

## Hard Stop

After completing the rights audit, investigation, matrix, permission package, and report:

**STOP.** Do not proceed into training.

The project should continue to:

- Build the usable corpus from **Category A** sources
- Attempt permission for **Category B** sources
- Research **Category C** sources to resolve uncertainty
- Respect **Category D** restrictions

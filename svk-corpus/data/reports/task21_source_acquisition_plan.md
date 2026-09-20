# Task 21: JainLLM Source Acquisition Plan

## Goal

Create a prioritized, machine-readable acquisition queue for the next corpus expansion. This is a **planning document** — no downloads, ingestion, or training happen from this queue alone.

## Files Created

| File | Description |
|------|-------------|
| `data/acquisition/source_acquisition_queue_v1.json` | 34-entry acquisition queue with P0-P3 priorities |
| `src/svk_corpus/knowledge/__init__.py` | Extended with queue validators (PRIORITIES, ACQUISITION_STATUSES, EXPECTED_USES, 4 new functions) |
| `tests/test_knowledge_contract.py` | Extended with 28 new queue validation tests |
| `data/reports/task21_source_acquisition_plan.md` | This report |

---

## Queue Summary

| Priority | Count | Description |
|----------|-------|-------------|
| P0 | 14 | Essential canonical texts + practice materials |
| P1 | 7 | Doctrinal/interpretive/commentary material |
| P2 | 7 | Teacher/biography/history material |
| P3 | 6 | Reference/comparative/lexicon material |
| **Total** | **34** | |

---

## Top P0 Sources (14)

### Canonical Texts (7)

| # | Title | Agam | Platform |
|---|-------|------|----------|
| ACQ-0001 | Acharanga Sutra — Sthanakavasi edition | AGAM-001 | JainQQ |
| ACQ-0002 | Sutrakritanga Sutra — Sthanakavasi edition | AGAM-002 | JainQQ |
| ACQ-0003 | Uttaradhyayana Sutra — Sthanakavasi edition | AGAM-013 | JainQQ |
| ACQ-0004 | Kalpa Sutra — Sthanakavasi edition | AGAM-015 | JainQQ |
| ACQ-0005 | Dashvaikalik Sutra — Sthanakavasi edition | AGAM-014 | JainQQ |
| ACQ-0006 | Nisitha Sutra — Sthanakavasi edition | AGAM-017 | JainQQ |
| ACQ-0007 | Avasyaka Sutra — Sthanakavasi edition | AGAM-018 | JainQQ |

**Rationale:** Current corpus has only English translations (SVK-1001, SVK-1002/1003) and one Hindi translation (SVK-0016). No Prakrit originals or Sthanakavasi-specific editions. JainQQ is the primary platform for Agam discovery.

### Practice Materials (7)

| # | Title | Practice | Platform |
|---|-------|----------|----------|
| ACQ-0008 | Samayik practice text — Sthanakavasi | SAMAYIK | JainQQ |
| ACQ-0009 | Pratikraman practice text — Sthanakavasi | PRATIKRAMAN | JainQQ |
| ACQ-0010 | Kayotsarga practice text — Sthanakavasi | KAYOTSARGA | JainQQ |
| ACQ-0011 | Vandana practice text — Sthanakavasi | VANDANA | JainQQ |
| ACQ-0012 | Pratyakhyan/Pachchhakhan practice text | PRATYAKHYAN | JainQQ |
| ACQ-0013 | Chauvisantho / Chaturvimshati-stava | CHAUVISANTHO | JainQQ |
| ACQ-0014 | Paryushan practice text / liturgy | PARYUSHAN | JainQQ |

**Rationale:** All 8 named practices are MISSING from the current corpus. Practice material is the single largest coverage gap. The Avashyaka Sutra (ACQ-0007) is the canonical source for most of these practices; standalone practice texts provide accessible versions.

---

## P1 Sources (7)

| # | Title | Knowledge Layer | Platform |
|---|-------|-----------------|----------|
| ACQ-0015 | Sthanakavasi doctrinal exposition — modern | TEACHER_INTERPRETATION | Jainebooks |
| ACQ-0016 | Sthanakavasi philosophy — anekantavada, syadvada | PHILOSOPHY | Jainebooks |
| ACQ-0017 | Acharya Haribhadra commentary — Sthanakavasi | COMMENTARY | JainQQ |
| ACQ-0018 | Acharya Amritchandra commentary — Sthanakavasi | COMMENTARY | JainQQ |
| ACQ-0019 | Prakrit grammar — Sthanakavasi pedagogical tradition | EDUCATIONAL | JainQQ |
| ACQ-0020 | Sthanakavasi history — tradition's own perspective | HISTORY | Jainebooks |
| ACQ-0021 | Tattvarthasutra — Sthanakavasi commentary | COMMENTARY | JainQQ |

**Rationale:** Sthanakavasi-specific doctrinal explanations, commentaries, and the tradition's own historical account are critically underrepresented. Current philosophy sources are Western scholarship (SVK-1005, SVK-1006) or general Jain (SVK-2011).

---

## P2 Sources (7)

| # | Title | Knowledge Layer | Platform |
|---|-------|-----------------|----------|
| ACQ-0022 | Pravachan collection — Sthanakavasi teachers | PRAVACHAN | Jainebooks |
| ACQ-0023 | Sthanakavasi Acharya biographies | BIOGRAPHY | Jainebooks |
| ACQ-0024 | Sthanakavasi Muni biographies | BIOGRAPHY | Jainebooks |
| ACQ-0025 | Sthanakavasi Sadhvi biographies | BIOGRAPHY | Jainebooks |
| ACQ-0026 | Sthanakavasi modern teacher material | TEACHER_INTERPRETATION | Jainebooks |
| ACQ-0027 | Sthanakavasi lineage history | HISTORY | Jainebooks |
| ACQ-0028 | Sthanakavasi magazine collection | OTHER | Jainebooks |

**Rationale:** Teacher biographies, pravachans, and modern teacher material are all MISSING from the corpus. Jainebooks is the primary discovery platform for these categories.

---

## P3 Sources (6)

| # | Title | Notes | Duplicate? |
|---|-------|-------|------------|
| ACQ-0029 | Paia-sadda-mahannavo — additional volumes | Likely duplicate of SVK-2006 | Yes |
| ACQ-0030 | Ardha Magadhi Dictionary — additional digitisations | Likely duplicate of SVK-0003 | Yes |
| ACQ-0031 | Comparative Jain traditions text | Cross-tradition distinction SFT task | No |
| ACQ-0032 | Jain philosophy — Sanskrit originals | GRETIL texts | No |
| ACQ-0033 | Woolner Introduction to Prakrit — additional editions | Likely duplicate of SVK-2008 | Yes |
| ACQ-0034 | Ardha Magadhi Dictionary — verified clearance | CC0 assertion needs verification | Yes |

---

## JainQQ Opportunities

JainQQ is the **primary platform** for:

1. **Agam discovery**: Identify which Sthanakavasi Agam texts exist, in what editions, and where hosted
2. **Canonical text acquisition**: Download or copy Prakrit originals and Sthanakavasi editions
3. **Commentary discovery**: Find traditional commentaries by Haribhadra, Amritchandra, and other Sthanakavasi acharyas
4. **Practice text discovery**: Locate Samayik, Pratikraman, and other practice guides

**14 of 34 candidates (41%) are JainQQ-sourced**, all at P0 or P1 priority.

---

## Jainebooks Opportunities

Jainebooks is the **primary platform** for:

1. **Teacher material**: Modern Sthanakavasi doctrinal exposition, pravachans
2. **Biographies**: Acharya, Muni, and Sadhvi biographies
3. **History**: Sthanakavasi institutional and lineage history from the tradition's own perspective
4. **Magazines**: Community magazines with doctrinal discussions

**14 of 34 candidates (41%) are Jainebooks-sourced**, mostly at P1-P2 priority.

**MCP note:** Jainebooks MCP is treated strictly as a catalogue/research discovery mechanism. It is NOT integrated into model inference. MCP metadata search/filter capabilities are documented for future source discovery.

---

## Practice Coverage Gaps

| Practice | Current Coverage | Candidate |
|----------|-----------------|-----------|
| SAMAYIK | MISSING | ACQ-0008 |
| PRATIKRAMAN | MISSING | ACQ-0009 |
| KAYOTSARGA | MISSING | ACQ-0010 |
| VANDANA | MISSING | ACQ-0011 |
| PRATYAKHYAN | MISSING | ACQ-0012 |
| CHAUVISANTHO | MISSING | ACQ-0013 |
| AVASHYAKA | MISSING | ACQ-0007 |
| PARYUSHAN | MISSING | ACQ-0014 |

**All 8 named practices are MISSING.** This is the most critical coverage gap in the corpus.

---

## Agam Coverage Gaps

| Agam | Current Status | Candidate |
|------|---------------|-----------|
| AGAM-001 (Acharanga) | English translation only (SVK-1001) | ACQ-0001 |
| AGAM-002 (Sutrakritanga) | English translation only (SVK-1001) | ACQ-0002 |
| AGAM-013 (Uttaradhyayana) | Hindi translation only (SVK-0016) | ACQ-0003 |
| AGAM-014 (Dashvaikalik) | Not in corpus | ACQ-0005 |
| AGAM-015 (Kalpasutra) | English translation only (SVK-1002/1003) | ACQ-0004 |
| AGAM-017 (Nisitha) | Not in corpus | ACQ-0006 |
| AGAM-018 (Avasyaka) | Not in corpus | ACQ-0007 |

**No Prakrit originals or Sthanakavasi-specific editions** are in the current corpus.

---

## Teacher/Pravachan Gaps

| Category | Current Status | Candidates |
|----------|---------------|------------|
| Acharya commentaries | MISSING | ACQ-0017, ACQ-0018, ACQ-0021 |
| Pravachans | MISSING | ACQ-0022 |
| Acharya biographies | MISSING | ACQ-0023 |
| Muni biographies | MISSING | ACQ-0024 |
| Sadhvi biographies | MISSING | ACQ-0025 |
| Modern teacher material | MISSING | ACQ-0026 |

**All teacher/pravachan categories are MISSING.** This blocks the `teacher_attribution` SFT task.

---

## Duplicate Candidates

| Candidate | Likely Duplicate Of | Action |
|-----------|-------------------|--------|
| ACQ-0029 | SVK-2006 (Paia-sadda-mahannavo) | Verify before acquiring |
| ACQ-0030 | SVK-0003 (Ardha Magadhi Dict) | Check for dedup |
| ACQ-0033 | SVK-2008 (Woolner Intro) | Verify edition differences |
| ACQ-0034 | SVK-0003 (Ardha Magadhi Dict) | CC0 clearance verification |

---

## Rights Blockers

All 34 candidates currently have `rights_status=UNKNOWN`. No rights have been cleared yet.

Key rights considerations:
- **P0 canonical texts**: Prakrit originals are likely pre-1930 (public domain by age). JainQQ editions may have uploader assertions that need verification.
- **P0 practice texts**: Many are modern publications. Rights clearance will be required.
- **P1 commentaries**: Historical commentaries (Haribhadra, Amritchandra) are likely PD. Modern commentaries need clearance.
- **P2 teacher material**: Modern publications. Rights clearance required.
- **P3 lexicons**: Some have CLEAR rights (Internet Archive). Others need verification.

---

## Recommended First Acquisition Batch

### Phase 1: Rights verification (Week 1-2)

1. Verify CC0 assertions for SVK-0003 through SVK-0006 (Ardha Magadhi Dictionary volumes)
2. Verify publication dates for SVK-0008, SVK-0009 (Sthanakavasi conference materials)
3. Assess rights for SVK-2001 (Ardha Magadhi Kosh + Maharashtri)

### Phase 2: JainQQ exploration (Week 2-4)

1. Explore JainQQ catalogue for Sthanakavasi Agam editions
2. Identify which P0 canonical texts are available in machine-readable form
3. Discover practice texts (Samayik, Pratikraman, etc.)
4. Register all discovered sources in the acquisition queue

### Phase 3: Jainebooks exploration (Week 3-5)

1. Search Jainebooks catalogue for Sthanakavasi-specific titles
2. Identify modern teacher material and pravachans
3. Discover biography and history material
4. Register all discovered sources in the acquisition queue

### Phase 4: First acquisitions (Week 5-8)

1. Acquire P0 canonical texts with verified rights
2. Acquire P0 practice texts with verified rights
3. Begin rights review for P1 sources

---

## Tests

29 new tests added to `tests/test_knowledge_contract.py`:
- Candidate validation (12 tests)
- Queue validation (2 tests)
- P0 restricted rights check (2 tests)
- SFT without clear rights check (2 tests)
- Queue loading and validation against actual file (4 tests)
- Hard rule enforcement (4 tests)

**Full test suite: 316/316 tests pass (287 existing + 29 new)**

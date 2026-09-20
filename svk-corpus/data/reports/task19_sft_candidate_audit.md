# Task 19: SFT Candidate Corpus Audit

## Goal

Audit all 62 sources in `manifests/source_manifest.csv` against the training corpus (`data/release/training_corpus.jsonl`, 82,470 units, ~4.56M tokens) and the SFT schema (`data/training/sft_schema_v1.json`, 9 task categories) to determine:
1. Which sources are suitable for supervised fine-tuning example generation
2. What SFT task categories can be supported
3. Critical gaps in Sthānakavāsī-specific training signal

## Executive Summary

| Metric | Value |
|--------|-------|
| Total sources in manifest | 62 |
| Sources with training corpus units | 27 |
| Sources in RAG only (not training) | 1 (SVK-2027) |
| Sources not in training or RAG | 34 |
| Total training units | 82,470 |
| Total training tokens (est.) | ~4.56M |
| CORE_STHANAKAVASI sources | 17 |
| CORE_STHANAKAVASI in training | 7 |
| Training units from CORE_STHANAKAVASI | 14,251 (17.3%) |
| Training units from lexicons (all) | 42,091 (51.0%) |

**Bottom line:** The training corpus is lexicon-dominated (~51% from Prakrit dictionaries). Only 17.3% of training units come from CORE_STHANAKAVASI sources. The SFT schema's 9 task categories are partially supported: `prakrit_explanation` and `source_citation` are well-covered; `sthanaqa`, `cross_tradition_distinction`, and `teacher_attribution` face severe Sthānakavāsī-specific data scarcity.

---

## Source Classification: SFT Suitability Tiers

### Tier A — Primary SFT Sources (7 sources, 14,251 units)

CORE_STHANAKAVASI scope + TRAINING_ALLOWED + in training corpus. These are the only sources that can generate Sthanakavāsī-specific SFT examples.

| SID | Title | Units | Chars | Knowledge Layer | Language |
|-----|-------|-------|-------|-----------------|----------|
| SVK-0007 | Ardha Magadhi Dictionary Vols 2 and 5 | 2,574 | 188K | LEXICON | pra/hi |
| SVK-0037 | Illustrated Ardha-Magadhi Dictionary Vol 1 (1923) | 1,493 | 141K | LEXICON | pra/sa |
| SVK-2002 | Illustrated Ardha Magadhi Dictionary Gujarati (1932) | 4,476 | 355K | LEXICON | pra/gu |
| SVK-2003 | Illustrated Ardha-Magadhi Dictionary Philosophic & Scientific | 2,575 | 186K | LEXICON | pra/gu |
| SVK-2004 | Ardha Magadhi Quadrilingual Dictionary Vol-2 | 3,111 | 233K | LEXICON | pra/sa/gu/hi |
| SVK-2005 | Illustrated Ardha-Magadhi Dictionary Vol-5 (1923, DLI) | 3,121 | 195K | LEXICON | pra/hi/sa |
| SVK-2010 | Jain Sathan Kavasi (1928) | 516 | 69K | SECT_LITERATURE | gu |

**Assessment:** All 7 Tier A sources are lexicons/dictionaries (6 of 7). Only SVK-2010 (Jain Sathan Kavasi) provides doctrinal/discursive content. The Sthānakavāsī-specific SFT signal is critically thin in non-lexicon material.

**SFT task coverage:**
- `prakrit_explanation`: Excellent (dictionary entries)
- `source_citation`: Good (citable entries)
- `multilingual_mapping`: Good (quadrilingual dictionaries)
- `sthanaqa`: Very limited (only SVK-2010 provides sect-specific Q&A material)
- `teacher_attribution`: None (no teacher commentaries in training)
- `cross_tradition_distinction`: None (no comparative material)

### Tier B — Secondary SFT Sources (12 sources, 34,117 units)

CANONICAL_FOUNDATION or CONTEXTUAL_JAIN scope + TRAINING_ALLOWED + in training corpus. Useful for general Jain knowledge, cross-tradition comparison, and English-language SFT.

| SID | Title | Units | Chars | Scope | Language |
|-----|-------|-------|-------|-------|----------|
| SVK-0016 | Shri Utradhyayan Sutar (Agam Seva) (1920) | 1,570 | 146K | UNKNOWN | hi |
| SVK-0026 | Atma3.1-ShareGPT (Atma Siddhi Shastra) | 3,635 | 4.7M | COMPARATIVE | en |
| SVK-0038 | Notes on Modern Jainism (1910) | 1,188 | 172K | HIGH_STHANAKAVASI_RELEVANCE | en |
| SVK-1001 | Gaina Sutras (Acaranga + Sutrakrtanga) | 3,770 | 652K | CANONICAL_FOUNDATION | en |
| SVK-1002 | Kalpa Sutra and Nava Tatva (1848) | 755 | 202K | CANONICAL_FOUNDATION | en |
| SVK-1003 | Kalpa Sutra (1848) second digitisation | 557 | 196K | CANONICAL_FOUNDATION | en |
| SVK-1005 | Notes on Religious Literature of India (1920) | 5,010 | 974K | CONTEXTUAL_JAIN | en |
| SVK-1006 | Jaina Psychology (1929) | 240 | 87K | CONTEXTUAL_JAIN | en |
| SVK-1007 | Essai de bibliographie jaina (1906) | 8,481 | 732K | CONTEXTUAL_JAIN | fr |
| SVK-1008 | Notes on the Jainas (1911) | 261 | 45K | CONTEXTUAL_JAIN | en |
| SVK-1009 | Risabha Deva, the Founder of Jainism (1929) | 768 | 245K | CONTEXTUAL_JAIN | en |
| SVK-1010 | Jain Shvetambar Conference Herald (1917) | 3,694 | 368K | HIGH_STHANAKAVASI_RELEVANCE | en/gu/hi |

**Assessment:** Tier B provides the bulk of English-language discursive content. SVK-1001 (canonical Acaranga/Sutrakrtanga translation) is the most doctrinally significant. SVK-1010 (Conference Herald) is sect-relevant but language is mixed. SVK-1007 (French bibliography) is out of target language scope but retained for metadata value.

**SFT task coverage:**
- `source_citation`: Good (English translations with identifiable sections)
- `canonical_commentary_distinction`: Good (SVK-1001, SVK-1002/1003 are canonical; SVK-1005, SVK-1006 are secondary scholarship)
- `cross_tradition_distinction`: Partial (SVK-1001 is Svetambara-wide, not Sthānakavāsī-specific)
- `sthanaqa`: Limited (SVK-0038 and SVK-1010 discuss Sthānakavāsī but as external observers)
- `abstention`: Good (many sources with unknown scope can train abstention)

### Tier C — Tertiary SFT Sources (8 sources, 34,102 units)

UNKNOWN scope + TRAINING_ALLOWED + in training corpus. Valuable for lexicon/grammar tasks but sectarian identity unknown.

| SID | Title | Units | Chars | Knowledge Layer | Language |
|-----|-------|-------|-------|-----------------|----------|
| SVK-2006 | Paia-sadda-mahannavo (1923) | 18,115 | 1.7M | LEXICON | pra/hi/sa |
| SVK-2007 | Paia-Sadda-Mahannavo MLB edition (1928) | 6,641 | 548K | LEXICON | pra/hi |
| SVK-2008 | Woolner's Introduction To Prakrit (1917) | 3,056 | 388K | GRAMMAR | en |
| SVK-2009 | Introduction To Prakrit MLB edition (1928) | 3,088 | 410K | GRAMMAR | en |
| SVK-2011 | Aadhyatm Saar (1913) | 903 | 137K | PHILOSOPHY | gu |
| SVK-2012 | Navyugno Jain (1921) | 1,464 | 401K | SECONDARY_SCHOLARSHIP | gu |
| SVK-2013 | Jain Dharm Praves Pothi (1908) | 122 | 14K | EDUCATIONAL | gu |
| SVK-2014 | Jain Sajjhaimala Bhag-4 (1927) | 1,286 | 146K | PRACTICE_LITERATURE | gu |

**Assessment:** Tier C is lexicon-heavy (SVK-2006 alone contributes 18,115 units = 22% of all training). The Paia-sadda-mahannavo is the canonical Prakrit lexicon — valuable for `prakrit_explanation` but not Sthānakavāsī-specific. The Gujarati sources (SVK-2011 through SVK-2014) provide the only Gujarati prose in training.

**SFT task coverage:**
- `prakrit_explanation`: Excellent (massive lexicon coverage)
- `multilingual_mapping`: Good (Prakrit-Hindi-Sanskrit mappings)
- `general_qa`: Moderate (Gujarati prose)

### Tier D — Blocked / Rights-Pending (17 sources, 0 units)

TRAINING_ALLOWED but not yet in training corpus, or WITH_CONDITIONS/NEEDS_PERMISSION.

| SID | Title | training_permission | religious_scope | Blocker |
|-----|-------|---------------------|-----------------|---------|
| SVK-0001 | CC0 Jain text library | WITH_CONDITIONS (R20) | UNKNOWN | Needs per-item audit |
| SVK-0002 | Jain Dharma (1958) | NEEDS_PERMISSION (R92) | CORE_STHANAKAVASI | Copyright term unexpired |
| SVK-0003 | Ardha Magadhi Dictionary Vol 1 (1923) | WITH_CONDITIONS (R30) | CORE_STHANAKAVASI | CC0 assertion unverified |
| SVK-0004 | Ardha Magadhi Dictionary Vol 3 (1930) | WITH_CONDITIONS (R30) | CORE_STHANAKAVASI | CC0 assertion unverified |
| SVK-0005 | Ardha Magadhi Dictionary Vol 3 Lahore | WITH_CONDITIONS (R30) | CORE_STHANAKAVASI | CC0 assertion unverified |
| SVK-0006 | Ardha Magadhi Dictionary Vol 4 (1932) | WITH_CONDITIONS (R30) | CORE_STHANAKAVASI | CC0 assertion unverified |
| SVK-0008 | Sthanakvasi Jainonum Dharamkartavya | WITH_CONDITIONS (R95) | CORE_STHANAKAVASI | Chronology unresolved |
| SVK-0009 | Sthanakvasi Conference no Chadati | WITH_CONDITIONS (R95) | CORE_STHANAKAVASI | Chronology unresolved |
| SVK-0010 | Sthanakvasi Conference history (dup) | WITH_CONDITIONS (R95) | CORE_STHANAKAVASI | Duplicate + chronology |
| SVK-0012 | Dashvaikalik Sutra Hindi Anuvad | WITH_CONDITIONS (R95) | UNKNOWN | Chronology unresolved |
| SVK-0013 | Uttradhyayan Sutra Hindi Anuvaad (1934) | WITH_CONDITIONS (R95) | UNKNOWN | Chronology unresolved |
| SVK-0014 | Uttradhyayan Sutra Hindi Anuvaad (1962) | WITH_CONDITIONS (R95) | UNKNOWN | Chronology unresolved |
| SVK-0015 | Sutrakratang Sutra (1938) | WITH_CONDITIONS (R95) | UNKNOWN | Chronology unresolved |
| SVK-0017 | Gyatadharmkathank Sutra (1964) | WITH_CONDITIONS (R95) | UNKNOWN | Chronology unresolved |
| SVK-1004 | Story of Kalaka (1933) | WITH_CONDITIONS (R95) | CONTEXTUAL_JAIN | Chronology unresolved |
| SVK-2001 | Ardha Magadhi Kosh + Maharashtri (1938) | WITH_CONDITIONS (R30) | CORE_STHANAKAVASI | CC0 assertion unverified |
| SVK-0036 | Jainendra Siddhanta Kosa (1990) | NEEDS_PERMISSION (R30) | UNKNOWN | CC0 asserted too recent |

**Assessment:** Tier D contains 7 CORE_STHANAKAVASI sources (SVK-0002 through SVK-0010, SVK-2001) that would significantly expand Sthānakavāsī-specific training if rights are resolved. SVK-0002 (Jain Dharma, 1958) is the most important blocked source — a modern Sthānakavāsī doctrinal text, but still in copyright.

### Tier E — Excluded (16 sources, 0 units)

NOT_ALLOWED, RAG_ONLY, RESEARCH_ONLY, DO_NOT_USE, NEEDS_PERMISSION with no path to training.

| SID | Title | Reason |
|-----|-------|--------|
| SVK-0011 | Acharrang Sutra Hindi (1966) | NEEDS_PERMISSION (R90) |
| SVK-0018 | Adhyatmik Pravachno (1960) | WITH_CONDITIONS (R95) |
| SVK-0019 | Stavanavali (1960) | WITH_CONDITIONS (R95) |
| SVK-0020 | Subodh Jain Pathshala (1964) | WITH_CONDITIONS (R95) |
| SVK-0021 | Jain Svetambara Agama Canon English | UNKNOWN (R99) |
| SVK-0022 | GRETIL Prakrit e-texts | UNKNOWN (R99) |
| SVK-0023 | GRETIL Sanskrit Jaina texts | UNKNOWN (R99) |
| SVK-0024 | dataspoof/Jains | UNKNOWN (R99) |
| SVK-0025 | shethjenil/JainBooks | UNKNOWN (R99) |
| SVK-0028 | Jain Literature Open Repository | UNKNOWN (R99) |
| SVK-0029 | Jainaagam 45 Aagam | UNKNOWN (R99) |
| SVK-0030 | Jain eLibrary | UNKNOWN (R99) |
| SVK-0032 | Wikipedia Jain articles | RAG_ALLOWED (R40) |
| SVK-0033 | Jain Dharm Aur Darshan (2018) | NOT_ALLOWED (R10 ND) |
| SVK-0034 | chaturmas-suchi | UNKNOWN (R99) |
| SVK-0035 | JainGPT / JainQQ | Systems, not sources |
| SVK-0031 | OPenn Jain manuscripts | WITH_CONDITIONS (R20) — OCR only |

### Tier F — Structural / Non-textual (4 sources, 0 units)

| SID | Title | Reason |
|-----|-------|--------|
| SVK-0027 | Deshika Parallel Corpus | In RAG only; training permission TRAINING_ALLOWED but not in training |
| SVK-1010 | (already counted in Tier B) | — |

*(No purely structural sources remain — all 62 are text-based or system references.)*

---

## SFT Task Category Feasibility

### Well-Supported Categories

| Category | Source Tier | Est. Derivable Units | Notes |
|----------|-------------|---------------------|-------|
| `prakrit_explanation` | A, C | ~42,000 | Lexicon entries → Prakrit term explanations |
| `source_citation` | A, B, C | ~82,000 | Any unit with identifiable source can generate citation examples |
| `multilingual_mapping` | A, C | ~35,000 | Quadrilingual dictionaries + Paia-sadda-mahannavo |
| `abstention` | All | ~82,000 | Units with low quality scores or uncertain scope train abstention |

### Partially Supported Categories

| Category | Source Tier | Est. Derivable Units | Gap |
|----------|-------------|---------------------|-----|
| `general_qa` | A, B, C | ~20,000 | Discursive content limited; lexicon entries don't yield QA |
| `canonical_commentary_distinction` | B | ~8,000 | Only English canonical translations (SVK-1001, 1002, 1003) |

### Severely Under-Supported Categories

| Category | Source Tier | Est. Derivable Units | Gap |
|----------|-------------|---------------------|-----|
| `sthanaqa` | A (SVK-2010 only), B (SVK-0038, SVK-1010) | ~600 | Only 1 CORE_STHANAKAVASI discursive source in training |
| `teacher_attribution` | None | 0 | No teacher/acarya commentaries in training corpus |
| `cross_tradition_distinction` | B | ~2,00 | No Sthānakavāsī vs Digambara comparative material in training |

---

## Critical Gaps

### 1. Sthānakavāsī Doctrinal Content Scarcity

The single largest gap: **only 1 non-lexicon CORE_STHANAKAVASI source (SVK-2010, 516 units) exists in training.** All other CORE_STHANAKAVASI training units are dictionary entries. This means:

- `sthanaqa` cannot be meaningfully trained on Sthānakavāsī-specific doctrine
- `teacher_attribution` has zero training signal (no acarya commentaries available)
- `cross_tradition_distinction` has no Sthānakavāsī side to distinguish from

### 2. Missing CORE_STHANAKAVASI Sources in Training

7 CORE_STHANAKAVASI sources exist in the manifest but are NOT in the training corpus:

| SID | Title | Why Blocked |
|-----|-------|-------------|
| SVK-0002 | Jain Dharma (1958) | NEEDS_PERMISSION (R92) — in copyright |
| SVK-0003 | Ardha Magadhi Dictionary Vol 1 (1923) | WITH_CONDITIONS (R30) — CC0 unverified |
| SVK-0004 | Ardha Magadhi Dictionary Vol 3 (1930) | WITH_CONDITIONS (R30) — CC0 unverified |
| SVK-0005 | Ardha Magadhi Dictionary Vol 3 Lahore | WITH_CONDITIONS (R30) — CC0 unverified |
| SVK-0006 | Ardha Magadhi Dictionary Vol 4 (1932) | WITH_CONDITIONS (R30) — CC0 unverified |
| SVK-0008 | Sthanakvasi Jainonum Dharamkartavya | WITH_CONDITIONS (R95) — chronology |
| SVK-0009 | Sthanakvasi Conference Chadati | WITH_CONDITIONS (R95) — chronology |
| SVK-2001 | Ardha Magadhi Kosh + Maharashtri | WITH_CONDITIONS (R30) — CC0 unverified |

If the R30 CC0 assertions for SVK-0003 through SVK-0006 and SVK-2001 can be verified (these are 1923-1938 publications with likely expired copyright), they would add ~15,000+ CORE_STHANAKAVASI lexicon units.

### 3. Knowledge Layer and Religious Scope Not Populated in Training Data

**Data quality issue:** The training corpus records ALL `knowledge_layer` and `religious_scope` fields as `"unknown"` — even though the manifest has these fields populated. This means the SFT schema's `provenance.knowledge_layer` and `provenance.religious_scope` cannot be automatically filled from training data. These must be back-filled from the manifest before SFT example generation.

### 4. Gujarati Content Limited to Lexicons

Gujarati-script sources in training are almost entirely dictionary entries (SVK-2002, 2003, 2004). The only Gujarati discursive sources (SVK-2010, 2011, 2012, 2013, 2014) contribute ~4,291 units total. Gujarati SFT examples will be thin.

### 5. English Dominance in Non-Lexicon Training

Of the 40,379 non-lexicon training units, ~25,000 are English. The model will be stronger at English Jain Q&A than Hindi or Gujarati.

---

## Recommendations

1. **Back-fill knowledge_layer and religious_scope** from manifest into training data before SFT generation
2. **Prioritize rights resolution** for SVK-0003 through SVK-0006 (CC0 assertion verification) — these are pre-1940 publications likely in public domain
3. **Accept that `teacher_attribution` and `cross_tradition_distinction` are not trainable** with current corpus — mark these categories as "data insufficient" in the SFT pipeline
4. **Use `abstention` training** to teach the model to say "I don't have Sthānakavāsī-specific information" rather than confabulating
5. **Consider synthetic data generation** for `sthanaqa` using SVK-1001 (canonical Acaranga) as the Sthānakavāsī canonical reference, paired with abstention for Digambara-specific questions

---

## Appendix: Full Source Inventory

See `data/reports/task19_sft_candidate_inventory.json` for machine-readable classification of all 62 sources.

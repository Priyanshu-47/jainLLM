# TASK 62 SFT REVIEW — Queue A
**Queue**: QUEUE A - SOURCE ATTRIBUTION
**Reason**: Task 60: unsupported source-attributed claims 6 -> 20 under DAPT-01.
**Candidates**: 39

## CRITERIA (check EACH candidate)
| # | Criterion | What to check | Priority |
|---|-----------|---------------|----------|
| 1 | qa_alignment | Answer actually answers the question? | Normal |
| 2 | source_grounding | Every factual claim supported by source quote? | HIGH |
| 3 | attribution | No commentary→Mahavira, teacher→canonical confusion? | HIGH |
| 4 | sect_distinction | No Sthanakavasi claim turned into universal Jain claim? | Normal |
| 5 | knowledge_layer | Canonical vs commentary preserved? | Normal |
| 6 | abstention | For evidence gaps, declines instead of inventing? | Normal |
| 7 | practice | Practice identity/tradition attribution correct? | Normal |
| 8 | language | Prakrit/Sanskrit terminology sound? | Normal |
| 9 | language_quality | Natural, grammatical phrasing? | Normal |
| 10 | no_fabrication | No invented citations/teachers/dates? | HIGH |
| 11 | pedagogy | Teaches source-aware behaviour? | Normal |

## OUTPUT FORMAT
Return JSONL, one line per candidate:
```json
{"review_id": "T61-CAND-0001", "decision": "APPROVE|REVISE|REJECT", "failed_criteria": ["name"], "notes": "reason", "revised_answer": ""}
```
- **APPROVE**: passes all HIGH criteria, no critical issues
- **REVISE**: fixable issues (specify failed criteria + revised_answer)
- **REJECT**: fundamentally flawed (fabrication, wrong sect, wrong attribution)

---

### T61-CAND-0001 (pos 1)
- Category: SOURCE_ATTRIBUTION | Priority: attribution, no_fabrication, source_grounding
- Source: Agam 03 Ang 03 Sthanang Sutra Part 01 Sthanakvasi (SVK-2025)
- Sect: STHANAKAVASI (HIGH) | Layer: CANONICAL_SCRIPTURE
- Rights: TRAINING_ALLOWED_WITH_PERMISSION_EVIDENCE | Split: validation

**Q**: According to the catalog header of "Agam 03 Ang 03 Sthanang Sutra Part 01 Sthanakvasi", who authored and published it?

**A**: The header records: "Author(s): Amarmuni, Shreechand Surana" It lists Amarmuni, Shreechand Surana as author(s) and Padma Prakashan as publisher.

**Evidence**: Author(s): Amarmuni, Shreechand Surana
**Source text**: Book Title: Agam 03 Ang 03 Sthanang Sutra Part 01 Sthanakvasi
Author(s): Amarmuni, Shreechand Surana
Publisher: Padma Prakashan
Catalog link: https://jainqq.org/explore/002905/1
- Citation: [Author(s): Amarmuni, Shreechand Surana](https://jainqq.org/explore/002905)
**Rights flags**: MANIFEST_RIGHTS_STALE: manifest training_permission='NEEDS_PERMISSION (R93_RESTRICTIVE_TERMS)' but permission evidence file reports PERMISSION_GRANTED

---

### T61-CAND-0002 (pos 2)
- Category: SOURCE_ATTRIBUTION | Priority: attribution, no_fabrication, source_grounding
- Source: Agam 29 Mool 02 Dasvaikalik Sutra Sthanakvasi (SVK-2026)
- Sect: STHANAKAVASI (HIGH) | Layer: CANONICAL_SCRIPTURE
- Rights: TRAINING_ALLOWED_WITH_PERMISSION_EVIDENCE | Split: test

**Q**: According to the catalog header of "Agam 29 Mool 02 Dasvaikalik Sutra Sthanakvasi", who authored and published it?

**A**: The header records: "Author(s): Shayyambhavsuri, Amarmuni, Shreechand Surana, Purushottamsingh Sardar, Harvindarsingh Sardar" It lists Shayyambhavsuri, Amarmuni, Shreechand Surana, Purushottamsingh Sardar, Harvindarsingh Sardar as author(s) and Padma Prakashan as publisher.

**Evidence**: Author(s): Shayyambhavsuri, Amarmuni, Shreechand Surana, Purushottamsingh Sardar, Harvindarsingh Sardar
**Source text**: Book Title: Agam 29 Mool 02 Dasvaikalik Sutra Sthanakvasi
Author(s): Shayyambhavsuri, Amarmuni, Shreechand Surana, Purushottamsingh Sardar, Harvindarsingh Sardar
Publisher: Padma Prakashan
Catalog link: https://jainqq.org/explore/007649/1
- Citation: [Author(s): Shayyambhavsuri, Amarmuni, Shreechand Surana, Purushottamsingh Sardar, Harvindarsingh Sardar](https://jainqq.org/explore/007649)
**Rights flags**: MANIFEST_RIGHTS_STALE: manifest training_permission='NEEDS_PERMISSION (R93_RESTRICTIVE_TERMS)' but permission evidence file reports PERMISSION_GRANTED

---

### T61-CAND-0003 (pos 3)
- Category: SOURCE_ATTRIBUTION | Priority: attribution, no_fabrication, source_grounding
- Source: Sthanakvasi Jain Itihas (SVK-2027)
- Sect: STHANAKAVASI (HIGH) | Layer: MIXED
- Rights: TRAINING_ALLOWED_WITH_PERMISSION_EVIDENCE | Split: test

**Q**: According to the catalog header of "Sthanakvasi Jain Itihas", who authored and published it?

**A**: The header records: "Author(s): Kesrichand Bhandari" It lists Kesrichand Bhandari as author(s) and Sthanakvasi Jain Karyalay as publisher.

**Evidence**: Author(s): Kesrichand Bhandari
**Source text**: Book Title: Sthanakvasi Jain Itihas
Author(s): Kesrichand Bhandari
Publisher: Sthanakvasi Jain Karyalay
Catalog link: https://jainqq.org/explore/020753/1
- Citation: [Author(s): Kesrichand Bhandari](https://jainqq.org/explore/020753)
**Rights flags**: MANIFEST_RIGHTS_STALE: manifest training_permission='NEEDS_PERMISSION (R93_RESTRICTIVE_TERMS)' but permission evidence file reports PERMISSION_GRANTED

---

### T61-CAND-0005 (pos 4)
- Category: SOURCE_ATTRIBUTION | Priority: attribution, no_fabrication, source_grounding
- Source: Ardha Magadhi Dictionary Vols 2 and 5 (1927; 1938) (SVK-0007)
- Sect: STHANAKAVASI (MEDIUM) | Layer: LEXICON
- Rights: TRAINING_ALLOWED | Split: train

**Q**: Who is listed as the author of Ardha Magadhi Dictionary Vols 2 and 5 (1927; 1938)?

**A**: The corpus manifest records Ardha Magadhi Dictionary Vols 2 and 5 (1927; 1938) as written by Muni Ratnachandraji in 1927. It is classified as LEXICON material with CORE_STHANAKAVASI scope.

- Citation: [](https://archive.org/details/in.ernet.dli.2015.327411)

---

### T61-CAND-0006 (pos 5)
- Category: SOURCE_ATTRIBUTION | Priority: attribution, no_fabrication, source_grounding
- Source: Shri Utradhyayan Sutar (Agam Seva) (1920) (SVK-0016)
- Sect: UNKNOWN (UNKNOWN) | Layer: CANONICAL_SCRIPTURE
- Rights: TRAINING_ALLOWED | Split: train

**Q**: What kind of text is Shri Utradhyayan Sutar (Agam Seva) (1920) - a canonical scripture, a commentary, or a later study?

**A**: The manifest records Shri Utradhyayan Sutar (Agam Seva) (1920) as PRIMARY CANON (Mulasutra material. Its canonical status is derived as CANONICAL.

- Citation: [](https://archive.org/details/in.ernet.dli.2015.545305)

---

### T61-CAND-0007 (pos 6)
- Category: SOURCE_ATTRIBUTION | Priority: attribution, no_fabrication, source_grounding
- Source: Atma3.1-ShareGPT (Atma Siddhi Shastra) (SVK-0026)
- Sect: GENERIC_JAIN (UNKNOWN) | Layer: MIXED
- Rights: TRAINING_ALLOWED | Split: train

**Q**: Which publisher and publication year are recorded for Atma3.1-ShareGPT (Atma Siddhi Shastra)?

**A**: The manifest records Atma3.1-ShareGPT (Atma Siddhi Shastra) as published by unknown in 2024; its recorded license basis is apache-2.0.

- Citation: [](https://huggingface.co/datasets/HappyAIUser/Atma3.1-ShareGPT)

---

### T61-CAND-0008 (pos 7)
- Category: SOURCE_ATTRIBUTION | Priority: attribution, no_fabrication, source_grounding
- Source: Deshika - Maharashtri Prakrit to English Parallel Corpus (SVK-0027)
- Sect: UNKNOWN (UNKNOWN) | Layer: MIXED
- Rights: TRAINING_ALLOWED | Split: train

**Q**: Which tradition and sect does the manifest record for Deshika - Maharashtri Prakrit to English Parallel Corpus?

**A**: The manifest records Deshika - Maharashtri Prakrit to English Parallel Corpus under tradition JAIN plus classical, sect UNKNOWN (confidence unknown), with classification basis recorded as insufficient_evidence.

- Citation: [](https://huggingface.co/datasets/VIITPune/Deshika-Maharashtri_Prakrit_to_English_Parallel_Corpus)

---

### T61-CAND-0009 (pos 8)
- Category: SOURCE_ATTRIBUTION | Priority: attribution, no_fabrication, source_grounding
- Source: An Illustrated Ardha-Magadhi Dictionary Vol 1 (1923) university copy (SVK-0037)
- Sect: STHANAKAVASI (MEDIUM) | Layer: LEXICON
- Rights: TRAINING_ALLOWED | Split: train

**Q**: Is An Illustrated Ardha-Magadhi Dictionary Vol 1 (1923) university copy specific to the Sthanakavasi tradition or general Jain material?

**A**: The manifest classifies An Illustrated Ardha-Magadhi Dictionary Vol 1 (1923) university copy with religious scope CORE_STHANAKAVASI on the basis of Publisher imprint (SS Jain Conference) per bibliographic record; third digitisation of the same volume. That is a manifest classification of the source, not a doctrinal judgement.

- Citation: [](https://archive.org/details/ksu.u3791.illustratedardha0000acwo)

---

### T61-CAND-0010 (pos 9)
- Category: SOURCE_ATTRIBUTION | Priority: attribution, no_fabrication, source_grounding
- Source: Notes on Modern Jainism (1910) (SVK-0038)
- Sect: UNKNOWN (HIGH) | Layer: MIXED
- Rights: TRAINING_ALLOWED | Split: train

**Q**: What is the recorded provenance of Notes on Modern Jainism (1910)?

**A**: The manifest records Notes on Modern Jainism (1910) as acquired from Internet Archive, with recorded training permission TRAINING_ALLOWED (R70_PRE_1930_PUBLICATION) and license basis public domain (pre-1929). The recorded source URL is kept in the citations metadata.

- Citation: [](https://archive.org/details/notesonmodernjai00steviala)

---

### T61-CAND-0011 (pos 10)
- Category: SOURCE_ATTRIBUTION | Priority: attribution, no_fabrication, source_grounding
- Source: Gaina Sutras (Sacred Books of the East): Acaranga and Sutrakrtanga (SVK-1001)
- Sect: SVETAMBARA (LOW) | Layer: CANONICAL_SCRIPTURE
- Rights: TRAINING_ALLOWED | Split: train

**Q**: Who is listed as the author of Gaina Sutras (Sacred Books of the East): Acaranga and Sutrakrtanga?

**A**: The corpus manifest records Gaina Sutras (Sacred Books of the East): Acaranga and Sutrakrtanga as written by Hermann Jacobi (translator) in 1884. It is classified as PRIMARY CANON (Anga material with CANONICAL_FOUNDATION scope.

- Citation: [](https://archive.org/details/gainastras01aco)

---

### T61-CAND-0012 (pos 11)
- Category: SOURCE_ATTRIBUTION | Priority: attribution, no_fabrication, source_grounding
- Source: The Kalpa Sutra and Nava Tatva (1848) second digitisation (SVK-1003)
- Sect: SVETAMBARA (LOW) | Layer: CANONICAL_SCRIPTURE
- Rights: TRAINING_ALLOWED | Split: train

**Q**: Which publisher and publication year are recorded for The Kalpa Sutra and Nava Tatva (1848) second digitisation?

**A**: The manifest records The Kalpa Sutra and Nava Tatva (1848) second digitisation as published by unknown in 1848; its recorded license basis is public domain (Internet Archive rights statement).

- Citation: [](https://archive.org/details/kalpasutraandna00bhadgoog)

---

### T61-CAND-0013 (pos 12)
- Category: SOURCE_ATTRIBUTION | Priority: attribution, no_fabrication, source_grounding
- Source: Notes on the Religious Literature of India (1920) (SVK-1005)
- Sect: MULTI_TRADITION (UNKNOWN) | Layer: SECONDARY_SCHOLARSHIP
- Rights: TRAINING_ALLOWED | Split: train

**Q**: Which tradition and sect does the manifest record for Notes on the Religious Literature of India (1920)?

**A**: The manifest records Notes on the Religious Literature of India (1920) under tradition JAIN plus other traditions, sect MULTI_TRADITION (confidence not recorded), with classification basis recorded as not recorded.

- Citation: [](https://archive.org/details/anoutlinereligi00farqgoog)

---

### T61-CAND-0014 (pos 13)
- Category: SOURCE_ATTRIBUTION | Priority: attribution, no_fabrication, source_grounding
- Source: Jaina Psychology (1929) (SVK-1006)
- Sect: UNKNOWN (UNKNOWN) | Layer: SECONDARY_SCHOLARSHIP
- Rights: TRAINING_ALLOWED | Split: train

**Q**: Is Jaina Psychology (1929) specific to the Sthanakavasi tradition or general Jain material?

**A**: The manifest classifies Jaina Psychology (1929) with religious scope CONTEXTUAL_JAIN on the basis of 1929 Jain psychology study; author unconfirmed. That is a manifest classification of the source, not a doctrinal judgement.

- Citation: [](https://archive.org/details/jaina-psychology)

---

### T61-CAND-0015 (pos 14)
- Category: SOURCE_ATTRIBUTION | Priority: attribution, no_fabrication, source_grounding
- Source: Essai de bibliographie jaina (1906) (SVK-1007)
- Sect: UNKNOWN (UNKNOWN) | Layer: REFERENCE
- Rights: TRAINING_ALLOWED | Split: train

**Q**: What is the recorded provenance of Essai de bibliographie jaina (1906)?

**A**: The manifest records Essai de bibliographie jaina (1906) as acquired from Internet Archive, with recorded training permission TRAINING_ALLOWED (R60_INSTITUTION_RIGHTS_STATEMENT) and license basis public domain (Internet Archive rights statement). The recorded source URL is kept in the citations metadata.

- Citation: [](https://archive.org/details/essaidebibliogr01gugoog)

---

### T61-CAND-0016 (pos 15)
- Category: SOURCE_ATTRIBUTION | Priority: attribution, no_fabrication, source_grounding
- Source: Risabha Deva, the Founder of Jainism (1929) (SVK-1009)
- Sect: UNKNOWN (UNKNOWN) | Layer: SECONDARY_SCHOLARSHIP
- Rights: TRAINING_ALLOWED | Split: train

**Q**: What kind of text is Risabha Deva, the Founder of Jainism (1929) - a canonical scripture, a commentary, or a later study?

**A**: The manifest records Risabha Deva, the Founder of Jainism (1929) as SECONDARY SCHOLARSHIP material. Its canonical status is derived as SECONDARY_SCHOLARSHIP.

- Citation: [](https://archive.org/details/in.gov.ignca.15558)

---

### T61-CAND-0017 (pos 16)
- Category: SOURCE_ATTRIBUTION | Priority: attribution, no_fabrication, source_grounding
- Source: Jain Shvetambar Conference Herald, Varsh 13 (1917) (SVK-1010)
- Sect: UNKNOWN (UNKNOWN) | Layer: MIXED
- Rights: TRAINING_ALLOWED | Split: train

**Q**: Which publisher and publication year are recorded for Jain Shvetambar Conference Herald, Varsh 13 (1917)?

**A**: The manifest records Jain Shvetambar Conference Herald, Varsh 13 (1917) as published by unknown in 1917; its recorded license basis is none declared.

- Citation: [](https://archive.org/details/in.ernet.dli.2015.543343)

---

### T61-CAND-0018 (pos 17)
- Category: SOURCE_ATTRIBUTION | Priority: attribution, no_fabrication, source_grounding
- Source: An Illustrated Ardha Magadhi Dictionary Gujarati (1932) (SVK-2002)
- Sect: STHANAKAVASI (MEDIUM) | Layer: LEXICON
- Rights: TRAINING_ALLOWED | Split: train

**Q**: Which tradition and sect does the manifest record for An Illustrated Ardha Magadhi Dictionary Gujarati (1932)?

**A**: The manifest records An Illustrated Ardha Magadhi Dictionary Gujarati (1932) under tradition JAIN, sect STHANAKAVASI (confidence medium), with classification basis recorded as publisher_imprint.

- Citation: [](https://archive.org/details/in.ernet.dli.2015.399871)

---

### T61-CAND-0019 (pos 18)
- Category: SOURCE_ATTRIBUTION | Priority: attribution, no_fabrication, source_grounding
- Source: An Illustrated Ardha Magadhi Dictionary Philosophic & Scientific (1930) (SVK-2003)
- Sect: STHANAKAVASI (MEDIUM) | Layer: LEXICON
- Rights: TRAINING_ALLOWED | Split: train

**Q**: Is An Illustrated Ardha Magadhi Dictionary Philosophic & Scientific (1930) specific to the Sthanakavasi tradition or general Jain material?

**A**: The manifest classifies An Illustrated Ardha Magadhi Dictionary Philosophic & Scientific (1930) with religious scope CORE_STHANAKAVASI on the basis of Publisher imprint (SS Jain Conference) on Woolner-edited edition. That is a manifest classification of the source, not a doctrinal judgement.

- Citation: [](https://archive.org/details/in.ernet.dli.2015.399872)

---

### T61-CAND-0020 (pos 19)
- Category: SOURCE_ATTRIBUTION | Priority: attribution, no_fabrication, source_grounding
- Source: Ardha Magadhi Quadrilingual Dictionary Vol-2 (1927) (SVK-2004)
- Sect: STHANAKAVASI (MEDIUM) | Layer: LEXICON
- Rights: TRAINING_ALLOWED | Split: train

**Q**: What is the recorded provenance of Ardha Magadhi Quadrilingual Dictionary Vol-2 (1927)?

**A**: The manifest records Ardha Magadhi Quadrilingual Dictionary Vol-2 (1927) as acquired from Internet Archive, with recorded training permission TRAINING_ALLOWED (R25_LIFE_PLUS_60_EXPIRED) and license basis public domain on documented facts. The recorded source URL is kept in the citations metadata.

- Citation: [](https://archive.org/details/in.ernet.dli.2015.399104)

---

### T61-CAND-0021 (pos 20)
- Category: SOURCE_ATTRIBUTION | Priority: attribution, no_fabrication, source_grounding
- Source: An Illustrated Ardha-magadhi Dictionary Vol-5 (1923, DLI scan) (SVK-2005)
- Sect: STHANAKAVASI (MEDIUM) | Layer: LEXICON
- Rights: TRAINING_ALLOWED | Split: train

**Q**: Who is listed as the author of An Illustrated Ardha-magadhi Dictionary Vol-5 (1923, DLI scan)?

**A**: The corpus manifest records An Illustrated Ardha-magadhi Dictionary Vol-5 (1923, DLI scan) as written by Muni Ratnachandra Ji Maharaj in 1923. It is classified as LEXICON material with CORE_STHANAKAVASI scope.

- Citation: [](https://archive.org/details/in.ernet.dli.2015.342545)

---

### T61-CAND-0022 (pos 21)
- Category: SOURCE_ATTRIBUTION | Priority: attribution, no_fabrication, source_grounding
- Source: Paia-sadda-mahannavo: a comprehensive Prakrit-Hindi dictionary (1923) (SVK-2006)
- Sect: UNKNOWN (UNKNOWN) | Layer: LEXICON
- Rights: TRAINING_ALLOWED | Split: train

**Q**: What kind of text is Paia-sadda-mahannavo: a comprehensive Prakrit-Hindi dictionary (1923) - a canonical scripture, a commentary, or a later study?

**A**: The manifest records Paia-sadda-mahannavo: a comprehensive Prakrit-Hindi dictionary (1923) as LEXICON material. Its canonical status is derived as REFERENCE_LEXICON.

- Citation: [](https://archive.org/details/paiasaddamahaavo0000seth)

---

### T61-CAND-0023 (pos 22)
- Category: SOURCE_ATTRIBUTION | Priority: attribution, no_fabrication, source_grounding
- Source: Paia-Sadda-Mahannavo, Motilal Banarsidass edition (1928) (SVK-2007)
- Sect: UNKNOWN (UNKNOWN) | Layer: LEXICON
- Rights: TRAINING_ALLOWED | Split: train

**Q**: Which publisher and publication year are recorded for Paia-Sadda-Mahannavo, Motilal Banarsidass edition (1928)?

**A**: The manifest records Paia-Sadda-Mahannavo, Motilal Banarsidass edition (1928) as published by Motilal Banarsidass in 1928; its recorded license basis is public domain on documented facts.

- Citation: [](https://archive.org/details/in.ernet.dli.2015.348701)

---

### T61-CAND-0024 (pos 23)
- Category: SOURCE_ATTRIBUTION | Priority: attribution, no_fabrication, source_grounding
- Source: Woolner's Introduction To Prakrit (1917) (SVK-2008)
- Sect: UNKNOWN (UNKNOWN) | Layer: MIXED
- Rights: TRAINING_ALLOWED | Split: train

**Q**: Which tradition and sect does the manifest record for Woolner's Introduction To Prakrit (1917)?

**A**: The manifest records Woolner's Introduction To Prakrit (1917) under tradition JAIN, sect UNKNOWN (confidence unknown), with classification basis recorded as insufficient_evidence.

- Citation: [](https://archive.org/details/IntroductionToPrakritWoolner_bookmarked)

---

### T61-CAND-0025 (pos 24)
- Category: SOURCE_ATTRIBUTION | Priority: attribution, no_fabrication, source_grounding
- Source: Introduction To Prakrit, Motilal Banarsidass edition (1928) (SVK-2009)
- Sect: UNKNOWN (UNKNOWN) | Layer: MIXED
- Rights: TRAINING_ALLOWED | Split: train

**Q**: Is Introduction To Prakrit, Motilal Banarsidass edition (1928) specific to the Sthanakavasi tradition or general Jain material?

**A**: The manifest classifies Introduction To Prakrit, Motilal Banarsidass edition (1928) with religious scope CONTEXTUAL_JAIN on the basis of Revised edition of a related manifest source; same basis. That is a manifest classification of the source, not a doctrinal judgement.

- Citation: [](https://archive.org/details/in.ernet.dli.2015.65389)

---

### T61-CAND-0026 (pos 25)
- Category: SOURCE_ATTRIBUTION | Priority: attribution, no_fabrication, source_grounding
- Source: Jain Sathan Kavasi (1928) (SVK-2010)
- Sect: STHANAKAVASI (MEDIUM) | Layer: MIXED
- Rights: TRAINING_ALLOWED | Split: train

**Q**: What is the recorded provenance of Jain Sathan Kavasi (1928)?

**A**: The manifest records Jain Sathan Kavasi (1928) as acquired from Internet Archive, with recorded training permission TRAINING_ALLOWED (R70_PRE_1930_PUBLICATION) and license basis public domain on documented facts. The recorded source URL is kept in the citations metadata.

- Citation: [](https://archive.org/details/in.ernet.dli.2015.306075)

---

### T61-CAND-0027 (pos 26)
- Category: SOURCE_ATTRIBUTION | Priority: attribution, no_fabrication, source_grounding
- Source: Aadhyatm Saar (1913) (SVK-2011)
- Sect: UNKNOWN (UNKNOWN) | Layer: MIXED
- Rights: TRAINING_ALLOWED | Split: train

**Q**: Who is listed as the author of Aadhyatm Saar (1913)?

**A**: The corpus manifest records Aadhyatm Saar (1913) as written by Yashovijay Upadhyay in 1913. It is classified as PHILOSOPHY (Gujarati) material with UNKNOWN scope.

- Citation: [](https://archive.org/details/in.ernet.dli.2015.306580)

---

### T61-CAND-0028 (pos 27)
- Category: SOURCE_ATTRIBUTION | Priority: attribution, no_fabrication, source_grounding
- Source: Navyugno Jain (1921) (SVK-2012)
- Sect: UNKNOWN (UNKNOWN) | Layer: SECONDARY_SCHOLARSHIP
- Rights: TRAINING_ALLOWED | Split: train

**Q**: What kind of text is Navyugno Jain (1921) - a canonical scripture, a commentary, or a later study?

**A**: The manifest records Navyugno Jain (1921) as SECONDARY SCHOLARSHIP material. Its canonical status is derived as SECONDARY_SCHOLARSHIP.

- Citation: [](https://archive.org/details/in.ernet.dli.2015.306156)

---

### T61-CAND-0029 (pos 28)
- Category: SOURCE_ATTRIBUTION | Priority: attribution, no_fabrication, source_grounding
- Source: Jain Dharm Praves Pothi Bhag 1 (1908) (SVK-2013)
- Sect: UNKNOWN (UNKNOWN) | Layer: MIXED
- Rights: TRAINING_ALLOWED | Split: train

**Q**: Which publisher and publication year are recorded for Jain Dharm Praves Pothi Bhag 1 (1908)?

**A**: The manifest records Jain Dharm Praves Pothi Bhag 1 (1908) as published by unknown in 1908; its recorded license basis is public domain on documented facts.

- Citation: [](https://archive.org/details/in.ernet.dli.2015.358432)

---

### T61-CAND-0030 (pos 29)
- Category: SOURCE_ATTRIBUTION | Priority: attribution, no_fabrication, source_grounding
- Source: Jain Sajjhaimala Bhag-4 (1927) (SVK-2014)
- Sect: UNKNOWN (UNKNOWN) | Layer: REFERENCE
- Rights: TRAINING_ALLOWED | Split: train

**Q**: Which tradition and sect does the manifest record for Jain Sajjhaimala Bhag-4 (1927)?

**A**: The manifest records Jain Sajjhaimala Bhag-4 (1927) under tradition JAIN, sect UNKNOWN (confidence unknown), with classification basis recorded as insufficient_evidence.

- Citation: [](https://archive.org/details/in.ernet.dli.2015.358666)

---

### T61-CAND-0031 (pos 30)
- Category: SOURCE_ATTRIBUTION | Priority: attribution, no_fabrication, source_grounding
- Source: Panch-pratikraman (1928) (SVK-2016)
- Sect: UNKNOWN (UNKNOWN) | Layer: MIXED
- Rights: TRAINING_ALLOWED | Split: train

**Q**: What is the recorded provenance of Panch-pratikraman (1928)?

**A**: The manifest records Panch-pratikraman (1928) as acquired from Internet Archive, with recorded training permission TRAINING_ALLOWED (R70_PRE_1930_PUBLICATION) and license basis none declared. The recorded source URL is kept in the citations metadata.

- Citation: [](https://archive.org/details/in.ernet.dli.2015.445046)

---

### T61-CAND-0032 (pos 31)
- Category: SOURCE_ATTRIBUTION | Priority: attribution, no_fabrication, source_grounding
- Source: Shri Kalpasutra Mul Or Hindi Bhashantar (1916) (SVK-2019)
- Sect: UNKNOWN (UNKNOWN) | Layer: CANONICAL_SCRIPTURE
- Rights: TRAINING_ALLOWED | Split: train

**Q**: Who is listed as the author of Shri Kalpasutra Mul Or Hindi Bhashantar (1916)?

**A**: The corpus manifest records Shri Kalpasutra Mul Or Hindi Bhashantar (1916) as written by Manakmuni Maharaj in 1916. It is classified as CANONICAL material with UNKNOWN scope.

- Citation: [](https://archive.org/details/in.ernet.dli.2015.344399)

---

### T61-CAND-0033 (pos 32)
- Category: SOURCE_ATTRIBUTION | Priority: attribution, no_fabrication, source_grounding
- Source: Uttara Adhyayan Sutra Vol I (1918) (SVK-2020)
- Sect: UNKNOWN (UNKNOWN) | Layer: CANONICAL_SCRIPTURE
- Rights: TRAINING_ALLOWED | Split: train

**Q**: What kind of text is Uttara Adhyayan Sutra Vol I (1918) - a canonical scripture, a commentary, or a later study?

**A**: The manifest records Uttara Adhyayan Sutra Vol I (1918) as CANONICAL material. Its canonical status is derived as CANONICAL.

- Citation: [](https://archive.org/details/in.ernet.dli.2015.548771)

---

### T61-CAND-0034 (pos 33)
- Category: SOURCE_ATTRIBUTION | Priority: attribution, no_fabrication, source_grounding
- Source: Shri Utradhyayan Sutar Agam Seva (1920) (SVK-2021)
- Sect: UNKNOWN (UNKNOWN) | Layer: CANONICAL_SCRIPTURE
- Rights: TRAINING_ALLOWED | Split: train

**Q**: Which publisher and publication year are recorded for Shri Utradhyayan Sutar Agam Seva (1920)?

**A**: The manifest records Shri Utradhyayan Sutar Agam Seva (1920) as published by unknown in 1920; its recorded license basis is none declared.

- Citation: [](https://archive.org/details/in.ernet.dli.2015.545305)

---

### T61-CAND-0035 (pos 34)
- Category: SOURCE_ATTRIBUTION | Priority: attribution, no_fabrication, source_grounding
- Source: Agam 28 Mool 01 Aavashyak Sutra Sthanakvasi (SVK-2022)
- Sect: STHANAKAVASI (HIGH) | Layer: CANONICAL_SCRIPTURE
- Rights: TRAINING_ALLOWED_WITH_PERMISSION_EVIDENCE | Split: validation

**Q**: Which tradition and sect does the manifest record for Agam 28 Mool 01 Aavashyak Sutra Sthanakvasi?

**A**: The manifest records Agam 28 Mool 01 Aavashyak Sutra Sthanakvasi under tradition SHWETAMBAR, sect STHANAKAVASI (confidence high), with classification basis recorded as title_explicitly_identifies_sthanakvasi_edition.

- Citation: [](https://jainqq.org/explore/002489)
**Rights flags**: MANIFEST_RIGHTS_STALE: manifest training_permission='NEEDS_PERMISSION (R93_RESTRICTIVE_TERMS)' but permission evidence file reports PERMISSION_GRANTED

---

### T61-CAND-0036 (pos 35)
- Category: SOURCE_ATTRIBUTION | Priority: attribution, no_fabrication, source_grounding
- Source: Agam 30 mool 03 Uttaradhyayana Sutra Sthanakvasi (SVK-2023)
- Sect: STHANAKAVASI (HIGH) | Layer: CANONICAL_SCRIPTURE
- Rights: TRAINING_ALLOWED_WITH_PERMISSION_EVIDENCE | Split: validation

**Q**: Is Agam 30 mool 03 Uttaradhyayana Sutra Sthanakvasi specific to the Sthanakavasi tradition or general Jain material?

**A**: The manifest classifies Agam 30 mool 03 Uttaradhyayana Sutra Sthanakvasi with religious scope STHANAKAVASI on the basis of title_and_author_and_publisher_all_confirm_sthanakvasi. That is a manifest classification of the source, not a doctrinal judgement.

- Citation: [](https://jainqq.org/explore/002494)
**Rights flags**: MANIFEST_RIGHTS_STALE: manifest training_permission='NEEDS_PERMISSION (R93_RESTRICTIVE_TERMS)' but permission evidence file reports PERMISSION_GRANTED

---

### T61-CAND-0037 (pos 36)
- Category: SOURCE_ATTRIBUTION | Priority: attribution, no_fabrication, source_grounding
- Source: Pratikraman - Observance of Self Reflection (SVK-2024)
- Sect: UNKNOWN (MEDIUM) | Layer: REFERENCE
- Rights: TRAINING_ALLOWED_WITH_PERMISSION_EVIDENCE | Split: validation

**Q**: What is the recorded provenance of Pratikraman - Observance of Self Reflection?

**A**: The manifest records Pratikraman - Observance of Self Reflection as acquired from JainQQ, with recorded training permission NEEDS_PERMISSION (R93_RESTRICTIVE_TERMS) and license basis JAIN EDUCATION INTERNATIONAL FOR PRIVATE AND PERSONAL USE ONLY. The recorded source URL is kept in the citations metadata.

- Citation: [](https://jainqq.org/explore/200026)
**Rights flags**: MANIFEST_RIGHTS_STALE: manifest training_permission='NEEDS_PERMISSION (R93_RESTRICTIVE_TERMS)' but permission evidence file reports PERMISSION_GRANTED

---

### T61-CAND-0038 (pos 37)
- Category: SOURCE_ATTRIBUTION | Priority: attribution, no_fabrication, source_grounding
- Source: Agam 03 Ang 03 Sthanang Sutra Part 01 Sthanakvasi (SVK-2025)
- Sect: STHANAKAVASI (HIGH) | Layer: CANONICAL_SCRIPTURE
- Rights: TRAINING_ALLOWED_WITH_PERMISSION_EVIDENCE | Split: validation

**Q**: Who is listed as the author of Agam 03 Ang 03 Sthanang Sutra Part 01 Sthanakvasi?

**A**: The corpus manifest records Agam 03 Ang 03 Sthanang Sutra Part 01 Sthanakvasi as written by Amarmuni, Shreechand Surana. It is classified as CANONICAL material with STHANAKAVASI scope.

- Citation: [](https://jainqq.org/explore/002905)
**Rights flags**: MANIFEST_RIGHTS_STALE: manifest training_permission='NEEDS_PERMISSION (R93_RESTRICTIVE_TERMS)' but permission evidence file reports PERMISSION_GRANTED

---

### T61-CAND-0039 (pos 38)
- Category: SOURCE_ATTRIBUTION | Priority: attribution, no_fabrication, source_grounding
- Source: Agam 29 Mool 02 Dasvaikalik Sutra Sthanakvasi (SVK-2026)
- Sect: STHANAKAVASI (HIGH) | Layer: CANONICAL_SCRIPTURE
- Rights: TRAINING_ALLOWED_WITH_PERMISSION_EVIDENCE | Split: test

**Q**: What kind of text is Agam 29 Mool 02 Dasvaikalik Sutra Sthanakvasi - a canonical scripture, a commentary, or a later study?

**A**: The manifest records Agam 29 Mool 02 Dasvaikalik Sutra Sthanakvasi as CANONICAL material. Its canonical status is derived as CANONICAL.

- Citation: [](https://jainqq.org/explore/007649)
**Rights flags**: MANIFEST_RIGHTS_STALE: manifest training_permission='NEEDS_PERMISSION (R93_RESTRICTIVE_TERMS)' but permission evidence file reports PERMISSION_GRANTED

---

### T61-CAND-0040 (pos 39)
- Category: SOURCE_ATTRIBUTION | Priority: attribution, no_fabrication, source_grounding
- Source: Sthanakvasi Jain Itihas (SVK-2027)
- Sect: STHANAKAVASI (HIGH) | Layer: MIXED
- Rights: TRAINING_ALLOWED_WITH_PERMISSION_EVIDENCE | Split: test

**Q**: Which publisher and publication year are recorded for Sthanakvasi Jain Itihas?

**A**: The manifest records Sthanakvasi Jain Itihas as published by Sthanakvasi Jain Karyalay (year not recorded); its recorded license basis is JAIN EDUCATION INTERNATIONAL FOR PRIVATE AND PERSONAL USE ONLY.

- Citation: [](https://jainqq.org/explore/020753)
**Rights flags**: MANIFEST_RIGHTS_STALE: manifest training_permission='NEEDS_PERMISSION (R93_RESTRICTIVE_TERMS)' but permission evidence file reports PERMISSION_GRANTED

---

# jain_svk_sources.md

**Project:** Open-weight Śvetāmbara Sthānakavāsī Jain AI system
**Phase:** Research → Discovery → Verification → Architecture decision (no training)
**Date of investigation:** 17 September 2026
**Method:** Direct primary-source verification only. Search-engine access was unavailable during
this investigation, so every claim below was verified by fetching official APIs or pages:
Hugging Face Hub API + full-text search, GitHub REST API, Internet Archive
`advancedsearch`/`metadata` APIs, PyPI JSON API, Wikipedia (secondary, cited),
and official project homepages. Anything not directly verified is marked `UNVERIFIED`.

---

## 0. How to read this document

| Marker | Meaning |
| --- | --- |
| ✅ VERIFIED | I fetched and read the primary source during this investigation. |
| ⚠️ PARTIAL | Primary source fetched, but the specific fact is inferred and must be confirmed. |
| ❓ UNVERIFIED | Not verified here. Do not rely on it without checking. |
| 🚫 NEGATIVE | Actively searched for and **not** found. This is itself a finding. |

---

## 1. Executive findings (the five that change the plan)

1. **✅ There is a genuinely CC0-licensed scanned Jain library on Internet Archive, and it is large.**
   A query against `collection:(ganeshvarnilibrary OR patron-library-collection)` with
   `mediatype:texts AND (title:jain OR subject:jain)` returns **`numFound: 1807`**, and every
   item sampled in that result carried `licenseurl: https://creativecommons.org/publicdomain/zero/1.0/`.
   This is the single most important legal discovery of this investigation: it is the only
   *quantity* of Jain text found anywhere that plausibly clears an AI-training gate.
   **Caveat (critical):** the CC0 mark is asserted by the uploading institution, not necessarily
   by the copyright holder. See `jain_svk_license_audit.md` §4.

2. **❌ The Sthānakavāsī-specific digital footprint is close to zero.** Searched and found:
   - Hugging Face full-text search for `Sthanakvasi` across datasets → **"No result found"** 🚫
   - GitHub repository search for `sthanakvasi` → **`total_count: 1`**, and that one repo is a
     chaturmas-placement directory, not a text corpus 🚫
   - Internet Archive title search `(sthanakvasi OR sthanakwasi OR sthanakavasi)` →
     **`numFound: 6`** 🚫
   - Internet Archive full-text search for `sthanakvasi` → **`numFound: 27`** (of which a
     minority are actually Sthānakavāsī publications)

   **There is no existing Sthānakavāsī corpus, dataset, model, or digitisation project to build on.**
   Every Sthānakavāsī asset in this project must be assembled or newly created. This is a
   much harder starting position than the preliminary research implied.

3. **✅ The pre-existing "Jain AI corpus" repos are unlicensed and stalled.**
   - `jainqq-org/JLOR` — license `NOASSERTION`, **`pushed_at: 2024-09-17`** (dormant ~2 years), 21 stars, 114 MB.
   - `jainism-portal/jainaagam` — **`"license": null`** (no licence at all → all rights reserved),
     **`pushed_at: 2023-01-26`** (dormant ~3.5 years), 10 stars.
   Neither can be redistributed or trained on as-is.

4. **✅ `jainaagam` is explicitly Mūrtipūjaka-scoped, not Sthānakavāsī.** Its own description reads
   *"a multilingual voluminous database of all **45** Jain Aagam"*. Sthānakavāsī tradition accepts
   **32** āgamas. Any 45-āgama corpus is by definition Mūrtipūjaka-canonical and **must be tagged
   `MURTIPUJAKA` / `MULTI_TRADITION`, never `STHANAKAVASI`**.

5. **✅ What was considered "the model question" has changed materially in 2026.**
   - **Gemma 4** (12B / 26B-A4B / 31B / E2B / E4B, July 2026) is tagged **`license:apache-2.0`** on the
     Hub — unlike Gemma 3's custom `license:gemma`. This makes Gemma newly viable for a permissive project.
   - **Qwen's current generation is Qwen3.5 / 3.6 / 3.8** (Mar–Aug 2026), all Apache-2.0, and the cards
     are tagged `image-text-to-text` (VL-native), not text-only.
   - **Sarvam-30B and Sarvam-105B** (Mar 2026, Apache-2.0, MoE) declare explicit `gu`, `hi`, `sa`
     language tags — the strongest Indic coverage found in any open-weight LLM.
   - **Llama's open-weight line has not advanced past Llama 4 (May 2025)** in the Hub's public
     `meta-llama` listings; its tag list covers `hi` but **not `gu` or `sa`**.
   The prior "Qwen + QLoRA" default is no longer obviously correct, and is answered in
   `jain_svk_architecture.md`.

---

## 2. Śvetāmbara Sthānakavāsī: the target domain (Part 1)

### 2.1 Hierarchy

```
Jainism
├── Śvetāmbara
│   ├── Mūrtipūjaka  (temple/temple-image worship; 45-āgama canon; Gacchas: Tapa, Kharatara, Achal, Upakeśa…)
│   ├── Sthānakavāsī (no images; worship in a sthanak; 32-āgama canon)   ← TARGET
│   │   └── monastic orders/streams incl. Vardhamān Sthānakavāsī Śramaṇ Saṅgh (order name VERIFIED in the
│   │       wild; its internal structure and current constituent orders are UNVERIFIED)
│   ├── Śvetāmbara Terapanth  (also non-idolatrous, also aligns with Loṅkā)  ← ADJACENT, MUST BE SEGREGATED
│   └── other/reform & lay-reform streams
├── Digambara     (rejects the Śvetāmbara canon; different authoritative corpus)
├── Yāpanīya / Bispanth / Terāpanth (Digambara) / Kānjī Panth / Tāraṇ Panth
└── Modern non-sectarian / secular interpretations of Jainism
```

### 2.2 Verified facts about Sthānakavāsī (✅ VERIFIED — Wikipedia, which cites Cort 2010, Dundas 2002, Flügel 2008, Long 2009, Wiley 2004)

- **Founded in the 17th century** by **Lava of Surat**, a follower of the 15th-century Gujarati reformer
  **Loṅkā Śāh**.
- **Core distinguishing doctrine:** rejects **idolatry** (mūrti-pūjā) and the necessity of temples; holds
  that religious practice belongs at a secular meeting-hall (**sthanak**) and that image worship and
  temple-building conflict with **ahiṃsā**.
- **Canonical position (the decisive metadata fact):** *"Sthānakavāsī accept **thirty-two** of the Jain
  Agamas, the Śvetāmbara canon."*
- **Terapanth shares the Loṅkā-derived non-idolatrous position.** Therefore *non-idolatry alone does not
  identify a text as Sthānakavāsī.* Sect attribution requires an author/publisher/order signal.
- **Contested point for evaluation design:** **Ātmārām (1837–1896)**, originally a Śvetāmbara
  Sthānakavāsī monk, became **Ācārya Vijayānandasūri** after concluding from Prakrit texts and Sanskrit
  commentaries that the non-Mūrtipūjaka position contradicted scripture. This is a real, documented
  intra-Śvetāmbara dispute about what the canon actually supports. **The model must not adjudicate it.**
  It belongs in the evaluation set as a *sect-context* item, and in the corpus as dual-tagged material.

### 2.3 Canon scope: 32 vs 45 (✅ VERIFIED structure)

From the canon enumeration (Śvetāmbara canon = 12 Aṅgas [11 extant + Dṛṣṭivāda lost] + 12 Upāṅgas +
6 Chedasūtras + 4 Mūlasūtras + 2 Cūlikasūtras + Prakīrṇakas):

| Category | Mūrtipūjaka (45) | Sthānakavāsī (32) — ⚠️ PARTIAL |
| --- | --- | --- |
| Aṅgas | 11 extant (12th, Dṛṣṭivāda, lost) | 11 |
| Upāṅgas | 12 | 12 |
| Chedasūtras | 6 | **4** — excludes **Jīyakappa (Jītakalpa)** and **Mahānisīha**, which the source explicitly notes are "only accepted as canonical by Mūrti-pūjaks" ✅ |
| Mūlasūtras | 4 | **2** — excludes **Piṇḍanijjutti** and **Oghanijjutti**, also "only accepted as canonical by Mūrti-pūjaks" ✅ |
| Cūlikasūtras | 2 (Nandī, Anuyogadvāra) | 2 ⚠️ (whether Sthānakavāsī counts these inside the 32 is UNVERIFIED) |
| Prakīrṇakas ("supernumerary") | 10 to 20+ (varies by sub-sect) — this is what carries the count to 45 | **excluded** ✅ (structurally; exact treatment UNVERIFIED) |

> **⚠️ EXPLICIT UNCERTAINTY / RESEARCH GAP #1:** 11 + 12 + 4 + 2 = 29, and 11 + 12 + 4 + 4 = 31.
> Wikipedia states "thirty-two" without enumerating them. **The exact list of the 32 āgamas accepted by
> Sthānakavāsī tradition is NOT settled by any source I could verify, and a deficit or surplus of 1–3 will
> exist depending on how Cūlikasūtras and the Āvassaya-nijjuttis are counted.** The 32-list must be
> fixed by a Sthānakavāsī scholar before any canon-scope metadata is published. Do not guess.
> **The 45-āgama list, however, is stable and verified — and must be the basis for the Mūrtipūjaka tag.**

### 2.4 Non-negotiable tagging rules

A source may be labelled `STHANAKAVASI` **only** if at least one of these holds, and the evidence is recorded:

1. Published by a Sthānakavāsī institution (e.g. **A.B.Shree Svetambar Sthanakvasi Jain Conference**,
   or a named Sthānakavāsī order/press) — ✅ this institutional signal is verified to exist in the wild.
2. Authored/translated/commentated by a named Sthānakavāsī monk or lay scholar.
3. Self-identified as Sthānakavāsī in its own front matter (verified in item text).

Otherwise:

- 45-āgama or gaccha-affiliated material → `MURTIPUJAKA`
- Non-idolatrous but Terapanth-derived (e.g. Jain Vishva Bharati / Ladnun; Ācārya Tulsi / Mahāprājña) → `TERAPANTH`
- Digambara institutions (e.g. **Shri Ganesh Varni Digambar Jain Sansthan** — appears repeatedly in the CC0 set) → `DIGAMBARA`
- Mixed or unclear → `MULTI_TRADITION` + `sectarian_confidence: LOW`

> **🚨 Finding that contradicts an easy assumption:** the large CC0 archive.org library that we most want
> to use **skews Digambara and generic-Hindi-Jain**, not Sthānakavāsī. Sampling of that collection shows
> Digambara institutions and Digambara authors (Ganesh Varni Digambar Jain Sansthan, Digambar Jain
> Atishay Kshetra Shri Mahavirji, Central Jaina Oriental Library, Acharya Shanti Sagar Smriti Granthamala).
> **Volume of legally-clean Jain text ≠ volume of Sthānakavāsī text.** Plan for that gap explicitly.

---

## 3. The Sthānakavāsī textual ecosystem (Part 2)

### 3.1 Primary/canonical layer

The Āgamas are in **Ardhamāgadhī / Jaina Māhārāṣṭrī Prakrit**. Modern editions are printed in
**Devanagari**; historical editions used **Gujarati, Kannada, Telugu scripts**, and 19th/20th-c.
Western editions used **Latin/IAST**. This script multiplicity is a first-order engineering problem
(see `jain_svk_data_pipeline.md` §5).

Verified canon structure (names given in Prakrit → Sanskrit → meaning):

| # | Section | Texts | SVK status |
| --- | --- | --- | --- |
| 1 | **Aṅgas** (limbs) | Āyāraṃga (Ācārāṅga), Sūyagaḍa (Sūtrakṛtāṅga), Ṭhāṇaṃga (Sthānāṅga), Samavāyaṃga, Viyāha-pannatti / Bhagavaī, Nāyā-dhamma-kahāo, Uvāsaga-dasāo, Aṇuttarovavāiya-dasāo, Anuttaraupapātikadaśāh, Paṇha-vāgaraṇa, Vivāga-suya, **Diṭhīvāya (lost)** | 11 extant, accepted ✅ |
| 2 | **Upāṅgas** | Uvavāiya, Rāya-paseṇaijja, Jīvājīvābhigama, Pannavaṇā, Sūriya-pannatti, Jambūdvīpa-pannatti, Canda-pannatti, Nirayāvaliyāo, Kappāvaḍaṃsiāo, Pupphiāo, Puppha-cūliāo, Vaṇhi-dasāo | 12, accepted ✅ |
| 3 | **Chedasūtras** | Āyāra-dasāo (ch. 8 = Kalpa-sūtra), Bihākappa, Vavahāra, Nisīha, ~~Jīya-kappa~~, ~~Mahā-nisīha~~ | 4 for SVK ✅ |
| 4 | **Mūlasūtras** | Dasaveyāliya, Uttarajjhayaṇa, Āvassaya, ~~Piṇḍa-nijjutti~~, ~~Ogha-nijjutti~~ | SVK subset ⚠️ (Āvassaya-nijjuttis treatment UNVERIFIED) |
| 5 | **Cūlikasūtras** | Nandī-sūtra, Anuyogadvāra-sūtra | 2 ⚠️ |
| 6 | **Paiṇṇaya / Prakīrṇaka** | "Miscellaneous", 10–20+, varying by sub-sect, generally *lower authority*, mostly Jaina Māhārāṣṭrī Prakrit | **excluded from SVK 32** ✅ |

Age (secondary scholarship, cited): Ācārāṅga, Sūtrakṛtāṅga, Uttarādhyayana are argued to be among the
oldest canon texts; Śvetāmbaras date codification to the **Council of Vallabhi (c. 454/466 CE)** under
**Devardhigaṇi**. This matters for metadata: **the "canonical text" is a recension, and editions differ.**
Every corpus item must therefore carry `edition` metadata, not just `text_name`.

### 3.2 Sthānakavāsī-relevant non-canonical layer (this is where the tradition actually lives)

The canonical layer is shared; the *distinctly Sthānakavāsī* material is downstream. Categories to
collect, with the sourcing status I actually established:

| Category | Description | Sourcing status |
| --- | --- | --- |
| Sthānakavāsī āgama translations | Gujarati/Hindi chāyā + anuvāda sets produced by the Conference and by Sthānakavāsī monks | ⚠️ DLI items exist whose text mentions "Sthānakvasi" (see §4.3); publisher-level attribution mostly missing from metadata |
| Sthānakavāsī pravachan (sermon) collections | Printed sermon and spiritual-discourse volumes (e.g. *Adhyātmik Pravachno*) | ⚠️ Found on Internet Archive, attribution requires bibliographic research |
| Sthānakavāsī institutional history | e.g. *A.b.shree Swetambar Sthanakvasi Jain Confaranceni Chadati Padatino Itihas* (1941, Gujarati) | ✅ two scan instances found |
| Sthānakavāsī lay-conduct / dharma-kartavya manuals | e.g. *Sthanakvasi Jainonum Dharamkartavya* (1960, Gujarati) | ✅ found |
| Sthānakavāsī-published lexicography | *An Illustrated Ardha Magadhi Dictionary*, Muni Ratnachandraji, **published by the S. Sthanakwasi Jaina Conference** | ✅ **CC0-licensed instances found (v1, v3, v4)** — see §4.2 |
| Stavan/stotra and devotional print | e.g. *Stavanavali* (1960) | ⚠️ found, sect attribution unverified |
| Sthānakavāsī pathshala / Bal pathshala curricula | Modern teaching material | 🚫 not found in any public digital repository |
| Sthānakavāsī periodicals | Conference smārikā and periodical runs (*Swarna Jayanti Smarika*, 1976; *Kaivalya Shamapan Divas… Prakashika Smarika*, 1992) | ⚠️ found, in copyright |

> **Conclusion for Part 2:** Sthānakavāsī textual authority **cannot** be represented by a generic
> Śvetāmbara list. The canon subset (32 vs 45) is a real, verifiable distinction; but the tradition's
> *distinctive* literature is 20th–21st-century Gujarati/Hindi print, most of which is **still in
> copyright** and **not digitised**. This is the project's central supply problem.

---

## 4. Actual digital assets found (Part 3 — assets, not websites)

### 4.1 Hugging Face (searched via Hub API + Hub full-text search)

| Asset | Verified facts |
| --- | --- |
| `Sthanakvasi` full-text search, type=dataset | ❓❓ **"No result found"** 🚫 |
| `shethjenil/JainBooks` | 39,072,202 bytes (`usedStorage`); single `data.parquet`; **no `license` tag at all**; created 2025-09-23; 19 downloads. → **no licence = NOASSERTION** |
| `HappyAIUser/Atma3.1-ShareGPT` | `license: apache-2.0` ✅; 1,693,875 bytes; `data.jsonl`; 7,700+ lines; **English**; text = *Ātma Siddhi* (Shrimad Rajchandra) — a modern non-sectarian/Śvetāmbara-adjacent Jain work; created 2024-11-14 |
| `dataspoof/Jains` | **no licence tag → NOASSERTION**; 120,329 bytes; `Haribhadrasuri_cleaned.csv`; card states it is **derived from GRETIL** → upstream terms govern; created 2026-03-10 |
| `VIITPune/Deshika-Maharashtri_Prakrit_to_English_Parallel_Corpus` | `license: apache-2.0` ✅; **`language:pra`** (the ISO 639-3 code for Prakrit!) + `en`; `1K<n<10K`; CSV. **This is the only Prakrit parallel corpus found on the Hub.** Mahārāṣṭrī Prakrit, not Ardhamāgadhī — related but not the canon's language |
| Jain *models* on Hub | Searched: none relevant. `author=Qwen`-style listing for "jain" returns unrelated name matches. **No open-weight Jain model found.** 🚫 |

### 4.2 Internet Archive — the CC0 Jain library (the major find)

- `collection:(ganeshvarnilibrary OR patron-library-collection)` + `mediatype:texts` +
  `(title:jain OR subject:jain)` → **`numFound: 1807`**; sampled items carry
  `licenseurl: CC0-1.0` ✅
- Item identifiers follow uploader prefixes (`alnh_`, `kbii-`, `kins_`, `tqtv-`, `zwmn-`, `WTyp_`,
  `BGsN`, `BFfW`, `jalz_`, `ekmv_`, `WTyp_` …), i.e. multiple independent institutional uploaders.
- **The Ardhamāgadhī Dictionary, all of it:** `title:("Ardha Magadhi Dictionary" OR "Ardhamagadhi Dictionary")`
  → **`numFound: 46`**, spanning vols 1–5, 1923–1938, by **Muni Ratnachandraji**, published by the
  **S. Sthanakwasi Jaina Conference** (vol 3 and vol 4 titles say so explicitly).
  CC0 instances verified:
  - `zwmn-an-illustrated-ardha-magadhi-dictionary-vol-1-by-m` (Indore 1923) → **CC0 1.0** ✅
  - `tqtv-an-illustrated-ardha-magadhi-dictionary-vol-3-by-m` (Bombay 1930) → **CC0 1.0** ✅
  - `WTyp_ardha-magadhi-dictionary-vol.-3-by-shri-ratna-chandra-ji-maharaja-1930-lahore-ja` → **CC0 1.0** ✅
  - `kbii-an-illustrated-ardha-magadhi-dictionary-vol-4-by-m` (1932) → **CC0 1.0** ✅
  - Non-CC0 duplicates of the same volumes exist under `in.ernet.dli.*` / `dli.ernet.*` (DLI) → the
    **same book in two rights states** is a real duplicate-resolution problem, not a hypothetical one.
  - ⚠️ vols 2 and 5 CC0 status not individually confirmed.
- **Sthānakavāsī-specific CC0 items verified:**
  - `kins_jain-dharma-by-muni-sushil-kumar-1958-new-delhi-a-b-s-sthanakvasi-jain-conference-bhavan`
    → **CC0 1.0**, *Jain Dharma*, Muni Sushil Kumar, 1958, **A.B.S. Sthānakavāsī Jain Conference Bhavan, New Delhi**.
    This is a Sthānakavāsī-titled, Sthānakavāsī-published English/Hindi work. A genuine seed item.
  - `in.ernet.dli.2015.440806` *Sthanakvasi Jainonum Dharamkartavya* (Gujarati, 1960) → **no licence field** 🟡
  - `in.ernet.dli.2015.258851` / `dli.ernet.410253` *A.b.shree Swetambar Sthanakvasi Jain Confaranceni
    Chadati Padatino Itihas* (Gujarati, 1941) → **no licence field** 🟡

#### ✅ OCR-quality datum (measured, not assumed)

`archive.org/metadata/in.ernet.dli.2015.440806` for a **Gujarati** book reports the derived OCR files as:

```
"ocr": "tesseract 5.0.0-alpha-20201231-10-g1236",
"ocr_parameters": "-l guj",
"ocr_detected_lang": "gu",  "ocr_detected_lang_conf": 1.0000,
"ocr_detected_script": "Bengali",  "ocr_detected_script_conf": 0.4658
```

**Archive.org's own Gujarati OCR pipeline mis-detected the script as Bengali at 46.6% confidence on a
Gujarati book.** This is independent confirmation that the existing `_djvu.txt` / hOCR text layer for
Gujarati items is unreliable and cannot be treated as a corpus without validation. Note also that a
`_djvu.txt` text layer IS produced (330,964 bytes for this item), so the text exists — it just cannot be trusted.

### 4.3 Internet Archive — DLI / JaiGyan (large, but rights-unclean)

- `collection:digitallibraryindia AND title:(aagam OR agam)` → **`numFound: 65`** ✅
- `q=sthanakvasi` (full-text, `text:sthanakvasi OR text__reviews:sthanakvasi`) → **`numFound: 27`** ✅,
  including Hindi translations of canon texts that **mention "Sthānakvāsī" inside their own text**:
  - `in.ernet.dli.2015.346505` *Shri Acharrang Sutra (hindi Chaya Anuwad)*, 1966
  - `in.ernet.dli.2015.308533` *Shri Dashvaikalik Sutra Ka Hindi Anuvad*, 1936
  - `in.ernet.dli.2015.446025` / `2015.348094` *Shri Uttradhyayan Sutra Ka Hindi Anuvaad*, 1962 / 1934
  - `in.ernet.dli.2015.308462` *Shri Sutrakratang Sutra*, 1938
  - `in.ernet.dli.2015.545305` *Shri Utradhyayan Sutar (Agam Seva)*, 1920
  - `in.ernet.dli.2015.327713` *Shrimada Gyatadharmkathank Sutra*, 1964
  - `in.ernet.dli.2015.327413` *Ardha-magadhi Dictionary Part 4*, 1932
- **Rights:** a targeted `fl[]` query for `licenseurl`, `rights`, and `possible-copyright-status` on
  DLI items returned **only `collection` and `identifier`** — i.e. **no licence field, no rights field,
  no copyright status field exists on these items.** Collections present: `digitallibraryindia`, `JaiGyan`.
  → **DLI items are legally unusable for training as they stand.** This is a verified negative, and it is
  the reason the DLI set (which is otherwise the richest Jain canon source) cannot be the training corpus.
- One community upload, `u-08-u-09-u-10-u-11-u-12-2_202210`, *"Jain Śvetāmbara Āgama Canon in English
  (w/Hindi)"*, sits in `opensource`/`community` with **no licence** → 🟡 NEEDS_PERMISSION.

### 4.4 GRETIL (Prakrit + Jaina Sanskrit e-texts)

✅ VERIFIED that GRETIL provides:
- a **`Jaina` category** under its Sanskrit e-texts,
- a separate **`E-texts in Prakrit`** section,
- **cumulative bulk downloads including "Download All Prakrit Texts"**,
- and that it is mid-migration to **TEI-conformant XML**, with plain `.txt` and analytic-HTML
  transformations offered per text.
❓ **No licence statement was found on the GRETIL landing page.** The site describes texts as
"contributed by various individuals and institutions" with "varying sources and quality" — which is an
explicit admission that rights are per-contribution and not asserted by GRETIL.
→ Treat GRETIL as **per-item rights research**, with the strong expectation that most individual
contributions are derivative transcriptions of public-domain editions and therefore likely PD-derived,
but **not proven**. This is the highest-value *typing* effort to inspect first, because a typed Unicode
Prakrit text removes the OCR problem entirely.

### 4.5 Manuscript image repositories (OCR/vision track, not text track)

- **OPenn (Univ. of Pennsylvania)** — Jain manuscript holdings with item-level rights information;
  prior research recorded CC BY 4.0 with public-domain treatment where applicable on *Ms. Indic 20*.
  ❓ Not re-verified in this pass; must be re-checked at the item level before use.
- Use case: OCR/VLM training and layout/diagram research, **not** as a text corpus. In India, a slavish
  scan of a 2-D public-domain work does not create a fresh copyright (the *skill-and-judgement* standard
  of *Eastern Book Co. v. D.B. Modak*, 2008) — but this is jurisdictional and must be confirmed by counsel
  (see `jain_svk_license_audit.md` §3).

### 4.6 Other Jain platforms (examined, no usable licence found)

| Platform | Status |
| --- | --- |
| `jainelibrary.org` (Jain eLibrary) | Homepage fetched: renders essentially no content server-side (JS app), **no licence or terms text discoverable on the landing page**, registration-gated. → **NEEDS_PERMISSION**, and the absence of discoverable terms is itself the finding |
| `jainqq.org` / JainQQ (homepage of JLOR) | Underlying repo unlicensed + dormant (§1.3) → NEEDS_PERMISSION |
| `jaingpt.com` (JainGPT) | Retrieval system, no published corpus, model, or licence → **research subject, not a source** |
| `saumyasanghvi03/AI-Yashvi` | RAG app over third-party websites; not a corpus → **research subject** |
| `aagam.jainism.info` (Jainaagam) | 45-āgama (Mūrtipūjaka scope), **no licence** → NEEDS_PERMISSION + wrong sect scope |
| `ankj77/chaturmas-suchi` (GitHub, created 2026-09-06) | Hindi/English chaturmas directory for **Shri Vardhaman Sthanakvasi Jain Shraman Sangh**. No licence. The **only** Sthānakavāsī-named repo on GitHub. 🟣 research/metadata value only |

---

## 5. What does NOT exist (verified negatives — these are load-bearing)

1. 🚫 **No Hugging Face dataset mentions Sthānakavāsī.** (Hub full-text search → no results.)
2. 🚫 **No open-weight Jain instruction model with documented training data** — consistent with the
   preliminary research, and now re-confirmed at the Hub API level for 2026.
3. 🚫 **No Ardhamāgadhī/Prakrit tokenizer, no Prakrit-capable embedding model, no Prakrit OCR model.**
   Jina v3's 94-language list contains `sa` but **no Prakrit**; Qwen3-Embedding claims "100+ languages"
   without enumerating them; no 2026 embedding model found that lists Prakrit.
   The only Prakrit-language Hub artefact is one Mahārāṣṭrī↔English parallel corpus (Apache-2.0).
4. 🚫 **No Sthānakavāsī pathshala/curriculum, pravachan audio archive, or periodical run** in any
   public digital repository I could reach.
5. 🚫 **No Gujarati OCR model of production maturity.** Best-in-class 2026 document-OCR VLMs
   (`chandra-ocr-2`, `DeepSeek-OCR-2`, `GLM-OCR`, `Unlimited-OCR`, `dots.ocr`, `surya-ocr-2`)
   carry **no Indic script tags**; PaddleOCR ships a Devanagari recogniser but **no Gujarati** one;
   the only Gujarati OCR model found, `umangchaudhari/gujarati-ocr` (Mar 2026, Apache-2.0), has ~305
   downloads — an individual contribution, not a dependable component.

---

## 6. Provenance / verification ledger

| Source of fact | Access path used | Date |
| --- | --- | --- |
| HF Hub model/dataset metadata | `huggingface.co/api/models`, `/api/datasets` (`?full=true`, `expand[]=tags`) | 2026-09-17 |
| HF full-text search | `huggingface.co/search/full-text?q=…&type=dataset` | 2026-09-17 |
| GitHub repo licence/activity | `api.github.com/repos/…`, `/search/repositories` | 2026-09-17 |
| Internet Archive holdings & rights | `archive.org/advancedsearch.php`, `/metadata/…` | 2026-09-17 |
| OCR pipeline metadata | IA item file-level `ocr*` attributes | 2026-09-17 |
| GRETIL corpus structure | `gretil.sub.uni-goettingen.de/gretil.html` | 2026-09-17 |
| Canon + sect facts | `en.wikipedia.org/wiki/Sthānakavāsī`, `/wiki/Jain_Agamas` (cites Cort/Dundas/Flügel/Long/Wiley) | 2026-09-17 |
| Library versions | `pypi.org/pypi/<pkg>/json` | 2026-09-17 |

**Search-engine note:** the web-search tool returned no results for every query during this session.
Compensating strategy was to query official APIs directly, which produced *stronger* evidence than
search snippets would have. Any item marked ❓ should be re-checked with a working search engine or
by direct API query before it is acted on.

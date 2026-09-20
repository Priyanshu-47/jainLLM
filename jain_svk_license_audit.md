# jain_svk_license_audit.md

**Purpose:** determine what this project may lawfully *train on*, *redistribute*, and *license out*.
**Standing rules:** online availability ≠ permission. Unknown licence = `NEEDS_PERMISSION`.
Absence of a licence field = **all rights reserved by default**, not "open".
**Not legal advice.** Items marked ⚖️ require a qualified Indian IP lawyer before release.

---

## 1. The four-gate model

Every source must pass four independent gates. Promotion past a gate is *per source*, never per collection.

| Gate | Question | Failure mode if skipped |
| --- | --- | --- |
| **G1 Acquire** | Can we lawfully obtain and store the file? | Base-rights exposure; no remedies |
| **G2 Train** | May we use it to update model weights? | Poisoned model weights that cannot be un-trained cleanly |
| **G3 Redistribute** | May we publish the text / derived dataset / embeddings? | Takedown of the dataset, then of the model |
| **G4 Commercialise** | May the model or dataset be used commercially? | Downstream users lose their own compliance |

**Our project decision (recommended):** every item in `jain-svk-corpus` must satisfy **G1 + G2 + G3**.
**G4 is required only for a clearly-marked subset** (`commercial_ok: true`), because an open-source
Jain project should not be able to hand users a licence it does not itself hold. Dual-track the corpus:
`commercial_ok=true` for the core, and a quarantined non-commercial lane that is *still* published
(transparency) but excluded from any release we licence permissively.

---

## 2. Permission taxonomy (project-wide vocabulary)

| Code | Meaning | Counts as TRAIN? |
| --- | --- | --- |
| `TRAINING_ALLOWED` | Explicit licence or unambiguous public-domain status permits training | ✅ |
| `TRAINING_ALLOWED_WITH_CONDITIONS` | Permitted, but attribution / ShareAlike / no-commercial / notice obligations attach | ⚠️ conditionally |
| `UNCLEAR` | Rights exist but are unstated or contested | ❌ → RAG/RESEARCH only |
| `TRAINING_NOT_ALLOWED` | Explicitly excluded (e.g. NC-only, or ARR) | ❌ |

Verified mapping for the licences that actually occur in this landscape:

| Licence / status | Train | Redistribute text | Redistribute derived dataset | Weights trained on it | Notes |
| --- | --- | --- | --- | --- | --- |
| **Public domain (India, author died >60 yrs ago)** | ✅ | ✅ | ✅ | ✅ | The cleanest basis. Indian term: life + 60 years (Copyright Act 1957) → as of 2026, authors who died **before 1966**. ⚖️ confirm per item |
| **CC0-1.0** | ✅ | ✅ | ✅ | ✅ | Dedication; no conditions. **But verify the dedicator had standing** (§4) |
| **CC BY 4.0** | ✅ | ✅ | ✅ | ✅ | Attribution required in NOTICE |
| **CC BY-SA 4.0** | ⚠️ | ✅ | ⚠️ ShareAlike may propagate to the derived dataset | ⚠️ contested | **Recommendation: keep out of the core corpus.** Isolate in a separate repo |
| **CC BY-NC 4.0 / CC BY-NC-SA** | ❌ (commercial) | ✅ non-comm. | ⚠️ | ⚠️ | Goes to the quarantine lane only |
| **CC BY-ND 3.0** (found in the wild: `JainDharmAurDarshan`) | ❌ | ⚠️ no derivatives | ❌ | ❌ | ND blocks the very act of normalising/normalising text. **DO_NOT_USE for corpus** |
| **Apache-2.0 / MIT** (datasets, code) | ✅ | ✅ | ✅ | ✅ | Best case; note patent/notice obligations |
| **`license: gemma`** (Gemma 3, embeddinggemma) | ⚠️ | ⚠️ | ⚠️ | ⚠️ | Use-of-prohibited-use policy attaches. **Gemma 4 moved to Apache-2.0** ✅ |
| **`license: other` / Llama community licences** | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 700M-MAU clause, naming/attribution clauses |
| **NOASSERTION / `"license": null` / no field** | ❌ | ❌ | ❌ | ❌ | **All rights reserved by default.** RAG_ONLY at most, and only with permission |
| **Government-of-India digitisation (DLI/JaiGyan)** | ❌ | ❌ | ❌ | ❌ | Scan-level status ≠ text-level licence (§5) |

---

## 3. Copyright mechanics that actually decide this project ⚖️

1. **Two different rights in every scanned book: the *text* and the *scan*.**
   - *Text:* literary copyright = author's life + 60 years (India). Translation/commentary is a **separate
     work** with its **own** term (translator's life + 60 years). A public-domain āgama with a 1985 Hindi
     anuvāda is *not* public domain.
   - *Scan:* under *Eastern Book Co. v. D.B. Modak* (2008) the Indian standard is **skill and judgement**,
     not "sweat of the brow", so a **slavish photographic scan of a 2-D public-domain page is not itself
     a new copyrightable work in India**. This is the legal basis for using scans of PD books.
     ⚖️ In the US/EU, faithful-reproduction scans have in some jurisdictions been held to attract
     "sweat-of-brow"-style protection (e.g. Bridgeman-style reasoning is *contested and jurisdiction-dependent*).
     Since we publish internationally, get this confirmed rather than assume it.
2. **The single most important practical consequence:**
   **for Sthānakavāsī material, the binding constraint is almost always the modern Hindi/Gujarati
   translation or commentary, not the Prakrit original.** The Prakrit canon is ancient and PD; the
   20th-century Gujarati anuvāda sets that the community actually reads are in copyright. **Do not
   collapse these two layers into one licence.**
3. **No text-and-data-mining exception is assumed.** India has no analogue of EU DSM Art. 4. Section 52
   fair dealing for "private use, research, criticism or review" is a *plausible* footing for
   non-commercial research, but it has not been settled for large-scale model training in India. ⚖️
   **Project stance: do not rely on fair dealing to justify training on in-copyright Jain texts.**
4. **Moral rights / religious sensitivity is not a legal gate but is a project gate.** Even where use is
   lawful, publishing sacred text in machine-readable form without community consent is a reputational
   and ethical failure mode. Every Sthānakavāsī item therefore also requires a **community-consent record**
   (`consent_status`), separately from `license`.

---

## 4. 🚨 The CC0 trap — and how to handle it

The Internet Archive CC0 Jain library (§4.2 of `jain_svk_sources.md`) is asserted-CC0 by institutional
uploaders. That is a strong signal but **not proof**. Three failure modes:

1. **Uploader without standing.** A 1997 autobiography (*Meri Jivan Gatha*, 1997) carries CC0 from the
   same uploader family as 1923 dictionaries. A 1997 work is in copyright in India. The CC0 tag is
   almost certainly wrong. **The tag cannot be trusted for post-1966 publications.**
2. **CC0 on the scan, not the text.** Even a valid CC0 on a scan does not cure a defect in the underlying
   translation rights.
3. **Collection-level drift.** The 1,807-item count is a *query* result over a patron library that also
   contains non-Jain material; assuming "the collection is CC0 hence the item is CC0" is exactly the error
   the standing rules forbid.

### The rule this project will apply (deterministic, auditable)

```
if license == CC0 and pub_year < 1966 and author_death_year < 1966   -> 🟢 TRAIN      (presumed PD in India + CC0)
if license == CC0 and pub_year < 1966 and author_death_year unknown  -> 🟡 NEEDS_PERMISSION (verify death year; usually resolves to 🟢)
if license == CC0 and 1966 <= pub_year                              -> 🟡 NEEDS_PERMISSION (uploader CC0 not credible)
if license == CC0 and pub_year unknown                               -> 🟡 NEEDS_PERMISSION (bibliographic research required)
if no licence field and pub_year < 1966 and author_death_year < 1966 -> 🟢 TRAIN      (it is PD *regardless* of the platform's silence)
if no licence field otherwise                                        -> 🟡 NEEDS_PERMISSION
if license in {CC-BY-NC*, CC-BY-ND*}                                 -> 🟣 RESEARCH / 🔵 RAG_ONLY (quarantine lane)
if license in {NOASSERTION, null} and rights-holder unknown          -> 🟡 NEEDS_PERMISSION
if text is generated by a strong LLM                                -> 🔵 RAG_ONLY or labelled-synthetic only (§7)
```

Note the fourth rule: **public-domain status is a property of the work, not of the platform's metadata.**
A pre-1966 book by a pre-1966 author is PD even if archive.org shows no licence. This is why the DLI
collection — which shows *no* licence at all — is not automatically unusable for **old** items; it is
unusable for *recent* ones, and for *any* item until the death-year research is done per item.
This distinction is worth roughly 80% of the usable corpus, so treat it as the audit's core work.

---

## 5. Per-source licensing verdicts

Legend: 🟢 TRAIN · 🟡 NEEDS_PERMISSION · 🔵 RAG ONLY · 🟣 RESEARCH ONLY · 🔴 DO NOT USE

| # | Source | Licence (verified) | Verdict | Reasoning |
| --- | --- | --- | --- | --- |
| 1 | CC0 Jain items, `patron-library-collection` / `ganeshvarnilibrary`, **pub < 1966** | `CC0-1.0` | 🟢 | CC0 + credible PD window. Requires per-item year/death-year check |
| 2 | Same collections, **pub ≥ 1966** | `CC0-1.0` | 🟡 | Uploader CC0 not credible for in-copyright works |
| 3 | `kins_jain-dharma-…-1958-…-sthanakvasi-jain-conference-bhavan` | `CC0-1.0` | 🟢 | 1958, institutional publisher, Sthānakavāsī. **Best single Sthānakavāsī seed item** |
| 4 | `Ardha Magadhi Dictionary` CC0 instances (v1 1923, v3 1930, v4 1932) | `CC0-1.0` | 🟢 | Pre-1966, Sthānakavāsī-published, and PD by age independently. **Highest-value Prakrit asset found** |
| 5 | `Ardha Magadhi Dictionary` DLI instances (no licence) | none | 🟢* | `*` = PD by age, not by metadata. Include only after death-year/bibliographic check |
| 6 | Internet Archive DLI / JaiGyan, any year, no licence field | none | 🟡 | No `licenseurl`, no `rights`, no `possible-copyright-status` **exists on these items** (verified). Pre-1966 works may still be PD-as-works; resolve per item |
| 7 | GRETIL Prakrit + Jaina Sanskrit e-texts | no site licence; per-contribution | 🟡→🟢 | Rights are per contributing scholar. TEI/plain-text editions of PD editions are likely PD-derived. **Resolve per file**; record contributor |
| 8 | `dataspoof/Jains` (GRETIL-derived) | no licence tag | 🟡 | Derivative of #7 **plus** an extra layer with its own (absent) licence. Source from GRETIL directly instead |
| 9 | `shethjenil/JainBooks` | no licence | 🟡 | 39 MB of unknown-provenance Jain text. **No source attribution in the card.** Cannot be used without provenance |
| 10 | `HappyAIUser/Atma3.1-ShareGPT` | `apache-2.0` | 🟢 | Cleanest modern Jain instruction dataset found. Non-sectarian (Shrimad Rajchandra) → tag `GENERIC_JAIN`, **not** SVK. English only |
| 11 | `VIITPune/Deshika-Maharashtra…Prakrit-to-English` | `apache-2.0` | 🟢 | Usable, but Mahārāṣṭrī not Ardhamāgadhī; small. Translation-quality review needed |
| 12 | `jainqq-org/JLOR` | `NOASSERTION`, dormant 2024-09 | 🟡 | **Cannot** train or redistribute. Approach the org for an explicit licence |
| 13 | `jainism-portal/jainaagam` | `"license": null`, dormant 2023-01 | 🟡 | All rights reserved. Plus **Mūrtipūjaka 45-āgama scope**, not SVK |
| 14 | `u-08…u-12-2_202210` "Jain Śvetāmbara Āgama Canon in English (w/Hindi)" | none, community upload | 🟡 | Unknown transcriber; could be a copy of a copyrighted English translation set |
| 15 | Jain eLibrary (`jainelibrary.org`) | no discoverable terms ✓ | 🟡 | Registration-gated, no licence page found. **Written permission required before any automated use** |
| 16 | OPenn Jain manuscripts (e.g. Ms. Indic 20, CC BY 4.0 per prior research) | `CC BY 4.0` ❓ | 🟢/🟣 | Re-verify per item. Use for OCR/VLM research, not as a text corpus |
| 17 | JainGPT / JainQQ / AI-Yashvi | n/a | 🟣 | Systems, not sources. Study their citation UX; do not harvest their outputs |
| 18 | Wikipedia / encyclopaedic Jain content | `CC BY-SA` | 🔵 | **Trailing-ShareAlike hazard.** Do not mix into the core dataset. Optional separate retrieval lane with attribution |
| 19 | AI-generated translations (JLOR-style, Gemini/Claude output) | derivative of #12/#13 | 🔴 | In-copyright source **and** machine-translated. Two defects. Our synthetic lane is separate and labelled (see `jain_svk_data_pipeline.md` §7) |
| 20 | `CC BY-ND 3.0` item (`JainDharmAurDarshan`) | `CC-BY-ND-3.0` | 🔴 | **NoDerivatives forbids normalisation, segmentation, OCR correction — i.e. every pipeline step** |
| 21 | Anything behind a login, paywall, or "free but not licensed" library | n/a | 🟡 | Availability is not permission |

---

## 6. Redistribution matrix — what we may actually ship

| Artefact | Permitted only if… | Recommended licence we attach |
| --- | --- | --- |
| **Original-text corpus** (cleaned, normalised, segmented) | All constituent items pass G1–G3 | **CC BY 4.0** + per-source `NOTICE` file + per-item licence ledger |
| **Derived metadata / manifest** (our own creation) | Always (our own work) | **CC0-1.0** — maximise reuse, zero friction |
| **Our translations / transliterations** (our own work) | We hold or are granted rights | **CC BY 4.0** |
| **Instruction dataset** (prompts/answers we author or generate) | Grounded only in G3-passing text | **CC BY 4.0** or **CC0-1.0** for prompts; see §7 re: synthetic |
| **Embeddings / indexes** | Embeddings of a PD text are generally not a reproduction, but the *underlying text* is retrievable from a vector DB → treat as redistribution of the text | Ship the corpus repo separately; document the link |
| **Model weights** | Trained **only** on G2-passing text; base-model licence permits derivatives and redistribution | **Apache-2.0** (consistent with Qwen base) |
| **Demo / Space** | Must reproduce the same citations + disclaimers as the model card | Code **Apache-2.0** |

**Hard rule:** if any item's rights change or are disputed, we must be able to rebuild the corpus
deterministically from a pinned manifest and identify every training run that consumed it. Therefore
every item carries `license`, `license_evidence_url`, `pub_year`, `author_death_year`,
`rights_verified_by`, `rights_verified_on`, and `consent_status`.

---

## 7. Synthetic data: a separate rights question

AI-generated text is **not** automatically ours and is **not** automatically copyrightable (several
jurisdictions require human authorship). Two independent problems:

1. **Input side:** if a generator was prompted with in-copyright text, the output may be a derivative of it.
   → *Rule:* only generate from G3-passing passages. Never generate "translations" of in-copyright commentaries.
2. **Output side:** the generated Q/A is of uncertain copyright status and of **zero scriptural authority**.
   → *Rule:* publish it under CC BY 4.0 with an explicit provenance record, and label every field:

```
ORIGINAL_TEXT | HUMAN_WRITTEN | SCHOLAR_VERIFIED | AI_GENERATED | AI_GENERATED_HUMAN_VERIFIED
```

**Never** allow `AI_GENERATED` text to occupy a field that the model is trained to treat as scripture.
The canonical text field and the explanation field must be physically separate columns, and the model's
training target must keep them separate.

---

## 8. Takedown, opt-out, and consent policy (adopt before publishing anything)

1. **Public `TAKEDOWN.md`** naming a single contact and a 30-day SLA.
2. **`sources/*.json` ledger** — one file per item; the corpus release pins the manifest hash.
3. **Recall procedure documented**: which corpus version fed which model version, and how a withdrawn
   item triggers a rebuild. Because our V1 is RAG-first, withdrawal removes the text immediately from
   retrieval, and only the fine-tuned v0.2+ adapter needs retraining.
4. **`consent_status`** field for Sthānakavāsī material: `NOT_SOUGHT | SOUGHT | GRANTED | DECLINED`.
   Publish nothing Sthānakavāsī with `NOT_SOUGHT` in the core corpus until the outreach round completes —
   this is the project's ethical gate, and it is stricter than copyright.
5. **No scraping of any site** whose terms we have not read and recorded. Jain eLibrary, temple sites,
   forums and pathshala sites are currently **out of scope**.

---

## 9. Open legal questions for counsel ⚖️ (do not self-answer)

1. Does the *Eastern Book Co.* skill-and-judgement standard in fact defeat scan-level copyright for
   foreign-uploaded scans we redistribute from archive.org?
2. Is training on PD text whose *host platform* shows no licence safe when the work itself is PD,
   given that the platform's silence is unambiguous? (Our position: yes, because PD status is
   property-of-work — but it should be papered.)
3. Does distributing a model trained on a PD corpus create any obligation to the corpus platform?
4. Does the ShareAlike clause of CC BY-SA attach to a *model* trained on CC BY-SA text? (Contested
   internationally; our mitigation is to avoid CC BY-SA in the core.)
5. India's position on TDM for research use, and whether a non-commercial research carve-out can be
   relied upon for the *dataset* (published) as opposed to the *training* act (private).
6. For any CC-BY-NC source we use in the quarantine lane: does NC restrict the *model weights*, or only
   the *dataset redistribution*?

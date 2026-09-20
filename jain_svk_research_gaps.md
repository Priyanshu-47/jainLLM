# jain_svk_research_gaps.md

Everything below is something this investigation **could not resolve**, ranked by how much it blocks the
project. Each gap states what is missing, why it matters, and the specific action that would close it.

Gaps are marked **BLOCKING** (cannot publish without resolving), **MATERIAL** (changes design), or
**NICE** (improves quality).

---

## GAP 1 · The exact list of the 32 āgamas accepted by Sthānakavāsī tradition — **BLOCKING**

- **What we know (verified):** Sthānakavāsī accept **thirty-two** of the Śvetāmbara āgamas; the
  Mūrtipūjaka canon is **45**; the difference structurally involves **Jīyakappa**, **Mahānisīha**,
  **Piṇḍanijjutti**, **Oghanijjutti** and the **Prakīrṇaka** collection, which are documented as
  "only accepted as canonical by Mūrti-pūjaks".
- **What is missing:** the *enumeration*. Our structural arithmetic yields 29–33 depending on how
  Cūlikasūtras and the Āvassaya-nijjuttis are counted. **No source I could verify enumerates the 32.**
- **Why it blocks:** `canon_scope` is the metadata field that prevents sect confusion — the project's
  hardest correctness requirement. Guessing it would bake a plausible-looking but wrong schema into
  every downstream artefact.
- **Closing action:** obtain written enumeration from a Sthānakavāsī scholar and from the published
  front matter of a Sthānakavāsī āgama edition (the **A.B. Shree Svetambar Sthanakvasi Jain Conference**
  editions are the natural source). Record the citation in the schema documentation.

## GAP 2 · No Sthānakavāsī corpus, dataset, model, or digitisation project exists — **BLOCKING**

- **Verified negatives:** HF full-text search `Sthanakvasi` → 0 datasets; GitHub `sthanakvasi` → 1 repo
  (a chaturmas directory); Internet Archive title search → 6 items; IA full-text → 27 items, a minority
  genuinely Sthānakavāsī.
- **Why it blocks:** there is nothing to build on. The entire corpus is a *creation* task, not an
  *aggregation* task — which is a fundamentally different project scale than the preliminary research implied.
- **Closing action:** direct institutional outreach. Verified real targets whose names appear in sources
  and metadata: the **A.B. Shree Svetambar Sthanakvasi Jain Conference**, the **Shri Vardhaman Sthanakvasi
  Jain Shraman Sangh**, Sthānakavāsī monastic orders and their presses, Sthānakavāsī pathshalas, and the
  manuscript/print collections of Gujarati Jain institutions. Ask for: bibliographies, out-of-print
  titles, permission to digitise, and named scholarly reviewers.

## GAP 3 · The CC0 evidence chain is uploader-asserted, not rights-holder-asserted — **BLOCKING**

- **What we know:** ~1,807 Jain items sit in CC0-tagged patron-library collections; specific CC0 instances
  of the Sthānakavāsī-published *Ardhamāgadhī Dictionary* (v1 1923, v3 1930, v4 1932) and of *Jain Dharma*
  (Muni Sushil Kumar, 1958, A.B.S. Sthānakavāsī Jain Conference Bhavan) were verified.
- **What is missing:** who has standing to apply CC0 to each item — the author? the publisher? the
  scanning institution? For pre-1966 works this may not matter (PD by age), but for the many post-1966
  items in the same collection it matters critically.
- **Closing action:** (a) build the per-item year/death-year audit (§4 rule-set of the licence audit);
  (b) contact the uploader institutions for a written statement of basis; (c) ⚖️ obtain counsel's view on
  whether CC0 upload of a PD work by a third party creates a usable licence (our working position: the
  work is PD regardless of licence metadata, so train on PD works and cite the licence as corroboration).

## GAP 4 · No Prakrit in any embedding model, tokenizer, or OCR model — **MATERIAL**

- **Verified:** no embedding model on the Hub lists Prakrit (jina v3 lists `sa` but not `pra`);
  the only Prakrit-language Hub artefact is one Mahārāṣṭrī↔English parallel corpus (Apache-2.0);
  OCR language tags across all 2026 VLM-OCR leaders are zh/en/ja/ko/ru/de/fr/es.
- **Why it matters:** dense retrieval will underperform on the tradition's own canonical language, and
  token costs for Ardhamāgadhī are unknown.
- **Closing action:** (1) measure tokenizer efficiency (tokens/word) for Ardhamāgadhī, Gujarati, Hindi,
  Sanskrit and English on our actual texts — this is a 30-minute experiment with a large consequence;
  (2) build the normaliser/transliterator; (3) build the verse-aligned parallel set needed to fine-tune
  an embedder; (4) report per-language recall@10 honestly in the model card.

## GAP 5 · Prakrit/Prakrit-adjacent lexical resources beyond the *Ardhamāgadhī Dictionary* — **MATERIAL**

- **What we know:** the *Illustrated Ardha Magadhi Dictionary* (5 vols, Muni Ratnachandraji,
  1923–1938, Sthānakavāsī-published) exists with verified CC0 instances for at least vols 1, 3 and 4.
  An *Ardha-magadhi Dictionary Part 4* also exists as a DLI item. Other lexicographic items appear in the
  CC0 Jain library (*Jainendra Siddhanta Kosa* Part 1, *Jaina Dictionary*, *Dhaturatnakar* Part 3).
- **What is missing:** whether all five volumes are available with a clean licence; whether the CC0
  instances are complete; and whether better Prakrit dictionaries (e.g. Pischel-adjacent works, Sheth's
  *Pāia-sadda-mahaṇṇavo*) are digitally available with usable rights.
- **Closing action:** enumerate all volumes, verify CC0 per volume, and **hand-type the headword–gloss
  core** of at least one volume. This is the single highest-value manual data-creation task in the project.

## GAP 6 · Sthānakavāsī material is almost entirely 20th–21st-century Gujarati/Hindi print — **MATERIAL**

- **What we know:** found assets are 1936–1992 Gujarati/Hindi items (āgama translations 1920–1966,
  pravachan collections 1960–1965, history 1941, lay-conduct 1960, smārikās 1976 and 1992).
- **Why it matters:** **the Prakrit canon is PD, but the community's actual reading material is not.**
  A legally clean V1 will therefore be able to *quote scripture* far more easily than it can *explain how
  the Sthānakavāsī tradition reads it*. That asymmetry will show up as a quality cliff in evaluation.
- **Closing action:** prioritise rights-holder permission for a *small, high-value* set of translations and
  commentaries rather than trying to clear everything. Ten cleared Gujarati volumes beat a thousand unsettled ones.

## GAP 7 · Gujarati OCR has no production-grade option — **MATERIAL**

- **Verified:** PaddleOCR ships a Devanagari recogniser but no Gujarati recogniser; the only Gujarati OCR
  model found (`umangchaudhari/gujarati-ocr`, Mar 2026, Apache-2.0) has ~305 downloads; archive.org's own
  Tesseract pipeline detected **Bengali** at 46.6% confidence on a Gujarati item.
- **Why it matters:** the majority of the distinctively Sthānakavāsī material is Gujarati. Without OCR,
  that material cannot be indexed at scale.
- **Closing action:** run the 200-page pilot (Devanagari × Gujarati × three typographic eras), publish CER
  per cell, and treat "Gujarati OCR ≥ 98% CER-corrected" as an explicit research problem with a possible
  fine-tune of a 2026 VLM-OCR on synthetic + real pairs.

## GAP 8 · GRETIL's rights per contribution are unstated — **MATERIAL**

- **Verified:** GRETIL offers a Jaina section, a Prakrit e-text corpus and a bulk "Download All Prakrit
  Texts", is migrating to TEI, and states texts come from "various individuals and institutions" of
  "varying sources and quality" — with **no licence statement on the site**.
- **Closing action:** enumerate GRETIL's Jaina + Prakrit files, record each contributor, and determine
  per file whether the underlying edition is PD. Typed Unicode Prakrit is worth more than any OCR output
  we could produce, so this inspection is high-value and cheap.

## GAP 9 · Translation and commentary coverage is unmeasured — **MATERIAL**

- Which of the 11 extant Aṅgas, 12 Upāṅgas and the Mūlasūtras have (a) a typed Prakrit text, (b) a Hindi
  anuvāda, (c) a Gujarati anuvāda, (d) an English translation, (e) a traditional commentary — and under
  what rights? **We have no field-wide census.** Every prior Jain-AI project (JainGPT, JLOR, Jainaagam)
  faces the same gap, which is likely why none publishes a canon-coverage matrix.
- **Closing action:** build the **canon coverage matrix** as a first-class deliverable
  (`coverage_matrix.csv`: one row per text × {typed_text, translation, commentary} × {present, rights, source_id}).
  This artefact is publishable on its own and is arguably the most useful thing this project can give the
  field, independent of the model.

## GAP 10 · No scholar relationship exists yet — **BLOCKING (for v0.2+)**

- The project cannot produce a trustworthy benchmark or SFT set without Sthānakavāsī reviewers. **No
  reviewer is named here because naming one would be inventing one.**
- **Closing action:** before any instruction data is generated, secure at least two reviewers with
  institutional affiliation and agreement on honoraria, the annotation schema, and how disagreement is
  adjudicated and published. Design review to be **paid, credited, and revocable**.

## GAP 11 · No audio corpus (pravachan) — **NICE**

- Sthānakavāsī teaching is substantially oral, and there is a `sarvamai/sarvam-translate` model plus
  ai4bharat ASR (`indic-conformer-600m-multilingual`) capable of Gujarati/Hindi speech. A pravachan audio
  corpus could be the largest genuinely Sthānakavāsī-specific resource in existence.
- **Blocking issues:** rights and speaker consent, and diarisation/quality at scale.
- **Closing action:** a scoping study only — do not build audio before text provenance is solved.

## GAP 12 · Search-engine access was unavailable during this investigation — **NICE but affects confidence**

- Every web-search query returned no results, so discovery ran through official APIs instead. That
  produced **stronger** evidence for the sources I did reach (licence tags, dates, download counts read
  directly), but it **weakens coverage**: a search engine would likely surface Gujarati-language
  Sthānakavāsī sites, PDFs, and institutional pages that no API indexes.
- **Closing action:** re-run discovery with a working search engine using the query list in
  `jain_svk_next_steps.md` §6 before finalising `corpus-v0.1`. **Treat the current manifest as a strong
  v0, not as exhaustive.**

## GAP 13 · Items individually flagged ❓ UNVERIFIED

| Item | Why unverified |
| --- | --- |
| OPenn Jain manuscript item-level rights (e.g. Ms. Indic 20 CC BY 4.0) | Not re-fetched this session; verify per item |
| CC0 status of *Ardhamāgadhī Dictionary* vols 2 and 5 | Only vols 1, 3, 4 confirmed CC0 |
| Whether Sthānakavāsī counts Cūlikasūtras within the 32 | Depends on GAP 1 |
| Whether "Āgama Suttāṇi" is a Terapanth or Sthānakavāsī publication | Not found on Internet Archive; attribution must be bibliographically confirmed before use |
| Publisher attribution of the DLI Hindi āgama translations (1920–1966) | DLI metadata lacks `publisher`; "Sthānakvasi" appears in the item *text*, implying but not proving Sthānakavāsī provenance |
| Exact text-layer quality of each CC0 item's `_djvu.txt` | Sampled one Gujarati item; needs systematic CER measurement per item |
| HF `datatrove`, PyMuPDF (AGPL), `indic-transliteration` licences | Not verified this session |
| Cloud GPU 2026 pricing | All cost figures are engineering estimates, unquoted |

---

## What would most change our conclusions

Ranked by how much a single new fact would move the design:

1. **A Sthānakavāsī institution granting digitisation rights to its published corpus.** This single event
   would change the project from "assemble fragments" to "build on a real corpus", and would justify the
   CPT stage that the current data volume does not.
2. **The enumerated 32-āgama list.** Unblocks `canon_scope` and all sect metadata.
3. **A typed Unicode Ardhamāgadhī corpus of even the 4 Mūlasūtras.** Removes OCR from the critical path
   and gives the benchmark real gold references.
4. **A Gujarati OCR model that actually works.** Converts the largest body of distinctively Sthānakavāsī
   print from "images" to "text".
5. **Evidence contradicting our central assumption.** We assumed the binding constraint is *law + data*,
   not model quality. If a permissive 2026 model turns out to handle Prakrit well out of the box, the
   priority shifts from corpus engineering to evaluation — but nothing in this investigation supports that.

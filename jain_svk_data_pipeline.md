# jain_svk_data_pipeline.md

Covers Parts 13–15 and 17–18 operationally: acquisition, licence gating, OCR, normalisation,
deduplication, contamination control, instruction generation, and human verification.

**Governing principle:** the pipeline is **licence-first and provenance-first**. A file that cannot be
licensed never reaches the parser; an item that loses its provenance is deleted, not repaired.

---

## 1. Pipeline overview

```
┌─ 0  SOURCE REGISTRY      every candidate source, with its licence verdict, before any bytes are fetched
├─ 1  ACQUISITION          API-driven, rate-limited, no scraping of unlicensed sites
├─ 2  LICENCE GATE         deterministic rules (license_audit §4) → 🟢 pass / 🟡 hold / 🔴 reject
├─ 3  DOCUMENT PARSING     PDF/scan → pages; EPUB/HTML/TXT → structured text; record parser + version
├─ 4  OCR (conditional)    only for 🟢/🟡-eligible scans; consensus + human gate
├─ 5  UNICODE NORMALISATION NFC + variant folding + transliteration variants indexed side-by-side
├─ 6  LANGUAGE / SCRIPT DETECTION   per page and per chunk; mixed-script chunks flagged
├─ 7  SEGMENTATION         verse / sutta / section units — never fixed-size windows
├─ 8  METADATA EXTRACTION  title, edition, author, sect, canon_scope, pub_year, verse addresses
├─ 9  CITATION ANCHORING   every unit gets a stable, human-checkable address
├─ 10 DEDUPLICATION        exact → near → semantic → cross-repository duplicate pairs
├─ 11 QUALITY FILTERING    length, garbage ratio, language confidence, repetition, boilerplate
├─ 12 SPLIT               train / validation / test BY DOCUMENT  +  SEALED benchmark repo
├─ 13 INSTRUCTION GEN      grounded-only synthesis + deterministic validation + review
└─ 14 HUMAN VERIFICATION   stratified sampling, dual review, κ, versioned review log
```

Every stage **emits a manifest row** — a single Parquet/JSONL table is the project's system of record,
and every downstream artefact points back into it by `source_id` + `chunk_id` + `pipeline_version`.

---

## 2. Stage 0–1 · Source registry and acquisition

- Registry lives in `sources/registry.csv` (the manifest in `jain_svk_corpus_manifest.csv` is its v0).
- Acquisition is **API-only** where an API exists:
  - **Internet Archive**: `advancedsearch.php` for discovery, `/metadata/<id>` for file inventory,
    then the exact derivative to fetch (`*_djvu.txt` for text, `*_hocr.html`/`_djvu.xml` when word
    positions matter, `*_jp2.zip` only if we intend to re-OCR).
  - **Hugging Face**: `huggingface_hub` for datasets; record the resolved **revision SHA**, never `main`.
  - **GRETIL**: bulk per-language archives + per-text plain/TEI files; record the contributor name.
- **Never** crawl: Jain eLibrary, temple sites, pathshala sites, forums, JainGPT/JainQQ/AI-Yashvi. Their
  terms are unread or absent (verified for Jain eLibrary). Any future use requires written permission
  recorded in `consent_status`.
- **Idempotency:** every fetch is keyed by `(repository, identifier, file, sha256)`; re-running is a no-op.

---

## 3. Stage 2 · Licence gate (the stage that protects the whole project)

Implements the deterministic rule set from `jain_svk_license_audit.md` §4. Inputs: platform `license`,
`pub_year`, `author_death_year`, `publisher`, `uploader`, `consent_status`. Outputs:
`TRAIN` / `RAG_ONLY` / `RESEARCH_ONLY` / `DO_NOT_USE` + `license_evidence_url` + verifier + date.

**Fail-closed.** Missing `pub_year` → 🟡, not 🟢. Unknown `author_death_year` for a pre-1966 work → 🟡
pending a one-line bibliographic lookup (these usually resolve to 🟢 and are the main audit workload).
**A `🟡` item may never be promoted by an automated process.**

Two extra gates beyond copyright, both required only for Sthānakavāsī-targeted content:
`consent_status` (community consent) and `sectarian_confidence` (attribution evidence strength).

---

## 4. Stage 3 · Document parsing

| Input | Tool | Notes |
| --- | --- | --- |
| Internet Archive `_djvu.txt` | direct | Cheapest; **OCR quality is the constraint**, not parsing |
| IA `_djvu.xml` / `_hocr.html` | `hocr`/XML parsing | Preserves word boxes → enables page-line verification and re-OCR alignment |
| PDF (born-digital) | PyMuPDF (`fitz`) | Text layer is authoritative; keep page numbers |
| PDF (image-only) | image extraction → OCR stage | Detect by text-layer density threshold |
| EPUB / HTML | `selectolax` / `beautifulsoup4` | Strip nav/boilerplate; keep structural headings |
| TXT (GRETIL) | plain + TEI XML | **TEI where available** — it carries structure we would otherwise have to guess |
| JSON/JSONL/CSV (HF datasets) | pandas/pyarrow | Record upstream revision SHA |

Record for every document: `parser`, `parser_version`, `extraction_timestamp`, `input_sha256`, `output_sha256`.

---

## 5. Stage 4 · OCR pipeline (Part 13)

```
SCAN
 ↓ IMAGE PREPROCESSING      grayscale → deskew (Hough) → denoise → adaptive binarise; keep the original
 ↓ LAYOUT + LINE DETECTION  PP-OCRv5_server_det (Apache-2.0) or a VLM layout model
 ↓ OCR — TWO ENGINES
      engine A: PaddlePaddle/devanagari_PP-OCRv5_mobile_rec     (Apache-2.0)   [Devanagari]
      engine B: one 2026 VLM-OCR (chandra-ocr-2 / DeepSeek-OCR-2 / GLM-OCR / Unlimited-OCR)
                — verified: none declares Indic scripts, so this is an EXPERIMENT, not a dependency
      Gujarati:  umangchaudhari/gujarati-ocr — experimental only, ~305 downloads, unproven
 ↓ TEXT NORMALISATION       both outputs → NFC Devanagari; strip OCR artefacts
 ↓ AGREEMENT SCORING        exact post-normalisation match → auto-accept
                            else → human queue with both candidates shown side by side
 ↓ SCRIPT/LANGUAGE DETECTION per line; flag lines whose detected script ≠ expected
 ↓ LEXICAL VALIDATION       token check against the Ardhamāgadhī lexicon built from the CC0 dictionaries
 ↓ HUMAN SAMPLE REVIEW      stratified by book/script/period; measure CER on the review set, publish it
 ↓ STRUCTURED CORPUS        only then does anything enter the corpus
```

### Design rules (from verified evidence)

1. **Trust nothing from a single engine.** Archive.org's own Tesseract pipeline was verified to
   mis-detect Gujarati as **Bengali at 46.6% confidence** on an actual Gujarati item in our target set.
   Any pipeline that reads `_djvu.txt` as ground truth will ingest systematic, invisible corruption.
2. **Never publish OCR as scripture.** The corpus records `ocr_engine`, `ocr_confidence`, and
   `human_verified`; the reader model must cite the *verification status*, and unverified OCR is marked
   `PROVISIONAL` and excluded from the sealed benchmark's gold references.
3. **Prakrit: type, don't OCR.** For the canonical core, human typing is cheaper than a speculative
   OCR project and yields ground truth that makes OCR measurable later.
4. **Keep the image.** Store page image references so every text line is re-checkable. This is what makes
   provenance real rather than claimed.
5. **Measure, then decide.** Before scaling OCR, run a 200-page pilot across (Devanagari, Gujarati) ×
   (1920s, 1960s, 1990s) typography, compute CER per cell, and only automate cells with acceptable CER.

---

## 6. Stage 5–7 · Normalisation, detection, segmentation

### 6.1 Normalisation and representation (this is a first-class engineering component)

| Concern | Handling |
| --- | --- |
| Unicode | **NFC** canonical; explicit mapping tables for known confusables and combining-order variants |
| Ardhamāgadhī orthography | Fold attested variants (`ṃ`/`ṁ`/`m̐`, anusvāra vs anunāsika, `ṇ`/`n` in specific editions, macron/diacritic loss from OCR) into a canonical key **while preserving the original in a parallel column** |
| Scripts | Store the **original** script verbatim; store a **Devanagari canonical** form; store an **IAST canonical** form. Retrieval indexes all three; display uses the original |
| Transliteration rate | IAST↔Devanagari↔Gujarati with an explicit lossy/lossless marker so we never silently "fix" a text |
| Sandhi | Do **not** automatically split Prakrit sandhi in the canonical field; where a split improves retrieval, store it as an additional *search variant*, never as the text |

**Why this matters more than the model choice:** the corpus's own metadata problem (32 vs 45 āgamas) and
the retrieval problem (no Prakrit embedding model) both reduce to *representation*. Getting normalisation
right converts an impossible retrieval problem into a tractable one.

### 6.2 Segmentation rules

- Canonical texts → **sutta/verse units**, with `text_id`, `section`, `verse`, `edition`.
- Prose (commentary, pravachan, history) → **paragraph/section units**, with `page` and `heading path`.
- **Never** fixed-token chunks as the primary unit. Fixed windows may exist only as a *fallback index*
  for texts where structure is unknown, and must be tagged `segmentation: FALLBACK` so evaluation can
  exclude them.
- Every unit is capped so that a citation is unambiguous: if a unit is longer than ~1,500 characters,
  it must carry an internal anchor.

---

## 7. Stage 8–9 · Metadata and citation anchoring

Mandatory per chunk:
`source_id · text_id · text_name_skt · text_name_prakrit · category · canon_scope · tradition · sect ·
language · script · edition · publisher · pub_year · section · verse · chunk_id · parent_sutta_id ·
license · license_evidence_url · training_permission · human_verified · ocr_engine · quality_score ·
pipeline_version`

**`canon_scope`** is an enum that carries the sect question directly:
`SVK_32 | MURTIPUJAKA_45 | DIGAMBARA | TERAPANTH | GENERIC_JAIN | MODERN_SECULAR | MULTI_TRADITION | UNKNOWN`.
`MURTIPUJAKA_45` items are a legitimate part of a *Jain* research corpus but must never be presented as
Sthānakavāsī authority — and the router will filter them out for Sthānakavāsī-scoped queries.

---

## 8. Stage 10 · Deduplication and contamination (Part 15)

### 8.1 Duplicate taxonomy we actually face

| Type | Real example found | Detection |
| --- | --- | --- |
| **Cross-repository duplicate** | `Ardha Magadhi Dictionary` vol 4 exists as both a CC0 `kbii-` item and a no-licence `in.ernet.dli.*` item | Title/author/year blocking + text-hash comparison; **prefer the better-licensed instance** |
| **Same work, different volumes/editions incorrectly merged** | vols 1–5 of the same dictionary across many uploads | Fuzzy title match **plus** volume/edition parsing — never merge across editions |
| **Photo-duplicate scans** | two scans of the 1941 Conference history (`in.ernet.dli.2015.258851`, `dli.ernet.410253`) | SimHash/MinHash + page-image perceptual hash |
| **Repeated verses across texts** | shared gāthās between canon texts and later anthologies | **Do NOT deduplicate** — mark as `repeated_verse_of` and keep both, so citations resolve correctly |
| **Repeated translations** | multiple Hindi anuvādas of Uttarādhyayana (1934, 1962) | Distinct `edition` entries; never collapsed |
| **OCR duplicates inside a book** | re-OCR pages, duplicated headers/footers | Boilerplate stripping + line-level MinHash |
| **Copied web content / synthetic text** | none identified yet; will appear | Similarity to known LLM outputs; provenance requirement means anything without a source is rejected |

### 8.2 Algorithm ladder (cheap → expensive)

1. **Exact** — sha256 per chunk and per document.
2. **Near-duplicate documents** — MinHash + LSH (`datasketch`), threshold tuned on a hand-labelled pair set.
3. **Near-duplicate chunks** — same, at chunk granularity; suffix-array exact-substring removal
   (`deduplicate-text-datasets`) for long shared spans.
4. **Semantic dedup** — cluster chunk embeddings; **never auto-delete** on semantic similarity alone
   (scripture genuinely repeats). Use it to surface candidates for human review.
5. **Image-level** — perceptual hash on page images to catch re-scans of the same physical book.

### 8.3 Train/eval contamination control (the part that protects the benchmark)

- The benchmark is built **before** the training corpus is finalised, stored in a **separate repo**, and
  listed in `eval/sealed_ids.json`.
- **Split by document, not by chunk** — otherwise the same book leaks across splits.
- A **hard guard** in the training pipeline: assert `set(train_doc_ids) ∩ set(bench_doc_ids) == ∅`, and
  additionally run n-gram overlap (13-gram, the standard) between every training item and every benchmark
  item; any overlap above threshold fails the build.
- Publish the contamination report in the model card. "We checked" is not evidence; the report is.
- **Re-run the guard after every corpus version bump.** This is the most likely way this project would
  silently corrupt its own benchmark.

---

## 9. Stage 11–12 · Quality filtering and splits

Filters (each with a recorded reason and a tunable threshold; all thresholds **tuned on a hand-labelled
sample**, not invented):

| Filter | Signal |
| --- | --- |
| Garbage/mojibake ratio | share of characters outside expected Unicode blocks; OCR noise markers |
| Language confidence | per-chunk detection; `UNKNOWN` chunks quarantined |
| Script purity | mixed-script chunks flagged (mandatory for a corpus with 4 scripts) |
| Length | min/max chunk length; drop fragments |
| Repetition | line/paragraph duplication within a document |
| Boilerplate | publisher pages, catalogues, tables of contents, colophons — **kept separately** as metadata, not discarded (colophons carry provenance) |
| Dictionary/lexicon content | detected and routed to a **separate lexical index**, not mixed into prose training |

Splits: **train / validation / test by document**, stratified by `language × canon_scope ×
verification_status`, plus the sealed benchmark. Publish split membership lists so results are reproducible.

---

## 10. Stage 13–14 · Instruction generation and verification

See `jain_svk_architecture.md` §5–6 for the workflow; operational requirements here:

- **Grounded-only generation**: the prompt contains exactly one retrieved passage and the model is
  instructed to ABSTAIN when the answer is absent. Store `passage_hash`.
- **Deterministic validation before any LLM judge**: citation resolves; quoted span is a literal substring
  of the normalised passage; declared language matches detected language; no ungrounded numeric/ID tokens.
  **A failed substring check is terminal — no repair, no judge override.**
- **Provenance per item**:
  `item_id · source_id · citation · original_span · question · answer · authority_level ·
   generator · generator_version · prompt_hash · seed · reviewer_status · reviewer_ids · review_date`.
- **`authority_level` enum**: `SCRIPTURE` (verbatim, retrieved) / `TRADITIONAL_COMMENTARY` /
  `MODERN_SCHOLARSHIP` / `AI_EXPLANATION`. The training target must never present `AI_EXPLANATION` in the
  same voice as `SCRIPTURE`.
- **Review log** is append-only (`reviews.jsonl`); dataset versions are cut from a frozen review state.

---

## 11. Reproducibility contract

1. Every stage is a versioned script; every artefact records `pipeline_version` + input hashes.
2. The corpus can be **rebuilt end-to-end from the manifest** with no network except the recorded
   `download_url` + expected `sha256`.
3. Any item whose `sha256` does not match is an error, not a warning.
4. The build is **deterministic**: fixed seeds, sorted inputs, and a build hash published with each
   corpus release; two runs must produce byte-identical Parquet.
5. **No manual edits** to corpus files. Corrections are applied as versioned patch records so the
   provenance chain is never broken.

---

## 12. Tool summary

| Need | Tool | Licence | Note |
| --- | --- | --- | --- |
| Pipeline orchestration | `datatrove` (HF) | Apache-2.0 ⚠️ verify | Designed for large text pipelines; local-friendly |
| Dataframes | polars / pyarrow | MIT / Apache-2.0 | Parquet-native |
| Near-dedup | `datasketch`, `text-dedup` | MIT / Apache-2.0 | MinHash+LSH |
| Exact substring dedup | `google-research/deduplicate-text-datasets` | Apache-2.0 | Suffix-array |
| OCR | PaddleOCR (PP-OCRv5) | Apache-2.0 | Devanagari rec available; **no Gujarati** |
| OCR (VLM) | chandra-ocr-2 / DeepSeek-OCR-2 / GLM-OCR / Unlimited-OCR | openrail / **Apache-2.0** / **MIT** / **MIT** | All unproven on Indic |
| PDF/HTML | PyMuPDF, selectolax, `hocr` | AGPL ⚠️ / MIT | **Check PyMuPDF's AGPL for a permissive project**; `pdfplumber`/`pypdfium2` are alternatives |
| Normalisation | `unicodedata`, `indic-transliteration`, custom tables | permissive ⚠️ verify | Custom rules unavoidable |
| Embedding | sentence-transformers / transformers | Apache-2.0 | |
| Vector DB | LanceDB (→ Qdrant) | Apache-2.0 | |
| Fine-tuning | Unsloth + TRL + PEFT + bitsandbytes | Apache-2.0 / MIT | |
| Serving | llama.cpp, Ollama, vLLM | MIT / MIT / Apache-2.0 | |
| Eval harness | custom (pytest + polars) | Apache-2.0 | Keep it in-repo; no SaaS |

**Licence hygiene on tools too:** PyMuPDF is AGPL — do not put it on the critical path of a
permissively-licensed project without review.

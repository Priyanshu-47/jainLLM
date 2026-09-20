# DATA CARD — svk-corpus v0.1

**Corpus version:** `svk-corpus-v0.1`
**Generated:** 2026-09-17 (see `data/reports/corpus_statistics.md` for the exact timestamp of the current build)
**Status:** first release. RAG-ready and training-ready. **Not** a complete corpus of anything.

---

## 1. What this dataset is

A licence-gated, provenance-complete text corpus built from sources that passed a
deterministic copyright gate. It exists in two products:

| Product | File | Contents | Records |
| --- | --- | --- | --- |
| RAG corpus | `data/release/rag_corpus.jsonl` | All units from gate-released sources (TRAINING_ALLOWED + RAG_ALLOWED), optimised for retrieval and citation | 50,325 |
| Training corpus | `data/release/training_corpus.jsonl` | Units only from sources whose gate state permits weight updates | 30,361 |

Excluded units are **not silently dropped**: 18,651 units were withheld by
quality floors, and every excluded *source* is listed with its gate rule in
`data/release/excluded_sources.jsonl`.

## 2. Contents in one table

| Measure | RAG | Training |
| --- | --- | --- |
| Records (text units) | 50,325 | 30,361 |
| Characters | 4,402,832 | 4,150,595 |
| Words (whitespace) | 777,117 | 725,085 |
| Tokens (sarvam-30b tokenizer) | 1,604,385 | 1,455,295 |
| Tokens (qwen3-0.6b tokenizer) | 1,906,474 | 1,722,572 |

All tokenizer measurements were performed by running the real `tokenizer.json`
files over the corpus; none are estimated. See §5.

## 3. Sources released (13)

| Source id | Title | Sect attribution | Basis |
| --- | --- | --- | --- |
| SVK-0007 | Ardha Magadhi Dictionary vols 2 & 5 (1927) | STHANAKAVASI | publisher imprint |
| SVK-0037 | Illustrated Ardha-Magadhi Dictionary vol 1 (1923) | STHANAKAVASI | publisher imprint |
| SVK-0016 | Shri Utradhyayan Sutar (Agam Seva) (1920) | unknown | — |
| SVK-0038 | Notes on Modern Jainism (1910) | MULTI_TRADITION (describes Sthanakavasi) | — |
| SVK-1001 | Gaina Sutras, Sacred Books of the East (1884) | SVETAMBARA | — |
| SVK-1002/3 | The Kalpa Sutra and Nava Tatva (1848, 2 scans) | SVETAMBARA | — |
| SVK-1005 | Notes on the Religious Literature of India (1920) | MULTI_TRADITION | — |
| SVK-1006 | Jaina Psychology (1929) | unknown | — |
| SVK-1007 | Essai de bibliographie jaina (1906) | unknown | — |
| SVK-1008 | Notes on the Jainas (1911) | MULTI_TRADITION | — |
| SVK-1009 | Risabha Deva, the Founder of Jainism (1929) | unknown | — |
| SVK-1010 | Jain Shvetambar Conference Herald (1917) | unknown | — |

Full metadata per source: `manifests/source_manifest.csv`.
Gate decision per source: `manifests/license_manifest.csv`.

## 4. Coverage — read the asymmetries before using this

**Language (RAG units):** en 36,164 · unknown 12,177 · hi 1,984.
The corpus is *majority English* — it is dominated by pre-1930 scholarly books
about Jainism, not Jain scripture. Gujarati, Sanskrit and Prakrit as separate
classes are effectively absent from this release.

**Script (RAG units):** Latin 36,164 · Devanagari 14,161.
No Gujarati-script record was released.

**Sect:** 12,177 records carry `STHANAKAVASI` attribution (both Ardha-Magadhi
Dictionary editions). **This is imprint-based, not content-verified**: the sect
field records the publisher (A.B. Sthanakvasi Jain Conference / Shastroddhar
Samiti), not a per-verse determination. Do not treat sect as ground truth for
any individual verse.

**Text role:** every released record is `ORIGINAL` (transcription-of-scan
origin, preserving the source text layer). There is no translation layer, no
commentary layer, and no bilingual alignment in v0.1.

**Unit types:** paragraph 37,199 · section 12,292 · verse 708 · chunk 126.
Only 708 units are `verse`-typed (terminated by the double danda ॥). A
paragraph unit must never be cited as numbered scripture — per-unit
`structure_confidence` marks this (`unknown` for paragraphs, `high` for ॥-terminated verses).

## 5. Tokenizer efficiency (why it matters for model choice)

Measured on the RAG corpus:

| Tokenizer | Tokens | tok/char |
| --- | --- | --- |
| qwen3-0.6b / qwen3-embed-0.6b | 1,906,474 | 0.4330 |
| qwen3.5-4b | 1,808,634 | 0.4108 |
| gemma-3-4b-it-unsloth | 1,604,358 | 0.3644 |
| gemma-4-E4B-it | 1,604,366 | 0.3644 |
| sarvam-30b | 1,604,385 | 0.3644 |

Indic text costs ~19% more tokens per character under Qwen tokenizers than
under Gemma/Sarvam tokenizers. Every training/inference cost estimate for this
project must carry the tokenizer split, not a single number.

## 6. Intended use

- **Intended:** building a retrieval corpus and, later, a *study/research
  assistant* over Sthānakavāsī Jain literature; linguistic analysis of the
  digitised material; reproducible corpus engineering research.
- **Not intended, and must not be claimed:** the model or corpus as a
  religious authority; scholarly editions for ritual use; substitute for a
  Jain teacher, ācārya, or critical edition.

## 7. Limitations (all verifiable in the reports)

1. **CPT verdict: NO.** 1,455,295 clean training tokens = 2.9% of the 50M
   threshold. Continued pretraining is not justified at this scale; RAG + SFT
   remains the path.
2. **18,651 units withheld by quality floors** — dominated by
   `SCRIPT_CONFUSION` (18,295): units whose Devanagari-codepoint text fails
   lexical-validation. These are preserved in the intermediate layers, not
   deleted.
3. **3 sources require manual OCR review** before their text may be treated as
   even provisional scripture.
4. **No content-level sect marking** (see §4).
5. **OCR provenance:** no OCR engine was installed in the build environment;
   the pipeline consumed Internet Archive's pre-existing OCR text and *measured*
   its quality (mean OCR-noise estimate 0.152) instead of generating new OCR.
6. **Duplicate rate 6.57%** across 73,828 assessed units (4,821 exact + 31
   near), before the release split.

## 8. Format

JSONL, one text unit per line. Key fields: `id`, `source_id`, `text`,
`normalized_text`, `text_role`, `language`, `script`, `tradition`, `sect`,
`unit_type`, `page`, `section`, `structure_confidence`, `provenance`
(source_url + artifact sha256), `license` (status + rule id),
`quality` (flags + metrics). Fields with no evidence are `null`/`"unknown"`,
never invented.

## 9. Licensing summary (of the 48-source manifest)

TRAINING_ALLOWED 15 · WITH_CONDITIONS 19 · UNKNOWN 10 · NEEDS_PERMISSION 2 ·
NOT_ALLOWED 1 · RAG_ALLOWED 1. The 13 released sources all carry an auditable
gate decision (rule id + evidence + confidence). Platform metadata (IA CC0
tags) is recorded as an uploader assertion, not treated as clearance.

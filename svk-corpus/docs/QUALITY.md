# QUALITY — svk-corpus v0.1

Quality here is **reported, not averaged away**. There is no single quality
number that gates a unit; there are per-unit metrics, per-unit flags, and
release floors, all inspectable.

## 1. The metric families

| Family | What it measures | Where |
| --- | --- | --- |
| `unicode_quality` | replacement chars, orphan combining marks, malformed sequences, symbol ratio | per unit |
| `ocr_quality` | OCR-noise estimate from lexical validation + replacement-char density | per unit |
| `structural_quality` | unit_type and structure_confidence consistency | per unit |
| `duplicate_rate` | exact + near duplicates across the whole release | corpus |
| `metadata_completeness` | required manifest fields present | per source |
| `provenance_completeness` | source_url + artifact hash + licence decision present | per source |

## 2. Release floors (what actually withheld units)

18,651 of 73,828 assessed units were withheld from the release by explicit
floors, each flag counted in `INGEST_REPORT.md`:

| Flag | Units | Meaning |
| --- | --- | --- |
| SCRIPT_CONFUSION | 18,295 | Devanagari-codepoint text failing lexical validation — the classic "scanned Gujarati read as Devanagari" failure mode |
| HIGH_DIGIT_RATIO | 3,935 | digit density far above prose norms (page numbers, tables, OCR debris) |
| SCRIPT_MISMATCH | 1,557 | detected script contradicts the declared script |
| BELOW_MIN_UNIT_CHARS / VERY_SHORT | 1,003 | below the minimum useful unit size |
| ORPHAN_COMBINING_MARKS | 519 | combining marks without bases (matra loss in OCR) |
| OCR_NOISE_HIGH | 456 | lexical-validation noise above floor |
| HIGH_SYMBOL_RATIO | 363 | symbol soup |
| REPEATED_CHARACTER_RUN / REPEATED_LINES | 12 | OCR repetition pathology |

Withheld units are **retained in the intermediate layers** (`data/segmented/`,
`data/normalized/`) — they are excluded from the release, not deleted, because
a future better OCR pass may recover them.

## 3. The SCRIPT_CONFUSION detector (v0.1's most important check)

Archive.org's own OCR pipeline, on a Gujarati book in our source set, reported
"Bengali 46.6%". Devanagari-codepoint garbage is *statistically* plausible to a
script detector while being lexically nonsense. The detector measures the share
of recognised Devanagari lexical tokens (vs CV-ratio garbage) and routes units
below the floor out of the release. It exists because "96% Devanagari" on a
Gujarati book is a *contra*-indicator, not a quality score.

## 4. Duplicate rate

Across 73,828 assessed units: 4,821 exact + 31 near = **6.57%**. Exact dedup is
scoped to (text_role, language) populations — a translation layer is not a
duplicate of its original, a commentary is not a duplicate of its base text.
Semantic dedup is deliberately disabled for v0.1 (no embedding model in the
research set has credible Prakrit coverage; a wrongly merged sūtra is
undetectable downstream).

## 5. OCR status — stated plainly

No OCR engine (Tesseract, PaddleOCR, etc.) was installed in the build
environment. v0.1 therefore **performed no OCR of its own**. The pipeline
consumed Internet Archive's pre-existing OCR derivatives where they were the
best available machine-readable layer, and *measured* that text:

- mean OCR-noise estimate over assessed units: 0.152
- 3 sources flagged `manual_review_required`
- OCR-quality figures in the reports describe IA's OCR, never ours

The OCR stage interface (`src/svk_corpus/ocr/pipeline.py`) exists so that a
real engine can be added without touching the quality or release stages.

## 6. Structure honesty

- Only units terminated by the double danda ॥ are typed `verse` (708 units),
  with `structure_confidence: high`.
- Prose paragraphs carry `structure_confidence: unknown` — they are not
  silently promoted to scripture.
- Headings must pass a conservative test (short, single-line, no verse marks,
  no terminal punctuation); doubtful blocks stay content.
- Page numbers-as-content blocks are dropped from content and counted.

## 7. Normalisation honesty

`NORMALIZATION_VERSION = "1.0.0"`. The normaliser:

- preserves ZWNJ/ZWJ (orthographically meaningful in Indic scripts) and counts them;
- preserves form feeds (page boundaries — citations depend on them);
- counts replacement chars and orphan marks instead of "fixing" them;
- keeps NFC by default; NFKC is opt-in and never applied blindly to scripture;
- returns `raw` untouched alongside `normalized`, with a per-document stats
  block (`spaces_folded`, `newlines_normalized`, `zero_width_removed`, …).

## 8. Validation

`make validate` re-checks every release record against the schema and the gate
contract. Current build: **80,686 records checked, 0 problems**. Validation
checks include: required fields present and non-fabricated, licence status
consistent with the source's gate decision, provenance (source_url +
artifact hash) present, quality flags within the known enum.

## 9. What quality does NOT claim

- It does not claim the text is a critical edition. Every released character
  came from scans (or transcriptions) of varying quality; the provenance chain
  tells you exactly which.
- It does not claim sect correctness per verse (see PROVENANCE.md §4).
- It does not claim OCR correctness anywhere it could not measure.

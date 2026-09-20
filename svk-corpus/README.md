# svk-corpus — licence-gated Sthānakavāsī Jain corpus pipeline

**Version:** `svk-corpus-v0.1` · **Status:** first release, validated · **License:** Apache-2.0

This repository builds the first trustworthy, provenance-complete, licence-gated
text corpus for an open Sthānakavāsī Jain AI system. It is deliberately a
**corpus** project: it trains nothing, generates no synthetic Q&A, and treats
legal provenance and textual fidelity as hard gates rather than nice-to-haves.

> A 500K-token clean corpus is worth more than a 100M-token legally ambiguous,
> OCR-corrupted one. This build produced **1,455,295 clean training tokens** —
> and reports that number honestly rather than inflating it.

## Headline results (this build)

| | |
| --- | --- |
| Sources in manifest | 48 (from the research phase) |
| Released | **13** (each with an auditable gate decision) |
| RAG corpus | 50,325 units · 4.4M chars · 1.6M tokens |
| Training corpus | 30,361 units · 4.15M chars · 1.455M tokens |
| CPT verdict | **NO** — 2.9% of the 50M threshold; RAG + SFT is the path |
| Validation | 80,686 records checked, 0 problems |
| Tests | 102 passing |

## Pipeline

```text
manifest → gate → acquire → extract → normalize → segment → dedupe
        → quality → tokens → release → stats → validate
```

```bash
make all        # full rebuild (reuses data/raw/)
make test       # 102 tests
make validate   # re-check every release record
```

Python 3.14, standard library only. See `docs/REPRODUCIBILITY.md`.

## What the gate enforces

Every source gets one of six states from a deterministic rule chain
(`licensing/gate.py`, rules R10–R99, no LLM in the loop):

`TRAINING_ALLOWED · RAG_ALLOWED · WITH_CONDITIONS · NEEDS_PERMISSION ·
NOT_ALLOWED · UNKNOWN`

`NEEDS_PERMISSION`, `NOT_ALLOWED` and `UNKNOWN` never enter the release.
Platform metadata (e.g. an Internet Archive CC0 tag) is recorded as an
**uploader assertion**, never as clearance. This build: 15 TRAINING_ALLOWED ·
19 WITH_CONDITIONS · 10 UNKNOWN · 2 NEEDS_PERMISSION · 1 NOT_ALLOWED ·
1 RAG_ALLOWED.

## What is actually in the release

13 sources, dominated by pre-1930 publications (public domain by publication
date), including the Sthānakavāsī-published **Ardha-Magadhi Dictionary**
editions (1923/1927, 12,177 records attributed by publisher imprint) and
Śvetāmbara canonical translations. Coverage is honest about its asymmetries:
majority English scholarly prose, Devanagari second, **no Gujarati-script
record released**, only 708 ॥-typed verse units.

Full numbers: `data/reports/corpus_statistics.md` ·
limitations and intended use: `docs/DATA_CARD.md`.

## Repository layout

```text
configs/            source curation + policy (floors, thresholds, tokenizer candidates)
manifests/          source_manifest.csv · artifact_manifest.csv · license_manifest.csv
src/svk_corpus/     acquisition · licensing · extraction · ocr · normalization
                    segmentation · deduplication · quality · tokenization · schemas
data/raw/           immutable artifacts + verbatim metadata + sha256 sidecars
data/release/       rag_corpus.jsonl · training_corpus.jsonl · excluded_sources.jsonl
data/reports/       corpus_statistics.md · INGEST_REPORT.md · tokenizer_measurements.json
tests/              102 tests (licensing, normalisation, segmentation, dedup, schema)
docs/               DATA_CARD · PROVENANCE · QUALITY · REPRODUCIBILITY
```

## Non-negotiables baked into the code

1. **Fail closed.** Missing evidence → UNKNOWN → excluded.
2. **Never destroy text.** Raw and normalised layers are separate; ZWNJ/ZWJ and
   form feeds (page boundaries) are preserved; observations are counted, not
   "repaired".
3. **Never fabricate.** Unknown fields stay `"unknown"`; verse types exist only
   where the source has ॥; sect is imprint-based and labelled as such.
4. **Population-scoped dedup.** A translation is not a duplicate of its
   original; a commentary is not a duplicate of its base text.
5. **Measured tokens, not guesses.** Six real candidate tokenizers run over the
   corpus; Indic text costs ~19% more tokens/char under Qwen than Gemma/Sarvam.

## Positioning

The eventual model built on this corpus is a **Jain study/research assistant**.
It is not, and must never be presented as, a religious authority.

## Parent project

Research phase artifacts (corpus manifest, license audit, architecture
decision, model comparison) live in the repository root: `jain_svk_*.md`,
`jain_svk_corpus_manifest.csv`.

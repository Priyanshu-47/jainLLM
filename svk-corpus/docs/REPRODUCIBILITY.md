# REPRODUCIBILITY — svk-corpus v0.1

## 1. The one command

```bash
make all        # manifest → gate → acquire → extract → normalize → segment
                #   → dedupe → quality → tokens → release → stats → validate
```

or, without make:

```bash
PYTHONPATH=src python -m svk_corpus all
```

Individual stages: `make manifest | gate | acquire | extract | normalize |
segment | dedupe | quality | tokens | release | stats | validate | test | clean`.

## 2. Environment

- **Python 3.14, standard library only.** No third-party runtime dependency.
  (`pyproject.toml` declares the package; nothing needs installing.)
- Tokenizer measurement downloads the *real* `tokenizer.json` files for the
  candidate models from Hugging Face and caches them under
  `data/cache/tokenizers/`. A tokenizer that cannot be downloaded is recorded
  with its HTTP status in `tokenizer_measurements.json` — never silently
  omitted.
- Network is required only for `acquire` and `tokens` (first run). Everything
  downstream runs offline from `data/raw/`.

On Windows where `python` is not on PATH:

```bash
make PYTHON="/c/Users/<you>/AppData/Local/Python/pythoncore-3.14-64/python.exe" all
```

## 3. Determinism contract

| Stage | Deterministic? | Notes |
| --- | --- | --- |
| manifest / gate | yes | the gate is a pure function of manifest fields; `evaluated_at` is an input, not wall-clock, when `now=` is passed |
| acquire | yes given same upstream | sha256 recorded; upstream items can change, the hash proves which version was used |
| extract / normalize / segment | yes | no randomness, no locale dependence |
| dedupe | yes | MinHash uses blake2b with fixed salts; LSH bucket ids are stable across processes (never `hash()`) |
| quality / release | yes | floors are thresholds on measured metrics |
| tokens | yes per tokenizer version | tokenizer.json content-addressed by model name; cache dir is content-stable |

Known non-determinism: timestamps written into reports (clearly marked as
generation times), and the *upstream* Internet Archive if items change between
runs — which is exactly why artifact hashes exist.

## 4. What is pinned

- `US_PD_PUBLICATION_CUTOFF = 1929` and `LIFE_PLUS_60_FLOOR_YEAR = 1966` are
  pinned constants in `licensing/gate.py`. The US cutoff advances annually in
  reality; pinning keeps decisions reproducible. Changing a pinned constant is
  a **corpus version bump**, never a silent edit.
- `NORMALIZATION_VERSION = "1.0.0"` — bumped whenever normalisation behaviour
  changes; every normalized artifact records the version that produced it.
- Gate rule set and priority order: fixed tuple `GATE_RULES`; adding a rule is
  a documented diff, and the rule set must remain *total* (asserted).
- Tokenizer candidates: named list in the config; adding/removing one changes
  `tokenizer_measurements.json` but never the text layers.

## 5. Test suite

```bash
make test       # PYTHONPATH=src python -m unittest discover -s tests -v
```

102 tests, all passing at this build. Coverage highlights:

- **Licensing** — unknown/ND/NC excluded, permissive allowed, R70 pre-1930,
  R92 term-unexpired vs R95 chronology-unresolved, uploader-CC0 treated as
  unverified, determinism (same inputs → identical rows).
- **Normalisation** — Gujarati/Devanagari/Sanskrit/Prakrit content preserved,
  ZWNJ/ZWJ preserved and counted, ZWSP stripped, CRLF/tab folding, NFC
  composition, NFKC on Prakrit Roman, raw layer untouched, replacement chars
  counted-not-created, transliteration lossless-or-flagged contract.
- **Segmentation** — form-feed page splitting, verse typing only on ॥,
  headings conservative, no fabricated sections (`structure_confidence:
  unknown` for prose), stable unit ids, oversized units split not lost,
  provenance attached.
- **Deduplication** — identical collapse, population separation (translation ≠
  original, commentary ≠ base, OCR ≠ original), near-dup threshold, MinHash
  determinism and similarity bounds.
- **Schema** — every release record validates against `schemas/records.py`;
  provenance fields required.

## 6. Re-running from scratch

```bash
make clean      # removes data/extracted, data/normalized, data/deduplicated, data/cache
make all        # reuses data/raw (never re-downloads what's present) and rebuilds
```

`data/raw/` and `data/release/` are never touched by `clean`.

## 7. Verifying a published release

Given a released JSONL + this repo:

1. `make test` — the suite must pass.
2. For any record: audit chain per PROVENANCE.md §6.
3. `make validate` — 0 problems expected.
4. Regenerate stats and diff against the published
   `data/reports/corpus_statistics.md` (modulo the generation timestamp).

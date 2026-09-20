# PROVENANCE — svk-corpus v0.1

Rule zero of this repository: **every released record must be traceable to an
original artifact with a content hash, and to a licensing decision with a rule
id.** This document explains the chain and how to audit it.

## 1. The provenance chain

```text
Internet Archive item (or GRETIL file, etc.)
  ↓  acquisition           data/raw/<source_id>/original.*
                          data/raw/<source_id>/metadata.json   (IA metadata verbatim)
                          data/raw/<source_id>/checksums.sha256
  ↓  artifact manifest     manifests/artifact_manifest.csv
                          sha256 + bytes + mime_type + download_timestamp per artifact
  ↓  extraction            data/extracted/<source_id>/*.txt
                          extraction method recorded per artifact
  ↓  normalisation         data/normalized/  (raw_text and normalized_text kept SEPARATE)
  ↓  segmentation          data/segmented/<source_id>/units.jsonl
                          every unit carries page + section + unit_id
  ↓  release               data/release/*.jsonl
                          each record: provenance{source_url, artifact_sha256}
                                       license{status, rule_id}
```

The raw artifact is never modified. Every downstream layer is derived and
re-derivable from it.

## 2. What each release record carries

```json
{
  "id": "SVK-0007:u00123:...",
  "source_id": "SVK-0007",
  "provenance": {
    "source_url": "https://archive.org/details/...",
    "artifact_sha256": "<sha256 of the exact downloaded artifact>"
  },
  "license": {
    "status": "TRAINING_ALLOWED",
    "rule_id": "R70_PRE_1930_PUBLICATION",
    "evidence": "...",
    "confidence": "..."
  },
  "page": 123,
  "section": "…",
  "structure_confidence": "unknown"
}
```

- `artifact_sha256` is the hash of the artifact actually downloaded, not of a
  URL. If the upstream item is ever altered, the hash proves which version we
  used.
- `page` comes from form-feed boundaries in the extraction (the page marker
  emitted by `pdftotext`) and is preserved through normalisation — the
  normaliser treats `\f` as structure, not as a control character to delete.
- `section` is recorded only when the segmenter's conservative heuristic
  detected a heading; it is never fabricated.

## 3. Licensing decisions are audit records, not vibes

Every source has a row in `manifests/license_manifest.csv` produced by the
deterministic gate (`src/svk_corpus/licensing/gate.py`):

- `state` — TRAINING_ALLOWED / RAG_ALLOWED / WITH_CONDITIONS / NEEDS_PERMISSION /
  NOT_ALLOWED / UNKNOWN.
- `rule_id` — the exact rule that fired (R10…R99), in a fixed, documented
  priority order.
- `evidence` — the manifest fields the rule read.
- `requirements` — outstanding conditions for WITH_CONDITIONS states.
- `evaluated_at` — the gate is deterministic: same inputs, same row.

**Platform metadata is not clearance.** An Internet Archive CC0 tag applied by
an uploader is recorded as `uploader_asserted=true` evidence; rule R30 treats
it as an unverified claim requiring supporting chronology (publication year /
death year), never as a grant by itself.

## 4. Sect provenance (important caveat)

`sect` values in the release (e.g. `STHANAKAVASI` for SVK-0007 / SVK-0037)
derive from **publisher imprint metadata** — the Ardha-Magadhi Dictionary was
published by the A.B. Sthanakvasi Jain Conference / Shastroddhar machinery —
recorded during source curation. No content-level sect verification has been
performed. Downstream uses must treat sect as provenance-based attribution,
not as a per-verse fact.

## 5. Text layers are kept separate

`raw_text` (as extracted, byte-preserving) and `normalized_text` (NFC, folded
whitespace, preserved ZWNJ/ZWJ) are separate fields; normalisation also emits
a stats block per document counting every change. Nothing is silently repaired:
observations (replacement chars, orphan combining marks, danda counts) are
counted, not fixed.

## 6. How to audit a single record

1. Take `source_id` + `artifact_sha256` from the record.
2. Find the row in `manifests/artifact_manifest.csv`; it names the raw file.
3. Recompute `sha256sum data/raw/<source_id>/original.*` and compare.
4. Find the licence row in `manifests/license_manifest.csv` and check the rule.
5. For the text: re-run extraction on the raw artifact and diff against
   `data/extracted/<source_id>/`.

## 7. Known provenance gaps

- 2 acquisition failures are recorded in `data/reports/acquisition_failures.json`
  rather than papered over; those sources are absent from the release.
- 10 sources have UNKNOWN gate state (missing publication year or similar) and
  were excluded — the gap is the *evidence*, and the manifest says so.
- IA metadata fields (possible-copyright-status, uploader) are stored verbatim
  in `data/raw/<id>/metadata.json`; they are inputs to the gate, never its
  substitute.

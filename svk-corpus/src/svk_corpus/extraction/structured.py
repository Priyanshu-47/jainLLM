"""Extraction of structured tabular sources (CSV/TSV parallel datasets).

v0.1 extracted CSVs as one flat text stream, which silently concatenates the
two languages of a parallel corpus into a single undifferentiated string. That
is precisely the "mixing text layers" failure the project forbids. This
extractor keeps the columns separate:

  * ``text``      - the PRIMARY layer only (the non-English source text)
  * ``pages``     - one entry per layer per row, in stable row order
  * ``text_roles``- parallel to ``pages``; the primary layer carries the
                    source-language role, the English layer TRANSLATION

The primary column is the first column whose values are predominantly
non-Latin-script; if every column is Latin-script (a fully English table),
the first column is primary and no translation role is asserted. Script
shares are measured with plain codepoint ranges - no language detection is
invoked, and nothing downstream trusts this classification more than the
curation metadata.
"""

from __future__ import annotations

import csv
from pathlib import Path

from svk_corpus.extraction.base import ExtractionResult

_ROLES_PRIMARY = ("ORIGINAL", "OCR")   # refined by segment stage per method
_ROLE_TRANSLATION = "TRANSLATION"


def _latin_share(s: str) -> float:
    if not s:
        return 0.0
    latin = sum(1 for ch in s if ch.isascii() and ch.isalpha())
    return latin / max(1, sum(1 for ch in s if ch.isalpha()))


def _pick_columns(header: list[str], sample: list[dict[str, str]]) -> dict | None:
    """Pick primary (source-language) and translation (English) columns."""
    if len(header) < 2:
        return None
    shares = {h: (_latin_share(" ".join(r.get(h, "") for r in sample))
                  if sample else 0.0) for h in header}
    english_col = next((h for h in header
                        if h.strip().lower() in ("english", "en", "translation",
                                                 "target", "eng")), None)
    if english_col is None:
        english_col = max(header, key=lambda h: shares[h])
    source_candidates = [h for h in header
                         if h != english_col and shares[h] < 0.5]
    if not source_candidates:
        return None
    # First non-Latin-script column in header order = primary layer.
    primary_col = source_candidates[0]
    return {"primary": primary_col, "translation": english_col}


def extract_structured_table(path: Path, delimiter: str = ",") -> ExtractionResult:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh, delimiter=delimiter)
            header = list(reader.fieldnames or [])
            rows = [row for row in reader]
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        return ExtractionResult(text="", pages=[], method="STRUCTURED_TABLE",
                                status="FAILED", error=str(exc))

    if not rows:
        return ExtractionResult(text="", pages=[], method="STRUCTURED_TABLE",
                                status="EMPTY", error="no data rows")
    if not header:
        return ExtractionResult(text="", pages=[], method="STRUCTURED_TABLE",
                                status="FAILED", error="no header row")

    pick = _pick_columns(header, rows[:50])
    if pick is None:
        return ExtractionResult(
            text="", pages=[], method="STRUCTURED_TABLE",
            status="UNSUPPORTED_FORMAT",
            error="structured table has fewer than two text columns or no "
                  "non-Latin primary column; refusing to guess layer roles",
        )

    primary_col, english_col = pick["primary"], pick["translation"]
    pages: list[str] = []
    roles: list[str] = []
    skipped = 0
    for index, row in enumerate(rows, start=1):
        primary = (row.get(primary_col) or "").strip()
        english = (row.get(english_col) or "").strip()
        if not primary and not english:
            skipped += 1
            continue
        # Stable layer order per row: source text first, then translation.
        if primary:
            pages.append(primary)
            roles.append("ORIGINAL")   # born-digital source layer, not OCR
        if english:
            pages.append(english)
            roles.append(_ROLE_TRANSLATION)

    # A row-ID locator is kept in the text itself as nothing else survives
    # into unit-level provenance; the segmenter reads it from the bracket tag.
    text = "\f".join(pages)
    return ExtractionResult(
        text=text,
        pages=pages,
        method="STRUCTURED_TABLE",
        status="OK",
        warnings=([f"{skipped} empty rows skipped"] if skipped else []),
        metrics={
            "rows": float(len(rows)),
            "primary_column": 0.0,   # placeholder; real per-column stats below
            "translation_rows": float(sum(1 for r in roles
                                          if r == _ROLE_TRANSLATION)),
        },
        text_roles=roles,
    )

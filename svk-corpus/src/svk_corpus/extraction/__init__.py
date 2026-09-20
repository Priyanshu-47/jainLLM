from __future__ import annotations

from pathlib import Path

from svk_corpus.extraction.base import ExtractionResult  # noqa: F401
from svk_corpus.extraction.epub import extract_epub  # noqa: F401
from svk_corpus.extraction.html import extract_hocr, extract_html  # noqa: F401
from svk_corpus.extraction.pdf import extract_pdf  # noqa: F401
from svk_corpus.extraction.plain_text import extract_plain_text  # noqa: F401


def extract_any(path: Path) -> ExtractionResult:
    """Dispatch on file extension. Unknown formats are reported, never guessed."""
    suffix = path.suffix.lower()
    if suffix in (".txt", ".text"):
        return extract_plain_text(path)
    if suffix == ".html":
        return extract_hocr(path)
    if suffix == ".epub":
        return extract_epub(path)
    if suffix == ".pdf":
        return extract_pdf(path)
    if suffix in (".jsonl", ".json"):
        return extract_plain_text(path)
    if suffix in (".csv", ".tsv"):
        # Structured data (e.g. the Deshika parallel corpus) must keep its two
        # text layers separate. A generic text dump would concatenate English
        # and Prakrit into one undifferentiated string - exactly the mixing
        # this project exists to prevent.
        from svk_corpus.extraction.structured import extract_structured_table
        return extract_structured_table(
            path, delimiter="\t" if suffix == ".tsv" else ",")
    if suffix == ".xml":
        return extract_plain_text(path)
    return ExtractionResult(
        text="", pages=[], method="NONE", status="UNSUPPORTED_FORMAT",
        error=f"no extractor registered for {suffix}",
    )

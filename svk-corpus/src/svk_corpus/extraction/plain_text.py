"""Plain-text extraction.

Archive.org's `DjVuTXT` derivative is the text layer produced by the source
repository's own OCR. It is treated as an INPUT, never as ground truth: the
quality stage measures it, and `human_verified` stays false.

Page splitting: DjVuTXT separates pages with a form-feed (U+000C). We preserve
that structure because page numbers are the backbone of citation locators.
"""

from __future__ import annotations

from pathlib import Path

from svk_corpus.extraction.base import ExtractionResult

_DEFAULT_ENCODINGS = ("utf-8-sig", "utf-8", "cp1252", "latin-1")


def decode_bytes(raw: bytes, encodings: tuple[str, ...] = _DEFAULT_ENCODINGS) -> tuple[str, str, int]:
    """Try encodings in order. Returns (text, encoding_used, decode_error_count)."""
    for encoding in encodings:
        try:
            return raw.decode(encoding), encoding, 0
        except UnicodeDecodeError:
            continue
    # Last resort: never raise on a corpus file. Record the damage instead.
    text = raw.decode("utf-8", errors="replace")
    errors = text.count("\ufffd")
    return text, "utf-8+replace", errors


def split_pages(text: str) -> list[str]:
    return text.split("\f")


def extract_plain_text(path: Path,
                       encoding_fallbacks: tuple[str, ...] | None = None
                       ) -> ExtractionResult:
    if not path.is_file():
        return ExtractionResult(text="", pages=[], method="PLAIN_TEXT",
                                status="FAILED", error="file not found")
    raw = path.read_bytes()
    if not raw:
        return ExtractionResult(text="", pages=[], method="PLAIN_TEXT",
                                status="EMPTY", error="zero-byte file")

    text, encoding, decode_errors = decode_bytes(
        raw, encoding_fallbacks or _DEFAULT_ENCODINGS)
    pages = split_pages(text)
    warnings: list[str] = []
    if decode_errors:
        warnings.append(f"{decode_errors} replacement characters after decoding as {encoding}")
    if len(pages) == 1 and len(text) > 200_000:
        warnings.append("no form-feed page separators found; page locators will be unavailable")

    stripped = text.strip()
    return ExtractionResult(
        text=text,
        pages=pages,
        method="PLAIN_TEXT",
        status="OK" if stripped else "EMPTY",
        warnings=warnings,
        metrics={
            "decode_errors": float(decode_errors),
            "pages": float(len(pages)),
            "characters": float(len(text)),
        },
    )

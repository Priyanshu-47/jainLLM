"""PDF text extraction.

PDF is the format where a stdlib-only pipeline is weakest, so this module is
written to fail HONESTLY rather than to guess:

  1. try the `pdftotext` binary (poppler) with `-layout -enc UTF-8`, reading from
     stdout so that no external file is created;
  2. else try an optional pure-Python backend if one happens to be installed;
  3. else return status UNAVAILABLE_NO_BACKEND with an explicit message.

A PDF whose text layer is empty yields status EMPTY, which the pipeline records
as "this artifact needs OCR", not as "this artifact has no content".
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from svk_corpus.extraction.base import ExtractionResult

_PDFTOTEXT_TIMEOUT = 180


def _try_pdftotext(path: Path) -> ExtractionResult | None:
    binary = shutil.which("pdftotext")
    if not binary:
        return None
    try:
        completed = subprocess.run(
            [binary, "-layout", "-enc", "UTF-8", str(path), "-"],
            capture_output=True, timeout=_PDFTOTEXT_TIMEOUT, check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return ExtractionResult(text="", pages=[], method="pdftotext",
                                status="FAILED", error=f"{type(exc).__name__}: {exc}")
    if completed.returncode != 0:
        return ExtractionResult(
            text="", pages=[], method="pdftotext", status="FAILED",
            error=f"pdftotext exit {completed.returncode}: "
                  f"{completed.stderr.decode('utf-8', 'replace')[:200]}")
    text = completed.stdout.decode("utf-8", errors="replace")
    pages = text.split("\f")
    return ExtractionResult(
        text=text, pages=pages, method=f"pdftotext[{Path(binary).name}]",
        status="OK" if text.strip() else "EMPTY",
        warnings=[] if text.strip() else ["PDF has an empty or absent text layer"],
        metrics={"pages": float(len(pages)), "characters": float(len(text))},
    )


def _try_python_backend(path: Path) -> ExtractionResult | None:
    try:  # pragma: no cover - depends on the environment
        import fitz  # PyMuPDF
    except ImportError:
        fitz = None
    if fitz is not None:
        try:  # pragma: no cover
            with fitz.open(path) as doc:
                pages = [page.get_text() for page in doc]
            text = "\n".join(pages)
            return ExtractionResult(text=text, pages=pages, method="pymupdf",
                                    status="OK" if text.strip() else "EMPTY",
                                    metrics={"pages": float(len(pages)),
                                             "characters": float(len(text))})
        except Exception as exc:  # pragma: no cover
            return ExtractionResult(text="", pages=[], method="pymupdf",
                                    status="FAILED", error=str(exc))
    try:  # pragma: no cover
        from pdfminer.high_level import extract_text as _pdfminer_extract
    except ImportError:
        return None
    try:  # pragma: no cover
        text = _pdfminer_extract(str(path)) or ""
        return ExtractionResult(text=text, pages=[text], method="pdfminer",
                                status="OK" if text.strip() else "EMPTY")
    except Exception as exc:  # pragma: no cover
        return ExtractionResult(text="", pages=[], method="pdfminer",
                                status="FAILED", error=str(exc))


def extract_pdf(path: Path) -> ExtractionResult:
    if not path.is_file():
        return ExtractionResult(text="", pages=[], method="PDF",
                                status="FAILED", error="file not found")
    for attempt in (_try_pdftotext, _try_python_backend):
        result = attempt(path)
        if result is not None:
            return result
    return ExtractionResult(
        text="", pages=[], method="PDF", status="UNAVAILABLE_NO_BACKEND",
        error="no PDF text backend available (pdftotext, PyMuPDF, pdfminer all missing); "
              "this artifact requires OCR in a later milestone",
    )

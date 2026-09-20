"""HTML / hOCR extraction.

hOCR is the most useful OCR derivative on Internet Archive, because it carries a
per-word confidence (`x_wconf`) and page structure. We use it to MEASURE the
quality of the repository's OCR rather than to trust it:

  * the mean `x_wconf` per page is recorded (where present)
  * words with very low confidence are counted

This gives the OCR quality report a real, source-attributable signal instead of
a guess, which matters given that archive.org's own script detection was
observed to be wrong on Gujarati material.
"""

from __future__ import annotations

import html as _html
import re
from html.parser import HTMLParser
from pathlib import Path

from svk_corpus.extraction.base import ExtractionResult

_WCONF_RE = re.compile(r"x_wconf\s+(-?\d+)")
_OCR_PAGE_RE = re.compile(r"class\s*=\s*[\"']?ocr_page")
_BLOCK_TAGS = {"p", "div", "br", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr"}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.in_page = False
        self.page_texts: list[str] = []
        self.page_confs: list[list[int]] = []
        self.concurrent: list[int] = []
        self._depth_pages = 0
        # Task 29: JainQQ wrappers embed <script>/<style> (dataLayer, gtag,
        # @font-face CSS). HTMLParser delivers their contents through
        # handle_data; without this guard the site's JavaScript ships as
        # "book text" (observed in SVK-2027). Script/style is never content.
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):  # noqa: D102
        attr = dict(attrs)
        classes = (attr.get("class") or "").split()
        if attr.get("id") == "page_1" or "ocr_page" in classes:
            if self.in_page:
                self._close_page()
            self.in_page = True
            self.concurrent = []
        if tag in ("script", "style"):
            self._skip_depth += 1
        if tag in _BLOCK_TAGS:
            self.parts.append("\n")
        if "x_wconf" in attr:
            try:
                self.concurrent.append(int(float(attr["x_wconf"])))
            except (TypeError, ValueError):
                pass

    def handle_endtag(self, tag):  # noqa: D102
        if tag in ("script", "style") and self._skip_depth:
            self._skip_depth -= 1
        if tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):  # noqa: D102
        if self._skip_depth:
            return
        if data.strip():
            self.parts.append(data)

    def _close_page(self) -> None:
        self.page_texts.append("".join(self.parts))
        self.page_confs.append(list(self.concurrent))
        self.parts = []
        self.concurrent = []

    def finish(self) -> None:
        if self.in_page:
            self._close_page()
        if not self.page_texts:
            self.page_texts = ["".join(self.parts)]


def extract_html(path: Path, method: str = "HTML_TEXT") -> ExtractionResult:
    if not path.is_file():
        return ExtractionResult(text="", pages=[], method=method,
                                status="FAILED", error="file not found")
    raw = path.read_text(encoding="utf-8", errors="replace")
    parser = _TextExtractor()
    parser.feed(raw)
    parser.finish()

    pages = [_html.unescape(p) for p in parser.page_texts]
    text = "\n".join(pages)
    confidences = [c for page in parser.page_confs for c in page]

    metrics: dict[str, float] = {}
    warnings: list[str] = []
    if confidences:
        metrics["ocr_mean_x_wconf"] = sum(confidences) / len(confidences)
        metrics["ocr_words"] = float(len(confidences))
        metrics["ocr_low_conf_words"] = float(sum(1 for c in confidences if c < 60))
    else:
        warnings.append("no x_wconf attributes found; OCR confidence unavailable")

    # hOCR also carries an explicit detected language/script in some exports.
    header = raw[:4000]
    detected = re.findall(r"x_ocr_(?:language|script)\s+([A-Za-z\-]+)", header)
    if detected:
        metrics["ocr_reported_script_tokens"] = float(len(detected))

    return ExtractionResult(
        text=text.strip("\n"),
        pages=pages,
        method=method,
        status="OK" if text.strip() else "EMPTY",
        warnings=warnings,
        metrics=metrics,
    )


def extract_hocr(path: Path) -> ExtractionResult:
    return extract_html(path, method="HOCR")

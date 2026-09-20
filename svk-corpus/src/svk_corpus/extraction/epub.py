"""EPUB extraction (stdlib only).

An EPUB is a ZIP containing XHTML documents plus an OPF package descriptor that
defines the reading order (the spine). We follow the spine so that the resulting
page/unit order matches the book, rather than the alphabetical order of the files
inside the archive — ordering errors are a common and silent corpus defect.
"""

from __future__ import annotations

import posixpath
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from svk_corpus.extraction.base import ExtractionResult
from svk_corpus.extraction.html import extract_html

_OPF_NS = {"opf": "http://www.idpf.org/2007/opf"}


def _spine_hrefs(zf: zipfile.ZipFile) -> tuple[list[str], str]:
    names = zf.namelist()
    opf_names = [n for n in names if n.lower().endswith(".opf")]
    if not opf_names:
        return [], ""
    opf_name = opf_names[0]
    root = ET.fromstring(zf.read(opf_name))
    base = posixpath.dirname(opf_name)

    manifest: dict[str, str] = {}
    for item in root.iter():
        if item.tag.endswith("}item") or item.tag == "item":
            item_id = item.attrib.get("id")
            href = item.attrib.get("href")
            if item_id and href:
                manifest[item_id] = posixpath.normpath(posixpath.join(base, href))

    hrefs: list[str] = []
    for ref in root.iter():
        if ref.tag.endswith("}itemref") or ref.tag == "itemref":
            idref = ref.attrib.get("idref")
            if idref in manifest:
                hrefs.append(manifest[idref])
    return hrefs, opf_name


def extract_epub(path: Path) -> ExtractionResult:
    if not path.is_file():
        return ExtractionResult(text="", pages=[], method="EPUB",
                                status="FAILED", error="file not found")
    try:
        with zipfile.ZipFile(path) as zf:
            hrefs, opf_name = _spine_hrefs(zf)
            if not hrefs:
                hrefs = sorted(n for n in zf.namelist()
                               if n.lower().endswith((".xhtml", ".html", ".htm")))
            pages: list[str] = []
            warnings: list[str] = []
            for href in hrefs:
                if href not in zf.namelist():
                    warnings.append(f"spine entry missing from archive: {href}")
                    continue
                member = zf.read(href)
                tmp = path.parent / f".__epub_member{Path(href).suffix or '.xhtml'}"
                tmp.write_bytes(member)
                try:
                    page = extract_html(tmp)
                finally:
                    tmp.unlink(missing_ok=True)
                body = re.sub(r"\n{3,}", "\n\n", page.text).strip()
                pages.append(body)
    except (zipfile.BadZipFile, ET.ParseError, KeyError) as exc:
        return ExtractionResult(text="", pages=[], method="EPUB", status="FAILED",
                                error=f"{type(exc).__name__}: {exc}")

    text = "\n\n".join(p for p in pages if p)
    return ExtractionResult(
        text=text, pages=pages, method="EPUB" if not opf_name else f"EPUB[{opf_name}]",
        status="OK" if text.strip() else "EMPTY",
        warnings=warnings,
        metrics={"pages": float(len(pages)), "characters": float(len(text))},
    )

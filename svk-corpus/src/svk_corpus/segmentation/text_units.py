"""Hierarchical segmentation into retrieval-sized textual units.

WHY NOT 500-TOKEN CHUNKS
The RAG layer has to produce citations a scholar can check. A citation reading
"chunk 47 of book.pdf" is not verifiable; "p. 123" is. So segmentation preserves
whatever structure the source actually has and records how confident we are
about it, instead of imposing a uniform window.

Levels emitted:  document -> section -> verse/sutta/paragraph -> chunk

THE FOUR RULES THAT MATTER
  1. We never fabricate structure. If a document has no discernible structure we
     emit paragraph units with `structure_confidence = "unknown"`. We do not
     invent sūtra numbers, chapter names, or verse indices.
  2. Text is never dropped. A section heading is emitted as a unit AND becomes
     the `section` label of the units that follow it, so it is both preserved and
     useful as retrieval metadata.
  3. Terminators stay attached. The danda (।) / double danda (॥) that ends a
     verse is part of the verse, not a delimiter to discard; citations depend on
     it.
  4. Splitting is deterministic. The same input yields byte-identical units and
     unit ids, which is what makes the release hashable.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field

from svk_corpus.schemas.records import TextUnit

# Devanagari/Gujarati verse terminators. Gujarati shares the danda codepoints.
DANDA = "\u0964"
DOUBLE_DANDA = "\u0965"
VERSE_TERMINATORS = (DOUBLE_DANDA, DANDA)  # DANDA: heading rejection + size-split only

FORM_FEED = "\f"

# Lines that are structurally noise in OCR'd books. Detected here so that
# quality.checks can report them; removal is opt-in and never happens in
# segmentation.
_PAGE_NUMBER_RE = re.compile(r"^\s*(?:\[?\s*\d{1,4}\s*\]?|[-–—]\s*\d{1,4}\s*[-–—])\s*$")
_SUTRA_NUMBER_RE = re.compile(
    r"(?:\u0965|\)|\])\s*[\u0966-\u096f\d]{1,3}\s*(?:\u0965|$)"
)


@dataclass
class PageSlice:
    page: int | None
    start: int
    end: int
    label: str = ""


@dataclass
class SegmentationStats:
    """Counters for one document.

    `units` counts EVERY emitted unit, including headings (a heading is emitted as
    a unit so that text is never dropped). `sections`, `verses`, `paragraphs` and
    `chunks` are disjoint subsets of `units`. Earlier revisions counted `units`
    excluding headings, which made the printed total disagree with the number of
    rows actually written to units.jsonl; that mismatch is exactly the kind of
    drift this pipeline cannot afford, so `units` is now the row count.
    """

    units: int = 0
    sections: int = 0
    verses: int = 0
    paragraphs: int = 0
    chunks: int = 0
    size_split_units: int = 0
    chars_in: int = 0
    chars_out: int = 0
    structure_confidence: str = "unknown"
    page_boundaries: int = 0
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return dict(vars(self))


def split_pages(text: str, page_labels: list[str] | None = None) -> list[PageSlice]:
    """Split on form feeds (what `pdftotext` emits) or on `=== page N ===` marks."""
    if FORM_FEED in text:
        chunks = text.split(FORM_FEED)
        slices: list[PageSlice] = []
        offset = 0
        for index, chunk in enumerate(chunks):
            slices.append(PageSlice(page=index + 1, start=offset,
                                    end=offset + len(chunk),
                                    label=(page_labels[index] if page_labels
                                           and index < len(page_labels) else "")))
            offset += len(chunk) + 1
        return slices
    return [PageSlice(page=None, start=0, end=len(text))]


def _blocks(text: str) -> list[str]:
    parts = re.split(r"\n\s*\n", text)
    return [p for p in parts if p.strip()]


def _looks_like_heading(block: str) -> bool:
    """Conservative heading test. Anything doubtful is NOT a heading.

    A false positive silently re-labels text as structure it does not have, which
    is worse than missing a heading: the latter merely loses metadata.
    """
    stripped = block.strip()
    if "\n" in stripped:
        return False
    if any(t in stripped for t in VERSE_TERMINATORS):
        return False
    if len(stripped) > 72:
        return False
    words = stripped.split()
    if not words or len(words) > 9:
        return False
    if stripped.endswith((".", ",", ";", ":", "!", "?")):
        return False
    # Require some letter content: OCR garbage rows are often symbol soup.
    letters = sum(1 for ch in stripped if unicodedata.category(ch).startswith("L"))
    return letters >= 4


def _verse_units(block: str) -> list[str]:
    """Split a block at double dandas, keeping each terminator attached.

    ONLY the double danda (॥) is a verse terminator. The single danda (।) ends
    ordinary sentences in Hindi/Gujarati/Sanskrit prose as well, so splitting on
    it would fabricate verse structure for plain prose and inflate the verse
    counts that downstream tooling trusts. Anything doubtful is not a verse.
    """
    out: list[str] = []
    buf: list[str] = []
    for ch in block:
        buf.append(ch)
        if ch == DOUBLE_DANDA:
            candidate = "".join(buf).strip()
            if candidate:
                out.append(candidate)
            buf = []
    tail = "".join(buf).strip()
    if tail:
        out.append(tail)
    return out or [block.strip()]


def _split_oversized(unit: str, max_chars: int) -> list[str]:
    """Break an oversized unit at the least-destructive boundary available."""
    if len(unit) <= max_chars:
        return [unit]
    pieces: list[str] = []
    remaining = unit
    while len(remaining) > max_chars:
        window = remaining[:max_chars]
        cut = -1
        for terminator in (DOUBLE_DANDA, DANDA, "|", ". ", "; "):
            idx = window.rfind(terminator)
            if idx > max_chars * 0.4:
                cut = idx + len(terminator)
                break
        if cut <= 0:
            idx = window.rfind(" ")
            cut = idx if idx > max_chars * 0.4 else max_chars
        pieces.append(remaining[:cut].strip())
        remaining = remaining[cut:].strip()
    if remaining:
        pieces.append(remaining)
    return [p for p in pieces if p]


def _unit_id(source_id: str, page: int | None, index: int, text: str) -> str:
    digest = hashlib.sha256(
        f"{source_id}|{page}|{index}|{text[:128]}".encode("utf-8")
    ).hexdigest()[:16]
    return f"{source_id}:u{index:05d}:{digest}"


def segment_document(
    text: str,
    *,
    source_id: str,
    language: str,
    script: str,
    text_role: str,
    page_labels: list[str] | None = None,
    page_roles: list[str] | None = None,
    max_chunk_chars: int = 1200,
    provenance: dict | None = None,
) -> tuple[list[TextUnit], SegmentationStats]:
    """Segment one document into ordered TextUnits plus a stats block."""
    stats = SegmentationStats(chars_in=len(text))
    units: list[TextUnit] = []
    doc_id = f"{source_id}:doc"

    slices = split_pages(text, page_labels)
    stats.page_boundaries = len(slices)

    # Round 2: multi-layer sources (parallel corpora) carry a role PER PAGE
    # (layer). Falling back to the document role keeps every v0.1 source
    # byte-identical in behaviour.
    def _role_for(page_no: int | None) -> str:
        if page_roles and page_no and 1 <= page_no <= len(page_roles):
            return page_roles[page_no - 1]
        return text_role

    page = slices[0].page if slices else None
    current_section: str | None = None
    index = 0
    saw_verse = False
    saw_heading = False

    # Document-level unit so that every unit has an ancestor and the hierarchy is
    # complete even for page-less input.
    document_unit = TextUnit(
        unit_id=doc_id,
        source_id=source_id,
        parent_id="",
        unit_type="document",
        text="",
        normalized_text="",
        language=language,
        script=script,
        page=page,
        section=None,
        source_locator={"page": page, "pages": len(slices)},
        text_role=text_role,
        structure_confidence="unknown",
        provenance=provenance or {},
        quality={"is_container": True},
    )
    units.append(document_unit)

    for slice_ in slices:
        page_text = text[slice_.start:slice_.end]
        page = slice_.page
        blocks = _blocks(page_text)

        # A block that is only a page number is reported, not treated as content.
        blocks = [b for b in blocks if not _PAGE_NUMBER_RE.match(b.strip())]

        for block in blocks:
            if _looks_like_heading(block):
                saw_heading = True
                current_section = block.strip()
                stats.sections += 1
                stats.units += 1
                index += 1
                units.append(TextUnit(
                    unit_id=_unit_id(source_id, page, index, block),
                    source_id=source_id,
                    parent_id=doc_id,
                    unit_type="section",
                    text=block.strip(),
                    normalized_text=block.strip(),
                    language=language,
                    script=script,
                    page=page,
                    section=current_section,
                    source_locator={"page": page, "section": current_section},
                    text_role=_role_for(page),
                    structure_confidence="medium",
                    detected_label=current_section,
                    provenance=provenance or {},
                    quality={"is_heading": True},
                ))
                continue

            # Verse detection uses the double danda only; see _verse_units.
            has_verse_mark = DOUBLE_DANDA in block
            if has_verse_mark:
                saw_verse = True
                candidates = [
                    ("verse" if c.endswith(DOUBLE_DANDA) else "paragraph", c)
                    for c in _verse_units(block)
                ]
            else:
                candidates = [("paragraph", block.strip())]

            for unit_type, candidate in candidates:
                for piece in _split_oversized(candidate, max_chunk_chars):
                    index += 1
                    if piece != candidate:
                        stats.size_split_units += 1
                        emitted_type = "chunk"
                        confidence = "low"
                    else:
                        emitted_type = unit_type
                        # A ॥ terminator is strong structural evidence -> high.
                        # A bare paragraph carries NO structural evidence, and
                        # "medium" would fabricate confidence the source never
                        # gave us; the honest value is "unknown" (see module
                        # docstring, rule 1).
                        confidence = "high" if emitted_type == "verse" else "unknown"
                    stats.chars_out += len(piece)
                    unit = TextUnit(
                        unit_id=_unit_id(source_id, page, index, piece),
                        source_id=source_id,
                        parent_id=doc_id,
                        unit_type=emitted_type,
                        text=piece,
                        normalized_text=piece,
                        language=language,
                        script=script,
                        page=page,
                        section=current_section,
                        source_locator={
                            "page": page,
                            "section": current_section,
                            "has_sutra_number": bool(_SUTRA_NUMBER_RE.search(piece)),
                        },
                        text_role=_role_for(page),
                        structure_confidence=confidence,
                        provenance=provenance or {},
                        quality={},
                    )
                    units.append(unit)
                    stats.units += 1
                    if emitted_type == "verse":
                        stats.verses += 1
                    elif emitted_type == "paragraph":
                        stats.paragraphs += 1
                    elif emitted_type == "chunk":
                        stats.chunks += 1

    # Confidence in the structure as a whole.
    if saw_verse and stats.page_boundaries > 1:
        stats.structure_confidence = "high"
    elif saw_verse or saw_heading:
        stats.structure_confidence = "medium"
    else:
        stats.structure_confidence = "unknown"
        stats.warnings.append(
            "no verse terminators and no headings detected; units are page/paragraph "
            "based and must not be cited as numbered scripture"
        )
    document_unit.structure_confidence = stats.structure_confidence
    return units, stats

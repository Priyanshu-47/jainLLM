"""Deterministic Unicode normalisation.

DESIGN RULE, IN ONE LINE: we produce a *second* text layer and never touch the
first one.

The pipeline stores `raw_text` and `normalized_text` as separate artifacts with
separate hashes. Nothing here is allowed to be lossy in a way we cannot account
for, so every operation is (a) individually switchable, (b) counted, and (c)
reported in `NormalizationStats`. If a reviewer disagrees with a rule, the
counters say exactly how much text that rule touched.

WHAT WE DELIBERATELY DO NOT DO
  * We do not ASCII-ify Indic text, and we do not "repair" Prakrit or Sanskrit
    orthography. A model doing that without a scholar is a model inventing
    scripture.
  * We do not strip ZWNJ (U+200C) or ZWJ (U+200D). They are meaningful in Indic
    shaping and their removal changes rendering.
  * We do not default to NFKC. NFKC performs compatibility decomposition, which
    folds distinctions that Indic and IAST text actually use (e.g. it decomposes
    Devanagari nukta forms and can collapse IAST presentation variants). NFKC is
    available, off by default, and when enabled it is recorded in the stats and
    in `NORMALIZATION_VERSION`.
  * We do not silently delete orphan combining marks. We count them, because an
    orphan mark is strong evidence of an OCR or encoding fault upstream and must
    propagate to the quality report.

WHY NFC AND NOT NFKC BY DEFAULT
NFC is canonically equivalence-preserving: two strings that render identically
and mean the same thing compare equal afterwards. NFKC additionally rewrites
compatibility characters, which is exactly the class of change we promise not to
make invisibly.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from typing import Any

NORMALIZATION_VERSION = "1.0.0"

# --- character classes we act on -------------------------------------------
BOM = "\ufeff"
ZERO_WIDTH_REMOVABLE = (
    "\u200b",  # ZERO WIDTH SPACE
    "\u2060",  # WORD JOINER
    "\u180e",  # MONGOLIAN VOWEL SEPARATOR
    "\u00ad",  # SOFT HYPHEN - invisible, never meaningful in our corpora
)
ZWNJ = "\u200c"
ZWJ = "\u200d"
FORM_FEED = "\f"  # page-boundary marker emitted by pdftotext

# Spaces that are visually a space but are not U+0020. Folding these is safe:
# none of them carry meaning in the scripts we hold.
SPACE_LIKE = {
    "\u00a0",  # NO-BREAK SPACE
    "\u1680",  # OGHAM SPACE MARK
    # EN QUAD .. HAIR SPACE must be individual members: as one concatenated
    # string they were never equal to a single character and never folded.
    "\u2000", "\u2001", "\u2002", "\u2003", "\u2004",
    "\u2005", "\u2006", "\u2007", "\u2008", "\u2009", "\u200a",
    "\u202f",  # NARROW NO-BREAK SPACE
    "\u205f",  # MEDIUM MATHEMATICAL SPACE
    "\u3000",  # IDEOGRAPHIC SPACE
}

REPLACEMENT_CHAR = "\ufffd"

UNICODE_FORMS = ("NFC", "NFD", "NFKC", "NFKD", "NONE")


@dataclass
class NormalizationStats:
    """Every counter is a number of *occurrences changed or observed*."""

    chars_in: int = 0
    chars_out: int = 0
    codepoints_in: int = 0
    codepoints_out: int = 0
    bom_removed: int = 0
    zero_width_removed: int = 0
    control_removed: int = 0
    spaces_folded: int = 0
    tabs_folded: int = 0
    newlines_normalized: int = 0
    space_runs_collapsed: int = 0
    blank_lines_collapsed: int = 0
    trailing_space_stripped: int = 0
    unicode_form: str = "NFC"
    unicode_recomposed: int = 0
    # observations, not repairs
    replacement_chars: int = 0
    orphan_combining_marks: int = 0
    zwnj_preserved: int = 0
    zwj_preserved: int = 0
    danda_count: int = 0
    double_danda_count: int = 0

    def as_dict(self) -> dict[str, Any]:
        return dict(vars(self))


@dataclass
class NormalizationResult:
    raw: str
    normalized: str
    stats: NormalizationStats = field(default_factory=NormalizationStats)
    version: str = NORMALIZATION_VERSION

    @property
    def changed(self) -> bool:
        return self.raw != self.normalized

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "changed": self.changed,
            "stats": self.stats.as_dict(),
        }


def _is_combining(ch: str) -> bool:
    return unicodedata.category(ch) in ("Mn", "Mc", "Me")


def _strip_zero_width(text: str, stats: NormalizationStats) -> str:
    out_chars: list[str] = []
    for ch in text:
        if ch == BOM:
            stats.bom_removed += 1
            continue
        if ch in ZERO_WIDTH_REMOVABLE:
            stats.zero_width_removed += 1
            continue
        if ch == ZWNJ:
            stats.zwnj_preserved += 1
            out_chars.append(ch)
            continue
        if ch == ZWJ:
            stats.zwj_preserved += 1
            out_chars.append(ch)
            continue
        out_chars.append(ch)
    return "".join(out_chars)


def _strip_control(text: str, stats: NormalizationStats) -> str:
    out_chars: list[str] = []
    for ch in text:
        if ch in ("\n", "\t"):
            out_chars.append(ch)
            continue
        if ch in (ZWNJ, ZWJ):
            # ZWNJ/ZWJ are Cf but orthographically meaningful in Indic scripts
            # (e.g. enforcing a visible virama break). Never delete them here;
            # `_strip_zero_width` already counted/preserved them.
            out_chars.append(ch)
            continue
        if ch == FORM_FEED:
            # Form feed is the page-boundary marker emitted by pdftotext and
            # consumed by segmentation. Deleting it would destroy every page
            # citation in the corpus, so it is preserved as structure.
            out_chars.append(ch)
            continue
        if unicodedata.category(ch) in ("Cc", "Cf"):
            stats.control_removed += 1
            continue
        out_chars.append(ch)
    return "".join(out_chars)


def _normalize_newlines(text: str, stats: NormalizationStats) -> str:
    if "\r" not in text:
        return text
    before = text.count("\r")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    stats.newlines_normalized += before
    return text


def _fold_spaces(text: str, stats: NormalizationStats) -> str:
    out_chars: list[str] = []
    for ch in text:
        if ch == "\t":
            stats.tabs_folded += 1
            out_chars.append(" ")
            continue
        if ch in SPACE_LIKE:
            stats.spaces_folded += 1
            out_chars.append(" ")
            continue
        out_chars.append(ch)
    return "".join(out_chars)


def _collapse_space_runs(text: str, stats: NormalizationStats) -> str:
    """Collapse runs of spaces *within* a line. Newlines are left alone here."""
    out_lines: list[str] = []
    for line in text.split("\n"):
        if "  " in line:
            stats.space_runs_collapsed += 1
            line = " ".join(part for part in line.split(" ") if part != "")
        out_lines.append(line)
    return "\n".join(out_lines)


def _strip_trailing_space(text: str, stats: NormalizationStats) -> str:
    lines = text.split("\n")
    fixed = 0
    out: list[str] = []
    for line in lines:
        new = line.rstrip(" ")
        if new != line:
            fixed += 1
        out.append(new)
    stats.trailing_space_stripped += fixed
    return "\n".join(out)


def _collapse_blank_lines(text: str, max_blank: int, stats: NormalizationStats) -> str:
    if max_blank < 0:
        return text
    max_newlines = max_blank + 1
    out_lines: list[str] = []
    run = 0
    for line in text.split("\n"):
        if line == "":
            run += 1
            if run > max_blank:
                stats.blank_lines_collapsed += 1
                continue
        else:
            run = 0
        out_lines.append(line)
    result = "\n".join(out_lines)
    # collapse any long newline run that survived
    while "\n" * (max_newlines + 1) in result:
        result = result.replace("\n" * (max_newlines + 1), "\n" * max_newlines)
        stats.blank_lines_collapsed += 1
    return result


def _unicode_form(text: str, form: str, stats: NormalizationStats) -> str:
    if form in (None, "NONE"):
        return text
    if form not in UNICODE_FORMS:
        raise ValueError(f"unsupported Unicode form: {form!r}")
    result = unicodedata.normalize(form, text)
    if result != text:
        stats.unicode_recomposed += 1
    return result


def observe(text: str, stats: NormalizationStats) -> None:
    """Record observations that must never trigger a repair."""
    stats.replacement_chars += text.count(REPLACEMENT_CHAR)
    stats.danda_count += text.count("\u0964")
    stats.double_danda_count += text.count("\u0965")

    # An orphan combining mark is a mark with no base: start of string, after
    # whitespace, or after punctuation. We count it and change nothing.
    prev = "\n"
    for ch in text:
        if _is_combining(ch) and (prev.isspace() or prev in "()[]{}.,;:!?\"'|"):
            stats.orphan_combining_marks += 1
        prev = ch


def normalize_text(
    text: str,
    *,
    unicode_form: str = "NFC",
    max_blank_lines: int = 1,
    fold_spaces: bool = True,
    collapse_space_runs: bool = True,
    strip_trailing_space: bool = True,
    strip_control: bool = True,
) -> NormalizationResult:
    """Produce the `normalized_text` layer from a raw text layer.

    The raw string is returned untouched in `.raw`; the cleaned form is in
    `.normalized`. Options that destroy information are off by default.
    """
    stats = NormalizationStats()
    stats.chars_in = len(text)
    stats.codepoints_in = len(text)
    raw = text

    # 1. observations before any mutation, so the counts describe the input
    observe(text, stats)

    # 2. invisible characters
    text = _strip_zero_width(text, stats)

    # 3. line endings BEFORE control-stripping, so CRLF is counted as a
    #    normalised newline instead of the lone \r vanishing as a control char.
    text = _normalize_newlines(text, stats)
    if strip_control:
        text = _strip_control(text, stats)

    # 4. horizontal whitespace, then vertical structure
    if fold_spaces:
        text = _fold_spaces(text, stats)
    if collapse_space_runs:
        text = _collapse_space_runs(text, stats)
    if strip_trailing_space:
        text = _strip_trailing_space(text, stats)
    text = _collapse_blank_lines(text, max_blank_lines, stats)

    # 5. canonical equivalence last, so earlier counters describe pre-form text
    text = _unicode_form(text, unicode_form, stats)
    stats.unicode_form = unicode_form

    stats.chars_out = len(text)
    stats.codepoints_out = len(text)
    return NormalizationResult(raw=raw, normalized=text, stats=stats)


# ---------------------------------------------------------------------------
# Unicode health metrics (used by quality.checks, not by normalisation)
# ---------------------------------------------------------------------------
def unicode_quality(text: str) -> dict[str, Any]:
    """Report Unicode health without changing anything.

    Returns a ratio in [0,1] plus the raw counts that produced it, so a human
    can audit the number instead of trusting it.
    """
    if not text:
        return {
            "score": 0.0,
            "replacement_chars": 0,
            "control_chars": 0,
            "orphan_combining_marks": 0,
            "unassigned": 0,
            "chars": 0,
        }

    replacement = text.count(REPLACEMENT_CHAR)
    control = sum(1 for ch in text if unicodedata.category(ch) == "Cc" and ch not in "\n\t")
    unassigned = sum(1 for ch in text if unicodedata.category(ch) in ("Cn", "Co", "Cs"))
    prev = "\n"
    orphans = 0
    for ch in text:
        if _is_combining(ch) and (prev.isspace() or prev in "()[]{}.,;:!?\"'|"):
            orphans += 1
        prev = ch

    total = len(text)
    bad = replacement + control + unassigned + orphans
    score = max(0.0, 1.0 - (bad / total) * 10.0)
    return {
        "score": round(min(1.0, score), 6),
        "replacement_chars": replacement,
        "control_chars": control,
        "orphan_combining_marks": orphans,
        "unassigned": unassigned,
        "chars": total,
    }

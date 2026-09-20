"""Quality checks that report their evidence.

NO SINGLE OPAQUE SCORE
The milestone requires individual metrics rather than one number, and that is the
right call for a scripture corpus: a text can be perfectly clean Unicode and
complete metadata while being OCR garbage, and a single score would average those
into a meaningless middle. So `assess_text` returns named metrics plus the raw
counts behind each one, and `aggregate` keeps them separate.

THE RECALL-FIRST RULE FOR SACRED TEXT
Every detector here is built to over-report rather than to delete. Nothing in this
module removes text. Emptiness, repetition and header/footer detection all produce
*flags*; the only component that may drop anything is the opt-in header/footer
stripper, which writes what it removed to a sidecar file so the removal is
reversible and auditable.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

from svk_corpus.normalization.unicode import REPLACEMENT_CHAR, unicode_quality

# Characters that legitimately appear in Indic religious text and must never be
# counted as "symbol noise".
_MEANINGFUL_SYMBOLS = frozenset("\u0964\u0965\u0950\u0ad0|\u0966\u0967\u0968\u0969"
                                "\u096a\u096b\u096c\u096d\u096e\u096f\u0ae6\u0ae7"
                                "\u0ae8\u0ae9\u0aea\u0aeb\u0aec\u0aed\u0aee\u0aef")

_PAGE_NUMBER_RE = re.compile(r"^\s*(?:\[?\s*[ivxlcdmIVXLCDM\d]{1,6}\s*\]?|[-–—]\s*\d{1,4}\s*[-–—])\s*$")
_LONG_TOKEN_RE = re.compile(r"\S{60,}")
_REPEATED_CHAR_RE = re.compile(r"(\S)\1{5,}")


@dataclass
class TextQuality:
    chars: int = 0
    words: int = 0
    lines: int = 0
    empty_ratio: float = 0.0
    replacement_ratio: float = 0.0
    symbol_ratio: float = 0.0
    digit_ratio: float = 0.0
    max_repeat_run: int = 0
    max_letter_repeat_run: int = 0
    repeated_run_count: int = 0
    long_token_count: int = 0
    orphan_mark_ratio: float = 0.0
    expected_script_ratio: float = 0.0
    # Intra-word script mixing. This is the metric that catches the corpus's most
    # serious defect: see `_script_confusion` for the worked case.
    mixed_word_ratio: float = 0.0
    foreign_inside_ratio: float = 0.0
    words_examined: int = 0
    line_repetition_ratio: float = 0.0
    unicode_quality: float = 0.0
    ocr_noise_estimate: float = 0.0
    structural_quality: float = 0.0
    flags: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return dict(vars(self))


def _script_expectation(language: str, script: str) -> str | None:
    """Which script should dominate, given the declared language and script?"""
    if script in ("Devanagari", "Gujarati", "Bengali", "Gurmukhi"):
        return script
    if script in ("IAST", "Roman", "Latin"):
        return "Latin"
    return None


def _in_script(ch: str, script: str) -> bool:
    cp = ord(ch)
    if script == "Devanagari":
        return 0x0900 <= cp <= 0x097F or 0xA8E0 <= cp <= 0xA8FF or 0x1CD0 <= cp <= 0x1CFF
    if script == "Gujarati":
        return 0x0A80 <= cp <= 0x0AFF
    if script == "Bengali":
        return 0x0980 <= cp <= 0x09FF
    if script == "Gurmukhi":
        return 0x0A00 <= cp <= 0x0A7F
    if script == "Arabic":
        # Round 2: DLI scans of Sindhi/Urdu-region Jain-community material can
        # surface Perso-Arabic script; the block check lets _script_expectation
        # route it instead of reporting it as unclassifiable noise.
        return 0x0600 <= cp <= 0x06FF or 0x0750 <= cp <= 0x077F or 0xFB50 <= cp <= 0xFDFF
    if script == "Latin":
        return cp < 0x0250 or 0x1E00 <= cp <= 0x1EFF
    return False


def assess_text(text: str, *, language: str = "unknown", script: str = "unknown",
                structural_quality: float = 0.0) -> TextQuality:
    """Measure one unit. Never mutates, never deletes."""
    q = TextQuality(chars=len(text))
    if not text:
        q.flags.append("EMPTY")
        q.ocr_noise_estimate = 1.0
        return q

    words = text.split()
    q.words = len(words)
    lines = [ln for ln in text.split("\n") if ln.strip()]
    q.lines = len(lines)

    uq = unicode_quality(text)
    q.unicode_quality = uq["score"]
    q.replacement_ratio = uq["replacement_chars"] / q.chars
    q.orphan_mark_ratio = uq["orphan_combining_marks"] / q.chars

    symbols = digits = letters = 0
    for ch in text:
        cat = unicodedata.category(ch)
        if cat[0] == "N":
            digits += 1
            continue
        if cat[0] == "L":
            letters += 1
            continue
        if cat.startswith("P") or cat.startswith("S"):
            if ch in _MEANINGFUL_SYMBOLS or cat == "Po":
                continue
            symbols += 1
    substantive = max(1, q.chars)
    q.symbol_ratio = symbols / substantive
    q.digit_ratio = digits / substantive

    max_run = 0
    max_letter_run = 0
    run = 1
    prev = ""
    for ch in text:
        if ch == prev and not ch.isspace():
            run += 1
            max_run = max(max_run, run)
            if ch.isalpha() or unicodedata.category(ch).startswith("M"):
                max_letter_run = max(max_letter_run, run)
        else:
            run = 1
        prev = ch
    q.max_repeat_run = max_run
    q.max_letter_repeat_run = max_letter_run
    q.repeated_run_count = len(_REPEATED_CHAR_RE.findall(text))
    q.long_token_count = len(_LONG_TOKEN_RE.findall(text))

    expectation = _script_expectation(language, script)
    if expectation:
        in_script = sum(1 for ch in text if _in_script(ch, expectation))
        q.expected_script_ratio = in_script / substantive

    q.mixed_word_ratio, q.foreign_inside_ratio, q.words_examined = _script_confusion(
        text, script)

    # Repeated lines: a header/footer repeated on every page shows up here.
    if lines:
        counter = Counter(ln.strip() for ln in lines)
        repeated = sum(count for ln, count in counter.items() if count > 1 and ln)
        q.line_repetition_ratio = repeated / len(lines)

    q.empty_ratio = 1.0 - (letters / substantive)
    q.ocr_noise_estimate = _ocr_noise(q, language, script)
    q.structural_quality = structural_quality

    # --- flags -------------------------------------------------------------
    if q.chars < 24:
        q.flags.append("VERY_SHORT")
    if q.replacement_ratio > 0:
        q.flags.append("REPLACEMENT_CHARS")
    if q.replacement_ratio > 0.002:
        q.flags.append("REPLACEMENT_CHARS_HIGH")
    if q.orphan_mark_ratio > 0.01:
        q.flags.append("ORPHAN_COMBINING_MARKS")
    if q.symbol_ratio > 0.25:
        q.flags.append("HIGH_SYMBOL_RATIO")
    if q.digit_ratio > 0.30:
        q.flags.append("HIGH_DIGIT_RATIO")
    # Task 29: only ALPHABETIC/COMBINING runs indicate genuine OCR corruption
    # ('kkkkk...'). JainQQ sources carry page furniture — long '-----' and
    # '____' separator rules — which is layout, not language. Flag that
    # separately as LOW_VALUE_LAYOUT so the distinction is visible without
    # downgrading otherwise-valid text. Historical sources (SVK-2015/2020) also
    # contain '------' page rules, so the letter-only threshold must not move.
    if q.max_letter_repeat_run > 12:
        q.flags.append("REPEATED_CHARACTER_RUN")
    if q.max_repeat_run > 12 and q.max_letter_repeat_run <= 12:
        q.flags.append("LOW_VALUE_LAYOUT")
    if q.long_token_count > 2:
        q.flags.append("SUSPICIOUS_LONG_TOKENS")
    if q.line_repetition_ratio > 0.30 and q.lines > 6:
        q.flags.append("REPEATED_LINES")
    # Task 29: an HTML/boilerplate unit (JainQQ page furniture, CSS) is an
    # extraction fault, not a script mismatch — it needs its own signal so it
    # can be reviewed without equating it with genuine mixed-script editions.
    # SVK-2025/2029 are legitimately mixed Romanized-Prakrit + Devanagari
    # editions; their units must NOT be flagged merely for mixing scripts.
    if _looks_like_web_boilerplate(text):
        q.flags.append("WEB_BOILERPLATE")
    elif expectation and q.expected_script_ratio < 0.35:
        q.flags.append("SCRIPT_MISMATCH")
    if q.ocr_noise_estimate > 0.55:
        q.flags.append("OCR_NOISE_HIGH")
    if q.foreign_inside_ratio > SCRIPT_CONFUSION_THRESHOLD and q.words_examined >= 5:
        q.flags.append("SCRIPT_CONFUSION")
    return q


# Calibrated against this corpus, where clean Devanagari OCR scores 0.03 and
# Gujarati-read-as-Devanagari OCR scores 0.14. Kept deliberately low, because the
# cost of diverting a slightly noisy unit to review is far lower than the cost of
# training on unreadable text labelled as scripture.
SCRIPT_CONFUSION_THRESHOLD = 0.08


# Task 29: JainQQ 'booktext' pages embed the site's own HTML head (dataLayer,
# gtag, @font-face, base64 CSS) when the wrapper is not fully stripped. That is
# an EXTRACTION fault with a very reliable signature, distinct from the
# language question of whether Romanized Indic text is English.
_WEB_BOILERPLATE_RE = re.compile(
    r"dataLayer|gtag\(|@font-face|window\.|font-family|src:url|<script|</style>",
    re.IGNORECASE,
)


def _looks_like_web_boilerplate(text: str) -> bool:
    """True when a unit is dominated by web page machinery, not content."""
    hits = len(_WEB_BOILERPLATE_RE.findall(text))
    return hits >= 3


def _script_confusion(text: str, script: str) -> tuple[float, float, int]:
    """Detect OCR script confusion by measuring mixing INSIDE words.

    THE WORKED CASE THIS EXISTS FOR
    Internet Archive item in.ernet.dli.2015 (SVK-0007) is a Gujarati-script Jain
    dictionary. Archive.org's OCR engine read the Gujarati glyphs and emitted
    DEVANAGARI codepoints, producing text such as::

        '< श्रा.सिद्योगिए् देवे सदावेद् "” जीवा २, रोव ४१, नाका० =, 5४, रायन २८'
        '01191708, 1008.7148.10108 €{6 विवा'

    Measured over the whole document this reads as '96% Devanagari at 100%
    purity', because the output really is Devanagari codepoints. Unicode-quality
    scoring gives it 0.995, symbol ratio 0.055, and the OCR noise estimate 0.10:
    every whole-document metric passes it. The text is nonetheless unreadable, and
    a model trained on it would learn to emit garbage fragments labelled as
    Prakrit scripture.

    What does separate it is *lexical* evidence. In readable Indic prose a word
    contains no Latin digits, no stray brackets and no quotation marks inside it:
    'सव्वं' and 'णमोक्कारो' are internally pure. In the confused output, a third of
    all words contain foreign codepoints.

    Measured on this corpus:
        SVK-0007 (Gujarati book read as Devanagari)  mixed_words 0.32, foreign 0.14
        SVK-0037 (same class of item)                mixed_words 0.36, foreign 0.15
        SVK-0016 (cleanly OCR'd Hindi agam)          mixed_words 0.10, foreign 0.03
        English / French sources                     not applicable

    HONEST LIMITS. This measures script mixing, not readability. A scholarly
    dictionary legitimately contains Latin abbreviations and numerals, so a high
    score is a triage signal for human review, never a verdict that text is
    corrupt. It is therefore reported as a flag that diverts a unit out of the
    training corpus rather than deleting the unit.
    """
    expectation = "Devanagari" if script == "Devanagari" else (
        "Gujarati" if script == "Gujarati" else (
            "Bengali" if script == "Bengali" else None))
    if expectation is None:
        return 0.0, 0.0, 0

    words = text.split()
    if not words:
        return 0.0, 0.0, 0

    mixed = 0
    foreign = 0
    total = 0
    for word in words:
        total += len(word)
        if not any(_in_script(ch, expectation) for ch in word):
            continue
        offenders = [ch for ch in word
                     if not _in_script(ch, expectation)
                     and not unicodedata.category(ch).startswith("M")]
        if offenders:
            mixed += 1
            foreign += len(offenders)
    return (mixed / len(words), foreign / max(1, total), len(words))


def _ocr_noise(q: TextQuality, language: str, script: str) -> float:
    """A transparent, weighted heuristic. Documented so it can be argued with.

    Weights are deliberately simple and reported alongside the inputs; this is a
    triage signal for human review, not a claim about any specific text.
    """
    score = 0.0
    score += min(1.0, q.replacement_ratio * 100) * 0.30
    # Weights sum to 1.20 once the script-confusion term is included, so the score
    # is clipped at 1.0. The excess is intentional: severe script confusion should
    # saturate the estimate rather than being diluted by the other terms.
    score += min(1.0, q.symbol_ratio / 0.35) * 0.25
    score += min(1.0, q.foreign_inside_ratio / 0.15) * 0.20
    score += min(1.0, q.orphan_mark_ratio / 0.03) * 0.15
    score += min(1.0, max(0, q.max_repeat_run - 6) / 20) * 0.15
    if q.expected_script_ratio:
        score += max(0.0, 0.6 - q.expected_script_ratio) / 0.6 * 0.15
    if q.chars < 40:
        score += 0.10
    return round(min(1.0, score), 6)


# ---------------------------------------------------------------------------
# Document-level checks
# ---------------------------------------------------------------------------
@dataclass
class RepeatedLine:
    text: str
    count: int
    share: float
    kind: str            # HEADER | FOOTER | PAGE_NUMBER | UNKNOWN

    def as_dict(self) -> dict[str, Any]:
        return {"text": self.text[:120], "count": self.count,
                "share": round(self.share, 4), "kind": self.kind}


def detect_running_headers(pages: Sequence[str], threshold: float = 0.30,
                           max_len: int = 90) -> list[RepeatedLine]:
    """Find lines that recur across pages: running heads, footers, page numbers.

    Reported, never applied. `strip_running_headers` is the opt-in application.
    """
    if len(pages) < 3:
        return []
    first_lines: Counter[str] = Counter()
    last_lines: Counter[str] = Counter()
    for page in pages:
        lines = [ln.strip() for ln in page.split("\n") if ln.strip()]
        if not lines:
            continue
        first_lines[lines[0]] += 1
        last_lines[lines[-1]] += 1

    found: list[RepeatedLine] = []
    for counter, kind in ((first_lines, "HEADER"), (last_lines, "FOOTER")):
        for line, count in counter.most_common():
            if not line or len(line) > max_len:
                continue
            share = count / len(pages)
            if share < threshold:
                continue
            line_kind = kind
            if _PAGE_NUMBER_RE.match(line):
                line_kind = "PAGE_NUMBER"
            found.append(RepeatedLine(text=line, count=count, share=share,
                                      kind=line_kind))
    # Same line as both header and footer is a single observation.
    deduped: dict[str, RepeatedLine] = {}
    for item in found:
        existing = deduped.get(item.text)
        if existing is None or item.count > existing.count:
            deduped[item.text] = item
    return sorted(deduped.values(), key=lambda r: -r.count)


def strip_running_headers(pages: Sequence[str], repeats: Sequence[RepeatedLine],
                          *, include_page_numbers: bool = True) -> tuple[list[str], dict]:
    """Remove detected headers/footers, returning what was removed.

    Only ever called explicitly. The return value is written next to the release
    so that every removed line can be inspected and the operation reversed.
    """
    targets = {r.text for r in repeats
               if r.kind != "PAGE_NUMBER" or include_page_numbers}
    removed: Counter[str] = Counter()
    out: list[str] = []
    for page in pages:
        lines = page.split("\n")
        kept: list[str] = []
        for index, line in enumerate(lines):
            stripped = line.strip()
            is_edge = index == 0 or index == len(lines) - 1
            if is_edge and stripped in targets:
                removed[stripped] += 1
                continue
            if include_page_numbers and _PAGE_NUMBER_RE.match(stripped) and stripped:
                removed[stripped] += 1
                continue
            kept.append(line)
        out.append("\n".join(kept))
    return out, {
        "removed_line_occurrences": sum(removed.values()),
        "distinct_removed_lines": len(removed),
        "removed_samples": [{"text": t[:120], "count": c}
                            for t, c in removed.most_common(20)],
        "note": "sidecar only; the raw extraction is never modified in place",
    }


# ---------------------------------------------------------------------------
# Metadata and provenance completeness
# ---------------------------------------------------------------------------
CORE_METADATA_FIELDS = (
    "source_id", "title", "author", "publisher", "publication_year",
    "tradition", "sect", "language", "script", "repository", "license",
    "license_evidence_url", "copyright_basis",
)
PROVENANCE_FIELDS = (
    "source_url", "artifact_sha256", "repository", "identifier",
    "license_evidence_url", "acquisition_timestamp",
)

_UNKNOWN_VALUES = {"", "unknown", "n/a", "none", "unverified", "null", "unmeasured"}


def metadata_completeness(row: dict[str, Any],
                          fields: Iterable[str] = CORE_METADATA_FIELDS) -> float:
    present = 0
    considered = 0
    for name in fields:
        considered += 1
        value = row.get(name)
        if value is None:
            continue
        if isinstance(value, str) and value.strip().lower() in _UNKNOWN_VALUES:
            continue
        if isinstance(value, (list, dict)) and not value:
            continue
        present += 1
    return round(present / considered, 4) if considered else 0.0


def provenance_completeness(record: dict[str, Any]) -> float:
    prov = record.get("provenance") or {}
    if not isinstance(prov, dict):
        return 0.0
    return metadata_completeness(prov, PROVENANCE_FIELDS)


# ---------------------------------------------------------------------------
# Aggregate
# ---------------------------------------------------------------------------
def aggregate(qualities: Sequence[TextQuality]) -> dict[str, Any]:
    if not qualities:
        return {"units": 0}
    n = len(qualities)
    flags: Counter[str] = Counter()
    for q in qualities:
        for flag in q.flags:
            flags[flag] += 1
    return {
        "units": n,
        "mean_unicode_quality": round(sum(q.unicode_quality for q in qualities) / n, 6),
        "mean_ocr_noise_estimate": round(sum(q.ocr_noise_estimate for q in qualities) / n, 6),
        "mean_structural_quality": round(sum(q.structural_quality for q in qualities) / n, 6),
        "mean_symbol_ratio": round(sum(q.symbol_ratio for q in qualities) / n, 6),
        "mean_foreign_inside_ratio": round(
            sum(q.foreign_inside_ratio for q in qualities) / n, 6),
        "mean_mixed_word_ratio": round(
            sum(q.mixed_word_ratio for q in qualities) / n, 6),
        "mean_line_repetition_ratio": round(
            sum(q.line_repetition_ratio for q in qualities) / n, 6),
        "units_with_flags": sum(1 for q in qualities if q.flags),
        "flag_counts": dict(flags.most_common()),
        "chars": sum(q.chars for q in qualities),
        "words": sum(q.words for q in qualities),
    }

"""Script and language evidence for Indic text.

THE PRINCIPLE THIS MODULE ENFORCES
  Gujarati script does not mean the Gujarati language.
  Devanagari script does not mean Hindi.

Devanagari in our corpora is genuinely ambiguous between Hindi, Sanskrit and
Jain Prakrit (and Rajasthani, Marathi, Nepali...). A blanket classifier that
answers "Hindi" for a Devanagari page would corrupt exactly the metadata that
makes this corpus worth building, so this module:

  * reports script from Unicode ranges, deterministically;
  * reports language only as a *hint*, with a method and a confidence, and
    returns "unknown" when the evidence does not separate the candidates;
  * never overwrites curated metadata. Anything derived here lands in a
    separate field (`detected_language`) so it can be compared against — rather
    than substituted for — the catalogue's own claim.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Script ranges
# ---------------------------------------------------------------------------
# Ordered most-specific-first: Vedic Extensions and Devanagari Extended must be
# tested before the base Devanagari block would otherwise be irrelevant, and
# Latin Extended Additional must be distinguished from plain Latin because it
# carries the IAST diacritics we care about.
SCRIPT_RANGES: tuple[tuple[str, int, int], ...] = (
    ("Devanagari Extended", 0xA8E0, 0xA8FF),
    ("Vedic Extensions", 0x1CD0, 0x1CFF),
    ("Devanagari", 0x0900, 0x097F),
    ("Gujarati", 0x0A80, 0x0AFF),
    ("Bengali", 0x0980, 0x09FF),
    ("Gurmukhi", 0x0A00, 0x0A7F),
    ("Tamil", 0x0B80, 0x0BFF),
    ("Telugu", 0x0C00, 0x0C7F),
    ("Kannada", 0x0C80, 0x0CFF),
    ("Malayalam", 0x0D00, 0x0D7F),
    ("Oriya", 0x0B00, 0x0B7F),
    ("Sinhala", 0x0D80, 0x0DFF),
    ("Tibetan", 0x0F00, 0x0FFF),
    ("Arabic", 0x0600, 0x06FF),
    ("Greek", 0x0370, 0x03FF),
    ("Cyrillic", 0x0400, 0x04FF),
    ("Hebrew", 0x0590, 0x05FF),
    ("Latin Extended Additional", 0x1E00, 0x1EFF),
    ("Latin Extended", 0x00C0, 0x024F),
    ("Latin", 0x0020, 0x007F),
)

# Scripts that are plausibly ours vs. scripts whose presence means upstream noise.
INDIC_SCRIPTS = frozenset({
    "Devanagari", "Devanagari Extended", "Vedic Extensions",
    "Gujarati", "Bengali", "Gurmukhi",
})
LATIN_SCRIPTS = frozenset({"Latin", "Latin Extended", "Latin Extended Additional"})
UNEXPECTED_SCRIPTS = frozenset({
    "Cyrillic", "Greek", "Hebrew", "Arabic", "Tibetan",
    "Telugu", "Kannada", "Malayalam", "Oriya", "Sinhala", "Tamil",
})

# Scripts whose text we can confidently hand to a Devanagari-based tokenizer.
DEVANAGARI_COMPATIBLE = frozenset({"Devanagari", "Devanagari Extended", "Vedic Extensions"})

# IAST codepoints (the Latin Extended Additional block covers most of them).
IAST_CHARS = frozenset("āīūṛṝḷḹṃḥṅñṭḍṇśṣḻṉṟêôạẓḍṛ")


def script_of_char(ch: str) -> str:
    """Return the script name for one character, or 'Common'/'Other'."""
    cp = ord(ch)
    for name, lo, hi in SCRIPT_RANGES:
        if lo <= cp <= hi:
            # ASCII printable + control live inside the Latin range; separate them.
            if name == "Latin" and (cp < 0x41):
                return "Common"
            return name
    cat = unicodedata.category(ch)
    if cat in ("Zs", "Zl", "Zp", "Cc", "Cf"):
        return "Common"
    if cat.startswith("P") or cat.startswith("N"):
        return "Common"
    if cat in ("Mn", "Mc", "Me"):
        return "Inherited"
    return "Other"


def script_profile(text: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for ch in text:
        counts[script_of_char(ch)] += 1
    return dict(counts.most_common())


@dataclass
class ScriptEvidence:
    script: str
    purity: float
    distribution: dict[str, int]
    ambiguous: bool = False
    note: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "script": self.script,
            "purity": round(self.purity, 4),
            "distribution": self.distribution,
            "ambiguous": self.ambiguous,
            "note": self.note,
        }


def detect_script(text: str, min_chars: int = 20) -> ScriptEvidence:
    """Detect the dominant script from Unicode ranges.

    `Common`/`Inherited` characters (spaces, digits, punctuation, combining
    marks) are excluded from the denominator: a Devanagari page that is 40%
    spaces must not be reported as script-ambiguous because of the spaces.
    """
    dist = script_profile(text)
    substantive = {k: v for k, v in dist.items() if k not in ("Common", "Inherited")}
    total = sum(substantive.values())
    if total < min_chars:
        return ScriptEvidence(
            script="unknown", purity=0.0, distribution=dist,
            ambiguous=True,
            note=f"fewer than {min_chars} substantive characters",
        )

    ordered = sorted(substantive.items(), key=lambda kv: (-kv[1], kv[0]))
    top_script, top_count = ordered[0]
    purity = top_count / total

    # Devanagari + Vedic/Extended is one writing system, not a mixture.
    if top_script in ("Devanagari Extended", "Vedic Extensions"):
        merged = sum(v for k, v in substantive.items() if k in DEVANAGARI_COMPATIBLE)
        top_script = "Devanagari"
        purity = merged / total

    second = ordered[1][1] / total if len(ordered) > 1 else 0.0
    ambiguous = purity < 0.90
    note = ""
    if ambiguous:
        runner_up = ordered[1][0] if len(ordered) > 1 else "n/a"
        note = (
            f"mixed script: {top_script} {purity:.1%}, {runner_up} {second:.1%}"
        )
        if any(s in UNEXPECTED_SCRIPTS for s in substantive):
            note += " (contains a script outside this project's scope — likely OCR fault)"
    return ScriptEvidence(
        script=top_script, purity=purity, distribution=dist,
        ambiguous=ambiguous, note=note,
    )


# ---------------------------------------------------------------------------
# Language hints
# ---------------------------------------------------------------------------
# Marker sets. These are *evidence of form*, not proof of language: Jain
# Prakrit and Sanskrit share enormous vocabulary and both use Devanagari, so the
# best outcome here is often "ambiguous", which is reported honestly.
MARKERS: dict[str, tuple[str, ...]] = {
    "hi": ("है", "हैं", "और", "में", "नहीं", "यह", "वह", "कि ", "था", "होता",
           "करने", "लिए", "साथ", "हुआ", "जाता"),
    "gu": ("છે", "અને", "માં", "ની", "તે", "કે", "હતું", "શ્રી", "માટે",
           "તથા", "જૈન", "એક", "આ ", "તેમજ"),
    "sa": ("श्री", "इति", "एव", "भवति", "अस्ति", "तथा", "यथा", "च ", "स्य",
           "ानां", "न च", "उक्तं", "तत्र", "क्ष", "ज्ञ"),
    "pra": ("णं", "तं ", "सव्व", "जाव", "हवइ", "भवइ", "अत्थि", "णत्थि",
            "से ", "तेसिं", "एस ", "समण", "सुत्त", "अंग", "पंच", "चउ",
            "जइ", "जं ", "तम्हा", "वि ", "पुण"),
    "en": (" the ", " and ", " of ", " is ", " which ", " with ", " this ",
           " that ", " for ", " from "),
}

# Task 29: Romanized Indic text is written in the LATIN script but is NOT
# English. Romanization of Prakrit/Hindi uses long-vowel macrons and letters
# English never uses (A/I/U with macron, ~n for anusvaara, .h for visarga,
# 3 for Middle Indic r/l, etc.). English function-word density alone cannot
# separate 'the' from an English word inside a Hindi translation; a strong
# diacritic/transliteration signal CAN separate Romanized Indic from English.
_ROMANIZED_INDIC_RE = re.compile(
    r"[AaIiUu][\u0304]|"            # vowel + combining macron (AA, II, UU)
    r"\b[AaIiUuRrLlMmHh][\u0304]\b|"  # standalone macron vowels (a, i, u...)
    r"[\u0303]|"                    # combining tilde (~n anusvaara)
    r"\b[nN][~\u0303]|"            # ~n / n-tilde
    r"\b[a-zA-Z]{1,3}3[a-zA-Z]|"    # 3 for Middle-Indic r/l (phar3a)
    r"\b[a-zA-Z]+\.[hH]\b"          # visarga as .h (dukkkr|.h)
)
# High-frequency romanized Hindi/Prakrit function words (IAST-style schemes).
_ROMANIZED_INDIC_MARKERS = (
    "sUtra", "sutra", "namaH", "nama", "karem", "karemi", "savva", "savvaM",
    "jJAna", "adhyAtma", "sAdhaka", "Avazyaka", "Avashyaka", "pratikramaN",
    "pratikraman", "sAmAyika", "samayik", "kAyotsarga", "kayotsarga",
    "pratyAkhyAna", "vandana", "zramaNa", "shraman", "ArAdhanA", "sadhu",
    "bhagavan", "jinendra", "moksha", "karma", "atma", "dharma",
)


def romanized_indic_evidence(text: str) -> dict[str, Any]:
    """Measure how strongly a Latin-script text looks like ROMANIZED INDIC.

    Task 29 honesty rule: this is a conservative signal, not a classifier.
    Returns evidence the caller must weigh; it never relabels text as a
    specific Indic language, because romanization schemes do not distinguish
    Prakrit from Hindi from Sanskrit reliably.
    """
    if not text:
        return {"hits": 0, "marker_hits": 0, "indication": "none"}
    diacritic_hits = len(_ROMANIZED_INDIC_RE.findall(text))
    lowered = text.lower()
    marker_hits = sum(lowered.count(m.lower()) for m in _ROMANIZED_INDIC_MARKERS)
    words = max(1, len(text.split()))
    # 1 diacritic per 40 words or 1 marker per 25 words is already strong:
    # English prose has neither macron vowels nor 'sUtra'/'namaH' patterns.
    strong = diacritic_hits * 3 >= words or marker_hits * 2 >= words
    some = diacritic_hits + marker_hits >= 2
    indication = ("strong" if strong else ("some" if some else "none"))
    return {
        "diacritic_hits": diacritic_hits,
        "marker_hits": marker_hits,
        "words": words,
        "indication": indication,
    }

LANGUAGE_DISPLAY = {
    "hi": "Hindi",
    "gu": "Gujarati",
    "sa": "Sanskrit",
    "pra": "Prakrit",
    "en": "English",
    "unknown": "unknown",
}


@dataclass
class LanguageHint:
    language: str
    confidence: str  # high | medium | low | unknown
    method: str
    evidence: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "language": self.language,
            "confidence": self.confidence,
            "method": self.method,
            "evidence": self.evidence,
        }


def script_implied_language(script: str) -> str | None:
    """Scripts in our scope whose correspondence to a language is near-total."""
    return {
        "Gujarati": "gu",
        "Bengali": "bn",
        "Gurmukhi": "pa",
    }.get(script)


def detect_language_hint(text: str, script: str | None = None) -> LanguageHint:
    """Deterministic lexical-marker language hint.

    Confidence is capped at `medium` on purpose. A marker count is not a
    classifier, and pretending otherwise would let an automated guess overwrite
    a catalogue's curated `language` field downstream.
    """
    # Short units (a single verse) must still get a script reading, so the
    # min_chars gate that suits whole documents is relaxed here.
    script_ev = detect_script(text, min_chars=4) if script is None else None
    effective_script = script or (script_ev.script if script_ev else "unknown")
    lowered = text.lower()

    scores: dict[str, int] = {}
    for lang, needles in MARKERS.items():
        hits = sum(lowered.count(n.lower()) for n in needles)
        if hits:
            scores[lang] = hits

    # Gujarati script with Gujarati markers is the one case we can be firm about,
    # and only because the script narrows the field to essentially one language.
    implied = script_implied_language(effective_script)
    if implied:
        if implied in scores:
            return LanguageHint(
                implied, "medium", "script+markers",
                {"script": effective_script, "marker_hits": scores},
            )
        return LanguageHint(
            implied, "low", "script-implied",
            {"script": effective_script, "marker_hits": scores,
             "note": "script narrows the language but few markers were found"},
        )

    if not scores:
        # Task 29: a Latin-script text with zero English function-word hits is
        # very unlikely to be English — but that absence alone does not make it
        # a *specific* Indic language. Check the romanization signal first.
        if effective_script in ("Latin", "Roman", "IAST"):
            ev = romanized_indic_evidence(text)
            if ev["indication"] in ("strong", "some"):
                return LanguageHint(
                    "unknown", "low", "romanized-indic-signal",
                    {"script": effective_script, **ev,
                     "note": "Latin script with Indic romanization markers; "
                             "NOT confidently English. Curated language value "
                             "required (Prakrit/Hindi/Sanskrit in Latin script)."},
                )
        return LanguageHint(
            "unknown", "unknown", "no-evidence",
            {"script": effective_script},
        )

    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    best, best_hits = ranked[0]
    runner_up, runner_hits = (ranked[1] if len(ranked) > 1 else ("", 0))

    # Devanagari best-cases are genuinely close (pra/sa/hi); do not separate them
    # on a handful of hits.
    if effective_script == "Devanagari":
        close = [lang for lang, hits in ranked if hits >= max(2, best_hits * 0.6)]
        if len(close) > 1:
            return LanguageHint(
                "unknown", "unknown", "ambiguous-devanagari",
                {"script": effective_script, "marker_hits": scores,
                 "candidates": sorted(close),
                 "note": "Devanagari does not separate Hindi, Sanskrit and Prakrit "
                         "reliably; a curated value is required"},
            )

    confidence = "medium" if best_hits >= 8 and best_hits >= 2 * max(1, runner_hits) else "low"
    # Task 29: Romanized Indic text often contains a few English words (Hindi
    # translations use English loanwords; bilingual headings say 'ILLUSTRATED
    # AAVASHYAK SUTRA'). When the romanization signal is strong and the English
    # lead is not overwhelming, refuse the English label rather than mislabel.
    if best == "en" and effective_script in ("Latin", "Roman", "IAST"):
        ev = romanized_indic_evidence(text)
        if ev["indication"] == "strong" and not (
                best_hits >= 8 and best_hits >= 4 * max(1, runner_hits)):
            return LanguageHint(
                "unknown", "low", "romanized-indic-over-english",
                {"script": effective_script, "marker_hits": scores, **ev,
                 "note": "Latin script with strong Indic romanization markers; "
                         "English function words present but not dominant. "
                         "Curated language value required."},
            )
    return LanguageHint(
        best, confidence, "markers",
        {"script": effective_script, "marker_hits": scores,
         "runner_up": runner_up, "runner_up_hits": runner_hits},
    )


def language_script_consistency(declared_language: str, script: str) -> list[str]:
    """Flag implausible catalogue claims. Never auto-corrects them."""
    problems: list[str] = []
    lang = (declared_language or "").strip().lower()
    if not lang or lang in ("unknown", "mixed", "multiple"):
        return problems
    if script == "unknown":
        return problems

    if lang.startswith("gu") and script == "Devanagari":
        problems.append(
            "declared Gujarati but dominant script is Devanagari "
            "(possible transliterated edition, or a mislabelled scan)"
        )
    if lang.startswith(("hi", "sa", "pra", "ardha")) and script == "Gujarati":
        problems.append(
            f"declared {lang} but dominant script is Gujarati "
            "(common for Gujarati-script editions of Sanskrit/Prakrit text)"
        )
    if lang.startswith("en") and script in INDIC_SCRIPTS:
        problems.append("declared English but dominant script is Indic")
    if lang.startswith("en") and script not in LATIN_SCRIPTS and script not in ("Common", "Inherited"):
        problems.append(f"declared English but dominant script is {script}")
    if script in UNEXPECTED_SCRIPTS:
        problems.append(
            f"dominant script {script} is outside this project's scope — "
            "treat as an OCR or file-selection fault"
        )
    return problems

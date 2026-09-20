"""Normalisation layers.

Public surface:
    normalize_text          -> raw + normalized layer, with counters
    unicode_quality         -> Unicode health metrics
    detect_script           -> script evidence from Unicode ranges
    detect_language_hint    -> lexical-marker language hint (never authoritative)
    language_script_consistency
    transliterate           -> Devanagari <-> IAST, Gujarati -> Devanagari
    NORMALIZATION_VERSION
"""

from svk_corpus.normalization.indic import (
    LanguageHint,
    ScriptEvidence,
    detect_language_hint,
    detect_script,
    language_script_consistency,
    script_implied_language,
    script_of_char,
    script_profile,
)
from svk_corpus.normalization.transliteration import (
    SUPPORTED_PAIRS,
    TransliterationResult,
    devanagari_to_iast,
    gujarati_to_devanagari,
    iast_to_devanagari,
    transliterate,
)
from svk_corpus.normalization.unicode import (
    NORMALIZATION_VERSION,
    NormalizationResult,
    NormalizationStats,
    normalize_text,
    unicode_quality,
)

__all__ = [
    "NORMALIZATION_VERSION",
    "NormalizationResult",
    "NormalizationStats",
    "normalize_text",
    "unicode_quality",
    "LanguageHint",
    "ScriptEvidence",
    "detect_language_hint",
    "detect_script",
    "language_script_consistency",
    "script_implied_language",
    "script_of_char",
    "script_profile",
    "SUPPORTED_PAIRS",
    "TransliterationResult",
    "devanagari_to_iast",
    "gujarati_to_devanagari",
    "iast_to_devanagari",
    "transliterate",
]

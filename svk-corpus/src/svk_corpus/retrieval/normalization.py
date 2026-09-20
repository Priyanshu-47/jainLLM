"""Deterministic romanization folding + alias expansion for retrieval.

Scope (Task 9)
--------------
Task 8's dominant failure mode was romanization variance: queries using one
period/standard spelling miss units using another ("Sutrakritanga" vs
"Sutrakrtanga", "Uttaradhyayana" vs "Utradhyayan", "Ratnachandra" vs
"Ratnachandraji"). This module fixes that at the RETRIEVAL LAYER ONLY, with
three hard guarantees:

1.  DETERMINISTIC. Pure functions over the config file; no randomness, no
    model, no fuzzy matching, no stemming. Two runs on the same input produce
    identical output.
2.  NON-DESTRUCTIVE. Folding and aliasing touch only the searchable token
    stream built by the BM25 index and the query string. Corpus files are
    never rewritten; every returned result exposes the ORIGINAL unit text and
    the full provenance record.
3.  EVIDENCE-BOUNDED. The alias table (`configs/retrieval_aliases_v1.json`)
    contains only variants justified by corpus text, Task 8 evaluation
    queries, or manifest metadata. An entry maps SPELLINGS, not doctrines:
    orthographic equivalence never implies religious, textual, or canonical
    equivalence between works or traditions.

Two mechanisms, both derived from the config:

*   Single-token aliases: an OR-expansion at the token level
    ("sutrakritanga" -> {sutrakritanga, sutrakrtanga}). Original term first,
    so relative term weights stay interpretable. Task 10 adds Gujarati
    spelling-variant groups (e.g. ધરમ <-> ધર્મ) under the same mechanism.
*   Multi-token phrase rules: a contiguous token SEQUENCE ("ratna chandra ji",
    "જૈન ધર્મ") additionally injects the fused canonical term
    ("ratnachandraji", "જૈનધર્મ") into the stream — which also lets a
    compound query reach spaced-form docs and vice versa, in BOTH directions,
    while the parts themselves are NEVER added as alias keys or index terms.

Design note — why fold+expand instead of edit-distance/fuzzy matching:
fuzzy matching merges distinct Prakrit/Sanskrit terms that happen to sound
alike (exactly the "aggressive normalization" the project forbids), while a
closed, evidence-cited alias set can be reviewed line by line. Folding is a
fixed one-directional character map (no ambiguity); aliasing is an explicit
OR over listed variants (no merge of unrelated terms).
"""

from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

# ---------------------------------------------------------------------------
# Tokenization (shared with the BM25 layer)
# ---------------------------------------------------------------------------

# A token starts with a letter/digit and continues with word characters OR
# Indic combining signs (matras/viramas/anusvara, categories Mn/Mc, plus the
# Indic script blocks' sign ranges). The old pattern `\w+` silently DROPPED
# every combining mark: જૈન -> ['જ','ન'], ધર્મ -> ['ધર','મ'] (virama split the
# word) — mangling all Indic text and even falsely merging જિન and જૈન into
# identical fragments (Task 10 finding). A combining sign can never START a
# token (first class excludes it), so this stays deterministic and safe.
_TOKEN_RE = re.compile(r"[^\W_][\w\u0900-\u0DFF]*", re.UNICODE)


def tokenize(text: str) -> list[str]:
    """Lowercased Unicode word tokens; digits kept (years/dictionary refs).

    Text is NFC-normalized FIRST so that canonically-equivalent Unicode forms
    (precomposed vs decomposed diacritics) tokenize identically — otherwise a
    decomposed Latin diacritic breaks the token mid-word. Indic-script words
    stay intact under NFC: matras (ા ૈ િ ...), viramas (્) and anusvara (ં ं)
    are combining marks attached to their base consonant and survive into the
    token. Latin tokens are unaffected.
    """
    text = unicodedata.normalize("NFC", text)
    return _TOKEN_RE.findall(text.lower())


# ---------------------------------------------------------------------------
# Folding
# ---------------------------------------------------------------------------

# One-directional Latin diacritic folding (diacritic -> ASCII). Deliberately
# unconditional on Latin tokens: every mapped codepoint is unambiguously a
# romanization diacritic, so the fold is idempotent and cannot loop.
_FOLD_MAP: dict[str, str] = {
    "ā": "a", "ī": "i", "ū": "u", "ē": "e", "ō": "o",
    "ṛ": "ri", "ṝ": "ri", "ḷ": "l", "ḹ": "l",
    "ṅ": "n", "ñ": "n", "ṇ": "n",
    "ṭ": "t", "ḍ": "d",
    "ś": "sh", "ṣ": "sh",
    "ṃ": "n", "ḥ": "",
}

_FOLD_TRANS = str.maketrans(_FOLD_MAP)

# Script ranges: tokens containing ANY Indic codepoint are passed through
# untouched (no cross-script transliteration in this task).
_INDIC_RANGES = (
    (0x0900, 0x097F),   # Devanagari
    (0x0A80, 0x0AFF),   # Gujarati
    (0x0A00, 0x0A7F),   # Gurmukhi (defensive)
    (0x0980, 0x09FF),   # Bengali (defensive)
)


def _is_indic(token: str) -> bool:
    return any(lo <= ord(ch) <= hi for ch in token for lo, hi in _INDIC_RANGES)


def fold_token(token: str) -> str:
    """Fold one token: Latin diacritics -> ASCII; Indic-script tokens pass through.

    Deterministic and idempotent: fold(fold(t)) == fold(t).
    """
    if _is_indic(token):
        return token
    return token.translate(_FOLD_TRANS)


# ---------------------------------------------------------------------------
# Alias table (loaded from the versioned config)
# ---------------------------------------------------------------------------

# single folded token -> tuple of additional search tokens.
_ALIASES: dict[str, tuple[str, ...]] = {}
# (parts..., canonical) phrase rules, in config order (deterministic).
_PHRASE_RULES: list[tuple[tuple[str, ...], str]] = []


def load_aliases(config_path: Path) -> None:
    """(Re)load the alias/phrase tables from a config JSON.

    Called at import time with the default config; tests may call it with a
    dedicated fixture config. Idempotent and deterministic.
    """
    global _ALIASES, _PHRASE_RULES
    data = json.loads(config_path.read_text(encoding="utf-8"))
    singles: dict[str, list[str]] = {}
    phrase: list[tuple[tuple[str, ...], str]] = []
    for group in data.get("alias_groups", []):
        canonical = fold_token(group["canonical_key"])
        variants: list[str] = [canonical]
        group_phrases: list[tuple[tuple[str, ...], str]] = []
        for raw in group.get("expansions", []):
            folded_parts = [fold_token(p) for p in raw.split()]
            if len(folded_parts) > 1:
                # Multi-token variant -> phrase rule. The parts are used ONLY
                # to detect the sequence; they never become alias keys NOR
                # extras of any key UNLESS the group explicitly sets
                # "parts_as_search_terms" (justified when the parts are real
                # attested standalone words, e.g. Gujarati જૈન + ધર્મ — and
                # forbidden when they are meaningless fragments, e.g. "ji").
                group_phrases.append((tuple(folded_parts), canonical))
            elif folded_parts and folded_parts[0]:
                variants.append(folded_parts[0])
        variants = list(dict.fromkeys(variants))          # deterministic dedup
        if group.get("parts_as_search_terms"):
            part_pool: list[str] = []
            for parts, _ in group_phrases:
                for p in parts:
                    if p not in part_pool:
                        part_pool.append(p)
        else:
            part_pool = []
        for key in variants:                              # keys: single tokens ONLY
            merged = list(singles.get(key, []))
            for extra in variants:
                if extra != key and extra not in merged:
                    merged.append(extra)
            for p in part_pool:                           # compound -> its parts
                if p != key and p not in merged and p not in variants:
                    merged.append(p)
            singles[key] = merged
        phrase.extend(group_phrases)
    _ALIASES = {k: tuple(v) for k, v in singles.items()}
    _PHRASE_RULES = phrase


_DEFAULT_CONFIG = Path(__file__).resolve().parents[3] / "configs" / "retrieval_aliases_v1.json"
if _DEFAULT_CONFIG.exists():
    load_aliases(_DEFAULT_CONFIG)


def expand_token(token: str) -> tuple[str, ...]:
    """Return the folded token plus its evidenced single-token alias variants.

    The token itself is always first, so original-term matches keep their
    weight. Aliases are OR-expanded at search time only — never merged into
    one canonical form, so relative term frequencies stay interpretable.
    """
    folded = fold_token(token)
    if not folded:
        return ()
    extras = _ALIASES.get(folded, ())
    return (folded,) + tuple(e for e in extras if e != folded)


def expand_query_text(text: str) -> list[str]:
    """Full deterministic expansion of a text/query into index/query terms.

    Order of operations (both BM25 sides use exactly this function):
      1. tokenize (lowercased word tokens; Indic matras/viramas preserved)
      2. fold each token (Indic-script tokens pass through)
      3. phrase rules: a contiguous sequence matching a multi-token variant
         additionally injects the fused canonical term after the span — in
         queries AND in index text, so compound<->spaced variants meet in
         both directions
      4. single-token alias OR-expansion

    Deterministic: fixed rule order, first-match-wins, stable dedup.
    """
    tokens = [fold_token(t) for t in tokenize(text)]
    out: list[str] = []
    i = 0
    while i < len(tokens):
        matched = False
        for parts, canonical in _PHRASE_RULES:
            n = len(parts)
            if n and tokens[i:i + n] == list(parts):
                for t in tokens[i:i + n]:
                    out.extend(expand_token(t))
                out.append(canonical)
                i += n
                matched = True
                break
        if not matched:
            out.extend(expand_token(tokens[i]))
            i += 1
    return out


@lru_cache(maxsize=1)
def alias_count() -> int:
    """Number of single-token alias keys loaded (for tests/reporting)."""
    return len(_ALIASES)


@lru_cache(maxsize=1)
def phrase_rule_count() -> int:
    """Number of multi-token phrase rules loaded (for tests/reporting)."""
    return len(_PHRASE_RULES)

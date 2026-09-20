"""Transliteration between the scripts our corpus actually uses.

WHY THIS MODULE EXISTS
The research phase found no embedding model with credible Prakrit coverage, and
Prakrit reaches us in at least three encodings: Gujarati script, Devanagari
script, and Roman/IAST. Retrieval cannot match ``णमोकारो`` against ``namokkāro``
or ``નમોક્કારો`` without an explicit mapping, so transliteration is a first-class
component of the corpus, not a display convenience.

DESIGN RULES
  1. Lossy in, reported out. Every function returns the unmapped codepoints it
     saw, with counts. We never drop a character silently.
  2. The source string is never mutated in place; callers store the
     transliteration as a NEW layer with its own hash and its own role
     (TRANSCRIPTION), so it can never be mistaken for the original.
  3. Devanagari <-> IAST is implemented as a state machine, not a dictionary
     substitution, because the inherent vowel ('a') is implicit in the Indic
     scripts and explicit in IAST. A naive char map produces "krishna" instead
     of "kṛṣṇa" and destroys every Prakrit citation it touches.
  4. Gujarati -> Devanagari is offset-based because the two blocks are laid out
     in parallel (U+0A80 block - 0x180 == the corresponding U+0900 codepoint for
     essentially the whole shared repertoire). Exceptions are listed explicitly
     and tested.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Devanagari codepoints
# ---------------------------------------------------------------------------
VIRAMA = 0x094D
NUKTA = 0x093C
ANUSVARA = 0x0902
CANDRABINDU = 0x0901
VISARGA = 0x0903
OM = 0x0950
DANDA = 0x0964
DOUBLE_DANDA = 0x0965

DEV_INDEPENDENT_VOWELS: dict[int, str] = {
    0x0905: "a", 0x0906: "ā", 0x0907: "i", 0x0908: "ī",
    0x0909: "u", 0x090A: "ū", 0x090B: "ṛ", 0x0960: "ṝ",
    0x090C: "ḷ", 0x0961: "ḹ", 0x090D: "ê", 0x090E: "e",
    0x090F: "e", 0x0910: "ai", 0x0911: "ô", 0x0912: "o",
    0x0913: "o", 0x0914: "au",
}

DEV_CONSONANTS: dict[int, str] = {
    0x0915: "k", 0x0916: "kh", 0x0917: "g", 0x0918: "gh", 0x0919: "ṅ",
    0x091A: "c", 0x091B: "ch", 0x091C: "j", 0x091D: "jh", 0x091E: "ñ",
    0x091F: "ṭ", 0x0920: "ṭh", 0x0921: "ḍ", 0x0922: "ḍh", 0x0923: "ṇ",
    0x0924: "t", 0x0925: "th", 0x0926: "d", 0x0927: "dh", 0x0928: "n",
    0x0929: "ṉ", 0x092A: "p", 0x092B: "ph", 0x092C: "b", 0x092D: "bh",
    0x092E: "m", 0x092F: "y", 0x0930: "r", 0x0931: "ṟ", 0x0932: "l",
    0x0933: "ḷ", 0x0934: "ḻ", 0x0935: "v", 0x0936: "ś", 0x0937: "ṣ",
    0x0938: "s", 0x0939: "h",
    # nukta forms
    0x0958: "q", 0x0959: "kha", 0x095A: "ġ", 0x095B: "z",
    0x095C: "ṛ", 0x095D: "ṛh", 0x095E: "f", 0x095F: "ẏ",
}

DEV_MATRAS: dict[int, str] = {
    0x093E: "ā", 0x093F: "i", 0x0940: "ī", 0x0941: "u", 0x0942: "ū",
    0x0943: "ṛ", 0x0944: "ṝ", 0x0945: "ê", 0x0946: "e", 0x0947: "e",
    0x0948: "ai", 0x0949: "ô", 0x094A: "o", 0x094B: "o", 0x094C: "au",
    0x0962: "ḷ", 0x0963: "ḹ",
}

DEV_SIGNS: dict[int, str] = {
    CANDRABINDU: "m̐",
    ANUSVARA: "ṃ",
    VISARGA: "ḥ",
    OM: "oṃ",
    DANDA: "|",
    DOUBLE_DANDA: "||",
    0x0970: "°",
}

DEV_DIGITS: dict[int, str] = {0x0966 + i: str(i) for i in range(10)}

# chars we knowingly drop, with the reason recorded by the caller
DEV_TRANSPARENT = {NUKTA, 0x094E, 0x094F, 0x0951, 0x0952, 0x0953, 0x0954, 0x0971}


# ---------------------------------------------------------------------------
# result type
# ---------------------------------------------------------------------------
@dataclass
class TransliterationResult:
    text: str
    source_script: str
    target_script: str
    unmapped: dict[str, int] = field(default_factory=dict)
    transparent_dropped: dict[str, int] = field(default_factory=dict)
    case_folded: int = 0

    @property
    def lossy(self) -> bool:
        return bool(self.unmapped)

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_script": self.source_script,
            "target_script": self.target_script,
            "lossy": self.lossy,
            "unmapped": self.unmapped,
            "transparent_dropped": self.transparent_dropped,
            "case_folded": self.case_folded,
            "chars_out": len(self.text),
        }


# ---------------------------------------------------------------------------
# Devanagari -> IAST
# ---------------------------------------------------------------------------
def devanagari_to_iast(text: str) -> TransliterationResult:
    """Devanagari (or Devanagari-encoded Prakrit) to IAST.

    The state machine matters: क is "ka", क् is "k", कि is "ki". A per-character
    map cannot express that, and getting it wrong silently corrupts every
    transliterated citation the corpus produces.
    """
    out: list[str] = []
    unmapped: dict[str, int] = {}
    dropped: dict[str, int] = {}
    i = 0
    n = len(text)

    while i < n:
        ch = text[i]
        cp = ord(ch)

        if cp in DEV_CONSONANTS:
            base = DEV_CONSONANTS[cp]
            nxt = text[i + 1] if i + 1 < n else ""
            ncp = ord(nxt) if nxt else -1
            if ncp == VIRAMA:
                out.append(base)          # explicit halant: no inherent vowel
                i += 2
                continue
            if ncp in DEV_MATRAS or ncp in (0x200C, 0x200D):
                out.append(base)
                i += 1                    # matra handled on the next iteration
                continue
            out.append(base + "a")
            i += 1
            continue

        if cp in DEV_MATRAS:
            out.append(DEV_MATRAS[cp])
            i += 1
            continue

        if cp in DEV_INDEPENDENT_VOWELS:
            out.append(DEV_INDEPENDENT_VOWELS[cp])
            i += 1
            continue

        if cp in DEV_SIGNS:
            out.append(DEV_SIGNS[cp])
            i += 1
            continue

        if cp in DEV_DIGITS:
            out.append(DEV_DIGITS[cp])
            i += 1
            continue

        if cp == VIRAMA:
            # Orphan virama: no consonant to attach to. Flag it, do not invent one.
            unmapped[ch] = unmapped.get(ch, 0) + 1
            i += 1
            continue

        if cp in DEV_TRANSPARENT:
            dropped[ch] = dropped.get(ch, 0) + 1
            i += 1
            continue

        if ch in ("\u200c", "\u200d"):
            i += 1
            continue

        if 0xA8E0 <= cp <= 0xA8FF or 0x1CD0 <= cp <= 0x1CFF:
            unmapped[ch] = unmapped.get(ch, 0) + 1
            i += 1
            continue

        # ASCII, punctuation, whitespace pass through untouched.
        out.append(ch)
        i += 1

    return TransliterationResult(
        text="".join(out), source_script="Devanagari", target_script="IAST",
        unmapped=unmapped, transparent_dropped=dropped,
    )


# ---------------------------------------------------------------------------
# IAST -> Devanagari
# ---------------------------------------------------------------------------
_IAST_CONSONANTS: dict[str, int] = {}
for _cp, _val in DEV_CONSONANTS.items():
    _IAST_CONSONANTS.setdefault(_val, _cp)
_IAST_CONSONANTS["kha"] = 0x0916   # prefer the ordinary ख over the nukta form
_IAST_CONSONANTS["ḷ"] = 0x0933    # retroflex ळ, not the vocalic vowel (see note)

# AMBIGUITY WE RESOLVE BY CONVENTION, NOT BY EVIDENCE
#   "ṛ"  is the vowel ऋ/ृ. The nukta consonant ड़ (0x095C) is also written "ṛ"
#        in IAST, but ड़ is a Perso-Arabic loan phoneme that does not occur in the
#        Prakrit and Sanskrit material this corpus holds, while vocalic ṛ occurs
#        constantly (kṛṣṇa, ṛṣabha, mokṣa-kṛt). Vowel wins.
#   "ḷ"  is the consonant ळ (0x0933), because retroflex ḷa is a live Prakrit
#        phoneme whereas vocalic ऌ is effectively extinct. Consequence: ऌ does not
#        round-trip and is reported by the round-trip test as a known loss.
_IAST_CONSONANTS.pop("ṛ", None)

_IAST_VOWEL_MATRAS: dict[str, int] = {}
for _cp, _val in DEV_MATRAS.items():
    _IAST_VOWEL_MATRAS.setdefault(_val, _cp)
_IAST_VOWEL_INDEPENDENT: dict[str, int] = {}
for _cp, _val in DEV_INDEPENDENT_VOWELS.items():
    _IAST_VOWEL_INDEPENDENT.setdefault(_val, _cp)
_IAST_VOWEL_MATRAS["a"] = 0  # inherent vowel: no matra glyph
_IAST_VOWEL_INDEPENDENT["a"] = 0x0905
# Fix collisions in favour of the common reading.
_IAST_VOWEL_MATRAS["e"] = 0x0947
_IAST_VOWEL_MATRAS["o"] = 0x094B
_IAST_VOWEL_INDEPENDENT["e"] = 0x090F
_IAST_VOWEL_INDEPENDENT["o"] = 0x0913
# Vocalic ḷ loses to the consonant (see the note above), so remove it here.
_IAST_VOWEL_MATRAS.pop("ḷ", None)
_IAST_VOWEL_INDEPENDENT.pop("ḷ", None)

_IAST_SIGNS: dict[str, int] = {
    "ṃ": ANUSVARA,
    "ṁ": ANUSVARA,
    "ḥ": VISARGA,
    "m̐": CANDRABINDU,
    "oṃ": OM,
    "||": DOUBLE_DANDA,
    "|": DANDA,
}

# Longest key wins. Among equal-length keys, SIGN beats VOWEL beats CONSONANT,
# because a shorter match that steals a vowel from a longer sign produces silent
# corruption ("saṃgha" must match "ṃ" as a sign, never "n"+"g" fiddling).
_KIND_RANK = {"sign": 0, "vowel": 1, "cons": 2}
_MATCH_KEYS: tuple[tuple[str, str], ...] = tuple(
    sorted(
        [(k, "sign") for k in _IAST_SIGNS]
        + [(k, "vowel") for k in _IAST_VOWEL_MATRAS if k != "a"]
        + [(k, "cons") for k in _IAST_CONSONANTS]
        + [("a", "vowel")],
        key=lambda kv: (-len(kv[0]), _KIND_RANK[kv[1]], kv[0]),
    )
)


def _match_at(text: str, i: int) -> tuple[str, str] | None:
    for key, kind in _MATCH_KEYS:
        if text.startswith(key, i):
            return key, kind
        # Latin uppercase forms of the same key (headings are capitalised)
        if text[i:i + len(key)].lower() == key and key[0] in "abcdefghijklmnopqrstuvwxyz":
            return text[i:i + len(key)], kind
    return None


def iast_to_devanagari(text: str) -> TransliterationResult:
    """IAST to Devanagari, reconstructing inherent vowels and halants correctly."""
    out: list[str] = []
    unmapped: dict[str, int] = {}
    folded = 0
    i = 0
    n = len(text)

    while i < n:
        ch = text[i]

        if ch.isdigit() and ch.isascii():
            out.append(chr(0x0966 + int(ch)))
            i += 1
            continue

        match = _match_at(text, i)
        if match is None:
            if ch.isascii():
                out.append(ch)          # ASCII punctuation/space passes through
            else:
                unmapped[ch] = unmapped.get(ch, 0) + 1
            i += 1
            continue

        key, kind = match
        if key != key.lower():
            folded += 1
        norm = key.lower()

        if kind == "sign":
            out.append(chr(_IAST_SIGNS[norm]))
            i += len(key)
            continue

        if kind == "vowel":
            if norm == "a":
                out.append(chr(0x0905))     # standalone 'a' is an independent vowel
            else:
                out.append(chr(_IAST_VOWEL_INDEPENDENT[norm]))
            i += len(key)
            continue

        # consonant: decide the following vowel
        cons_cp = _IAST_CONSONANTS[norm]
        j = i + len(key)
        nxt = _match_at(text, j)
        if nxt is not None and nxt[1] == "vowel":
            vkey, _ = nxt
            vnorm = vkey.lower()
            if vnorm == "a":
                out.append(chr(cons_cp))            # inherent vowel
            else:
                out.append(chr(cons_cp) + chr(_IAST_VOWEL_MATRAS[vnorm]))
            i = j + len(vkey)
            continue
        out.append(chr(cons_cp) + chr(VIRAMA))      # bare consonant
        i = j

    return TransliterationResult(
        text="".join(out), source_script="IAST", target_script="Devanagari",
        unmapped=unmapped, case_folded=folded,
    )


# ---------------------------------------------------------------------------
# Gujarati -> Devanagari (offset-based, exceptions explicit)
# ---------------------------------------------------------------------------
GUJARATI_TO_DEVANAGARI_OFFSET = 0x180

# Ranges where the parallel-block offset holds exactly.
_OFFSET_OK: tuple[tuple[int, int], ...] = (
    (0x0A81, 0x0A94),   # signs + independent vowels
    (0x0A95, 0x0AB9),   # consonants
    (0x0ABC, 0x0ACD),   # nukta .. virama (matras in 0x0ABE-0x0ACC)
    (0x0AD0, 0x0AD0),   # ૐ -> ॐ
    (0x0AE0, 0x0AE1),   # ૠ ૡ
    (0x0AE6, 0x0AEF),   # digits
)

# Gujarati codepoints with no Devanagari counterpart, and Devanagari-specific
# codepoints with no Gujarati counterpart. Listed so the loss is explicit.
_GUJARATI_UNMAPPABLE = {
    0x0AF0,  # ૰ abbreviation sign
    0x0AF1,  # ૱ rupee sign
    0x0AF9,  # ૹ
    0x0AFA, 0x0AFB, 0x0AFC, 0x0AFD, 0x0AFE, 0x0AFF,
}


def _in_ranges(cp: int, ranges: tuple[tuple[int, int], ...]) -> bool:
    return any(lo <= cp <= hi for lo, hi in ranges)


def gujarati_to_devanagari(text: str) -> TransliterationResult:
    """Gujarati script to Devanagari script (script conversion, not translation).

    Gujarati and Devanagari are parallel encodings of a shared repertoire for
    the range we need, so most of this is a codepoint offset. The exceptions are
    enumerated rather than assumed, and anything outside them is reported as
    unmapped instead of being guessed at.
    """
    out: list[str] = []
    unmapped: dict[str, int] = {}
    for ch in text:
        cp = ord(ch)
        if cp in _GUJARATI_UNMAPPABLE:
            unmapped[ch] = unmapped.get(ch, 0) + 1
            continue
        if _in_ranges(cp, _OFFSET_OK):
            out.append(chr(cp - GUJARATI_TO_DEVANAGARI_OFFSET))
            continue
        if 0x0A80 <= cp <= 0x0AFF:
            unmapped[ch] = unmapped.get(ch, 0) + 1
            continue
        out.append(ch)   # ASCII, whitespace, punctuation pass through
    return TransliterationResult(
        text="".join(out), source_script="Gujarati", target_script="Devanagari",
        unmapped=unmapped,
    )


# ---------------------------------------------------------------------------
# dispatch
# ---------------------------------------------------------------------------
SUPPORTED_PAIRS = {
    ("Devanagari", "IAST"): devanagari_to_iast,
    ("IAST", "Devanagari"): iast_to_devanagari,
    ("Roman", "Devanagari"): iast_to_devanagari,
    ("Gujarati", "Devanagari"): gujarati_to_devanagari,
}


def transliterate(text: str, source_script: str, target_script: str) -> TransliterationResult:
    """Transliterate, or raise loudly if the pair is not implemented.

    We deliberately do NOT fall back to a generic library: a silent fallback
    would transliterate Prakrit through a Sanskrit-oriented table and produce
    plausible-looking wrong text, which is the single worst failure mode for a
    scripture corpus.
    """
    if source_script == target_script:
        return TransliterationResult(text=text, source_script=source_script,
                                     target_script=target_script)
    fn = SUPPORTED_PAIRS.get((source_script, target_script))
    if fn is None:
        raise NotImplementedError(
            f"no {source_script} -> {target_script} transliteration implemented; "
            f"supported pairs: {sorted(SUPPORTED_PAIRS)}"
        )
    return fn(text)

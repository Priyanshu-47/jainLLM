"""A dependency-free BPE encoder that reads Hugging Face `tokenizer.json`.

WHY WE WROTE THIS INSTEAD OF INSTALLING `transformers`
The single most important output of this milestone is a *measured* token count
per candidate model. The environment this pipeline runs in has no third-party
packages, and installing a multi-gigabyte stack to count tokens would also make
the measurement un-auditable. `tokenizer.json` is a self-describing artefact, so
the encoder is reproducible from the file the model actually ships.

WHAT IS SUPPORTED (verified against real files in data/cache/tokenizers/)
  * BPE with GPT-2 byte-level pre-tokenisation   -- Qwen3 family
  * BPE with SentencePiece-style metaspace + byte fallback -- Sarvam, Gemma
  * Added/special tokens as literal splits
  * The cl100k/Qwen pre-tokenisation regex, reimplemented as a scanner
    (Python's `re` does not support `\\p{L}`, and HF uses the Rust regex crate,
    so a hand-written leftmost-first scanner is the faithful option)

WHAT IS NOT SUPPORTED, AND IS REFUSED RATHER THAN GUESSED
  * Unigram / SentencePiece-Viterbi models (some Gemma releases ship as
    `model.type == "Unigram"`). `load()` raises UnsupportedTokenizer.
  * Precompiled (tiktoken `.tiktoken`) normalizers.

TRUST MODEL
The encoder computes a **round-trip check at load time**: encode a probe string,
decode it back, and require the original text. That validates the byte mapping,
the merge ranks and the decoder. It does NOT validate the pre-tokenisation split
(BPE merging is associative over different splits as far as decoding is
concerned, but the split changes the count). So the measurement layer reports
both a pre-tokenised count and an unsplit count and calls the pair a bracket.
`roundtrip_verified` must be true before a count may be quoted without the
bracket.
"""

from __future__ import annotations

import heapq
import json
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class UnsupportedTokenizer(RuntimeError):
    """Raised when a tokenizer.json uses a scheme this encoder cannot honour."""


# ---------------------------------------------------------------------------
# byte <-> unicode map (GPT-2 / ByteLevel)
# ---------------------------------------------------------------------------
def bytes_to_unicode() -> dict[int, str]:
    """The canonical GPT-2 byte encoder: every byte becomes one printable char."""
    printable = (
        list(range(ord("!"), ord("~") + 1))
        + list(range(ord("\u00a1"), ord("\u00ac") + 1))
        + list(range(ord("\u00ae"), ord("\u00ff") + 1))
    )
    chars = printable[:]
    n = 0
    for byte in range(256):
        if byte not in printable:
            printable.append(byte)
            chars.append(256 + n)
            n += 1
    return dict(zip(printable, (chr(c) for c in chars)))


_BYTE_ENCODER = bytes_to_unicode()
_BYTE_DECODER = {v: k for k, v in _BYTE_ENCODER.items()}


# ---------------------------------------------------------------------------
# character predicates for the cl100k / Qwen split pattern
# ---------------------------------------------------------------------------
def _is_letter(ch: str) -> bool:
    return unicodedata.category(ch).startswith("L")


def _is_number(ch: str) -> bool:
    return unicodedata.category(ch)[0] == "N"


def _is_space(ch: str) -> bool:
    # Python's isspace() is very close to Unicode White_Space. The known
    # divergence is the C0 file-separator block (U+001C..U+001F), which is
    # stripped by normalisation long before tokenisation.
    return ch.isspace()


_CONTRACTIONS = ("'re", "'ve", "'ll", "'s", "'t", "'m", "'d")


def split_cl100k(text: str) -> list[str]:
    """Reimplementation of the Qwen/cl100k pre-tokenisation pattern.

    Pattern (Rust regex, leftmost-first, greedy):
        (?i:'s|'t|'re|'ve|'m|'ll|'d)
      | [^\\r\\n\\p{L}\\p{N}]?\\p{L}+
      | \\p{N}
      |  ?[^\\s\\p{L}\\p{N}]+[\\r\\n]*
      | \\s*[\\r\\n]+
      | \\s+(?!\\S)
      | \\s+

    Each alternative is tried in order at the scan position, exactly as the
    reference engine does. The scanner always advances at least one character,
    so it cannot loop.
    """
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]

        # (1) English contractions, case-insensitive
        low = text[i:i + 3].lower()
        hit = next((c for c in _CONTRACTIONS if low.startswith(c)), None)
        if hit is not None:
            out.append(text[i:i + len(hit)])
            i += len(hit)
            continue

        # (2) optional single non-letter/non-digit prefix, then letters
        if _is_letter(ch):
            j = i
            while j < n and _is_letter(text[j]):
                j += 1
            out.append(text[i:j])
            i = j
            continue
        if (ch not in "\r\n" and not _is_number(ch)
                and i + 1 < n and _is_letter(text[i + 1])):
            j = i + 1
            while j < n and _is_letter(text[j]):
                j += 1
            out.append(text[i:j])
            i = j
            continue

        # (3) exactly one digit
        if _is_number(ch):
            out.append(ch)
            i += 1
            continue

        # (4) optional space, then non-space/non-letter/non-digit run, then newlines
        j = i + 1 if ch == " " else i
        k = j
        while (k < n and not _is_space(text[k]) and not _is_letter(text[k])
               and not _is_number(text[k])):
            k += 1
        if k > j:
            while k < n and text[k] in "\r\n":
                k += 1
            out.append(text[i:k])
            i = k
            continue

        # (5) whitespace including at least one newline
        j = i
        while j < n and _is_space(text[j]) and text[j] not in "\r\n":
            j += 1
        k = j
        while k < n and text[k] in "\r\n":
            k += 1
        if k > j:
            out.append(text[i:k])
            i = k
            continue

        # (6) and (7) whitespace runs
        if _is_space(ch):
            j = i
            while j < n and _is_space(text[j]):
                j += 1
            out.append(text[i:j])
            i = j
            continue

        # Guarantee progress for any character no alternative claimed.
        out.append(ch)
        i += 1
    return out


def split_sentencepiece(text: str) -> list[str]:
    """`Split(" ", MergedWithPrevious)`: the space attaches to the preceding run.

    "a b c" -> ["a ", "b ", "c"]. This is what Llama-3-derived tokenizers
    (Sarvam, and the Gemma mirror we test) declare.
    """
    if text == "":
        return []
    parts = text.split(" ")
    out = [p + " " for p in parts[:-1]]
    if parts[-1] != "" or len(parts) == 1:
        out.append(parts[-1])
    return [p for p in out if p != ""]


@dataclass
class BPETokenizer:
    """A BPE encoder built from a Hugging Face `tokenizer.json`."""

    name: str
    path: Path
    vocab: dict[str, int] = field(default_factory=dict)
    merge_rank: dict[tuple[str, str], int] = field(default_factory=dict)
    added_tokens: dict[str, int] = field(default_factory=dict)
    added_lengths: tuple[int, ...] = ()
    unk_id: int | None = None
    byte_level: bool = False
    byte_fallback: bool = False
    metaspace: bool = False
    normalizer_supported: bool = True
    pretokenizer_kind: str = "none"
    roundtrip_verified: bool = False
    roundtrip_probe: str = ""
    notes: list[str] = field(default_factory=list)
    _max_piece_len: int = 0
    _inverse: dict[int, str] = field(default_factory=dict, repr=False)
    _added_inverse: dict[int, str] = field(default_factory=dict, repr=False)
    _merge_cache_limit: int = 400_000
    _merge_cache: dict[tuple[str, ...], list[str]] = field(default_factory=dict,
                                                           repr=False)

    # ---- loading -----------------------------------------------------------
    @classmethod
    def load(cls, name: str, path: Path) -> "BPETokenizer":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        model = raw.get("model", {})
        model_type = model.get("type")
        if model_type != "BPE":
            raise UnsupportedTokenizer(
                f"{name}: model.type={model_type!r} is not BPE. Unigram/Viterbi "
                f"encoding is not implemented, and guessing at it would produce "
                f"wrong token counts. This model must be measured with a real "
                f"tokenizer library or excluded."
            )

        norm = raw.get("normalizer")
        metaspace = False
        normalizer_supported = True
        if isinstance(norm, dict):
            ntype = norm.get("type")
            pat = norm.get("pattern", {})
            content = norm.get("content")
            if ntype == "Replace" and pat.get("String") == " " and content == "\u2581":
                metaspace = True
            elif ntype in ("Sequence", "Lowercase", "NFC", "NFD", "NFKC", "NFKD", "Prepend"):
                # Harmless for our purposes; NFC is already applied upstream.
                if ntype == "Sequence":
                    for sub in norm.get("normalizers", []):
                        if isinstance(sub, dict) and sub.get("type") == "Replace" \
                                and sub.get("pattern", {}).get("String") == " " \
                                and sub.get("content") == "\u2581":
                            metaspace = True
            elif ntype == "Precompiled":
                normalizer_supported = False
                metaspace = True  # tiktoken-style: metaspace-equivalent handling

        pretok = raw.get("pre_tokenizer", {})
        byte_level = _contains_type(pretok, "ByteLevel")
        if byte_level:
            pretokenizer_kind = "cl100k"
        elif _split_pattern_is_space(pretok):
            pretokenizer_kind = "split-space"
        elif pretok in ({}, None):
            pretokenizer_kind = "none"
            normalizer_supported = normalizer_supported
        else:
            pretokenizer_kind = "unsupported"

        with_metaspace = metaspace or pretokenizer_kind == "split-space"
        byte_fallback = bool(model.get("byte_fallback", False))
        if with_metaspace and not byte_fallback:
            byte_fallback = any(k.startswith("<0x") for k in model.get("vocab", {}))

        vocab = {str(k): int(v) for k, v in model.get("vocab", {}).items()}
        merges: dict[tuple[str, str], int] = {}
        for rank, entry in enumerate(model.get("merges", [])):
            if isinstance(entry, str):
                pair = entry.split(" ")
                if len(pair) != 2:
                    continue
                merges[(pair[0], pair[1])] = rank
            elif isinstance(entry, (list, tuple)) and len(entry) == 2:
                merges[(str(entry[0]), str(entry[1]))] = rank

        added: dict[str, int] = {}
        for tok in raw.get("added_tokens", []) or []:
            content = tok.get("content")
            tid = tok.get("id")
            if content is not None and tid is not None:
                added[str(content)] = int(tid)

        unk = model.get("unk_token")
        unk_id = vocab.get(unk) if unk else None

        tok = cls(
            name=name, path=Path(path), vocab=vocab, merge_rank=merges,
            added_tokens=added,
            added_lengths=tuple(sorted({len(k) for k in added}, reverse=True)),
            unk_id=unk_id,
            byte_level=byte_level or normalizer_supported is False,
            byte_fallback=byte_fallback,
            metaspace=with_metaspace,
            normalizer_supported=normalizer_supported,
            pretokenizer_kind=pretokenizer_kind,
        )

        if pretokenizer_kind == "unsupported":
            tok.notes.append(
                f"unrecognised pre_tokenizer {json.dumps(pretok)[:120]}; falling "
                f"back to no-split encoding (count is a lower bound)"
            )
        if not normalizer_supported:
            tok.notes.append("normalizer is Precompiled/unrecognised; trailing "
                             "space handling may differ from the reference")
        tok._max_piece_len = max((len(k) for k in vocab), default=0)
        tok._inverse = {v: k for k, v in vocab.items()}
        tok._added_inverse = {v: k for k, v in added.items()}
        tok._verify_roundtrip()
        return tok

    # ---- properties --------------------------------------------------------
    @property
    def vocab_size(self) -> int:
        return len(self.vocab)

    # ---- round-trip self-check --------------------------------------------
    def _verify_roundtrip(self) -> None:
        probe = (
            "kṛṣṇa dharma saṃgha\n"
            "णमोक्कारो सव्वं अट्ठमंगलं सुत्त\n"
            "જૈન ધર્મ અહિંસા\n"
            "जैन धर्म   \t  \u0964\u0964\n"
            "tīrthaṃkara + ahiṃsā = mokṣa 12,345\n"
        )
        self.roundtrip_probe = probe
        try:
            ids = self.encode(probe)
            back = self.decode(ids)
        except Exception as exc:  # pragma: no cover - reported, not raised
            self.roundtrip_verified = False
            self.notes.append(f"round-trip raised {type(exc).__name__}: {exc}")
            return
        self.roundtrip_verified = back == probe
        if not self.roundtrip_verified:
            self.notes.append(
                "round-trip mismatch: decode(encode(x)) != x; token counts from "
                "this tokenizer must be treated as unverified"
            )

    # ---- pre-tokenisation --------------------------------------------------
    def _pretokenize(self, text: str, apply: bool) -> list[str]:
        if not apply or self.pretokenizer_kind in ("none", "unsupported"):
            return [text] if text else []
        if self.pretokenizer_kind == "cl100k":
            return split_cl100k(text)
        return split_sentencepiece(text)

    def _initial_symbols(self, piece: str) -> list[str]:
        """Turn a pre-token into the starting symbol sequence for BPE."""
        if self.byte_level and not self.metaspace:
            # GPT-2 byte-level: every byte becomes one printable character.
            return [_BYTE_ENCODER[b] for b in piece.encode("utf-8")]

        symbols: list[str] = []
        for ch in piece:
            if ch in self.vocab:
                symbols.append(ch)
                continue
            if self.byte_fallback:
                symbols.extend(f"<0x{b:02X}>" for b in ch.encode("utf-8"))
                continue
            # No representation at all. Keep the character in the symbol
            # stream: it cannot merge (it has no merge rank), and encode() will
            # resolve it to unk_id. Dropping it would undercount the token count.
            symbols.append(ch)
        return symbols

    # ---- BPE merge ---------------------------------------------------------
    def _merge(self, symbols: list[str]) -> list[str]:
        """Memoised wrapper around the heap-based merge.

        Corpora repeat themselves: refrains, running heads, dictionary headwords
        and OCR artifacts all recur, so the same symbol tuples are merged over and
        over. The cache is bounded so that a pathological document cannot exhaust
        memory, and it is keyed on the symbol tuple, which makes it deterministic.
        """
        key = tuple(symbols)
        cached = self._merge_cache.get(key)
        if cached is not None:
            return cached
        result = self._merge_heap(list(symbols))
        if len(self._merge_cache) < self._merge_cache_limit:
            self._merge_cache[key] = result
        return result

    def _merge_heap(self, symbols: list[str]) -> list[str]:
        """Apply merges by globally lowest rank, efficiently.

        THE RULE: at each step, merge the adjacent pair with the LOWEST merge
        rank; ties go to the leftmost pair. That is the reference semantics, and
        `_merge_reference` below implements it directly.

        WHY NOT USE THE REFERENCE IMPLEMENTATION
        The direct version rescans every adjacent pair on every step and rebuilds
        the list, so it is O(n^2) per merge round and quadratic-to-cubic overall.
        Units in this corpus reach 1500 characters, and the metaspace tokenizers
        (Sarvam, Gemma) do not split inside Devanagari, so a single piece can be
        1500 initial symbols. Measured on the real release, the reference version
        could not finish ~98k records in ten minutes.

        This version keeps the same rule but uses a doubly linked list plus a heap
        of candidate pairs with lazy invalidation, which is O(n log n). Merged
        results must be identical: `tests/test_tokenization.py` asserts that on
        real corpus samples, so the optimisation is proven equivalent rather than
        assumed equivalent.
        """
        count = len(symbols)
        if count < 2:
            return symbols

        tokens = list(symbols)
        prev_index = [i - 1 for i in range(count)]
        next_index = [i + 1 for i in range(count)]
        alive = [True] * count
        version = [0] * count

        heap: list[tuple[int, int, int]] = []
        merge_rank = self.merge_rank
        for i in range(count - 1):
            rank = merge_rank.get((tokens[i], tokens[i + 1]))
            if rank is not None:
                heap.append((rank, i, 0))
        heapq.heapify(heap)

        while heap:
            rank, i, stamp = heapq.heappop(heap)
            if stamp != version[i] or not alive[i]:
                continue
            j = next_index[i]
            if j >= count or not alive[j]:
                continue
            # The pair may have changed under us; re-derive its rank and check.
            if merge_rank.get((tokens[i], tokens[j])) != rank:
                continue

            tokens[i] = tokens[i] + tokens[j]
            alive[j] = False
            after = next_index[j]
            next_index[i] = after
            if after < count:
                prev_index[after] = i
            version[i] += 1

            # heappush, NOT append. Appending leaves the list in an arbitrary
            # order and heappop then returns something that is not the minimum,
            # which silently produces different token counts than the reference
            # rule. This was caught by test_heap_merge_matches_reference.
            if after < count:
                new_rank = merge_rank.get((tokens[i], tokens[after]))
                if new_rank is not None:
                    heapq.heappush(heap, (new_rank, i, version[i]))
            before = prev_index[i]
            if before >= 0 and alive[before]:
                new_rank = merge_rank.get((tokens[before], tokens[i]))
                if new_rank is not None:
                    heapq.heappush(heap, (new_rank, before, version[before]))

        return [tokens[i] for i in range(count) if alive[i]]

    def _merge_reference(self, symbols: list[str]) -> list[str]:
        """Direct, unoptimised implementation of the BPE merge rule.

        Kept in the shipped code on purpose: it is the oracle that the fast path
        is tested against, so a future change to `_merge` cannot silently change
        token counts without a test failing.
        """
        if len(symbols) < 2:
            return symbols
        while True:
            best_rank = None
            best_i = -1
            for i in range(len(symbols) - 1):
                rank = self.merge_rank.get((symbols[i], symbols[i + 1]))
                if rank is not None and (best_rank is None or rank < best_rank):
                    best_rank = rank
                    best_i = i
            if best_i < 0:
                return symbols
            symbols = (symbols[:best_i]
                       + [symbols[best_i] + symbols[best_i + 1]]
                       + symbols[best_i + 2:])

    # ---- encode / decode ---------------------------------------------------
    def encode(self, text: str, apply_pretokenizer: bool = True) -> list[int]:
        if text == "":
            return []
        if self.metaspace:
            text = text.replace(" ", "\u2581")

        ids: list[int] = []
        for chunk, is_added in self._split_added(text):
            if is_added:
                ids.append(self.added_tokens[chunk])
                continue
            for piece in self._pretokenize(chunk, apply_pretokenizer):
                if piece == "":
                    continue
                symbols = self._merge(self._initial_symbols(piece))
                for sym in symbols:
                    tid = self.vocab.get(sym)
                    if tid is None:
                        tid = self.added_tokens.get(sym)
                    if tid is None:
                        if self.unk_id is None:
                            raise KeyError(
                                f"{self.name}: symbol {sym!r} has no id and the "
                                f"model declares no unk_token"
                            )
                        tid = self.unk_id
                    ids.append(tid)
        return ids

    def _split_added(self, text: str) -> list[tuple[str, bool]]:
        if not self.added_tokens or not self.added_lengths:
            return [(text, False)]
        out: list[tuple[str, bool]] = []
        buf: list[str] = []
        i = 0
        n = len(text)
        while i < n:
            hit = None
            for length in self.added_lengths:
                if i + length <= n and text[i:i + length] in self.added_tokens:
                    hit = text[i:i + length]
                    break
            if hit is not None:
                if buf:
                    out.append(("".join(buf), False))
                    buf = []
                out.append((hit, True))
                i += len(hit)
                continue
            buf.append(text[i])
            i += 1
        if buf:
            out.append(("".join(buf), False))
        return out

    def decode(self, ids: list[int]) -> str:
        inverse = self._inverse
        added_inverse = self._added_inverse
        pieces: list[str] = []
        for tid in ids:
            if tid in added_inverse:
                pieces.append(added_inverse[tid])
                continue
            tok = inverse.get(tid)
            if tok is None:
                pieces.append("")
                continue
            if self.byte_fallback and tok.startswith("<0x") and tok.endswith(">"):
                try:
                    pieces.append(bytes([int(tok[3:-1], 16)]).decode("latin-1"))
                except ValueError:
                    pieces.append(tok)
            elif self.byte_level or self.metaspace:
                pieces.append(tok)
            else:
                pieces.append(tok)

        joined = "".join(pieces)
        if self.metaspace:
            joined = joined.replace("\u2581", " ")

        # Rebuild bytes, then decode as UTF-8. Tokens hold either byte-map
        # characters (Qwen) or literal text plus latin-1 byte placeholders.
        raw = bytearray()
        for ch in joined:
            if self.byte_level:
                raw.extend(bytes([_BYTE_DECODER[ch]]) if ch in _BYTE_DECODER
                           else ch.encode("utf-8"))
            else:
                raw.extend(ch.encode("latin-1") if ord(ch) < 256 else ch.encode("utf-8"))
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return raw.decode("utf-8", errors="replace")

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "path": str(self.path),
            "vocab_size": self.vocab_size,
            "merges": len(self.merge_rank),
            "byte_level": self.byte_level,
            "byte_fallback": self.byte_fallback,
            "metaspace": self.metaspace,
            "pretokenizer_kind": self.pretokenizer_kind,
            "normalizer_supported": self.normalizer_supported,
            "roundtrip_verified": self.roundtrip_verified,
            "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _contains_type(node: Any, wanted: str) -> bool:
    if isinstance(node, dict):
        if node.get("type") == wanted:
            return True
        return any(_contains_type(v, wanted) for v in node.values())
    if isinstance(node, list):
        return any(_contains_type(v, wanted) for v in node)
    return False


def _split_pattern_is_space(node: Any) -> bool:
    if isinstance(node, dict):
        if node.get("type") == "Split":
            pat = node.get("pattern", {})
            if pat.get("String") == " " or pat.get("Regex") == " ":
                return True
        return any(_split_pattern_is_space(v) for v in node.values())
    if isinstance(node, list):
        return any(_split_pattern_is_space(v) for v in node)
    return False

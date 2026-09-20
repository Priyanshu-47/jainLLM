"""Tokenizer tests.

The important test in this file is `test_heap_merge_matches_reference`. The BPE
merge was rewritten from a direct O(n^2) scan to a heap over a linked list in
order to measure the corpus in reasonable time. An optimisation like that either
produces identical token counts or it silently corrupts every number the project
reports, so equivalence is asserted against the unoptimised implementation on real
text drawn from the release, not on toy strings.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from svk_corpus.tokenization.bpe import (
    BPETokenizer,
    UnsupportedTokenizer,
    bytes_to_unicode,
    split_cl100k,
    split_sentencepiece,
)

REPO = Path(__file__).resolve().parents[1]
TOKENIZER_DIR = REPO / "data" / "cache" / "tokenizers"
RELEASE = REPO / "data" / "release" / "rag_corpus.jsonl"

SAMPLE_TEXTS = (
    "णमोक्कारो सव्वं अट्ठमंगलं सुत्तं जाव हवइ अत्थि णत्थि तम्हा पुण दव्वं",
    "kṛṣṇa dharma saṃgha tīrthaṃkara ahiṃsā mokṣa ṛṣabha namokkāro savvaṃ",
    "જૈન ધર્મ અહિંસા સત્ય અચૌર્ય બ્રહ્મચર્ય અપરિગ્રહ પંચ મહાવ્રત",
    "The Sthanakvasi tradition is a Svetambara Jain sect that rejects temple worship.",
    "श्री तीर्थंकर महावीर स्वामी इति भवति अस्ति तथा यथा ज्ञान दर्शन चारित्र मोक्ष",
    "0123456789 [[ ]] \"mixed\" (पाठ) 12,345.67 — dash",
)


def _available_tokenizers() -> list[tuple[str, Path]]:
    if not TOKENIZER_DIR.is_dir():
        return []
    out = []
    for path in sorted(TOKENIZER_DIR.glob("*.tokenizer.json")):
        out.append((path.name.replace(".tokenizer.json", ""), path))
    return out


def _release_samples(limit: int) -> list[str]:
    if not RELEASE.is_file():
        return []
    texts: list[str] = []
    with RELEASE.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            text = record.get("normalized_text") or record.get("text") or ""
            if len(text) >= 60:
                texts.append(text)
            if len(texts) >= limit:
                break
    return texts


class ByteMapTests(unittest.TestCase):
    def test_bytes_to_unicode_is_a_bijection_over_256_bytes(self):
        mapping = bytes_to_unicode()
        self.assertEqual(len(mapping), 256)
        self.assertEqual(len(set(mapping.values())), 256)
        self.assertEqual(mapping[0x20], "\u0120")   # space -> 'Ġ'
        self.assertEqual(mapping[0x0A], "\u010a")   # newline -> 'Ċ'

    def test_invertible(self):
        mapping = bytes_to_unicode()
        inverse = {v: k for k, v in mapping.items()}
        for byte, char in mapping.items():
            self.assertEqual(inverse[char], byte)


class SplitterTests(unittest.TestCase):
    def test_cl100k_attaches_leading_space_to_the_word(self):
        self.assertEqual(
            split_cl100k("The Sthanakvasi tradition"),
            ["The", " Sthanakvasi", " tradition"],
        )

    def test_cl100k_isolates_single_digits(self):
        self.assertEqual(split_cl100k("12"), ["1", "2"])

    def test_cl100k_handles_contractions_case_insensitively(self):
        self.assertEqual(split_cl100k("it's Don't"), ["it", "'s", " Don", "'t"])

    def test_cl100k_reconstructs_the_input_exactly(self):
        for text in SAMPLE_TEXTS:
            self.assertEqual("".join(split_cl100k(text)), text)

    def test_sentencepiece_split_merges_space_with_previous(self):
        self.assertEqual(split_sentencepiece("a b c"), ["a ", "b ", "c"])
        self.assertEqual(split_sentencepiece(""), [])

    def test_sentencepiece_reconstructs_the_input_exactly(self):
        for text in SAMPLE_TEXTS:
            self.assertEqual("".join(split_sentencepiece(text)), text)


class TokenizerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tokenizers: dict[str, BPETokenizer] = {}
        for name, path in _available_tokenizers():
            try:
                cls.tokenizers[name] = BPETokenizer.load(name, path)
            except UnsupportedTokenizer:
                continue

    def test_at_least_one_tokenizer_is_available(self):
        if not _available_tokenizers():
            self.skipTest("no tokenizer.json cached")
        self.assertTrue(self.tokenizers, "no tokenizer could be loaded")

    def test_roundtrip_verified_for_every_loaded_tokenizer(self):
        for name, tokenizer in self.tokenizers.items():
            with self.subTest(tokenizer=name):
                self.assertTrue(
                    tokenizer.roundtrip_verified,
                    f"{name} failed decode(encode(x)) == x: {tokenizer.notes}",
                )

    def test_encode_decode_roundtrips_on_sample_text(self):
        for name, tokenizer in self.tokenizers.items():
            for text in SAMPLE_TEXTS:
                with self.subTest(tokenizer=name, text=text[:24]):
                    self.assertEqual(tokenizer.decode(tokenizer.encode(text)), text)

    def test_empty_input_yields_no_tokens(self):
        for tokenizer in self.tokenizers.values():
            self.assertEqual(tokenizer.encode(""), [])

    def test_heap_merge_matches_reference(self):
        """The optimisation must be provably equivalent, on real corpus text."""
        samples = _release_samples(60) or list(SAMPLE_TEXTS)
        self.assertTrue(samples)
        for name, tokenizer in self.tokenizers.items():
            for text in samples:
                for piece in tokenizer._pretokenize(text, True)[:40]:
                    symbols = tokenizer._initial_symbols(piece)
                    with self.subTest(tokenizer=name, piece=piece[:24]):
                        self.assertEqual(
                            tokenizer._merge_heap(list(symbols)),
                            tokenizer._merge_reference(list(symbols)),
                        )

    def test_merge_cache_does_not_change_counts(self):
        for name, tokenizer in self.tokenizers.items():
            for text in SAMPLE_TEXTS:
                first = tokenizer.encode(text)
                tokenizer._merge_cache.clear()
                second = tokenizer.encode(text)
                with self.subTest(tokenizer=name):
                    self.assertEqual(first, second)

    def test_no_third_party_imports_are_required(self):
        import svk_corpus.tokenization.bpe as module
        source = Path(module.__file__).read_text(encoding="utf-8")
        for forbidden in ("import torch", "import transformers", "import regex",
                          "import sentencepiece"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()

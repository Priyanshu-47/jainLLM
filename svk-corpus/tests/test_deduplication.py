"""Deduplication tests: exact + near collapse, translation/commentary preserved.

The policy being tested: duplicates collapse only within the same (text_role,
language) population. A translation is not a duplicate of its original, and a
commentary is not a duplicate of its base text.
"""

from __future__ import annotations

import unittest

from svk_corpus.deduplication.dedupe import (
    STATUS_EXACT,
    STATUS_NEAR,
    STATUS_UNIQUE,
    Deduplicator,
    MinHasher,
)


def _long_text(seed: str) -> str:
    # Three DISJOINT paragraph bodies. Tests that require *distinct* texts must
    # not share long n-grams: the original single-body helper differed only by
    # one digit, giving MinHash Jaccard ~0.98, so near-dedup collapsed them
    # *by design* (threshold 0.85) and the tests were testing the wrong thing.
    body = _BODIES[int(seed) % len(_BODIES)]
    return body + f" विशिष्ट परिशिष्ट संख्या {seed}।"


_BODIES = (
    (
        "प्रथम अध्याय में श्री गुरु कहते हैं कि जीवों में दया धर्म का मूल है। "
        "उन्होंने समझाया कि अहिंसा परमो धर्मः और यही शास्त्र की मुख्य दिशा है। "
        "इसके बाद सम्पूर्ण सम्प्रदाय के आचरण का वर्णन आता है। "
    ),
    (
        "दूसरे प्रकरण में सम्यक दर्शन की परिभाषा दी गई है और उसके आठ अंग बताए गए हैं। "
        "विमल कीर्ति गणि लिखते हैं कि सम्यक चारित्र के बिना मोक्ष मार्ग अधूरा है। "
        "यहाँ गुप्त अर्थ की व्याख्या और उसके प्रमाण भी दिए गए हैं। "
    ),
    (
        "तीसरे भाग में तप के बाहरी और भीतरी भेदों का विस्तार से वर्णन है। "
        "उपवास, वृत्ति संक्षेप और कायोत्सर्ग को बाहरी तप कहा गया है। "
        "आचार्य समझाते हैं कि तप का अंतिम उद्देश्य क्षय है, न कि केवल शरीर की क्लेश। "
    ),
)


class TestExactDeduplication(unittest.TestCase):
    def test_identical_text_collapses(self):
        d = Deduplicator()
        a = d.add("u1", _long_text("7"), language="hi")
        b = d.add("u2", _long_text("7"), language="hi")
        self.assertEqual(a.status, STATUS_UNIQUE)
        self.assertEqual(b.status, STATUS_EXACT)
        self.assertEqual(b.canonical_unit_id, "u1")
        self.assertFalse(b.kept)

    def test_unique_text_kept(self):
        d = Deduplicator()
        self.assertTrue(d.add("u1", _long_text("1"), language="hi").kept)
        self.assertTrue(d.add("u2", _long_text("2"), language="hi").kept)

    def test_counts_track_statuses(self):
        d = Deduplicator()
        d.add("u1", _long_text("3"), language="hi")
        d.add("u2", _long_text("3"), language="hi")
        d.add("u3", _long_text("4"), language="hi")
        self.assertEqual(d.counts[STATUS_EXACT], 1)
        self.assertEqual(d.counts[STATUS_UNIQUE], 2)

    def test_raw_layer_dedup(self):
        # Same raw text, different normalisation results: still an exact dup.
        d = Deduplicator()
        d.add("u1", "अहिंसा  परमो", raw_text="अहिंसा  परमो", language="hi")
        dec = d.add("u2", "अहिंसा परमो", raw_text="अहिंसा  परमो", language="hi")
        self.assertEqual(dec.status, STATUS_EXACT)


class TestPopulationSeparation(unittest.TestCase):
    def test_translation_not_duplicate_of_original(self):
        text = _long_text("9")
        d = Deduplicator()
        self.assertTrue(d.add("orig", text, language="hi").kept)
        # Same string, but it is a translation into Gujarati: different population.
        self.assertTrue(d.add("trans", text, language="gu").kept)

    def test_commentary_not_duplicate_of_base(self):
        text = _long_text("9")
        d = Deduplicator()
        self.assertTrue(d.add("base", text, text_role="ORIGINAL", language="hi").kept)
        self.assertTrue(
            d.add("comm", text, text_role="COMMENTARY", language="hi").kept
        )

    def test_ocr_role_separate_from_original(self):
        text = _long_text("11")
        d = Deduplicator()
        self.assertTrue(d.add("o1", text, text_role="ORIGINAL", language="hi").kept)
        self.assertTrue(d.add("o2", text, text_role="OCR", language="hi").kept)


class TestNearDeduplication(unittest.TestCase):
    def test_minor_ocr_variation_is_near(self):
        base = _long_text("13")
        variant = base.replace("अहिंसा", "अहिंसा", 1) + " अतिरिक्त शब्द।"
        d = Deduplicator()
        first = d.add("u1", base, language="hi")
        second = d.add("u2", variant, language="hi")
        self.assertEqual(first.status, STATUS_UNIQUE)
        self.assertIn(second.status, (STATUS_NEAR, STATUS_EXACT))
        self.assertFalse(second.kept)

    def test_different_text_not_collapsed(self):
        d = Deduplicator()
        self.assertTrue(d.add("u1", _long_text("21"), language="hi").kept)
        self.assertTrue(d.add("u2", _long_text("22"), language="hi").kept)


class TestMinHashDeterminism(unittest.TestCase):
    def test_signature_deterministic(self):
        m = MinHasher()
        s1 = m.signature(_long_text("31"))
        s2 = m.signature(_long_text("31"))
        self.assertEqual(s1, s2)

    def test_similarity_bounds(self):
        m = MinHasher()
        a = m.signature(_long_text("32"))
        b = m.signature(_long_text("33"))
        for sig in (a, b):
            self.assertEqual(len(sig), m.num_hashes)
        sim = m.similarity(a, b)
        self.assertGreaterEqual(sim, 0.0)
        self.assertLessEqual(sim, 1.0)

    def test_identical_texts_similarity_one(self):
        m = MinHasher()
        a = m.signature(_long_text("34"))
        b = m.signature(_long_text("34"))
        self.assertEqual(m.similarity(a, b), 1.0)


if __name__ == "__main__":
    unittest.main()

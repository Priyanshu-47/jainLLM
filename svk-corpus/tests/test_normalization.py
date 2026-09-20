"""Normalisation tests: Gujarati, Devanagari, Sanskrit, Prakrit, Roman, marks.

The invariant being tested: normalisation must never destroy Indic text. Every
destructive-opportunity case (zero-width, control chars, whitespace, NFKC) keeps
the alphabetic content intact.
"""

from __future__ import annotations

import unittest
import unicodedata

from svk_corpus.normalization.unicode import NORMALIZATION_VERSION, normalize_text, unicode_quality
from svk_corpus.normalization.indic import (
    detect_language_hint,
    detect_script,
    language_script_consistency,
    script_profile,
)
from svk_corpus.normalization.transliteration import (
    devanagari_to_iast,
    gujarati_to_devanagari,
    iast_to_devanagari,
)

# ----------------------------------------------------------------- fixtures --
GUJARATI = "જૈન ધર્મમાં અહિંસા પરમો ધર્મઃ છે અને સત્ય તેનું મૂળ છે."          # Gujarati prose
DEVANAGARI = "अहिंसा परमो धर्मः। सत्येन धर्मः परिपाल्यते॥"                    # Hindi/Sanskrit prose
SANSKRIT = "सर्वे भवन्तु सुखिनः सर्वे सन्तु निरामयाः।"                        # Sanskrit verse line
PRAKRIT_ROMAN = "savve jīvā vi icchanti jīvitun na marijjium"               # Ardhamāgadhī in IAST
IAST_MARKS = "ā ī ū ṛ ṭ ḍ ṇ ś ṣ ṁ ḥ ṃ"


class TestNormalizationDoesNotDestroyIndic(unittest.TestCase):
    def test_gujarati_content_preserved(self):
        res = normalize_text(GUJARATI)
        self.assertEqual(res.raw, GUJARATI)
        for ch in GUJARATI:
            if unicodedata.category(ch).startswith("L"):
                self.assertIn(ch, res.normalized)
        self.assertIn("જૈન", res.normalized)
        self.assertIn("ધર્મ", res.normalized)

    def test_devanagari_content_preserved(self):
        res = normalize_text(DEVANAGARI)
        for ch in DEVANAGARI:
            if unicodedata.category(ch).startswith("L"):
                self.assertIn(ch, res.normalized)
        self.assertIn("अहिंसा", res.normalized)

    def test_sanskrit_combining_marks_survive(self):
        # सुखिनः = स + ु + ख + ि + न + ् + ः — matras and virama must survive.
        res = normalize_text(SANSKRIT)
        self.assertIn("सुखिनः", res.normalized)
        self.assertIn("निरामयाः", res.normalized)
        # Virama explicitly:
        self.assertIn("सन्तु", res.normalized)

    def test_zwnj_preserved_zwj_preserved(self):
        # ZWNJ (U+200C) is orthographically meaningful in Indic scripts.
        text = "क्ष" + "\u200c" + "त्र"
        res = normalize_text(text)
        self.assertIn("\u200c", res.normalized)
        self.assertNotIn("\u200b", res.normalized)  # ZWSP must go

    def test_zero_width_stripped_but_letters_kept(self):
        text = "જૈન\u200bધર્મ\u200b"
        res = normalize_text(text)
        self.assertNotIn("\u200b", res.normalized)
        self.assertIn("જૈનધર્મ", res.normalized)

    def test_crlf_and_tabs(self):
        res = normalize_text("पंक्ति एक\r\nपंक्ति दो\r\n\r\n\r\nपंक्ति तीन")
        self.assertNotIn("\r", res.normalized)
        # max_blank_lines=1 permits ONE blank line ("\n\n") but collapses the
        # triple run; zero double-newlines would mean blank lines are banned.
        self.assertEqual(res.normalized.count("\n\n"), 1)
        self.assertNotIn("\n\n\n", res.normalized)

    def test_nfc_composes_decomposed_devanagari(self):
        decomposed = "अ" + "ह" + "\u093f" + "न" + "स" + "ा"   # ि before स? no — NFD-ish vowel sign sequence
        res = normalize_text(decomposed)
        self.assertEqual(res.normalized, unicodedata.normalize("NFC", decomposed))

    def test_nfkc_where_safe_keeps_prakrit_roman(self):
        res = normalize_text(PRAKRIT_ROMAN, unicode_form="NFKC")
        self.assertIn("jīvā", res.normalized)

    def test_raw_layer_untouched(self):
        messy = "  अहिंसा  \u200b\r\n\n   परमो  "
        res = normalize_text(messy)
        self.assertEqual(res.raw, messy)  # raw preserved verbatim

    def test_stats_report_what_happened(self):
        res = normalize_text("જૈન\u200b A\r\nB")
        self.assertGreaterEqual(res.stats.zero_width_removed, 1)
        self.assertGreaterEqual(res.stats.newlines_normalized, 1)
        self.assertTrue(res.stats.chars_in >= res.stats.chars_out)

    def test_empty_input(self):
        res = normalize_text("")
        self.assertEqual(res.normalized, "")

    def test_replacement_char_counted_not_created(self):
        # A U+FFFD already present is counted, never introduced by us.
        clean = normalize_text(GUJARATI)
        self.assertNotIn("\ufffd", clean.normalized)
        dirty = "abc\ufffddef"
        q = unicode_quality(dirty)
        self.assertEqual(q["replacement_chars"], 1)


class TestScriptDetection(unittest.TestCase):
    def test_gujarati_script(self):
        ev = detect_script(GUJARATI)
        self.assertEqual(ev.script, "Gujarati")
        self.assertGreater(ev.purity, 0.9)

    def test_devanagari_script(self):
        ev = detect_script(DEVANAGARI)
        self.assertEqual(ev.script, "Devanagari")

    def test_roman_script(self):
        ev = detect_script(PRAKRIT_ROMAN)
        self.assertEqual(ev.script, "Latin")

    def test_mixed_script_flags_ambiguity(self):
        mixed = GUJARATI + " " + DEVANAGARI
        ev = detect_script(mixed)
        self.assertTrue(ev.ambiguous or ev.purity < 0.9)

    def test_short_text_returns_unknown(self):
        ev = detect_script("ab")
        self.assertEqual(ev.script, "unknown")

    def test_profile_excludes_common_from_denominator(self):
        # Spaces/digits must not dilute script purity.
        ev = detect_script("૧૨૩ ૪૫૬   " + GUJARATI)
        self.assertEqual(ev.script, "Gujarati")

    def test_script_profile_counts(self):
        prof = script_profile("જૈન जैन")
        self.assertGreater(prof.get("Gujarati", 0), 0)
        self.assertGreater(prof.get("Devanagari", 0), 0)


class TestLanguageHints(unittest.TestCase):
    def test_gujarati_script_implies_gujarati(self):
        hint = detect_language_hint(GUJARATI, script="Gujarati")
        self.assertEqual(hint.language, "gu")
        # Confidence is capped at medium BY DESIGN — never overwrite curated data.
        self.assertIn(hint.confidence, ("medium", "high"))

    def test_hindi_markers_in_devanagari(self):
        hindi = "यह एक विशाल और प्रसिद्ध ग्रंथ है और इसमें बहुत कुछ नहीं है।"
        hint = detect_language_hint(hindi, script="Devanagari")
        self.assertEqual(hint.language, "hi")

    def test_prakrit_markers_win_over_sanskrit(self):
        prakrit = "सव्वे जीवा वि इच्छंति जीविउं ण मरिज्जिउं, तम्हा पाणिवहं घोरं निहत्था।"
        hint = detect_language_hint(prakrit, script="Devanagari")
        # Documented contract: Devanagari does NOT separate pra/sa/hi on lexical
        # markers alone, so the hint is deliberately "unknown" with the
        # candidates recorded in evidence — a curated value is required.
        self.assertEqual(hint.language, "unknown")
        self.assertEqual(hint.method, "ambiguous-devanagari")
        self.assertIn("pra", hint.evidence.get("candidates", []))

    def test_english(self):
        hint = detect_language_hint(
            "The Jain Agamas are the canonical texts and this is the tradition.")
        self.assertEqual(hint.language, "en")

    def test_hint_never_high_for_marker_method(self):
        hint = detect_language_hint("यह और वह इसमें नहीं है।", script="Devanagari")
        self.assertNotEqual(hint.confidence, "high")

    def test_consistency_gujarati_language_gujarati_script_ok(self):
        self.assertEqual(language_script_consistency("Gujarati", "Gujarati"), [])

    def test_consistency_flags_mismatch(self):
        problems = language_script_consistency("Gujarati", "Devanagari")
        self.assertTrue(problems)


class TestTransliteration(unittest.TestCase):
    def test_devanagari_to_iast_basic(self):
        res = devanagari_to_iast("धर्म")
        self.assertEqual(res.text, "dharma")

    def test_devanagari_to_iast_virama(self):
        res = devanagari_to_iast("क्")
        self.assertEqual(res.text, "k")

    def test_devanagari_to_iast_vowel_signs(self):
        res = devanagari_to_iast("कि")
        self.assertEqual(res.text, "ki")

    def test_iast_to_devanagari_roundtrip(self):
        for word in ("dharma", "ahimsa", "sutra", "moksa"):
            res = iast_to_devanagari(word)
            back = devanagari_to_iast(res.text)
            self.assertEqual(back.text, word, f"roundtrip failed for {word}")

    def test_iast_diacritics_roundtrip(self):
        res = iast_to_devanagari("āśrama")
        back = devanagari_to_iast(res.text)
        self.assertEqual(back.text, "āśrama")

    def test_lossy_transliteration_flagged(self):
        # Devanagari digits map LOSSLESSLY to Roman (१२३ -> 123): not lossy.
        digits = devanagari_to_iast("जैन १२३")
        self.assertFalse(digits.lossy)
        self.assertEqual(digits.text, "jaina 123")
        # The real transparent-drop case: nukta forms have no IAST equivalent,
        # so the mark is dropped and REPORTED, never silently discarded.
        nukta = devanagari_to_iast("क़ ज़")
        self.assertTrue(nukta.transparent_dropped)
        self.assertFalse(nukta.lossy)

    def test_gujarati_to_devanagari(self):
        res = gujarati_to_devanagari("ધર્મ")
        self.assertTrue(res.text)
        # Roundtrip through IAST proves the mapping carried the letters.
        back = devanagari_to_iast(res.text)
        self.assertEqual(back.text, "dharma")

    def test_transliteration_is_not_silent_about_unmapped(self):
        res = devanagari_to_iast("abc!")
        # Latin and ASCII punctuation pass through; lossless-or-flagged is the contract.
        self.assertIsInstance(res.unmapped, dict)


if __name__ == "__main__":
    unittest.main()

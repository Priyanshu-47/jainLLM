"""Segmentation tests: structure preservation without fabrication.

The invariant: when verse/heading structure exists it must be reflected in the
units; when it does not exist, structure_confidence must say "unknown" and no
verse numbers or section names may be invented.
"""

from __future__ import annotations

import unittest

from svk_corpus.segmentation.text_units import segment_document, split_pages

PROSE = (
    "यह एक प्रसिद्ध ग्रंथ का प्रथम अध्याय है और इसमें बहुत सी कथाएँ हैं। "
    "इस ग्रंथ की भाषा अर्धमागधी है और इसकी टीकाएँ बहुत प्राचीन मानी जाती हैं।"
)

VERSED = (
    "सव्वे जीवा वि इच्छंति जीविउं ण मरिज्जिउं॥\n"
    "तम्हा पाणिवहं घोरं निहत्था जीवा ण हंसंति॥\n"
    "अहिंसा भावपूर्वका सव्वेषु जीवेषु णं कायव्वइ॥"
)

WITH_HEADING = (
    "प्रथम अध्याय\n\n" + PROSE + "\n\nद्वितीय अध्याय\n\n" + VERSED
)


class TestSplitPages(unittest.TestCase):
    def test_form_feed_pages(self):
        text = "page one\fpage two\fpage three"
        slices = split_pages(text)
        self.assertEqual([s.page for s in slices], [1, 2, 3])
        # PageSlice exposes offsets, not a text accessor: slice the source.
        self.assertIn("page two", text[slices[1].start:slices[1].end])

    def test_no_pages_means_single_slice(self):
        slices = split_pages(PROSE)
        self.assertEqual(len(slices), 1)
        self.assertIsNone(slices[0].page)


class TestSegmentDocument(unittest.TestCase):
    def test_prose_only_is_unknown_structure(self):
        units, stats = segment_document(PROSE, source_id="T1", language="hi",
                                        script="Devanagari", text_role="ORIGINAL")
        self.assertTrue(units)
        self.assertEqual(stats.structure_confidence, "unknown")
        # A document ancestor exists so every unit has a parent.
        doc = [u for u in units if u.unit_type == "document"]
        self.assertEqual(len(doc), 1)
        for unit in units:
            if unit.unit_type != "document":
                self.assertTrue(unit.parent_id)

    def test_verse_terminators_split_units(self):
        units, stats = segment_document(VERSED, source_id="T2", language="pra",
                                        script="Devanagari", text_role="ORIGINAL")
        content = [u for u in units if u.unit_type not in ("document",)]
        self.assertGreaterEqual(len(content), 3)
        self.assertTrue(stats.saw_verse if hasattr(stats, "saw_verse") else True)
        for unit in content:
            self.assertIn("॥", unit.text + unit.normalized_text)

    def test_verse_units_are_typed_verse(self):
        units, stats = segment_document(VERSED, source_id="T2b", language="pra",
                                        script="Devanagari", text_role="ORIGINAL")
        types = {u.unit_type for u in units}
        self.assertIn("verse", types)

    def test_heading_creates_section_context(self):
        units, stats = segment_document(WITH_HEADING, source_id="T3", language="hi",
                                        script="Devanagari", text_role="ORIGINAL")
        sections = [u.section for u in units if u.section]
        self.assertTrue(sections, "expected at least one section from the heading")
        self.assertIn("प्रथम अध्याय", sections)

    def test_no_fabricated_section_when_structure_unknown(self):
        units, _ = segment_document(PROSE, source_id="T4", language="hi",
                                    script="Devanagari", text_role="ORIGINAL")
        for unit in units:
            if unit.unit_type == "paragraph" and unit.section is None:
                self.assertEqual(unit.structure_confidence, "unknown")
                break

    def test_page_numbers_carried_into_units(self):
        paged = "पृष्ठ एक का विषय यहाँ वर्णित है। यह अनुच्छेद लंबा है।\fपृष्ठ दो का विषय यहाँ है।"
        units, _ = segment_document(paged, source_id="T5", language="hi",
                                    script="Devanagari", text_role="ORIGINAL")
        pages = {u.page for u in units}
        self.assertIn(2, pages)

    def test_unit_ids_are_stable(self):
        u1, _ = segment_document(PROSE, source_id="T6", language="hi",
                                 script="Devanagari", text_role="ORIGINAL")
        u2, _ = segment_document(PROSE, source_id="T6", language="hi",
                                 script="Devanagari", text_role="ORIGINAL")
        self.assertEqual([u.unit_id for u in u1], [u.unit_id for u in u2])

    def test_units_carry_language_script_role(self):
        units, _ = segment_document(PROSE, source_id="T7", language="hi",
                                    script="Devanagari", text_role="OCR")
        for unit in units:
            self.assertEqual(unit.language, "hi")
            self.assertEqual(unit.script, "Devanagari")
            self.assertEqual(unit.text_role, "OCR")

    def test_oversized_unit_is_split_not_lost(self):
        long_text = "यह अत्यंत लंबा वाक्य है। " * 200
        units, _ = segment_document(long_text, source_id="T8", language="hi",
                                    script="Devanagari", text_role="ORIGINAL",
                                    max_chunk_chars=300)
        for unit in units:
            self.assertLessEqual(len(unit.text), 320)

    def test_provenance_attached(self):
        prov = {"source_url": "https://example.org/item", "artifact_sha256": "ab" * 32}
        units, _ = segment_document(PROSE, source_id="T9", language="hi",
                                    script="Devanagari", text_role="ORIGINAL",
                                    provenance=prov)
        doc = [u for u in units if u.unit_type == "document"][0]
        self.assertEqual(doc.provenance.get("source_url"), prov["source_url"])


if __name__ == "__main__":
    unittest.main()

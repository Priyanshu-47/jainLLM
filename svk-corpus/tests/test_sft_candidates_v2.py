"""Tests for SFT candidate passage extraction v2 (strict eligibility)."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from svk_corpus.training.sft_candidates_v2 import (
    CandidatePassage,
    SourceMeta,
    _assess_quality_strict,
    _compute_priority_rank,
    _detect_categories_strict,
    _is_excluded,
    compute_statistics,
    extract_candidates,
    load_source_metadata,
    write_candidates,
)


class TestStrictCategoryDetection(unittest.TestCase):
    """Verify passage-level evidence requirements."""

    def test_source_author_does_not_produce_teacher_attribution(self):
        """Source-level author metadata alone does NOT create TEACHER_ATTRIBUTION."""
        meta = SourceMeta(source_id="SVK-TEST", author="Manakmuni Maharaj")
        # A generic passage from this source should NOT get teacher attribution
        cats, reason, evidence = _detect_categories_strict(
            "This is a generic passage about Jain philosophy.", meta
        )
        self.assertNotIn("TEACHER_ATTRIBUTION", cats)

    def test_explicit_attribution_produces_teacher_attribution(self):
        """Passage with explicit attribution DOES create TEACHER_ATTRIBUTION."""
        meta = SourceMeta(source_id="SVK-TEST")
        cats, reason, evidence = _detect_categories_strict(
            "आचार्य मनकमुनि कहते हैं कि धर्म का अर्थ है", meta
        )
        self.assertIn("TEACHER_ATTRIBUTION", cats)

    def test_hindi_language_alone_does_not_produce_multilingual(self):
        """Hindi language alone does NOT create MULTILINGUAL_MAPPING."""
        meta = SourceMeta(source_id="SVK-TEST", language="hi")
        cats, reason, evidence = _detect_categories_strict(
            "यह एक हिंदी पाठ है जो जैन दर्शन के बारे में है।", meta
        )
        self.assertNotIn("MULTILINGUAL_MAPPING", cats)

    def test_cross_language_content_produces_multilingual(self):
        """Passage with actual cross-language content DOES create MULTILINGUAL_MAPPING."""
        meta = SourceMeta(source_id="SVK-TEST")
        cats, reason, evidence = _detect_categories_strict(
            "अहिंसा = non-violence, यह जैन धर्म का मूल सिद्धांत है", meta
        )
        self.assertIn("MULTILINGUAL_MAPPING", cats)

    def test_agam_source_alone_does_not_produce_sthanakvasi(self):
        """Source being from an Agam does NOT create STHANAKAVASI_EXPLANATION."""
        meta = SourceMeta(source_id="SVK-2019", agam_id="AGAM-015",
                          knowledge_layer="CANONICAL")
        cats, reason, evidence = _detect_categories_strict(
            "This is a canonical passage about monastic discipline.", meta
        )
        self.assertNotIn("STHANAKAVASI_EXPLANATION", cats)

    def test_sthanakvasi_text_produces_sthanakvasi(self):
        """Passage mentioning Sthanakavasi DOES create STHANAKAVASI_EXPLANATION."""
        meta = SourceMeta(source_id="SVK-TEST")
        cats, reason, evidence = _detect_categories_strict(
            "स्थानकवासी सम्प्रदाय में यह परम्परा महत्वपूर्ण है", meta
        )
        self.assertIn("STHANAKAVASI_EXPLANATION", cats)

    def test_pratikraman_mention_alone_does_not_produce_practice(self):
        """Mere mention of 'Pratikraman' does NOT create PRACTICE_PRATIKRAMAN."""
        meta = SourceMeta(source_id="SVK-TEST")
        cats, reason, evidence = _detect_categories_strict(
            "प्रतिक्रमण एक महत्वपूर्ण अनुष्ठान है।", meta
        )
        # Just mentioning the word is not enough — needs explanation pattern
        self.assertNotIn("PRACTICE_PRATIKRAMAN", cats)

    def test_pratikraman_explanation_produces_practice(self):
        """Passage explaining Pratikraman DOES create PRACTICE_PRATIKRAMAN."""
        meta = SourceMeta(source_id="SVK-TEST")
        cats, reason, evidence = _detect_categories_strict(
            "प्रतिक्रमण कर्म का विधि यह है कि साधक को अपने पापों का प्रायश्चित्त करना चाहिए",
            meta
        )
        self.assertIn("PRACTICE_PRATIKRAMAN", cats)

    def test_dictionary_fragment_excluded(self):
        """Dictionary fragment without explanation is excluded."""
        meta = SourceMeta(source_id="SVK-TEST", knowledge_layer="LEXICON")
        cats, reason, evidence = _detect_categories_strict(
            "अहिंसा", meta
        )
        # Single word without explanation should be excluded
        self.assertIn("EXCLUDED", cats)

    def test_coherent_term_explanation_produces_lexicon_reference(self):
        """Coherent term + explanation produces LEXICON_REFERENCE."""
        meta = SourceMeta(source_id="SVK-TEST", knowledge_layer="LEXICON")
        cats, reason, evidence = _detect_categories_strict(
            "अहिंसा = किसी भी प्राणी को हानि न पहुँचाने का सिद्धांत है", meta
        )
        self.assertIn("LEXICON_REFERENCE", cats)
        # PRAKRIT_SANSKIRT_TERM is skipped when LEXICON_REFERENCE is present
        self.assertNotIn("PRAKRIT_SANSKIRT_TERM", cats)

    def test_ocr_noisy_text_review_required(self):
        """OCR-noisy text gets REVIEW_REQUIRED quality."""
        q = _assess_quality_strict("This is a long enough passage for testing.", ["OCR_NOISE_HIGH"])
        self.assertEqual(q, "REVIEW_REQUIRED")

    def test_provenance_preserved(self):
        """Every candidate retains full provenance via source metadata."""
        meta = SourceMeta(source_id="SVK-2019", agam_id="AGAM-015")
        # Text must be >= 40 chars to pass minimum quality gate
        cats, reason, evidence = _detect_categories_strict(
            "कल्प सूत्र में वर्णित नियमों के अनुसार यह नियम बहुत महत्वपूर्ण है।", meta
        )
        # Provenance is preserved in candidate record fields (source_id, agam_id)
        self.assertIn("AGAM_GROUNDED", cats)
        self.assertIn("source_agam_id", evidence)


class TestExclusion(unittest.TestCase):
    """Exclusion rules."""

    def test_short_text_excluded(self):
        excluded, reason = _is_excluded(["EXCLUDED"], "hi", [])
        self.assertTrue(excluded)

    def test_good_text_not_excluded(self):
        excluded, reason = _is_excluded(
            ["GENERAL_JAIN_CONTENT"],
            "This is a substantial passage about Jain philosophy and practice.",
            []
        )
        self.assertFalse(excluded)


class TestV2Extraction(unittest.TestCase):
    """End-to-end v2 extraction tests."""

    def test_candidate_file_exists(self):
        path = Path(__file__).parent.parent / "data" / "training" / "sft_candidate_passages_v2.jsonl"
        self.assertTrue(path.is_file(), "v2 candidate file not found")

    def test_candidate_fields(self):
        path = Path(__file__).parent.parent / "data" / "training" / "sft_candidate_passages_v2.jsonl"
        if not path.is_file():
            self.skipTest("v2 candidate file not yet generated")
        with path.open(encoding="utf-8") as f:
            first = json.loads(f.readline())
        required = [
            "candidate_id", "source_id", "text_id", "text", "title",
            "locator", "language", "script", "tradition",
            "religious_scope", "knowledge_layer", "content_role",
            "canonical_status", "teacher_or_author", "lineage",
            "source_quality", "candidate_categories", "candidate_reason",
            "evidence_fields", "quality_flags", "rights_status",
            "verification_status", "sft_status", "text_length",
        ]
        for field in required:
            self.assertIn(field, first, f"Missing required field: {field}")

    def test_sft_status_always_candidate(self):
        path = Path(__file__).parent.parent / "data" / "training" / "sft_candidate_passages_v2.jsonl"
        if not path.is_file():
            self.skipTest("v2 candidate file not yet generated")
        with path.open(encoding="utf-8") as f:
            for i, line in enumerate(f):
                r = json.loads(line)
                self.assertEqual(r["sft_status"], "CANDIDATE",
                                 f"Line {i}: sft_status must be CANDIDATE")
                if i > 500:
                    break

    def test_candidate_categories_non_empty(self):
        path = Path(__file__).parent.parent / "data" / "training" / "sft_candidate_passages_v2.jsonl"
        if not path.is_file():
            self.skipTest("v2 candidate file not yet generated")
        with path.open(encoding="utf-8") as f:
            for i, line in enumerate(f):
                r = json.loads(line)
                self.assertIsInstance(r["candidate_categories"], list)
                self.assertGreater(len(r["candidate_categories"]), 0)
                if i > 500:
                    break

    def test_v2_fewer_candidates_than_v1(self):
        """v2 should produce significantly fewer candidates than v1."""
        v1_path = Path(__file__).parent.parent / "data" / "training" / "sft_candidate_passages_v1.jsonl"
        v2_path = Path(__file__).parent.parent / "data" / "training" / "sft_candidate_passages_v2.jsonl"
        if not v1_path.is_file() or not v2_path.is_file():
            self.skipTest("Both v1 and v2 candidate files needed")
        v1_count = sum(1 for _ in v1_path.open(encoding="utf-8"))
        v2_count = sum(1 for _ in v2_path.open(encoding="utf-8"))
        self.assertLess(v2_count, v1_count, "v2 should have fewer candidates than v1")
        self.assertLess(v2_count, v1_count * 0.7, "v2 should have at least 30% fewer candidates")


class TestTeacherAttributionStrict(unittest.TestCase):
    """Verify teacher attribution is strict."""

    def test_no_teacher_attribution_from_metadata(self):
        """Source author metadata does NOT produce teacher attribution."""
        path = Path(__file__).parent.parent / "data" / "training" / "sft_candidate_passages_v2.jsonl"
        if not path.is_file():
            self.skipTest("v2 candidate file not yet generated")
        # Count TEACHER_ATTRIBUTION candidates
        teacher_count = 0
        total = 0
        with path.open(encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                total += 1
                if "TEACHER_ATTRIBUTION" in r.get("candidate_categories", []):
                    teacher_count += 1
        # Should be much less than total
        self.assertLess(teacher_count, total * 0.1,
                        f"Teacher attribution {teacher_count}/{total} should be <10%")

    def test_multilingual_not_from_language_label(self):
        """Multilingual mapping requires actual cross-language content."""
        path = Path(__file__).parent.parent / "data" / "training" / "sft_candidate_passages_v2.jsonl"
        if not path.is_file():
            self.skipTest("v2 candidate file not yet generated")
        ml_count = 0
        total = 0
        with path.open(encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                total += 1
                if "MULTILINGUAL_MAPPING" in r.get("candidate_categories", []):
                    ml_count += 1
        # Should be significantly less than total
        self.assertLess(ml_count, total * 0.6,
                        f"Multilingual mapping {ml_count}/{total} should be <60%")


if __name__ == "__main__":
    unittest.main()

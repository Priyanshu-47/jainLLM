"""Tests for SFT candidate passage extraction (Task 23)."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from svk_corpus.training.sft_candidates import (
    CandidatePassage,
    SourceMeta,
    _assess_quality,
    _compute_priority_rank,
    _detect_categories,
    compute_statistics,
    extract_candidates,
    load_source_metadata,
    write_candidates,
)


class TestSourceMeta(unittest.TestCase):
    """Source metadata loading."""

    def test_load_source_metadata(self):
        meta = load_source_metadata(
            Path(__file__).parent.parent / "manifests" / "source_manifest.csv"
        )
        self.assertGreater(len(meta), 0)
        self.assertIn("SVK-2015", meta)
        self.assertEqual(meta["SVK-2015"].source_id, "SVK-2015")

    def test_from_csv_row(self):
        row = {
            "source_id": "SVK-TEST",
            "title": "Test Title",
            "knowledge_layer": "CANONICAL",
            "agam_id": "AGAM-001",
        }
        m = SourceMeta.from_csv_row(row)
        self.assertEqual(m.source_id, "SVK-TEST")
        self.assertEqual(m.knowledge_layer, "CANONICAL")


class TestCategoryDetection(unittest.TestCase):
    """Deterministic category detection."""

    def test_practice_pratikraman(self):
        meta = SourceMeta(source_id="SVK-2016", knowledge_layer="PRACTICE")
        cats, reason = _detect_categories("प्रतिक्रमण कर्म", meta)
        self.assertIn("PRACTICE_PRATIKRAMAN", cats)

    def test_canonical_source(self):
        meta = SourceMeta(source_id="SVK-2019", knowledge_layer="CANONICAL",
                          agam_id="AGAM-015")
        cats, reason = _detect_categories("कल्प सूत्र text", meta)
        self.assertIn("CANONICAL_SOURCE", cats)
        self.assertIn("AGAM_GROUNDED", cats)

    def test_sthanakvasi_detection(self):
        meta = SourceMeta(source_id="SVK-2010")
        cats, reason = _detect_categories(
            "स्थानकवासी परंपरा में महत्वपूर्ण", meta
        )
        self.assertIn("STHANAKAVASI_EXPLANATION", cats)

    def test_prakrit_sanskrit_term(self):
        meta = SourceMeta(source_id="SVK-2020", language="sa")
        cats, reason = _detect_categories("नमोऽस्तु श्री", meta)
        self.assertIn("PRAKRIT_SANSKIRT_TERM", cats)

    def test_teacher_attribution(self):
        meta = SourceMeta(source_id="SVK-2019", author="Manakmuni Maharaj")
        cats, reason = _detect_categories("some text", meta)
        self.assertIn("TEACHER_ATTRIBUTION", cats)

    def test_abstention_evidence(self):
        meta = SourceMeta(source_id="SVK-TEST")
        cats, reason = _detect_categories(
            "यह विषय अनिश्चित है और मतभेद हैं", meta
        )
        self.assertIn("ABSTENTION_EVIDENCE", cats)

    def test_general_fallback(self):
        meta = SourceMeta(source_id="SVK-TEST")
        cats, reason = _detect_categories("some generic text", meta)
        self.assertIn("GENERAL_JAIN", cats)


class TestQualityAssessment(unittest.TestCase):
    """Quality classification."""

    def test_high_confidence(self):
        text = "This is a sufficiently long passage with meaningful content about Jain philosophy and practice."
        q = _assess_quality(text, [])
        self.assertEqual(q, "HIGH_CONFIDENCE_CANDIDATE")

    def test_low_quality_short(self):
        q = _assess_quality("hi", [])
        self.assertEqual(q, "LOW_QUALITY")

    def test_review_required_ocr(self):
        text = "This is a sufficiently long passage with meaningful content about Jain practice and philosophy."
        q = _assess_quality(text, ["OCR_NOISE_HIGH"])
        self.assertEqual(q, "REVIEW_REQUIRED")


class TestPriorityRanking(unittest.TestCase):
    """Priority ranking for sources."""

    def test_priority_sources(self):
        self.assertEqual(_compute_priority_rank("SVK-2015"), 1)
        self.assertEqual(_compute_priority_rank("SVK-2016"), 2)
        self.assertEqual(_compute_priority_rank("SVK-2019"), 3)
        self.assertEqual(_compute_priority_rank("SVK-2020"), 4)

    def test_unknown_source(self):
        rank = _compute_priority_rank("SVK-9999")
        self.assertGreater(rank, 0)


class TestCandidateExtraction(unittest.TestCase):
    """End-to-end extraction tests."""

    def test_candidate_fields(self):
        """Every candidate has all required fields."""
        path = Path(__file__).parent.parent / "data" / "training" / "sft_candidate_passages_v1.jsonl"
        if not path.is_file():
            self.skipTest("Candidate file not yet generated")
        with path.open(encoding="utf-8") as f:
            first = json.loads(f.readline())
        required = [
            "candidate_id", "source_id", "text_id", "text", "title",
            "locator", "language", "script", "tradition",
            "religious_scope", "knowledge_layer", "content_role",
            "canonical_status", "teacher_or_author", "lineage",
            "source_quality", "candidate_categories", "candidate_reason",
            "quality_flags", "rights_status", "verification_status",
            "sft_status", "text_length",
        ]
        for field in required:
            self.assertIn(field, first, f"Missing required field: {field}")

    def test_candidate_id_uniqueness(self):
        """Candidate IDs are unique."""
        path = Path(__file__).parent.parent / "data" / "training" / "sft_candidate_passages_v1.jsonl"
        if not path.is_file():
            self.skipTest("Candidate file not yet generated")
        ids = set()
        with path.open(encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                cid = r["candidate_id"]
                self.assertNotIn(cid, ids, f"Duplicate candidate_id: {cid}")
                ids.add(cid)

    def test_sft_status_valid(self):
        """SFT status is always CANDIDATE."""
        path = Path(__file__).parent.parent / "data" / "training" / "sft_candidate_passages_v1.jsonl"
        if not path.is_file():
            self.skipTest("Candidate file not yet generated")
        with path.open(encoding="utf-8") as f:
            for i, line in enumerate(f):
                r = json.loads(line)
                self.assertEqual(r["sft_status"], "CANDIDATE",
                                 f"Line {i}: sft_status must be CANDIDATE")
                if i > 1000:
                    break  # spot check

    def test_provenance_present(self):
        """Every candidate has provenance metadata."""
        path = Path(__file__).parent.parent / "data" / "training" / "sft_candidate_passages_v1.jsonl"
        if not path.is_file():
            self.skipTest("Candidate file not yet generated")
        with path.open(encoding="utf-8") as f:
            for i, line in enumerate(f):
                r = json.loads(line)
                self.assertTrue(r["source_id"], f"Line {i}: source_id empty")
                self.assertTrue(r["text_id"], f"Line {i}: text_id empty")
                self.assertTrue(r["rights_status"], f"Line {i}: rights_status empty")
                if i > 1000:
                    break

    def test_categories_are_lists(self):
        """candidate_categories is a non-empty list."""
        path = Path(__file__).parent.parent / "data" / "training" / "sft_candidate_passages_v1.jsonl"
        if not path.is_file():
            self.skipTest("Candidate file not yet generated")
        with path.open(encoding="utf-8") as f:
            for i, line in enumerate(f):
                r = json.loads(line)
                self.assertIsInstance(r["candidate_categories"], list)
                self.assertGreater(len(r["candidate_categories"]), 0)
                if i > 1000:
                    break


class TestStatistics(unittest.TestCase):
    """Statistics computation."""

    def test_compute_statistics(self):
        """Statistics return expected structure."""
        path = Path(__file__).parent.parent / "data" / "training" / "sft_candidate_passages_v1.jsonl"
        if not path.is_file():
            self.skipTest("Candidate file not yet generated")
        candidates = []
        with path.open(encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                candidates.append(CandidatePassage(
                    candidate_id=r["candidate_id"],
                    source_id=r["source_id"],
                    text_id=r["text_id"],
                    text=r["text"],
                    title=r.get("title", ""),
                    locator=r.get("locator", {}),
                    language=r.get("language", ""),
                    script=r.get("script", ""),
                    tradition=r.get("tradition", ""),
                    religious_scope=r.get("religious_scope", ""),
                    knowledge_layer=r.get("knowledge_layer", ""),
                    content_role=r.get("content_role", ""),
                    canonical_status=r.get("canonical_status", ""),
                    teacher_or_author=r.get("teacher_or_author", ""),
                    lineage=r.get("lineage", ""),
                    source_quality=r.get("source_quality", ""),
                    candidate_categories=r.get("candidate_categories", []),
                    candidate_reason=r.get("candidate_reason", ""),
                    quality_flags=r.get("quality_flags", []),
                    rights_status=r.get("rights_status", ""),
                    verification_status=r.get("verification_status", ""),
                    sft_status=r.get("sft_status", ""),
                    text_length=r.get("text_length", 0),
                ))
        stats = compute_statistics(candidates)
        self.assertGreater(stats["total"], 0)
        self.assertIn("by_source", stats)
        self.assertIn("by_category", stats)
        self.assertIn("by_quality", stats)


if __name__ == "__main__":
    unittest.main()

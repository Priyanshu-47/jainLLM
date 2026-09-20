"""Tests for the Retrieval Evidence Contract (Task 14).

Scope: canonical result creation, channel validation, BM25 evidence,
metadata evidence, metadata-to-unit expansion, provenance preservation,
normalization evidence, unavailable dense channel, missing metadata,
invalid/malformed results.

The corpus used here is synthetic and tiny; these tests never touch the
release files.
"""

from __future__ import annotations

import unittest

from svk_corpus.retrieval.contract import (
    CanonicalResult,
    ContractViolation,
    MetadataMatchEvidence,
    NormalizationEvidence,
    RetrievalChannel,
    assert_valid,
    validate_batch,
    validate_result,
)


def _bm25_result(result_id: str = "u1", source_id: str = "SVK-0007",
                 text: str = "test text", **over) -> CanonicalResult:
    """Create a valid unit_bm25 result for testing."""
    base = dict(
        result_id=result_id,
        source_id=source_id,
        text=text,
        title=f"Title {source_id}",
        retrieval_channel=RetrievalChannel.UNIT_BM25,
        retrieval_rank=1,
        retrieval_score=4.2,
        unit_bm25_rank=1,
        unit_bm25_score=4.2,
    )
    base.update(over)
    return CanonicalResult(**base)


def _metadata_result(result_id: str = "u1", source_id: str = "SVK-2005",
                     text: str = "representative unit text", **over) -> CanonicalResult:
    """Create a valid source_metadata result for testing."""
    match = MetadataMatchEvidence(
        source_id=source_id,
        matched_field="author",
        matched_value="Muni Ratnachandraji",
        matched_token="ratnachandraji",
        weight=3.0,
    )
    base = dict(
        result_id=result_id,
        source_id=source_id,
        text=text,
        title=f"Title {source_id}",
        retrieval_channel=RetrievalChannel.SOURCE_METADATA,
        retrieval_rank=10,
        retrieval_score=0.0,
        metadata_match=match,
    )
    base.update(over)
    return CanonicalResult(**base)


def _expansion_result(result_id: str = "u1", source_id: str = "SVK-2002",
                      text: str = "woolner unit text", **over) -> CanonicalResult:
    """Create a valid source_metadata_expansion result for testing."""
    match = MetadataMatchEvidence(
        source_id=source_id,
        matched_field="author",
        matched_value="A. C. Woolner",
        matched_token="woolner",
        weight=3.0,
        via_family=True,
        family_root="SVK-0007",
    )
    base = dict(
        result_id=result_id,
        source_id=source_id,
        text=text,
        title=f"Title {source_id}",
        retrieval_channel=RetrievalChannel.SOURCE_METADATA_EXPANSION,
        retrieval_rank=11,
        retrieval_score=0.0,
        metadata_match=match,
    )
    base.update(over)
    return CanonicalResult(**base)


class TestCanonicalResultCreation(unittest.TestCase):
    """Verify CanonicalResult can be created with required fields."""

    def test_bm25_result_creation(self):
        r = _bm25_result()
        self.assertEqual(r.result_id, "u1")
        self.assertEqual(r.source_id, "SVK-0007")
        self.assertEqual(r.retrieval_channel, RetrievalChannel.UNIT_BM25)
        self.assertEqual(r.unit_bm25_rank, 1)
        self.assertEqual(r.unit_bm25_score, 4.2)

    def test_metadata_result_creation(self):
        r = _metadata_result()
        self.assertEqual(r.retrieval_channel, RetrievalChannel.SOURCE_METADATA)
        self.assertIsNotNone(r.metadata_match)
        self.assertEqual(r.metadata_match.source_id, "SVK-2005")

    def test_expansion_result_creation(self):
        r = _expansion_result()
        self.assertEqual(r.retrieval_channel, RetrievalChannel.SOURCE_METADATA_EXPANSION)
        self.assertTrue(r.metadata_match.via_family)

    def test_provenance_export(self):
        r = _bm25_result()
        prov = r.provenance()
        self.assertIn("source_id", prov)
        self.assertIn("retrieval_channel", prov)
        self.assertEqual(prov["retrieval_channel"], "unit_bm25")


class TestChannelValidation(unittest.TestCase):
    """Validate channel-specific constraints."""

    def test_bm25_result_valid(self):
        r = _bm25_result()
        violations = validate_result(r)
        self.assertEqual(violations, [])

    def test_metadata_result_valid(self):
        r = _metadata_result()
        violations = validate_result(r)
        self.assertEqual(violations, [])

    def test_expansion_result_valid(self):
        r = _expansion_result()
        violations = validate_result(r)
        self.assertEqual(violations, [])

    def test_bm25_missing_rank(self):
        r = _bm25_result(unit_bm25_rank=None)
        violations = validate_result(r)
        self.assertTrue(any("unit_bm25_rank" in v for v in violations))

    def test_bm25_missing_score(self):
        r = _bm25_result(unit_bm25_score=None)
        violations = validate_result(r)
        self.assertTrue(any("unit_bm25_score" in v for v in violations))

    def test_bm25_with_metadata_match_is_invalid(self):
        match = MetadataMatchEvidence(
            source_id="SVK-0007", matched_field="author",
            matched_value="test", matched_token="test", weight=1.0
        )
        r = _bm25_result(metadata_match=match)
        violations = validate_result(r)
        self.assertTrue(any("should not have metadata_match" in v for v in violations))

    def test_metadata_result_missing_metadata_match(self):
        r = _metadata_result(metadata_match=None)
        violations = validate_result(r)
        self.assertTrue(any("missing metadata_match" in v for v in violations))

    def test_metadata_result_with_bm25_rank_is_invalid(self):
        r = _metadata_result(unit_bm25_rank=1)
        violations = validate_result(r)
        self.assertTrue(any("unit_bm25_rank" in v for v in violations))

    def test_metadata_result_with_bm25_score_is_invalid(self):
        r = _metadata_result(unit_bm25_score=1.0)
        violations = validate_result(r)
        self.assertTrue(any("unit_bm25_score" in v for v in violations))

    def test_dense_result_is_invalid(self):
        r = _bm25_result(retrieval_channel=RetrievalChannel.DENSE)
        violations = validate_result(r)
        self.assertTrue(any("dense" in v and "missing" in v for v in violations))


class TestBM25Evidence(unittest.TestCase):
    """BM25 results must carry textual retrieval evidence."""

    def test_bm25_evidence_present(self):
        r = _bm25_result(unit_bm25_rank=3, unit_bm25_score=2.5)
        self.assertEqual(r.unit_bm25_rank, 3)
        self.assertEqual(r.unit_bm25_score, 2.5)
        self.assertIsNone(r.metadata_match)

    def test_bm25_no_metadata_evidence(self):
        r = _bm25_result()
        self.assertIsNone(r.metadata_match)


class TestMetadataEvidence(unittest.TestCase):
    """Source metadata results must carry metadata match evidence."""

    def test_metadata_evidence_present(self):
        r = _metadata_result()
        self.assertIsNotNone(r.metadata_match)
        self.assertEqual(r.metadata_match.matched_field, "author")
        self.assertEqual(r.metadata_match.matched_token, "ratnachandraji")

    def test_metadata_no_bm25_evidence(self):
        r = _metadata_result()
        self.assertIsNone(r.unit_bm25_rank)
        self.assertIsNone(r.unit_bm25_score)


class TestExpansionEvidence(unittest.TestCase):
    """Source metadata expansion results must be labelled correctly."""

    def test_expansion_channel(self):
        r = _expansion_result()
        self.assertEqual(r.retrieval_channel, RetrievalChannel.SOURCE_METADATA_EXPANSION)

    def test_expansion_via_family(self):
        r = _expansion_result()
        self.assertTrue(r.metadata_match.via_family)
        self.assertEqual(r.metadata_match.family_root, "SVK-0007")


class TestProvenancePreservation(unittest.TestCase):
    """Provenance fields must be preserved and not mixed with authority."""

    def test_religious_scope_preserved(self):
        r = _bm25_result(religious_scope="CORE_STHANAKAVASI")
        self.assertEqual(r.religious_scope, "CORE_STHANAKAVASI")

    def test_knowledge_layer_preserved(self):
        r = _bm25_result(knowledge_layer="LEXICON")
        self.assertEqual(r.knowledge_layer, "LEXICON")

    def test_teacher_or_author_preserved(self):
        r = _bm25_result(teacher_or_author="Muni Ratnachandra")
        self.assertEqual(r.teacher_or_author, "Muni Ratnachandra")


class TestNormalizationEvidence(unittest.TestCase):
    """Normalization evidence is optional but must be accurate when present."""

    def test_normalization_optional(self):
        r = _bm25_result()
        self.assertIsNone(r.normalization)

    def test_normalization_recorded(self):
        norm = NormalizationEvidence(
            original_query="Sutrakritanga",
            normalized_tokens=("sutrakritanga", "sutrakrtanga"),
            aliases_applied=("sutrakritanga",),
        )
        r = _bm25_result(normalization=norm)
        self.assertEqual(r.normalization.original_query, "Sutrakritanga")
        self.assertIn("sutrakrtanga", r.normalization.normalized_tokens)


class TestDenseChannelValidation(unittest.TestCase):
    """Dense channel is a real channel (Task 16) with its own evidence fields."""

    def test_dense_result_missing_rank(self):
        r = CanonicalResult(
            result_id="d1", source_id="SVK-0007", text="test text", title="T",
            retrieval_channel=RetrievalChannel.DENSE,
            retrieval_rank=1, retrieval_score=0.8,
            dense_score=0.8, dense_rank=None,
        )
        violations = validate_result(r)
        self.assertTrue(any("dense_rank" in v for v in violations))

    def test_dense_result_missing_score(self):
        r = CanonicalResult(
            result_id="d1", source_id="SVK-0007", text="test text", title="T",
            retrieval_channel=RetrievalChannel.DENSE,
            retrieval_rank=1, retrieval_score=0.8,
            dense_rank=1, dense_score=None,
        )
        violations = validate_result(r)
        self.assertTrue(any("dense_score" in v for v in violations))

    def test_dense_result_with_bm25_rank_is_invalid(self):
        r = CanonicalResult(
            result_id="d1", source_id="SVK-0007", text="test text", title="T",
            retrieval_channel=RetrievalChannel.DENSE,
            retrieval_rank=1, retrieval_score=0.8,
            dense_rank=1, dense_score=0.8,
            unit_bm25_rank=1,
        )
        violations = validate_result(r)
        self.assertTrue(any("unit_bm25_rank" in v and "dense" in v for v in violations))

    def test_dense_result_valid(self):
        r = CanonicalResult(
            result_id="d1", source_id="SVK-0007", text="test text", title="T",
            retrieval_channel=RetrievalChannel.DENSE,
            retrieval_rank=1, retrieval_score=0.8,
            dense_rank=1, dense_score=0.8,
        )
        violations = validate_result(r)
        self.assertEqual(violations, [])

    def test_dense_in_available_channels(self):
        self.assertIn(RetrievalChannel.DENSE.value,
                      RetrievalChannel.available_channels())

    def test_dense_not_in_reserved_channels(self):
        self.assertNotIn(RetrievalChannel.DENSE.value,
                         RetrievalChannel.reserved_channels())


class TestMissingMetadata(unittest.TestCase):
    """Results with missing/empty optional fields should still validate."""

    def test_missing_parent_source_id(self):
        r = _bm25_result(parent_source_id="")
        violations = validate_result(r)
        self.assertEqual(violations, [])

    def test_missing_religious_scope(self):
        r = _bm25_result(religious_scope="UNKNOWN")
        violations = validate_result(r)
        self.assertEqual(violations, [])


class TestInvalidMalformedResults(unittest.TestCase):
    """Malformed results must be caught by validation."""

    def test_missing_source_id(self):
        r = _bm25_result(source_id="")
        violations = validate_result(r)
        self.assertTrue(any("source_id" in v for v in violations))

    def test_missing_result_id(self):
        r = _bm25_result(result_id="")
        violations = validate_result(r)
        self.assertTrue(any("result_id" in v for v in violations))

    def test_empty_text_in_bm25_result(self):
        r = _bm25_result(text="")
        violations = validate_result(r)
        self.assertTrue(any("empty text" in v for v in violations))

    def test_batch_validation(self):
        results = [_bm25_result("u1"), _bm25_result("u2")]
        violations = validate_batch(results)
        self.assertEqual(violations, {})

    def test_batch_with_violations(self):
        results = [_bm25_result("u1"), _bm25_result("u2", source_id="")]
        violations = validate_batch(results)
        self.assertIn("u2", violations)


class TestAssertValid(unittest.TestCase):
    """assert_valid raises ContractViolation on invalid results."""

    def test_valid_result_no_raise(self):
        r = _bm25_result()
        assert_valid(r)  # Should not raise

    def test_invalid_result_raises(self):
        r = _bm25_result(retrieval_channel=RetrievalChannel.DENSE)
        with self.assertRaises(ContractViolation):
            assert_valid(r)


if __name__ == "__main__":
    unittest.main()

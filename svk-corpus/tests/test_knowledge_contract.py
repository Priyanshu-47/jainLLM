"""Tests for knowledge architecture contracts (Task 20).

Scope: Ontology vocabularies, Agam inventory validation, source registry
validation, knowledge coverage matrix validation, and critical rules:
- download_available does NOT imply training permission
- sft_candidate requires CLEAR rights
- VERIFIED canonical status requires evidence
"""

from __future__ import annotations

import unittest

from svk_corpus.knowledge import (
    TRADITIONS,
    KNOWLEDGE_LAYERS,
    CONTENT_ROLES,
    PRACTICES,
    CANONICAL_STATUSES,
    RIGHTS_STATUSES,
    VERIFICATION_STATUSES,
    RELIGIOUS_SCOPES,
    PLATFORMS,
    AGAM_GROUPS,
    COVERAGE_STATUSES,
    COVERAGE_CATEGORIES,
    TRADITION_RELEVANCE,
    ENTITY_TYPES,
    RELATIONSHIP_TYPES,
    PRIORITIES,
    ACQUISITION_STATUSES,
    EXPECTED_USES,
    load_ontology,
    load_agam_inventory,
    load_source_registry,
    load_coverage_matrix,
    load_acquisition_queue,
    validate_agam_entry,
    validate_agam_inventory,
    validate_source_entry,
    validate_source_registry,
    validate_coverage_entry,
    validate_coverage_matrix,
    validate_acquisition_candidate,
    validate_acquisition_queue,
    check_no_download_implies_training,
    check_no_unlicensed_verified_canonical,
    check_no_p0_restricted_rights,
    check_no_sft_without_clear_rights,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _valid_agam_entry(**over) -> dict:
    """Create a minimal valid Agam entry."""
    base = {
        "agam_id": "AGAM-099",
        "traditional_name": "Test Agam",
        "alternate_names": [],
        "sequence_number": 99,
        "group": "ANGA",
        "tradition": "MULTI_TRADITION",
        "canonical_status": "CANONICAL",
        "source_id": None,
        "source_basis": None,
        "language": "Prakrit",
        "script": "Devanagari",
        "translation_available": False,
        "commentary_available": False,
        "rights_status": "UNKNOWN",
        "verification_status": "UNKNOWN",
    }
    base.update(over)
    return base


def _valid_source_entry(**over) -> dict:
    """Create a minimal valid source registry entry."""
    base = {
        "source_id": "EXT-0999",
        "title": "Test Source",
        "alternate_titles": [],
        "platform": "JAINQQ",
        "source_url": None,
        "tradition": "UNKNOWN",
        "religious_scope": "UNKNOWN",
        "knowledge_layer": "OTHER",
        "content_role": "OTHER",
        "canonical_status": "UNKNOWN",
        "author": None,
        "commentator": None,
        "editor": None,
        "translator": None,
        "teacher_or_author": None,
        "lineage": None,
        "language": "unknown",
        "script": "unknown",
        "publication_year": None,
        "publisher": None,
        "edition": None,
        "format": "unknown",
        "page_count": None,
        "text_available": False,
        "ocr_available": False,
        "download_available": False,
        "rights_status": "UNKNOWN",
        "license": None,
        "license_evidence_url": None,
        "provenance_notes": None,
        "verification_status": "UNKNOWN",
        "retrieval_candidate": False,
        "sft_candidate": False,
        "notes": None,
    }
    base.update(over)
    return base


def _valid_coverage_entry(**over) -> dict:
    """Create a minimal valid coverage entry."""
    base = {
        "topic_id": "TOPIC-099",
        "topic_name": "Test Topic",
        "category": "PHILOSOPHY",
        "tradition_relevance": "ALL_JAIN",
        "coverage_status": "MISSING",
        "retrieval_ready": False,
        "sft_ready": False,
        "evaluation_ready": False,
        "source_count": 0,
        "external_source_count": 0,
        "notes": None,
    }
    base.update(over)
    return base


# ---------------------------------------------------------------------------
# Ontology tests
# ---------------------------------------------------------------------------

class TestOntologyVocabularies(unittest.TestCase):
    """Validate that ontology vocabularies are complete and consistent."""

    def test_traditions_complete(self):
        self.assertIn("STHANAKAVASI", TRADITIONS)
        self.assertIn("DIGAMBARA", TRADITIONS)
        self.assertIn("UNKNOWN", TRADITIONS)
        self.assertEqual(len(TRADITIONS), 7)

    def test_knowledge_layers_complete(self):
        self.assertIn("CANONICAL", KNOWLEDGE_LAYERS)
        self.assertIn("LEXICON", KNOWLEDGE_LAYERS)
        self.assertEqual(len(KNOWLEDGE_LAYERS), 14)

    def test_content_roles_complete(self):
        self.assertIn("PRIMARY_SCRIPTURE", CONTENT_ROLES)
        self.assertIn("LEXICON", CONTENT_ROLES)
        self.assertEqual(len(CONTENT_ROLES), 12)

    def test_practices_complete(self):
        self.assertIn("SAMAYIK", PRACTICES)
        self.assertIn("CHAUVISANTHO", PRACTICES)
        self.assertEqual(len(PRACTICES), 9)

    def test_canonical_statuses_complete(self):
        self.assertIn("CANONICAL", CANONICAL_STATUSES)
        self.assertIn("UNKNOWN", CANONICAL_STATUSES)
        self.assertEqual(len(CANONICAL_STATUSES), 6)

    def test_rights_statuses_complete(self):
        self.assertIn("CLEAR", RIGHTS_STATUSES)
        self.assertIn("RESTRICTED", RIGHTS_STATUSES)
        self.assertEqual(len(RIGHTS_STATUSES), 5)

    def test_verification_statuses_complete(self):
        self.assertIn("VERIFIED", VERIFICATION_STATUSES)
        self.assertIn("UNKNOWN", VERIFICATION_STATUSES)
        self.assertEqual(len(VERIFICATION_STATUSES), 4)

    def test_religious_scopes_complete(self):
        self.assertIn("CORE_STHANAKAVASI", RELIGIOUS_SCOPES)
        self.assertEqual(len(RELIGIOUS_SCOPES), 5)

    def test_platforms_complete(self):
        self.assertIn("JAINQQ", PLATFORMS)
        self.assertIn("JAINEBOOKS", PLATFORMS)
        self.assertEqual(len(PLATFORMS), 7)

    def test_entity_types_complete(self):
        self.assertIn("AGAM", ENTITY_TYPES)
        self.assertIn("TIRTHANKARA", ENTITY_TYPES)
        self.assertEqual(len(ENTITY_TYPES), 18)

    def test_relationship_types_complete(self):
        self.assertIn("SOURCE_CONTAINS", RELATIONSHIP_TYPES)
        self.assertIn("AGAM_PART_OF_INVENTORY", RELATIONSHIP_TYPES)
        self.assertEqual(len(RELATIONSHIP_TYPES), 11)

    def test_ontology_loads(self):
        onto = load_ontology()
        self.assertEqual(onto["version"], "1.0")
        self.assertIn("traditions", onto)
        self.assertIn("knowledge_layers", onto)
        self.assertIn("entity_types", onto)
        self.assertIn("relationship_types", onto)


# ---------------------------------------------------------------------------
# Agam inventory tests
# ---------------------------------------------------------------------------

class TestAgamInventoryValidation(unittest.TestCase):
    """Validate Agam inventory entries."""

    def test_valid_entry_passes(self):
        entry = _valid_agam_entry()
        violations = validate_agam_entry(entry)
        self.assertEqual(violations, [])

    def test_missing_required_field(self):
        entry = _valid_agam_entry()
        del entry["group"]
        violations = validate_agam_entry(entry)
        self.assertTrue(any("group" in v for v in violations))

    def test_invalid_group(self):
        entry = _valid_agam_entry(group="INVALID")
        violations = validate_agam_entry(entry)
        self.assertTrue(any("group" in v for v in violations))

    def test_invalid_tradition(self):
        entry = _valid_agam_entry(tradition="INVALID")
        violations = validate_agam_entry(entry)
        self.assertTrue(any("tradition" in v for v in violations))

    def test_invalid_canonical_status(self):
        entry = _valid_agam_entry(canonical_status="INVALID")
        violations = validate_agam_entry(entry)
        self.assertTrue(any("canonical_status" in v for v in violations))

    def test_invalid_rights_status(self):
        entry = _valid_agam_entry(rights_status="INVALID")
        violations = validate_agam_entry(entry)
        self.assertTrue(any("rights_status" in v for v in violations))

    def test_invalid_verification_status(self):
        entry = _valid_agam_entry(verification_status="INVALID")
        violations = validate_agam_entry(entry)
        self.assertTrue(any("verification_status" in v for v in violations))

    def test_agam_id_format(self):
        entry = _valid_agam_entry(agam_id="BAD-ID")
        violations = validate_agam_entry(entry)
        self.assertTrue(any("agam_id" in v for v in violations))

    def test_verified_canonical_requires_source_basis(self):
        entry = _valid_agam_entry(
            canonical_status="CANONICAL",
            verification_status="VERIFIED",
            source_basis=None,
        )
        violations = validate_agam_entry(entry)
        self.assertTrue(any("source_basis" in v for v in violations))

    def test_verified_canonical_with_source_basis_passes(self):
        entry = _valid_agam_entry(
            canonical_status="CANONICAL",
            verification_status="VERIFIED",
            source_basis="bibliographic_record",
        )
        violations = validate_agam_entry(entry)
        self.assertEqual(violations, [])

    def test_inventory_duplicate_ids_detected(self):
        inv = {
            "sample_entries": [
                _valid_agam_entry(agam_id="AGAM-001"),
                _valid_agam_entry(agam_id="AGAM-001"),
            ]
        }
        violations = validate_agam_inventory(inv)
        self.assertTrue(any("duplicate" in v for v in violations))

    def test_inventory_valid_entries_pass(self):
        inv = {
            "sample_entries": [
                _valid_agam_entry(agam_id="AGAM-001"),
                _valid_agam_entry(agam_id="AGAM-002"),
            ]
        }
        violations = validate_agam_inventory(inv)
        self.assertEqual(violations, [])


# ---------------------------------------------------------------------------
# Source registry tests
# ---------------------------------------------------------------------------

class TestSourceRegistryValidation(unittest.TestCase):
    """Validate source registry entries."""

    def test_valid_entry_passes(self):
        entry = _valid_source_entry()
        violations = validate_source_entry(entry)
        self.assertEqual(violations, [])

    def test_missing_required_field(self):
        entry = _valid_source_entry()
        del entry["platform"]
        violations = validate_source_entry(entry)
        self.assertTrue(any("platform" in v for v in violations))

    def test_invalid_platform(self):
        entry = _valid_source_entry(platform="INVALID")
        violations = validate_source_entry(entry)
        self.assertTrue(any("platform" in v for v in violations))

    def test_invalid_tradition(self):
        entry = _valid_source_entry(tradition="INVALID")
        violations = validate_source_entry(entry)
        self.assertTrue(any("tradition" in v for v in violations))

    def test_invalid_religious_scope(self):
        entry = _valid_source_entry(religious_scope="INVALID")
        violations = validate_source_entry(entry)
        self.assertTrue(any("religious_scope" in v for v in violations))

    def test_invalid_knowledge_layer(self):
        entry = _valid_source_entry(knowledge_layer="INVALID")
        violations = validate_source_entry(entry)
        self.assertTrue(any("knowledge_layer" in v for v in violations))

    def test_invalid_content_role(self):
        entry = _valid_source_entry(content_role="INVALID")
        violations = validate_source_entry(entry)
        self.assertTrue(any("content_role" in v for v in violations))

    def test_invalid_rights_status(self):
        entry = _valid_source_entry(rights_status="INVALID")
        violations = validate_source_entry(entry)
        self.assertTrue(any("rights_status" in v for v in violations))

    def test_source_id_format(self):
        entry = _valid_source_entry(source_id="BAD-ID")
        violations = validate_source_entry(entry)
        self.assertTrue(any("source_id" in v for v in violations))

    def test_download_available_does_not_imply_clear(self):
        """KEY RULE: download_available=true does NOT mean training is allowed."""
        entry = _valid_source_entry(
            download_available=True,
            rights_status="UNKNOWN",
            sft_candidate=False,
        )
        violations = validate_source_entry(entry)
        self.assertEqual(violations, [])

    def test_sft_candidate_requires_clear_rights(self):
        """KEY RULE: sft_candidate requires CLEAR rights."""
        entry = _valid_source_entry(
            sft_candidate=True,
            rights_status="UNKNOWN",
        )
        violations = validate_source_entry(entry)
        self.assertTrue(any("sft_candidate" in v for v in violations))

    def test_sft_candidate_with_clear_rights_passes(self):
        entry = _valid_source_entry(
            sft_candidate=True,
            rights_status="CLEAR",
            license="CC0-1.0",
        )
        violations = validate_source_entry(entry)
        self.assertEqual(violations, [])

    def test_verified_canonical_requires_evidence(self):
        """KEY RULE: VERIFIED canonical status needs evidence."""
        entry = _valid_source_entry(
            canonical_status="CANONICAL",
            verification_status="VERIFIED",
            license=None,
            license_evidence_url=None,
        )
        violations = validate_source_entry(entry)
        self.assertTrue(any("VERIFIED" in v for v in violations))

    def test_verified_canonical_with_license_passes(self):
        entry = _valid_source_entry(
            canonical_status="CANONICAL",
            verification_status="VERIFIED",
            license="CC0-1.0",
        )
        violations = validate_source_entry(entry)
        self.assertEqual(violations, [])

    def test_registry_duplicate_ids_detected(self):
        reg = {
            "initial_entries": [
                _valid_source_entry(source_id="EXT-0001"),
                _valid_source_entry(source_id="EXT-0001"),
            ]
        }
        violations = validate_source_registry(reg)
        self.assertTrue(any("duplicate" in v for v in violations))

    def test_registry_valid_entries_pass(self):
        reg = {
            "initial_entries": [
                _valid_source_entry(source_id="EXT-0001"),
                _valid_source_entry(source_id="EXT-0002"),
            ]
        }
        violations = validate_source_registry(reg)
        self.assertEqual(violations, [])

    def test_check_no_download_implies_training(self):
        entries = [
            _valid_source_entry(
                source_id="EXT-0001",
                download_available=True,
                rights_status="UNCLEAR",
                sft_candidate=True,
            ),
        ]
        violations = check_no_download_implies_training(entries)
        self.assertEqual(len(violations), 1)
        self.assertIn("EXT-0001", violations[0])

    def test_check_no_download_implies_training_clean(self):
        entries = [
            _valid_source_entry(
                source_id="EXT-0001",
                download_available=True,
                rights_status="UNCLEAR",
                sft_candidate=False,
            ),
        ]
        violations = check_no_download_implies_training(entries)
        self.assertEqual(violations, [])

    def test_check_no_unlicensed_verified_canonical(self):
        entries = [
            _valid_source_entry(
                source_id="EXT-0001",
                canonical_status="CANONICAL",
                verification_status="VERIFIED",
                license=None,
                license_evidence_url=None,
            ),
        ]
        violations = check_no_unlicensed_verified_canonical(entries)
        self.assertEqual(len(violations), 1)
        self.assertIn("EXT-0001", violations[0])

    def test_check_no_unlicensed_verified_canonical_clean(self):
        entries = [
            _valid_source_entry(
                source_id="EXT-0001",
                canonical_status="CANONICAL",
                verification_status="VERIFIED",
                license="CC0-1.0",
            ),
        ]
        violations = check_no_unlicensed_verified_canonical(entries)
        self.assertEqual(violations, [])


# ---------------------------------------------------------------------------
# Coverage matrix tests
# ---------------------------------------------------------------------------

class TestCoverageMatrixValidation(unittest.TestCase):
    """Validate coverage matrix entries."""

    def test_valid_entry_passes(self):
        entry = _valid_coverage_entry()
        violations = validate_coverage_entry(entry)
        self.assertEqual(violations, [])

    def test_missing_required_field(self):
        entry = _valid_coverage_entry()
        del entry["category"]
        violations = validate_coverage_entry(entry)
        self.assertTrue(any("category" in v for v in violations))

    def test_invalid_category(self):
        entry = _valid_coverage_entry(category="INVALID")
        violations = validate_coverage_entry(entry)
        self.assertTrue(any("category" in v for v in violations))

    def test_invalid_tradition_relevance(self):
        entry = _valid_coverage_entry(tradition_relevance="INVALID")
        violations = validate_coverage_entry(entry)
        self.assertTrue(any("tradition_relevance" in v for v in violations))

    def test_invalid_coverage_status(self):
        entry = _valid_coverage_entry(coverage_status="INVALID")
        violations = validate_coverage_entry(entry)
        self.assertTrue(any("coverage_status" in v for v in violations))

    def test_negative_source_count(self):
        entry = _valid_coverage_entry(source_count=-1)
        violations = validate_coverage_entry(entry)
        self.assertTrue(any("source_count" in v for v in violations))

    def test_topic_id_format(self):
        entry = _valid_coverage_entry(topic_id="BAD-ID")
        violations = validate_coverage_entry(entry)
        self.assertTrue(any("topic_id" in v for v in violations))

    def test_matrix_duplicate_ids_detected(self):
        matrix = {
            "entries": [
                _valid_coverage_entry(topic_id="TOPIC-001"),
                _valid_coverage_entry(topic_id="TOPIC-001"),
            ]
        }
        violations = validate_coverage_matrix(matrix)
        self.assertTrue(any("duplicate" in v for v in violations))

    def test_matrix_valid_entries_pass(self):
        matrix = {
            "entries": [
                _valid_coverage_entry(topic_id="TOPIC-001"),
                _valid_coverage_entry(topic_id="TOPIC-002"),
            ]
        }
        violations = validate_coverage_matrix(matrix)
        self.assertEqual(violations, [])


# ---------------------------------------------------------------------------
# File loading tests
# ---------------------------------------------------------------------------

class TestKnowledgeFilesLoad(unittest.TestCase):
    """Verify all knowledge files load correctly."""

    def test_ontology_loads(self):
        onto = load_ontology()
        self.assertIn("version", onto)
        self.assertEqual(onto["version"], "1.0")

    def test_agam_inventory_loads(self):
        inv = load_agam_inventory()
        self.assertIn("sample_entries", inv)
        self.assertGreater(len(inv["sample_entries"]), 0)

    def test_source_registry_loads(self):
        reg = load_source_registry()
        self.assertIn("initial_entries", reg)
        self.assertGreater(len(reg["initial_entries"]), 0)

    def test_coverage_matrix_loads(self):
        matrix = load_coverage_matrix()
        self.assertIn("entries", matrix)
        self.assertGreater(len(matrix["entries"]), 0)

    def test_agam_inventory_validates(self):
        inv = load_agam_inventory()
        violations = validate_agam_inventory(inv)
        self.assertEqual(violations, [])

    def test_source_registry_validates(self):
        reg = load_source_registry()
        violations = validate_source_registry(reg)
        self.assertEqual(violations, [])

    def test_coverage_matrix_validates(self):
        matrix = load_coverage_matrix()
        violations = validate_coverage_matrix(matrix)
        self.assertEqual(violations, [])

    def test_no_sft_candidate_with_unclear_rights(self):
        """Hard rule: no SFT candidate may have non-CLEAR rights."""
        reg = load_source_registry()
        entries = reg.get("initial_entries", [])
        for entry in entries:
            if entry.get("sft_candidate"):
                self.assertEqual(
                    entry.get("rights_status"), "CLEAR",
                    f"{entry.get('source_id')}: sft_candidate=true "
                    f"but rights_status={entry.get('rights_status')!r}"
                )

    def test_no_verified_canonical_without_evidence(self):
        """Hard rule: no source may claim VERIFIED canonical status without evidence."""
        reg = load_source_registry()
        entries = reg.get("initial_entries", [])
        for entry in entries:
            if (entry.get("verification_status") == "VERIFIED"
                    and entry.get("canonical_status") in (
                        "CANONICAL", "CANONICAL_TRANSLATION",
                        "COMMENTARY_ON_CANON")):
                self.assertTrue(
                    entry.get("license") or entry.get("license_evidence_url"),
                    f"{entry.get('source_id')}: VERIFIED canonical status "
                    f"without license or license_evidence_url"
                )

    def test_no_download_implies_training_in_registry(self):
        """Hard rule: download_available does not imply training permission."""
        reg = load_source_registry()
        entries = reg.get("initial_entries", [])
        violations = check_no_download_implies_training(entries)
        self.assertEqual(violations, [])


# ---------------------------------------------------------------------------
# Acquisition queue helpers
# ---------------------------------------------------------------------------

def _valid_acq_candidate(**over) -> dict:
    """Create a minimal valid acquisition candidate."""
    base = {
        "candidate_id": "ACQ-0999",
        "title": "Test Candidate",
        "source_url": None,
        "platform": "JAINQQ",
        "source_id_if_known": None,
        "priority": "P1",
        "tradition": "UNKNOWN",
        "knowledge_layer": "OTHER",
        "content_role": "OTHER",
        "practice": None,
        "agam_id_if_applicable": None,
        "author": None,
        "teacher_or_author": None,
        "language": "unknown",
        "format": "unknown",
        "availability": "UNKNOWN",
        "download_available": False,
        "text_available": False,
        "estimated_size": None,
        "reason_for_priority": "Test reason",
        "expected_use": "REFERENCE",
        "rights_status": "UNKNOWN",
        "acquisition_status": "DISCOVERED",
        "evidence_urls": [],
        "duplicate_candidate": False,
        "duplicate_of": None,
        "notes": None,
    }
    base.update(over)
    return base


# ---------------------------------------------------------------------------
# Acquisition queue tests
# ---------------------------------------------------------------------------

class TestAcquisitionQueueValidation(unittest.TestCase):
    """Validate acquisition queue entries."""

    def test_valid_candidate_passes(self):
        entry = _valid_acq_candidate()
        violations = validate_acquisition_candidate(entry)
        self.assertEqual(violations, [])

    def test_missing_required_field(self):
        entry = _valid_acq_candidate()
        del entry["priority"]
        violations = validate_acquisition_candidate(entry)
        self.assertTrue(any("priority" in v for v in violations))

    def test_invalid_priority(self):
        entry = _valid_acq_candidate(priority="P5")
        violations = validate_acquisition_candidate(entry)
        self.assertTrue(any("priority" in v for v in violations))

    def test_invalid_platform(self):
        entry = _valid_acq_candidate(platform="INVALID")
        violations = validate_acquisition_candidate(entry)
        self.assertTrue(any("platform" in v for v in violations))

    def test_invalid_tradition(self):
        entry = _valid_acq_candidate(tradition="INVALID")
        violations = validate_acquisition_candidate(entry)
        self.assertTrue(any("tradition" in v for v in violations))

    def test_invalid_knowledge_layer(self):
        entry = _valid_acq_candidate(knowledge_layer="INVALID")
        violations = validate_acquisition_candidate(entry)
        self.assertTrue(any("knowledge_layer" in v for v in violations))

    def test_invalid_content_role(self):
        entry = _valid_acq_candidate(content_role="INVALID")
        violations = validate_acquisition_candidate(entry)
        self.assertTrue(any("content_role" in v for v in violations))

    def test_invalid_practice(self):
        entry = _valid_acq_candidate(practice="INVALID")
        violations = validate_acquisition_candidate(entry)
        self.assertTrue(any("practice" in v for v in violations))

    def test_valid_practice_passes(self):
        entry = _valid_acq_candidate(practice="SAMAYIK")
        violations = validate_acquisition_candidate(entry)
        self.assertEqual(violations, [])

    def test_invalid_rights_status(self):
        entry = _valid_acq_candidate(rights_status="INVALID")
        violations = validate_acquisition_candidate(entry)
        self.assertTrue(any("rights_status" in v for v in violations))

    def test_invalid_acquisition_status(self):
        entry = _valid_acq_candidate(acquisition_status="INVALID")
        violations = validate_acquisition_candidate(entry)
        self.assertTrue(any("acquisition_status" in v for v in violations))

    def test_invalid_expected_use(self):
        entry = _valid_acq_candidate(expected_use="INVALID")
        violations = validate_acquisition_candidate(entry)
        self.assertTrue(any("expected_use" in v for v in violations))

    def test_candidate_id_format(self):
        entry = _valid_acq_candidate(candidate_id="BAD-ID")
        violations = validate_acquisition_candidate(entry)
        self.assertTrue(any("candidate_id" in v for v in violations))

    def test_p0_restricted_rights_detected(self):
        entry = _valid_acq_candidate(priority="P0", rights_status="RESTRICTED")
        violations = validate_acquisition_candidate(entry)
        self.assertTrue(any("RESTRICTED" in v for v in violations))

    def test_sft_without_clear_rights_detected(self):
        entry = _valid_acq_candidate(expected_use="BOTH", rights_status="RESTRICTED")
        violations = validate_acquisition_candidate(entry)
        self.assertTrue(any("SFT" in v or "expected_use" in v for v in violations))

    def test_sft_with_clear_rights_passes(self):
        entry = _valid_acq_candidate(expected_use="BOTH", rights_status="CLEAR")
        violations = validate_acquisition_candidate(entry)
        self.assertEqual(violations, [])

    def test_sft_with_unknown_rights_passes(self):
        """In a planning queue, SFT+UNKNOWN is acceptable (rights not yet reviewed)."""
        entry = _valid_acq_candidate(expected_use="BOTH", rights_status="UNKNOWN")
        violations = validate_acquisition_candidate(entry)
        self.assertEqual(violations, [])

    def test_duplicate_candidate_requires_duplicate_of(self):
        entry = _valid_acq_candidate(duplicate_candidate=True, duplicate_of=None)
        violations = validate_acquisition_candidate(entry)
        self.assertTrue(any("duplicate_of" in v for v in violations))

    def test_duplicate_candidate_with_target_passes(self):
        entry = _valid_acq_candidate(duplicate_candidate=True, duplicate_of="SVK-0006")
        violations = validate_acquisition_candidate(entry)
        self.assertEqual(violations, [])

    def test_queue_duplicate_ids_detected(self):
        queue = {
            "candidates": [
                _valid_acq_candidate(candidate_id="ACQ-001"),
                _valid_acq_candidate(candidate_id="ACQ-001"),
            ]
        }
        violations = validate_acquisition_queue(queue)
        self.assertTrue(any("duplicate" in v for v in violations))

    def test_queue_valid_entries_pass(self):
        queue = {
            "candidates": [
                _valid_acq_candidate(candidate_id="ACQ-001"),
                _valid_acq_candidate(candidate_id="ACQ-002"),
            ]
        }
        violations = validate_acquisition_queue(queue)
        self.assertEqual(violations, [])

    def test_check_no_p0_restricted(self):
        candidates = [
            _valid_acq_candidate(candidate_id="ACQ-001", priority="P0", rights_status="RESTRICTED"),
        ]
        violations = check_no_p0_restricted_rights(candidates)
        self.assertEqual(len(violations), 1)
        self.assertIn("ACQ-001", violations[0])

    def test_check_no_p0_restricted_clean(self):
        candidates = [
            _valid_acq_candidate(candidate_id="ACQ-001", priority="P0", rights_status="UNKNOWN"),
        ]
        violations = check_no_p0_restricted_rights(candidates)
        self.assertEqual(violations, [])

    def test_check_no_sft_without_clear(self):
        candidates = [
            _valid_acq_candidate(candidate_id="ACQ-001", expected_use="BOTH", rights_status="RESTRICTED"),
        ]
        violations = check_no_sft_without_clear_rights(candidates)
        self.assertEqual(len(violations), 1)
        self.assertIn("ACQ-001", violations[0])

    def test_check_no_sft_without_clear_clean(self):
        candidates = [
            _valid_acq_candidate(candidate_id="ACQ-001", expected_use="BOTH", rights_status="CLEAR"),
        ]
        violations = check_no_sft_without_clear_rights(candidates)
        self.assertEqual(violations, [])

    def test_acquisition_queue_loads(self):
        queue = load_acquisition_queue()
        self.assertIn("candidates", queue)
        self.assertGreater(len(queue["candidates"]), 0)

    def test_acquisition_queue_validates(self):
        queue = load_acquisition_queue()
        violations = validate_acquisition_queue(queue)
        self.assertEqual(violations, [])

    def test_no_p0_restricted_in_queue(self):
        """Hard rule: no P0 candidate may have RESTRICTED rights."""
        queue = load_acquisition_queue()
        violations = check_no_p0_restricted_rights(queue.get("candidates", []))
        self.assertEqual(violations, [])

    def test_no_sft_without_clear_in_queue(self):
        """Hard rule: no SFT candidate may have non-CLEAR rights."""
        queue = load_acquisition_queue()
        violations = check_no_sft_without_clear_rights(queue.get("candidates", []))
        self.assertEqual(violations, [])


if __name__ == "__main__":
    unittest.main()

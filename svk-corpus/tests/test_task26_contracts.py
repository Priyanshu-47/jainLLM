"""Tests for Task 26 Jainebooks MCP discovery contracts."""
import json
from pathlib import Path

DATA = Path("data/acquisition")

REQUIRED_QUEUE_FIELDS = {
    "candidate_id", "title", "book_id", "url", "platform", "author",
    "tradition", "lineage", "knowledge_layer", "language", "script",
    "year", "format", "availability", "rights_status", "priority",
    "expected_training_use", "contextual_relevance", "evidence"
}

REQUIRED_GAP_FIELDS = {
    "practice", "existing_candidates", "new_jainebooks_candidates",
    "strongest_source", "teacher_or_lineage"
}


class TestJainebooksQueue:
    def test_file_exists(self):
        assert (DATA / "jainebooks_candidate_inventory_v1.json").exists()

    def test_valid_json_structure(self):
        with open(DATA / "jainebooks_candidate_inventory_v1.json") as f:
            data = json.load(f)
        assert isinstance(data, dict)
        assert "candidates" in data
        assert isinstance(data["candidates"], list)
        assert len(data["candidates"]) > 0

    def test_required_fields(self):
        with open(DATA / "jainebooks_candidate_inventory_v1.json") as f:
            data = json.load(f)
        for item in data["candidates"]:
            for field in REQUIRED_QUEUE_FIELDS:
                assert field in item, f"Missing {field} in {item.get('candidate_id', '?')}"

    def test_unique_ids(self):
        with open(DATA / "jainebooks_candidate_inventory_v1.json") as f:
            data = json.load(f)
        ids = [item["candidate_id"] for item in data["candidates"]]
        assert len(ids) == len(set(ids))

    def test_priority_values(self):
        with open(DATA / "jainebooks_candidate_inventory_v1.json") as f:
            data = json.load(f)
        for item in data["candidates"]:
            assert item["priority"] in {"P0", "P1", "P2", "P3"}, \
                f"Invalid priority {item['priority']} in {item['candidate_id']}"

    def test_no_verified_sft(self):
        with open(DATA / "jainebooks_candidate_inventory_v1.json") as f:
            data = json.load(f)
        for item in data["candidates"]:
            assert "VERIFIED_SFT" not in str(item.get("verification_status", "")), \
                f"Verified SFT status in {item['candidate_id']}"

    def test_evidence_present(self):
        with open(DATA / "jainebooks_candidate_inventory_v1.json") as f:
            data = json.load(f)
        for item in data["candidates"]:
            assert item.get("evidence"), f"No evidence in {item['candidate_id']}"

    def test_total_matches_count(self):
        with open(DATA / "jainebooks_candidate_inventory_v1.json") as f:
            data = json.load(f)
        assert data["total_candidates"] == len(data["candidates"])


class TestPracticeGapMatrix:
    def test_file_exists(self):
        assert (DATA / "sthanakavasi_practice_gap_v2.json").exists()

    def test_practices_covered(self):
        with open(DATA / "sthanakavasi_practice_gap_v2.json") as f:
            data = json.load(f)
        practices = {item["practice"] for item in data["practices"]}
        expected = {"SAMAYIK", "PRATIKRAMAN", "KAYOTSARGA", "VANDANA",
                    "PRATYAKHYAN", "CHAUVISANTHO", "AVASHYAKA", "PARYUSHAN"}
        assert expected == practices

    def test_required_fields(self):
        with open(DATA / "sthanakavasi_practice_gap_v2.json") as f:
            data = json.load(f)
        for item in data["practices"]:
            for field in REQUIRED_GAP_FIELDS:
                assert field in item, f"Missing {field} in {item['practice']}"


class TestTeacherInventory:
    def test_file_exists(self):
        assert (DATA / "sthanakavasi_teacher_source_inventory_v2.json").exists()

    def test_valid_json_structure(self):
        with open(DATA / "sthanakavasi_teacher_source_inventory_v2.json") as f:
            data = json.load(f)
        assert isinstance(data, dict)
        assert "teachers" in data
        assert isinstance(data["teachers"], list)
        assert len(data["teachers"]) > 0

    def test_no_inferred_lineage_without_evidence(self):
        with open(DATA / "sthanakavasi_teacher_source_inventory_v2.json") as f:
            data = json.load(f)
        for item in data["teachers"]:
            lineage = str(item.get("lineage", "")).lower()
            evidence = str(item.get("evidence_of_sthanakvasi", "")).lower()
            # Lineage must be either UNKNOWN or supported by evidence
            assert "unknown" in lineage or \
                   "sthanakvasi" in lineage or \
                   "sthanakvasi" in evidence, \
                f"Lineage inferred without evidence in {item['name']}"

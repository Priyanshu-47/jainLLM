"""Schema + provenance tests for the release record contract.

The invariant: a release record without complete provenance or a licence block
must never validate. `validate_release_record` is the last line of defence
before anything reaches data/release/.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from svk_corpus.schemas.records import (
    RELEASE_REQUIRED_FIELDS,
    validate_release_record,
)


def _valid_record() -> dict:
    return {
        "id": "svk_T1:u00001:deadbeefdeadbeef",
        "source_id": "T1",
        "text": "सव्वे जीवा वि इच्छंति जीविउं ण मरिज्जिउं॥",
        "normalized_text": "सव्वे जीवा वि इच्छंति जीविउं ण मरिज्जिउं॥",
        "text_role": "ORIGINAL",
        "language": "pra",
        "script": "Devanagari",
        "unit_type": "verse",
        "source_locator": {"page": 42, "citation": "T1, p. 42"},
        "provenance": {
            "source_url": "https://archive.org/details/some-item",
            "artifact_sha256": "ab" * 32,
            "repository": "internetarchive",
        },
        "license": {
            "status": "TRAINING_ALLOWED",
            "evidence": "R70_PRE_1930_PUBLICATION: publication_year=1923",
        },
        "quality": {"ocr_required": True},
        "publication_year": 1923,
        "tradition": "Shvetambara",
        "sect": "unknown",
        "pipeline_version": "0.1.0",
    }


class TestValidRecords(unittest.TestCase):
    def test_valid_record_passes(self):
        self.assertEqual(validate_release_record(_valid_record()), [])

    def test_json_roundtrip(self):
        record = json.loads(json.dumps(_valid_record()))
        self.assertEqual(validate_release_record(record), [])


class TestMissingFields(unittest.TestCase):
    def test_each_required_field_is_required(self):
        for field in RELEASE_REQUIRED_FIELDS:
            record = _valid_record()
            del record[field]
            problems = validate_release_record(record)
            self.assertTrue(
                any(f"missing field: {field}" in p for p in problems),
                f"deleting {field} was not flagged",
            )

    def test_empty_text_rejected(self):
        record = _valid_record()
        record["text"] = ""
        record["normalized_text"] = ""
        problems = validate_release_record(record)
        self.assertTrue(any("no text" in p for p in problems))


class TestProvenance(unittest.TestCase):
    def test_missing_source_url_rejected(self):
        record = _valid_record()
        record["provenance"]["source_url"] = ""
        self.assertTrue(any("source_url" in p
                            for p in validate_release_record(record)))

    def test_missing_artifact_sha256_rejected(self):
        record = _valid_record()
        record["provenance"]["artifact_sha256"] = ""
        self.assertTrue(any("artifact_sha256" in p
                            for p in validate_release_record(record)))

    def test_missing_repository_rejected(self):
        record = _valid_record()
        record["provenance"]["repository"] = ""
        self.assertTrue(any("repository" in p
                            for p in validate_release_record(record)))

    def test_non_dict_provenance_rejected(self):
        record = _valid_record()
        record["provenance"] = "https://example.org"
        self.assertTrue(any("provenance must be an object" in p
                            for p in validate_release_record(record)))


class TestLicenseBlock(unittest.TestCase):
    def test_empty_status_rejected(self):
        record = _valid_record()
        record["license"]["status"] = ""
        self.assertTrue(any("license.status" in p
                            for p in validate_release_record(record)))

    def test_empty_evidence_rejected(self):
        record = _valid_record()
        record["license"]["evidence"] = ""
        self.assertTrue(any("license.evidence" in p
                            for p in validate_release_record(record)))

    def test_unknown_text_role_rejected(self):
        record = _valid_record()
        record["text_role"] = "SCRIPTURE"  # not in the closed enum
        self.assertTrue(any("unknown text_role" in p
                            for p in validate_release_record(record)))


class TestReleasedFilesValidate(unittest.TestCase):
    """The actual release products must pass the same validator."""

    RELEASE_DIR = Path(__file__).resolve().parents[1] / "data" / "release"

    def test_release_jsonl_validates(self):
        rag = self.RELEASE_DIR / "rag_corpus.jsonl"
        train = self.RELEASE_DIR / "training_corpus.jsonl"
        if not (rag.is_file() and train.is_file()):
            self.skipTest("release files not present; run `python -m svk_corpus release`")
        problems = []
        checked = 0
        for path in (rag, train):
            with path.open("r", encoding="utf-8") as fh:
                for line_number, line in enumerate(fh, 1):
                    line = line.strip()
                    if not line:
                        continue
                    checked += 1
                    record = json.loads(line)
                    for problem in validate_release_record(record):
                        problems.append(f"{path.name}:{line_number}: {problem}")
        self.assertEqual(problems, [])
        self.assertGreater(checked, 0)


if __name__ == "__main__":
    unittest.main()

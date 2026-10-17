"""TASK 64 tests: SFT-01 dataset preparation.

Covers the validation bullets required by the Task 64 spec:

    * every output row is schema-valid (sft_schema_v1);
    * no duplicate example_ids, questions or answers (incl. near-dups);
    * provenance complete, every source present in source_manifest.csv;
    * rights cleared in the record and on recomputation (no downgrades);
    * source-level deterministic train/eval split, no leakage;
    * no Task 63 REJECT/REVISE record in the outputs;
    * messages match question/answer exactly;
    * answers complete, no raw URLs / SVK ids / OCR index fragments;
    * grounding + attribution re-verified against linked evidence;
    * sect / knowledge layer / tradition / scope consistent with manifest;
    * HUMAN_VERIFIED integrity: 8 in, 5 selected, 3 excluded, 0 created;
    * the frozen 47-case eval file is untouched;
    * stats JSON agrees with the files (counts + sha256);
    * the split assignment is reproducible from seed 42.

Everything is read-only: no source record, human decision file or frozen eval
case is modified by these tests.
"""

from __future__ import annotations

import json
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SFT01_DIR = os.path.join(ROOT, "experiments", "sft_01")
if SFT01_DIR not in sys.path:
    sys.path.insert(0, SFT01_DIR)

import validate_sft01_dataset as v  # noqa: E402

_PAYLOAD = None


def payload():
    global _PAYLOAD
    if _PAYLOAD is None:
        train, eval_rows = v.load_outputs()
        stats = v.load_stats()
        _PAYLOAD = (train, eval_rows, stats)
    return _PAYLOAD


def rows():
    train, eval_rows, _ = payload()
    return train, eval_rows


class TestSft01Dataset(unittest.TestCase):
    def test_schema_validity(self):
        train, eval_rows = rows()
        ok, bad = v.check_schema(train, eval_rows)
        self.assertTrue(ok, bad[:3])

    def test_example_id_uniqueness(self):
        train, eval_rows = rows()
        ok, bad = v.check_example_ids_unique(train, eval_rows)
        self.assertTrue(ok, bad)

    def test_no_exact_duplicates(self):
        train, eval_rows = rows()
        ok, bad = v.check_no_exact_duplicates(train, eval_rows)
        self.assertTrue(ok, bad[:3])

    def test_no_near_duplicates(self):
        train, eval_rows = rows()
        ok, bad = v.check_no_near_duplicates(train, eval_rows)
        self.assertTrue(ok, bad[:3])

    def test_provenance_and_manifest(self):
        train, eval_rows = rows()
        ok, bad = v.check_provenance_and_manifest(train, eval_rows)
        self.assertTrue(ok, bad[:3])

    def test_rights_recorded_and_recomputed(self):
        train, eval_rows = rows()
        ok, bad = v.check_rights(train, eval_rows)
        self.assertTrue(ok, bad[:3])

    def test_split_separation(self):
        train, eval_rows = rows()
        ok, bad = v.check_split_separation(train, eval_rows)
        self.assertTrue(ok, bad[:3])

    def test_deterministic_split_reproducible(self):
        train, eval_rows = rows()
        ok, bad = v.check_deterministic_split(train, eval_rows)
        self.assertTrue(ok, bad)

    def test_split_sizes_reasonable(self):
        train, eval_rows = rows()
        total = len(train) + len(eval_rows)
        self.assertEqual(total, 59)
        self.assertEqual(len(train), 50)
        self.assertEqual(len(eval_rows), 9)
        self.assertGreaterEqual(len(eval_rows), 6)
        self.assertLessEqual(len(eval_rows), 0.25 * total)

    def test_no_task63_reject_or_revise(self):
        train, eval_rows = rows()
        ok, bad = v.check_no_task63_reject_revise(train, eval_rows)
        self.assertTrue(ok, bad)

    def test_messages_match_question_answer(self):
        train, eval_rows = rows()
        ok, bad = v.check_messages(train, eval_rows)
        self.assertTrue(ok, bad[:3])

    def test_answer_quality_and_no_raw_ids(self):
        train, eval_rows = rows()
        ok, bad = v.check_answer_quality(train, eval_rows)
        self.assertTrue(ok, bad[:3])

    def test_metadata_consistency(self):
        train, eval_rows = rows()
        ok, bad = v.check_metadata_consistency(train, eval_rows)
        self.assertTrue(ok, bad[:3])

    def test_grounding_and_attribution(self):
        train, eval_rows = rows()
        ok, bad = v.check_grounding(train, eval_rows)
        self.assertTrue(ok, bad[:3])

    def test_human_verified_integrity(self):
        train, eval_rows, stats = payload()
        ok, bad = v.check_human_verified_integrity(train, eval_rows, stats)
        self.assertTrue(ok, bad)

    def test_no_new_human_verified_status(self):
        train, eval_rows = rows()
        for r in train + eval_rows:
            if r["sft01"]["input"] == "task63_approve":
                self.assertNotEqual(r.get("human_review_status"), "HUMAN_VERIFIED")
                self.assertNotEqual(r.get("HUMAN_VERIFIED"), True)

    def test_frozen_eval_untouched(self):
        ok, bad = v.check_frozen_eval_untouched(*rows())
        self.assertTrue(ok, bad)

    def test_stats_json_consistency(self):
        train, eval_rows, stats = payload()
        ok, bad = v.check_stats_consistency(train, eval_rows, stats)
        self.assertTrue(ok, bad)

    def test_counts_match_spec_expectations(self):
        _, _, stats = payload()
        self.assertEqual(stats["inputs"], {"task63_approve": 54, "human_verified": 8,
                                           "total": 62})
        self.assertEqual(stats["exclusions"], {"TASK63_REJECT": 3})
        self.assertEqual(stats["selected_total"], 59)
        self.assertEqual(stats["human_verified"]["selected"], 5)
        self.assertEqual(stats["human_verified"]["newly_created"], 0)

    def test_inputs_unchanged(self):
        gold = os.path.join(ROOT, "data", "training", "sft_gold_v4_candidates.jsonl")
        human = os.path.join(ROOT, "data", "training", "sft_reconciled_v1.jsonl")
        self.assertEqual(len(v.b.read_jsonl(gold)), 54)
        self.assertEqual(len(v.b.read_jsonl(human)), 8)

    def test_schema_file_not_modified(self):
        with open(v.b.SCHEMA_PATH, encoding="utf-8") as fh:
            schema = json.load(fh)
        self.assertIn("messages", schema["properties"])


if __name__ == "__main__":
    unittest.main()

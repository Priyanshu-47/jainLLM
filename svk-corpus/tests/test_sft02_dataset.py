"""TASK 67 tests: SFT-02 dataset preparation.

Covers the validation bullets required by the Task 67 spec:

    * every output row is schema-valid (sft_schema_v1);
    * no duplicate example_ids, questions or answers (incl. near-dups);
    * provenance complete, every source present in source_manifest.csv;
    * rights cleared in the record and on recomputation;
    * origin object schema + approved/task67 row markers;
    * source-level deterministic train/eval split, no leakage;
    * pair integrity: every pair_group intact, same split, train-locked;
    * eval coverage of the 3 required categories, sizes sane;
    * no frozen source / frozen-question leakage, frozen file untouched;
    * messages match question/answer exactly;
    * answer quality (>= 12 words, no raw URLs / SVK ids / unit ids);
    * row gates + grounding re-verified against linked evidence;
    * Task-66 s14 category targets (ranges) met;
    * abstention balance: 4 pairs, 4 answerable / 4 unanswerable,
      >= 4 refusal phrasings;
    * attribution balance: 16-18 rows, >= 6 unknown, <= 40% share;
    * anti-fabrication: 6-8 pairs (12 rows) / all intact + train-locked;
    * style: >= 10 wh-openers, median answer <= 350 chars;
    * stats JSON agrees with the files (counts + leakage + gate);
    * SFT-02 config consistent with the built files (rows, LR, epochs);
    * read-only inputs unchanged (v1 train/eval, gold, schema);
    * anti-template gate re-run passes (PASS/WARN only).

Everything is read-only: no source record, frozen eval case or input
dataset is modified by these tests.
"""

from __future__ import annotations

import json
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SFT02_DIR = os.path.join(ROOT, "experiments", "sft_02")
if SFT02_DIR not in sys.path:
    sys.path.insert(0, SFT02_DIR)

import validate_sft02_dataset as v  # noqa: E402

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


class TestSft02Dataset(unittest.TestCase):
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

    def test_origin_object_schema(self):
        train, eval_rows = rows()
        ok, bad = v.check_origin_object(train, eval_rows)
        self.assertTrue(ok, bad[:3])

    def test_split_separation(self):
        train, eval_rows = rows()
        ok, bad = v.check_split_separation(train, eval_rows)
        self.assertTrue(ok, bad[:3])

    def test_deterministic_split_reproducible(self):
        train, eval_rows = rows()
        ok, bad = v.check_deterministic_split(train, eval_rows)
        self.assertTrue(ok, bad)

    def test_pair_integrity(self):
        train, eval_rows = rows()
        ok, bad = v.check_pair_integrity(train, eval_rows)
        self.assertTrue(ok, bad)

    def test_eval_coverage_and_sizes(self):
        train, eval_rows = rows()
        ok, bad = v.check_eval_coverage(train, eval_rows)
        self.assertTrue(ok, bad)
        total = len(train) + len(eval_rows)
        self.assertEqual(total, 74)
        self.assertEqual(len(train), 61)
        self.assertEqual(len(eval_rows), 13)

    def test_no_frozen_leakage(self):
        train, eval_rows = rows()
        ok, bad = v.check_frozen_leakage(train, eval_rows)
        self.assertTrue(ok, bad[:3])

    def test_messages_match_question_answer(self):
        train, eval_rows = rows()
        ok, bad = v.check_messages(train, eval_rows)
        self.assertTrue(ok, bad[:3])

    def test_answer_quality_and_no_raw_ids(self):
        train, eval_rows = rows()
        ok, bad = v.check_answer_quality(train, eval_rows)
        self.assertTrue(ok, bad[:3])

    def test_row_gates_and_grounding(self):
        train, eval_rows = rows()
        ok, bad = v.check_row_gates_and_grounding(train, eval_rows)
        self.assertTrue(ok, bad[:3])

    def test_anti_template_gate_pass(self):
        train, eval_rows = rows()
        ok, bad = v.check_gate_rerun(train, eval_rows)
        self.assertTrue(ok, bad)

    def test_category_targets_task66(self):
        train, eval_rows = rows()
        ok, bad = v.check_category_targets(train, eval_rows)
        self.assertTrue(ok, bad)

    def test_abstention_balance(self):
        train, eval_rows = rows()
        ok, bad = v.check_abstention_balance(train, eval_rows)
        self.assertTrue(ok, bad)

    def test_attribution_balance(self):
        train, eval_rows = rows()
        ok, bad = v.check_attribution_balance(train, eval_rows)
        self.assertTrue(ok, bad)

    def test_antifabrication_pairs(self):
        train, eval_rows = rows()
        ok, bad = v.check_antifabrication(train, eval_rows)
        self.assertTrue(ok, bad)

    def test_style_spread_and_concision(self):
        train, eval_rows = rows()
        ok, bad = v.check_style_spread(train, eval_rows)
        self.assertTrue(ok, bad)

    def test_stats_json_consistency(self):
        train, eval_rows, stats = payload()
        ok, bad = v.check_stats_consistency(train, eval_rows, stats)
        self.assertTrue(ok, bad)

    def test_frozen_eval_untouched(self):
        ok, bad = v.check_frozen_eval_untouched(*rows())
        self.assertTrue(ok, bad)

    def test_config_consistency(self):
        train, eval_rows = rows()
        ok, bad = v.check_config_consistency(train, eval_rows)
        self.assertTrue(ok, bad)

    def test_readonly_inputs_unchanged(self):
        train, eval_rows = rows()
        ok, bad = v.check_readonly_inputs(train, eval_rows)
        self.assertTrue(ok, bad)
        self.assertEqual(len(v.read_jsonl(v.TRAIN_V1_PATH)), 50)
        self.assertEqual(len(v.read_jsonl(v.OUT_TRAIN)), 61)
        self.assertEqual(len(v.read_jsonl(v.OUT_EVAL)), 13)
        self.assertEqual(len(v.read_jsonl(v.GOLD_PATH)), 54)

    def test_stats_key_counts(self):
        _, _, stats = payload()
        self.assertEqual(stats["totals"], {"train": 61, "eval": 13, "total": 74})
        self.assertEqual(stats["seed"], "42")
        self.assertEqual(stats["frozen_sha256"], v.FROZEN_EVAL_SHA256)
        self.assertEqual(stats["abstention_pairs"]["intact_after_dedup"], 4)
        self.assertEqual(stats["antifab_pairs_intact"], 6)
        self.assertEqual(stats["gate_report"]["level"], "WARN")
        self.assertEqual(stats["split"]["coverage_missing"], [])
        self.assertEqual(stats["leakage"]["frozen_sources_in_dataset"], [])
        self.assertEqual(stats["leakage"]["shared_sources_train_eval"], [])

    def test_schema_file_not_modified(self):
        with open(v.SCHEMA_PATH, encoding="utf-8") as fh:
            schema = json.load(fh)
        self.assertIn("messages", schema["properties"])


if __name__ == "__main__":
    unittest.main()

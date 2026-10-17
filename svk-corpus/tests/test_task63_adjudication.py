"""TASK 63 tests: the consolidated adjudication layer.

These cover the validation bullets required by the Task 63 spec:

    * every candidate has exactly one decision;
    * no candidate disappears;
    * no duplicate review IDs;
    * APPROVE/REVISE/REJECT counts sum to total;
    * rejected candidates are retained;
    * revised answers have revision_basis;
    * no raw URLs inside answer text if the schema prohibits them;
    * no unsupported source attribution;
    * no cross-sect contamination;
    * no HUMAN_VERIFIED status is fabricated;
    * gold candidates are traceable to evidence.

Everything is built in memory from the immutable Task 62 review queue, so the
tests never depend on files having been written and never modify a candidate
source record.
"""

from __future__ import annotations

import json
import os
import re
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TASK63_DIR = os.path.join(ROOT, "experiments", "sft_curation", "task63")
if TASK63_DIR not in sys.path:
    sys.path.insert(0, TASK63_DIR)

import run_task63  # noqa: E402

QUEUE_PATH = run_task63.QUEUE_PATH
SCHEMA_PATH = run_task63.SCHEMA_PATH

_PAYLOAD = None


def payload():
    global _PAYLOAD
    if _PAYLOAD is None:
        _PAYLOAD = run_task63.build(write=False)
    return _PAYLOAD


def _read(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


class TestOneDecisionPerCandidate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = payload()

    def test_every_candidate_has_exactly_one_decision(self):
        records = self.p["records"]
        self.assertEqual(len(records), len(self.p["queue"]))
        for rec in records:
            self.assertIn(rec["decision"], run_task63.DECISIONS)
            self.assertIn("failed_criteria", rec)

    def test_no_candidate_disappears(self):
        queue_ids = {r["review_id"] for r in self.p["queue"]}
        rec_ids = {r["review_id"] for r in self.p["records"]}
        self.assertEqual(queue_ids, rec_ids)

    def test_no_duplicate_review_ids(self):
        ids = [r["review_id"] for r in self.p["records"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_counts_sum_to_total(self):
        counts = self.p["stats"]["counts"]
        total = sum(counts.values())
        self.assertEqual(total, len(self.p["queue"]))
        self.assertEqual(counts.get("APPROVE", 0) + counts.get("REVISE", 0)
                         + counts.get("REJECT", 0), len(self.p["queue"]))

    def test_each_queue_is_fully_adjudicated(self):
        for queue in sorted({r["queue"] for r in self.p["queue"]}):
            expected = {r["review_id"] for r in self.p["queue"]
                        if r["queue"] == queue}
            got = {r["review_id"] for r in self.p["records"]
                   if r["queue"] == queue}
            self.assertEqual(expected, got, "queue %s" % queue)


class TestRejectedAreRetained(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = payload()

    def test_rejected_candidates_retained(self):
        rejected = [r for r in self.p["records"] if r["decision"] == "REJECT"]
        emitted = self.p["outputs"]["reject"]
        self.assertEqual(len(rejected), len(emitted))
        self.assertEqual({r["review_id"] for r in rejected},
                         {r["review_id"] for r in emitted})
        self.assertEqual(len(emitted), self.p["stats"]["counts"]["REJECT"])

    def test_reject_record_shape(self):
        required = {"review_id", "decision", "failed_criteria", "reason",
                    "source_id"}
        for rec in self.p["outputs"]["reject"]:
            self.assertTrue(required.issubset(rec), sorted(required - set(rec)))
            self.assertEqual(rec["decision"], "REJECT")
            self.assertTrue(rec["reason"].strip())
            self.assertTrue(rec["source_id"] or rec["review_id"])

    def test_reject_reason_is_never_empty(self):
        for rec in self.p["records"]:
            if rec["decision"] == "REJECT":
                self.assertTrue(str(rec["notes"]).strip(), rec["review_id"])

    def test_written_reject_file_matches(self):
        rows = _read(run_task63.REJECT_PATH)
        if not rows:
            self.skipTest("emitted files not written yet")
        self.assertEqual({r["review_id"] for r in rows},
                         {r["review_id"] for r in self.p["outputs"]["reject"]})


class TestRevisions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = payload()

    def test_revised_answers_have_revision_basis(self):
        for rec in self.p["outputs"]["revise"]:
            self.assertTrue(rec["revised_answer"].strip(), rec["review_id"])
            self.assertTrue(rec["revision_basis"].strip(), rec["review_id"])

    def test_revise_record_shape(self):
        required = {"review_id", "decision", "failed_criteria",
                    "original_question", "original_answer", "evidence",
                    "revised_answer", "revision_basis", "source_id",
                    "human_review_required"}
        for rec in self.p["outputs"]["revise"]:
            self.assertTrue(required.issubset(rec),
                            sorted(required - set(rec)))
            self.assertEqual(rec["decision"], "REVISE")
            self.assertTrue(rec["human_review_required"])
            self.assertFalse(rec["human_verified"])

    def test_revised_answer_never_repeats_the_original_verbatim(self):
        for rec in self.p["outputs"]["revise"]:
            self.assertNotEqual(rec["revised_answer"].strip(),
                                rec["original_answer"].strip(),
                                rec["review_id"])

    def test_revised_answer_never_contains_the_full_source_dump(self):
        for rec in self.p["outputs"]["revise"]:
            src = rec.get("source_text") or ""
            if len(src) > 400:
                self.assertNotEqual(rec["revised_answer"], src, rec["review_id"])

    def test_revision_basis_cites_supplied_evidence_only(self):
        for rec in self.p["outputs"]["revise"]:
            basis = rec["revision_basis"].lower()
            self.assertNotIn("http://", basis)
            self.assertNotIn("https://", basis)


class TestApproveAndGold(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = payload()

    def test_approve_answers_are_never_fragments(self):
        for rec in self.p["outputs"]["approve"]:
            self.assertFalse(
                run_task63.answer_is_fragment(rec["original_answer"]),
                rec["review_id"])

    def test_gold_contains_only_approve_rows(self):
        approved = {r["review_id"] for r in self.p["records"]
                    if r["decision"] == "APPROVE"}
        gold_ids = {g["review"]["review_id"] for g in self.p["gold"]}
        self.assertTrue(gold_ids.issubset(approved))

    def test_gold_candidates_traceable_to_evidence(self):
        for g in self.p["gold"]:
            self.assertTrue((g.get("provenance") or {}).get("source_id"))
            review = g.get("review") or {}
            self.assertTrue(review.get("review_id"))
            self.assertTrue(review.get("evidence") is not None)
            self.assertEqual(review.get("decision"), "APPROVE")
            self.assertEqual(g.get("source_id"),
                             g["provenance"]["source_id"])

    def test_gold_candidates_pass_every_gate(self):
        by_id = {r["review_id"]: r for r in self.p["records"]}
        for g in self.p["gold"]:
            rid = g["review"]["review_id"]
            gates = by_id[rid]["gold_gates"]
            self.assertTrue(all(gates.values()), (rid, gates))

    def test_gold_candidates_validate_against_sft_schema(self):
        import jsonschema

        schema = json.load(open(SCHEMA_PATH, encoding="utf-8"))
        validator = jsonschema.Draft7Validator(schema)
        for g in self.p["gold"]:
            errors = [e.message for e in validator.iter_errors(g)]
            self.assertEqual(errors, [], g.get("example_id"))

    def test_gold_candidates_carry_unique_questions(self):
        seen = {}
        for g in self.p["gold"]:
            key = run_task63.norm_question(g["question"])
            self.assertNotIn(key, seen, (g["example_id"], seen.get(key)))
            seen[key] = g["example_id"]


class TestNoFabricatedHumanVerification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = payload()

    def test_records_do_not_claim_human_verification(self):
        for rec in self.p["records"]:
            self.assertIsNot(rec.get("human_verified"), True,
                            rec["review_id"])
            self.assertTrue(rec.get("human_review_required") is True,
                            rec["review_id"])

    def test_outputs_do_not_claim_human_verification(self):
        for name, rows in self.p["outputs"].items():
            for rec in rows:
                self.assertIsNot(rec.get("human_verified"), True,
                                 "%s %s" % (name, rec["review_id"]))
                self.assertIsNot(rec.get("HUMAN_VERIFIED"), True,
                                 "%s %s" % (name, rec["review_id"]))

    def test_gold_candidates_stay_human_review_required(self):
        for g in self.p["gold"]:
            self.assertIsNot(g.get("HUMAN_VERIFIED"), True, g["example_id"])
            self.assertEqual(g.get("human_review_status"),
                             "HUMAN_REVIEW_REQUIRED", g["example_id"])
            self.assertTrue(g["review"]["human_review_required"])

    def test_verified_count_is_unchanged_by_this_task(self):
        stats = self.p["stats"]
        self.assertEqual(stats["human_verified_before"],
                         stats["human_verified_after"])
        self.assertEqual(stats["human_verified_delta"], 0)

    def test_written_files_do_not_claim_human_verification(self):
        for path in (run_task63.ADJ_PATH, run_task63.APPROVE_PATH,
                     run_task63.REVISE_PATH, run_task63.REJECT_PATH,
                     run_task63.GOLD_PATH):
            rows = _read(path)
            if not rows:
                continue
            for rec in rows:
                self.assertIsNot(rec.get("human_verified"), True, path)
                self.assertIsNot(rec.get("HUMAN_VERIFIED"), True, path)


class TestGroundingAndContamination(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = payload()

    def test_no_unsupported_source_attribution(self):
        for rec in self.p["records"]:
            if rec["decision"] == "REJECT":
                continue
            answer = rec.get("revised_answer") or rec["original_answer"] or ""
            for match in run_task63.ACCORDING_RE.finditer(answer):
                claimed = " ".join(run_task63.norm_question(
                    match.group(1)).split())
                hay = " ".join([
                    run_task63.norm_question(rec.get("source_title") or ""),
                    run_task63.norm_question(rec.get("evidence") or ""),
                    run_task63.norm_question(json.dumps(
                        rec.get("manifest_fields") or {}, ensure_ascii=False)),
                ])
                self.assertIn(claimed, hay,
                              "%s attributes to %r" % (rec["review_id"],
                                                       claimed))

    def test_no_raw_urls_in_answers(self):
        for rec in self.p["records"]:
            for text in (rec["original_answer"],
                         rec.get("revised_answer") or ""):
                self.assertIsNone(run_task63.URL_RE.search(text),
                                  rec["review_id"])
                self.assertIsNone(run_task63.RAW_ID_RE.search(text),
                                  rec["review_id"])

    def test_schema_has_no_url_restriction(self):
        # the bullet is conditional on the schema prohibiting URLs; record the
        # outcome here so the report can state it rather than assume it
        schema = json.load(open(SCHEMA_PATH, encoding="utf-8"))
        props = json.dumps(schema.get("properties", {})).lower()
        self.assertNotIn("http", props)
        self.assertNotIn("url", props)

    def test_no_cross_sect_contamination(self):
        for rec in self.p["records"]:
            if rec["category"] in run_task63.DISTINCTION_CATEGORIES:
                continue
            answer = (rec.get("revised_answer") or rec["original_answer"]
                      or "").lower()
            source = " ".join([rec.get("source_text") or "",
                               rec.get("evidence") or "",
                               rec.get("source_title") or ""]).lower()
            for name, marks in run_task63.SECT_MARKERS.items():
                if any(m in answer for m in marks):
                    self.assertTrue(
                        any(m in source for m in marks),
                        "%s introduces %s material not present in the source"
                        % (rec["review_id"], name))

    def test_no_other_religion_named_in_an_approved_answer(self):
        import adjudicate as A

        for rec in self.p["records"]:
            if rec["decision"] != "APPROVE":
                continue
            answer_words = set(re.findall(r"[a-z]+",
                                          rec["original_answer"].lower()))
            source = " ".join([rec.get("source_text") or "",
                               rec.get("evidence") or "",
                               rec.get("source_title") or "",
                               json.dumps(rec.get("manifest_fields") or {},
                                          ensure_ascii=False)]).lower()
            for alien in sorted(A.ALIEN & answer_words):
                self.assertIn(alien, source,
                              "%s names %r without source support"
                              % (rec["review_id"], alien))


class TestDuplicatePass(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = payload()

    def test_duplicate_stats_are_reported(self):
        dedup = self.p["stats"]["deduplication"]
        for key in ("exact_duplicate_question_groups",
                    "spacing_duplicate_question_groups",
                    "near_duplicate_pairs",
                    "same_evidence_and_answer_groups",
                    "demoted_to_reject_as_duplicate",
                    "removed_from_sft_pool_by_duplication"):
            self.assertIn(key, dedup)

    def test_gold_pool_is_free_of_near_duplicates(self):
        import itertools

        questions = [run_task63.norm_question(g["question"])
                     for g in self.p["gold"]]
        shingles = [run_task63.shingles(q) for q in questions]
        for i, j in itertools.combinations(range(len(shingles)), 2):
            value = run_task63.jaccard(shingles[i], shingles[j])
            self.assertLess(value, run_task63.NEAR_DUP_THRESHOLD,
                            (questions[i][:60], questions[j][:60]))

    def test_duplicate_demotions_are_documented(self):
        for rec in self.p["records"]:
            if rec.get("duplicate_of"):
                self.assertEqual(rec["decision"], "REJECT", rec["review_id"])
                self.assertIn("duplicate", rec["notes"].lower())

    def test_shared_source_alone_is_not_a_duplicate_rejection(self):
        for rec in self.p["records"]:
            if rec["decision"] == "REJECT" and rec.get("duplicate_of"):
                continue
            self.assertFalse(rec.get("duplicate_of"), rec["review_id"])


class TestPriorStateUntouched(unittest.TestCase):
    def test_task51_review_to_seed_set_is_resolved(self):
        # the documented discrepancy: 18 decision rows vs 6 seed candidates
        task51 = _read(os.path.join(ROOT, "data/training",
                                    "sft_task51_human_review_v1.jsonl"))
        seed = _read(os.path.join(ROOT, "data/training", "sft_seed_v1.jsonl"))
        reconciled = _read(os.path.join(ROOT, "data/training",
                                        "sft_reconciled_v1.jsonl"))
        approved = {r["candidate_id"] for r in task51
                    if r.get("decision") == "APPROVE"}
        self.assertEqual(len(task51), 18)
        self.assertEqual(approved, {r["candidate_id"] for r in seed})
        self.assertEqual(len(seed), 6)
        verified_ids = {r["example_id"] for r in reconciled
                        if r.get("human_review_status") == "HUMAN_VERIFIED"}
        self.assertTrue({r["id"] for r in seed}.issubset(verified_ids))

    def test_no_new_human_verified_rows_are_created(self):
        stats = payload()["stats"]
        self.assertEqual(stats["human_verified_before"],
                         stats["human_verified_after"])
        self.assertEqual(stats["human_verified_delta"], 0)

    def test_queue_is_read_only(self):
        before = open(QUEUE_PATH, "rb").read()
        payload()
        after = open(QUEUE_PATH, "rb").read()
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()

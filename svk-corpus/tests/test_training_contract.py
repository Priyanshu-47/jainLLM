"""Tests for training/evaluation data contracts (Task 18).

Scope: SFT schema validation, JainBench-v0 schema validation,
split leakage prevention, provenance requirements.
"""

from __future__ import annotations

import unittest

from svk_corpus.training import (
    validate_sft_example,
    validate_bench_question,
    validate_sft_batch,
    validate_bench_batch,
    assign_source_splits,
    check_split_leakage,
    check_evaluation_held_out,
    load_sft_schema,
    load_jainbench_schema,
    SFT_TASK_CATEGORIES,
    KNOWLEDGE_LAYERS,
    RELIGIOUS_SCOPES,
    ORIGIN_METHODS,
    BENCH_CATEGORIES,
)


def _valid_sft_example(**over) -> dict:
    """Create a minimal valid SFT example for testing."""
    base = {
        "example_id": "SVK-0007:qa:a1b2c3d4",
        "version": "1.0",
        "task_category": "sthanaqa",
        "messages": [
            {"role": "user", "content": "What is the Ardha Magadhi dictionary?"},
            {"role": "assistant", "content": "The Ardha Magadhi dictionary is a Prakrit lexicon."},
        ],
        "provenance": {
            "source_id": "SVK-0007",
            "text_id": "SVK-0007:u00008:215b8833",
            "knowledge_layer": "LEXICON",
            "religious_scope": "CORE_STHANAKAVASI",
        },
        "origin": {
            "synthetic": False,
            "method": "source_paraphrase",
        },
        "split": "train",
    }
    base.update(over)
    return base


def _valid_bench_question(**over) -> dict:
    """Create a minimal valid JainBench question for testing."""
    base = {
        "question_id": "JB-v0-001",
        "category": "sthanaqa_factual",
        "question": "What year was the Ardha Magadhi Dictionary first published?",
        "expected_behavior": "answer_with_citation",
        "scoring": {
            "type": "exact_match",
            "reference_answer": "1923",
            "required_citations": ["SVK-0003"],
        },
    }
    base.update(over)
    return base


class TestSFTSchemaValidation(unittest.TestCase):
    """Validate SFT examples against the contract."""

    def test_valid_example_passes(self):
        ex = _valid_sft_example()
        violations = validate_sft_example(ex)
        self.assertEqual(violations, [])

    def test_missing_required_field(self):
        ex = _valid_sft_example()
        del ex["example_id"]
        violations = validate_sft_example(ex)
        self.assertTrue(any("example_id" in v for v in violations))

    def test_invalid_version(self):
        ex = _valid_sft_example(version="2.0")
        violations = validate_sft_example(ex)
        self.assertTrue(any("version" in v for v in violations))

    def test_invalid_task_category(self):
        ex = _valid_sft_example(task_category="invalid_category")
        violations = validate_sft_example(ex)
        self.assertTrue(any("task_category" in v for v in violations))

    def test_messages_too_few(self):
        ex = _valid_sft_example(messages=[{"role": "user", "content": "hi"}])
        violations = validate_sft_example(ex)
        self.assertTrue(any("messages" in v for v in violations))

    def test_last_must_be_assistant(self):
        ex = _valid_sft_example(messages=[
            {"role": "user", "content": "question"},
            {"role": "user", "content": "another"},
        ])
        violations = validate_sft_example(ex)
        self.assertTrue(any("assistant" in v for v in violations))

    def test_empty_content_violation(self):
        ex = _valid_sft_example(messages=[
            {"role": "user", "content": "question"},
            {"role": "assistant", "content": ""},
        ])
        violations = validate_sft_example(ex)
        self.assertTrue(any("empty content" in v for v in violations))

    def test_invalid_knowledge_layer(self):
        ex = _valid_sft_example()
        ex["provenance"]["knowledge_layer"] = "INVALID_LAYER"
        violations = validate_sft_example(ex)
        self.assertTrue(any("knowledge_layer" in v for v in violations))

    def test_invalid_religious_scope(self):
        ex = _valid_sft_example()
        ex["provenance"]["religious_scope"] = "INVALID_SCOPE"
        violations = validate_sft_example(ex)
        self.assertTrue(any("religious_scope" in v for v in violations))

    def test_invalid_origin_method(self):
        ex = _valid_sft_example()
        ex["origin"]["method"] = "magic"
        violations = validate_sft_example(ex)
        self.assertTrue(any("origin.method" in v for v in violations))

    def test_invalid_split(self):
        ex = _valid_sft_example(split="trainTest")
        violations = validate_sft_example(ex)
        self.assertTrue(any("split" in v for v in violations))

    def test_all_task_categories_accepted(self):
        for cat in SFT_TASK_CATEGORIES:
            ex = _valid_sft_example(task_category=cat)
            violations = validate_sft_example(ex)
            cat_violations = [v for v in violations if "task_category" in v]
            self.assertEqual(cat_violations, [], f"category {cat!r} should be valid")


class TestBenchQuestionValidation(unittest.TestCase):
    """Validate JainBench questions against the contract."""

    def test_valid_question_passes(self):
        q = _valid_bench_question()
        violations = validate_bench_question(q)
        self.assertEqual(violations, [])

    def test_missing_required_field(self):
        q = _valid_bench_question()
        del q["question_id"]
        violations = validate_bench_question(q)
        self.assertTrue(any("question_id" in v for v in violations))

    def test_invalid_question_id_format(self):
        q = _valid_bench_question(question_id="Q001")
        violations = validate_bench_question(q)
        self.assertTrue(any("JB-v0" in v for v in violations))

    def test_invalid_category(self):
        q = _valid_bench_question(category="invalid")
        violations = validate_bench_question(q)
        self.assertTrue(any("category" in v for v in violations))

    def test_invalid_scoring_type(self):
        q = _valid_bench_question(scoring={"type": "invalid_type"})
        violations = validate_bench_question(q)
        self.assertTrue(any("scoring.type" in v for v in violations))

    def test_abstention_with_reference_answer(self):
        q = _valid_bench_question(scoring={
            "type": "abstention_check",
            "required_abstention": True,
            "reference_answer": "some answer",
        })
        violations = validate_bench_question(q)
        self.assertTrue(any("abstention" in v for v in violations))

    def test_all_bench_categories_accepted(self):
        for cat in BENCH_CATEGORIES:
            q = _valid_bench_question(category=cat)
            violations = validate_bench_question(q)
            cat_violations = [v for v in violations if "category" in v]
            self.assertEqual(cat_violations, [], f"category {cat!r} should be valid")


class TestBatchValidation(unittest.TestCase):
    """Batch validation catches duplicates and collects violations."""

    def test_sft_batch_catches_duplicates(self):
        ex = _valid_sft_example()
        violations = validate_sft_batch([ex, ex])
        all_viols = [v for viols in violations.values() for v in viols]
        self.assertTrue(any("duplicate" in v for v in all_viols))

    def test_bench_batch_catches_duplicates(self):
        q = _valid_bench_question()
        violations = validate_bench_batch([q, q])
        all_viols = [v for viols in violations.values() for v in viols]
        self.assertTrue(any("duplicate" in v for v in all_viols))


class TestSplitAssignment(unittest.TestCase):
    """Source-level split assignment prevents leakage."""

    def test_assign_source_splits(self):
        sources = [f"SVK-{i:04d}" for i in range(1, 63)]
        splits = assign_source_splits(sources)
        self.assertEqual(len(splits), 62)
        counts = {}
        for s in splits.values():
            counts[s] = counts.get(s, 0) + 1
        self.assertGreater(counts["train"], 0)
        self.assertGreater(counts["validation"], 0)
        self.assertGreater(counts["test"], 0)

    def test_split_ratios_approximate(self):
        sources = [f"SVK-{i:04d}" for i in range(1, 63)]
        splits = assign_source_splits(sources, train_ratio=0.7, val_ratio=0.15, test_ratio=0.15)
        counts = {}
        for s in splits.values():
            counts[s] = counts.get(s, 0) + 1
        total = len(sources)
        self.assertAlmostEqual(counts["train"] / total, 0.7, delta=0.1)
        self.assertAlmostEqual(counts["validation"] / total, 0.15, delta=0.1)
        self.assertAlmostEqual(counts["test"] / total, 0.15, delta=0.1)

    def test_split_deterministic(self):
        sources = [f"SVK-{i:04d}" for i in range(1, 20)]
        s1 = assign_source_splits(sources, seed=42)
        s2 = assign_source_splits(sources, seed=42)
        self.assertEqual(s1, s2)

    def test_split_ratios_must_sum_to_one(self):
        with self.assertRaises(ValueError):
            assign_source_splits(["a", "b"], train_ratio=0.5, val_ratio=0.5, test_ratio=0.5)


class TestLeakagePrevention(unittest.TestCase):
    """Split leakage detection."""

    def test_clean_splits(self):
        train = {"SVK-0001", "SVK-0002"}
        val = {"SVK-0003"}
        test = {"SVK-0004"}
        violations = check_split_leakage(train, val, test)
        self.assertEqual(violations, [])

    def test_train_val_leak(self):
        train = {"SVK-0001", "SVK-0002"}
        val = {"SVK-0002", "SVK-0003"}
        test = {"SVK-0004"}
        violations = check_split_leakage(train, val, test)
        self.assertTrue(any("train/val" in v for v in violations))

    def test_train_test_leak(self):
        train = {"SVK-0001", "SVK-0002"}
        val = {"SVK-0003"}
        test = {"SVK-0002", "SVK-0004"}
        violations = check_split_leakage(train, val, test)
        self.assertTrue(any("train/test" in v for v in violations))

    def test_val_test_leak(self):
        train = {"SVK-0001"}
        val = {"SVK-0002", "SVK-0003"}
        test = {"SVK-0003", "SVK-0004"}
        violations = check_split_leakage(train, val, test)
        self.assertTrue(any("val/test" in v for v in violations))


class TestEvaluationHeldOut(unittest.TestCase):
    """Evaluation questions must use sources not in SFT training."""

    def test_clean_held_out(self):
        eval_sources = {"SVK-0010", "SVK-0011"}
        train_sources = {"SVK-0001", "SVK-0002"}
        violations = check_evaluation_held_out(eval_sources, train_sources)
        self.assertEqual(violations, [])

    def test_overlap_detected(self):
        eval_sources = {"SVK-0002", "SVK-0010"}
        train_sources = {"SVK-0001", "SVK-0002"}
        violations = check_evaluation_held_out(eval_sources, train_sources)
        self.assertTrue(any("SVK-0002" in v for v in violations))


class TestSchemaLoading(unittest.TestCase):
    """Schema files are loadable."""

    def test_load_sft_schema(self):
        schema = load_sft_schema()
        self.assertIn("properties", schema)
        self.assertIn("example_id", schema["properties"])

    def test_load_jainbench_schema(self):
        schema = load_jainbench_schema()
        self.assertIn("properties", schema)
        self.assertIn("questions", schema["properties"])


if __name__ == "__main__":
    unittest.main()

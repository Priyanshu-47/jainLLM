"""Training/Evaluation data contract validators (Task 18).

Provides JSON Schema validation for:
- SFT examples (sft_schema_v1.json)
- JainBench-v0 questions (jainbench_schema_v1.json)

Also implements split leakage prevention rules:
- No near-duplicate source passages across train/validation/test
- Evaluation questions held out from SFT training data
- Source-level split assignment (not unit-level) to prevent leakage
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

_SCHEMA_DIR = Path(__file__).resolve().parents[3] / "data"
_SFT_SCHEMA_PATH = _SCHEMA_DIR / "training" / "sft_schema_v1.json"
_BENCH_SCHEMA_PATH = _SCHEMA_DIR / "evaluation" / "jainbench_schema_v1.json"

# Controlled vocabularies
SFT_TASK_CATEGORIES = {
    "sthanaqa",
    "source_citation",
    "prakrit_explanation",
    "multilingual_mapping",
    "teacher_attribution",
    "canonical_commentary_distinction",
    "cross_tradition_distinction",
    "abstention",
    "general_qa",
}

KNOWLEDGE_LAYERS = {
    "CANONICAL_SCRIPTURE",
    "COMMENTARY",
    "TEACHER_INTERPRETATION",
    "LEXICON",
    "SECONDARY_SCHOLARSHIP",
    "REFERENCE",
    "INSTRUCTION_DATA",
    "MIXED",
}

RELIGIOUS_SCOPES = {
    "CORE_STHANAKAVASI",
    "HIGH_STHANAKAVASI_RELEVANCE",
    "COMPARATIVE_OTHER_TRADITION",
    "CONTEXTUAL_JAIN",
    "UNKNOWN",
}

SECT_CONFIDENCE = {"HIGH", "MEDIUM", "LOW", "UNKNOWN"}
SOURCE_QUALITY = {"HIGH", "MEDIUM", "LOW", "UNKNOWN"}

ORIGIN_METHODS = {
    "human_authored",
    "source_paraphrase",
    "extraction",
    "translation",
    "synthetic_qa_generation",
    "synthetic_abstention",
    "expert_reviewed",
}

BENCH_CATEGORIES = {
    "sthanaqa_factual",
    "sthanaqa_doctrinal",
    "sthanaqa_history",
    "source_citation",
    "prakrit_term",
    "multilingual",
    "teacher_attribution",
    "canonical_commentary",
    "cross_tradition",
    "abstention",
    "conflicting_sources",
}

BENCH_SCORING_TYPES = {
    "exact_match",
    "fuzzy_match",
    "citation_check",
    "abstention_check",
    "likert",
    "rubric",
}


def _load_schema(path: Path) -> dict[str, Any]:
    """Load a JSON schema file."""
    return json.loads(path.read_text(encoding="utf-8"))


def load_sft_schema() -> dict[str, Any]:
    """Load the SFT example schema v1."""
    return _load_schema(_SFT_SCHEMA_PATH)


def load_jainbench_schema() -> dict[str, Any]:
    """Load the JainBench-v0 schema."""
    return _load_schema(_BENCH_SCHEMA_PATH)


def validate_sft_example(example: dict[str, Any]) -> list[str]:
    """Validate an SFT example against the schema and project rules.

    Returns a list of violation descriptions (empty if valid).
    """
    violations: list[str] = []

    # Required top-level fields
    required = ["example_id", "version", "task_category", "messages", "provenance", "origin", "split"]
    for field in required:
        if field not in example:
            violations.append(f"missing required field: {field}")

    # Version check
    if example.get("version") != "1.0":
        violations.append(f"invalid version: {example.get('version')!r} (expected '1.0')")

    # Task category
    cat = example.get("task_category", "")
    if cat not in SFT_TASK_CATEGORIES:
        violations.append(f"invalid task_category: {cat!r}")

    # Messages structure
    msgs = example.get("messages", [])
    if not isinstance(msgs, list) or len(msgs) < 2:
        violations.append("messages must be a list with at least 2 entries")
    else:
        roles = [m.get("role") for m in msgs]
        if roles[0] not in ("system", "user"):
            violations.append(f"first message role must be 'system' or 'user', got {roles[0]!r}")
        if roles[-1] != "assistant":
            violations.append(f"last message role must be 'assistant', got {roles[-1]!r}")
        for i, m in enumerate(msgs):
            if not m.get("content"):
                violations.append(f"message[{i}] has empty content")

    # Provenance
    prov = example.get("provenance", {})
    if not isinstance(prov, dict):
        violations.append("provenance must be an object")
    else:
        for field in ["source_id", "text_id", "knowledge_layer", "religious_scope"]:
            if not prov.get(field):
                violations.append(f"provenance missing required field: {field}")
        if prov.get("knowledge_layer") not in KNOWLEDGE_LAYERS:
            violations.append(f"invalid knowledge_layer: {prov.get('knowledge_layer')!r}")
        if prov.get("religious_scope") not in RELIGIOUS_SCOPES:
            violations.append(f"invalid religious_scope: {prov.get('religious_scope')!r}")

    # Origin
    origin = example.get("origin", {})
    if not isinstance(origin, dict):
        violations.append("origin must be an object")
    else:
        if "synthetic" not in origin:
            violations.append("origin missing 'synthetic' field")
        if origin.get("method") not in ORIGIN_METHODS:
            violations.append(f"invalid origin.method: {origin.get('method')!r}")

    # Split
    if example.get("split") not in ("train", "validation", "test"):
        violations.append(f"invalid split: {example.get('split')!r}")

    # Quality flags
    for flag in example.get("quality_flags", []):
        valid_flags = {
            "needs_review", "low_confidence", "conflicting_info",
            "ocr_noisy", "translation_uncertain", "synthetic_unverified"
        }
        if flag not in valid_flags:
            violations.append(f"invalid quality_flag: {flag!r}")

    return violations


def validate_bench_question(question: dict[str, Any]) -> list[str]:
    """Validate a JainBench-v0 question against the schema and project rules.

    Returns a list of violation descriptions (empty if valid).
    """
    violations: list[str] = []

    # Required fields
    for field in ["question_id", "category", "question", "expected_behavior", "scoring"]:
        if field not in question:
            violations.append(f"missing required field: {field}")

    # Question ID format
    qid = question.get("question_id", "")
    if qid and not qid.startswith("JB-v0-"):
        violations.append(f"question_id must start with 'JB-v0-': {qid!r}")

    # Category
    cat = question.get("category", "")
    if cat and cat not in BENCH_CATEGORIES:
        violations.append(f"invalid category: {cat!r}")

    # Scoring
    scoring = question.get("scoring", {})
    if isinstance(scoring, dict):
        stype = scoring.get("type", "")
        if stype and stype not in BENCH_SCORING_TYPES:
            violations.append(f"invalid scoring.type: {stype!r}")
        if scoring.get("required_abstention") and scoring.get("reference_answer"):
            violations.append("abstention questions should not have a reference_answer")

    return violations


def validate_sft_batch(examples: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Validate a batch of SFT examples, returning violations keyed by example_id."""
    all_violations: dict[str, list[str]] = {}
    seen_ids: set[str] = set()
    for ex in examples:
        eid = ex.get("example_id", f"unknown_{len(seen_ids)}")
        viols = validate_sft_example(ex)
        if eid in seen_ids:
            viols.append(f"duplicate example_id: {eid!r}")
        seen_ids.add(eid)
        if viols:
            all_violations[eid] = viols
    return all_violations


def validate_bench_batch(questions: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Validate a batch of JainBench questions, returning violations keyed by question_id."""
    all_violations: dict[str, list[str]] = {}
    seen_ids: set[str] = set()
    for q in questions:
        qid = q.get("question_id", f"unknown_{len(seen_ids)}")
        viols = validate_bench_question(q)
        if qid in seen_ids:
            viols.append(f"duplicate question_id: {qid!r}")
        seen_ids.add(qid)
        if viols:
            all_violations[qid] = viols
    return all_violations


# ---------------------------------------------------------------------------
# Split leakage prevention
# ---------------------------------------------------------------------------

def _text_hash(text: str) -> str:
    """Deterministic short hash for text deduplication."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def assign_source_splits(
    source_ids: list[str],
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42,
) -> dict[str, str]:
    """Assign source IDs to train/val/test splits.

    Uses source-level assignment: all units from one source go to the same split.
    This prevents near-duplicate passages from leaking across splits.

    The split is deterministic given the same inputs (seed-based shuffling).
    """
    import random
    if not (0.99 <= train_ratio + val_ratio + test_ratio <= 1.01):
        raise ValueError(f"Ratios must sum to ~1.0, got {train_ratio + val_ratio + test_ratio}")

    rng = random.Random(seed)
    shuffled = list(source_ids)
    rng.shuffle(shuffled)

    n = len(shuffled)
    n_train = int(n * train_ratio)
    n_val = int(n * val_ratio)

    splits: dict[str, str] = {}
    for i, sid in enumerate(shuffled):
        if i < n_train:
            splits[sid] = "train"
        elif i < n_train + n_val:
            splits[sid] = "validation"
        else:
            splits[sid] = "test"
    return splits


def check_split_leakage(
    train_sources: set[str],
    val_sources: set[str],
    test_sources: set[str],
) -> list[str]:
    """Check for source-level leakage across splits.

    Returns a list of violations (empty if clean).
    """
    violations: list[str] = []
    train_val = train_sources & val_sources
    train_test = train_sources & test_sources
    val_test = val_sources & test_sources
    if train_val:
        violations.append(f"train/val overlap: {sorted(train_val)}")
    if train_test:
        violations.append(f"train/test overlap: {sorted(train_test)}")
    if val_test:
        violations.append(f"val/test overlap: {sorted(val_test)}")
    return violations


def check_evaluation_held_out(
    eval_source_ids: set[str],
    train_source_ids: set[str],
) -> list[str]:
    """Check that evaluation questions use sources not in SFT training data.

    Returns a list of violations (empty if clean).
    """
    overlap = eval_source_ids & train_source_ids
    if overlap:
        return [f"evaluation sources in training data: {sorted(overlap)}"]
    return []

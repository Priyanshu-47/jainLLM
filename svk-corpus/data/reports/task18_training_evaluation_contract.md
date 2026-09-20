# Task 18: JainLLM Training/Evaluation Data Contract

## Goal

Design versioned schemas and validators for SFT training examples and JainBench-v0 evaluation questions, with provenance traceability and split leakage prevention.

## Files Created

| File | Description |
|------|-------------|
| `data/training/sft_schema_v1.json` | JSON Schema for SFT examples |
| `data/evaluation/jainbench_schema_v1.json` | JSON Schema for JainBench-v0 questions |
| `src/svk_corpus/training/__init__.py` | Validation utilities + split rules |
| `tests/test_training_contract.py` | 33 tests for validation |
| `data/reports/task18_training_evaluation_contract.md` | This report |

## SFT Schema Design (`sft_schema_v1.json`)

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `example_id` | string | `<source_id>:<unit_type>:<hash8>` |
| `version` | "1.0" | Schema version |
| `task_category` | enum | Training category (see below) |
| `messages` | array | `[user, assistant]` or `[system, user, assistant]` |
| `provenance` | object | Source traceability (source_id, text_id, knowledge_layer, religious_scope) |
| `origin` | object | synthetic flag + method |
| `split` | "train"/"validation"/"test" | Data split |

### Task Categories

| Category | Description |
|----------|-------------|
| `sthanaqa` | Sthanakavasi sect-aware Q&A |
| `source_citation` | Answer with source citation |
| `prakrit_explanation` | Prakrit term → explanation |
| `multilingual_mapping` | Gujarati/Hindi/English transfer |
| `teacher_attribution` | Teacher/acarya attribution |
| `canonical_commentary_distinction` | Canonical vs commentary vs interpretation |
| `cross_tradition_distinction` | Sthanakavasi vs Digambara vs other |
| `abstention` | Insufficient evidence response |
| `general_qa` | General Q&A not fitting above |

### Provenance Requirements

Every factual SFT example MUST carry:
- `source_id` — maps to `manifests/source_manifest.csv`
- `text_id` — maps to RAG/training corpus unit
- `knowledge_layer` — CANONICAL_SCRIPTURE, COMMENTARY, TEACHER_INTERPRETATION, LEXICON, SECONDARY_SCHOLARSHIP, REFERENCE, INSTRUCTION_DATA, MIXED
- `religious_scope` — CORE_STHANAKAVASI, HIGH_STHANAKAVASI_RELEVANCE, COMPARATIVE_OTHER_TRADITION, CONTEXTUAL_JAIN, UNKNOWN

Optional provenance: title, author, publication_year, language, sect, sect_confidence, teacher_or_author, lineage, source_quality, locator, license_status, citation_text.

### Origin Tracking

| Field | Values |
|-------|--------|
| `synthetic` | true/false |
| `method` | human_authored, source_paraphrase, extraction, translation, synthetic_qa_generation, synthetic_abstention, expert_reviewed |
| `reviewer` | Human reviewer name (if expert_reviewed) |
| `confidence` | high/medium/low |

## JainBench-v0 Schema Design (`jainbench_schema_v1.json`)

### Structure

- `bench_version`: "jainbench-v0"
- `total_questions`: 150-200
- `questions[]`: Array of BenchQuestion objects
- `categories`: Category distribution with counts
- `metadata`: corpus_version, held_out_sources, scoring_protocol

### BenchQuestion Categories

| Category | Count Target | Description |
|----------|-------------|-------------|
| `sthanaqa_factual` | 25-30 | Factual Sthanakavasi questions |
| `sthanaqa_doctrinal` | 20-25 | Doctrinal Sthanakavasi questions |
| `sthanaqa_history` | 15-20 | Historical Sthanakavasi questions |
| `source_citation` | 20-25 | Must cite specific sources |
| `prakrit_term` | 15-20 | Prakrit term explanations |
| `multilingual` | 15-20 | Cross-language questions |
| `teacher_attribution` | 10-15 | Teacher/author attribution |
| `canonical_commentary` | 15-20 | Canonical vs commentary distinction |
| `cross_tradition` | 15-20 | Cross-tradition comparison |
| `abstention` | 15-20 | Must abstain (insufficient evidence) |
| `conflicting_sources` | 5-10 | Conflicting source handling |

### Scoring Types

| Type | Description |
|------|-------------|
| `exact_match` | Exact string match |
| `fuzzy_match` | Fuzzy/semantic match |
| `citation_check` | Verify required citations present |
| `abstention_check` | Verify model abstains |
| `likert` | Likert scale rating |
| `rubric` | Multi-criteria rubric with weights |

## Split Leakage Prevention

### Rules

1. **Source-level assignment**: All units from one source go to the same split. This prevents near-duplicate passages from leaking across splits.

2. **Deterministic**: `assign_source_splits(sources, seed=42)` produces identical splits given the same inputs.

3. **Default ratios**: 70% train, 15% validation, 15% test.

4. **Validation**: `check_split_leakage()` detects any source appearing in multiple splits.

5. **Evaluation held-out**: `check_evaluation_held_out()` ensures JainBench sources are NOT in SFT training data.

### Implementation

```python
# Assign splits
splits = assign_source_splits(source_ids, seed=42)

# Check for leakage
violations = check_split_leakage(train_sources, val_sources, test_sources)

# Check evaluation held-out
violations = check_evaluation_held_out(eval_sources, train_sources)
```

## Validation Utilities (`training/__init__.py`)

### Functions

| Function | Description |
|----------|-------------|
| `validate_sft_example(example)` | Validate one SFT example |
| `validate_sft_batch(examples)` | Validate batch, catch duplicates |
| `validate_bench_question(question)` | Validate one JainBench question |
| `validate_bench_batch(questions)` | Validate batch, catch duplicates |
| `assign_source_splits(sources)` | Deterministic source-level split |
| `check_split_leakage(train, val, test)` | Detect cross-split leakage |
| `check_evaluation_held_out(eval, train)` | Detect eval/train overlap |
| `load_sft_schema()` | Load SFT JSON Schema |
| `load_jainbench_schema()` | Load JainBench JSON Schema |

### Controlled Vocabularies

- `SFT_TASK_CATEGORIES` — 9 values
- `KNOWLEDGE_LAYERS` — 8 values
- `RELIGIOUS_SCOPES` — 5 values
- `ORIGIN_METHODS` — 7 values
- `BENCH_CATEGORIES` — 11 values
- `BENCH_SCORING_TYPES` — 6 values

## Tests

33 new tests, 224 total. All pass.

| Test Class | Tests | Coverage |
|------------|-------|----------|
| TestSFTSchemaValidation | 12 | Required fields, version, categories, messages, provenance, origin, split |
| TestBenchQuestionValidation | 7 | Required fields, ID format, categories, scoring, abstention |
| TestBatchValidation | 2 | Duplicate detection |
| TestSplitAssignment | 4 | Ratios, determinism, validation |
| TestLeakagePrevention | 4 | Train/val, train/test, val/test overlap |
| TestEvaluationHeldOut | 2 | Eval/train overlap |
| TestSchemaLoading | 2 | Schema file loading |

## Unresolved Decisions

1. **JainBench-v0 questions**: Schema defined, 150-200 questions NOT yet created (deferred to future task).
2. **Base model selection**: Not decided in this task.
3. **SFT data generation**: No synthetic Q&A created in this task.
4. **Source ingestion**: No new sources ingested.
5. **Retrieval code**: Not modified.

## Design Rationale

- **Source-level splits** (not unit-level): Units from the same source are near-duplicates. Splitting at unit level would leak training data into test set.
- **Provenance-first**: Every factual example traces to a source_id + text_id. This prevents hallucinated training data.
- **Explicit abstention category**: The model must learn to say "I don't know" when evidence is insufficient. This is a core safety requirement.
- **Knowledge layer distinction**: Canonical scripture, commentary, and teacher interpretation are different epistemological categories that must not be conflated.
- **Cross-tradition awareness**: The model must distinguish Sthanakavasi-specific content from generic Jain or Digambara content.

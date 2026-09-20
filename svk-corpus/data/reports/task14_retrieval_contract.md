# Task 14 — Retrieval Evidence Contract

**Date:** 2026-09-18 · **Scope:** Define canonical retrieval result schema and evidence contract to make evidence types distinguishable for future RAG/LLM generation layers.

---

## 1. Purpose

Define a single canonical retrieval-result contract that makes it impossible for a future generation layer to confuse:

> "The query matched this passage" (unit_bm25)

with:

> "The query matched metadata about the source containing this passage" (source_metadata)

These are different evidence types and must remain distinguishable.

## 2. Canonical Result Schema

### 2.1 Identity Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `result_id` | str | Yes | Unique identifier (typically unit_id) |
| `source_id` | str | Yes | Source this unit belongs to |
| `parent_source_id` | str | No | Edition parent (if any) |

### 2.2 Content Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `text` | str | Yes | Original unit text — IMMUTABLE, never modified by normalization |
| `title` | str | Yes | Source title |
| `locator` | dict | No | Page/location information |

### 2.3 Provenance Fields (Descriptive, Not Authority)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `religious_scope` | str | "UNKNOWN" | Descriptive metadata, NOT a truth/authority score |
| `religious_scope_confidence` | str | "UNKNOWN" | Confidence in scope classification |
| `knowledge_layer` | str | "" | Descriptive metadata, NOT a truth/authority score |
| `teacher_or_author` | str | "" | Named teacher or author |
| `lineage` | str | "" | Religious lineage |
| `source_quality` | str | "" | Artifact/OCR fidelity |

### 2.4 Retrieval Evidence Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `retrieval_channel` | RetrievalChannel | Yes | HOW this result was found |
| `retrieval_rank` | int | Yes | Rank within this channel's results |
| `retrieval_score` | float | Yes | Score (channel-specific scale) |
| `unit_bm25_rank` | int \| None | Conditional | Present only for unit_bm25 results |
| `unit_bm25_score` | float \| None | Conditional | Present only for unit_bm25 results |
| `metadata_match` | MetadataMatchEvidence \| None | Conditional | Present only for source_metadata results |
| `normalization` | NormalizationEvidence \| None | No | Optional query normalization evidence |
| `methods` | dict[str, int] | No | Audit trail of contributing methods |

## 3. Retrieval Channels

### 3.1 Controlled Values

```python
class RetrievalChannel(str, Enum):
    UNIT_BM25 = "unit_bm25"
    SOURCE_METADATA = "source_metadata"
    SOURCE_METADATA_EXPANSION = "source_metadata_expansion"
    DENSE = "dense"  # RESERVED — currently unavailable
```

### 3.2 Evidence Semantics

#### `unit_bm25`
The query matched searchable text associated with the retrieved unit.

**Contract requirements:**
- Must have `unit_bm25_rank` and `unit_bm25_score`
- Must NOT have `metadata_match`
- Text is the direct match target

#### `source_metadata`
The query matched source metadata (title/author/etc.), not unit text.

**Contract requirements:**
- Must have `metadata_match` with field/value evidence
- Must NOT have `unit_bm25_rank` or `unit_bm25_score`
- The unit is a representative from the source, not a match

#### `source_metadata_expansion`
The unit was returned because its source matched metadata via edition-family expansion.

**Contract requirements:**
- Must have `metadata_match` with `via_family=True`
- Must NOT have `unit_bm25_rank` or `unit_bm25_score`
- The unit itself did NOT match the query

#### `dense` (RESERVED)
Reserved for future semantic retrieval.

**Current status:** NOT available (no embedding model installed). Must not appear in measured results.

## 4. Normalization Evidence

When retrieval normalization is applied, it is recorded as attachment-only:

```python
@dataclass(frozen=True)
class NormalizationEvidence:
    original_query: str           # User's original query, unmodified
    normalized_tokens: tuple[str, ...]  # Token stream after fold+alias
    aliases_applied: tuple[str, ...]    # Which alias expansions triggered
    phrase_rules_triggered: tuple[str, ...]  # Which phrase rules triggered
```

**Key principle:** Normalization never modifies original text. The returned corpus text must remain unchanged.

## 5. Provenance Invariants

1. **Original corpus text is immutable** from the retrieval layer.
2. **Retrieval normalization does not modify source provenance.**
3. **Metadata retrieval is never represented as body-text evidence.**
4. **Source-to-unit expansion remains explicitly labelled.**
5. **A source match does not imply every unit in that source is relevant.**
6. **Unknown provenance remains unknown.**
7. **`religious_scope` is descriptive metadata, NOT a truth/authority score.**
8. **`knowledge_layer` is descriptive metadata, NOT a truth/authority score.**
9. **Dense retrieval cannot claim availability when no dense model exists.**
10. **Retrieval scores must retain their channel meaning** and must not be compared as if scores from different channels were inherently equivalent.

## 6. Validation Rules

### 6.1 Required Fields
- `source_id` must not be empty
- `result_id` must not be empty
- `text` must not be empty (except for source_metadata_expansion)

### 6.2 Channel-Specific Rules

**unit_bm25:**
- Must have `unit_bm25_rank` (not None)
- Must have `unit_bm25_score` (not None)
- Must NOT have `metadata_match`

**source_metadata / source_metadata_expansion:**
- Must have `metadata_match` (not None)
- Must NOT have `unit_bm25_rank` (must be None)
- Must NOT have `unit_bm25_score` (must be None)

**dense:**
- Currently RESERVED — must not appear in measured results

### 6.3 Validation Functions

```python
def validate_result(result: CanonicalResult) -> list[str]:
    """Return list of violations (empty if valid)."""

def assert_valid(result: CanonicalResult) -> None:
    """Raise ContractViolation if invalid."""

def validate_batch(results: list[CanonicalResult]) -> dict[str, list[str]]:
    """Validate batch, return violations keyed by result_id."""
```

## 7. Valid Examples

### 7.1 Unit BM25 Result

```python
CanonicalResult(
    result_id="SVK-0007:u00123",
    source_id="SVK-0007",
    text="The Sutrakrtanga begins with the ascetic's conduct.",
    title="Ardha Magadhi Dictionary",
    retrieval_channel=RetrievalChannel.UNIT_BM25,
    retrieval_rank=1,
    retrieval_score=4.2,
    unit_bm25_rank=1,
    unit_bm25_score=4.2,
    religious_scope="CORE_STHANAKAVASI",
)
```

### 7.2 Source Metadata Result

```python
CanonicalResult(
    result_id="SVK-2005:u00001",
    source_id="SVK-2005",
    text="Woolner's dictionary edition...",
    title="Illustrated Dictionary Gujarati",
    retrieval_channel=RetrievalChannel.SOURCE_METADATA,
    retrieval_rank=10,
    retrieval_score=0.0,
    metadata_match=MetadataMatchEvidence(
        source_id="SVK-2005",
        matched_field="author",
        matched_value="Muni Ratnachandraji Maharaj",
        matched_token="ratnachandraji",
        weight=3.0,
    ),
)
```

### 7.3 Source Metadata Expansion Result

```python
CanonicalResult(
    result_id="SVK-2002:u00001",
    source_id="SVK-2002",
    text="Woolner's illustrated edition...",
    title="Illustrated Dictionary Gujarati",
    retrieval_channel=RetrievalChannel.SOURCE_METADATA_EXPANSION,
    retrieval_rank=11,
    retrieval_score=0.0,
    metadata_match=MetadataMatchEvidence(
        source_id="SVK-2002",
        matched_field="author",
        matched_value="A. C. Woolner",
        matched_token="woolner",
        weight=3.0,
        via_family=True,
        family_root="SVK-0007",
    ),
)
```

## 8. Invalid Examples

### 8.1 Metadata Result Falsely Claiming Body-Text Match

```python
# INVALID: metadata result has unit_bm25_rank
CanonicalResult(
    result_id="...",
    source_id="...",
    text="...",
    title="...",
    retrieval_channel=RetrievalChannel.SOURCE_METADATA,
    unit_bm25_rank=1,  # VIOLATION: metadata match is not a body-text match
    metadata_match=...,
)
```

### 8.2 BM25 Result Missing Evidence

```python
# INVALID: BM25 result missing rank/score
CanonicalResult(
    result_id="...",
    source_id="...",
    text="...",
    title="...",
    retrieval_channel=RetrievalChannel.UNIT_BM25,
    unit_bm25_rank=None,  # VIOLATION: must have rank
    unit_bm25_score=None,  # VIOLATION: must have score
)
```

### 8.3 Dense Result When Unavailable

```python
# INVALID: dense channel is RESERVED
CanonicalResult(
    result_id="...",
    source_id="...",
    text="...",
    title="...",
    retrieval_channel=RetrievalChannel.DENSE,  # VIOLATION: currently unavailable
)
```

## 9. Future Dense Compatibility

The contract is designed to accommodate dense retrieval when available:

1. Add `dense_rank` and `dense_score` fields (optional, default None)
2. Add `embedding_model` field to record which model was used
3. Keep `retrieval_channel=RetrievalChannel.DENSE` for dense results
4. Dense results will have their own evidence fields, separate from BM25

**Current status:** Dense channel is RESERVED. No dense model is installed. The `DenseRetriever` interface exists but `UnavailableDense` is the honest default.

## 10. Regression Results

### 10.1 Test Suite

```
Ran 185 tests in 19.040s — OK
```

- Original tests: 148/148 passing
- New contract tests: 37/37 passing
- Total: 185/185 passing

### 10.2 Key Regression Checks

| Check | Status |
|-------|--------|
| q09 source-level recovery | ✓ SVK-2005 reached via source_metadata |
| q17 rank-1 | ✓ જૈન ધર્મ remains rank-1 |
| q19 corpus-gap probe | ✓ No fake fill added |
| Task 9 romanization recovery | ✓ Sutrakritanga ↔ Sutrakrtanga intact |
| Gujarati tokenizer fix | ✓ જૈન/જિન remain distinct |
| Task 11 diversification | ✓ Edition-aware cap working |

### 10.3 No Behavioral Changes

- BM25 scoring unchanged
- No new aliases added
- No corpus/gate/release modifications
- Existing retrieval behavior preserved

---

**Measured vs interpretation:** Schema and validation rules are engineering definitions. Regression results are measured. Provenance invariants are design principles.

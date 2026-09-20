"""Retrieval Evidence Contract (Task 14).

Purpose
-------
Define a canonical retrieval-result structure that makes it impossible for a
future generation layer to confuse:

  "The query matched this passage" (unit_bm25)

with:

  "The query matched metadata about the source containing this passage"
  (source_metadata / source_metadata_expansion)

These are different evidence types and must remain distinguishable.

Design principles
-----------------
1. ORIGINAL TEXT IS IMMUTABLE. Retrieval normalization never modifies corpus
   text; every result exposes the original unit text and full provenance.
2. CHANNEL IS EXPLICIT. Every result carries a controlled retrieval_channel
   value that describes HOW it was found.
3. EVIDENCE IS PRESERVED. Normalization/alias information is attached but
   never replaces original text.
4. PROVENANCE IS INVARIANT. Metadata fields are descriptive, not authority
   scores. religious_scope and knowledge_layer are metadata, not truth.
  5. DENSE IS A REAL CHANNEL (Task 16). The "dense" channel produces
    results when a SentenceTransformer model is available. Dense results
    carry dense_rank/dense_score instead of unit_bm25 fields.

Current channels
----------------
- unit_bm25: query matched searchable text associated with the unit
- source_metadata: query matched source metadata (title/author/etc.)
- source_metadata_expansion: unit returned because its source matched metadata
- dense: semantic retrieval via dense embedding similarity (Task 16)

Future channels
---------------
Dense retrieval will add a "dense" channel when an embedding model is
available. The contract is designed to accommodate this without breaking
changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Controlled channel values
# ---------------------------------------------------------------------------

class RetrievalChannel(str, Enum):
    """Controlled vocabulary for retrieval evidence types.

    Each value describes HOW the result was found, not what it means.
    """
    UNIT_BM25 = "unit_bm25"
    SOURCE_METADATA = "source_metadata"
    SOURCE_METADATA_EXPANSION = "source_metadata_expansion"
    DENSE = "dense"  # Task 16: real semantic retrieval channel

    @classmethod
    def available_channels(cls) -> set[str]:
        """Channels currently producing real results."""
        return {cls.UNIT_BM25.value, cls.SOURCE_METADATA.value,
                cls.SOURCE_METADATA_EXPANSION.value, cls.DENSE.value}

    @classmethod
    def reserved_channels(cls) -> set[str]:
        """Channels defined but not yet producing real results."""
        return set()


# ---------------------------------------------------------------------------
# Normalization evidence
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class NormalizationEvidence:
    """Record of what retrieval normalization did to a query.

    This is ATTACHMENT ONLY — it never modifies the original query or
    corpus text. A future generation layer can use this to explain
    "your query 'X' matched because we searched for 'Y'".
    """

    original_query: str
    """The user's original query, unmodified."""

    normalized_tokens: tuple[str, ...]
    """The token stream after fold+alias expansion.

    For example, query "Sutrakritanga" becomes ("sutrakritanga", "sutrakrtanga").
    """

    aliases_applied: tuple[str, ...] = ()
    """Which alias expansions were triggered (the canonical keys)."""

    phrase_rules_triggered: tuple[str, ...] = ()
    """Which phrase rules were triggered (the canonical forms)."""


# ---------------------------------------------------------------------------
# Metadata match evidence
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MetadataMatchEvidence:
    """Evidence that a source was matched via metadata, not unit text.

    This is the key distinction: a source_metadata result means "the query
    matched this source's metadata", NOT "this unit's text matches the query".
    """

    source_id: str
    matched_field: str
    """Which metadata field matched (e.g. 'author', 'title')."""

    matched_value: str
    """The actual value that matched (e.g. 'Muni Ratnachandraji')."""

    matched_token: str
    """The specific token that triggered the match."""

    weight: float
    """Field weight (reach-based, not relevance)."""

    via_family: bool = False
    """True if this source was reached via edition-family expansion."""

    family_root: str = ""
    """The root source of the edition family (if via_family)."""


# ---------------------------------------------------------------------------
# Canonical retrieval result
# ---------------------------------------------------------------------------

@dataclass
class CanonicalResult:
    """A retrieval result that preserves all evidence and provenance.

    This is the canonical structure that all retrieval channels must
    produce. It extends the existing RetrievalResult with explicit
    contract enforcement.
    """

    # Identity
    result_id: str
    """Unique identifier for this result (typically unit_id)."""

    source_id: str
    """The source this unit belongs to."""

    # Content
    text: str
    """Original unit text — IMMUTABLE, never modified by normalization."""

    title: str
    """Source title."""

    parent_source_id: str = ""
    """Edition parent (if any)."""

    locator: dict[str, Any] = field(default_factory=dict)
    """Page/location information."""

    # Provenance (descriptive, not authority)
    religious_scope: str = "UNKNOWN"
    religious_scope_confidence: str = "UNKNOWN"
    knowledge_layer: str = ""
    teacher_or_author: str = ""
    lineage: str = ""
    source_quality: str = ""

    # Retrieval evidence
    retrieval_channel: RetrievalChannel = RetrievalChannel.UNIT_BM25
    """HOW this result was found — the key contract field."""

    retrieval_rank: int = 0
    """Rank within this channel's results."""

    retrieval_score: float = 0.0
    """Score within this channel (channel-specific scale)."""

    # Unit-level BM25 evidence (present only for unit_bm25 results)
    unit_bm25_rank: int | None = None
    unit_bm25_score: float | None = None

    # Dense retrieval evidence (present only for dense results)
    dense_rank: int | None = None
    dense_score: float | None = None

    # Source metadata evidence (present only for source_metadata results)
    metadata_match: MetadataMatchEvidence | None = None

    # Normalization evidence (optional, for query解释)
    normalization: NormalizationEvidence | None = None

    # Audit trail
    methods: dict[str, int] = field(default_factory=dict)
    """Which retrieval methods contributed and their ranks."""

    def provenance(self) -> dict[str, Any]:
        """Export provenance for downstream consumption."""
        return {
            "result_id": self.result_id,
            "source_id": self.source_id,
            "parent_source_id": self.parent_source_id,
            "title": self.title,
            "locator": self.locator,
            "religious_scope": self.religious_scope,
            "religious_scope_confidence": self.religious_scope_confidence,
            "knowledge_layer": self.knowledge_layer,
            "teacher_or_author": self.teacher_or_author,
            "lineage": self.lineage,
            "source_quality": self.source_quality,
            "retrieval_channel": self.retrieval_channel.value,
            "retrieval_rank": self.retrieval_rank,
            "retrieval_score": self.retrieval_score,
            "unit_bm25_rank": self.unit_bm25_rank,
            "unit_bm25_score": self.unit_bm25_score,
            "metadata_match": self.metadata_match.__dict__ if self.metadata_match else None,
            "normalization": self.normalization.__dict__ if self.normalization else None,
            "methods": dict(sorted(self.methods.items())),
        }


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class ContractViolation(Exception):
    """Raised when a retrieval result violates the evidence contract."""
    pass


def validate_result(result: CanonicalResult) -> list[str]:
    """Validate a CanonicalResult against the evidence contract.

    Returns a list of violation descriptions (empty if valid).
    Does NOT raise — callers decide whether to error or warn.
    """
    violations: list[str] = []

    # Required fields
    if not result.source_id:
        violations.append("missing source_id")
    if not result.result_id:
        violations.append("missing result_id")

    # Channel validation
    channel = result.retrieval_channel
    if channel not in RetrievalChannel:
        violations.append(f"invalid retrieval_channel: {channel!r}")

    # Unit BM25 results must have textual evidence
    if channel == RetrievalChannel.UNIT_BM25:
        if result.unit_bm25_rank is None:
            violations.append("unit_bm25 result missing unit_bm25_rank")
        if result.unit_bm25_score is None:
            violations.append("unit_bm25 result missing unit_bm25_score")
        if result.metadata_match is not None:
            violations.append("unit_bm25 result should not have metadata_match")

    # Source metadata results must NOT claim body-text match
    if channel in (RetrievalChannel.SOURCE_METADATA,
                   RetrievalChannel.SOURCE_METADATA_EXPANSION):
        if result.metadata_match is None:
            violations.append(f"{channel.value} result missing metadata_match")
        if result.unit_bm25_rank is not None:
            violations.append(f"{channel.value} result should not have unit_bm25_rank "
                             "(metadata match is not a body-text match)")
        if result.unit_bm25_score is not None:
            violations.append(f"{channel.value} result should not have unit_bm25_score "
                             "(metadata match is not a body-text match)")

    # Dense results must have dense rank/score, must not have BM25 or metadata fields
    if channel == RetrievalChannel.DENSE:
        if result.dense_rank is None:
            violations.append("dense result missing dense_rank")
        if result.dense_score is None:
            violations.append("dense result missing dense_score")
        if result.unit_bm25_rank is not None:
            violations.append("dense result should not have unit_bm25_rank")
        if result.unit_bm25_score is not None:
            violations.append("dense result should not have unit_bm25_score")
        if result.metadata_match is not None:
            violations.append("dense result should not have metadata_match")

    # Text must not be empty (unless it's a source_metadata expansion with no text)
    if not result.text and channel != RetrievalChannel.SOURCE_METADATA_EXPANSION:
        violations.append("empty text in non-expansion result")

    return violations


def assert_valid(result: CanonicalResult) -> None:
    """Raise ContractViolation if the result is invalid."""
    violations = validate_result(result)
    if violations:
        raise ContractViolation(
            f"Result {result.result_id}: {'; '.join(violations)}"
        )


def validate_batch(results: list[CanonicalResult]) -> dict[str, list[str]]:
    """Validate a batch of results, returning violations keyed by result_id."""
    all_violations: dict[str, list[str]] = {}
    for r in results:
        violations = validate_result(r)
        if violations:
            all_violations[r.result_id] = violations
    return all_violations

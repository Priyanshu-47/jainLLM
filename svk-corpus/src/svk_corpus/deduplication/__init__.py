"""Exact, near, and (interface-only) semantic deduplication."""

from svk_corpus.deduplication.dedupe import (  # noqa: F401
    SEMANTIC_SAFE_LANGUAGES,
    STATUS_EXACT,
    STATUS_EXACT_LOW_SIGNAL,
    STATUS_NEAR,
    STATUS_UNIQUE,
    DedupDecision,
    Deduplicator,
    MinHasher,
    SemanticDeduplicator,
)

__all__ = [
    "SEMANTIC_SAFE_LANGUAGES",
    "STATUS_EXACT",
    "STATUS_EXACT_LOW_SIGNAL",
    "STATUS_NEAR",
    "STATUS_UNIQUE",
    "DedupDecision",
    "Deduplicator",
    "MinHasher",
    "SemanticDeduplicator",
]

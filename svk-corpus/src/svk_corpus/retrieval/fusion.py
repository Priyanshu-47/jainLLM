"""Reciprocal Rank Fusion and the hybrid search orchestrator.

RRF is used because BM25 scores and cosine similarities live on different
scales; RRF needs only ranks, which makes the fusion deterministic and
parameter-light:  score(d) = sum over lists of 1 / (k + rank_i(d)).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

from svk_corpus.retrieval.documents import RetrievalDocument

RRF_K = 60  # the constant from Cormack et al. (2009); small and standard.


@dataclass
class RetrievalResult:
    """A retrieval result that refuses to lose provenance."""

    doc: RetrievalDocument
    score: float
    rank: int
    methods: dict[str, int] = field(default_factory=dict)  # method -> rank in that list

    def provenance(self) -> dict[str, Any]:
        return {
            "text_id": self.doc.text_id,
            "source_id": self.doc.source_id,
            "title": self.doc.title,
            "author": self.doc.author,
            "publication_year": self.doc.publication_year,
            "citation": self.doc.citation,
            "locator": self.doc.locator,
            "section": self.doc.section,
            "unit_type": self.doc.unit_type,
            "language": self.doc.language,
            "script": self.doc.script,
            "sect": self.doc.sect,
            "religious_scope": self.doc.religious_scope,
            "religious_scope_confidence": self.doc.religious_scope_confidence,
            "knowledge_layer": self.doc.knowledge_layer,
            "teacher_or_author": self.doc.teacher_or_author,
            "lineage": self.doc.lineage,
            "methods": dict(sorted(self.methods.items())),
            "fused_score": round(self.score, 6),
        }


def _fusion_key(item: Any) -> Any:
    """Hash-stable fusion key.

    RetrievalDocument is a mutable (unhashable) dataclass, so documents are
    keyed by identity while genuinely hashable items (e.g. test strings) are
    keyed by value. The lookup map preserves the original objects.
    """
    try:
        hash(item)
    except TypeError:
        return ("id", id(item))
    return item


def reciprocal_rank_fusion(rankings: Sequence[Sequence[Any]],
                           k: int = RRF_K) -> list[tuple[Any, float, dict[str, int]]]:
    """Fuse ranked lists (best-first) into one ranked list.

    Ties in the fused score are broken by first appearance, keeping the
    fusion deterministic.
    """
    scores: dict[Any, float] = {}
    methods: dict[Any, dict[str, int]] = {}
    original: dict[Any, Any] = {}
    for list_idx, ranking in enumerate(rankings):
        for rank, item in enumerate(ranking, 1):
            key = _fusion_key(item)
            original.setdefault(key, item)
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
            methods.setdefault(key, {})[f"list{list_idx}"] = rank
    ordered = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    return [(original[key], sc, methods[key]) for key, sc in ordered]


def _indices_matching(docs: Sequence[RetrievalDocument],
                      where: dict[str, Any] | None) -> list[int] | None:
    """Return allowed doc indices for the metadata prefilter, or None for all."""
    if not where:
        return None
    allowed: list[int] = []
    for i, doc in enumerate(docs):
        ok = True
        for key, want in where.items():
            got = getattr(doc, key, None)
            if isinstance(want, (set, frozenset, list, tuple)):
                if got not in want:
                    ok = False
                    break
            elif got != want:
                ok = False
                break
        if ok:
            allowed.append(i)
    return allowed


class HybridRetriever:
    """Query -> metadata prefilter -> BM25 (+ dense) -> RRF -> provenance."""

    def __init__(self, docs: Sequence[RetrievalDocument],
                 bm25: Any, dense: Any = None,
                 rrf_k: int = RRF_K) -> None:
        self.docs = list(docs)
        self.bm25 = bm25
        self.dense = dense  # None or UnavailableDense means lexical-only.
        self.rrf_k = rrf_k

    def search(self, query: str, top_k: int = 10,
               where: dict[str, Any] | None = None) -> list[RetrievalResult]:
        allowed = _indices_matching(self.docs, where)
        if allowed is not None and not allowed:
            return []
        bm25_hits = self.bm25.search(query, top_k=max(top_k * 4, 50), allowed=allowed)
        rankings: list[list[Any]] = [[h.doc for h in bm25_hits]]
        if self.dense is not None and getattr(self.dense, "name", "") != "unavailable":
            dense_hits = self.dense.search(query, top_k=max(top_k * 4, 50), allowed=allowed)
            rankings.append([doc for doc, _ in dense_hits])
        fused = reciprocal_rank_fusion(rankings, k=self.rrf_k)
        out: list[RetrievalResult] = []
        for rank, (doc, score, methods) in enumerate(fused[:top_k], 1):
            out.append(RetrievalResult(
                doc=doc,
                score=score,
                rank=rank,
                methods={("bm25" if m == "list0" else "dense" if m == "list1" else m): r
                         for m, r in methods.items()},
            ))
        return out

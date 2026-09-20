"""Experimental post-BM25 reranking layers (Task 11).

Position in the pipeline
------------------------
Strictly AFTER BM25, as an experiment:

    query -> BM25 (unchanged, primary signal) -> [reranker] -> fusion -> results

Hard rules honoured by every layer here:

1.  BM25 stays the primary signal. These layers reorder a BM25-ranked list;
    they never invent scores, never retrieve documents BM25 did not return,
    and never drop a result (reordering only — the list length is unchanged).
2.  Original evidence preserved: every result keeps the BM25 rank and score
    it had BEFORE reranking, so the experiment stays auditable.
3.  Deterministic: fixed rule order, stable sort, no randomness, no models.
4.  Existing metadata only. No authority scores are invented, and no field
    that could smuggle one in (no language->sect inference, no id ordering
    as authority). Source quality fields exist in the manifest but describe
    artifact/OCR fidelity, not authority — deliberately NOT used.
5.  Configurable: the caller chooses the strategy; defaults stay neutral.

Strategies
----------
"bm25"        identity — return the input order unchanged (the baseline A).
"tiebreak"    stable re-sort of the BM25 list by BM25 score (exact, since the
              input is already sorted by it), then metadata tie-breaks for
              EXACT score ties only. With quantized scores (see below) this
              is what breaks the pathological all-equal-tie case.
              Tie-break keys, in order:
                1. religious_scope_confidence (HIGH > MEDIUM > LOW > UNKNOWN)
                   — existing audit field, per-source, evidence-backed.
                2. source_quality             (HIGH > MEDIUM > LOW > UNKNOWN)
                   — artifact/OCR fidelity from the manifest.
                3. publication_year           (older first — documented as an
                   ARBITRARY but deterministic choice, not an authority claim;
                   earliest attested edition of a work is the conservative
                   citation anchor).
"diversify"   edition-aware selection for the tie region + within-source cap.
              Uses ONLY the existing edition_of/parent_source_id fields:
              sources in the same edition cluster are alternates covering the
              same work, so after the top results the list rotates through
              distinct sources instead of draining one source's near-identical
              units. A per-source cap (max_per_source, default 3) keeps any
              single source from monopolising the top-k. Caps REORDER nothing
              that is dropped: excess units stay in the list, after the
              rotated first tier. The per-source cap is a presentation-tier
              control for evaluation; the full BM25 list remains available.

Why no metadata PRIOR (strategy C)
----------------------------------
A multiplicative/additive prior would promote documents by metadata rather
than relevance. The only candidates are scope-confidence and quality — the
first is edition-identical across the q09 cluster (no effect except across
unrelated queries), and the second measures OCR fidelity, not authority or
relevance. Granting it prior weight would silently demote low-OCR-fidelity
sources in EVERY query without a relevance basis. Declined; not implemented.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

from svk_corpus.retrieval.documents import RetrievalDocument
from svk_corpus.retrieval.fusion import RetrievalResult

_CONF_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "UNKNOWN": 3}


def _conf_rank(value: str | None) -> int:
    return _CONF_ORDER.get((value or "UNKNOWN").upper(), 3)


@dataclass
class RerankInfo:
    """Audit trail of what the reranker did to one result."""

    bm25_rank: int
    bm25_score: float
    strategies: list[str] = field(default_factory=list)


def _edition_cluster_key(source_id: str,
                         parent_of: dict[str, str]) -> tuple[str, ...]:
    """Root of the edition_of chain for a source (path-compressed path walk).

    Deterministic and cycle-safe (walks at most len(parent_of) steps).
    A source with no parent is its own root.
    """
    seen: set[str] = set()
    cur = source_id
    while cur in parent_of and cur not in seen:
        seen.add(cur)
        cur = parent_of[cur]
    return (cur, source_id)


def _quantize(score: float, ndigits: int = 1) -> float:
    """Quantize BM25 scores for tie detection.

    Rationale (measured in the Task 11 baseline): units of one source that
    match a query identically get scores like 4.198, 4.195, 4.203 —
    micro-differences from average-doc-length feedback that carry no
    relevance meaning. Quantizing to 1 decimal groups those into one tie
    region while keeping genuinely different match strengths apart (e.g.
    4.2 vs 3.9 vs 2.1). This is the smallest change that makes the
    all-tie pathology visible to the tie-break layer.
    """
    return round(score, ndigits)


class Reranker:
    """Post-BM25 experimental reranker (see module docstring)."""

    def __init__(self, strategy: str = "bm25",
                 max_per_source: int = 3,
                 tie_ndigits: int = 1) -> None:
        self.strategy = strategy
        self.max_per_source = max_per_source
        self.tie_ndigits = tie_ndigits

    # ------------------------------------------------------------------
    def rerank(self, hits: Sequence[RetrievalResult]) -> list[RetrievalResult]:
        """Return a reordered copy; input list is not mutated, nothing removed."""
        if self.strategy == "bm25" or len(hits) <= 1:
            return list(hits)

        bm25_rank = {id(h): h.rank for h in hits}
        bm25_score = {id(h): h.score for h in hits}

        if self.strategy == "tiebreak":
            ordered = self._tiebreak_sort(hits)
        elif self.strategy == "diversify":
            ordered = self._diversify(hits)
        else:
            raise ValueError(f"unknown rerank strategy: {self.strategy!r}")

        out: list[RetrievalResult] = []
        for new_rank, h in enumerate(ordered, 1):
            res = RetrievalResult(
                doc=h.doc,
                score=h.score,          # BM25 score preserved untouched
                rank=new_rank,
                methods=dict(h.methods),
            )
            # Attach the audit trail without changing RetrievalResult's contract:
            # BM25 rank/score as they were BEFORE reranking.
            res.extra = RerankInfo(     # type: ignore[attr-defined]
                bm25_rank=bm25_rank[id(h)],
                bm25_score=bm25_score[id(h)],
                strategies=[self.strategy],
            )
            out.append(res)
        return out

    # ------------------------------------------------------------------
    def _sort_key(self) -> Any:
        def key(h: RetrievalResult) -> tuple:
            d = h.doc
            return (
                -_quantize(h.score, self.tie_ndigits),      # BM25 first (quantized)
                _conf_rank(d.religious_scope_confidence),   # metadata tie-breaks
                _conf_rank(d.source_quality),
                _safe_year(d.publication_year),
            )
        return key

    def _tiebreak_sort(self, hits: Sequence[RetrievalResult]) -> list[RetrievalResult]:
        return sorted(hits, key=self._sort_key())

    # ------------------------------------------------------------------
    def _diversify(self, hits: Sequence[RetrievalResult]) -> list[RetrievalResult]:
        parents = self._parent_map(hits)
        base = self._tiebreak_sort(hits)

        head: list[RetrievalResult] = []
        used_sources: dict[str, int] = {}
        overflow: list[RetrievalResult] = []
        rotated: list[RetrievalResult] = []

        for h in base:
            sid = h.doc.source_id
            if used_sources.get(sid, 0) < self.max_per_source:
                head.append(h)
                used_sources[sid] = used_sources.get(sid, 0) + 1
            else:
                overflow.append(h)

        # Rotate through distinct sources for the first tier after the head:
        # one best unit per edition-cluster root, in deterministic order.
        by_root: dict[tuple[str, ...], list[RetrievalResult]] = {}
        rotated_ids: set[int] = set()
        for h in overflow:
            by_root.setdefault(_edition_cluster_key(h.doc.source_id, parents), []).append(h)
        rotated: list[RetrievalResult] = []
        for root in sorted(by_root):                       # deterministic order
            if by_root[root]:
                pick = by_root[root].pop(0)
                rotated.append(pick)
                rotated_ids.add(id(pick))
        # Remaining overflow keeps base order after the rotated first tier.
        tail = [h for h in overflow if id(h) not in rotated_ids]
        return head + rotated + tail

    def _parent_map(self, hits: Sequence[RetrievalResult]) -> dict[str, str]:
        """parent_source_id map for the sources present (manifest-backed)."""
        parents: dict[str, str] = {}
        for h in hits:
            sid = h.doc.source_id
            if sid in parents:
                continue
            parents[sid] = getattr(h.doc, "parent_source_id", "") or ""
        return parents


def _safe_year(value: str | None) -> int:
    try:
        return int(str(value or "")[:4])
    except ValueError:
        return 9999

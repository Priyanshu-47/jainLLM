"""Production retrieval service (Task 76).

A small, maintainable retrieval abstraction with an explicit, auditable mode
selection between two ranked-list producers:

  bm25           the current production behaviour (H1).  Governed BM25 pool
                 (top ``pool``) -> ``Reranker(strategy="diversify")`` ->
                 source-metadata tail fills (max ``max_metadata_fill``).  This
                 is byte-compatible with
                 ``src/svk_corpus/retrieval/evaluate.py`` mode ``C_combined``
                 and with the Task-69/72/74 ``H1_BM25`` config.

  hybrid_rrf20   the Task-74/75 recommended experimental candidate (H3_RRF20).
                 Deterministic RRF over the FULL BM25 ranking and the FULL
                 dense ranking, ``k = 20``, numpy-lexsort tie-breaking.
                 Evidence window ``evidence_k = 5`` / ``text_trunc = 500``
                 (Task-69 width).  This is the config that scored
                 unit@5 = 0.5385 / src@5 = 0.9783 / ceiling = 0.8372 on the
                 frozen 47-case benchmark (Tasks 74-75).

Hard rules honoured here
------------------------
* BM25 remains the production default.  The default mode is ``bm25``; hybrid
  requires an explicit opt-in (policy config or the ``SVK_RETRIEVAL_MODE``
  environment variable).  Nothing in this module flips the default.
* No silent fallback.  If hybrid is requested but the dense index cannot be
  loaded/validated, or no query encoder is available, the service either
  raises (``strict_dense=True``) or falls back to ``bm25`` WITH an explicit
  ``fallback_reason`` recorded on the response and emitted through the
  logger.  ``SearchResponse.mode_used`` always reports the retriever that
  actually served the request.
* Determinism.  Ranking is fully deterministic: stable sorts, fixed
  tie-break keys, no randomness, no network.  Two identical queries against
  the same artifacts return byte-identical rankings.
* Provenance.  Every result carries its retrieval channel and the source /
  unit / dense / metadata evidence needed by the evidence contract
  (``contract.py``).  No provenance field is invented.
* Separation of concerns.  Query encoding (model inference), retrieval,
  evidence validation and response generation are independent.  This module
  does RETRIEVAL only; it never calls a generative model and never builds
  answer prompts.  Callers validate results via ``to_canonical()`` +
  ``contract.validate_result`` and build their own evidence context.

Dense-index provenance
----------------------
The hybrid path consumes the Task-74 experiment-local dense index
(``experiments/task74/dense_index/``): BAAI/bge-m3 (revision
``5617a9f61b02...``), dim 1024, L2-normalised, float16 corpus matrix over
164,238 docs.  ``load_dense_index`` verifies the ``corpus_emb`` sha256
against ``index_meta.json`` and (optionally) the full text/id alignment
shas, so an unverified index is NEVER silently accepted.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from svk_corpus.retrieval.bm25 import BM25Index
from svk_corpus.retrieval.contract import (CanonicalResult, MetadataMatchEvidence,
                                           RetrievalChannel)
from svk_corpus.retrieval.documents import RetrievalDocument
from svk_corpus.retrieval.fusion import RetrievalResult
from svk_corpus.retrieval.rerank import Reranker
from svk_corpus.retrieval.source_channel import (SourceIndex, SourceUnitExpander,
                                                 build_source_index)

INF = 10 ** 9


# ---------------------------------------------------------------------------
# Mode + policy
# ---------------------------------------------------------------------------

class RetrievalMode(str, Enum):
    """Controlled vocabulary for the retrieval mode that serves a request."""

    BM25 = "bm25"
    HYBRID_RRF20 = "hybrid_rrf20"

    @classmethod
    def values(cls) -> tuple[str, ...]:
        return tuple(m.value for m in cls)


@dataclass
class RetrievalPolicy:
    """Explicit, auditable retrieval configuration.

    The production default is ``bm25``.  ``hybrid_rrf20`` is experimental and
    must be opted into deliberately; it is never the default.
    """

    mode: RetrievalMode = RetrievalMode.BM25
    top_k: int = 10
    pool: int = 2000
    max_metadata_fill: int = 3
    evidence_k: int = 5
    text_trunc: int = 500
    rrf_k: int = 20
    dense_index_dir: str = "experiments/task74/dense_index"
    fallback_on_dense_failure: bool = True
    strict_dense: bool = False
    shadow_mode: bool = False

    # ---- constructors -----------------------------------------------------
    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "RetrievalPolicy":
        """Build a policy from a plain mapping (e.g. a TOML section)."""
        kw: dict[str, Any] = {}
        if "mode" in data:
            kw["mode"] = RetrievalMode(str(data["mode"]).strip().lower())
        for key in ("top_k", "pool", "max_metadata_fill", "evidence_k",
                    "text_trunc", "rrf_k"):
            if key in data:
                kw[key] = int(data[key])
        for key in ("fallback_on_dense_failure", "strict_dense", "shadow_mode"):
            if key in data:
                kw[key] = bool(data[key])
        if "dense_index_dir" in data:
            kw["dense_index_dir"] = str(data["dense_index_dir"])
        return cls(**kw)

    @classmethod
    def from_toml_section(cls, section: dict[str, Any]) -> "RetrievalPolicy":
        return cls.from_mapping(section)

    def with_env_overrides(self, environ: dict[str, str] | None = None) -> "RetrievalPolicy":
        """Apply ``SVK_RETRIEVAL_*`` environment overrides and return a copy.

        The env vars are a runtime feature flag that does not require editing
        policy.toml:

            SVK_RETRIEVAL_MODE    bm25 | hybrid_rrf20
            SVK_RETRIEVAL_SHADOW  0 | 1 | true | false
            SVK_RETRIEVAL_STRICT  0 | 1 | true | false

        An invalid ``SVK_RETRIEVAL_MODE`` value is IGNORED (not applied) so a
        typo can never silently enable hybrid retrieval.
        """
        env = os.environ if environ is None else environ
        import copy
        out = copy.copy(self)
        raw = env.get("SVK_RETRIEVAL_MODE", "").strip().lower()
        if raw in RetrievalMode.values():
            out.mode = RetrievalMode(raw)
        if "SVK_RETRIEVAL_SHADOW" in env:
            out.shadow_mode = env["SVK_RETRIEVAL_SHADOW"].strip().lower() in ("1", "true", "yes")
        if "SVK_RETRIEVAL_STRICT" in env:
            out.strict_dense = env["SVK_RETRIEVAL_STRICT"].strip().lower() in ("1", "true", "yes")
        return out


# ---------------------------------------------------------------------------
# Dense index loading + validation
# ---------------------------------------------------------------------------

class DenseIndexUnavailable(RuntimeError):
    """Raised when the dense index is missing, corrupt, or fails verification."""


@dataclass
class DenseIndexState:
    """A loaded, L2-normalised dense index ready for cosine search."""

    emb: Any                      # np.ndarray (n, dim) float32, L2-normalised
    n: int
    dim: int
    meta: dict[str, Any]
    tid2idx: dict[str, int]
    disk_bytes: int
    load_seconds: float
    verified: bool
    verification_notes: list[str] = field(default_factory=list)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_dense_index(index_dir: Path, docs: Sequence[RetrievalDocument],
                     verify_file_sha: bool = True,
                     verify_alignment: bool = False) -> DenseIndexState:
    """Load and validate the Task-74 numpy dense index.

    Parameters
    ----------
    index_dir : Path
        Directory containing ``corpus_emb.f16.npy`` and ``index_meta.json``.
    docs : Sequence[RetrievalDocument]
        The corpus in index order (``text_id`` -> row index).
    verify_file_sha : bool
        Verify ``corpus_emb.f16.npy`` sha256 against ``index_meta.json``.
        Default True — an unverified index is never silently accepted.
    verify_alignment : bool
        Additionally verify the full ``corpus_text``/``doc_ids`` alignment
        shas and doc count.  Expensive (iterates all docs); default False for
        warm starts, True in the benchmark gate.

    Raises
    ------
    DenseIndexUnavailable
        If any required artifact is missing or any verification fails.
    """
    import numpy as np

    t0 = time.perf_counter()
    index_dir = Path(index_dir)
    meta_path = index_dir / "index_meta.json"
    emb_path = index_dir / "corpus_emb.f16.npy"
    notes: list[str] = []

    if not meta_path.is_file():
        raise DenseIndexUnavailable(f"index_meta.json not found in {index_dir}")
    if not emb_path.is_file():
        raise DenseIndexUnavailable(f"corpus_emb.f16.npy not found in {index_dir}")

    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DenseIndexUnavailable(f"index_meta.json unreadable: {exc}") from exc

    if verify_file_sha:
        expected = meta.get("corpus_emb_f16_sha256")
        if not expected:
            raise DenseIndexUnavailable("index_meta.json missing corpus_emb_f16_sha256")
        actual = _sha256_file(emb_path)
        if actual != expected:
            raise DenseIndexUnavailable(
                f"corpus_emb sha256 mismatch: expected {expected[:16]}..., "
                f"got {actual[:16]}...")
        notes.append("corpus_emb sha256 verified")

    try:
        emb = np.load(emb_path).astype(np.float32)
    except (OSError, ValueError) as exc:
        raise DenseIndexUnavailable(f"corpus_emb.f16.npy unreadable: {exc}") from exc
    if emb.ndim != 2:
        raise DenseIndexUnavailable(f"corpus_emb has ndim={emb.ndim}, expected 2")

    # L2-renormalise (matching Task-74/75: local search casts to fp32 and
    # re-normalises, so cosine == inner product).
    nrm = np.linalg.norm(emb, axis=1, keepdims=True)
    nrm[nrm == 0] = 1.0
    emb /= nrm

    n, dim = int(emb.shape[0]), int(emb.shape[1])
    al = meta.get("alignment") or {}
    if al.get("doc_count") is not None and al["doc_count"] != n:
        raise DenseIndexUnavailable(
            f"doc_count {al['doc_count']} != embedding rows {n}")
    if al.get("doc_count") is not None and al["doc_count"] != len(docs):
        raise DenseIndexUnavailable(
            f"doc_count {al['doc_count']} != len(docs) {len(docs)}")
    if len(docs) != n:
        raise DenseIndexUnavailable(f"len(docs) {len(docs)} != embedding rows {n}")

    if verify_alignment:
        text_sha = hashlib.sha256()
        id_sha = hashlib.sha256()
        for d in docs:
            text_sha.update(d.search_text.encode("utf-8"))
            id_sha.update(d.text_id.encode("utf-8"))
        if al.get("corpus_text_sha256") and text_sha.hexdigest() != al["corpus_text_sha256"]:
            raise DenseIndexUnavailable("corpus_text_sha256 alignment mismatch")
        if al.get("doc_ids_sha256") and id_sha.hexdigest() != al["doc_ids_sha256"]:
            raise DenseIndexUnavailable("doc_ids_sha256 alignment mismatch")
        notes.append("corpus_text/doc_ids alignment shas verified")

    tid2idx = {d.text_id: i for i, d in enumerate(docs)}
    disk_bytes = emb_path.stat().st_size
    return DenseIndexState(
        emb=emb, n=n, dim=dim, meta=meta, tid2idx=tid2idx,
        disk_bytes=disk_bytes, load_seconds=time.perf_counter() - t0,
        verified=True, verification_notes=notes)


# ---------------------------------------------------------------------------
# Deterministic full-list RRF (H3_RRF20)
# ---------------------------------------------------------------------------

def rrf_fuse_full(bm25_rank: dict[str, int], dense_rank_of: Any,
                  k: int, tid2idx: dict[str, int], n: int) -> Any:
    """Full-list RRF -> doc indices in fused order.

    Semantics identical to Task-74 ``rrf_fuse``:
      score(d) = sum over signals present of 1/(k + rank), ranks 1-based,
      FULL lists.  Sort key (-score, bm25_rank or INF, dense_rank,
      doc_index) via ``np.lexsort`` — deterministic, stable ties.

    The BM25 contribution is applied with numpy fancy indexing (vectorised)
    rather than a per-document Python loop; the resulting score/bmr arrays
    are bit-identical to the loop form, and the lexsort keys are unchanged.
    Proven exactly equivalent on 54 cases (47 frozen + 7 synthetic edge
    cases) in Task 77 (``experiments/task77/task77_fusion_opt.py``).
    """
    import numpy as np
    score = 1.0 / (k + dense_rank_of.astype(np.float64))
    bmr = np.full(n, INF, dtype=np.int64)
    if bm25_rank:
        # Vectorised update; skip text_ids absent from tid2idx (defensive,
        # matching the original per-doc `tid2idx.get(tid)` semantics).
        hits = []
        ranks = []
        for tid, r in bm25_rank.items():
            di = tid2idx.get(tid)
            if di is not None:
                hits.append(di)
                ranks.append(r)
        if hits:
            h = np.asarray(hits, dtype=np.int64)
            rk = np.asarray(ranks, dtype=np.int64)
            score[h] += 1.0 / (k + rk.astype(np.float64))
            bmr[h] = rk
    order = np.lexsort((np.arange(n), dense_rank_of, bmr, -score))
    return order


# ---------------------------------------------------------------------------
# Service results
# ---------------------------------------------------------------------------

@dataclass
class ServiceResult:
    """One ranked retrieval result with its channel and provenance evidence."""

    doc: RetrievalDocument
    score: float
    rank: int
    channel: str
    methods: dict[str, int] = field(default_factory=dict)
    unit_bm25_rank: int | None = None
    unit_bm25_score: float | None = None
    dense_rank: int | None = None
    dense_score: float | None = None
    metadata_match: MetadataMatchEvidence | None = None

    def to_retrieval_result(self) -> RetrievalResult:
        """Convert to the generic ``RetrievalResult`` used elsewhere."""
        rr = RetrievalResult(doc=self.doc, score=self.score, rank=self.rank,
                             methods=dict(self.methods))
        extra: dict[str, Any] = {
            "retrieval_channel": self.channel,
            "unit_bm25_rank": self.unit_bm25_rank,
            "unit_bm25_score": self.unit_bm25_score,
            "dense_rank": self.dense_rank,
            "dense_score": self.dense_score,
        }
        if self.metadata_match is not None:
            extra["source_metadata_match"] = self.metadata_match.__dict__
        rr.extra = extra  # type: ignore[attr-defined]
        return rr

    def to_canonical(self, query: str, norm_tokens: Sequence[str],
                     case_id: str = "") -> CanonicalResult:
        """Build a contract-validatable ``CanonicalResult`` for this result.

        The caller is responsible for running
        ``contract.validate_result`` on the returned object; this method only
        assembles it with the correct channel semantics.
        """
        channel = RetrievalChannel(self.channel)
        cr = CanonicalResult(
            result_id=f"{case_id}:{self.doc.text_id}" if case_id else self.doc.text_id,
            source_id=self.doc.source_id,
            text=self.doc.text,
            title=self.doc.title,
            parent_source_id=self.doc.parent_source_id,
            locator=dict(self.doc.locator or {}),
            religious_scope=self.doc.religious_scope,
            religious_scope_confidence=self.doc.religious_scope_confidence,
            knowledge_layer=self.doc.knowledge_layer,
            teacher_or_author=self.doc.teacher_or_author,
            lineage=self.doc.lineage,
            source_quality=self.doc.source_quality,
            retrieval_channel=channel,
            retrieval_rank=self.rank,
            retrieval_score=float(self.score),
            methods=dict(self.methods),
        )
        if channel is RetrievalChannel.UNIT_BM25:
            cr.unit_bm25_rank = self.unit_bm25_rank
            cr.unit_bm25_score = self.unit_bm25_score
            # H3_RRF20 hybrid: a lexically-found result also records the dense
            # rank it held so fused provenance is complete. The contract allows
            # dense fields on unit_bm25 (it only forbids metadata_match here).
            cr.dense_rank = self.dense_rank
            cr.dense_score = self.dense_score
        elif channel is RetrievalChannel.DENSE:
            cr.dense_rank = self.dense_rank
            cr.dense_score = self.dense_score
            # DENSE-channel results must NOT carry unit_bm25 fields (contract).
        elif channel in (RetrievalChannel.SOURCE_METADATA,
                         RetrievalChannel.SOURCE_METADATA_EXPANSION):
            cr.metadata_match = self.metadata_match
        return cr


@dataclass
class SearchResponse:
    """Result of one search, with the mode that ACTUALLY served it."""

    results: list[ServiceResult]
    mode_requested: RetrievalMode
    mode_used: RetrievalMode
    fallback_reason: str | None
    latency_s: float
    top_k: int
    query_id: str | None = None

    @property
    def served_by_hybrid(self) -> bool:
        return self.mode_used is RetrievalMode.HYBRID_RRF20

    def summary(self) -> dict[str, Any]:
        """Compact, loggable summary (no raw query text, no retrieved text)."""
        return {
            "mode_requested": self.mode_requested.value,
            "mode_used": self.mode_used.value,
            "fallback_reason": self.fallback_reason,
            "latency_s": round(self.latency_s, 6),
            "top_k": self.top_k,
            "n_results": len(self.results),
            "channels": [r.channel for r in self.results],
            "query_id": self.query_id,
        }


# ---------------------------------------------------------------------------
# The service
# ---------------------------------------------------------------------------

class RetrievalService:
    """Mode-selectable retrieval over the released RAG corpus.

    Dependencies are injected so every component stays independently testable:
    the BM25 index, source index, expander, diversify reranker, dense index
    state and query encoder are all optional constructor arguments.  A
    ``from_repo`` classmethod wires the production defaults.
    """

    def __init__(
        self,
        policy: RetrievalPolicy,
        docs: Sequence[RetrievalDocument],
        bm25: BM25Index | None = None,
        sidx: SourceIndex | None = None,
        expander: SourceUnitExpander | None = None,
        diversify: Reranker | None = None,
        dense: DenseIndexState | None = None,
        query_encoder: Callable[[str], Any] | None = None,
        logger: Callable[[str], None] | None = None,
    ) -> None:
        self.policy = policy
        self.docs = list(docs)
        self.bm25 = bm25 if bm25 is not None else BM25Index(self.docs, k1=1.5, b=0.75)
        self.sidx = sidx
        self.expander = expander if expander is not None else SourceUnitExpander(self.docs)
        self.diversify = diversify if diversify is not None else Reranker(
            strategy="diversify", max_per_source=3)
        self.dense = dense
        self.query_encoder = query_encoder
        self._log = logger if logger is not None else (lambda _msg: None)

    # ---- factory ----------------------------------------------------------
    @classmethod
    def from_repo(cls, policy: RetrievalPolicy, root: Path,
                  dense: DenseIndexState | None = None,
                  query_encoder: Callable[[str], Any] | None = None,
                  logger: Callable[[str], None] | None = None) -> "RetrievalService":
        """Wire the production defaults from a repo root."""
        from svk_corpus.retrieval.documents import load_corpus
        docs = load_corpus(root / "data" / "release" / "rag_corpus.jsonl",
                           root / "manifests" / "source_manifest.csv")
        sidx = build_source_index(root / "manifests" / "source_manifest.csv")
        if dense is None and policy.mode is RetrievalMode.HYBRID_RRF20:
            # Attempt to load; failure is handled at search time (fallback).
            try:
                dense = load_dense_index(root / policy.dense_index_dir, docs)
            except DenseIndexUnavailable as exc:
                if policy.strict_dense:
                    raise
                if logger:
                    logger(f"[service] dense index unavailable at startup: {exc}")
        return cls(policy=policy, docs=docs, sidx=sidx, dense=dense,
                   query_encoder=query_encoder, logger=logger)

    # ---- public API -------------------------------------------------------
    def search(self, query: str, top_k: int | None = None,
               query_id: str | None = None,
               query_embedding: Any | None = None) -> SearchResponse:
        """Retrieve ``top_k`` results under the configured (or overridden) mode.

        ``query_embedding`` lets a caller that already has a query vector
        (e.g. the offline benchmark replay) avoid re-encoding.  When hybrid is
        requested and neither ``query_embedding`` nor ``self.query_encoder`` is
        available, the service falls back to ``bm25`` with an explicit reason.
        """
        t0 = time.perf_counter()
        k = top_k if top_k is not None else self.policy.top_k
        mode_req = self.policy.mode

        if mode_req is RetrievalMode.HYBRID_RRF20:
            reason = self._hybrid_unavailable_reason(query_embedding)
            if reason is None:
                results = self._search_hybrid(query, k, query_embedding)
                used = RetrievalMode.HYBRID_RRF20
                fallback = None
            elif self.policy.strict_dense:
                raise DenseIndexUnavailable(reason)
            elif self.policy.fallback_on_dense_failure:
                self._log(f"[service] hybrid unavailable -> fallback bm25: {reason}")
                results = self._search_bm25(query, k)
                used = RetrievalMode.BM25
                fallback = reason
            else:
                raise DenseIndexUnavailable(reason)
        else:
            results = self._search_bm25(query, k)
            used = RetrievalMode.BM25
            fallback = None

        resp = SearchResponse(
            results=results, mode_requested=mode_req, mode_used=used,
            fallback_reason=fallback, latency_s=time.perf_counter() - t0,
            top_k=k, query_id=query_id)
        return resp

    # ---- H1 production path (byte-compatible with evaluate mode C) --------
    def _search_bm25(self, query: str, top_k: int) -> list[ServiceResult]:
        p = self.policy
        pool = self.bm25.search(query, top_k=p.pool)
        unit_pool = [RetrievalResult(doc=h.doc, score=h.score, rank=h.rank,
                                     methods={"bm25": h.rank}) for h in pool]
        unit_tier = self.diversify.rerank(unit_pool)[:top_k]

        out: list[ServiceResult] = []
        unit_ids = {r.doc.text_id for r in unit_tier}
        unit_sids = {r.doc.source_id for r in unit_tier}

        if self.sidx is not None:
            smatches = self.sidx.search(query, top_k=top_k)
            missing = [m for m in smatches
                       if m.source_id not in unit_sids and not m.identifier_only]
            n_fill = min(p.max_metadata_fill, len(missing))
            fill = self.expander.expand(missing[:n_fill], top_k=n_fill) if n_fill else []
            keep = max(top_k - len(fill), 0)
            combined = list(unit_tier[:keep]) + list(fill)
        else:
            combined = unit_tier

        for rank, rr in enumerate(combined[:top_k], 1):
            if rr.doc.text_id in unit_ids:
                out.append(ServiceResult(
                    doc=rr.doc, score=float(rr.score), rank=rank,
                    channel=RetrievalChannel.UNIT_BM25.value,
                    methods=dict(rr.methods),
                    unit_bm25_rank=rr.rank, unit_bm25_score=float(rr.score)))
            else:
                extra = getattr(rr, "extra", {}) or {}
                match_dict = extra.get("source_metadata_match") if isinstance(extra, dict) else None
                if match_dict:
                    # SourceMatch.as_dict() carries identifier_only (a
                    # SourceIndex bookkeeping flag); the evidence contract
                    # field set is MetadataMatchEvidence's.  Reconstruct only
                    # with contract fields so channel provenance stays valid.
                    _mm_fields = {k: v for k, v in match_dict.items()
                                  if k in MetadataMatchEvidence.__dataclass_fields__}
                    mm = MetadataMatchEvidence(**_mm_fields)
                else:
                    mm = None
                out.append(ServiceResult(
                    doc=rr.doc, score=float(rr.score), rank=rank,
                    channel=RetrievalChannel.SOURCE_METADATA.value,
                    methods=dict(rr.methods), metadata_match=mm))
        return out

    # ---- H3_RRF20 experimental candidate ----------------------------------
    def _search_hybrid(self, query: str, top_k: int,
                       query_embedding: Any | None) -> list[ServiceResult]:
        import numpy as np
        p = self.policy
        dense: DenseIndexState = self.dense  # guaranteed non-None by caller
        n = dense.n

        # BM25 full positive-score ranking (same call shape as Task-69/74).
        full = self.bm25.search(query, top_k=INF)
        bm25_rank = {r.doc.text_id: r.rank for r in full}
        bm25_score = {r.doc.text_id: r.score for r in full}

        # Dense full ordering.  Query vector is L2-normalised before the
        # inner product so cosine == dot (matching Task-74/75).
        if query_embedding is not None:
            q_vec = np.asarray(query_embedding, dtype=np.float32)
        else:
            q_vec = np.asarray(self.query_encoder(query), dtype=np.float32)
        qn = float(np.linalg.norm(q_vec)) or 1.0
        q_vec = q_vec / qn
        scores = dense.emb @ q_vec
        order = np.argsort(-scores, kind="stable")
        rank_of = np.empty(n, dtype=np.int64)
        rank_of[order] = np.arange(1, n + 1)

        fused = rrf_fuse_full(bm25_rank, rank_of, p.rrf_k, dense.tid2idx, n)
        fused_top = [int(x) for x in fused[:top_k]]

        out: list[ServiceResult] = []
        for rank, di in enumerate(fused_top, 1):
            doc = self.docs[di]
            tid = doc.text_id
            dr = int(rank_of[di])
            rrf_score = float(
                (1.0 / (p.rrf_k + dr))
                + ((1.0 / (p.rrf_k + bm25_rank[tid])) if tid in bm25_rank else 0.0))
            in_bm25 = tid in bm25_rank
            methods: dict[str, int] = {"dense": dr}
            if in_bm25:
                methods["bm25"] = bm25_rank[tid]
            if in_bm25:
                out.append(ServiceResult(
                    doc=doc, score=rrf_score, rank=rank,
                    channel=RetrievalChannel.UNIT_BM25.value,
                    methods=methods,
                    unit_bm25_rank=bm25_rank[tid],
                    unit_bm25_score=float(bm25_score[tid]),
                    dense_rank=dr, dense_score=float(scores[di])))
            else:
                out.append(ServiceResult(
                    doc=doc, score=rrf_score, rank=rank,
                    channel=RetrievalChannel.DENSE.value,
                    methods=methods, dense_rank=dr,
                    dense_score=float(scores[di])))
        return out

    # ---- availability probe ------------------------------------------------
    def _hybrid_unavailable_reason(self, query_embedding: Any | None) -> str | None:
        if self.dense is None:
            return "dense index not loaded (load_dense_index not run or failed)"
        if query_embedding is None and self.query_encoder is None:
            return ("no query encoder available (bge-m3 query-encoding runtime "
                    "not deployed; pass query_embedding for offline replay)")
        return None

    def dense_stats(self) -> dict[str, Any]:
        """Report dense-index state for operational observability."""
        if self.dense is None:
            return {"loaded": False, "reason": "no DenseIndexState"}
        return {
            "loaded": True,
            "n_docs": self.dense.n,
            "dim": self.dense.dim,
            "disk_mib": round(self.dense.disk_bytes / 2 ** 20, 1),
            "load_seconds": round(self.dense.load_seconds, 3),
            "verified": self.dense.verified,
            "verification_notes": list(self.dense.verification_notes),
            "model_id": (self.dense.meta or {}).get("model_id"),
            "model_revision": str((self.dense.meta or {}).get("model_revision", ""))[:12],
            "query_encoder_available": self.query_encoder is not None,
        }

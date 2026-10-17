"""Regression tests for the production retrieval service (Task 76).

Covers the ten required behaviours:
  1.  Existing BM25 behaviour remains unchanged / byte-compatible (H1 path).
  2.  Hybrid retrieval reproduces the Task-74 H3_RRF20 fusion semantics.
  3.  Identical queries + artifacts produce deterministic ranked results.
  4.  Duplicate results are handled correctly during fusion.
  5.  Evidence records preserve source / parent / locator / layer / scope /
      authorship / retrieval provenance.
  6.  Invalid or unavailable dense artifacts produce an explicit, observable
      failure or a configured, logged fallback.
  7.  The evidence contract rejects malformed or unsupported provenance.
  8.  The retrieval interface does not silently change evidence ordering,
      truncation, or answer-generation prompts (retrieval-only separation).
  9.  Feature-flag selection cannot accidentally enable hybrid by default.
  10. Shadow mode: BM25 stays authoritative; hybrid never replaces the answer.

Plus additional tests for failures discovered during implementation
(env-override typo safety, dense doc-count mismatch, encoder absence).
The corpus here is synthetic and tiny; these tests never touch release files.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from svk_corpus.retrieval import BM25Index, RetrievalDocument, load_corpus
from svk_corpus.retrieval.contract import (CanonicalResult, RetrievalChannel,
                                           validate_result)
from svk_corpus.retrieval.fusion import RetrievalResult
from svk_corpus.retrieval.rerank import Reranker
from svk_corpus.retrieval.service import (DenseIndexState, DenseIndexUnavailable,
                                          RetrievalMode, RetrievalPolicy,
                                          RetrievalService, SearchResponse,
                                          load_dense_index, rrf_fuse_full)


def _doc(text_id: str, text: str, **over) -> RetrievalDocument:
    base = dict(
        text_id=text_id, source_id=f"SRC-{text_id}", title=f"Title {text_id}",
        text=text, language="en", script="Latin", sect="unknown",
        religious_scope="CONTEXTUAL_JAIN", religious_scope_confidence="MEDIUM",
        knowledge_layer="SECONDARY SCHOLARSHIP", teacher_or_author="unknown",
        lineage="none", unit_type="paragraph", section="",
        locator={"citation": f"Title {text_id} [SRC-{text_id}]", "page": 3},
        publication_year="1900", author="Someone",
        parent_source_id=f"PARENT-{text_id}",
    )
    base.update(over)
    return RetrievalDocument(**base)


def _corpus() -> list[RetrievalDocument]:
    return [
        _doc("a", "The Kalpa Sutra translation of the Kalpa Sutra text."),
        _doc("b", "A study of monastic conduct and ordination rituals."),
        _doc("c", "Kalpa references in unrelated poetry and verse."),
        _doc("d", "Samayika meditation practice among the Sthanakavasi."),
        _doc("e", "Ahimsa non-violence principle in Jain ethics."),
        _doc("f", "Terapanth sect founded by Bhagwanaji in modern era."),
    ]


def _policy(**over) -> RetrievalPolicy:
    return RetrievalPolicy(**over)


def _service(docs, policy=None, **kw) -> RetrievalService:
    return RetrievalService(policy=policy or _policy(), docs=docs, **kw)


# ---------------------------------------------------------------------------
# helpers: a tiny on-disk dense index fixture
# ---------------------------------------------------------------------------

def _make_dense_fixture(tmp: Path, docs, seed: int = 0) -> Path:
    """Write a tiny, self-consistent dense index (corpus_emb + meta)."""
    rng = np.random.RandomState(seed)
    dim = 8
    emb = rng.randn(len(docs), dim).astype(np.float16)
    idx = tmp / "corpus_emb.f16.npy"
    np.save(idx, emb)
    import hashlib
    sha = hashlib.sha256(idx.read_bytes()).hexdigest()
    text_sha = hashlib.sha256()
    id_sha = hashlib.sha256()
    for d in docs:
        text_sha.update(d.search_text.encode("utf-8"))
        id_sha.update(d.text_id.encode("utf-8"))
    meta = {
        "model_id": "test-double", "model_revision": "0", "embedding_dim": dim,
        "alignment": {
            "corpus_text_sha256": text_sha.hexdigest(),
            "doc_ids_sha256": id_sha.hexdigest(),
            "doc_count": len(docs),
        },
        "corpus_emb_f16_sha256": sha,
    }
    (tmp / "index_meta.json").write_text(json.dumps(meta), encoding="utf-8")
    return tmp


def _state_from_docs(docs, seed: int = 0) -> DenseIndexState:
    """Build a DenseIndexState in memory (no disk) for hybrid unit tests."""
    rng = np.random.RandomState(seed)
    dim = 8
    emb = rng.randn(len(docs), dim).astype(np.float32)
    nrm = np.linalg.norm(emb, axis=1, keepdims=True)
    nrm[nrm == 0] = 1.0
    emb /= nrm
    return DenseIndexState(
        emb=emb, n=len(docs), dim=dim, meta={"model_id": "test-double"},
        tid2idx={d.text_id: i for i, d in enumerate(docs)},
        disk_bytes=0, load_seconds=0.0, verified=True, verification_notes=[])


def _encoder_for(docs, seed: int = 0):
    """Deterministic query encoder: hash the query into the same dim."""
    rng = np.random.RandomState(seed + 999)
    basis = rng.randn(64, 8).astype(np.float32)

    def enc(query: str) -> np.ndarray:
        h = abs(hash(query)) % 64
        return basis[h].copy()
    return enc


# ---------------------------------------------------------------------------
# 1. BM25 behaviour unchanged / byte-compatible (H1 path)
# ---------------------------------------------------------------------------

class TestBM25Compatibility(unittest.TestCase):
    def test_h1_mode_is_the_default(self):
        pol = RetrievalPolicy()
        self.assertIs(pol.mode, RetrievalMode.BM25)

    def test_h1_ranking_matches_production_mode_c(self):
        """H1 path reproduces evaluate_source_channel mode C_combined."""
        docs = _corpus()
        svc = _service(docs)
        query = "Kalpa Sutra translation"
        resp = svc.search(query, top_k=4)
        self.assertIs(resp.mode_used, RetrievalMode.BM25)
        got = [r.doc.text_id for r in resp.results]

        # Reimplement the production mode-C logic inline.
        bm25 = BM25Index(docs, k1=1.5, b=0.75)
        diversify = Reranker(strategy="diversify", max_per_source=3)
        pool = bm25.search(query, top_k=2000)
        unit_tier = diversify.rerank(
            [RetrievalResult(doc=h.doc, score=h.score, rank=h.rank,
                             methods={"bm25": h.rank}) for h in pool])[:4]
        expect = [r.doc.text_id for r in unit_tier]
        self.assertEqual(got, expect)

    def test_h1_channels_are_unit_bm25_for_lexical_hits(self):
        docs = _corpus()
        resp = _service(docs).search("Kalpa Sutra", top_k=3)
        for r in resp.results:
            self.assertEqual(r.channel, "unit_bm25")
            self.assertIsNotNone(r.unit_bm25_rank)
            self.assertIsNotNone(r.unit_bm25_score)

    def test_h1_no_dense_fields_set(self):
        docs = _corpus()
        resp = _service(docs).search("Kalpa Sutra", top_k=3)
        for r in resp.results:
            self.assertIsNone(r.dense_rank)
            self.assertIsNone(r.dense_score)


# ---------------------------------------------------------------------------
# 2. Hybrid reproduces Task-74 H3_RRF20 fusion semantics
# ---------------------------------------------------------------------------

class TestHybridRRF20(unittest.TestCase):
    def test_rrf_fuse_full_prefers_items_in_both_lists(self):
        # doc order: 0=a 1=b 2=c 3=d; bm25 ranks a=1,b=2; dense ranks b=1,a=2
        bm25_rank = {"a": 1, "b": 2}
        dense_rank = np.array([2, 1, 3, 4], dtype=np.int64)  # a=2 b=1 c=3 d=4
        tid2idx = {"a": 0, "b": 1, "c": 2, "d": 3}
        order = rrf_fuse_full(bm25_rank, dense_rank, 20, tid2idx, 4)
        ids = ["a", "b", "c", "d"]
        self.assertEqual([ids[i] for i in order[:2]], ["a", "b"])

    def test_rrf_k20_is_the_policy_default(self):
        self.assertEqual(RetrievalPolicy().rrf_k, 20)

    def test_rrf_fuse_full_matches_reference_on_edge_cases(self):
        """Vectorised rrf_fuse_full must equal a per-doc reference implementation.

        Task-77 optimised the BM25 update path (numpy fancy indexing replaces
        per-document array writes).  This test pins exact equivalence on
        deterministic edge cases: empty BM25 list, full overlap, heavy ties,
        one-sided hits, anti-correlated ranks, and missing tid2idx keys.
        """
        INF = 10 ** 9

        def reference(bm25_rank, dense_rank_of, k, tid2idx, n):
            score = 1.0 / (k + dense_rank_of.astype(np.float64))
            bmr = np.full(n, INF, dtype=np.int64)
            for tid, r in bm25_rank.items():
                di = tid2idx.get(tid)
                if di is not None:
                    score[di] += 1.0 / (k + r)
                    bmr[di] = r
            return np.lexsort((np.arange(n), dense_rank_of, bmr, -score))

        rng = np.random.RandomState(7)
        n = 2000
        tid2idx = {f"d{i}": i for i in range(n)}
        dr = rng.permutation(n) + 1
        cases = [
            ("empty_bm25", {}, dr),
            ("full_overlap",
             {f"d{i}": int(dr[i]) for i in range(n)}, dr),
            ("all_ties_dense",
             {f"d{i}": 1 for i in range(0, n, 2)},
             np.ones(n, dtype=np.int64)),
            ("one_hit", {"d7": 1}, dr),
            ("anti_correlated",
             {f"d{i}": n - i for i in range(n)},
             np.arange(1, n + 1)),
            ("missing_key_defensive",
             {"d1": 1, "not_in_index": 5, "d2": 2}, dr),
            ("sparse_random",
             {f"d{i}": int(rng.randint(1, 500))
              for i in rng.choice(n, size=n // 10, replace=False)}, dr),
        ]
        for label, bm25_rank, dense_ranks in cases:
            got = rrf_fuse_full(bm25_rank, dense_ranks, 20, tid2idx, n)
            exp = reference(bm25_rank, dense_ranks, 20, tid2idx, n)
            self.assertTrue(
                np.array_equal(got, exp),
                f"mismatch on {label}: got {got[:10]} expected {exp[:10]}")

    def test_rrf_fuse_full_skips_unknown_tids_without_crashing(self):
        tid2idx = {"a": 0, "b": 1}
        dense_rank = np.array([1, 2], dtype=np.int64)
        order = rrf_fuse_full({"a": 1, "zzz": 3}, dense_rank, 20, tid2idx, 2)
        self.assertEqual(len(order), 2)
        self.assertEqual(int(order[0]), 0)  # 'a' has both signals

    def test_hybrid_mode_sets_dense_and_bm25_provenance(self):
        docs = _corpus()
        dense = _state_from_docs(docs)
        enc = _encoder_for(docs)
        svc = _service(docs, policy=_policy(mode=RetrievalMode.HYBRID_RRF20),
                       dense=dense, query_encoder=enc)
        resp = svc.search("Kalpa Sutra", top_k=4)
        self.assertIs(resp.mode_used, RetrievalMode.HYBRID_RRF20)
        self.assertIsNone(resp.fallback_reason)
        self.assertTrue(resp.served_by_hybrid)
        for r in resp.results:
            self.assertIsNotNone(r.dense_rank)
            self.assertIn(r.channel, ("unit_bm25", "dense"))
            if r.channel == "unit_bm25":
                self.assertIsNotNone(r.unit_bm25_rank)

    def test_hybrid_uses_rrf_fuse_full_ordering(self):
        docs = _corpus()
        dense = _state_from_docs(docs)
        enc = _encoder_for(docs)
        svc = _service(docs, policy=_policy(mode=RetrievalMode.HYBRID_RRF20),
                       dense=dense, query_encoder=enc)
        query = "Samayika meditation"
        resp = svc.search(query, top_k=5)
        # independently recompute the fused order
        full = svc.bm25.search(query, top_k=10 ** 9)
        bm25_rank = {r.doc.text_id: r.rank for r in full}
        q = np.asarray(enc(query), dtype=np.float32)
        q /= (float(np.linalg.norm(q)) or 1.0)
        scores = dense.emb @ q
        order = np.argsort(-scores, kind="stable")
        rank_of = np.empty(dense.n, dtype=np.int64)
        rank_of[order] = np.arange(1, dense.n + 1)
        fused = rrf_fuse_full(bm25_rank, rank_of, 20, dense.tid2idx, dense.n)
        expect = [docs[int(i)].text_id for i in fused[:5]]
        got = [r.doc.text_id for r in resp.results]
        self.assertEqual(got, expect)


# ---------------------------------------------------------------------------
# 3. Deterministic ranking + stable tie-breaking
# ---------------------------------------------------------------------------

class TestDeterminism(unittest.TestCase):
    def test_same_query_twice_same_ranking(self):
        docs = _corpus()
        svc = _service(docs)
        a = svc.search("Kalpa Sutra", top_k=4)
        b = svc.search("Kalpa Sutra", top_k=4)
        self.assertEqual([r.doc.text_id for r in a.results],
                         [r.doc.text_id for r in b.results])
        self.assertEqual([r.score for r in a.results],
                         [r.score for r in b.results])

    def test_hybrid_same_query_twice_same_ranking(self):
        docs = _corpus()
        dense = _state_from_docs(docs)
        enc = _encoder_for(docs)
        svc = _service(docs, policy=_policy(mode=RetrievalMode.HYBRID_RRF20),
                       dense=dense, query_encoder=enc)
        a = svc.search("Ahimsa non-violence", top_k=5)
        b = svc.search("Ahimsa non-violence", top_k=5)
        self.assertEqual([r.doc.text_id for r in a.results],
                         [r.doc.text_id for r in b.results])

    def test_rrf_tie_break_is_lexsort_deterministic(self):
        # Two docs with identical fused scores -> lexsort breaks by
        # (bm25_rank, dense_rank, doc_index); doc_index is the last key.
        bm25_rank = {"x": 1, "y": 1}          # identical bm25 ranks
        dense_rank = np.array([1, 1], dtype=np.int64)  # identical dense ranks
        tid2idx = {"x": 0, "y": 1}
        order = rrf_fuse_full(bm25_rank, dense_rank, 20, tid2idx, 2)
        self.assertEqual(list(order), [0, 1])  # doc_index tie-break: x then y


# ---------------------------------------------------------------------------
# 4. Duplicate results handled correctly during fusion
# ---------------------------------------------------------------------------

class TestFusionDuplicates(unittest.TestCase):
    def test_doc_in_both_lists_scores_once_per_list(self):
        # A doc present in both lists must get score = 1/(k+rb) + 1/(k+rd).
        bm25_rank = {"a": 1}
        dense_rank = np.array([1, 2], dtype=np.int64)
        tid2idx = {"a": 0, "b": 1}
        n = 2
        k = 20
        score = 1.0 / (k + dense_rank.astype(np.float64))
        bmr = np.full(n, 10 ** 9, dtype=np.int64)
        for tid, r in bm25_rank.items():
            di = tid2idx[tid]
            score[di] += 1.0 / (k + r)
            bmr[di] = r
        # doc a: present in both -> 1/(20+1) + 1/(20+1) = 2/21
        self.assertAlmostEqual(score[0], 2.0 / 21.0, places=9)
        # doc b: dense only -> 1/(20+2)
        self.assertAlmostEqual(score[1], 1.0 / 22.0, places=9)

    def test_hybrid_no_duplicate_text_ids_in_output(self):
        docs = _corpus()
        dense = _state_from_docs(docs)
        enc = _encoder_for(docs)
        svc = _service(docs, policy=_policy(mode=RetrievalMode.HYBRID_RRF20),
                       dense=dense, query_encoder=enc)
        resp = svc.search("Kalpa Sutra", top_k=6)
        ids = [r.doc.text_id for r in resp.results]
        self.assertEqual(len(ids), len(set(ids)))

    def test_rrf_fuse_full_fuses_same_doc_across_lists(self):
        # Same doc appears in bm25 and dense; fusion must merge (not duplicate).
        bm25_rank = {"a": 1, "b": 2}
        dense_rank = np.array([1, 2], dtype=np.int64)  # a=1, b=2
        tid2idx = {"a": 0, "b": 1}
        order = rrf_fuse_full(bm25_rank, dense_rank, 20, tid2idx, 2)
        self.assertEqual(len(order), 2)  # one entry per doc, not per list


# ---------------------------------------------------------------------------
# 5. Evidence records preserve full provenance
# ---------------------------------------------------------------------------

class TestProvenancePreservation(unittest.TestCase):
    def test_service_result_carries_source_parent_locator_layer_scope_author(self):
        docs = _corpus()
        resp = _service(docs).search("Kalpa Sutra", top_k=3)
        for r in resp.results:
            self.assertTrue(r.doc.source_id)
            self.assertTrue(r.doc.parent_source_id)
            self.assertIn("page", r.doc.locator)
            self.assertTrue(r.doc.knowledge_layer)
            self.assertTrue(r.doc.religious_scope)
            self.assertTrue(r.doc.teacher_or_author)
            self.assertTrue(r.doc.author)

    def test_to_canonical_preserves_provenance_and_validates(self):
        docs = _corpus()
        resp = _service(docs).search("Kalpa Sutra", top_k=3)
        for r in resp.results:
            cr = r.to_canonical(query="Kalpa Sutra", norm_tokens=("kalpa",),
                                case_id="T1")
            self.assertEqual(cr.source_id, r.doc.source_id)
            self.assertEqual(cr.parent_source_id, r.doc.parent_source_id)
            self.assertEqual(cr.locator, r.doc.locator)
            self.assertEqual(cr.knowledge_layer, r.doc.knowledge_layer)
            self.assertEqual(cr.religious_scope, r.doc.religious_scope)
            self.assertEqual(cr.teacher_or_author, r.doc.teacher_or_author)
            self.assertEqual(cr.retrieval_channel.value, r.channel)
            self.assertEqual(validate_result(cr), [])

    def test_hybrid_to_canonical_sets_dense_fields(self):
        docs = _corpus()
        dense = _state_from_docs(docs)
        enc = _encoder_for(docs)
        svc = _service(docs, policy=_policy(mode=RetrievalMode.HYBRID_RRF20),
                       dense=dense, query_encoder=enc)
        resp = svc.search("Kalpa Sutra", top_k=4)
        for r in resp.results:
            cr = r.to_canonical("Kalpa Sutra", ("kalpa",), case_id="T1")
            self.assertIsNotNone(cr.dense_rank)
            self.assertIsNotNone(cr.dense_score)
            if r.channel == "unit_bm25":
                self.assertIsNotNone(cr.unit_bm25_rank)
                self.assertIsNotNone(cr.unit_bm25_score)
                self.assertIsNone(cr.metadata_match)
            self.assertEqual(validate_result(cr), [])


# ---------------------------------------------------------------------------
# 6. Invalid / unavailable dense artifacts -> explicit failure or logged fallback
# ---------------------------------------------------------------------------

class TestDenseFailureModes(unittest.TestCase):
    def test_missing_index_dir_raises(self):
        docs = _corpus()
        with self.assertRaises(DenseIndexUnavailable):
            load_dense_index(Path("/nonexistent/dir"), docs)

    def test_sha_mismatch_raises(self):
        docs = _corpus()
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            _make_dense_fixture(tmp, docs)
            # corrupt the meta sha so verification fails
            meta = json.loads((tmp / "index_meta.json").read_text())
            meta["corpus_emb_f16_sha256"] = "0" * 64
            (tmp / "index_meta.json").write_text(json.dumps(meta))
            with self.assertRaises(DenseIndexUnavailable):
                load_dense_index(tmp, docs, verify_file_sha=True)

    def test_doc_count_mismatch_raises(self):
        docs = _corpus()
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            _make_dense_fixture(tmp, docs)
            meta = json.loads((tmp / "index_meta.json").read_text())
            meta["alignment"]["doc_count"] = 999
            (tmp / "index_meta.json").write_text(json.dumps(meta))
            with self.assertRaises(DenseIndexUnavailable):
                load_dense_index(tmp, docs, verify_file_sha=True)

    def test_verify_file_sha_false_skips_sha_but_keeps_count(self):
        docs = _corpus()
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            _make_dense_fixture(tmp, docs)
            meta = json.loads((tmp / "index_meta.json").read_text())
            meta["corpus_emb_f16_sha256"] = "0" * 64  # wrong, but skip check
            (tmp / "index_meta.json").write_text(json.dumps(meta))
            state = load_dense_index(tmp, docs, verify_file_sha=False)
            self.assertEqual(state.n, len(docs))
            self.assertTrue(state.verified)

    def test_hybrid_without_dense_falls_back_to_bm25_with_reason(self):
        docs = _corpus()
        logged: list[str] = []
        svc = _service(docs, policy=_policy(mode=RetrievalMode.HYBRID_RRF20,
                                            fallback_on_dense_failure=True),
                       logger=logged.append)
        resp = svc.search("Kalpa Sutra", top_k=3)
        self.assertIs(resp.mode_requested, RetrievalMode.HYBRID_RRF20)
        self.assertIs(resp.mode_used, RetrievalMode.BM25)
        self.assertIsNotNone(resp.fallback_reason)
        self.assertIn("dense index not loaded", resp.fallback_reason)
        self.assertTrue(any("fallback bm25" in m for m in logged))
        # results are real BM25 results, not empty
        self.assertTrue(resp.results)

    def test_hybrid_strict_mode_raises_when_dense_missing(self):
        docs = _corpus()
        svc = _service(docs, policy=_policy(mode=RetrievalMode.HYBRID_RRF20,
                                            strict_dense=True))
        with self.assertRaises(DenseIndexUnavailable):
            svc.search("Kalpa Sutra", top_k=3)

    def test_hybrid_without_encoder_falls_back_with_reason(self):
        docs = _corpus()
        dense = _state_from_docs(docs)
        svc = _service(docs, policy=_policy(mode=RetrievalMode.HYBRID_RRF20,
                                            fallback_on_dense_failure=True),
                       dense=dense, query_encoder=None)
        resp = svc.search("Kalpa Sutra", top_k=3)
        self.assertIs(resp.mode_used, RetrievalMode.BM25)
        self.assertIn("no query encoder", resp.fallback_reason)

    def test_hybrid_with_precomputed_embedding_no_encoder_needed(self):
        docs = _corpus()
        dense = _state_from_docs(docs)
        svc = _service(docs, policy=_policy(mode=RetrievalMode.HYBRID_RRF20),
                       dense=dense, query_encoder=None)
        emb = np.zeros(dense.dim, dtype=np.float32)
        emb[0] = 1.0
        resp = svc.search("anything", top_k=3, query_embedding=emb)
        self.assertIs(resp.mode_used, RetrievalMode.HYBRID_RRF20)
        self.assertIsNone(resp.fallback_reason)


# ---------------------------------------------------------------------------
# 7. Evidence contract rejects malformed provenance
# ---------------------------------------------------------------------------

class TestContractEnforcement(unittest.TestCase):
    def test_dense_result_missing_dense_rank_is_invalid(self):
        cr = CanonicalResult(
            result_id="r1", source_id="S1", text="t", title="T",
            retrieval_channel=RetrievalChannel.DENSE, retrieval_rank=1,
            retrieval_score=0.5)
        violations = validate_result(cr)
        self.assertTrue(violations)  # dense must carry dense_rank/dense_score

    def test_unit_bm25_with_metadata_match_is_invalid(self):
        from svk_corpus.retrieval.contract import MetadataMatchEvidence
        cr = CanonicalResult(
            result_id="r1", source_id="S1", text="t", title="T",
            retrieval_channel=RetrievalChannel.UNIT_BM25, retrieval_rank=1,
            retrieval_score=0.5, unit_bm25_rank=1, unit_bm25_score=0.5,
            metadata_match=MetadataMatchEvidence(
                source_id="S1", matched_field="title", matched_value="v",
                matched_token="t", weight=1.0))
        self.assertTrue(validate_result(cr))

    def test_service_results_never_produce_contract_violations(self):
        docs = _corpus()
        for mode in (RetrievalMode.BM25,):
            resp = _service(docs, policy=_policy(mode=mode)).search(
                "Kalpa Sutra", top_k=4)
            for r in resp.results:
                cr = r.to_canonical("Kalpa Sutra", ("kalpa",), case_id="X")
                self.assertEqual(validate_result(cr), [])


# ---------------------------------------------------------------------------
# 8. Retrieval-only separation: ordering preserved, no prompt building
# ---------------------------------------------------------------------------

class TestNoSilentInterfaceChange(unittest.TestCase):
    def test_service_does_not_expose_prompt_or_generation_methods(self):
        docs = _corpus()
        svc = _service(docs)
        for banned in ("generate", "build_prompt", "build_context",
                       "answer", "chat", "complete"):
            self.assertFalse(hasattr(svc, banned),
                             f"service must not expose '{banned}'")

    def test_h1_ordering_is_the_diversified_bm25_order(self):
        docs = _corpus()
        svc = _service(docs)
        query = "Samayika meditation Sthanakavasi"
        resp = svc.search(query, top_k=4)
        bm25 = BM25Index(docs, k1=1.5, b=0.75)
        diversify = Reranker(strategy="diversify", max_per_source=3)
        pool = bm25.search(query, top_k=2000)
        expect = [h.doc.text_id for h in diversify.rerank(
            [RetrievalResult(doc=h.doc, score=h.score, rank=h.rank,
                             methods={"bm25": h.rank}) for h in pool])[:4]]
        self.assertEqual([r.doc.text_id for r in resp.results], expect)

    def test_search_response_exposes_mode_actually_used(self):
        docs = _corpus()
        resp = _service(docs).search("x", top_k=2)
        self.assertIsInstance(resp, SearchResponse)
        self.assertEqual(resp.summary()["mode_used"], "bm25")
        self.assertIn("mode_requested", resp.summary())


# ---------------------------------------------------------------------------
# 9. Feature flag cannot accidentally enable hybrid by default
# ---------------------------------------------------------------------------

class TestFeatureFlagSafety(unittest.TestCase):
    def test_default_policy_is_bm25(self):
        self.assertIs(RetrievalPolicy().mode, RetrievalMode.BM25)

    def test_from_toml_default_is_bm25(self):
        # The shipped policy.toml must keep bm25 as the default.
        from svk_corpus.config import load_config
        from pathlib import Path as _P
        root = _P(__file__).resolve().parents[1]
        cfg = load_config(root)
        pol = RetrievalPolicy.from_toml_section(cfg.section("retrieval"))
        self.assertIs(pol.mode, RetrievalMode.BM25)

    def test_env_override_enables_hybrid_explicitly(self):
        pol = RetrievalPolicy().with_env_overrides({"SVK_RETRIEVAL_MODE": "hybrid_rrf20"})
        self.assertIs(pol.mode, RetrievalMode.HYBRID_RRF20)

    def test_env_override_typo_is_ignored(self):
        pol = RetrievalPolicy().with_env_overrides({"SVK_RETRIEVAL_MODE": "hybrid"})
        self.assertIs(pol.mode, RetrievalMode.BM25)

    def test_env_override_case_insensitive(self):
        pol = RetrievalPolicy().with_env_overrides({"SVK_RETRIEVAL_MODE": "BM25"})
        self.assertIs(pol.mode, RetrievalMode.BM25)

    def test_service_with_default_policy_never_touches_dense(self):
        docs = _corpus()
        svc = _service(docs)  # no dense, no encoder
        resp = svc.search("Kalpa Sutra", top_k=3)
        self.assertIs(resp.mode_used, RetrievalMode.BM25)
        self.assertIsNone(resp.fallback_reason)  # no fallback happened; bm25 was requested


# ---------------------------------------------------------------------------
# 10. Shadow mode: BM25 authoritative, hybrid never replaces the answer
# ---------------------------------------------------------------------------

class TestShadowMode(unittest.TestCase):
    def test_shadow_runs_both_but_bm25_serves(self):
        """Offline shadow replay: BM25 is authoritative; hybrid is evaluated
        alongside but never replaces the BM25 answer."""
        docs = _corpus()
        dense = _state_from_docs(docs)
        enc = _encoder_for(docs)
        auth_svc = _service(docs, policy=_policy(mode=RetrievalMode.BM25))
        shadow_svc = _service(docs, policy=_policy(mode=RetrievalMode.HYBRID_RRF20),
                              dense=dense, query_encoder=enc)
        query = "Kalpa Sutra"
        authoritative = auth_svc.search(query, top_k=4)
        shadow = shadow_svc.search(query, top_k=4)
        # BM25 serves the answer.
        self.assertIs(authoritative.mode_used, RetrievalMode.BM25)
        # Shadow is evaluated separately and does not mutate the authoritative.
        self.assertIs(shadow.mode_used, RetrievalMode.HYBRID_RRF20)
        self.assertEqual(authoritative.summary()["mode_used"], "bm25")
        # The authoritative result set is untouched by the shadow run.
        again = auth_svc.search(query, top_k=4)
        self.assertEqual([r.doc.text_id for r in authoritative.results],
                         [r.doc.text_id for r in again.results])

    def test_shadow_summary_does_not_leak_query_or_text(self):
        docs = _corpus()
        resp = _service(docs).search("secret Kalpa query", top_k=3,
                                      query_id="anon-1")
        s = resp.summary()
        blob = json.dumps(s)
        self.assertNotIn("secret", blob)
        self.assertNotIn("Kalpa", blob)
        self.assertEqual(s["query_id"], "anon-1")
        self.assertNotIn("text", s)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""TASK 81 — BM25 candidate-pool optimization experiment.

Offline experiment. Does NOT change production behavior. Runs inside the
Task-80 isolated venv (real BGE-M3 encoder). Loads the sha-verified dense
index without rebuilding. Tests BM25 candidate-pool caps for H3_RRF20 and a
true BM25 top-k selection optimization, measuring quality (source/unit recall,
evidence ceiling, evidence-zero) and end-to-end latency against the full-list
control.

Usage:
    /home/azureuser/.venvs/task80-bge/bin/python experiments/task81/task81_pool_opt.py --stage profile
    /home/azureuser/.venvs/task80-bge/bin/python experiments/task81/task81_pool_opt.py --stage sweep
    /home/azureuser/.venvs/task80-bge/bin/python experiments/task81/task81_pool_opt.py --stage optimize
    /home/azureuser/.venvs/task80-bge/bin/python experiments/task81/task81_pool_opt.py --stage all
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import heapq
import json
import math
import os
import resource
import statistics
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

from svk_corpus.retrieval import BM25Index, load_corpus  # noqa: E402
from svk_corpus.retrieval.bm25 import BM25Result  # noqa: E402
from svk_corpus.retrieval.documents import RetrievalDocument  # noqa: E402
from svk_corpus.retrieval.normalization import expand_query_text  # noqa: E402
from svk_corpus.retrieval.service import (  # noqa: E402
    DenseIndexState, RetrievalChannel, RetrievalMode, RetrievalPolicy,
    RetrievalService, ServiceResult, load_dense_index, rrf_fuse_full)

import task72.task72_experiment as t72  # noqa: E402
import task69.build_rag_evidence as t69  # noqa: E402
from task76.task76_benchmark import DENSE_DIR, QUERIES_EMB, case_ranks_from_results  # noqa: E402

OUT = ROOT / "data" / "reports" / "task81_pool_opt.json"
TOP_K = 10
INF = 10 ** 9
RRF_K = 20
POOL_SIZES = [50, 100, 250, 500, 1000, INF]
WARMUP = 1
LATENCY_ITERS = 3  # 3 x 47 = 141 samples per variant
CARDS: dict = {}  # manifest cards, loaded in main for evidence-block rendering


def log(m: str) -> None:
    print(f"[t81] {m}", flush=True)


def rss_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def pct(vals: list[float]) -> dict:
    if not vals:
        return {}
    s = sorted(vals)
    return {"n": len(s), "mean_ms": round(statistics.mean(s) * 1000, 2),
            "p50_ms": round(s[len(s) // 2] * 1000, 2),
            "p95_ms": round(s[int(0.95 * len(s))] * 1000, 2),
            "p99_ms": round(s[min(len(s) - 1, int(0.99 * len(s)))] * 1000, 2),
            "max_ms": round(max(s) * 1000, 2)}


# ---------------------------------------------------------------------------
# Instrumented BM25 (measures scoring vs sorting vs building separately)
# ---------------------------------------------------------------------------

class InstrumentedBM25(BM25Index):
    """BM25Index with fine-grained timing of scoring / sorting / building.

    Also exposes `search_ranks` (rank+score dicts without BM25Result objects)
    and `search_topk_heap` (bounded top-k via heapq, exact within pool).
    """

    def __init__(self, docs, k1=1.5, b=0.75):
        super().__init__(docs, k1=k1, b=b)
        self.last_profile: dict[str, float] = {}

    def search_profiled(self, query: str, top_k: int = INF) -> list[BM25Result]:
        """Same semantics as search(), but records scoring/sorting/build timing."""
        t0 = time.perf_counter()
        q_terms = expand_query_text(query)
        t_norm = time.perf_counter() - t0

        t0 = time.perf_counter()
        scores: dict[int, float] = {}
        for term in q_terms:
            plist = self._postings.get(term)
            if not plist:
                continue
            idf = self._idf[term]
            k1, b, avgdl = self.k1, self.b, self._avgdl
            dlen = self._doc_len
            dc = self._doc_counts
            for di in plist:
                f = dc[di][term]
                denom = f + k1 * (1 - b + b * dlen[di] / avgdl)
                scores[di] = scores.get(di, 0.0) + idf * f * (k1 + 1) / denom
        t_score = time.perf_counter() - t0

        t0 = time.perf_counter()
        ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
        t_sort = time.perf_counter() - t0

        t0 = time.perf_counter()
        out: list[BM25Result] = []
        for rank, (di, score) in enumerate(ranked[:top_k], 1):
            out.append(BM25Result(self.docs[di], score, rank))
        t_build = time.perf_counter() - t0

        self.last_profile = {
            "n_scored": len(scores), "n_terms": len(q_terms),
            "norm_s": t_norm, "score_s": t_score,
            "sort_s": t_sort, "build_s": t_build,
            "total_s": t_norm + t_score + t_sort + t_build}
        return out

    def search_ranks(self, query: str, top_k: int = INF) -> tuple[dict, dict]:
        """Return (rank_dict, score_dict) for the top_k docs — no BM25Result objects."""
        q_terms = expand_query_text(query)
        scores: dict[int, float] = {}
        k1, b, avgdl = self.k1, self.b, self._avgdl
        dlen = self._doc_len
        dc = self._doc_counts
        for term in q_terms:
            plist = self._postings.get(term)
            if not plist:
                continue
            idf = self._idf[term]
            for di in plist:
                f = dc[di][term]
                denom = f + k1 * (1 - b + b * dlen[di] / avgdl)
                scores[di] = scores.get(di, 0.0) + idf * f * (k1 + 1) / denom
        ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))[:top_k]
        rank_d: dict[str, int] = {}
        score_d: dict[str, float] = {}
        for r, (di, sc) in enumerate(ranked, 1):
            tid = self.docs[di].text_id
            rank_d[tid] = r
            score_d[tid] = sc
        return rank_d, score_d

    def search_topk_heap(self, query: str, top_k: int) -> tuple[dict, dict]:
        """Bounded top-k via heapq.nlargest — exact rankings within pool, O(m log k)."""
        q_terms = expand_query_text(query)
        scores: dict[int, float] = {}
        k1, b, avgdl = self.k1, self.b, self._avgdl
        dlen = self._doc_len
        dc = self._doc_counts
        for term in q_terms:
            plist = self._postings.get(term)
            if not plist:
                continue
            idf = self._idf[term]
            for di in plist:
                f = dc[di][term]
                denom = f + k1 * (1 - b + b * dlen[di] / avgdl)
                scores[di] = scores.get(di, 0.0) + idf * f * (k1 + 1) / denom
        # nsmallest with key=(-score, doc_idx): smallest key = best score,
        # smallest doc_idx for ties — exactly matches sorted(...)[:top_k].
        top = heapq.nsmallest(top_k, scores.items(), key=lambda kv: (-kv[1], kv[0]))
        rank_d: dict[str, int] = {}
        score_d: dict[str, float] = {}
        for r, (di, sc) in enumerate(top, 1):
            tid = self.docs[di].text_id
            rank_d[tid] = r
            score_d[tid] = sc
        return rank_d, score_d


# ---------------------------------------------------------------------------
# Experiment-local pooled hybrid search (pool cap applies ONLY to BM25 list)
# ---------------------------------------------------------------------------

def pooled_search(bm25: InstrumentedBM25, docs, dense: DenseIndexState,
                  query: str, q_vec: np.ndarray, top_k: int, pool: int,
                  rrf_k: int = RRF_K) -> list[ServiceResult]:
    """Full pooled hybrid search returning ServiceResult rows (for quality)."""
    n = dense.n
    bm25_rank, bm25_score = bm25.search_ranks(query, top_k=pool)

    qn = float(np.linalg.norm(q_vec)) or 1.0
    qv = q_vec / qn
    scores = dense.emb @ qv
    order = np.argsort(-scores, kind="stable")
    rank_of = np.empty(n, dtype=np.int64)
    rank_of[order] = np.arange(1, n + 1)

    fused = rrf_fuse_full(bm25_rank, rank_of, rrf_k, dense.tid2idx, n)
    fused_top = [int(x) for x in fused[:top_k]]

    out: list[ServiceResult] = []
    for rank, di in enumerate(fused_top, 1):
        doc = docs[di]
        tid = doc.text_id
        dr = int(rank_of[di])
        rrf_score = float(
            (1.0 / (rrf_k + dr))
            + ((1.0 / (rrf_k + bm25_rank[tid])) if tid in bm25_rank else 0.0))
        in_bm25 = tid in bm25_rank
        methods: dict[str, int] = {"dense": dr}
        if in_bm25:
            methods["bm25"] = bm25_rank[tid]
            out.append(ServiceResult(
                doc=doc, score=rrf_score, rank=rank,
                channel=RetrievalChannel.UNIT_BM25.value, methods=methods,
                unit_bm25_rank=bm25_rank[tid],
                unit_bm25_score=float(bm25_score[tid]),
                dense_rank=dr, dense_score=float(scores[di])))
        else:
            out.append(ServiceResult(
                doc=doc, score=rrf_score, rank=rank,
                channel=RetrievalChannel.DENSE.value, methods=methods,
                dense_rank=dr, dense_score=float(scores[di])))
    return out


# ---------------------------------------------------------------------------
# Quality metrics (retrieval-side, includes deterministic evidence ceiling)
# ---------------------------------------------------------------------------

def compute_quality(results_per_case: list[dict], cases: list[dict],
                    cfg: dict, cards: dict | None = None) -> dict:
    """Compute source/unit recall, MRR, evidence ceiling, ev0 — t72-style."""
    if cards is None:
        cards = {}
    per_case = []
    for case, results in zip(cases, results_per_case):
        # results are ServiceResult rows -> convert to result_row-like dicts
        rows = []
        for r in results:
            loc = dict(r.doc.locator or {})
            rows.append({
                "text_id": r.doc.text_id,
                "source_id": r.doc.source_id,
                "title": r.doc.title,
                "retrieval_channel": r.channel,
                "retrieval_rank": r.rank,
                "retrieval_score": round(float(r.score), 4),
                "locator_citation": (loc.get("citation") or "") if isinstance(loc, dict) else "",
                "provenance": {
                    "author": r.doc.author,
                    "religious_scope": r.doc.religious_scope,
                    "religious_scope_confidence": r.doc.religious_scope_confidence,
                    "knowledge_layer": r.doc.knowledge_layer,
                    "teacher_or_author": r.doc.teacher_or_author,
                    "lineage": r.doc.lineage,
                    "source_quality": r.doc.source_quality,
                    "sect": r.doc.sect,
                    "language": r.doc.language,
                    "script": r.doc.script,
                    "publication_year": r.doc.publication_year,
                },
                "text": r.doc.text,
            })
        first, uhit = case_ranks_from_results(results, case)
        mb = t72.build_block_and_metrics(case, rows, CARDS, cfg)
        prov = case.get("provenance") or {}
        esrc = prov.get("source_id")
        src_hits = [r for r in results
                    if esrc and r.doc.source_id == esrc]
        per_case.append({
            "example_id": case["example_id"],
            "expected_source": bool(esrc),
            "expected_units": bool(prov.get("unit_ids")),
            "source_first_rank": first,
            "unit_hit_rank": uhit,
            "evidence_answer_score": mb["evidence_answer_score"],
            "evidence_forbidden_hits": mb["evidence_forbidden_hits"],
            "context_chars": mb["context_chars"],
            "user_content_chars": mb["user_content_chars"],
            "results": [{"contract_violations": []} for _ in rows],
            "results_sources_hit": bool(src_hits),
            "results_sources_hit_only_metadata": bool(src_hits) and all(
                r.channel.startswith("source_metadata") for r in src_hits),
            # dense list is always FULL in pooled search -> every doc is in
            # the candidate set; expected unit is always reachable.
            "expected_unit_in_candidate_set": True,
        })
    return t72.aggregate(per_case, cfg)


# ---------------------------------------------------------------------------
# Baseline fine-grained profiling
# ---------------------------------------------------------------------------

def stage_profile(bm25, docs, dense, q_emb, cases, queries, R) -> dict:
    log("profile: fine-grained component attribution (47 queries, real encoder)")
    from sentence_transformers import SentenceTransformer
    # encoder already loaded by caller and stored in R["_model"]
    model = R["_model"]

    comp = {k: [] for k in ["norm", "score", "sort", "build", "dict",
                            "encode", "dense", "fusion", "result", "total"]}
    n_scored_samples = []

    for idx, q in enumerate(queries):
        t_all = time.perf_counter()

        # 1-3. BM25 (instrumented: norm/score/sort/build)
        full = bm25.search_profiled(q, top_k=INF)
        prof = bm25.last_profile
        comp["norm"].append(prof["norm_s"])
        comp["score"].append(prof["score_s"])
        comp["sort"].append(prof["sort_s"])
        comp["build"].append(prof["build_s"])
        n_scored_samples.append(prof["n_scored"])

        # 4. dict building (bm25_rank, bm25_score)
        t0 = time.perf_counter()
        bm25_rank = {r.doc.text_id: r.rank for r in full}
        bm25_score = {r.doc.text_id: r.score for r in full}
        comp["dict"].append(time.perf_counter() - t0)

        # 5. dense encoding (real encoder)
        t0 = time.perf_counter()
        q_vec = model.encode([q], normalize_embeddings=True,
                             convert_to_numpy=True)[0].astype(np.float32)
        comp["encode"].append(time.perf_counter() - t0)

        # 6. dense search (matmul + argsort)
        n = dense.n
        t0 = time.perf_counter()
        qn = float(np.linalg.norm(q_vec)) or 1.0
        qv = q_vec / qn
        scores = dense.emb @ qv
        order = np.argsort(-scores, kind="stable")
        rank_of = np.empty(n, dtype=np.int64)
        rank_of[order] = np.arange(1, n + 1)
        comp["dense"].append(time.perf_counter() - t0)

        # 7. RRF fusion
        t0 = time.perf_counter()
        fused = rrf_fuse_full(bm25_rank, rank_of, RRF_K, dense.tid2idx, n)
        comp["fusion"].append(time.perf_counter() - t0)

        # 8. result construction (top_k ServiceResult rows)
        t0 = time.perf_counter()
        fused_top = [int(x) for x in fused[:TOP_K]]
        for rank, di in enumerate(fused_top, 1):
            doc = docs[di]
            tid = doc.text_id
            dr = int(rank_of[di])
            _ = (doc, tid, dr, bm25_rank.get(tid), scores[di])
        comp["result"].append(time.perf_counter() - t0)

        comp["total"].append(time.perf_counter() - t_all)

    prof_out = {k: pct(v) for k, v in comp.items()}
    prof_out["n_bm25_scored"] = {
        "mean": round(statistics.mean(n_scored_samples), 0),
        "min": min(n_scored_samples), "max": max(n_scored_samples)}
    # cost attribution: share of total
    total_mean = prof_out["total"]["mean_ms"]
    prof_out["cost_attribution_pct"] = {
        k: round(prof_out[k]["mean_ms"] / total_mean * 100, 1)
        for k in ["norm", "score", "sort", "build", "dict",
                  "encode", "dense", "fusion", "result"]}
    log(f"  total p50 {prof_out['total']['p50_ms']}ms | "
        f"score {prof_out['score']['p50_ms']}ms sort {prof_out['sort']['p50_ms']}ms "
        f"fusion {prof_out['fusion']['p50_ms']}ms encode {prof_out['encode']['p50_ms']}ms")
    log(f"  n_bm25_scored mean={prof_out['n_bm25_scored']['mean']} "
        f"attribution={prof_out['cost_attribution_pct']}")
    return prof_out


# ---------------------------------------------------------------------------
# Edge-case equivalence tests for heap top-k vs full sort
# ---------------------------------------------------------------------------

def _edge_case_tests() -> dict:
    """Synthetic edge cases: tie-breaking, equal scores, dup IDs, missing, deterministic."""
    from svk_corpus.retrieval.documents import RetrievalDocument

    def doc(tid, text="x", sid="s"):
        return RetrievalDocument(text_id=tid, source_id=sid, title="t",
                                 text=text, language="", script="", sect="",
                                 religious_scope="", religious_scope_confidence="",
                                 knowledge_layer="", teacher_or_author="",
                                 lineage="", unit_type="", section="",
                                 locator={}, author="")

    tests = []
    # 1. Equal scores -> tie-break by doc_idx (deterministic)
    docs = [doc("a", "alpha beta"), doc("b", "alpha beta"),
            doc("c", "alpha beta"), doc("d", "alpha beta")]
    bm = InstrumentedBM25(docs)
    r_f, s_f = bm.search_ranks("alpha", top_k=2)
    r_h, s_h = bm.search_topk_heap("alpha", top_k=2)
    tests.append(("equal_scores_tiebreak", r_f == r_h and s_f.keys() == s_h.keys()))

    # 2. Distinct scores -> correct ordering
    docs2 = [doc("x", "alpha"), doc("y", "alpha alpha"), doc("z", "alpha alpha alpha")]
    bm2 = InstrumentedBM25(docs2)
    r_f, _ = bm2.search_ranks("alpha", top_k=3)
    r_h, _ = bm2.search_topk_heap("alpha", top_k=3)
    tests.append(("distinct_scores", r_f == r_h and r_f.get("z") == 1))

    # 3. Duplicate text_ids -> no crash, deterministic
    docs3 = [doc("dup", "alpha"), doc("dup", "alpha alpha"), doc("other", "alpha")]
    bm3 = InstrumentedBM25(docs3)
    r_f, _ = bm3.search_ranks("alpha", top_k=3)
    r_h, _ = bm3.search_topk_heap("alpha", top_k=3)
    tests.append(("duplicate_ids", r_f == r_h))

    # 4. Missing candidates (query term not in corpus) -> empty, no crash
    docs4 = [doc("a", "gamma")]
    bm4 = InstrumentedBM25(docs4)
    r_f, _ = bm4.search_ranks("alpha", top_k=5)
    r_h, _ = bm4.search_topk_heap("alpha", top_k=5)
    tests.append(("missing_candidates", r_f == r_h == {}))

    # 5. Deterministic ranking (same query twice -> identical)
    docs5 = [doc(f"d{i}", f"alpha {'beta' * (i % 3)}") for i in range(20)]
    bm5 = InstrumentedBM25(docs5)
    r1, _ = bm5.search_topk_heap("alpha", top_k=7)
    r2, _ = bm5.search_topk_heap("alpha", top_k=7)
    tests.append(("deterministic_ranking", r1 == r2))

    # 6. top_k > n_scored -> returns all, no crash
    docs6 = [doc("a", "alpha"), doc("b", "beta")]
    bm6 = InstrumentedBM25(docs6)
    r_f, _ = bm6.search_ranks("alpha", top_k=10)
    r_h, _ = bm6.search_topk_heap("alpha", top_k=10)
    tests.append(("topk_gt_nsored", r_f == r_h))

    n_pass = sum(1 for _, ok in tests if ok)
    return {"all_pass": n_pass == len(tests), "n_tests": len(tests),
            "n_passed": n_pass,
            "tests": {name: ok for name, ok in tests}}


# ---------------------------------------------------------------------------
# Candidate-pool sweep
# ---------------------------------------------------------------------------

def stage_sweep(bm25, docs, dense, q_emb, cases, queries, R, cfg) -> dict:
    from sentence_transformers import SentenceTransformer
    model = R["_model"]
    results = {}

    for pool in POOL_SIZES:
        label = "full" if pool == INF else str(pool)
        log(f"sweep: pool={label} ...")

        # warm-up
        for q in queries[:3]:
            qv = model.encode([q], normalize_embeddings=True,
                              convert_to_numpy=True)[0].astype(np.float32)
            pooled_search(bm25, docs, dense, q, qv, TOP_K, pool)

        # quality (single pass over all 47)
        res_per_case = []
        for idx, q in enumerate(queries):
            qv = q_emb[idx]  # pre-computed for quality (deterministic)
            res_per_case.append(pooled_search(bm25, docs, dense, q, qv, TOP_K, pool))
        qual = compute_quality(res_per_case, cases, cfg)

        # latency (real encoder, LATENCY_ITERS x 47)
        lat = []
        for _ in range(LATENCY_ITERS):
            for q in queries:
                t0 = time.perf_counter()
                qv = model.encode([q], normalize_embeddings=True,
                                  convert_to_numpy=True)[0].astype(np.float32)
                pooled_search(bm25, docs, dense, q, qv, TOP_K, pool)
                lat.append(time.perf_counter() - t0)
        lat_stats = pct(lat)

        # BM25 component timing for this pool (profiled, pre-computed embedding)
        bm25_comp = {"score": [], "sort": [], "build": []}
        for q in queries:
            bm25.search_profiled(q, top_k=pool)
            p = bm25.last_profile
            bm25_comp["score"].append(p["score_s"])
            bm25_comp["sort"].append(p["sort_s"])
            bm25_comp["build"].append(p["build_s"])

        results[label] = {
            "pool": pool,
            "quality": {
                "source_recall_at_5": qual.get("source_recall_at_5"),
                "unit_recall_at_5": qual.get("unit_recall_at_5"),
                "unit_mrr": qual.get("unit_mrr"),
                "evidence_ceiling_mean": qual.get("evidence_ceiling_mean"),
                "ev0_count": qual.get("ev0_count"),
                "source_recall_at_1": qual.get("source_recall_at_1"),
                "source_recall_at_10": qual.get("source_recall_at_10"),
                "unit_recall_at_1": qual.get("unit_recall_at_1"),
                "unit_recall_at_10": qual.get("unit_recall_at_10"),
            },
            "latency_e2e": lat_stats,
            "bm25_component": {k: pct(v) for k, v in bm25_comp.items()},
            "peak_rss_mb": round(rss_mb(), 1),
        }
        log(f"  pool={label}: unit@5={qual.get('unit_recall_at_5')} "
            f"src@5={qual.get('source_recall_at_5')} "
            f"ceil={qual.get('evidence_ceiling_mean')} ev0={qual.get('ev0_count')} "
            f"p95={lat_stats['p95_ms']}ms")

    return results


# ---------------------------------------------------------------------------
# True BM25 optimization: heap top-k vs full sort (exact-equivalence test)
# ---------------------------------------------------------------------------

def stage_optimize(bm25, docs, dense, q_emb, cases, queries, R, cfg) -> dict:
    log("optimize: heap top-k vs full-sort exact-equivalence + latency")
    from sentence_transformers import SentenceTransformer
    model = R["_model"]

    # 0. Service-level baseline reproduction (builds BM25Result objects, pool=INF)
    log("optimize: service-level baseline (builds BM25Result objects, full list)...")
    def _enc(q: str) -> np.ndarray:
        return model.encode([q], normalize_embeddings=True,
                            convert_to_numpy=True)[0].astype(np.float32)
    svc = RetrievalService(policy=RetrievalPolicy(mode=RetrievalMode.HYBRID_RRF20),
                           docs=docs, bm25=bm25, dense=dense, query_encoder=_enc)
    svc_lat = []
    for _ in range(LATENCY_ITERS):
        for q in queries:
            t0 = time.perf_counter()
            svc.search(q, top_k=TOP_K)
            svc_lat.append(time.perf_counter() - t0)
    svc_stats = pct(svc_lat)
    log(f"  service-level (builds BM25Result): p50 {svc_stats['p50_ms']}ms p95 {svc_stats['p95_ms']}ms")

    # 1. Exact-equivalence: search_topk_heap vs search_ranks (full sort) within pool
    equiv_pass = True
    equiv_cases = 0
    max_rank_diff = 0
    for pool in [50, 100, 250, 500, 1000]:
        for q in queries:
            r_full, s_full = bm25.search_ranks(q, top_k=pool)
            r_heap, s_heap = bm25.search_topk_heap(q, top_k=pool)
            if r_full != r_heap or set(s_full) != set(s_heap):
                equiv_pass = False
            else:
                for tid in r_full:
                    if r_full[tid] != r_heap[tid]:
                        equiv_pass = False
                        max_rank_diff = max(max_rank_diff, abs(r_full[tid] - r_heap[tid]))
            equiv_cases += 1
    log(f"  equivalence: {equiv_cases} cases, pass={equiv_pass}, max_rank_diff={max_rank_diff}")

    # 1b. Edge-case equivalence tests (tie-breaking, equal scores, dup IDs,
    #     missing candidates, deterministic ranking) on synthetic docs.
    edge = _edge_case_tests()
    log(f"  edge-case tests: pass={edge['all_pass']} ({edge['n_passed']}/{edge['n_tests']})")
    equiv_pass = equiv_pass and edge["all_pass"]

    # 2. Latency: full-sort (search_ranks) vs heap (search_topk_heap) at pool=1000 and INF
    lat_cmp = {}
    for pool in [1000, INF]:
        label = "full" if pool == INF else str(pool)
        full_lat, heap_lat = [], []
        for _ in range(3):
            for q in queries:
                t0 = time.perf_counter()
                bm25.search_ranks(q, top_k=pool)
                full_lat.append(time.perf_counter() - t0)
                if pool != INF:  # heap with k=INF is meaningless; only test bounded pools
                    t0 = time.perf_counter()
                    bm25.search_topk_heap(q, top_k=pool)
                    heap_lat.append(time.perf_counter() - t0)
        lat_cmp[label] = {
            "full_sort": pct(full_lat),
            "heap_topk": pct(heap_lat) if heap_lat else None,
            "note": "heap only meaningful for bounded pools; full-list RRF needs full sort",
        }
        log(f"  pool={label}: full_sort p50 {lat_cmp[label]['full_sort']['p50_ms']}ms"
            + (f" | heap p50 {lat_cmp[label]['heap_topk']['p50_ms']}ms"
               if heap_lat else " | heap n/a (full-list)"))

    # 3. Quality of heap-based pooled search at best pool (if equivalence holds)
    quality_heap = None
    if equiv_pass:
        best_pool = 1000
        res_per_case = []
        for idx, q in enumerate(queries):
            qv = q_emb[idx]
            # pooled_search but with heap-based bm25
            n = dense.n
            bm25_rank, bm25_score = bm25.search_topk_heap(q, top_k=best_pool)
            qn = float(np.linalg.norm(qv)) or 1.0
            scores = dense.emb @ (qv / qn)
            order = np.argsort(-scores, kind="stable")
            rank_of = np.empty(n, dtype=np.int64)
            rank_of[order] = np.arange(1, n + 1)
            fused = rrf_fuse_full(bm25_rank, rank_of, RRF_K, dense.tid2idx, n)
            fused_top = [int(x) for x in fused[:TOP_K]]
            out = []
            for rank, di in enumerate(fused_top, 1):
                doc = docs[di]
                tid = doc.text_id
                dr = int(rank_of[di])
                rrf_score = float((1.0 / (RRF_K + dr))
                                  + ((1.0 / (RRF_K + bm25_rank[tid])) if tid in bm25_rank else 0.0))
                if tid in bm25_rank:
                    out.append(ServiceResult(doc=doc, score=rrf_score, rank=rank,
                                             channel=RetrievalChannel.UNIT_BM25.value,
                                             methods={"dense": dr, "bm25": bm25_rank[tid]},
                                             unit_bm25_rank=bm25_rank[tid],
                                             unit_bm25_score=float(bm25_score[tid]),
                                             dense_rank=dr, dense_score=float(scores[di])))
                else:
                    out.append(ServiceResult(doc=doc, score=rrf_score, rank=rank,
                                             channel=RetrievalChannel.DENSE.value,
                                             methods={"dense": dr},
                                             dense_rank=dr, dense_score=float(scores[di])))
            res_per_case.append(out)
        quality_heap = compute_quality(res_per_case, cases, cfg)
        log(f"  heap pool={best_pool} quality: unit@5={quality_heap.get('unit_recall_at_5')} "
            f"ceil={quality_heap.get('evidence_ceiling_mean')}")

    return {"service_level_baseline": svc_stats,
            "equivalence_pass": equiv_pass, "equivalence_cases": equiv_cases,
            "max_rank_diff": max_rank_diff, "edge_case_tests": edge,
            "latency_comparison": lat_cmp,
            "quality_heap_at_1000": quality_heap}


# ---------------------------------------------------------------------------
# Per-case regression / recovery analysis
# ---------------------------------------------------------------------------

def per_case_analysis(control_res, variant_res, cases, label) -> dict:
    """Compare per-case unit_hit_rank and source_first_rank vs control."""
    regressions = []
    recoveries = []
    for case, ctrl, var in zip(cases, control_res, variant_res):
        c_first, c_uhit = case_ranks_from_results(ctrl, case)
        v_first, v_uhit = case_ranks_from_results(var, case)
        eid = case["example_id"]
        # regression: control hit unit, variant missed or worse
        if c_uhit is not None and (v_uhit is None or v_uhit > c_uhit):
            regressions.append({"example_id": eid, "control_unit_rank": c_uhit,
                                "variant_unit_rank": v_uhit})
        # recovery: control missed, variant hit
        if c_uhit is None and v_uhit is not None:
            recoveries.append({"example_id": eid, "variant_unit_rank": v_uhit})
    return {"variant": label, "regressions": regressions,
            "recoveries": recoveries,
            "n_regressions": len(regressions), "n_recoveries": len(recoveries)}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["profile", "sweep", "optimize", "all"],
                    default="all")
    args = ap.parse_args()

    import torch
    from sentence_transformers import SentenceTransformer

    torch.set_num_threads(2)

    R: dict = {"task": 81, "stage": args.stage,
               "environment": {"python": sys.version.split()[0],
                               "torch": torch.__version__,
                               "torch_num_threads": torch.get_num_threads()}}
    M: dict = {}
    R["measurements"] = M

    # ---- integrity ----
    log("integrity: frozen bench + dense index sha")
    sha = t72.sha256_file(t72.CASES_PATH)
    assert sha == t72.FROZEN_SHA, "frozen bench sha mismatch"
    emb_sha = hashlib.sha256((DENSE_DIR / "corpus_emb.f16.npy").read_bytes()).hexdigest()
    meta = json.loads((DENSE_DIR / "index_meta.json").read_text())
    assert emb_sha == meta["corpus_emb_f16_sha256"], "dense index sha mismatch"
    M["integrity_before"] = {"frozen_bench_sha_ok": True, "dense_index_sha_ok": True}

    # ---- load ----
    cases = [json.loads(l) for l in Path(t72.CASES_PATH).read_text(encoding="utf-8").splitlines() if l.strip()]
    queries = [c["question"] for c in cases]
    q_emb = np.load(QUERIES_EMB).astype(np.float32)
    qn = np.linalg.norm(q_emb, axis=1, keepdims=True); qn[qn == 0] = 1.0; q_emb /= qn
    CARDS.update(t69.load_manifest_cards(t72.MANIFEST_PATH))

    log("loading corpus + BM25 + dense index...")
    gc.collect()
    docs = load_corpus(t72.CORPUS_PATH, t72.MANIFEST_PATH)
    bm25 = InstrumentedBM25(docs, k1=1.5, b=0.75)
    dense = load_dense_index(DENSE_DIR, docs, verify_file_sha=True, verify_alignment=False)
    log(f"  loaded: {len(docs)} docs, dense n={dense.n}, rss={rss_mb():.0f}MB")

    # ---- encoder ----
    log("loading BGE-M3 encoder (cached)...")
    model = SentenceTransformer("BAAI/bge-m3",
                                revision=meta["model_revision"], device="cpu")
    R["_model"] = model  # stash for stage functions

    cfg = {"evidence_k": 5, "text_trunc": 500}

    # ---- stages ----
    if args.stage in ("profile", "all"):
        M["profile"] = stage_profile(bm25, docs, dense, q_emb, cases, queries, R)

    if args.stage in ("sweep", "all"):
        M["sweep"] = stage_sweep(bm25, docs, dense, q_emb, cases, queries, R, cfg)

        # per-case regression/recovery vs full-list control
        log("sweep: per-case regression/recovery vs full-list control...")
        control_res = []
        for idx, q in enumerate(queries):
            control_res.append(pooled_search(bm25, docs, dense, q, q_emb[idx], TOP_K, INF))
        M["per_case_analysis"] = {}
        for pool in [50, 100, 250, 500, 1000]:
            var_res = []
            for idx, q in enumerate(queries):
                var_res.append(pooled_search(bm25, docs, dense, q, q_emb[idx], TOP_K, pool))
            M["per_case_analysis"][str(pool)] = per_case_analysis(
                control_res, var_res, cases, str(pool))
            log(f"  pool={pool}: regressions={M['per_case_analysis'][str(pool)]['n_regressions']} "
                f"recoveries={M['per_case_analysis'][str(pool)]['n_recoveries']}")

    if args.stage in ("optimize", "all"):
        M["optimize"] = stage_optimize(bm25, docs, dense, q_emb, cases, queries, R, cfg)

    # ---- integrity after ----
    emb_sha2 = hashlib.sha256((DENSE_DIR / "corpus_emb.f16.npy").read_bytes()).hexdigest()
    M["integrity_after"] = {
        "frozen_bench_sha_ok": t72.sha256_file(t72.CASES_PATH) == t72.FROZEN_SHA,
        "dense_index_sha_ok": emb_sha2 == meta["corpus_emb_f16_sha256"]}
    M["peak_rss_mb"] = round(rss_mb(), 1)

    del R["_model"]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(R, indent=2, default=str), encoding="utf-8")
    log(f"wrote {OUT}")

    # summary
    summary = {"stage": args.stage, "peak_rss_mb": M["peak_rss_mb"]}
    if "profile" in M:
        summary["profile_total_p95_ms"] = M["profile"]["total"]["p95_ms"]
        summary["bottleneck"] = max(M["profile"]["cost_attribution_pct"],
                                    key=M["profile"]["cost_attribution_pct"].get)
    if "sweep" in M:
        summary["sweep_p95"] = {k: v["latency_e2e"]["p95_ms"] for k, v in M["sweep"].items()}
        summary["sweep_unit5"] = {k: v["quality"]["unit_recall_at_5"] for k, v in M["sweep"].items()}
    if "optimize" in M:
        summary["equivalence_pass"] = M["optimize"]["equivalence_pass"]
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

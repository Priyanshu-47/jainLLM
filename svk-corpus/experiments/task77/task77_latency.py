#!/usr/bin/env python3
"""Task 77 — serving latency, memory, and fusion-cost measurement.

Measures (locally, CPU-only, with the verified Task-74 dense index and
pre-computed query embeddings — the encoder is NOT run here):

  * Cold-start: corpus load, BM25 index build, dense index load.
  * BM25 search latency (production H1 pool=2000 and full-list top_k=INF).
  * Dense search latency (matmul + argsort over 164k docs).
  * Full-list RRF@20 fusion latency (rrf_fuse_full), profiled by component.
  * End-to-end H1 (BM25) and H3_RRF20 (hybrid) service latency.
  * Warm latency percentiles (p50/p95/p99) over a documented repeat workload.
  * Sequential throughput.
  * Peak RSS and on-disk index size.

Encoder latency is measured separately (BLOCKED locally — no torch, no GPU,
no identified serving environment); see task77_serving_env_audit.md.

Usage:
    PYTHONPATH=src:experiments python3 experiments/task77/task77_latency.py
"""

from __future__ import annotations

import gc
import json
import os
import resource
import statistics
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

from svk_corpus.retrieval import BM25Index, load_corpus  # noqa: E402
from svk_corpus.retrieval.service import (  # noqa: E402
    RetrievalMode, RetrievalPolicy, RetrievalService, load_dense_index,
    rrf_fuse_full)

import task72.task72_experiment as t72  # noqa: E402
from task76.task76_benchmark import DENSE_DIR, QUERIES_EMB  # noqa: E402

OUT = ROOT / "data" / "reports" / "task77_latency.json"
TOP_K = 10
INF = 10 ** 9
RRF_K = 20
WARM_REPEATS = 10          # 47 queries x 10 = 470 warm samples per mode
POOL = 2000                # production H1 BM25 pool


def log(msg: str) -> None:
    print(f"[t77-lat] {msg}", flush=True)


def rss_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def pct(vals: list[float]) -> dict:
    if not vals:
        return {}
    s = sorted(vals)
    def q(p: float) -> float:
        return round(s[min(len(s) - 1, int(p * len(s)))], 6)
    return {
        "n": len(s),
        "mean": round(statistics.mean(s), 6),
        "p50": q(0.50), "p95": q(0.95), "p99": q(0.99),
        "min": round(min(s), 6), "max": round(max(s), 6),
    }


def timed(fn, *a, **kw):
    t0 = time.perf_counter()
    out = fn(*a, **kw)
    return out, time.perf_counter() - t0


def main() -> int:
    report: dict = {"task": 77, "measurements": {}}
    M = report["measurements"]

    # ---------------- cold start ----------------
    log("cold-start: corpus load")
    gc.collect()
    rss0 = rss_mb()
    docs, t_corpus = timed(load_corpus, t72.CORPUS_PATH, t72.MANIFEST_PATH)
    n = len(docs)
    rss_after_corpus = rss_mb()
    log(f"  corpus: {n} docs in {t_corpus:.2f}s, rss {rss_after_corpus:.0f} MB")

    log("cold-start: BM25 index build")
    bm25, t_bm25_build = timed(BM25Index, docs, k1=1.5, b=0.75)
    rss_after_bm25 = rss_mb()

    log("cold-start: dense index load (sha + doc-count verified)")
    dense, t_dense_load = timed(load_dense_index, DENSE_DIR, docs,
                                verify_file_sha=True, verify_alignment=False)
    rss_after_dense = rss_mb()
    log(f"  dense: n={dense.n} in {t_dense_load:.2f}s, rss {rss_after_dense:.0f} MB")

    q_emb = np.load(QUERIES_EMB).astype(np.float32)
    qn = np.linalg.norm(q_emb, axis=1, keepdims=True)
    qn[qn == 0] = 1.0
    q_emb /= qn

    cases = [json.loads(l) for l in
             t72.CASES_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    queries = [c["question"] for c in cases]
    assert len(queries) == 47

    M["cold_start"] = {
        "corpus_load_s": round(t_corpus, 3),
        "bm25_index_build_s": round(t_bm25_build, 3),
        "dense_index_load_s": round(t_dense_load, 3),
        "total_startup_s": round(t_corpus + t_bm25_build + t_dense_load, 3),
        "corpus_docs": n,
        "rss_baseline_mb": round(rss0, 1),
        "rss_after_corpus_mb": round(rss_after_corpus, 1),
        "rss_after_bm25_mb": round(rss_after_bm25, 1),
        "rss_after_dense_mb": round(rss_after_dense, 1),
        "rss_delta_dense_mb": round(rss_after_dense - rss_after_bm25, 1),
        "note": "corpus load + BM25 build + dense load are sequential; "
                "dense load is optional (BM25-only serving skips it).",
    }

    # ---------------- per-component latency (47 frozen queries) ----------------
    log("component latency: BM25 pool=2000 (production H1)")
    bm25_pool_s: list[float] = []
    for q in queries:
        _, dt = timed(bm25.search, q, top_k=POOL)
        bm25_pool_s.append(dt)

    log("component latency: BM25 full-list (top_k=INF, H3 fusion input)")
    bm25_full_s: list[float] = []
    bm25_rank_cache: list[dict] = []
    bm25_score_cache: list[dict] = []
    for q in queries:
        full, dt = timed(bm25.search, q, top_k=INF)
        bm25_full_s.append(dt)
        bm25_rank_cache.append({r.doc.text_id: r.rank for r in full})
        bm25_score_cache.append({r.doc.text_id: r.score for r in full})

    log("component latency: dense search (matmul + argsort)")
    dense_search_s: list[float] = []
    rank_of_cache: list[np.ndarray] = []
    score_cache: list[np.ndarray] = []
    for i, q in enumerate(queries):
        def _dense():
            scores = dense.emb @ q_emb[i]
            order = np.argsort(-scores, kind="stable")
            rank_of = np.empty(dense.n, dtype=np.int64)
            rank_of[order] = np.arange(1, dense.n + 1)
            return scores, rank_of
        (scores, rank_of), dt = timed(_dense)
        dense_search_s.append(dt)
        score_cache.append(scores)
        rank_of_cache.append(rank_of)

    log("component latency: RRF@20 full-list fusion")
    fuse_s: list[float] = []
    fused_cache: list[np.ndarray] = []
    for i in range(len(queries)):
        fused, dt = timed(rrf_fuse_full, bm25_rank_cache[i], rank_of_cache[i],
                          RRF_K, dense.tid2idx, dense.n)
        fuse_s.append(dt)
        fused_cache.append(fused)

    # profile fusion internals on one query
    log("fusion micro-profile (single query, 200 iterations)")
    br = bm25_rank_cache[0]
    ro = rank_of_cache[0]
    n_f = dense.n
    t2idx = dense.tid2idx
    N_ITER = 200
    # score computation only
    t0 = time.perf_counter()
    for _ in range(N_ITER):
        score = 1.0 / (RRF_K + ro.astype(np.float64))
        bmr = np.full(n_f, INF, dtype=np.int64)
        for tid, r in br.items():
            di = t2idx[tid]
            score[di] += 1.0 / (RRF_K + r)
            bmr[di] = r
    t_score = (time.perf_counter() - t0) / N_ITER
    # lexsort only
    t0 = time.perf_counter()
    for _ in range(N_ITER):
        np.lexsort((np.arange(n_f), ro, bmr, -score))
    t_lexsort = (time.perf_counter() - t0) / N_ITER

    M["component_latency_47_queries"] = {
        "bm25_pool_2000_s": pct(bm25_pool_s),
        "bm25_full_list_s": pct(bm25_full_s),
        "dense_search_s": pct(dense_search_s),
        "rrf20_fusion_s": pct(fuse_s),
        "fusion_micro_profile": {
            "score_compute_s": round(t_score, 6),
            "lexsort_s": round(t_lexsort, 6),
            "dominant": "lexsort" if t_lexsort > t_score else "score_compute",
            "iterations": N_ITER,
            "n_candidates": n_f,
        },
    }
    log(f"  bm25 pool: {statistics.mean(bm25_pool_s)*1000:.1f} ms | "
        f"bm25 full: {statistics.mean(bm25_full_s)*1000:.1f} ms | "
        f"dense: {statistics.mean(dense_search_s)*1000:.1f} ms | "
        f"fusion: {statistics.mean(fuse_s)*1000:.1f} ms")

    # ---------------- end-to-end service latency (warm, repeat workload) ----------------
    log(f"end-to-end warm latency: {WARM_REPEATS} repeats x 47 queries")
    svc_h1 = RetrievalService(policy=RetrievalPolicy(mode=RetrievalMode.BM25),
                              docs=docs, bm25=bm25)
    svc_h3 = RetrievalService(
        policy=RetrievalPolicy(mode=RetrievalMode.HYBRID_RRF20),
        docs=docs, bm25=bm25, dense=dense, query_encoder=None)

    e2e_h1: list[float] = []
    e2e_h3: list[float] = []
    first_h1 = first_h3 = None
    for rep in range(WARM_REPEATS):
        for i, q in enumerate(queries):
            _, dt = timed(svc_h1.search, q, top_k=TOP_K)
            if rep == 0 and first_h1 is None:
                first_h1 = dt
            e2e_h1.append(dt)
            _, dt = timed(svc_h3.search, q, top_k=TOP_K,
                          query_embedding=q_emb[i])
            if rep == 0 and first_h3 is None:
                first_h3 = dt
            e2e_h3.append(dt)

    M["end_to_end_warm"] = {
        "workload": f"{WARM_REPEATS} sequential repeats of the 47 frozen queries",
        "samples_per_mode": len(e2e_h1),
        "H1_BM25_s": pct(e2e_h1),
        "H3_RRF20_s": pct(e2e_h3),
        "first_query_H1_s": round(first_h1, 6),
        "first_query_H3_s": round(first_h3, 6),
        "throughput_H1_qps": round(len(e2e_h1) / sum(e2e_h1), 2),
        "throughput_H3_qps": round(len(e2e_h3) / sum(e2e_h3), 2),
        "h3_over_h1_mean_ratio": round(
            statistics.mean(e2e_h3) / statistics.mean(e2e_h1), 3),
        "note": "Sequential single-threaded; no concurrent server exists. "
                "Query embeddings are pre-computed (encoder not run).",
    }
    log(f"  H1 p50 {M['end_to_end_warm']['H1_BM25_s']['p50']*1000:.1f} ms | "
        f"H3 p50 {M['end_to_end_warm']['H3_RRF20_s']['p50']*1000:.1f} ms | "
        f"H1 qps {M['end_to_end_warm']['throughput_H1_qps']} | "
        f"H3 qps {M['end_to_end_warm']['throughput_H3_qps']}")

    # ---------------- memory & disk ----------------
    disk_dense = (DENSE_DIR / "corpus_emb.f16.npy").stat().st_size
    M["memory_disk"] = {
        "peak_rss_mb": round(rss_mb(), 1),
        "dense_disk_bytes": disk_dense,
        "dense_loaded_f32_bytes": int(dense.emb.nbytes),
        "dense_index_load_s": round(t_dense_load, 3),
        "bm25_memory_bytes": "unresolved (python object graph; not directly measurable)",
        "corpus_docs": n,
    }

    # ---------------- failure / fallback observability ----------------
    log("fallback observability probe")
    logged: list[str] = []
    svc_fb = RetrievalService(
        policy=RetrievalPolicy(mode=RetrievalMode.HYBRID_RRF20,
                               fallback_on_dense_failure=True),
        docs=docs, bm25=bm25, logger=logged.append)
    resp = svc_fb.search(queries[0], top_k=3)
    M["fallback_probe"] = {
        "mode_used": resp.mode_used.value,
        "fallback_reason": resp.fallback_reason,
        "logged": any("fallback bm25" in m for m in logged),
        "results_nonempty": bool(resp.results),
        "pass": (resp.mode_used is RetrievalMode.BM25
                 and resp.fallback_reason is not None
                 and bool(resp.results)),
    }

    report["environment"] = {
        "cpu": "AMD EPYC 7763, 4 logical / 2 physical cores",
        "isa": "avx, avx2, fma (no avx512, no amx)",
        "ram_total_gb": round(os.sysconf("SC_PAGE_SIZE") *
                              os.sysconf("SC_PHYS_PAGES") / 2**30, 2),
        "gpu": "none",
        "python": sys.version.split()[0],
        "numpy": np.__version__,
        "torch": "absent",
        "device": "cpu-only",
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    log(f"wrote {OUT}")
    print(json.dumps({
        "cold_start_total_s": M["cold_start"]["total_startup_s"],
        "H1_p50_ms": round(M["end_to_end_warm"]["H1_BM25_s"]["p50"] * 1000, 1),
        "H3_p50_ms": round(M["end_to_end_warm"]["H3_RRF20_s"]["p50"] * 1000, 1),
        "H3_p99_ms": round(M["end_to_end_warm"]["H3_RRF20_s"]["p99"] * 1000, 1),
        "fusion_mean_ms": round(M["component_latency_47_queries"]["rrf20_fusion_s"]["mean"] * 1000, 1),
        "fusion_dominant": M["component_latency_47_queries"]["fusion_micro_profile"]["dominant"],
        "peak_rss_mb": M["memory_disk"]["peak_rss_mb"],
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

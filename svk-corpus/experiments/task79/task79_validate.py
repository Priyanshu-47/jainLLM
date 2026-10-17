#!/usr/bin/env python3
"""Task 79 — safe, bounded retrieval validation on the existing Azure VM.

Read-only w.r.t. the VM (no installs, no model downloads, no provisioning).
Loads the sha-verified Task-74 dense index + BM25, runs the frozen 47-case
benchmark in H1 (BM25) and H3_RRF20 (hybrid) modes using PRE-COMPUTED query
embeddings (queries_emb.f32.npy), and measures latency/memory.

The BGE-M3 ENCODER is NOT run: bge-m3 is not cached locally and
torch/sentence-transformers are absent; downloading/installing is out of
scope for this task.  Therefore end-to-end hybrid latency INCLUDING encoding
is UNRESOLVED; only retrieval-side (BM25 + dense search + fusion, with
pre-computed embeddings) is measured.  This is explicitly NOT represented as
end-to-end hybrid latency.

Usage:
    PYTHONPATH=src:experiments python3 experiments/task79/task79_validate.py
"""

from __future__ import annotations

import gc
import json
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
    DenseIndexUnavailable, RetrievalMode, RetrievalPolicy, RetrievalService,
    load_dense_index)

import task72.task72_experiment as t72  # noqa: E402
from task76.task76_benchmark import DENSE_DIR, QUERIES_EMB, case_ranks_from_results  # noqa: E402

OUT = ROOT / "data" / "reports" / "task79_azure_validation.json"
TOP_K = 10
INF = 10 ** 9
RRF_K = 20
WARM_REPEATS = 5  # 47 x 5 = 235 warm samples/mode (bounded)


def log(m: str) -> None:
    print(f"[t79] {m}", flush=True)


def rss_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def pct(vals):
    if not vals:
        return {}
    s = sorted(vals)
    return {"n": len(s), "mean": round(statistics.mean(s), 6),
            "p50": round(s[len(s)//2], 6),
            "p95": round(s[int(0.95*len(s))], 6),
            "p99": round(s[min(len(s)-1, int(0.99*len(s)))], 6),
            "max": round(max(s), 6)}


def main() -> int:
    R: dict = {"task": 79, "measurements": {}}
    M = R["measurements"]

    # ---- integrity ----
    log("integrity: frozen bench + dense index sha")
    sha = t72.sha256_file(t72.CASES_PATH)
    assert sha == t72.FROZEN_SHA
    import hashlib
    emb_sha = hashlib.sha256((DENSE_DIR / "corpus_emb.f16.npy").read_bytes()).hexdigest()
    meta = json.loads((DENSE_DIR / "index_meta.json").read_text())
    assert emb_sha == meta["corpus_emb_f16_sha256"]
    M["integrity"] = {"frozen_bench_sha_ok": True, "dense_index_sha_ok": True,
                      "frozen_bench_sha256": sha, "dense_emb_sha256": emb_sha[:16] + "..."}

    # ---- cold start ----
    log("cold start: corpus -> BM25 -> dense")
    gc.collect()
    t0 = time.perf_counter(); docs = load_corpus(t72.CORPUS_PATH, t72.MANIFEST_PATH); t_corpus = time.perf_counter()-t0
    n = len(docs)
    t0 = time.perf_counter(); bm25 = BM25Index(docs, k1=1.5, b=0.75); t_bm25 = time.perf_counter()-t0
    t0 = time.perf_counter()
    dense = load_dense_index(DENSE_DIR, docs, verify_file_sha=True, verify_alignment=False)
    t_dense = time.perf_counter()-t0
    M["cold_start"] = {
        "corpus_load_s": round(t_corpus, 3), "bm25_build_s": round(t_bm25, 3),
        "dense_load_s": round(t_dense, 3),
        "total_s": round(t_corpus + t_bm25 + t_dense, 3),
        "corpus_docs": n, "rss_after_mb": round(rss_mb(), 1)}
    log(f"  total {M['cold_start']['total_s']}s rss {M['cold_start']['rss_after_mb']}MB")

    # ---- queries + pre-computed embeddings ----
    cases = [json.loads(l) for l in
             t72.CASES_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    q_emb = np.load(QUERIES_EMB).astype(np.float32)
    qn = np.linalg.norm(q_emb, axis=1, keepdims=True); qn[qn == 0] = 1.0; q_emb /= qn
    queries = [c["question"] for c in cases]

    # ---- component latency (47 queries) ----
    log("component latency (pre-computed embeddings; encoder NOT in loop)")
    bm25_pool, bm25_full, dense_s, fuse_s = [], [], [], []
    for i, q in enumerate(queries):
        t0 = time.perf_counter(); bm25.search(q, top_k=2000); bm25_pool.append(time.perf_counter()-t0)
        t0 = time.perf_counter(); full = bm25.search(q, top_k=INF); bm25_full.append(time.perf_counter()-t0)
        rank = {r.doc.text_id: r.rank for r in full}
        t0 = time.perf_counter()
        scores = dense.emb @ q_emb[i]; order = np.argsort(-scores, kind="stable")
        rank_of = np.empty(dense.n, dtype=np.int64); rank_of[order] = np.arange(1, dense.n+1)
        dense_s.append(time.perf_counter()-t0)
        t0 = time.perf_counter()
        from svk_corpus.retrieval.service import rrf_fuse_full
        rrf_fuse_full(rank, rank_of, RRF_K, dense.tid2idx, dense.n)
        fuse_s.append(time.perf_counter()-t0)
    M["component_latency"] = {"bm25_pool2000_s": pct(bm25_pool),
                              "bm25_full_s": pct(bm25_full),
                              "dense_search_s": pct(dense_s),
                              "rrf_fusion_s": pct(fuse_s),
                              "note": "encoder excluded; pre-computed embeddings"}

    # ---- frozen-benchmark reproduction (H1 + H3, pre-computed embeddings) ----
    log("frozen benchmark reproduction (H1 + H3, pre-computed embeddings)")
    def recall(vals, k): return t72.recall(vals, k)
    def mrr(vals): return t72.mrr(vals)

    def run_mode(mode, dense_state):
        svc = RetrievalService(
            policy=RetrievalPolicy(mode=mode),
            docs=docs, bm25=bm25, dense=dense_state,
            query_encoder=None)
        per = []
        lat = []
        for i, c in enumerate(cases):
            t0 = time.perf_counter()
            resp = svc.search(c["question"], top_k=TOP_K,
                              query_embedding=q_emb[i] if mode is RetrievalMode.HYBRID_RRF20 else None)
            lat.append(time.perf_counter()-t0)
            first, uhit = case_ranks_from_results(resp.results, c)
            per.append({"src": first, "unit": uhit,
                        "exp_src": bool((c.get("provenance") or {}).get("source_id")),
                        "exp_unit": bool((c.get("provenance") or {}).get("unit_ids")),
                        "mode": resp.mode_used.value,
                        "fallback": resp.fallback_reason})
        src = [p["src"] for p in per if p["exp_src"]]
        unit = [p["unit"] for p in per if p["exp_unit"]]
        return {"agg": {"src@5": recall(src, 5), "unit@5": recall(unit, 5),
                        "src_mrr": mrr(src), "unit_mrr": mrr(unit),
                        "n_src": len(src), "n_unit": len(unit)},
                "latency_s": pct(lat),
                "modes": sorted({p["mode"] for p in per}),
                "fallbacks": sum(1 for p in per if p["fallback"])}

    h1 = run_mode(RetrievalMode.BM25, None)
    h3 = run_mode(RetrievalMode.HYBRID_RRF20, dense)
    M["frozen_benchmark"] = {
        "H1_BM25": h1, "H3_RRF20": h3,
        "expected": {"H1_unit5": 0.3846, "H1_src5": 0.9130,
                     "H3_unit5": 0.5385, "H3_src5": 0.9783},
        "reproduction_pass": (
            abs(h1["agg"]["unit@5"] - 0.3846) < 1e-3 and abs(h1["agg"]["src@5"] - 0.9130) < 1e-3 and
            abs(h3["agg"]["unit@5"] - 0.5385) < 1e-3 and abs(h3["agg"]["src@5"] - 0.9783) < 1e-3),
        "note": "pre-computed embeddings; encoder excluded from latency"}
    log(f"  reproduction_pass={M['frozen_benchmark']['reproduction_pass']} "
        f"H3 unit@5={h3['agg']['unit@5']} src@5={h3['agg']['src@5']}")

    # ---- warm e2e retrieval (pre-computed embeddings only) ----
    log(f"warm e2e retrieval latency ({WARM_REPEATS}x47, pre-computed embeddings)")
    svc_h1 = RetrievalService(policy=RetrievalPolicy(mode=RetrievalMode.BM25), docs=docs, bm25=bm25)
    svc_h3 = RetrievalService(policy=RetrievalPolicy(mode=RetrievalMode.HYBRID_RRF20),
                              docs=docs, bm25=bm25, dense=dense, query_encoder=None)
    e2e_h1, e2e_h3 = [], []
    for rep in range(WARM_REPEATS):
        for i, q in enumerate(queries):
            t0 = time.perf_counter(); svc_h1.search(q, top_k=TOP_K); e2e_h1.append(time.perf_counter()-t0)
            t0 = time.perf_counter(); svc_h3.search(q, top_k=TOP_K, query_embedding=q_emb[i]); e2e_h3.append(time.perf_counter()-t0)
    M["warm_e2e_retrieval_only"] = {
        "samples_per_mode": len(e2e_h1), "H1_s": pct(e2e_h1), "H3_s": pct(e2e_h3),
        "throughput_H1_qps": round(len(e2e_h1)/sum(e2e_h1), 2),
        "throughput_H3_qps": round(len(e2e_h3)/sum(e2e_h3), 2),
        "note": "PRE-COMPUTED embeddings; NOT end-to-end hybrid (encoder excluded)"}
    log(f"  H1 p95 {M['warm_e2e_retrieval_only']['H1_s']['p95']*1000:.0f}ms | "
        f"H3 p95 {M['warm_e2e_retrieval_only']['H3_s']['p95']*1000:.0f}ms")

    # ---- fallback probe ----
    log("fallback probe")
    logged = []
    svc_fb = RetrievalService(policy=RetrievalPolicy(mode=RetrievalMode.HYBRID_RRF20,
                                                     fallback_on_dense_failure=True),
                              docs=docs, bm25=bm25, logger=logged.append)
    resp = svc_fb.search(queries[0], top_k=3)
    M["fallback_probe"] = {"mode_used": resp.mode_used.value,
                           "fallback_reason": resp.fallback_reason,
                           "logged": any("fallback bm25" in m for m in logged),
                           "results_nonempty": bool(resp.results),
                           "pass": resp.mode_used is RetrievalMode.BM25 and resp.fallback_reason is not None}

    # ---- memory / disk ----
    M["memory_disk"] = {"peak_rss_mb": round(rss_mb(), 1),
                        "dense_disk_mb": round((DENSE_DIR/"corpus_emb.f16.npy").stat().st_size/2**20, 1),
                        "dense_loaded_f32_mb": round(dense.emb.nbytes/2**20, 1)}

    # ---- encoder blocker ----
    M["encoder"] = {
        "status": "BLOCKED",
        "reason": "bge-m3 not cached in ~/.cache/huggingface/hub; torch/sentence-transformers absent in system python and fpvenv; model download + large dependency install are out of scope for this task.",
        "end_to_end_hybrid_latency": "UNRESOLVED (encoder excluded from all latency numbers above)"}

    R["environment_note"] = "Standard_B4as_v2 (westus2), AMD EPYC 7763, 2 physical cores, 15.6 GiB RAM, no GPU; measured while OpenCode + uvicorn orchestrator + ollama were running."

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(R, indent=2), encoding="utf-8")
    log(f"wrote {OUT}")
    print(json.dumps({
        "reproduction_pass": M["frozen_benchmark"]["reproduction_pass"],
        "H3_p95_ms": round(M["warm_e2e_retrieval_only"]["H3_s"]["p95"]*1000, 1),
        "H1_p95_ms": round(M["warm_e2e_retrieval_only"]["H1_s"]["p95"]*1000, 1),
        "cold_start_s": M["cold_start"]["total_s"],
        "peak_rss_mb": M["memory_disk"]["peak_rss_mb"],
        "encoder": "BLOCKED"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

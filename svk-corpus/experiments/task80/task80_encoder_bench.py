#!/usr/bin/env python3
"""TASK 80 — BGE-M3 CPU encoder benchmark on the existing Azure VM.

Runs inside the isolated venv /home/azureuser/.venvs/task80-bge (torch CPU +
sentence-transformers). Downloads ONLY BAAI/bge-m3 rev 5617a9f; loads the
sha-verified Task-74 dense index without rebuilding; measures encoder latency
and (if headroom is adequate) end-to-end H3_RRF20 hybrid retrieval with the
REAL encoder, comparing against the Task-74/79 baseline.

Read-only w.r.t. frozen artifacts and the existing application. No training,
no fine-tuning, no Qwen serving.

Usage:
    /home/azureuser/.venvs/task80-bge/bin/python experiments/task80/task80_encoder_bench.py --stage smoke
    /home/azureuser/.venvs/task80-bge/bin/python experiments/task80/task80_encoder_bench.py --stage full
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import resource
import statistics
import sys
import threading
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

MODEL_ID = "BAAI/bge-m3"
MODEL_REV = "5617a9f61b028005a4858fdac845db406aefb181"  # from index_meta.json
OUT = ROOT / "data" / "reports" / "task80_encoder_bench.json"
TOP_K = 10
INF = 10 ** 9
RRF_K = 20


def log(m: str) -> None:
    print(f"[t80] {m}", flush=True)


def rss_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def pct(vals):
    if not vals:
        return {}
    s = sorted(vals)
    return {"n": len(s), "mean_ms": round(statistics.mean(s) * 1000, 2),
            "p50_ms": round(s[len(s) // 2] * 1000, 2),
            "p95_ms": round(s[int(0.95 * len(s))] * 1000, 2),
            "p99_ms": round(s[min(len(s) - 1, int(0.99 * len(s)))] * 1000, 2),
            "max_ms": round(max(s) * 1000, 2)}


class CpuSampler:
    """Sample process CPU% and (optionally) system load in a background thread."""

    def __init__(self, interval: float = 0.05):
        self.interval = interval
        self._stop = threading.Event()
        self._proc = []
        self._load = []
        self._t = threading.Thread(target=self._run, daemon=True)

    def _cpu_times(self):
        # self + children utime+stime
        def one(pid):
            try:
                with open(f"/proc/{pid}/stat") as f:
                    parts = f.read().split()
                return float(parts[13]) + float(parts[14])
            except Exception:
                return 0.0
        pids = [os.getpid()]
        try:
            pids += [int(p) for p in os.listdir("/proc") if p.isdigit()]
        except Exception:
            pass
        # limit to self tree for process CPU; also read loadavg for system
        self_t = one(os.getpid())
        with open("/proc/loadavg") as f:
            load1 = float(f.read().split()[0])
        return self_t, load1

    def _run(self):
        prev_t, prev_load = self._cpu_times()
        prev_wall = time.time()
        while not self._stop.wait(self.interval):
            t, load1 = self._cpu_times()
            wall = time.time() - prev_wall
            if wall > 0:
                # self CPU cores utilized (process only)
                self._proc.append((t - prev_t) / wall * 100.0)
                self._load.append(load1)
            prev_t, prev_wall, prev_load = t, time.time(), load1

    def start(self):
        self._t.start(); return self

    def stop(self):
        self._stop.set(); self._t.join(timeout=2)
        def st(v):
            if not v:
                return {}
            s = sorted(v)
            return {"mean_pct": round(statistics.mean(s), 1),
                    "p95_pct": round(s[int(0.95 * len(s))], 1),
                    "max_pct": round(max(s), 1)}
        return {"process_cpu_pct": st(self._proc), "system_load1": st(self._load)}


def pick_representative_queries(cases, per_lang=4):
    """Pick a small representative multilingual query subset (EN/Devanagari/GUJ)."""
    def lang(q):
        if any('\u0900' <= c <= '\u097F' for c in q):
            return "devanagari"
        if any('\u0A80' <= c <= '\u0AFF' for c in q):
            return "gujarati"
        return "latin"
    buckets = {}
    for c in cases:
        buckets.setdefault(lang(c["question"]), []).append(c)
    picked = []
    for k, v in buckets.items():
        picked.extend(v[:per_lang])
    return picked


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["smoke", "full"], default="smoke")
    ap.add_argument("--warmup", type=int, default=3)
    ap.add_argument("--iters", type=int, default=10)
    args = ap.parse_args()

    import torch
    from sentence_transformers import SentenceTransformer

    R = {"task": 80, "stage": args.stage,
         "environment": {"python": sys.version.split()[0], "torch": torch.__version__,
                         "torch_cuda_available": torch.cuda.is_available(),
                         "sentence_transformers": __import__("sentence_transformers").__version__,
                         "transformers": __import__("transformers").__version__,
                         "numpy": np.__version__,
                         "torch_num_threads": torch.get_num_threads(),
                         "torch_num_interop_threads": torch.get_num_interop_threads()}}
    M = {}
    R["measurements"] = M

    # keep thread count bounded to physical cores to protect the running app
    torch.set_num_threads(2)

    # ---- load frozen cases ----
    import task72.task72_experiment as t72
    cases = [json.loads(l) for l in Path(t72.CASES_PATH).read_text(encoding="utf-8").splitlines() if l.strip()]
    all_queries = [c["question"] for c in cases]
    rep = pick_representative_queries(cases, per_lang=4)
    rep_queries = [c["question"] for c in rep]
    M["query_set"] = {"total_frozen": len(all_queries),
                      "representative": len(rep_queries),
                      "representative_ids": [c["example_id"] for c in rep],
                      "languages_covered": sorted({("devanagari" if any('\u0900' <= ch <= '\u097F' for ch in q) else "gujarati" if any('\u0A80' <= ch <= '\u0AFF' for ch in q) else "latin") for q in rep_queries})}

    # ---- download + init (timed; first load caches model) ----
    log(f"loading {MODEL_ID} rev {MODEL_REV[:12]} (download on first load)...")
    cache_home = Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface"))
    hub_before = cache_home / "hub" / ("models--" + MODEL_ID.replace("/", "--"))
    existed_before = hub_before.exists()
    gc.collect()
    base_rss = rss_mb()
    sampler = CpuSampler().start()
    t0 = time.perf_counter()
    model = SentenceTransformer(MODEL_ID, revision=MODEL_REV, device="cpu")
    t_init = time.perf_counter() - t0
    cpu_stats_load = sampler.stop()
    peak_rss_load = rss_mb()
    # measure model disk footprint
    def dirsize(p):
        if not p.exists():
            return 0
        return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
    model_disk_mb = round(dirsize(hub_before) / 2 ** 20, 1)
    M["model_load"] = {
        "model_id": MODEL_ID, "model_revision": MODEL_REV,
        "was_cached_before": existed_before,
        "download_plus_init_s": round(t_init, 2),
        "cache_path": str(hub_before),
        "model_disk_mb": model_disk_mb,
        "rss_before_mb": round(base_rss, 1),
        "rss_after_load_mb": round(peak_rss_load, 1),
        "cpu_during_load": cpu_stats_load}
    log(f"  loaded in {t_init:.1f}s, model disk {model_disk_mb} MB, rss {peak_rss_load:.0f} MB")

    # ---- embedding validity on one query ----
    e = model.encode([rep_queries[0]], normalize_embeddings=True,
                     convert_to_numpy=True, show_progress_bar=False)
    emb = np.asarray(e, dtype=np.float32)
    M["embedding_validity"] = {
        "dim": int(emb.shape[1]),
        "dtype": str(emb.dtype),
        "l2_norm_first": round(float(np.linalg.norm(emb[0])), 6),
        "finite": bool(np.isfinite(emb).all()),
        "matches_index_dim_1024": bool(emb.shape[1] == 1024),
        "normalized_l2_1": bool(abs(float(np.linalg.norm(emb[0])) - 1.0) < 1e-3)}
    log(f"  dim={emb.shape[1]} l2={M['embedding_validity']['l2_norm_first']}")

    # ---- determinism (same query encoded twice) ----
    a = model.encode([rep_queries[0]], normalize_embeddings=True, convert_to_numpy=True)
    b = model.encode([rep_queries[0]], normalize_embeddings=True, convert_to_numpy=True)
    diff = float(np.max(np.abs(np.asarray(a) - np.asarray(b))))
    M["determinism"] = {"max_abs_diff_repeat": diff,
                        "within_1e4": bool(diff < 1e-4),
                        "note": "float32 CPU inference, deterministic ops"}

    # ---- first-query latency (cold model in memory) ----
    t0 = time.perf_counter()
    _ = model.encode([rep_queries[0]], normalize_embeddings=True, convert_to_numpy=True)
    M["first_query_s"] = round(time.perf_counter() - t0, 3)
    log(f"  first-query {M['first_query_s']}s")

    if args.stage == "smoke":
        # bounded: encode representative set a few times, report latency, exit
        log(f"smoke: warm-up {args.warmup}x over {len(rep_queries)} queries...")
        for _ in range(args.warmup):
            model.encode(rep_queries, normalize_embeddings=True, convert_to_numpy=True,
                         batch_size=8, show_progress_bar=False)
        log(f"smoke: measuring {args.iters}x over {len(rep_queries)} queries...")
        lat = []
        sampler = CpuSampler().start()
        for _ in range(args.iters):
            t0 = time.perf_counter()
            model.encode(rep_queries, normalize_embeddings=True, convert_to_numpy=True,
                         batch_size=8, show_progress_bar=False)
            # per-batch wall; divide by queries to get per-query proxy
            dt = (time.perf_counter() - t0) / len(rep_queries)
            lat.extend([dt] * len(rep_queries))
        M["encoder_warm_proxy"] = {"samples": len(lat), **pct(lat),
                                   "note": "batch wall / n_queries proxy; see --stage full for per-query",
                                   "cpu": sampler.stop()}
        M["peak_rss_mb"] = round(rss_mb(), 1)
        log(f"  encoder proxy p50 {M['encoder_warm_proxy']['p50_ms']}ms p95 {M['encoder_warm_proxy']['p95_ms']}ms")
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(R, indent=2), encoding="utf-8")
        log(f"wrote {OUT}")
        print(json.dumps({"stage": "smoke", "dim": emb.shape[1],
                          "l2": M["embedding_validity"]["l2_norm_first"],
                          "first_query_s": M["first_query_s"],
                          "proxy_p95_ms": M["encoder_warm_proxy"]["p95_ms"],
                          "peak_rss_mb": M["peak_rss_mb"]}, indent=1))
        return 0

    # ---- FULL: per-query latency over representative set + all 47 ----
    log(f"full: warm-up {args.warmup} over representative set...")
    for _ in range(args.warmup):
        model.encode(rep_queries, normalize_embeddings=True, convert_to_numpy=True,
                     batch_size=8, show_progress_bar=False)
    # per-query latency: encode one at a time to isolate per-query cost
    log(f"full: per-query latency, {args.iters} iters x {len(rep_queries)} rep queries...")
    lat_rep = []
    sampler = CpuSampler().start()
    for _ in range(args.iters):
        for q in rep_queries:
            t0 = time.perf_counter()
            model.encode([q], normalize_embeddings=True, convert_to_numpy=True)
            lat_rep.append(time.perf_counter() - t0)
    M["encoder_warm_per_query_rep"] = {"samples": len(lat_rep), **pct(lat_rep),
                                       "queries": len(rep_queries), "iters": args.iters,
                                       "cpu": sampler.stop()}
    log(f"  per-query rep p50 {M['encoder_warm_per_query_rep']['p50_ms']}ms "
        f"p95 {M['encoder_warm_per_query_rep']['p95_ms']}ms")

    # all 47 frozen queries, 3 iters (141 samples) — per-query
    log("full: per-query latency over all 47 frozen queries (3 iters)...")
    lat_all = []
    for _ in range(3):
        for q in all_queries:
            t0 = time.perf_counter()
            model.encode([q], normalize_embeddings=True, convert_to_numpy=True)
            lat_all.append(time.perf_counter() - t0)
    M["encoder_warm_per_query_all47"] = {"samples": len(lat_all), **pct(lat_all)}
    log(f"  per-query all47 p50 {M['encoder_warm_per_query_all47']['p50_ms']}ms "
        f"p95 {M['encoder_warm_per_query_all47']['p95_ms']}ms "
        f"p99 {M['encoder_warm_per_query_all47']['p99_ms']}ms")

    M["peak_rss_mb"] = round(rss_mb(), 1)

    # ---- end-to-end retrieval with REAL encoder ----
    log("end-to-end: load verified dense index, encode + search + fuse...")
    from svk_corpus.retrieval import BM25Index, load_corpus
    from svk_corpus.retrieval.service import (RetrievalMode, RetrievalPolicy,
                                              RetrievalService, load_dense_index,
                                              rrf_fuse_full)
    from task76.task76_benchmark import DENSE_DIR, case_ranks_from_results

    # verify dense index sha unchanged
    emb_sha = hashlib.sha256((DENSE_DIR / "corpus_emb.f16.npy").read_bytes()).hexdigest()
    meta = json.loads((DENSE_DIR / "index_meta.json").read_text())
    assert emb_sha == meta["corpus_emb_f16_sha256"], "dense index sha CHANGED - abort"
    assert meta["model_revision"] == MODEL_REV, "model revision mismatch - abort"
    assert meta["embedding_dim"] == emb.shape[1] == 1024, "dim mismatch - abort"
    log("  dense index sha + model rev + dim verified; no rebuild")

    gc.collect()
    t0 = time.perf_counter(); docs = load_corpus(t72.CORPUS_PATH, t72.MANIFEST_PATH); t_corpus = time.perf_counter() - t0
    t0 = time.perf_counter(); bm25 = BM25Index(docs, k1=1.5, b=0.75); t_bm25 = time.perf_counter() - t0
    t0 = time.perf_counter(); dense = load_dense_index(DENSE_DIR, docs, verify_file_sha=True, verify_alignment=False); t_dense = time.perf_counter() - t0
    M["e2e_cold_start_s"] = {"corpus": round(t_corpus, 2), "bm25": round(t_bm25, 2),
                             "dense": round(t_dense, 2),
                             "total_without_encoder_load": round(t_corpus + t_bm25 + t_dense, 2),
                             "note": "encoder already loaded above; not re-timed here"}

    # wire the real encoder into the service (wrap str -> 1D vec, matching Callable[[str], Any])
    def _encode_query(q: str) -> np.ndarray:
        return model.encode([q], normalize_embeddings=True,
                            convert_to_numpy=True)[0].astype(np.float32)

    svc_h3 = RetrievalService(policy=RetrievalPolicy(mode=RetrievalMode.HYBRID_RRF20),
                              docs=docs, bm25=bm25, dense=dense, query_encoder=_encode_query)

    # per-component timing on representative queries
    comp = {"encode_s": [], "dense_s": [], "fusion_s": [], "bm25_s": [], "total_s": []}
    log(f"e2e: component timing over {len(rep_queries)} rep queries (5 iters)...")
    for _ in range(5):
        for q in rep_queries:
            t_all = time.perf_counter()
            t0 = time.perf_counter()
            qe = model.encode([q], normalize_embeddings=True, convert_to_numpy=True)[0].astype(np.float32)
            t_enc = time.perf_counter() - t0
            t0 = time.perf_counter()
            full = bm25.search(q, top_k=INF)
            rank = {r.doc.text_id: r.rank for r in full}
            t_bm = time.perf_counter() - t0
            t0 = time.perf_counter()
            scores = dense.emb @ qe
            order = np.argsort(-scores, kind="stable")
            rank_of = np.empty(dense.n, dtype=np.int64); rank_of[order] = np.arange(1, dense.n + 1)
            t_dense_s = time.perf_counter() - t0
            t0 = time.perf_counter()
            rrf_fuse_full(rank, rank_of, RRF_K, dense.tid2idx, dense.n)
            t_fuse = time.perf_counter() - t0
            comp["encode_s"].append(t_enc); comp["bm25_s"].append(t_bm)
            comp["dense_s"].append(t_dense_s); comp["fusion_s"].append(t_fuse)
            comp["total_s"].append(time.perf_counter() - t_all)
    M["e2e_components_rep"] = {k: pct(v) for k, v in comp.items()}
    log(f"  e2e encode p50 {M['e2e_components_rep']['encode_s']['p50_ms']}ms total p50 {M['e2e_components_rep']['total_s']['p50_ms']}ms")

    # service-level e2e (real encoder) over all 47, 3 iters
    log("e2e: service-level H3_RRF20 over all 47 frozen queries (3 iters, real encoder)...")
    svc_lat = []
    for _ in range(3):
        for q in all_queries:
            t0 = time.perf_counter()
            svc_h3.search(q, top_k=TOP_K)
            svc_lat.append(time.perf_counter() - t0)
    M["e2e_h3_service_all47"] = {"samples": len(svc_lat), **pct(svc_lat),
                                 "note": "REAL encoder + dense + fusion + contract; end-to-end"}
    log(f"  service e2e p50 {M['e2e_h3_service_all47']['p50_ms']}ms "
        f"p95 {M['e2e_h3_service_all47']['p95_ms']}ms p99 {M['e2e_h3_service_all47']['p99_ms']}ms")

    # frozen benchmark reproduction (real encoder, single pass)
    log("frozen benchmark reproduction (real encoder, H1 + H3, single pass)...")
    from svk_corpus.retrieval.service import RetrievalMode as RM

    def recall(vals, k):
        return t72.recall(vals, k)

    def mrr(vals):
        return t72.mrr(vals)

    def run_mode(mode, dense_state):
        svc = RetrievalService(policy=RetrievalPolicy(mode=mode), docs=docs, bm25=bm25,
                               dense=dense_state, query_encoder=_encode_query)
        per = []
        for c in cases:
            resp = svc.search(c["question"], top_k=TOP_K)
            first, uhit = case_ranks_from_results(resp.results, c)
            per.append({"src": first, "unit": uhit,
                        "exp_src": bool((c.get("provenance") or {}).get("source_id")),
                        "exp_unit": bool((c.get("provenance") or {}).get("unit_ids")),
                        "fallback": resp.fallback_reason})
        src = [p["src"] for p in per if p["exp_src"]]
        unit = [p["unit"] for p in per if p["exp_unit"]]
        return {"agg": {"src@5": recall(src, 5), "unit@5": recall(unit, 5),
                        "src_mrr": mrr(src), "unit_mrr": mrr(unit),
                        "n_src": len(src), "n_unit": len(unit)},
                "fallbacks": sum(1 for p in per if p["fallback"])}

    h1 = run_mode(RM.BM25, None)
    h3 = run_mode(RM.HYBRID_RRF20, dense)
    M["frozen_benchmark_real_encoder"] = {
        "H1_BM25": h1, "H3_RRF20": h3,
        "expected_H3": {"unit@5": 0.5385, "src@5": 0.9783},
        "reproduction_pass": (
            abs(h3["agg"]["unit@5"] - 0.5385) < 2e-3 and abs(h3["agg"]["src@5"] - 0.9783) < 2e-3),
        "note": "real encoder; tolerance 2e-3 to allow CPU/GPU float differences"}
    log(f"  H3 unit@5={h3['agg']['unit@5']} src@5={h3['agg']['src@5']} "
        f"pass={M['frozen_benchmark_real_encoder']['reproduction_pass']}")

    M["peak_rss_mb"] = round(rss_mb(), 1)
    R["environment_note"] = "Standard_B4as_v2 (westus2), AMD EPYC 7763, 2 physical cores, 15.6 GiB RAM, no GPU; measured while OpenCode + uvicorn orchestrator + ollama were running; torch threads bounded to 2."

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(R, indent=2), encoding="utf-8")
    log(f"wrote {OUT}")
    print(json.dumps({
        "stage": "full",
        "dim": emb.shape[1],
        "encoder_per_query_all47_p95_ms": M["encoder_warm_per_query_all47"]["p95_ms"],
        "encoder_per_query_all47_p99_ms": M["encoder_warm_per_query_all47"]["p99_ms"],
        "e2e_h3_service_p95_ms": M["e2e_h3_service_all47"]["p95_ms"],
        "e2e_h3_service_p99_ms": M["e2e_h3_service_all47"]["p99_ms"],
        "frozen_repro_pass": M["frozen_benchmark_real_encoder"]["reproduction_pass"],
        "H3_unit5": h3["agg"]["unit@5"], "H3_src5": h3["agg"]["src@5"],
        "peak_rss_mb": M["peak_rss_mb"]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

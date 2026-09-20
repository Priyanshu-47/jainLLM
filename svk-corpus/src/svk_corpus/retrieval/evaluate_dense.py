"""Dense retrieval benchmark (Task 16).

Compares three retrieval modes on the same 20-query labelled set:
  1. Dense-only (SentenceTransformerDense)
  2. BM25+source baseline C (regression — must match Task 13)
  3. Hybrid BM25+dense RRF (Reciprocal Rank Fusion)

Usage:
    python -m svk_corpus.retrieval.evaluate_dense
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from svk_corpus.retrieval import (BM25Index, HybridRetriever, SentenceTransformerDense,
                                  UnavailableDense, load_corpus, RetrievalResult)
from svk_corpus.retrieval.fusion import reciprocal_rank_fusion
from svk_corpus.retrieval.rerank import Reranker
from svk_corpus.retrieval.source_channel import (SourceIndex, SourceUnitExpander,
                                                  build_source_index)
from svk_corpus.retrieval.contract import CanonicalResult, RetrievalChannel, validate_result


def _load_queries(config_root: Path) -> dict[str, Any]:
    path = config_root / "configs" / "retrieval_eval_queries_v1.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _build_dense_index(docs, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
                       batch_size: int = 64) -> SentenceTransformerDense:
    """Build the dense index from corpus documents."""
    print(f"Building dense index with {model_name} over {len(docs)} units...")
    t0 = time.perf_counter()
    dense = SentenceTransformerDense(docs, model_name=model_name, batch_size=batch_size)
    t1 = time.perf_counter()
    stats = dense.stats()
    print(f"  Dense index built in {t1 - t0:.1f}s "
          f"({stats['n_vectors']} vectors, dim={stats['dim']})")
    return dense


def _compute_metrics(queries, hit_sources_per_q, top_k=10):
    """Compute R@5, R@10, MRR, zero-relevant for source-level queries."""
    recalls5, recalls10, rr = [], [], []
    zero = 0
    for q, hits in zip(queries, hit_sources_per_q):
        if q.get("relevance") != "source-level":
            continue
        expected = set(q.get("expected_source_ids") or [])
        if not expected:
            continue
        f5 = len(expected & set(hits[:5])) / len(expected)
        f10 = len(expected & set(hits[:top_k])) / len(expected)
        first = next((i for i, s in enumerate(hits, 1) if s in expected), None)
        recalls5.append(f5)
        recalls10.append(f10)
        rr.append(1.0 / first if first else 0.0)
        if not (expected & set(hits)):
            zero += 1
    return {
        "recall@5": round(sum(recalls5) / len(recalls5), 3) if recalls5 else None,
        "recall@10": round(sum(recalls10) / len(recalls10), 3) if recalls10 else None,
        "mrr": round(sum(rr) / len(rr), 3) if rr else None,
        "queries_with_zero_relevant": zero,
        "n_source_level": len(recalls5),
    }


def _per_query_detail(queries, hit_sources_per_q, top_k=10):
    """Per-query breakdown for the report."""
    details = []
    for q, hits in zip(queries, hit_sources_per_q):
        entry = {"id": q["id"], "category": q.get("category", ""),
                 "relevance": q.get("relevance", ""),
                 "query": q["query"][:80]}
        if q.get("relevance") == "source-level":
            expected = set(q.get("expected_source_ids") or [])
            entry["expected"] = sorted(expected)
            entry["found_in_top5"] = sorted(expected & set(hits[:5]))
            entry["found_in_top10"] = sorted(expected & set(hits[:top_k]))
            entry["missed"] = sorted(expected - set(hits[:top_k]))
            entry["top_sources"] = hits[:top_k]
        else:
            entry["top_sources"] = hits[:5]
        details.append(entry)
    return details


def evaluate_dense_only(docs, dense, queries, top_k=10):
    """Evaluate dense retrieval alone."""
    print("Evaluating dense-only...")
    hit_sources_per_q = []
    latencies = []
    for q in queries:
        t0 = time.perf_counter()
        results = dense.search(q["query"], top_k=top_k)
        dt = time.perf_counter() - t0
        latencies.append(dt)
        hit_sources_per_q.append([r.source_id for r, _ in results])
    metrics = _compute_metrics(queries, hit_sources_per_q, top_k)
    metrics["mean_latency_s"] = round(sum(latencies) / len(latencies), 4)
    metrics["max_latency_s"] = round(max(latencies), 4) if latencies else None
    return metrics, hit_sources_per_q


def evaluate_bm25_source_baseline(docs, bm25, queries, top_k=10):
    """Evaluate BM25+source combined C (regression check against Task 13)."""
    print("Evaluating BM25+source baseline (C)...")
    sidx = build_source_index(Path(__file__).resolve().parents[3] / "manifests" / "source_manifest.csv")
    expander = SourceUnitExpander(docs)
    diversify = Reranker(strategy="diversify", max_per_source=3)
    hit_sources_per_q = []
    latencies = []
    for q in queries:
        t0 = time.perf_counter()
        pool = bm25.search(q["query"], top_k=2000)
        unit_tier = diversify.rerank([RetrievalResult(doc=h.doc, score=h.score,
                                                       rank=h.rank, methods={"bm25": h.rank})
                                       for h in pool])[:top_k]
        smatches = sidx.search(q["query"], top_k=top_k)
        missing = [m for m in smatches
                   if m.source_id not in {r.doc.source_id for r in unit_tier}
                   and not m.identifier_only]
        n_fill = min(3, len(missing))
        fill = expander.expand(missing[:n_fill], top_k=n_fill)
        keep = max(top_k - len(fill), 0)
        combined = (list(unit_tier[:keep]) + fill)[:top_k]
        dt = time.perf_counter() - t0
        latencies.append(dt)
        hit_sources_per_q.append([r.doc.source_id for r in combined])
    metrics = _compute_metrics(queries, hit_sources_per_q, top_k)
    metrics["mean_latency_s"] = round(sum(latencies) / len(latencies), 4)
    metrics["max_latency_s"] = round(max(latencies), 4) if latencies else None
    return metrics, hit_sources_per_q


def evaluate_hybrid_rrf(docs, bm25, dense, queries, top_k=10, rrf_k=60):
    """Evaluate BM25+dense via Reciprocal Rank Fusion."""
    print("Evaluating hybrid RRF (BM25+dense)...")
    hit_sources_per_q = []
    latencies = []
    for q in queries:
        t0 = time.perf_counter()
        # BM25 results
        bm25_results = bm25.search(q["query"], top_k=top_k * 3)
        bm25_ranks = {r.doc.text_id: i + 1 for i, r in enumerate(bm25_results)}
        bm25_scores = {r.doc.text_id: r.score for r in bm25_results}

        # Dense results
        dense_results = dense.search(q["query"], top_k=top_k * 3)
        dense_ranks = {}
        for rank, (doc, score) in enumerate(dense_results, 1):
            dense_ranks[doc.text_id] = rank

        # RRF fusion
        all_ids = set(bm25_ranks.keys()) | set(dense_ranks.keys())
        fused = []
        for tid in all_ids:
            r1 = bm25_ranks.get(tid, top_k * 3 + 1)
            r2 = dense_ranks.get(tid, top_k * 3 + 1)
            rrf_score = 1.0 / (rrf_k + r1) + 1.0 / (rrf_k + r2)
            # Find the document object
            doc = None
            for r in bm25_results:
                if r.doc.text_id == tid:
                    doc = r.doc
                    break
            if doc is None:
                for d, _ in dense_results:
                    if d.text_id == tid:
                        doc = d
                        break
            if doc is not None:
                fused.append((rrf_score, doc))
        fused.sort(key=lambda t: (-t[0], t[1].text_id))
        dt = time.perf_counter() - t0
        latencies.append(dt)
        hit_sources_per_q.append([doc.source_id for _, doc in fused[:top_k]])
    metrics = _compute_metrics(queries, hit_sources_per_q, top_k)
    metrics["mean_latency_s"] = round(sum(latencies) / len(latencies), 4)
    metrics["max_latency_s"] = round(max(latencies), 4) if latencies else None
    return metrics, hit_sources_per_q


def main() -> int:
    root = Path(__file__).resolve().parents[3]
    rag = root / "data" / "release" / "rag_corpus.jsonl"
    manifest = root / "manifests" / "source_manifest.csv"

    print("=" * 70)
    print("Task 16: Dense Retrieval Benchmark")
    print("=" * 70)

    # Load corpus
    t0 = time.perf_counter()
    docs = load_corpus(rag, manifest)
    t_load = time.perf_counter() - t0
    print(f"Corpus loaded: {len(docs)} units in {t_load:.1f}s")

    # Load queries
    queries = _load_queries(root)["queries"]
    print(f"Evaluation queries: {len(queries)}")

    # Build BM25 index
    t0 = time.perf_counter()
    bm25 = BM25Index(docs)
    t_bm25 = time.perf_counter() - t0
    print(f"BM25 index built in {t_bm25:.1f}s")

    # Build dense index (MiniLM for CPU feasibility; bge-m3 for production/GPU)
    dense = _build_dense_index(docs, model_name="paraphrase-multilingual-MiniLM-L12-v2", batch_size=128)
    dense_stats = dense.stats()

    # Run evaluations
    print()
    dense_metrics, dense_hits = evaluate_dense_only(docs, dense, queries)
    print(f"  Dense-only: R@5={dense_metrics['recall@5']}  "
          f"R@10={dense_metrics['recall@10']}  MRR={dense_metrics['mrr']}  "
          f"zero={dense_metrics['queries_with_zero_relevant']}  "
          f"lat={dense_metrics['mean_latency_s']}s")

    bm25_metrics, bm25_hits = evaluate_bm25_source_baseline(docs, bm25, queries)
    print(f"  BM25+src C: R@5={bm25_metrics['recall@5']}  "
          f"R@10={bm25_metrics['recall@10']}  MRR={bm25_metrics['mrr']}  "
          f"zero={bm25_metrics['queries_with_zero_relevant']}  "
          f"lat={bm25_metrics['mean_latency_s']}s")

    hybrid_metrics, hybrid_hits = evaluate_hybrid_rrf(docs, bm25, dense, queries)
    print(f"  Hybrid RRF: R@5={hybrid_metrics['recall@5']}  "
          f"R@10={hybrid_metrics['recall@10']}  MRR={hybrid_metrics['mrr']}  "
          f"zero={hybrid_metrics['queries_with_zero_relevant']}  "
          f"lat={hybrid_metrics['mean_latency_s']}s")

    # Compute deltas
    print()
    print("Delta (hybrid vs BM25 baseline):")
    if bm25_metrics["recall@5"] and hybrid_metrics["recall@5"]:
        print(f"  R@5:  {hybrid_metrics['recall@5'] - bm25_metrics['recall@5']:+.3f}")
    if bm25_metrics["recall@10"] and hybrid_metrics["recall@10"]:
        print(f"  R@10: {hybrid_metrics['recall@10'] - bm25_metrics['recall@10']:+.3f}")
    if bm25_metrics["mrr"] and hybrid_metrics["mrr"]:
        print(f"  MRR:  {hybrid_metrics['mrr'] - bm25_metrics['mrr']:+.3f}")

    # Per-query comparison
    print()
    print("Per-query source-level comparison:")
    print(f"{'Query':<6} {'BM25 R@5':>9} {'Dense R@5':>10} {'Hybrid R@5':>11} "
          f"{'BM25 R@10':>10} {'Dense R@10':>11} {'Hybrid R@10':>12}")
    print("-" * 80)
    for q, bm25_h, dense_h, hybrid_h in zip(queries, bm25_hits, dense_hits, hybrid_hits):
        if q.get("relevance") != "source-level":
            continue
        expected = set(q.get("expected_source_ids") or [])
        if not expected:
            continue
        b5 = len(expected & set(bm25_h[:5])) / len(expected)
        d5 = len(expected & set(dense_h[:5])) / len(expected)
        h5 = len(expected & set(hybrid_h[:5])) / len(expected)
        b10 = len(expected & set(bm25_h[:10])) / len(expected)
        d10 = len(expected & set(dense_h[:10])) / len(expected)
        h10 = len(expected & set(hybrid_h[:10])) / len(expected)
        print(f"{q['id']:<6} {b5:>9.3f} {d5:>10.3f} {h5:>11.3f} "
              f"{b10:>10.3f} {d10:>11.3f} {h10:>12.3f}")

    # Write full report
    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "label": "task16_dense_retrieval_benchmark",
        "corpus_units": len(docs),
        "n_queries": len(queries),
        "model": dense_stats["model"],
        "embedding_dim": dense_stats["dim"],
        "index_build_time_s": dense_stats["build_time_s"],
        "dense_encode_time_s": dense_stats["encode_time_s"],
        "bm25_index_build_s": round(t_bm25, 2),
        "corpus_load_s": round(t_load, 2),
        "modes": {
            "dense_only": {
                "metrics": dense_metrics,
                "per_query": _per_query_detail(queries, dense_hits),
            },
            "bm25_source_baseline": {
                "metrics": bm25_metrics,
                "per_query": _per_query_detail(queries, bm25_hits),
            },
            "hybrid_rrf": {
                "metrics": hybrid_metrics,
                "per_query": _per_query_detail(queries, hybrid_hits),
            },
        },
        "delta_hybrid_vs_baseline": {
            "recall@5": round(hybrid_metrics["recall@5"] - bm25_metrics["recall@5"], 3)
                        if hybrid_metrics["recall@5"] and bm25_metrics["recall@5"] else None,
            "recall@10": round(hybrid_metrics["recall@10"] - bm25_metrics["recall@10"], 3)
                         if hybrid_metrics["recall@10"] and bm25_metrics["recall@10"] else None,
            "mrr": round(hybrid_metrics["mrr"] - bm25_metrics["mrr"], 3)
                   if hybrid_metrics["mrr"] and bm25_metrics["mrr"] else None,
        },
    }

    out = root / "data" / "reports" / "task16_dense_retrieval_benchmark.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

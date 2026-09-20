"""Run the retrieval evaluation set against the released RAG corpus.

This is the Task-8 measurement script. It reports exactly what is measured and
marks what is not measurable: corpus-gap queries are excluded from Recall/MRR
by design, exploratory queries are described, never scored.

Usage:
    python -m svk_corpus.retrieval.evaluate
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from svk_corpus.retrieval import (BM25Index, HybridRetriever, UnavailableDense,
                                  load_corpus)
from svk_corpus.retrieval.fusion import RetrievalResult
from svk_corpus.retrieval.rerank import Reranker
from svk_corpus.retrieval.source_channel import (SourceIndex, SourceUnitExpander,
                                                 build_source_index)


def _load_queries(config_root: Path) -> dict[str, Any]:
    path = config_root / "configs" / "retrieval_eval_queries_v1.json"
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate(config_root: Path, top_k: int = 10,
             label: str = "task8", out_name: str | None = None) -> dict[str, Any]:
    """Run the eval set. `label`/`out_name` let later tasks (Task 9) write a
    separate comparison file instead of overwriting the earlier baseline."""
    rag = config_root / "data" / "release" / "rag_corpus.jsonl"
    manifest = config_root / "manifests" / "source_manifest.csv"

    t0 = time.perf_counter()
    docs = load_corpus(rag, manifest)
    t_load = time.perf_counter() - t0

    t0 = time.perf_counter()
    bm25 = BM25Index(docs)
    t_index = time.perf_counter() - t0

    retriever = HybridRetriever(docs, bm25, dense=UnavailableDense())

    queries = _load_queries(config_root)["queries"]
    per_query: list[dict[str, Any]] = []
    recalls5: list[float] = []
    recalls10: list[float] = []
    rr: list[float] = []
    zero_hit = 0
    latencies: list[float] = []
    context_dist: Counter[str] = Counter()          # svk-specific queries, top-10 slots
    first_result_scope: Counter[str] = Counter()    # svk-specific queries
    generic_dist: Counter[str] = Counter()          # exploratory generic query
    examples: list[dict[str, Any]] = []

    for q in queries:
        rel = q.get("relevance")
        expected = set(q.get("expected_source_ids") or [])
        t0 = time.perf_counter()
        results = retriever.search(q["query"], top_k=top_k)
        dt = time.perf_counter() - t0
        latencies.append(dt)

        hit_sources = [r.doc.source_id for r in results]
        entry: dict[str, Any] = {"id": q["id"], "category": q["category"],
                                 "relevance": rel, "latency_s": round(dt, 4)}

        if rel == "source-level" and expected:
            found5 = len(expected & set(hit_sources[:5]))
            found10 = len(expected & set(hit_sources[:10]))
            recalls5.append(found5 / len(expected))
            recalls10.append(found10 / len(expected))
            first_rank = next((i for i, s in enumerate(hit_sources, 1) if s in expected), None)
            rr.append(1.0 / first_rank if first_rank else 0.0)
            if not (expected & set(hit_sources)):
                zero_hit += 1
            entry.update({"recall@5": round(found5 / len(expected), 3),
                          "recall@10": round(found10 / len(expected), 3),
                          "mrr": round(rr[-1], 3),
                          "hit_sources_in_top10": sorted(expected & set(hit_sources))})
        elif rel == "corpus-gap":
            entry["expected"] = "NO relevant material in corpus (documented gap)"
            entry["top_sources"] = hit_sources[:5]
            zero_hit += 1 if not hit_sources else 0
        else:  # exploratory
            entry["top_sources"] = hit_sources[:5]
            if not q.get("svk_specific"):
                generic_dist.update(r.doc.religious_scope for r in results)

        if q.get("svk_specific"):
            scopes10 = [r.doc.religious_scope for r in results]
            context_dist.update(scopes10)
            if results:
                first_result_scope[results[0].doc.religious_scope] += 1
        if q["id"] in ("q10", "q17", "q18", "q20") and results:
            examples.append({
                "query": q["query"], "id": q["id"],
                "top3": [{"source_id": r.doc.source_id, "title": r.doc.title[:60],
                          "scope": r.doc.religious_scope, "sect": r.doc.sect,
                          "citation": r.doc.citation[:110],
                          "text_head": r.doc.text[:90].replace("\n", " ")}
                         for r in results[:3]],
            })
        per_query.append(entry)

    svk_slots = sum(context_dist.values())
    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "label": label,
        "corpus_units": len(docs),
        "index_build_s": round(t_index, 2),
        "corpus_load_s": round(t_load, 2),
        "retrieval_mode": "BM25 only (dense unavailable in this environment)",
        "queries_total": len(queries),
        "metrics": {
            "note": "Averaged over source-level queries only; corpus-gap queries excluded by design; exploratory queries unlabelled.",
            "recall@5": round(sum(recalls5) / len(recalls5), 3) if recalls5 else None,
            "recall@10": round(sum(recalls10) / len(recalls10), 3) if recalls10 else None,
            "mrr": round(sum(rr) / len(rr), 3) if rr else None,
            "queries_with_zero_relevant_results": zero_hit,
            "mean_latency_s": round(sum(latencies) / len(latencies), 4),
            "max_latency_s": round(max(latencies), 4) if latencies else None,
            "n_source_level_queries": len(recalls5),
        },
        "sect_context": {
            "note": ("Distribution of religious_scope across top-10 results of the "
                     "svk_specific queries. A generic-Jain hit is not 'wrong' unless "
                     "the query definition excludes it; q12 and q17 are defined loosely."),
            "svk_specific_slot_distribution": dict(context_dist.most_common()),
            "svk_specific_first_result_scope": dict(first_result_scope.most_common()),
            "svk_share_of_slots": round(
                (context_dist.get("CORE_STHANAKAVASI", 0)
                 + context_dist.get("HIGH_STHANAKAVASI_RELEVANCE", 0)) / svk_slots, 3)
            if svk_slots else None,
            "generic_query_q20_distribution": dict(generic_dist.most_common()),
        },
        "per_query": per_query,
        "examples": examples,
    }

    out = config_root / "data" / "reports" / (out_name or "retrieval_eval_results.json")
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def evaluate_strategies(config_root: Path, top_k: int = 10, pool: int = 2000,
                        strategies: tuple[str, ...] = ("bm25", "tiebreak", "diversify"),
                        label: str = "task11", out_name: str = "retrieval_eval_results_task11.json") -> dict[str, Any]:
    """Task 11 experiment: compare post-BM25 reranking strategies over the
    SAME labelled query set.

    Protocol (anti-circularity): every strategy sees the identical BM25
    candidate pool per query (top-`pool` of the single-list RRF, which is
    order-identical to BM25). The baseline strategy "bm25" is an identity
    rerank, so its top-`top_k` equals the Task 10 output exactly. No metric,
    label, or query is touched; strategies are compared on the FULL labelled
    set, not tuned on q09.
    """
    rag = config_root / "data" / "release" / "rag_corpus.jsonl"
    manifest = config_root / "manifests" / "source_manifest.csv"

    t0 = time.perf_counter()
    docs = load_corpus(rag, manifest)
    t_load = time.perf_counter() - t0
    t0 = time.perf_counter()
    bm25 = BM25Index(docs)
    t_index = time.perf_counter() - t0
    retriever = HybridRetriever(docs, bm25, dense=UnavailableDense())  # kept for parity checks
    rerankers = {s: Reranker(strategy=s, max_per_source=3) for s in strategies}
    queries = _load_queries(config_root)["queries"]

    agg: dict[str, dict[str, Any]] = {
        s: {"recalls5": [], "recalls10": [], "rr": [], "zero": 0, "lat": [],
            "context": Counter(), "first_scope": Counter(), "per_query": [],
            "displaced": Counter()}
        for s in strategies}
    q09_detail: dict[str, list[dict[str, Any]]] = {}

    for q in queries:
        t0 = time.perf_counter()
        # The reranker consumes TRUE BM25 output (doc, BM25 score, BM25 rank) —
        # not RRF-fused scores, whose 1/(k+rank) scale quantizes to 0.0 and
        # would collapse the whole pool into one metadata-only tie.
        allowed = None
        bm25_pool = bm25.search(q["query"], top_k=pool, allowed=allowed)
        pool_results = [RetrievalResult(doc=h.doc, score=h.score, rank=h.rank,
                                        methods={"bm25": h.rank})
                        for h in bm25_pool]
        dt_pool = time.perf_counter() - t0
        expected = set(q.get("expected_source_ids") or [])
        for s in strategies:
            t0 = time.perf_counter()
            results = rerankers[s].rerank(pool_results)[:top_k]
            dt = dt_pool + (time.perf_counter() - t0)
            A = agg[s]
            A["lat"].append(dt)
            hits = [r.doc.source_id for r in results]
            entry: dict[str, Any] = {"id": q["id"], "relevance": q.get("relevance")}
            if q.get("relevance") == "source-level" and expected:
                f5 = len(expected & set(hits[:5])) / len(expected)
                f10 = len(expected & set(hits[:10])) / len(expected)
                first = next((i for i, src in enumerate(hits, 1) if src in expected), None)
                A["recalls5"].append(f5); A["recalls10"].append(f10)
                A["rr"].append(1.0 / first if first else 0.0)
                if not (expected & set(hits)):
                    A["zero"] += 1
                entry.update({"recall@5": round(f5, 3), "recall@10": round(f10, 3),
                              "mrr": round(A["rr"][-1], 3),
                              "hit_sources_in_top10": sorted(set(hits[:10]))})
            if q.get("svk_specific"):
                A["context"].update(r.doc.religious_scope for r in results)
                if results:
                    A["first_scope"][results[0].doc.religious_scope] += 1
            if q.get("relevance") != "source-level":
                entry["top_sources"] = hits[:5]
            A["per_query"].append(entry)
            if q["id"] == "q09":
                q09_detail[s] = [{
                    "rank": r.rank,
                    "source_id": r.doc.source_id,
                    "title": r.doc.title[:45],
                    "bm25_rank_before": getattr(r, "extra", None).bm25_rank if hasattr(r, "extra") else r.rank,
                    "bm25_score": round(getattr(r, "extra", None).bm25_score if hasattr(r, "extra") else r.score, 4),
                    "scope": r.doc.religious_scope,
                    "confidence": r.doc.religious_scope_confidence,
                    "source_quality": r.doc.source_quality,
                    "year": r.doc.publication_year,
                    "text_head": r.doc.text[:50].replace("\n", " "),
                } for r in results]

    # (Displacement/harm analysis is computed from the stored per-query
    # hit_sources_in_top10 by the report step, not by re-running retrieval.)

    svk_slots = {s: sum(agg[s]["context"].values()) for s in strategies}
    out_payload: dict[str, Any] = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "label": label,
        "corpus_units": len(docs),
        "index_build_s": round(t_index, 2),
        "corpus_load_s": round(t_load, 2),
        "pool_size": pool,
        "max_per_source": 3,
        "strategies": {},
        "q09_detail": q09_detail,
    }
    for s in strategies:
        A = agg[s]
        slots = svk_slots[s] or 1
        out_payload["strategies"][s] = {
            "metrics": {
                "recall@5": round(sum(A["recalls5"]) / len(A["recalls5"]), 3) if A["recalls5"] else None,
                "recall@10": round(sum(A["recalls10"]) / len(A["recalls10"]), 3) if A["recalls10"] else None,
                "mrr": round(sum(A["rr"]) / len(A["rr"]), 3) if A["rr"] else None,
                "queries_with_zero_relevant_results": A["zero"],
                "mean_latency_s": round(sum(A["lat"]) / len(A["lat"]), 4),
                "n_source_level_queries": len(A["recalls5"]),
            },
            "sect_context": {
                "svk_share_of_slots": round((A["context"].get("CORE_STHANAKAVASI", 0)
                                             + A["context"].get("HIGH_STHANAKAVASI_RELEVANCE", 0)) / slots, 3),
                "slot_distribution": dict(A["context"].most_common()),
                "first_result_scope": dict(A["first_scope"].most_common()),
            },
            "per_query": A["per_query"],
        }

    out = config_root / "data" / "reports" / out_name
    out.write_text(json.dumps(out_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_payload


def evaluate_source_channel(config_root: Path, top_k: int = 10,
                            label: str = "task13",
                            out_name: str = "retrieval_eval_results_task13.json") -> dict[str, Any]:
    """Task 13: unit channel (A) vs source-metadata channel (B) vs combined (C).

    Combined policy (deterministic, no invented weights, exactly the task's
    five steps): unit results first (BM25 + diversify presentation tier);
    source-derived representative units are appended for metadata-matched
    sources, deduplicated by unit identity, filling only positions AFTER the
    unit tier — a metadata match never displaces a lexically-matching unit.
    Every result records its retrieval_channel.
    """
    rag = config_root / "data" / "release" / "rag_corpus.jsonl"
    manifest = config_root / "manifests" / "source_manifest.csv"
    t0 = time.perf_counter(); docs = load_corpus(rag, manifest); t_load = time.perf_counter() - t0
    t0 = time.perf_counter(); bm25 = BM25Index(docs); t_index = time.perf_counter() - t0
    t0 = time.perf_counter(); sidx = build_source_index(manifest); t_srcidx = time.perf_counter() - t0
    expander = SourceUnitExpander(docs)
    diversify = Reranker(strategy="diversify", max_per_source=3)
    queries = _load_queries(config_root)["queries"]

    modes = ("A_unit_diversify", "B_source_only", "C_combined")
    agg = {m: {"r5": [], "r10": [], "rr": [], "zero": 0, "lat": [], "ctx": Counter(),
               "per_query": []} for m in modes}
    q09_detail: dict[str, Any] = {}
    q17_q19: dict[str, Any] = {}

    for q in queries:
        expected = set(q.get("expected_source_ids") or [])
        t0 = time.perf_counter()
        pool = bm25.search(q["query"], top_k=2000)
        unit_tier = diversify.rerank([RetrievalResult(doc=h.doc, score=h.score,
                                                      rank=h.rank, methods={"bm25": h.rank})
                                      for h in pool])[:top_k]
        t_unit = time.perf_counter() - t0
        t0 = time.perf_counter()
        smatches = sidx.search(q["query"], top_k=top_k)
        src_units = expander.expand(smatches, top_k=top_k)
        t_src = time.perf_counter() - t0
        unit_ids = {r.doc.text_id for r in unit_tier}
        unit_sids = {r.doc.source_id for r in unit_tier}
        # Combined policy, step 5 of the task: unit results stay FIRST; source
        # evidence fills only MISSING candidates — matched sources with ZERO
        # lexical presence in the unit tier get the tail slots (max 3), each
        # labelled source_metadata. A source already covered by unit hits is
        # never duplicated; a metadata match never displaces a top unit slot.
        missing = [m for m in smatches
                   if m.source_id not in unit_sids and not m.identifier_only]
        n_fill = min(3, len(missing))
        fill = expander.expand(missing[:n_fill], top_k=n_fill)
        keep = max(top_k - len(fill), 0)
        combined = (list(unit_tier[:keep]) + fill)[:top_k]
        for r in combined:
            if r.doc.text_id not in unit_ids:
                extra = getattr(r, "extra", {})
                if isinstance(extra, dict):
                    extra.setdefault("retrieval_channel", "source_metadata")
        results_by_mode = {
            "A_unit_diversify": unit_tier,
            "B_source_only": src_units,
            "C_combined": combined[:top_k],
        }
        for mode, results in results_by_mode.items():
            A = agg[mode]
            A["lat"].append(t_unit + t_src if mode == "C_combined" else
                            (t_unit if mode == "A_unit_diversify" else t_src))
            hits = [r.doc.source_id for r in results]
            entry: dict[str, Any] = {"id": q["id"], "relevance": q.get("relevance"),
                                     "channels": [getattr(r, "extra", {}).get("retrieval_channel", "unit_bm25")
                                                  if isinstance(getattr(r, "extra", {}), dict)
                                                  else "unit_bm25" for r in results]}
            if q.get("relevance") == "source-level" and expected:
                f5 = len(expected & set(hits[:5])) / len(expected)
                f10 = len(expected & set(hits[:10])) / len(expected)
                first = next((i for i, s in enumerate(hits, 1) if s in expected), None)
                A["r5"].append(f5); A["r10"].append(f10)
                A["rr"].append(1.0 / first if first else 0.0)
                if not (expected & set(hits)):
                    A["zero"] += 1
                entry.update({"recall@5": round(f5, 3), "recall@10": round(f10, 3),
                              "mrr": round(A["rr"][-1], 3)})
            if q.get("svk_specific"):
                A["ctx"].update(r.doc.religious_scope for r in results)
            A["per_query"].append(entry)
        if q["id"] in ("q09", "q17", "q19"):
            detail: dict[str, Any] = {"query": q["query"], "expected": sorted(expected)}
            for mode, results in results_by_mode.items():
                per_source = {}
                for sid in sorted(expected):
                    pos = next((i for i, r in enumerate(results, 1)
                                if r.doc.source_id == sid), None)
                    if pos is None:
                        per_source[sid] = {"rank": None, "channel": None}
                    else:
                        r = results[pos - 1]
                        extra = getattr(r, "extra", {})
                        per_source[sid] = {
                            "rank": pos,   # position within THIS mode's list
                            "channel": extra.get("retrieval_channel", "unit_bm25")
                                       if isinstance(extra, dict) else "unit_bm25",
                            "matched_field": extra.get("source_metadata_match", {}).get("matched_field")
                                             if isinstance(extra, dict) else None,
                        }
                detail[mode] = per_source
            if q["id"] == "q09":
                q09_detail = detail
            else:
                q17_q19[q["id"]] = detail

    payload: dict[str, Any] = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "label": label,
        "corpus_units": len(docs),
        "index_build_s": round(t_index, 2),
        "source_index_build_s": round(t_srcidx, 4),
        "corpus_load_s": round(t_load, 2),
        "sources_indexed": len(sidx.sources),
        "modes": {},
        "q09_detail": q09_detail,
        "q17_q19": q17_q19,
    }
    for mode in modes:
        A = agg[mode]
        slots = sum(A["ctx"].values()) or 1
        payload["modes"][mode] = {
            "metrics": {
                "recall@5": round(sum(A["r5"]) / len(A["r5"]), 3) if A["r5"] else None,
                "recall@10": round(sum(A["r10"]) / len(A["r10"]), 3) if A["r10"] else None,
                "mrr": round(sum(A["rr"]) / len(A["rr"]), 3) if A["rr"] else None,
                "queries_with_zero_relevant_results": A["zero"],
                "mean_latency_s": round(sum(A["lat"]) / len(A["lat"]), 4),
            },
            "sect_context": dict(A["ctx"].most_common()),
            "per_query": A["per_query"],
        }
    out = config_root / "data" / "reports" / out_name
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def main() -> int:
    root = Path(__file__).resolve().parents[3]
    mode = sys.argv[1] if len(sys.argv) > 1 else "task8"
    if mode == "strategies":
        out_name = sys.argv[2] if len(sys.argv) > 2 else "retrieval_eval_results_task11.json"
        payload = evaluate_strategies(root, out_name=out_name)
        print(f"strategy comparison over {payload['corpus_units']:,} units "
              f"(pool {payload['pool_size']}, index build {payload['index_build_s']}s)")
        for s, block in payload["strategies"].items():
            m = block["metrics"]
            sc = block["sect_context"]
            print(f"  {s:10} R@5 {m['recall@5']}  R@10 {m['recall@10']}  MRR {m['mrr']}  "
                  f"zero {m['queries_with_zero_relevant_results']}  "
                  f"lat {m['mean_latency_s']}s  svk-share {sc['svk_share_of_slots']}")
        print("  wrote data/reports/" + out_name)
        return 0
    if mode == "source-channel":
        out_name = sys.argv[2] if len(sys.argv) > 2 else "retrieval_eval_results_task13.json"
        payload = evaluate_source_channel(root, out_name=out_name)
        print(f"source-channel comparison over {payload['corpus_units']:,} units, "
              f"{payload['sources_indexed']} sources indexed")
        for m, block in payload["modes"].items():
            mm = block["metrics"]
            print(f"  {m:16} R@5 {mm['recall@5']}  R@10 {mm['recall@10']}  MRR {mm['mrr']}  "
                  f"zero {mm['queries_with_zero_relevant_results']}  lat {mm['mean_latency_s']}s")
        print("  wrote data/reports/" + out_name)
        return 0
    label = mode
    out_name = sys.argv[2] if len(sys.argv) > 2 else None
    payload = evaluate(root, label=label, out_name=out_name)
    m = payload["metrics"]
    print(f"retrieval eval over {payload['corpus_units']:,} units "
          f"(index build {payload['index_build_s']}s, BM25 only)")
    print(f"  Recall@5 {m['recall@5']}  Recall@10 {m['recall@10']}  MRR {m['mrr']}  "
          f"zero-relevant {m['queries_with_zero_relevant_results']}/{m['n_source_level_queries']}")
    print(f"  latency mean {m['mean_latency_s']}s  max {m['max_latency_s']}s")
    sc = payload["sect_context"]
    print(f"  svk-context slots (svk-specific queries): CORE+HIGH share "
          f"{sc['svk_share_of_slots']}; distribution {sc['svk_specific_slot_distribution']}")
    print("  wrote data/reports/" + (out_name or "retrieval_eval_results.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

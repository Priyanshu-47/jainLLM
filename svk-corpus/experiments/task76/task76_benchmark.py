#!/usr/bin/env python3
"""Task 76 — frozen-benchmark regression for the retrieval service.

Compares the production H1 (BM25) path against the H3_RRF20 hybrid candidate
on the frozen 47-case DAPT-01 benchmark, through the NEW retrieval service
(`svk_corpus.retrieval.service.RetrievalService`) rather than the prototype
scripts.  Verifies:

  * H3_RRF20 reproduces the Task-74 pre-registered aggregates
    (unit@5 = 0.5385, source@5 = 0.9783) through the service interface.
  * H1 (BM25) reproduces its Task-74 aggregates (unit@5 = 0.3846,
    source@5 = 0.9130) — i.e. the service did not change production behaviour.
  * Per-query latency components: bm25 search, dense search, fusion, total.
  * Index disk/memory footprint.
  * Failure behaviour: missing / sha-mismatched dense artifacts produce an
    explicit, observable failure or a logged fallback to BM25.

No training, no new models, no frozen-benchmark modification.  Dense query
embeddings are the pre-computed Task-74 artifact (queries_emb.f32.npy); the
encoder is NOT run here (torch is absent locally, so encoder latency is
reported as UNRESOLVED).

Usage:
    PYTHONPATH=src python3 experiments/task76/task76_benchmark.py
"""

from __future__ import annotations

import json
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
    load_dense_index, rrf_fuse_full)

import task72.task72_experiment as t72  # noqa: E402

DENSE_DIR = ROOT / "experiments" / "task74" / "dense_index"
QUERIES_EMB = DENSE_DIR / "queries_emb.f32.npy"
OUT = ROOT / "data" / "reports" / "task76_benchmark.json"

TOP_K = 10
INF = 10 ** 9
RRF_K = 20
EVIDENCE_K = 5

# Task-74 pre-registered aggregates (frozen reference; do not edit).
PRE_REG = {
    "H1_BM25": {"unit_recall_at_5": 0.3846, "source_recall_at_5": 0.9130},
    "H3_RRF20": {"unit_recall_at_5": 0.5385, "source_recall_at_5": 0.9783},
}
TOL = 1e-3


def log(msg: str) -> None:
    print(f"[t76-bench] {msg}", flush=True)


def pct(vals: list[float]) -> dict:
    if not vals:
        return {}
    s = sorted(vals)
    return {
        "mean": round(statistics.mean(s), 4),
        "median": round(statistics.median(s), 4),
        "p95": round(s[min(len(s) - 1, int(0.95 * len(s)))], 4),
        "max": round(max(s), 4),
        "n": len(s),
    }


def unit_key(tid: str) -> str:
    return t72.unit_key(tid)


def case_ranks_from_results(results, case) -> tuple[int | None, int | None]:
    """Mirror t72.case_ranks using ServiceResult rows."""
    prov = case.get("provenance") or {}
    esrc = prov.get("source_id")
    eunits = prov.get("unit_ids") or []
    first = None
    if esrc:
        first = next((i for i, r in enumerate(results, 1)
                      if r.doc.source_id == esrc), None)
    uhit = None
    for i, r in enumerate(results, 1):
        if any(unit_key(r.doc.text_id) == u for u in eunits):
            uhit = i
            break
    return first, uhit


def run_mode(svc: RetrievalService, cases, q_emb, docs, dense_state,
             mode_name: str) -> dict:
    """Search all frozen cases under one mode; collect ranks + latencies."""
    per_case = []
    total_s: list[float] = []
    first_query_s = None
    bm25_s: list[float] = []
    dense_s: list[float] = []
    fuse_s: list[float] = []
    contract_violations: list[dict] = []

    bm25_index = svc.bm25
    n = dense_state.n if dense_state else 0
    tid2idx = dense_state.tid2idx if dense_state else {}

    for idx, case in enumerate(cases):
        query = case["question"]
        qvec = q_emb[idx] if q_emb is not None else None
        t0 = time.perf_counter()
        resp = svc.search(query, top_k=TOP_K, query_id=case["example_id"],
                          query_embedding=qvec)
        dt = time.perf_counter() - t0
        total_s.append(dt)
        if first_query_s is None:
            first_query_s = dt

        # component timings (H3 only; measured on the same artifacts)
        if mode_name == "H3_RRF20" and dense_state is not None:
            t = time.perf_counter()
            full = bm25_index.search(query, top_k=INF)
            bm25_s.append(time.perf_counter() - t)
            bm25_rank = {r.doc.text_id: r.rank for r in full}
            t = time.perf_counter()
            scores = dense_state.emb @ qvec
            order = np.argsort(-scores, kind="stable")
            dense_s.append(time.perf_counter() - t)
            rank_of = np.empty(n, dtype=np.int64)
            rank_of[order] = np.arange(1, n + 1)
            t = time.perf_counter()
            rrf_fuse_full(bm25_rank, rank_of, RRF_K, tid2idx, n)
            fuse_s.append(time.perf_counter() - t)

        first, uhit = case_ranks_from_results(resp.results, case)
        src_hits = [r for r in resp.results
                    if case.get("provenance", {}).get("source_id")
                    and r.doc.source_id == case["provenance"]["source_id"]]
        per_case.append({
            "example_id": case["example_id"],
            "source_first_rank": first,
            "unit_hit_rank": uhit,
            "expected_source": bool((case.get("provenance") or {}).get("source_id")),
            "expected_units": bool((case.get("provenance") or {}).get("unit_ids")),
            "results_sources_hit": bool(src_hits),
            "results_sources_hit_only_metadata": bool(src_hits) and all(
                r.channel.startswith("source_metadata") for r in src_hits),
            "mode_used": resp.mode_used.value,
            "fallback_reason": resp.fallback_reason,
            "latency_s": round(dt, 6),
        })

        # contract-validate every served result
        for r in resp.results:
            cr = r.to_canonical(query, (), case_id=case["example_id"])
            from svk_corpus.retrieval.contract import validate_result
            v = validate_result(cr)
            if v:
                contract_violations.append(
                    {"example_id": case["example_id"],
                     "result_id": cr.result_id, "violations": v})

    src = [p["source_first_rank"] for p in per_case if p["expected_source"]]
    unit = [p["unit_hit_rank"] for p in per_case if p["expected_units"]]
    agg = {
        "n_source_level": len(src),
        "source_recall_at_1": t72.recall(src, 1),
        "source_recall_at_3": t72.recall(src, 3),
        "source_recall_at_5": t72.recall(src, 5),
        "source_recall_at_10": t72.recall(src, 10),
        "source_mrr": t72.mrr(src),
        "n_unit_labeled": len(unit),
        "unit_recall_at_1": t72.recall(unit, 1),
        "unit_recall_at_3": t72.recall(unit, 3),
        "unit_recall_at_5": t72.recall(unit, 5),
        "unit_recall_at_10": t72.recall(unit, 10),
        "unit_mrr": t72.mrr(unit),
    }
    return {
        "aggregates": agg,
        "per_case": per_case,
        "latency_total_s": pct(total_s),
        "first_query_s": round(first_query_s, 6) if first_query_s else None,
        "latency_bm25_full_s": pct(bm25_s),
        "latency_dense_search_s": pct(dense_s),
        "latency_fusion_s": pct(fuse_s),
        "contract_violations": contract_violations,
        "contract_violations_total": len(contract_violations),
        "modes_used": sorted({p["mode_used"] for p in per_case}),
        "fallbacks": sum(1 for p in per_case if p["fallback_reason"]),
    }


def check_reproduction(agg: dict, expected: dict, name: str) -> dict:
    gates = {}
    for key, exp in expected.items():
        got = agg.get(key)
        ok = got is not None and abs(got - exp) <= TOL
        gates[key] = {"expected": exp, "got": got, "pass": ok}
    gates["all_pass"] = all(g["pass"] for g in gates.values()
                            if isinstance(g, dict) and "pass" in g)
    log(f"{name} reproduction: {gates['all_pass']}")
    return gates


def failure_behavior(docs, dense_dir: Path) -> dict:
    out: dict = {}
    # 1. missing index dir -> fallback with logged reason
    logged: list[str] = []
    pol = RetrievalPolicy(mode=RetrievalMode.HYBRID_RRF20,
                          fallback_on_dense_failure=True)
    svc = RetrievalService(policy=pol, docs=docs, logger=logged.append)
    resp = svc.search("Kalpa Sutra", top_k=3)
    out["missing_dir_falls_back"] = (
        resp.mode_used is RetrievalMode.BM25
        and resp.fallback_reason is not None
        and bool(resp.results))
    out["missing_dir_logged"] = any("fallback bm25" in m for m in logged)

    # 2. missing index dir -> strict raises
    pol_s = RetrievalPolicy(mode=RetrievalMode.HYBRID_RRF20, strict_dense=True)
    svc_s = RetrievalService(policy=pol_s, docs=docs)
    try:
        svc_s.search("x", top_k=2)
        out["strict_raises"] = False
    except DenseIndexUnavailable:
        out["strict_raises"] = True

    # 3. sha-mismatched index -> load raises DenseIndexUnavailable
    import hashlib, tempfile
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        emb = np.zeros((len(docs), 4), dtype=np.float16)
        idx = tmp / "corpus_emb.f16.npy"
        np.save(idx, emb)
        meta = {"model_id": "x", "model_revision": "0", "embedding_dim": 4,
                "corpus_emb_f16_sha256": "0" * 64,
                "alignment": {"corpus_text_sha256": "0" * 64,
                              "doc_ids_sha256": "0" * 64,
                              "doc_count": len(docs)}}
        (tmp / "index_meta.json").write_text(json.dumps(meta))
        try:
            load_dense_index(tmp, docs, verify_file_sha=True)
            out["sha_mismatch_raises"] = False
        except DenseIndexUnavailable:
            out["sha_mismatch_raises"] = True

    out["all_pass"] = all(v for k, v in out.items()
                          if isinstance(v, bool))
    return out


def main() -> int:
    log("integrity: verifying frozen benchmark sha")
    sha = t72.sha256_file(t72.CASES_PATH)
    assert sha == t72.FROZEN_SHA, f"frozen bench sha mismatch: {sha}"
    log(f"  frozen sha ok: {sha[:16]}…")

    log("loading corpus (this takes a while)")
    docs = load_corpus(t72.CORPUS_PATH, t72.MANIFEST_PATH)
    n = len(docs)
    log(f"  corpus docs: {n}")

    cases = [json.loads(l) for l in
             t72.CASES_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(cases) == 47, f"expected 47 cases, got {len(cases)}"

    log("loading dense index (full alignment verification)")
    t0 = time.perf_counter()
    dense_state = load_dense_index(DENSE_DIR, docs, verify_file_sha=True,
                                   verify_alignment=True)
    load_s = time.perf_counter() - t0
    log(f"  dense loaded in {load_s:.2f}s; n={dense_state.n}; "
        f"verified={dense_state.verified}")

    q_emb = np.load(QUERIES_EMB).astype(np.float32)
    qn = np.linalg.norm(q_emb, axis=1, keepdims=True)
    qn[qn == 0] = 1.0
    q_emb /= qn
    assert q_emb.shape[0] == 47

    # ---- H1 (BM25 production default) ----
    log("running H1 (BM25) through the service")
    svc_h1 = RetrievalService(policy=RetrievalPolicy(mode=RetrievalMode.BM25),
                              docs=docs)
    h1 = run_mode(svc_h1, cases, q_emb, docs, dense_state, "H1_BM25")

    # ---- H3 (hybrid RRF@20 candidate) ----
    log("running H3_RRF20 (hybrid) through the service")
    svc_h3 = RetrievalService(
        policy=RetrievalPolicy(mode=RetrievalMode.HYBRID_RRF20),
        docs=docs, dense=dense_state, query_encoder=None)
    h3 = run_mode(svc_h3, cases, q_emb, docs, dense_state, "H3_RRF20")

    # ---- reproduction gates ----
    h1_gates = check_reproduction(h1["aggregates"], PRE_REG["H1_BM25"], "H1")
    h3_gates = check_reproduction(h3["aggregates"], PRE_REG["H3_RRF20"], "H3")

    # ---- performance / failure ----
    log("probing failure behaviour")
    fails = failure_behavior(docs, DENSE_DIR)
    log(f"  failure probes all pass: {fails['all_pass']}")

    disk_bytes = (DENSE_DIR / "corpus_emb.f16.npy").stat().st_size
    index_info = {
        "dense_disk_bytes": disk_bytes,
        "dense_array_bytes_loaded_f32": int(dense_state.emb.nbytes),
        "dense_index_load_s": round(load_s, 3),
        "dense_index_meta_runtime": dense_state.meta.get("runtime"),
        "corpus_docs": n,
        "bm25_memory_bytes": "unresolved (python object graph; not measured)",
        "query_encoder_latency": "UNRESOLVED (torch absent locally; "
                                 "queries pre-encoded by Task-74 artifact)",
    }

    all_repro = h1_gates["all_pass"] and h3_gates["all_pass"]
    verdict = "REPRODUCTION_PASS" if all_repro else "REPRODUCTION_FAIL"

    report = {
        "task": 76,
        "verdict": verdict,
        "frozen_bench_sha256": sha,
        "n_cases": 47,
        "H1_BM25": h1,
        "H3_RRF20": h3,
        "reproduction_gates": {"H1_BM25": h1_gates, "H3_RRF20": h3_gates},
        "index_info": index_info,
        "failure_behavior": fails,
        "notes": [
            "Latency excludes one-time dense index load and corpus load.",
            "H1/H3 latencies measured per query through the service.",
            "Encoder latency is UNRESOLVED locally; dense query vectors are "
            "the pre-computed Task-74 artifact (queries_emb.f32.npy).",
            "BM25 is the production default throughout; H3_RRF20 is opt-in.",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    log(f"wrote {OUT}")
    log(f"VERDICT: {verdict}")
    print(json.dumps({"verdict": verdict,
                      "h1_u5": h1["aggregates"]["unit_recall_at_5"],
                      "h3_u5": h3["aggregates"]["unit_recall_at_5"],
                      "h3_s5": h3["aggregates"]["source_recall_at_5"],
                      "h3_total_s": h3["latency_total_s"]}, indent=1))
    return 0 if all_repro else 1


if __name__ == "__main__":
    sys.exit(main())

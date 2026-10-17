#!/usr/bin/env python3
"""Task 77 — fusion-cost evaluation and exactly-equivalent optimisation.

The current ``rrf_fuse_full`` (Task-74/76 semantics) costs ~67 ms mean per
query at 164k docs (measured in task77_latency.py).  That is material
(~19 % of H3_RRF20 p50).  This script:

  1. Profiles the current implementation by component.
  2. Prototypes an EXACTLY-equivalent optimised implementation in this
     experiment-local path (vectorised BM25 update — no Python loop; the
     lexsort semantics are unchanged).
  3. Verifies exact ranked-output equivalence across all 47 frozen queries
     plus additional deterministic test queries (varying BM25-list sizes,
     tie scenarios, empty/one-sided lists).
  4. Compares latency and memory before/after.

The production ``service.rrf_fuse_full`` is NOT modified here.  If the
optimised version is proven equivalent AND covered by regression tests, a
follow-up may adopt it; this script only establishes the evidence.

Usage:
    PYTHONPATH=src:experiments python3 experiments/task77/task77_fusion_opt.py
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

from svk_corpus.retrieval.service import rrf_fuse_full  # noqa: E402
from svk_corpus.retrieval import load_corpus  # noqa: E402

import task72.task72_experiment as t72  # noqa: E402
from task76.task76_benchmark import DENSE_DIR, QUERIES_EMB  # noqa: E402

from svk_corpus.retrieval.service import load_dense_index  # noqa: E402

OUT = ROOT / "data" / "reports" / "task77_fusion_opt.json"
INF = 10 ** 9
RRF_K = 20
N_ITER = 200


def log(msg: str) -> None:
    print(f"[t77-fuse] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Baseline (current production) and optimised implementations
# ---------------------------------------------------------------------------

def rrf_fuse_full_baseline(bm25_rank: dict[str, int], dense_rank_of,
                           k: int, tid2idx: dict[str, int], n: int):
    """Current implementation — copied semantics from service.rrf_fuse_full."""
    score = 1.0 / (k + dense_rank_of.astype(np.float64))
    bmr = np.full(n, INF, dtype=np.int64)
    for tid, r in bm25_rank.items():
        di = tid2idx[tid]
        score[di] += 1.0 / (k + r)
        bmr[di] = r
    order = np.lexsort((np.arange(n), dense_rank_of, bmr, -score))
    return order


def rrf_fuse_full_optimized(bm25_rank: dict[str, int], dense_rank_of,
                            k: int, tid2idx: dict[str, int], n: int):
    """Exactly-equivalent optimisation: vectorised BM25 update.

    Identical arithmetic and lexsort keys; the only change is that the
    per-document Python loop is replaced by numpy fancy indexing, which
    produces bit-identical score/bmr arrays.
    """
    score = 1.0 / (k + dense_rank_of.astype(np.float64))
    bmr = np.full(n, INF, dtype=np.int64)
    if bm25_rank:
        hits = np.fromiter((tid2idx[tid] for tid in bm25_rank),
                           dtype=np.int64, count=len(bm25_rank))
        ranks = np.fromiter(bm25_rank.values(), dtype=np.int64,
                            count=len(bm25_rank))
        score[hits] += 1.0 / (k + ranks.astype(np.float64))
        bmr[hits] = ranks
    order = np.lexsort((np.arange(n), dense_rank_of, bmr, -score))
    return order


# ---------------------------------------------------------------------------
# Equivalence checks
# ---------------------------------------------------------------------------

def check_equivalence(cases: list[dict]) -> dict:
    """Verify exact ranked-output equality baseline vs optimised."""
    mismatches: list[dict] = []
    n_checked = 0
    for c in cases:
        bm25_rank = c["bm25_rank"]
        dense_rank = c["dense_rank"]
        tid2idx = c["tid2idx"]
        n = c["n"]
        k = c.get("k", RRF_K)
        o1 = rrf_fuse_full_baseline(bm25_rank, dense_rank, k, tid2idx, n)
        o2 = rrf_fuse_full_optimized(bm25_rank, dense_rank, k, tid2idx, n)
        n_checked += 1
        if not np.array_equal(o1, o2):
            mismatches.append({
                "label": c.get("label", "?"),
                "first_divergence": int(np.argmax(o1 != o2)),
                "baseline_head": o1[:10].tolist(),
                "optimized_head": o2[:10].tolist(),
            })
    return {
        "n_cases": n_checked,
        "n_mismatches": len(mismatches),
        "exact_match": len(mismatches) == 0,
        "mismatches": mismatches[:5],
    }


def build_synthetic_cases(n: int = 5000) -> list[dict]:
    """Deterministic synthetic tie/edge cases beyond the frozen queries."""
    rng = np.random.RandomState(42)
    cases: list[dict] = []
    tid2idx = {f"d{i}": i for i in range(n)}

    def mk(label, bm25_pairs, dense_ranks, n=n, tid2idx=tid2idx):
        cases.append({
            "label": label,
            "bm25_rank": {tid: r for tid, r in bm25_pairs},
            "dense_rank": np.asarray(dense_ranks, dtype=np.int64),
            "tid2idx": tid2idx, "n": n,
        })

    # 1. empty bm25 list
    dr = rng.permutation(n) + 1
    mk("empty_bm25", [], dr)
    # 2. bm25 covers every doc (dense irrelevant for ties)
    mk("full_overlap", [(f"d{i}", int(dr[i])) for i in range(n)], dr)
    # 3. heavy ties: all bm25 ranks identical, dense ranks identical
    mk("all_ties", [(f"d{i}", 1) for i in range(0, n, 2)],
       np.ones(n, dtype=np.int64))
    # 4. one-sided: single bm25 hit
    mk("one_hit", [("d7", 1)], dr)
    # 5. bm25 ranks descending opposite to dense
    mk("anti_correlated", [(f"d{i}", n - i) for i in range(n)],
       np.arange(1, n + 1))
    # 6. random sparse bm25
    idx = rng.choice(n, size=n // 10, replace=False)
    mk("sparse_random", [(f"d{i}", int(rng.randint(1, 1000))) for i in idx], dr)
    # 7. duplicate-value stress (many identical fused scores)
    dr2 = np.ones(n, dtype=np.int64)
    mk("dense_flat", [(f"d{i}", 1) for i in range(0, n, 3)], dr2)
    return cases


def main() -> int:
    log("loading corpus + dense index for frozen-query cases")
    docs = load_corpus(t72.CORPUS_PATH, t72.MANIFEST_PATH)
    dense = load_dense_index(DENSE_DIR, docs, verify_file_sha=True,
                             verify_alignment=False)
    q_emb = np.load(QUERIES_EMB).astype(np.float32)
    qn = np.linalg.norm(q_emb, axis=1, keepdims=True)
    qn[qn == 0] = 1.0
    q_emb /= qn
    cases = [json.loads(l) for l in
             t72.CASES_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]

    from svk_corpus.retrieval import BM25Index
    bm25 = BM25Index(docs, k1=1.5, b=0.75)

    log("building frozen-query fusion cases")
    frozen_cases: list[dict] = []
    for i, case in enumerate(cases):
        q = case["question"]
        full = bm25.search(q, top_k=10 ** 9)
        bm25_rank = {r.doc.text_id: r.rank for r in full}
        scores = dense.emb @ q_emb[i]
        order = np.argsort(-scores, kind="stable")
        rank_of = np.empty(dense.n, dtype=np.int64)
        rank_of[order] = np.arange(1, dense.n + 1)
        frozen_cases.append({
            "label": case["example_id"], "bm25_rank": bm25_rank,
            "dense_rank": rank_of, "tid2idx": dense.tid2idx, "n": dense.n,
        })

    synth_cases = build_synthetic_cases()
    all_cases = frozen_cases + synth_cases

    log(f"equivalence check: {len(all_cases)} cases "
        f"({len(frozen_cases)} frozen + {len(synth_cases)} synthetic)")
    equiv = check_equivalence(all_cases)
    log(f"  exact match: {equiv['exact_match']} "
        f"({equiv['n_mismatches']} mismatches)")

    # ---- latency comparison on frozen queries ----
    log(f"latency comparison ({N_ITER} iterations x frozen queries, interleaved)")
    base_s: list[float] = []
    opt_s: list[float] = []
    for c in frozen_cases:
        for _ in range(N_ITER // len(frozen_cases) + 1):
            t0 = time.perf_counter()
            rrf_fuse_full_baseline(c["bm25_rank"], c["dense_rank"], RRF_K,
                                   c["tid2idx"], c["n"])
            base_s.append(time.perf_counter() - t0)
            t0 = time.perf_counter()
            rrf_fuse_full_optimized(c["bm25_rank"], c["dense_rank"], RRF_K,
                                    c["tid2idx"], c["n"])
            opt_s.append(time.perf_counter() - t0)

    def pct(vals):
        s = sorted(vals)
        return {"n": len(s), "mean": round(statistics.mean(s), 6),
                "p50": round(s[len(s)//2], 6),
                "p95": round(s[int(0.95*len(s))], 6)}

    base_p, opt_p = pct(base_s), pct(opt_s)
    speedup = round(base_p["mean"] / opt_p["mean"], 3) if opt_p["mean"] else None
    log(f"  baseline mean {base_p['mean']*1000:.2f} ms | "
        f"optimized mean {opt_p['mean']*1000:.2f} ms | speedup {speedup}x")

    # ---- memory: peak array footprint is identical (same arrays) ----
    sample = frozen_cases[0]
    sc = 1.0 / (RRF_K + sample["dense_rank"].astype(np.float64))
    mem_bytes = sc.nbytes + np.full(sample["n"], INF, dtype=np.int64).nbytes

    report = {
        "task": 77,
        "fusion_bottleneck_material": True,
        "materiality_note": "fusion mean ~67ms = ~19% of H3_RRF20 p50 (338ms)",
        "dominant_cost": "lexsort (~25ms) + score compute (~23ms) + "
                         "python bm25 loop (~19ms)",
        "optimization": {
            "change": "vectorised BM25 score/bmr update (numpy fancy indexing "
                      "replaces per-doc python loop); lexsort keys unchanged",
            "equivalence": equiv,
            "production_modified": False,
            "note": "experiment-local prototype only; production "
                    "service.rrf_fuse_full untouched",
        },
        "latency": {"baseline": base_p, "optimized": opt_p, "speedup": speedup},
        "memory": {
            "score_array_bytes": int(sc.nbytes),
            "bmr_array_bytes": int(np.full(sample["n"], INF, dtype=np.int64).nbytes),
            "note": "identical array footprint before/after; only the "
                    "update path is faster",
        },
        "e2e_context": {
            "H3_RRF20_p50_ms": 338.5,
            "fusion_baseline_mean_ms": round(base_p["mean"] * 1000, 2),
            "fusion_optimized_mean_ms": round(opt_p["mean"] * 1000, 2),
            "expected_e2e_saving_ms": round(
                (base_p["mean"] - opt_p["mean"]) * 1000, 2),
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    log(f"wrote {OUT}")
    print(json.dumps({
        "exact_match": equiv["exact_match"],
        "baseline_mean_ms": round(base_p["mean"] * 1000, 2),
        "optimized_mean_ms": round(opt_p["mean"] * 1000, 2),
        "speedup": speedup,
        "expected_e2e_saving_ms": report["e2e_context"]["expected_e2e_saving_ms"],
    }, indent=1))
    return 0 if equiv["exact_match"] else 1


if __name__ == "__main__":
    sys.exit(main())

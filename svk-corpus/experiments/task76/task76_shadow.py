#!/usr/bin/env python3
"""Task 76 — offline shadow replay of H3_RRF20 alongside authoritative BM25.

Replays the frozen 47-case DAPT-01 benchmark through the production retrieval
service in a shadow configuration:

  * BM25 (H1) is AUTHORITATIVE — it serves the answer, unchanged.
  * H3_RRF20 is evaluated alongside as a SHADOW — its rankings are recorded
    for comparison but never replace the authoritative BM25 results.

Measures agreement between authoritative and shadow rankings (overlap@5),
and quantifies what the hybrid candidate would change if ever promoted:

  * recoveries  — expected unit is a top-5 MISS under BM25 but a top-5 HIT
    under hybrid (the hybrid adds value).
  * regressions — expected unit is a top-5 HIT under BM25 but a top-5 MISS
    under hybrid (the hybrid would lose ground).
  * unchanged hits / unchanged misses.

This is an OFFLINE replay: there is no live serving API in this pipeline, so
shadow validation is OFFLINE (not LIVE).  No production default is changed;
BM25 remains the served mode throughout.

Usage:
    PYTHONPATH=src:experiments python3 experiments/task76/task76_shadow.py
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

from svk_corpus.retrieval import load_corpus  # noqa: E402
from svk_corpus.retrieval.service import (  # noqa: E402
    RetrievalMode, RetrievalPolicy, RetrievalService, load_dense_index)

import task72.task72_experiment as t72  # noqa: E402
from task76.task76_benchmark import (DENSE_DIR, QUERIES_EMB,  # noqa: E402
                                     case_ranks_from_results)

OUT = ROOT / "data" / "reports" / "task76_shadow.json"
TOP_K = 10


def log(msg: str) -> None:
    print(f"[t76-shadow] {msg}", flush=True)


def top5_ids(resp) -> set[str]:
    return {r.doc.text_id for r in resp.results[:5]}


def main() -> int:
    log("loading corpus + dense index")
    docs = load_corpus(t72.CORPUS_PATH, t72.MANIFEST_PATH)
    dense_state = load_dense_index(DENSE_DIR, docs, verify_file_sha=True,
                                   verify_alignment=False)
    cases = [json.loads(l) for l in
             t72.CASES_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    q_emb = np.load(QUERIES_EMB).astype(np.float32)
    qn = np.linalg.norm(q_emb, axis=1, keepdims=True)
    qn[qn == 0] = 1.0
    q_emb /= qn

    auth_svc = RetrievalService(policy=RetrievalPolicy(mode=RetrievalMode.BM25),
                                docs=docs)
    shadow_svc = RetrievalService(
        policy=RetrievalPolicy(mode=RetrievalMode.HYBRID_RRF20),
        docs=docs, dense=dense_state, query_encoder=None)

    recoveries: list[str] = []
    regressions: list[str] = []
    both_hit: list[str] = []
    both_miss: list[str] = []
    overlaps: list[float] = []
    per_case: list[dict] = []
    auth_modes: set[str] = set()

    for idx, case in enumerate(cases):
        eid = case["example_id"]
        query = case["question"]
        qvec = q_emb[idx]

        # AUTHORITATIVE: BM25 serves the answer.
        auth = auth_svc.search(query, top_k=TOP_K, query_id=eid)
        auth_modes.add(auth.mode_used.value)
        assert auth.mode_used is RetrievalMode.BM25, "BM25 must stay authoritative"

        # SHADOW: hybrid evaluated alongside; does not touch auth.
        shadow = shadow_svc.search(query, top_k=TOP_K, query_id=eid,
                                   query_embedding=qvec)
        assert shadow.mode_used is RetrievalMode.HYBRID_RRF20

        a5 = top5_ids(auth)
        s5 = top5_ids(shadow)
        union = a5 | s5
        ov = len(a5 & s5) / len(union) if union else 1.0
        overlaps.append(ov)

        a_uhit = case_ranks_from_results(auth.results, case)[1]
        s_uhit = case_ranks_from_results(shadow.results, case)[1]
        a_hit = a_uhit is not None and a_uhit <= 5
        s_hit = s_uhit is not None and s_uhit <= 5
        if a_hit and s_hit:
            both_hit.append(eid)
        elif a_hit and not s_hit:
            regressions.append(eid)
        elif not a_hit and s_hit:
            recoveries.append(eid)
        else:
            both_miss.append(eid)

        per_case.append({
            "example_id": eid,
            "auth_unit_rank": a_uhit, "shadow_unit_rank": s_uhit,
            "auth_hit5": a_hit, "shadow_hit5": s_hit,
            "overlap5": round(ov, 4),
            "auth_mode": auth.mode_used.value,
            "shadow_mode": shadow.mode_used.value,
        })

        # authoritative result set must be identical across repeated serves
        again = auth_svc.search(query, top_k=TOP_K, query_id=eid)
        assert [r.doc.text_id for r in auth.results] == \
               [r.doc.text_id for r in again.results], "auth mutated"

    n = len(cases)
    unit_cases = [c for c in cases if (c.get("provenance") or {}).get("unit_ids")]
    nu = len(unit_cases)
    report = {
        "task": 76,
        "shadow_validation": "OFFLINE",
        "authoritative_mode": "bm25",
        "shadow_mode": "hybrid_rrf20",
        "n_cases": n,
        "n_unit_labeled": nu,
        "served_modes_observed": sorted(auth_modes),
        "bm25_authoritative_unchanged": auth_modes == {"bm25"},
        "shadow_never_replaced_authoritative": True,
        "agreement": {
            "overlap_at_5_mean": round(statistics.mean(overlaps), 4),
            "overlap_at_5_median": round(statistics.median(overlaps), 4),
        },
        "unit_hit5_dynamics": {
            "both_hit": len(both_hit), "both_hit_cases": both_hit,
            "recoveries_hybrid_adds": len(recoveries),
            "recoveries_cases": recoveries,
            "regressions_hybrid_loses": len(regressions),
            "regressions_cases": regressions,
            "both_miss": len(both_miss), "both_miss_cases": both_miss,
            "net_delta_hits_at_5": len(recoveries) - len(regressions),
        },
        "per_case": per_case,
        "notes": [
            "Offline replay: no live serving API exists; shadow is OFFLINE.",
            "BM25 is authoritative and unchanged; hybrid is recorded alongside.",
            "Recoveries = expected unit a top-5 miss under BM25 but hit under "
            "hybrid; regressions = the reverse.",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    log(f"wrote {OUT}")
    dyn = report["unit_hit5_dynamics"]
    log(f"authoritative unchanged: {report['bm25_authoritative_unchanged']}")
    log(f"overlap@5 mean: {report['agreement']['overlap_at_5_mean']}")
    log(f"recoveries: {dyn['recoveries_hybrid_adds']}, "
        f"regressions: {dyn['regressions_hybrid_loses']}, "
        f"net: {dyn['net_delta_hits_at_5']}")
    print(json.dumps({
        "shadow_validation": "OFFLINE",
        "bm25_authoritative_unchanged": True,
        "overlap5_mean": report["agreement"]["overlap_at_5_mean"],
        "recoveries": dyn["recoveries_hybrid_adds"],
        "regressions": dyn["regressions_hybrid_loses"],
        "net": dyn["net_delta_hits_at_5"],
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

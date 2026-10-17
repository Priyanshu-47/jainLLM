"""TASK 75 Phase-1 — reproduce Task-74 H3_RRF20 and build governed evidence.

Reuses Task-74/72/69 machinery verbatim (result_row74, rrf_fuse,
build_block_and_metrics, build_context_block). Re-runs only the H3_RRF20
config (evidence_k=5, text_trunc=500 — Task-69 evidence width) over the
frozen 47-case benchmark and HARD-STOPs unless aggregates match the frozen
Task-74 record: unit@5=0.5385, src@5=0.9783, ceiling=0.8372, Ev0=7.

Outputs (never overwrite prior-task artifacts)
  data/evaluation/task75_rag_evidence.jsonl
  data/evaluation/task75_rag_prompts.jsonl
  data/evaluation/task75_retrieval_metrics.json
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "experiments" / "dapt_01" / "evaluation"))
sys.path.insert(0, str(REPO / "experiments" / "task72"))
sys.path.insert(0, str(REPO / "experiments" / "task74"))
sys.path.insert(0, str(REPO / "experiments" / "task75"))

import score_task60  # noqa: E402
from svk_corpus.retrieval import (  # noqa: E402
    BM25Index,
    RetrievalResult,
    load_corpus,
)
from svk_corpus.retrieval.contract import validate_result  # noqa: E402
from svk_corpus.retrieval.normalization import expand_query_text  # noqa: E402
from svk_corpus.retrieval.rerank import Reranker  # noqa: E402
from svk_corpus.retrieval.source_channel import (  # noqa: E402
    SourceUnitExpander,
    build_source_index,
)

import task72_experiment as t72  # noqa: E402
import task74_experiment as t74  # noqa: E402

t69 = t72.t69

CASES_PATH = REPO / "data" / "evaluation" / "dapt01_eval_cases.jsonl"
MANIFEST_PATH = REPO / "manifests" / "source_manifest.csv"
CORPUS_PATH = REPO / "data" / "release" / "rag_corpus.jsonl"
FROZEN_SHA = "06625f72190e3ae130447345afdc04342bd19cb76f842285706480cba7765b81"
TASK74_METRICS = REPO / "data" / "evaluation" / "task74_metrics.json"

DENSE_DIR = REPO / "experiments" / "task74" / "dense_index"
INDEX_META = DENSE_DIR / "index_meta.json"
CORPUS_EMB = DENSE_DIR / "corpus_emb.f16.npy"
QUERIES_EMB = DENSE_DIR / "queries_emb.f32.npy"

OUT_EVIDENCE = REPO / "data" / "evaluation" / "task75_rag_evidence.jsonl"
OUT_PROMPTS = REPO / "data" / "evaluation" / "task75_rag_prompts.jsonl"
OUT_METRICS = REPO / "data" / "evaluation" / "task75_retrieval_metrics.json"

RRF_K = 20
TOP_K = 10
EVIDENCE_K = 5
TEXT_TRUNC = 500
CFG = {"evidence_k": EVIDENCE_K, "text_trunc": TEXT_TRUNC, "mode": "rrf"}

# Frozen Task-74 H3_RRF20 aggregates — reproduction gate.
EXPECTED = {
    "unit_recall_at_5": 0.5385,
    "source_recall_at_5": 0.9783,
    "evidence_ceiling_mean": 0.8372,
    "ev0_count": 7,
}


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    t0 = time.time()
    if sha256_file(CASES_PATH) != FROZEN_SHA:
        print("STOP: frozen benchmark sha mismatch")
        return 3
    if not TASK74_METRICS.exists():
        print("STOP: task74_metrics.json missing — run Task-74 first")
        return 3
    t74_meta = json.loads(TASK74_METRICS.read_text(encoding="utf-8"))
    t74_agg = t74_meta["aggregates"]["H3_RRF20"]
    for key, want in EXPECTED.items():
        got = t74_agg.get(key)
        if got != want:
            print(f"STOP: task74 frozen {key}={got} != expected {want}")
            return 3
    log(f"task74 frozen H3_RRF20 aggregates verified {EXPECTED}")

    cases = t72.load_jsonl(CASES_PATH)
    cards = t69.load_manifest_cards(MANIFEST_PATH)
    if len(cases) != 47 or not INDEX_META.exists() or not CORPUS_EMB.exists():
        print("STOP: cases!=47 or dense index missing")
        return 3
    meta = json.loads(INDEX_META.read_text(encoding="utf-8"))
    al = meta["alignment"]

    docs = load_corpus(CORPUS_PATH, MANIFEST_PATH)
    bm25 = BM25Index(docs, k1=1.5, b=0.75)
    log(f"corpus {len(docs)} docs, bm25 built")

    text_sha = hashlib.sha256()
    id_sha = hashlib.sha256()
    for d in docs:
        text_sha.update(d.search_text.encode("utf-8"))
        id_sha.update(d.text_id.encode("utf-8"))
    q_sha = hashlib.sha256()
    for c in cases:
        q_sha.update(c["question"].encode("utf-8"))
    problems = []
    if text_sha.hexdigest() != al["corpus_text_sha256"]:
        problems.append("corpus_text_sha256")
    if id_sha.hexdigest() != al["doc_ids_sha256"]:
        problems.append("doc_ids_sha256")
    if q_sha.hexdigest() != al["queries_sha256"]:
        problems.append("queries_sha256")
    if al["doc_count"] != len(docs):
        problems.append("doc_count")
    if problems:
        print("STOP: dense index alignment failure: " + "; ".join(problems))
        return 3
    log("alignment shas verified")

    emb = np.load(CORPUS_EMB).astype(np.float32)
    nrm = np.linalg.norm(emb, axis=1, keepdims=True)
    nrm[nrm == 0] = 1.0
    emb /= nrm
    q_emb = np.load(QUERIES_EMB).astype(np.float32)
    qn = np.linalg.norm(q_emb, axis=1, keepdims=True)
    qn[qn == 0] = 1.0
    q_emb /= qn
    n = emb.shape[0]
    log(f"dense index loaded {emb.shape}")

    tid2idx = {d.text_id: i for i, d in enumerate(docs)}

    evidence_rows: list[dict] = []
    prompt_rows: list[dict] = []
    per_case: list[dict] = []
    violations_total: list[dict] = []

    for idx, case in enumerate(cases):
        eid = case["example_id"]
        query = case["question"]
        norm_tokens = tuple(expand_query_text(query))

        scores = emb @ q_emb[idx]
        order = np.argsort(-scores, kind="stable")
        rank_of = np.empty(n, dtype=np.int64)
        rank_of[order] = np.arange(1, n + 1)

        full = bm25.search(query, top_k=10 ** 9)
        bm25_rank = {r.doc.text_id: r.rank for r in full}
        bm25_score = {r.doc.text_id: r.score for r in full}

        fused = t74.rrf_fuse(bm25_rank, rank_of, RRF_K, tid2idx, n)
        fused10 = [int(x) for x in fused[:TOP_K]]

        results_out: list[dict] = []
        for i, di in enumerate(fused10, 1):
            tid = docs[di].text_id
            dr = int(rank_of[di])
            rrf_score = float(
                (1.0 / (RRF_K + dr))
                + ((1.0 / (RRF_K + bm25_rank[tid])) if tid in bm25_rank else 0.0)
            )
            in_bm25 = tid in bm25_rank
            methods = {"dense": dr}
            if in_bm25:
                methods["bm25"] = bm25_rank[tid]
            rr = RetrievalResult(doc=docs[di], score=rrf_score, rank=i,
                                 methods=methods)
            if in_bm25:
                rr.extra = t74.NS(bm25_rank=bm25_rank[tid],
                                  bm25_score=float(bm25_score[tid]))
            if in_bm25:
                row, _ = t74.result_row74(rr, eid, i, "unit_bm25", query,
                                          norm_tokens)
                row["dense_rank"] = dr
                row["dense_score"] = round(float(scores[di]), 6)
            else:
                row, _ = t74.result_row74(rr, eid, i, "dense", query,
                                          norm_tokens,
                                          dense=(dr, float(scores[di])))
            results_out.append(row)
            if row["contract_violations"]:
                violations_total.append(
                    {"result_id": row["result_id"],
                     "violations": row["contract_violations"]})

        mb = t72.build_block_and_metrics(case, results_out, cards, CFG)
        first, uhit = t72.case_ranks(results_out, case)
        prov = case.get("provenance") or {}
        esrc = prov.get("source_id")
        eunits = prov.get("unit_ids") or []
        src_hits = [r for r in results_out if r["source_id"] == esrc] if esrc else []

        ctx_items = []
        for pos, res in enumerate(results_out[:EVIDENCE_K], 1):
            ctx_items.append({
                "pos": pos,
                "text_id": res["text_id"],
                "source_id": res["source_id"],
                "title": res["title"],
                "retrieval_channel": res["retrieval_channel"],
                "retrieval_rank": res["retrieval_rank"],
                "retrieval_score": res["retrieval_score"],
                "provenance": res["provenance"],
                "locator_citation": res["locator_citation"],
                "text_truncated": t69.truncate(res["text"], TEXT_TRUNC),
            })
        block = mb["context_text"]
        user_content = block + "\n\n" + query
        prompt_rows.append({
            "example_id": eid,
            "question": query,
            "user_content": user_content,
            "context_sha256": mb["context_sha256"],
            "n_evidence_items": mb["n_evidence_items"],
            "context_chars": mb["context_chars"],
        })
        evidence_rows.append({
            "example_id": eid,
            "query": query,
            "retrieval": {
                "mode": "RRF(BM25 full, dense full) k=20",
                "top_k": TOP_K,
                "evidence_k": EVIDENCE_K,
                "text_trunc": TEXT_TRUNC,
                "metadata_filters_applied": [],
                "dense_channel": "BAAI/bge-m3 cosine (task74 dense_index)",
                "normalization": "BM25Index internal expand_query_text",
                "normalized_tokens": list(norm_tokens),
                "fill_count": 0,
                "source_channel_matches": [],
            },
            "results": results_out,
            "canonical_contract": {
                "n_results": len(results_out),
                "all_valid": all(r["contract_valid"] for r in results_out),
            },
            "evidence_context": {
                "n_items": mb["n_evidence_items"],
                "text": block,
                "sha256": mb["context_sha256"],
                "source_cards": [
                    t69.render_card(s, cards)
                    for s in dict.fromkeys(r["source_id"] for r in results_out[:EVIDENCE_K])
                    if t69.render_card(s, cards)
                ],
            },
            "retrieval_metrics": {},
        })
        per_case.append({
            "example_id": eid,
            "category": case["category"],
            "language": case["language"],
            "query": query,
            "metadata_filters_applied": [],
            "retrieval_mode": "RRF(BM25 full, dense full) k=20",
            "expected_source": esrc,
            "expected_units": eunits,
            "source_first_rank": first,
            "source_hit_at_1": first is not None and first <= 1,
            "source_hit_at_5": first is not None and first <= 5,
            "source_hit_at_10": first is not None and first <= 10,
            "source_reciprocal_rank": (1.0 / first) if first else 0.0,
            "unit_hit_rank": uhit,
            "unit_hit_at_10": uhit is not None and uhit <= 10,
            "unit_reciprocal_rank": (1.0 / uhit) if uhit else 0.0,
            "expected_source_found": bool(src_hits),
            "top1_metadata_agrees_with_expected_source": bool(
                src_hits and results_out[0]["source_id"] == esrc),
            "evidence_answer_score": mb["evidence_answer_score"],
            "evidence_forbidden_hits": mb["evidence_forbidden_hits"],
            "fill_count": 0,
            "source_channel_matches": [],
            "n_results": len(results_out),
            "context_sha256": mb["context_sha256"],
            "context_chars": mb["context_chars"],
        })
        evidence_rows[-1]["retrieval_metrics"] = per_case[-1]
        if (idx + 1) % 10 == 0:
            log(f"  cases {idx+1}/47")

    src = [p for p in per_case if p["expected_source"]]
    unit = [p for p in per_case if p["expected_units"]]
    src_first = [p["source_first_rank"] for p in src]
    unit_hit = [p["unit_hit_rank"] for p in unit]
    scored = [p["evidence_answer_score"] for p in per_case
              if p["evidence_answer_score"] is not None]
    agg = {
        "n_source_level": len(src),
        "source_recall_at_5": t72.recall(src_first, 5),
        "source_recall_at_10": t72.recall(src_first, 10),
        "source_mrr": t72.mrr(src_first),
        "source_zero_hit_cases": [p["example_id"] for p in src
                                  if p["source_first_rank"] is None],
        "n_unit_labeled": len(unit),
        "unit_recall_at_5": t72.recall(unit_hit, 5),
        "unit_recall_at_10": t72.recall(unit_hit, 10),
        "unit_mrr": t72.mrr(unit_hit),
        "evidence_ceiling_mean": (
            round(sum(scored) / len(scored), 4) if scored else None),
        "evidence_ceiling_full": sum(1 for s in scored if s == 1.0),
        "ev0_count": sum(1 for s in scored if s == 0.0),
        "ev0_cases": [p["example_id"] for p in per_case
                      if p["evidence_answer_score"] == 0.0],
        "abstention_forbidden_hits": sum(
            1 for p in per_case if p["evidence_forbidden_hits"]),
        "contract_violations": len(violations_total),
        "context_chars": {
            "median": int(np.median([p["context_chars"] for p in per_case])),
            "mean": round(float(np.mean([p["context_chars"] for p in per_case])), 1),
            "max": max(p["context_chars"] for p in per_case),
        },
    }

    mismatches = []
    for key, want in EXPECTED.items():
        if agg.get(key) != want:
            mismatches.append(f"{key}: got {agg.get(key)} want {want}")
    if mismatches:
        print("STOP: H3_RRF20 reproduction mismatch — " + "; ".join(mismatches))
        return 3
    log(f"H3_RRF20 reproduction PASS {EXPECTED}")

    OUT_EVIDENCE.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in evidence_rows),
        encoding="utf-8")
    OUT_PROMPTS.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in prompt_rows),
        encoding="utf-8")
    OUT_METRICS.write_text(json.dumps({
        "task": "TASK 75 — H3_RRF20 governed RAG evidence (RRF k=20)",
        "frozen_sha256": FROZEN_SHA,
        "corpus": {"path": str(CORPUS_PATH.relative_to(REPO)),
                   "n_docs": len(docs)},
        "config": {"top_k": TOP_K, "evidence_k": EVIDENCE_K,
                   "text_trunc": TEXT_TRUNC, "rrf_k": RRF_K,
                   "bm25": {"k1": 1.5, "b": 0.75},
                   "dense": "BAAI/bge-m3 (task74 dense_index, sha-verified)"},
        "task74_reproduction_gate": {
            "expected": EXPECTED, "observed": {
                k: agg[k] for k in EXPECTED}, "result": "PASS"},
        "aggregate": agg,
        "per_case": per_case,
        "runtime_seconds": round(time.time() - t0, 1),
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    log(f"wrote {OUT_EVIDENCE.name} ({len(evidence_rows)}), "
        f"{OUT_PROMPTS.name} ({len(prompt_rows)}), {OUT_METRICS.name}")
    log(f"unit@5={agg['unit_recall_at_5']} src@5={agg['source_recall_at_5']} "
        f"ceiling={agg['evidence_ceiling_mean']} ev0={agg['ev0_count']} "
        f"in {time.time()-t0:.1f}s")
    print("TASK 75 BUILD EVIDENCE DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

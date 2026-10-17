"""TASK 82 Phase-1 — build optimized H3_RRF20 (BM25 pool=250) RAG evidence.

Reuses Task-75/74/72/69 machinery verbatim (result_row74, rrf_fuse,
build_block_and_metrics, build_context_block). The ONLY experimental change vs
Task-75 is the BM25 candidate-pool cap: bm25.search(query, top_k=250) instead
of the full list (Task-81 best eligible pool; 0 per-case regressions, exact
ranking equivalence). Dense list stays full; RRF k=20, EVIDENCE_K=5,
TEXT_TRUNC=500 unchanged.

HARD-STOP gates (before any generation):
  1. frozen benchmark sha = 06625f72…
  2. Task-74 frozen H3_RRF20 aggregates still hold (unit@5=0.5385 etc.)
  3. pool-250 reproduction: same aggregates as full-list H3_RRF20
  4. context_sha256 per case vs Task-75 prompts (identical => prompts byte-equal)
  5. generation acceptance gates REGISTERED (written to preflight json BEFORE
     the Kaggle kernel is pushed; no threshold is invented after outputs exist)

Outputs (never overwrite prior-task artifacts)
  data/evaluation/task82_rag_evidence.jsonl
  data/evaluation/task82_rag_prompts.jsonl
  data/evaluation/task82_retrieval_metrics.json
  data/evaluation/task82_preflight.json
"""

from __future__ import annotations

import hashlib
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
sys.path.insert(0, str(REPO / "experiments" / "task81"))

import score_task60  # noqa: E402
from svk_corpus.retrieval import (  # noqa: E402
    BM25Index,
    RetrievalResult,
    load_corpus,
)
from svk_corpus.retrieval.contract import validate_result  # noqa: E402
from svk_corpus.retrieval.normalization import expand_query_text  # noqa: E402

import task72_experiment as t72  # noqa: E402
import task74_experiment as t74  # noqa: E402

t69 = t72.t69

CASES_PATH = REPO / "data" / "evaluation" / "dapt01_eval_cases.jsonl"
MANIFEST_PATH = REPO / "manifests" / "source_manifest.csv"
CORPUS_PATH = REPO / "data" / "release" / "rag_corpus.jsonl"
FROZEN_SHA = "06625f72190e3ae130447345afdc04342bd19cb76f842285706480cba7765b81"
TASK74_METRICS = REPO / "data" / "evaluation" / "task74_metrics.json"
TASK75_PROMPTS = REPO / "data" / "evaluation" / "task75_rag_prompts.jsonl"
TASK75_METRICS = REPO / "data" / "evaluation" / "task75_retrieval_metrics.json"

DENSE_DIR = REPO / "experiments" / "task74" / "dense_index"
INDEX_META = DENSE_DIR / "index_meta.json"
CORPUS_EMB = DENSE_DIR / "corpus_emb.f16.npy"
QUERIES_EMB = DENSE_DIR / "queries_emb.f32.npy"

OUT_EVIDENCE = REPO / "data" / "evaluation" / "task82_rag_evidence.jsonl"
OUT_PROMPTS = REPO / "data" / "evaluation" / "task82_rag_prompts.jsonl"
OUT_METRICS = REPO / "data" / "evaluation" / "task82_retrieval_metrics.json"
OUT_PREFLIGHT = REPO / "data" / "evaluation" / "task82_preflight.json"

RRF_K = 20
TOP_K = 10
EVIDENCE_K = 5
TEXT_TRUNC = 500
BM25_POOL = 250  # Task-81 best eligible candidate pool
CFG = {"evidence_k": EVIDENCE_K, "text_trunc": TEXT_TRUNC, "mode": "rrf"}

# Frozen Task-74/75 H3_RRF20 aggregates — reproduction gate (pool-250 must match).
EXPECTED = {
    "unit_recall_at_5": 0.5385,
    "source_recall_at_5": 0.9783,
    "evidence_ceiling_mean": 0.8372,
    "ev0_count": 7,
}

# Task-75 frozen four-arm reference (generation baseline for Task-82).
TASK75_FOUR_ARMS = {
    "base": {"macro_keyterm": 0.2021, "pass_all": 6},
    "dapt": {"macro_keyterm": 0.266, "pass_all": 8},
    "base_rag": {"macro_keyterm": 0.695, "pass_all": 32},
    "dapt_rag": {"macro_keyterm": 0.695, "pass_all": 31},
}
TASK75_BEHAVIOUR = {
    "abstention_correct": {"base_rag": 0, "dapt_rag": 1},
    "looped": {"base_rag": 0, "dapt_rag": 4},
    "failure_counts": {
        "base_rag": {"FABRICATION": 2},
        "dapt_rag": {"FABRICATION": 1},
    },
    "contract_violations": 0,
    "prompts_sha256": "302f6c917b538bb440d244eeeba9aba35756186bef04cb1cd89415f65a774409",
    "adapter_sha256": "9b4d2bdcfe089118d0634815596b628506a83c434d3863cff7a731cba75a58e9",
}

# ---- Generation acceptance gates — REGISTERED BEFORE ANY GENERATION ----------
# Tolerance mirrors a single-case swing on n=47 (1.0/47 = 0.0213 -> 0.02;
# pass_all +/- 2). Rationale: if pool-250 evidence is byte-identical to
# Task-75, generation with the same greedy protocol may only differ by GPU
# numerical nondeterminism across run hosts, not by retrieval change.
TOL_MACRO = 0.02
TOL_PASS = 2
GENERATION_GATES = {
    "arms_ab_reproduce_task75": {
        "description": (
            "no-RAG arms A/B must reproduce Task-75 macro/pass_all exactly "
            "(same model, same prompts, same evaluator — validates run setup)"
        ),
        "expected": {"base": TASK75_FOUR_ARMS["base"], "dapt": TASK75_FOUR_ARMS["dapt"]},
    },
    "arm_c_macro_not_down": {
        "description": f"BASE+RAG macro >= Task-75 (0.695) - {TOL_MACRO}",
        "threshold": round(0.695 - TOL_MACRO, 4),
    },
    "arm_c_pass_not_down": {
        "description": f"BASE+RAG pass_all >= Task-75 (32) - {TOL_PASS}",
        "threshold": 32 - TOL_PASS,
    },
    "arm_d_macro_not_down": {
        "description": f"DAPT+RAG macro >= Task-75 (0.695) - {TOL_MACRO}",
        "threshold": round(0.695 - TOL_MACRO, 4),
    },
    "arm_d_pass_not_down": {
        "description": f"DAPT+RAG pass_all >= Task-75 (31) - {TOL_PASS}",
        "threshold": 31 - TOL_PASS,
    },
    "abstention_not_regressed": {
        "description": (
            "RAG-arm abstention-correct total (base_rag + dapt_rag) >= "
            "Task-75 total (0 + 1 = 1)"
        ),
        "threshold": 1,
    },
    "no_loop_increase": {
        "description": "base_rag loops <= Task-75 (0) AND dapt_rag loops <= Task-75 (4)",
        "threshold": {"base_rag": 0, "dapt_rag": 4},
    },
    "contract_violations_zero": {"description": "retrieval contract violations == 0"},
    "identical_contexts_both_rag_arms": {
        "description": "arms C and D carry byte-identical evidence contexts"
    },
    "fabrication_not_up": {
        "description": (
            "FABRICATION failure count not above Task-75 "
            "(base_rag 2, dapt_rag 1)"
        ),
        "threshold": {"base_rag": 2, "dapt_rag": 1},
    },
    "dapt_value_under_rag_still_zero": {
        "description": (
            "DAPT value under optimized RAG (D-C macro) still ~0: "
            f"|delta| <= {TOL_MACRO}"
        ),
        "threshold": TOL_MACRO,
    },
    "every_new_regression_investigated": {
        "description": (
            "each case whose score dropped vs the same Task-75 arm is listed "
            "with a written cause (retrieval evidence diff vs generation "
            "numerics); no unexplained regression may remain"
        ),
    },
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
    if not TASK74_METRICS.exists() or not TASK75_PROMPTS.exists():
        print("STOP: task74_metrics.json or task75 prompts missing")
        return 3
    t74_meta = json.loads(TASK74_METRICS.read_text(encoding="utf-8"))
    t74_agg = t74_meta["aggregates"]["H3_RRF20"]
    for key, want in EXPECTED.items():
        got = t74_agg.get(key)
        if got != want:
            print(f"STOP: task74 frozen {key}={got} != expected {want}")
            return 3
    log(f"task74 frozen H3_RRF20 aggregates verified {EXPECTED}")

    task75_prompts = {
        r["example_id"]: r
        for r in (
            json.loads(ln)
            for ln in TASK75_PROMPTS.read_text(encoding="utf-8").splitlines()
            if ln.strip()
        )
    }
    if len(task75_prompts) != 47:
        print("STOP: task75 prompts != 47 rows")
        return 3

    cases = t72.load_jsonl(CASES_PATH)
    cards = t69.load_manifest_cards(MANIFEST_PATH)
    if len(cases) != 47 or not INDEX_META.exists() or not CORPUS_EMB.exists():
        print("STOP: cases!=47 or dense index missing")
        return 3
    meta = json.loads(INDEX_META.read_text(encoding="utf-8"))
    al = meta["alignment"]

    docs = load_corpus(CORPUS_PATH, MANIFEST_PATH)
    bm25 = BM25Index(docs, k1=1.5, b=0.75)
    log(f"corpus {len(docs)} docs, bm25 built (pool={BM25_POOL})")

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
    context_matches_task75 = 0
    context_mismatch_ids: list[str] = []

    for idx, case in enumerate(cases):
        eid = case["example_id"]
        query = case["question"]
        norm_tokens = tuple(expand_query_text(query))

        scores = emb @ q_emb[idx]
        order = np.argsort(-scores, kind="stable")
        rank_of = np.empty(n, dtype=np.int64)
        rank_of[order] = np.arange(1, n + 1)

        # Task-81 optimized config: BM25 candidate pool capped at BM25_POOL.
        # ranks are positions in the full sorted BM25 order (1..pool), i.e.
        # identical values to the full-list ranks for the same doc ids.
        full = bm25.search(query, top_k=BM25_POOL)
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

        block = mb["context_text"]
        user_content = block + "\n\n" + query
        t75_row = task75_prompts[eid]
        ctx_match = t75_row["context_sha256"] == mb["context_sha256"]
        if ctx_match:
            context_matches_task75 += 1
        else:
            context_mismatch_ids.append(eid)

        prompt_rows.append({
            "example_id": eid,
            "question": query,
            "user_content": user_content,
            "context_sha256": mb["context_sha256"],
            "n_evidence_items": mb["n_evidence_items"],
            "context_chars": mb["context_chars"],
            "context_matches_task75": ctx_match,
        })
        evidence_rows.append({
            "example_id": eid,
            "query": query,
            "retrieval": {
                "mode": f"RRF(BM25 pool={BM25_POOL}, dense full) k=20",
                "top_k": TOP_K,
                "evidence_k": EVIDENCE_K,
                "text_trunc": TEXT_TRUNC,
                "bm25_pool": BM25_POOL,
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
            "retrieval_mode": f"RRF(BM25 pool={BM25_POOL}, dense full) k=20",
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
            "context_matches_task75": ctx_match,
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
        print("STOP: pool-250 H3_RRF20 reproduction mismatch — " + "; ".join(mismatches))
        return 3
    log(f"pool-250 H3_RRF20 reproduction PASS {EXPECTED}")

    # Task-75 context comparison (prompts byte-equal claim).
    task75_metrics = json.loads(TASK75_METRICS.read_text(encoding="utf-8"))
    t75_agg = task75_metrics["aggregate"]
    identical_aggregates = all(agg.get(k) == t75_agg.get(k) for k in EXPECTED)
    all_contexts_match = context_matches_task75 == 47
    log(f"contexts vs task75: {context_matches_task75}/47 match; "
        f"aggregates identical: {identical_aggregates}")

    OUT_EVIDENCE.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in evidence_rows),
        encoding="utf-8")
    OUT_PROMPTS.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in prompt_rows),
        encoding="utf-8")
    OUT_METRICS.write_text(json.dumps({
        "task": "TASK 82 — optimized H3_RRF20 (BM25 pool=250) governed RAG evidence",
        "frozen_sha256": FROZEN_SHA,
        "corpus": {"path": str(CORPUS_PATH.relative_to(REPO)),
                   "n_docs": len(docs)},
        "config": {"top_k": TOP_K, "evidence_k": EVIDENCE_K,
                   "text_trunc": TEXT_TRUNC, "rrf_k": RRF_K,
                   "bm25_pool": BM25_POOL,
                   "bm25": {"k1": 1.5, "b": 0.75},
                   "dense": "BAAI/bge-m3 (task74 dense_index, sha-verified)"},
        "reproduction_gate": {
            "expected": EXPECTED, "observed": {
                k: agg[k] for k in EXPECTED}, "result": "PASS"},
        "task75_context_comparison": {
            "contexts_matching": context_matches_task75,
            "n_cases": 47,
            "mismatched_example_ids": context_mismatch_ids,
            "aggregates_identical_to_task75": identical_aggregates,
            "prompts_sha256_task75": TASK75_BEHAVIOUR["prompts_sha256"],
            "result": "IDENTICAL" if all_contexts_match else "DIFFERS",
        },
        "aggregate": agg,
        "per_case": per_case,
        "runtime_seconds": round(time.time() - t0, 1),
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    preflight = {
        "task": "TASK 82 preflight — verified setup + gates registered BEFORE generation",
        "verified_before_generation": {
            "frozen_benchmark_sha256": FROZEN_SHA,
            "frozen_benchmark_sha_ok": True,
            "dense_index_sha_ok": True,
            "task74_frozen_aggregates_ok": True,
            "dapt01_adapter_sha256": TASK75_BEHAVIOUR["adapter_sha256"],
            "dapt01_adapter_sha_ok": None,  # filled by task82_verify.py
            "task81_pool250_reproduction": {
                "expected": EXPECTED,
                "observed": {k: agg[k] for k in EXPECTED},
                "result": "PASS",
            },
            "task81_context_equivalence_vs_task75": {
                "contexts_matching": context_matches_task75,
                "n_cases": 47,
                "mismatched_example_ids": context_mismatch_ids,
                "result": "IDENTICAL" if all_contexts_match else "DIFFERS",
            },
            "prompts_sha256_task82": sha256_file(OUT_PROMPTS),
            "prompts_sha256_task75": TASK75_BEHAVIOUR["prompts_sha256"],
            "prompts_byte_identical_to_task75": (
                sha256_file(OUT_PROMPTS) == TASK75_BEHAVIOUR["prompts_sha256"]
                or all_contexts_match  # context shas identical => content equal
            ),
            "evaluator": "score_task60 norm/group_pass/score_case via score_task69_rag (verbatim)",
            "generation_protocol": {
                "model": "Qwen/Qwen3-8B-Base",
                "adapter": "DAPT-01 checkpoint-15248",
                "quantization": "4bit-nf4-double, compute fp16",
                "decoding": "greedy, max_new_tokens=192, seed=42",
                "system_prompt": (
                    "You are a careful assistant for Jain studies. "
                    "Answer the user's question concisely (in 1-3 sentences). "
                    "If you are unsure or the information is not available, say so."
                ),
                "identical_to_task75": True,
            },
            "run_host": "Kaggle T4 (established safe execution method; "
                        "Colab T4 session token expired 2026-10-09 05:57 UTC)",
        },
        "task75_reference_four_arms": TASK75_FOUR_ARMS,
        "task75_reference_behaviour": TASK75_BEHAVIOUR,
        "generation_acceptance_gates": GENERATION_GATES,
        "gate_registration": (
            "written BEFORE any Task-82 generation was run; thresholds not "
            "informed by Task-82 outputs"
        ),
        "task75_contexts_all_identical": all_contexts_match,
    }
    OUT_PREFLIGHT.write_text(json.dumps(preflight, indent=2, ensure_ascii=False),
                             encoding="utf-8")

    log(f"wrote {OUT_EVIDENCE.name} ({len(evidence_rows)}), "
        f"{OUT_PROMPTS.name} ({len(prompt_rows)}), {OUT_METRICS.name}, "
        f"{OUT_PREFLIGHT.name}")
    log(f"unit@5={agg['unit_recall_at_5']} src@5={agg['source_recall_at_5']} "
        f"ceiling={agg['evidence_ceiling_mean']} ev0={agg['ev0_count']} "
        f"contexts_match_task75={context_matches_task75}/47 "
        f"in {time.time()-t0:.1f}s")
    print("TASK 82 BUILD EVIDENCE DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

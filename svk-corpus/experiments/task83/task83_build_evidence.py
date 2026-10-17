"""TASK 83 Phase-1 — targeted evidence-composition mini-gate (P500 / P1000).

Reuses the exact Task-81/82 retrieval implementation (bm25.search(query,
top_k=pool), t74.rrf_fuse, t72.build_block_and_metrics; RRF k=20, dense list
full, EVIDENCE_K=5, TEXT_TRUNC=500, deterministic stable tie-breaking). The
ONLY experimental change vs Task-75 PFULL is the BM25 candidate-pool cap:
pool=500 and pool=1000 (Task-82's pool=250 and Task-75's full list are the
recorded reference configurations; no rebuild).

HARD-STOP checks (before any generation):
  1. frozen benchmark sha = 06625f72…
  2. dense index alignment + task74 frozen H3_RRF20 aggregates
  3. DAPT-01 adapter sha = 9b4d2bdc…
  4. the 12 Task-82 differing cases recovered byte-exactly from recorded
     task75/task82 prompts; case 037 contexts + outputs recovered
  5. mini-gate acceptance criteria REGISTERED in task83_preflight.json
     BEFORE the Kaggle kernel is pushed (no threshold invented after outputs)

Outputs (never overwrite prior-task artifacts)
  data/evaluation/task83_rag_evidence_p500.jsonl
  data/evaluation/task83_rag_evidence_p1000.jsonl
  data/evaluation/task83_rag_prompts_p500.jsonl
  data/evaluation/task83_rag_prompts_p1000.jsonl
  data/evaluation/task83_retrieval_metrics_p500.json
  data/evaluation/task83_retrieval_metrics_p1000.json
  data/evaluation/task83_kernel_payload.json      (embedded into the kernel)
  data/evaluation/task83_case037_evidence.json    (4-config 5th-item comparison)
  data/evaluation/task83_preflight.json           (gates registered pre-gen)
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

import score_task60  # noqa: E402
from svk_corpus.retrieval import (  # noqa: E402
    BM25Index,
    RetrievalResult,
    load_corpus,
)
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
TASK82_PROMPTS = REPO / "data" / "evaluation" / "task82_rag_prompts.jsonl"
TASK82_PREFLIGHT = REPO / "data" / "evaluation" / "task82_preflight.json"
ADAPTER_PATH = Path("/tmp/opencode/task75/adapter_model.safetensors")
ADAPTER_SHA = "9b4d2bdcfe089118d0634815596b628506a83c434d3863cff7a731cba75a58e9"

DENSE_DIR = REPO / "experiments" / "task74" / "dense_index"
INDEX_META = DENSE_DIR / "index_meta.json"
CORPUS_EMB = DENSE_DIR / "corpus_emb.f16.npy"
QUERIES_EMB = DENSE_DIR / "queries_emb.f32.npy"

POOLS = (500, 1000)
PRIORITY_CASE = "DAPT01EVAL-037"
T82_DIFF_IDS = [
    "DAPT01EVAL-001", "DAPT01EVAL-007", "DAPT01EVAL-010", "DAPT01EVAL-011",
    "DAPT01EVAL-012", "DAPT01EVAL-013", "DAPT01EVAL-017", "DAPT01EVAL-021",
    "DAPT01EVAL-033", "DAPT01EVAL-034", "DAPT01EVAL-037", "DAPT01EVAL-039",
]
T75_037_CTX_SHA = "9b28cfb693c1d7d30a78dda0a106b845d07b28a1f4ae43dda599afb46a941f4e"
T82_037_CTX_SHA = "f5035285236ccc7d92c8912ed358955b3386e64f2149f48040d6297a688cd5c6"

RRF_K = 20
TOP_K = 10
EVIDENCE_K = 5
TEXT_TRUNC = 500
CFG = {"evidence_k": EVIDENCE_K, "text_trunc": TEXT_TRUNC, "mode": "rrf"}

EXPECTED_FROZEN = {
    "unit_recall_at_5": 0.5385,
    "source_recall_at_5": 0.9783,
    "evidence_ceiling_mean": 0.8372,
    "ev0_count": 7,
}

# Task-82 registered gates (recovered verbatim; the mini-gate maps onto them).
TASK82_GATES = {
    "arm_c_macro_not_down": {"threshold": 0.675},
    "arm_c_pass_not_down": {"threshold": 30},
    "arm_d_macro_not_down": {"threshold": 0.675},
    "arm_d_pass_not_down": {"threshold": 29},
    "abstention_not_regressed": {"threshold": 1},
    "no_loop_increase": {"threshold": {"base_rag": 0, "dapt_rag": 4}},
    "contract_violations_zero": {"threshold": 0},
    "identical_contexts_both_rag_arms": {"threshold": True},
    "fabrication_not_up": {"threshold": {"base_rag": 2, "dapt_rag": 1}},
    "dapt_value_under_rag_still_zero": {"threshold": 0.02},
    "every_new_regression_investigated": {"threshold": None},
}

# ---- Mini-gate acceptance criteria — REGISTERED BEFORE ANY GENERATION --------
# Thresholds are either (a) recovered Task-82 registered values applied to the
# PROJECTED full-47 (candidate fresh scores on differing cases + recorded
# Task-75 scores elsewhere, valid because non-differing contexts are
# byte-identical to Task-75), or (b) the recorded Task-75 outcome for the
# specific case/subset (reference-derived, never from new outputs).
TOL_MACRO = 0.02
MINI_GATES = {
    "case037_context_restored": {
        "description": (
            "DAPT01EVAL-037 evidence context sha equals the Task-75 full-list "
            f"sha {T75_037_CTX_SHA[:16]}… (the SVK-1005:u02684 fifth item returns)"
        ),
        "expected_sha": T75_037_CTX_SHA,
    },
    "all_12_contexts_restored": {
        "description": (
            "every one of the 12 Task-82 differing cases has evidence context "
            "sha identical to the Task-75 full-list reference"
        ),
        "threshold": 12,
    },
    "case037_dapt_outcome_restored": {
        "description": (
            "DAPT arm on 037 reproduces the Task-75 outcome: score 1.0, "
            "abstention_correct=true, failure class ABSTENTION_CORRECT "
            "(no GENERATION_FABRICATION)"
        ),
        "expected_score": 1.0,
    },
    "case037_base_outcome_preserved": {
        "description": (
            "BASE arm on 037 score equals the Task-75 Task-82-stable value 0.0 "
            "(byte-identical answer history; no fabrication flag introduced)"
        ),
        "expected_score": 0.0,
    },
    "projected_base_rag_macro_not_down": {
        "description": (
            "PROJECTED full-47 BASE+RAG macro >= Task-75 (0.695) - 0.02 "
            "(Task-82 gate arm_c_macro_not_down)"
        ),
        "threshold": 0.675,
    },
    "projected_base_rag_pass_not_down": {
        "description": "PROJECTED full-47 BASE+RAG pass_all >= 30 (Task-82 gate)",
        "threshold": 30,
    },
    "projected_dapt_rag_macro_not_down": {
        "description": (
            "PROJECTED full-47 DAPT+RAG macro >= Task-75 (0.695) - 0.02 "
            "(Task-82 gate arm_d_macro_not_down — the gate that FAILED at pool=250)"
        ),
        "threshold": 0.675,
    },
    "projected_dapt_rag_pass_not_down": {
        "description": "PROJECTED full-47 DAPT+RAG pass_all >= 29 (Task-82 gate)",
        "threshold": 29,
    },
    "projected_abstention_not_regressed": {
        "description": (
            "PROJECTED RAG-arm abstention-correct total >= Task-75 total 1 "
            "(Task-82 gate abstention_not_regressed)"
        ),
        "threshold": 1,
    },
    "projected_no_loop_increase": {
        "description": (
            "PROJECTED loops: base_rag <= 0 AND dapt_rag <= 4 (Task-82 gate)"
        ),
        "threshold": {"base_rag": 0, "dapt_rag": 4},
    },
    "projected_fabrication_not_up": {
        "description": (
            "PROJECTED GENERATION_FABRICATION counts: base_rag <= 2 AND "
            "dapt_rag <= 1 (Task-82 gate fabrication_not_up, keyed by the "
            "evaluator's GENERATION_FABRICATION class)"
        ),
        "threshold": {"base_rag": 2, "dapt_rag": 1},
    },
    "projected_dapt_value_under_rag_still_zero": {
        "description": (
            "PROJECTED |D-C macro| <= 0.02 (Task-82 gate dapt_value_under_rag_still_zero)"
        ),
        "threshold": TOL_MACRO,
    },
    "contract_violations_zero": {
        "description": "retrieval contract violations == 0 (Task-82 gate)",
        "threshold": 0,
    },
    "identical_contexts_both_rag_arms": {
        "description": (
            "BASE and DAPT arms carry byte-identical evidence contexts per case "
            "(Task-82 gate; enforced by construction — one context per config)"
        ),
    },
    "attribution_not_worse_on_12": {
        "description": (
            "on the 12-case subset, per arm, counts of cited_evidence_author and "
            "cited_attribution_word are >= the recorded Task-75 subset counts "
            "(reference-derived; no attribution behaviour may be lost)"
        ),
    },
    "sect_term_counts_not_up_on_12": {
        "description": (
            "on the 12-case subset, per arm and per sect term "
            "(sthanakvasi|digambara|shvetambara|agam), mechanical occurrence "
            "counts in answers are <= recorded Task-75 subset counts "
            "(reference-derived; no new sect confusion)"
        ),
    },
    "every_new_regression_investigated": {
        "description": (
            "each case whose projected score drops vs the same Task-75 arm is "
            "listed with a written cause; no unexplained regression may remain "
            "(Task-82 gate)"
        ),
    },
}


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(ln)
        for ln in path.read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]


def classify_diff(ctx_a: str, ids_a: list[str], ctx_b: str, ids_b: list[str]) -> str:
    """Characterise how config-A context differs from reference-B."""
    if ctx_a == ctx_b:
        return "identical"
    if ids_a == ids_b:
        # same ids and order: header/score/channel lines must differ
        return "channel_header_only"
    if sorted(ids_a) == sorted(ids_b):
        return "reorder_same_set"
    overlap = len(set(ids_a) & set(ids_b))
    if overlap == len(ids_a) - 1 == len(ids_b) - 1:
        return "one_item_swap"
    return f"other_overlap_{overlap}"


def item_ids(context_text: str) -> list[str]:
    """Top-5 evidence item ids from a context block (lines 'N. <text_id>:...')."""
    ids: list[str] = []
    for ln in context_text.splitlines():
        if ln[:2].rstrip(".").isdigit() and ". " in ln[:5]:
            ident = ln.split(". ", 1)[1].split(" | ", 1)[0].strip()
            ids.append(ident)
        if ln.startswith("[source-metadata card]"):
            break
    return ids


def build_config(
    pool: int,
    cases: list[dict],
    docs,
    bm25,
    emb,
    q_emb,
    tid2idx,
    cards,
    task75_prompts: dict,
    task82_prompts: dict,
) -> tuple[list[dict], list[dict], list[dict], dict]:
    """Build evidence+prompts+metrics rows for one BM25 pool over all 47 cases."""
    n = emb.shape[0]
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

        full = bm25.search(query, top_k=pool)
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
        t75_sha = task75_prompts[eid]["context_sha256"]
        t82_sha = task82_prompts[eid]["context_sha256"]
        ids = item_ids(block)
        ctx_match_t75 = mb["context_sha256"] == t75_sha

        prompt_rows.append({
            "example_id": eid,
            "question": query,
            "user_content": user_content,
            "context_sha256": mb["context_sha256"],
            "n_evidence_items": mb["n_evidence_items"],
            "context_chars": mb["context_chars"],
            "context_matches_task75": ctx_match_t75,
        })
        evidence_rows.append({
            "example_id": eid,
            "query": query,
            "retrieval": {
                "mode": f"RRF(BM25 pool={pool}, dense full) k=20",
                "top_k": TOP_K,
                "evidence_k": EVIDENCE_K,
                "text_trunc": TEXT_TRUNC,
                "bm25_pool": pool,
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
            "retrieval_mode": f"RRF(BM25 pool={pool}, dense full) k=20",
            "expected_source": esrc,
            "expected_units": eunits,
            "source_first_rank": first,
            "source_hit_at_5": first is not None and first <= 5,
            "unit_hit_rank": uhit,
            "unit_hit_at_10": uhit is not None and uhit <= 10,
            "expected_source_found": bool(src_hits),
            "evidence_answer_score": mb["evidence_answer_score"],
            "evidence_forbidden_hits": mb["evidence_forbidden_hits"],
            "fill_count": 0,
            "n_results": len(results_out),
            "context_sha256": mb["context_sha256"],
            "context_chars": mb["context_chars"],
            "context_matches_task75": ctx_match_t75,
            "diff_vs_task75": classify_diff(
                block, ids,
                task75_prompts[eid]["user_content"].split("\n\n")[0],
                item_ids(task75_prompts[eid]["user_content"].split("\n\n")[0]),
            ),
            "diff_vs_task82": classify_diff(
                block, ids,
                task82_prompts[eid]["user_content"].split("\n\n")[0],
                item_ids(task82_prompts[eid]["user_content"].split("\n\n")[0]),
            ),
            "item_ids": ids,
        })
        evidence_rows[-1]["retrieval_metrics"] = per_case[-1]
        if (idx + 1) % 20 == 0:
            log(f"  pool={pool} cases {idx+1}/47")

    src = [p for p in per_case if p["expected_source"]]
    unit = [p for p in per_case if p["expected_units"]]
    src_first = [p["source_first_rank"] for p in src]
    unit_hit = [p["unit_hit_rank"] for p in unit]
    scored = [p["evidence_answer_score"] for p in per_case
              if p["evidence_answer_score"] is not None]
    agg = {
        "unit_recall_at_5": t72.recall(unit_hit, 5),
        "source_recall_at_5": t72.recall(src_first, 5),
        "evidence_ceiling_mean": (
            round(sum(scored) / len(scored), 4) if scored else None),
        "ev0_count": sum(1 for s in scored if s == 0.0),
        "contexts_matching_task75": sum(
            1 for p in per_case if p["context_matches_task75"]),
        "contract_violations": len(violations_total),
    }
    diff_t75 = [p["example_id"] for p in per_case
                if not p["context_matches_task75"]]
    kinds: dict[str, int] = {}
    for p in per_case:
        kinds[p["diff_vs_task75"]] = kinds.get(p["diff_vs_task75"], 0) + 1
    summary = {
        "pool": pool,
        "aggregate": agg,
        "diff_vs_task75": diff_t75,
        "diff_vs_task75_n": len(diff_t75),
        "diff_kinds_vs_task75": kinds,
        "identical_to_task82_n": sum(
            1 for p in per_case if p["diff_vs_task82"] == "identical"),
    }
    return evidence_rows, prompt_rows, per_case, summary


def main() -> int:
    t0 = time.time()
    # --- HARD STOP checks ---------------------------------------------------
    if sha256_file(CASES_PATH) != FROZEN_SHA:
        print("STOP: frozen benchmark sha mismatch")
        return 3
    if not ADAPTER_PATH.exists() or sha256_file(ADAPTER_PATH) != ADAPTER_SHA:
        print("STOP: DAPT-01 adapter missing or sha mismatch")
        return 3
    t74_meta = json.loads(TASK74_METRICS.read_text(encoding="utf-8"))
    t74_agg = t74_meta["aggregates"]["H3_RRF20"]
    for key, want in EXPECTED_FROZEN.items():
        if t74_agg.get(key) != want:
            print(f"STOP: task74 frozen {key}={t74_agg.get(key)} != {want}")
            return 3
    log(f"frozen bench + adapter ({ADAPTER_SHA[:16]}…) + task74 aggregates verified")

    task75_prompts = {r["example_id"]: r for r in load_jsonl(TASK75_PROMPTS)}
    task82_prompts = {r["example_id"]: r for r in load_jsonl(TASK82_PROMPTS)}
    t82_preflight = json.loads(TASK82_PREFLIGHT.read_text(encoding="utf-8"))
    recovered_12 = [
        c["example_id"]
        for c in t82_preflight["task81_context_equivalence_vs_task75_breakdown"]["cases"]
    ]
    if recovered_12 != T82_DIFF_IDS:
        print(f"STOP: 12-case list mismatch {recovered_12}")
        return 3
    # byte-exact recovery of the 037 reference contexts
    if task75_prompts[PRIORITY_CASE]["context_sha256"] != T75_037_CTX_SHA:
        print("STOP: task75 037 context sha mismatch")
        return 3
    if task82_prompts[PRIORITY_CASE]["context_sha256"] != T82_037_CTX_SHA:
        print("STOP: task82 037 context sha mismatch")
        return 3
    log(f"12-case diff set recovered {T82_DIFF_IDS}")
    log(f"037 contexts recovered (t75 {T75_037_CTX_SHA[:16]}…, "
        f"t82 {T82_037_CTX_SHA[:16]}…)")

    cases = t72.load_jsonl(CASES_PATH)
    cards = t69.load_manifest_cards(MANIFEST_PATH)
    if len(cases) != 47:
        print("STOP: cases != 47")
        return 3
    meta = json.loads(INDEX_META.read_text(encoding="utf-8"))
    al = meta["alignment"]
    docs = load_corpus(CORPUS_PATH, MANIFEST_PATH)
    bm25 = BM25Index(docs, k1=1.5, b=0.75)
    emb = np.load(CORPUS_EMB).astype(np.float32)
    nrm = np.linalg.norm(emb, axis=1, keepdims=True)
    nrm[nrm == 0] = 1.0
    emb /= nrm
    q_emb = np.load(QUERIES_EMB).astype(np.float32)
    qn = np.linalg.norm(q_emb, axis=1, keepdims=True)
    qn[qn == 0] = 1.0
    q_emb /= qn
    tid2idx = {d.text_id: i for i, d in enumerate(docs)}
    text_sha = hashlib.sha256()
    for d in docs:
        text_sha.update(d.search_text.encode("utf-8"))
    if text_sha.hexdigest() != al["corpus_text_sha256"]:
        print("STOP: dense alignment corpus sha mismatch")
        return 3
    log(f"corpus {len(docs)} docs, bm25 + dense index loaded {emb.shape}")

    # --- build P500 / P1000 ------------------------------------------------
    config_summaries: dict[str, dict] = {}
    built: dict[int, tuple[list[dict], list[dict], list[dict]]] = {}
    for pool in POOLS:
        log(f"building pool={pool} evidence for 47 cases…")
        ev, pr, pc, summary = build_config(
            pool, cases, docs, bm25, emb, q_emb, tid2idx, cards,
            task75_prompts, task82_prompts)
        built[pool] = (ev, pr, pc)
        config_summaries[str(pool)] = summary
        (REPO / "data" / "evaluation" / f"task83_rag_evidence_p{pool}.jsonl").write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in ev),
            encoding="utf-8")
        (REPO / "data" / "evaluation" / f"task83_rag_prompts_p{pool}.jsonl").write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in pr),
            encoding="utf-8")
        (REPO / "data" / "evaluation" / f"task83_retrieval_metrics_p{pool}.json").write_text(
            json.dumps({
                "task": f"TASK 83 — H3_RRF20 BM25 pool={pool} governed RAG evidence",
                "frozen_sha256": FROZEN_SHA,
                "config": {"top_k": TOP_K, "evidence_k": EVIDENCE_K,
                           "text_trunc": TEXT_TRUNC, "rrf_k": RRF_K,
                           "bm25_pool": pool,
                           "bm25": {"k1": 1.5, "b": 0.75},
                           "dense": "BAAI/bge-m3 (task74 dense_index, sha-verified)"},
                "aggregate": summary["aggregate"],
                "per_case": pc,
            }, indent=2, ensure_ascii=False), encoding="utf-8")
        log(f"  pool={pool}: contexts matching task75 "
            f"{summary['aggregate']['contexts_matching_task75']}/47, "
            f"diff vs t75 n={summary['diff_vs_task75_n']}, "
            f"kinds={summary['diff_kinds_vs_task75']}, "
            f"unit@5={summary['aggregate']['unit_recall_at_5']} "
            f"ceiling={summary['aggregate']['evidence_ceiling_mean']}")

    # sanity: identical to task82 where both configs agree? (p500 vs p250 is
    # informational — a candidate may recover toward task75, so fewer matches
    # vs task82 is expected when it converges to task75)
    for pool in POOLS:
        log(f"  pool={pool}: identical to task82 contexts for "
            f"{config_summaries[str(pool)]['identical_to_task82_n']}/47")

    # --- generation target set --------------------------------------------
    targets: dict[str, list[str]] = {}
    for pool in POOLS:
        diff = config_summaries[str(pool)]["diff_vs_task75"]
        s = set(diff) | {PRIORITY_CASE}
        targets[f"p{pool}"] = sorted(s)
    union = sorted(set(targets["p500"]) | set(targets["p1000"]))
    log(f"generation targets: p500={len(targets['p500'])} "
        f"p1000={len(targets['p1000'])} union={len(union)}")

    # --- case 037 four-config item comparison ------------------------------
    def items_of(pool_or_ref: str) -> list[dict]:
        if pool_or_ref == "t75":
            ev = {r["example_id"]: r for r in load_jsonl(
                REPO / "data" / "evaluation" / "task75_rag_evidence.jsonl")}
        elif pool_or_ref == "t82":
            ev = {r["example_id"]: r for r in load_jsonl(
                REPO / "data" / "evaluation" / "task82_rag_evidence.jsonl")}
        else:
            pool = int(pool_or_ref)
            ev = {r["example_id"]: r for r in built[pool][0]}
        row = ev[PRIORITY_CASE]
        out = []
        for res in row["results"][:EVIDENCE_K]:
            out.append({
                "text_id": res["text_id"],
                "channel": res["retrieval_channel"],
                "retrieval_rank": res["retrieval_rank"],
                "unit_bm25_rank": res.get("unit_bm25_rank"),
                "score": res["retrieval_score"],
                "title": (res.get("title") or "")[:70],
            })
        return out

    case037 = {
        "example_id": PRIORITY_CASE,
        "question": cases[
            next(i for i, c in enumerate(cases) if c["example_id"] == PRIORITY_CASE)
        ]["question"],
        "configs": {
            "pfull_task75": {
                "context_sha256": task75_prompts[PRIORITY_CASE]["context_sha256"],
                "items": items_of("t75"),
            },
            "p250_task82": {
                "context_sha256": task82_prompts[PRIORITY_CASE]["context_sha256"],
                "items": items_of("t82"),
            },
            "p500": {
                "context_sha256": built[500][1][
                    next(i for i, r in enumerate(built[500][1])
                         if r["example_id"] == PRIORITY_CASE)
                ]["context_sha256"],
                "items": items_of(500),
            },
            "p1000": {
                "context_sha256": built[1000][1][
                    next(i for i, r in enumerate(built[1000][1])
                         if r["example_id"] == PRIORITY_CASE)
                ]["context_sha256"],
                "items": items_of(1000),
            },
        },
    }
    for name, cfg in case037["configs"].items():
        fifth = cfg["items"][4]
        cfg["fifth_item_text_id"] = fifth["text_id"]
        cfg["fifth_item_channel"] = fifth["channel"]
        cfg["matches_task75_sha"] = (
            cfg["context_sha256"] == T75_037_CTX_SHA)
    (REPO / "data" / "evaluation" / "task83_case037_evidence.json").write_text(
        json.dumps(case037, indent=2, ensure_ascii=False), encoding="utf-8")
    log("037 four-config comparison: " + json.dumps({
        k: {"sha": v["context_sha256"][:16], "item5": v["fifth_item_text_id"],
            "match_t75": v["matches_task75_sha"]}
        for k, v in case037["configs"].items()}))

    # --- kernel payload ----------------------------------------------------
    def case_entry(pool: int, eid: str) -> dict:
        row = next(r for r in built[pool][1] if r["example_id"] == eid)
        return {
            "example_id": eid,
            "question": row["question"],
            "user_content": row["user_content"],
            "context_sha256": row["context_sha256"],
            "n_evidence_items": row["n_evidence_items"],
        }

    payload = {
        "task": "TASK 83 targeted mini-gate generation payload",
        "configs": {
            "p500": {eid: case_entry(500, eid) for eid in targets["p500"]},
            "p1000": {eid: case_entry(1000, eid) for eid in targets["p1000"]},
            "p250ctrl": {
                PRIORITY_CASE: {
                    "example_id": PRIORITY_CASE,
                    "question": task82_prompts[PRIORITY_CASE]["question"],
                    "user_content": task82_prompts[PRIORITY_CASE]["user_content"],
                    "context_sha256": task82_prompts[PRIORITY_CASE]["context_sha256"],
                    "n_evidence_items": task82_prompts[PRIORITY_CASE]["n_evidence_items"],
                },
            },
            "pfullctrl": {
                PRIORITY_CASE: {
                    "example_id": PRIORITY_CASE,
                    "question": task75_prompts[PRIORITY_CASE]["question"],
                    "user_content": task75_prompts[PRIORITY_CASE]["user_content"],
                    "context_sha256": task75_prompts[PRIORITY_CASE]["context_sha256"],
                    "n_evidence_items": task75_prompts[PRIORITY_CASE]["n_evidence_items"],
                },
            },
        },
        "meta": {
            "generation_protocol": "task75/82 identical: greedy, 192, seed 42, 4-bit nf4",
            "priority_case": PRIORITY_CASE,
            "controls": {
                "p250ctrl": "recorded Task-82 pool-250 context rerun (determinism check)",
                "pfullctrl": "recorded Task-75 full-list context rerun (determinism check)",
            },
        },
    }
    payload_path = REPO / "data" / "evaluation" / "task83_kernel_payload.json"
    payload_path.write_text(json.dumps(payload, ensure_ascii=False),
                            encoding="utf-8")
    log(f"kernel payload {sha256_file(payload_path)[:16]}… "
        f"configs={ {k: len(v) for k, v in payload['configs'].items()} }")

    # --- preflight + gate registration (BEFORE generation) ------------------
    preflight = {
        "task": (
            "TASK 83 preflight — verified setup + mini-gate criteria "
            "registered BEFORE generation"
        ),
        "verified_before_generation": {
            "frozen_benchmark_sha256": FROZEN_SHA,
            "frozen_benchmark_sha_ok": True,
            "dense_index_alignment_ok": True,
            "dapt01_adapter_sha256": ADAPTER_SHA,
            "dapt01_adapter_sha_ok": True,
            "task74_frozen_aggregates_ok": True,
            "task82_12_case_list_recovered": recovered_12,
            "case037_contexts_recovered": {
                "task75_sha": T75_037_CTX_SHA,
                "task82_sha": T82_037_CTX_SHA,
                "ok": True,
            },
            "case037_outputs_recovered": {
                "task75_dapt_answer_prefix": "The Terapanth was founded in 1583 by Kundakunda",
                "task82_dapt_answer_prefix": "The Terapanth was founded in 1658 by Birbhan",
                "task75_dapt_flags": {
                    "abstention_detected": True, "abstention_correct": True,
                    "forbidden_hits": [], "looped": False, "at_cap_192": False,
                },
                "task82_dapt_flags": {
                    "abstention_detected": False, "abstention_correct": False,
                    "forbidden_hits": [], "looped": False, "at_cap_192": True,
                },
            },
            "task81_implementation": (
                "bm25.search(query, top_k=pool) + t74.rrf_fuse stable "
                "tie-breaking, dense full list, RRF k=20 — exact Task-81/82 code"
            ),
            "task81_edge_equivalence_reference": (
                "6/6 PASS re-verified in Task-82 preflight"
            ),
            "run_host": (
                "Kaggle T4 (established; Colab token expired 2026-10-09)"
            ),
            "evidence_generation_only": True,
            "production_default_unchanged": True,
        },
        "config_summaries": config_summaries,
        "generation_targets": targets,
        "generation_target_union_n": len(union),
        "task82_registered_gates_recovered": TASK82_GATES,
        "mini_gate_acceptance_criteria": MINI_GATES,
        "gate_registration": (
            "written BEFORE any Task-83 generation was run; thresholds are "
            "recovered Task-82 values applied to the projected full-47 or "
            "recorded Task-75 reference outcomes; none informed by Task-83 outputs"
        ),
        "projection_method": (
            "projected full-47 arm = fresh Task-83 scores on the candidate's "
            "differing cases + recorded Task-75 rows elsewhere (valid: "
            "non-differing contexts are byte-identical to Task-75; cross-host "
            "determinism established by Task-82 arms A/B/C exact reproduction)"
        ),
        "prior_comparisons": {
            "task75_pfull": {"base_rag": [0.695, 32], "dapt_rag": [0.695, 31],
                             "abstention_correct": {"base_rag": 0, "dapt_rag": 1},
                             "loops": {"base_rag": 0, "dapt_rag": 4},
                             "generation_fabrication": {"base_rag": 2, "dapt_rag": 1}},
            "task82_p250": {"base_rag": [0.695, 32], "dapt_rag": [0.6738, 30],
                            "abstention_correct": {"base_rag": 0, "dapt_rag": 0},
                            "loops": {"base_rag": 0, "dapt_rag": 4},
                            "generation_fabrication": {"base_rag": 2, "dapt_rag": 2}},
        },
    }
    (REPO / "data" / "evaluation" / "task83_preflight.json").write_text(
        json.dumps(preflight, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"wrote task83_preflight.json — {len(MINI_GATES)} mini-gate criteria "
        f"registered BEFORE generation")

    log(f"TASK 83 BUILD EVIDENCE DONE in {time.time()-t0:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""TASK 70 Phases 1-4 — reconstruct, instrument, classify, measure.

Read-only forensics over the frozen Task-69 artifacts:

  Phase 1  recompute Task-69 state from raw JSONL (never trust the report)
  Phase 2  classify every case into A..H with recorded evidence + confidence
  Phase 3  source-vs-passage retrieval metrics (Recall@1/3/5/10, MRR, ...)
  Phase 4  forensic table for the evidence-zero set

Integrity anchors: baseline re-execution must reproduce Task-69 context
sha256, source/unit ranks and evidence scores for all 47 cases before any
classification is emitted.

Outputs:
  data/evaluation/task70_retrieval_failure_cases.jsonl
  data/evaluation/task70_phase1_4.json
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from retrieval_stack import (  # noqa: E402
    BASELINE,
    CASES_PATH,
    CONSOLIDATED_PATH,
    EVIDENCE_PATH,
    FROZEN_SHA,
    METRICS_PATH,
    PROMPTS_PATH,
    load_jsonl,
    load_stack,
    retrieve,
    unit_key,
)

REPO = Path(__file__).resolve().parents[2]
OUT_CASES = REPO / "data" / "evaluation" / "task70_retrieval_failure_cases.jsonl"
OUT_PHASE = REPO / "data" / "evaluation" / "task70_phase1_4.json"

CLASS_NAMES = {
    "A": "CORPUS_ABSENCE",
    "B": "SOURCE_MISS",
    "C": "UNIT_MISS",
    "D": "RANKING_MISS",
    "E": "METADATA_ONLY",
    "F": "EVIDENCE_CONTRACT_LOSS",
    "G": "GENERATION_FAILURE",
    "H": "OTHER",
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def classify(r: dict, scores: dict, failure_class: dict) -> dict:
    eid = r["example_id"]
    n = r["n_groups"] or 0
    s = r["support"]
    ev = r["evidence_score"]
    arm_scores = scores[eid]
    arm_fc = failure_class[eid]

    facts = {
        "evidence_score": ev,
        "support_block_groups": s["block"],
        "support_ev5_full_groups": s["ev5_full"],
        "support_top10_full_groups": s["top_full"],
        "n_groups": n,
        "expected_source": r["expected_source"],
        "expected_units": r["expected_units"],
        "source_first_rank": r["source_first_rank"],
        "source_first_channel": r["source_first_channel"],
        "source_in_pool_rank": r["source_in_pool_rank"],
        "unit_hit_rank": r["unit_hit_rank"],
        "unit_pool_ranks": r["unit_pool_ranks"],
        "expected_in_smatches": r["expected_in_smatches"],
        "block_sha256": r["block_sha256"],
        "contract_violations": len(r["contract_violations"]),
        "task69_failure_class": arm_fc,
        "arm_scores": arm_scores,
    }

    def out(cls: str, reason: str, confidence: str) -> dict:
        return {
            "example_id": eid,
            "classification": cls,
            "class_name": CLASS_NAMES[cls],
            "reason": reason,
            "confidence": confidence,
            "evidence_supporting_classification": facts,
        }

    # --- abstention cases: evidence cannot "answer"; generation decides ---
    if r["abstention_case"]:
        base_ok = arm_scores.get("base_rag") == 1.0
        dapt_ok = arm_scores.get("dapt_rag") == 1.0
        if base_ok and dapt_ok:
            return out("H", "no failure: both RAG arms abstained correctly "
                            "(evidence contained risky patterns but model refused)", "high")
        risk = bool(r["forbidden_hits"])
        detail = ("forbidden pattern present in evidence block (retrieval surfaced risk); "
                  "model still asserted the claim" if risk else
                  "forbidden pattern absent from evidence block; model fabricated the claim")
        armnote = f" base_rag_ok={base_ok} dapt_rag_ok={dapt_ok}"
        return out("G", "abstention failure — generation must refuse: " + detail + armnote, "high")

    # --- corpus absence ---
    if not r["expected_source"]:
        return out("A", "no expected source recorded for this case and no corpus "
                        "candidate supports the answer; Task-69 marks this query as "
                        "corpus-absence (evidence genuinely absent)", "high")
    if r["expected_source"] not in _CORPUS_SOURCES:
        return out("A", f"expected source {r['expected_source']} does not exist in "
                        f"data/release/rag_corpus.jsonl", "high")

    # --- source never retrieved ---
    if r["source_first_rank"] is None:
        via_meta = r["expected_in_smatches"]
        return out("B", f"expected source {r['expected_source']} exists in corpus "
                        f"(pool rank {r['source_in_pool_rank']}) but is absent from the "
                        f"mode-C top-{BASELINE.top_k} result list"
                        + (f"; source-metadata channel DID match it but the fill did not "
                           f"surface a supporting passage" if via_meta else
                           f"; source-metadata channel did not match it either"), "high")

    # --- evidence sufficient (all groups pass on the block) ---
    if ev == 1.0:
        failed_arms = [a for a in ("base_rag", "dapt_rag") if arm_scores.get(a, 0.0) < 1.0]
        if failed_arms:
            return out("G", f"evidence sufficient (ev=1.0, all {n} groups pass on the "
                            f"block) but arm(s) {failed_arms} scored below ceiling — "
                            f"generation-side failure (task69={arm_fc})", "high")
        return out("H", "no failure: evidence sufficient and both RAG arms scored 1.0", "high")

    # --- evidence insufficient: locate the loss (per-group set gains) ---
    sb, s5, st = set(s["block"]), set(s["ev5_full"]), set(s["top_full"])

    # F: support exists in the SELECTED items' full text but 500-char truncation lost it
    if s5 - sb:
        gained = sorted(s5 - sb)
        return out("F", f"supporting keyterms exist in the selected evidence items' full "
                        f"text (groups {gained} pass) but the {BASELINE.text_trunc}-char "
                        f"truncation dropped them (block passes {sorted(sb)}/{n})", "high")

    # D: support exists in the candidate list beyond the selected evidence items
    if st - s5:
        gained = sorted(st - s5)
        return out("D", f"supporting keyterms exist in candidates outside the evidence "
                        f"selection (groups {gained} pass on full top-{BASELINE.top_k} "
                        f"texts but not on the selected {BASELINE.ev_k}) — lost during "
                        f"ranking/top-K/evidence selection", "high")

    # C: expected unit(s) never enter the BM25 candidate pool
    if r["expected_units"]:
        if all(u not in _CORPUS_UNITS for u in r["expected_units"]):
            return out("A", f"expected source was retrieved (rank {r['source_first_rank']}) "
                            f"but expected unit(s) {r['expected_units']} do not exist "
                            f"anywhere in data/release/rag_corpus.jsonl — relevant passage "
                            f"genuinely absent (corpus absence)", "high")
        pool_ranks = r["unit_pool_ranks"]
        if all(v is None for v in pool_ranks.values()):
            return out("C", f"expected source was retrieved (rank {r['source_first_rank']}) "
                            f"but expected unit(s) {r['expected_units']} never enter the "
                            f"BM25 pool of {BASELINE.pool} — passage-level candidate "
                            f"generation failure", "high")
        # D: unit in pool but never selected into candidates/evidence
        if r["unit_hit_rank"] is None:
            pr = {k: v for k, v in pool_ranks.items() if v is not None}
            return out("D", f"expected unit present in BM25 pool (ranks {pr}) but not in "
                            f"the mode-C top-{BASELINE.top_k} — lost at "
                            f"diversify/max_per_source/top-K stage", "high")
        # unit retrieved but text does not support the answer groups
        if not (st - sb):
            return out("E", f"expected source and unit retrieved (source rank "
                            f"{r['source_first_rank']}, unit rank {r['unit_hit_rank']}) but "
                            f"no retrieved passage text supports any additional scoring "
                            f"groups (block passes {sorted(sb)}/{n}) — source/unit match "
                            f"without useful textual evidence", "medium")

    # source found, no units declared (or units handled), nothing supports
    if not (st - sb):
        chan = r["source_first_channel"]
        return out("E", f"expected source retrieved (rank {r['source_first_rank']}, first "
                        f"channel={chan}) but retrieved passages do not carry additional "
                        f"answer keyterms (block passes {sorted(sb)}/{n}) — source/metadata "
                        f"match without useful textual evidence", "medium")

    return out("H", f"residual: ev={ev}, block={sorted(sb)}, top={sorted(st)} — "
                    f"inspect manually", "low")


_CORPUS_SOURCES: set[str] = set()
_CORPUS_UNITS: set[str] = set()


def main() -> int:
    global _CORPUS_SOURCES, _CORPUS_UNITS
    # ---------------- Phase 1: reconstruction from raw artifacts ----------------
    frozen_sha = sha256_file(CASES_PATH)
    assert frozen_sha == FROZEN_SHA, f"frozen drift: {frozen_sha}"
    cases = load_jsonl(CASES_PATH)
    prompts = {r["example_id"]: r for r in load_jsonl(PROMPTS_PATH)}
    evidence = {r["example_id"]: r for r in load_jsonl(EVIDENCE_PATH)}
    metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    rm_per = {r["example_id"]: r for r in metrics["per_case"]}
    consolidated = load_jsonl(CONSOLIDATED_PATH)
    scores = {r["example_id"]: r["scores"] for r in consolidated}
    failure_class = {r["example_id"]: r["failure_class"] for r in consolidated}

    ev0_ids = sorted(r["example_id"] for r in consolidated
                     if r["evidence"]["evidence_answer_score"] == 0)
    ri_base = sorted(r["example_id"] for r in consolidated
                     if r["failure_class"]["base_rag"] == "RETRIEVAL_INSUFFICIENT")
    ri_dapt = sorted(r["example_id"] for r in consolidated
                     if r["failure_class"]["dapt_rag"] == "RETRIEVAL_INSUFFICIENT")
    phase1 = {
        "n_cases": len(cases),
        "frozen_sha256": frozen_sha,
        "evidence_zero_cases": ev0_ids,
        "n_evidence_zero": len(ev0_ids),
        "ri_base_rag": ri_base,
        "n_ri_base_rag": len(ri_base),
        "ri_dapt_rag": ri_dapt,
        "n_ri_dapt_rag": len(ri_dapt),
        "ev0_but_prior_knowledge": sorted(set(ev0_ids) - set(ri_base)),
        "evidence_k": metrics["config"]["evidence_k"],
        "top_k": metrics["config"]["top_k"],
        "pool": metrics["config"]["pool"],
        "retrieval_mode": metrics["aggregate"]["retrieval_mode"],
        "contract_violations_task69": metrics["aggregate"]["contract_violations"],
        "note_13_vs_15": (
            "Task-70 brief cites 13 Ev=0; raw artifacts show 15 evidence-zero cases. "
            "13 = BASE+RAG RETRIEVAL_INSUFFICIENT count; DAPT01EVAL-004 and -009 are "
            "evidence-zero too but scored 1.0 from prior knowledge in BASE+RAG "
            "(047 likewise in DAPT+RAG), so they leave the failure bucket."
        ),
    }
    assert len(cases) == 47
    assert phase1["evidence_k"] == 5 and phase1["top_k"] == 10
    assert phase1["contract_violations_task69"] == []

    # ---------------- instrumented baseline re-execution ----------------
    stack = load_stack(BASELINE)
    _CORPUS_SOURCES = stack["corpus_sources"]
    _CORPUS_UNITS = stack["corpus_units"]
    print(f"corpus {len(stack['docs'])} docs, {len(stack['corpus_sources'])} sources", flush=True)

    retr: dict[str, dict] = {}
    repro_failures: list[str] = []
    for case in cases:
        eid = case["example_id"]
        r = retrieve(case, stack, BASELINE)
        retr[eid] = r
        p = prompts[eid]
        m = rm_per[eid]
        e = evidence[eid]
        checks = {
            "block_sha": r["block_sha256"] == p["context_sha256"] == e["evidence_context"]["sha256"],
            "source_rank": r["source_first_rank"] == m["source_first_rank"],
            "unit_rank": r["unit_hit_rank"] == m["unit_hit_rank"],
            "ev_score": r["evidence_score"] == m["evidence_answer_score"],
            "text_order": [x["text_id"] for x in r["results"]]
                          == [x["text_id"] for x in e["results"]],
            "contract": r["contract_violations"] == [],
        }
        bad = [k for k, v in checks.items() if not v]
        if bad:
            repro_failures.append(f"{eid}: {bad}")
    if repro_failures:
        raise SystemExit("baseline reproduction FAILED:\n" + "\n".join(repro_failures))
    print(f"baseline reproduction verified for all {len(cases)} cases "
          f"(block shas, ranks, ev scores, contracts)", flush=True)

    # ---------------- Phase 2: classification ----------------
    rows_out = []
    for case in cases:
        eid = case["example_id"]
        r = retr[eid]
        cls = classify(r, scores, failure_class)
        retrieved_source_ids = [x["source_id"] for x in r["results"]]
        retrieved_unit_ids = list(dict.fromkeys(unit_key(x["text_id"]) for x in r["results"]))
        rows_out.append(
            {
                "case_id": eid,
                "category": case["category"],
                "language": case["language"],
                "abstention_case": bool(case.get("abstention_case")),
                "classification": cls["classification"],
                "class_name": cls["class_name"],
                "reason": cls["reason"],
                "confidence": cls["confidence"],
                "retrieved_source_ids": retrieved_source_ids,
                "retrieved_unit_ids": retrieved_unit_ids,
                "relevant_source_id": r["expected_source"],
                "relevant_unit_ids": r["expected_units"] or None,
                "in_ev0_set": eid in ev0_ids,
                "in_ri13_base_rag": eid in ri_base,
                "evidence_supporting_classification": cls["evidence_supporting_classification"],
            }
        )

    OUT_CASES.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows_out),
        encoding="utf-8",
    )
    print(f"wrote {OUT_CASES.relative_to(REPO)} ({len(rows_out)} rows)")

    cls_counter = Counter(r["classification"] for r in rows_out)
    ev0_counter = Counter(r["classification"] for r in rows_out if r["in_ev0_set"])
    print("classification (all 47):", dict(sorted(cls_counter.items())))
    print("classification (15 Ev=0):", dict(sorted(ev0_counter.items())))

    # ---------------- Phase 3: source vs passage retrieval ----------------
    src_cases = [r for r in retr.values() if r["expected_source"]]
    unit_cases = [r for r in retr.values() if r["expected_units"]]

    def recall(rows: list[dict], key: str, k: int) -> float:
        hits = [1.0 if (r[key] is not None and r[key] <= k) else 0.0 for r in rows]
        return round(sum(hits) / len(hits), 4) if hits else 0.0

    def mrr(rows: list[dict], key: str) -> float:
        vals = [(1.0 / r[key]) if r[key] else 0.0 for r in rows]
        return round(sum(vals) / len(vals), 4) if vals else 0.0

    metadata_only, src_hit_unit_miss, pool_unit_hits = [], [], 0
    for r in retr.values():
        sid = r["expected_source"]
        if not sid:
            continue
        hits = [x for x in r["results"] if x["source_id"] == sid]
        if hits and all(x["retrieval_channel"] == "source_metadata" for x in hits):
            metadata_only.append(r["example_id"])
        if r["expected_units"] and r["source_first_rank"] is not None and r["unit_hit_rank"] is None:
            src_hit_unit_miss.append(r["example_id"])
    for r in unit_cases:
        if any(v is not None for v in r["unit_pool_ranks"].values()):
            pool_unit_hits += 1

    phase3 = {
        "n_source_level": len(src_cases),
        "n_no_expected_source": len(retr) - len(src_cases),
        "source_recall_at_1": recall(src_cases, "source_first_rank", 1),
        "source_recall_at_3": recall(src_cases, "source_first_rank", 3),
        "source_recall_at_5": recall(src_cases, "source_first_rank", 5),
        "source_recall_at_10": recall(src_cases, "source_first_rank", 10),
        "source_mrr": mrr(src_cases, "source_first_rank"),
        "source_zero_hit": [r["example_id"] for r in src_cases if r["source_first_rank"] is None],
        "n_unit_labeled": len(unit_cases),
        "unit_recall_at_1": recall(unit_cases, "unit_hit_rank", 1),
        "unit_recall_at_3": recall(unit_cases, "unit_hit_rank", 3),
        "unit_recall_at_5": recall(unit_cases, "unit_hit_rank", 5),
        "unit_recall_at_10": recall(unit_cases, "unit_hit_rank", 10),
        "unit_mrr": mrr(unit_cases, "unit_hit_rank"),
        "unit_candidate_pool_hit": pool_unit_hits,
        "unit_candidate_pool_hit_at_2000": round(pool_unit_hits / len(unit_cases), 4)
        if unit_cases else None,
        "metadata_only_cases": metadata_only,
        "n_metadata_only": len(metadata_only),
        "source_hit_but_unit_miss_cases": src_hit_unit_miss,
        "n_source_hit_but_unit_miss": len(src_hit_unit_miss),
        "not_measured": [
            "graded/passage-level relevance: NOT_MEASURED (no graded qrels exist)",
            "recall@k for the 1 corpus-absence case: NOT_APPLICABLE (no expected source)",
            "unit recall for the 8 cases without unit_ids provenance: NOT_MEASURED",
        ],
    }

    # ---------------- Phase 4: Ev=0 forensic table ----------------
    phase4 = []
    for eid in ev0_ids:
        r = retr[eid]
        case = next(c for c in cases if c["example_id"] == eid)
        unit_in_evidence = r["unit_hit_rank"] is not None and r["unit_hit_rank"] <= BASELINE.ev_k
        removed_before = bool(
            (any(v is not None for v in r["unit_pool_ranks"].values()) and r["unit_hit_rank"] is None)
            or (r["unit_hit_rank"] is not None and r["unit_hit_rank"] > BASELINE.ev_k)
            or (r["source_first_rank"] is not None and r["source_first_rank"] > BASELINE.ev_k
                and r["unit_hit_rank"] is None)
        )
        cls = next(x for x in rows_out if x["case_id"] == eid)
        fundamental = "generation" if cls["classification"] == "G" else "retrieval"
        phase4.append(
            {
                "case_id": eid,
                "category": case["category"],
                "language": case["language"],
                "in_ri13_base_rag": eid in ri_base,
                "task69_failure_class_base_rag": failure_class[eid]["base_rag"],
                "correct_source_present": r["source_first_rank"] is not None,
                "source_first_rank": r["source_first_rank"],
                "source_within_top_5": (r["source_first_rank"] or 99) <= 5,
                "relevant_unit_ids": r["expected_units"] or None,
                "relevant_unit_present": r["unit_hit_rank"] is not None,
                "relevant_unit_rank": r["unit_hit_rank"],
                "relevant_unit_within_top_5": unit_in_evidence,
                "unit_in_pool_rank": {k: v for k, v in r["unit_pool_ranks"].items()},
                "metadata_found_expected_source": r["expected_in_smatches"],
                "bm25_found_expected_source": r["source_in_pool_rank"] is not None,
                "bm25_found_expected_unit": any(v is not None for v in r["unit_pool_ranks"].values()),
                "removed_before_final_evidence": removed_before,
                "support_top10_full": r["support"]["top_full"],
                "support_block": r["support"]["block"],
                "classification": cls["classification"],
                "class_name": cls["class_name"],
                "reason": cls["reason"],
                "confidence": cls["confidence"],
                "fundamental_side": fundamental,
            }
        )

    payload = {
        "phase1_reconstruction": phase1,
        "phase2_classification_counts_all": dict(sorted(cls_counter.items())),
        "phase2_classification_counts_ev0": dict(sorted(ev0_counter.items())),
        "phase3_retrieval_metrics": phase3,
        "phase4_ev0_table": phase4,
        "baseline_reproduction": "verified (block sha, ranks, ev scores, contracts, text order)",
        "frozen_sha256": frozen_sha,
    }
    OUT_PHASE.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT_PHASE.relative_to(REPO)}")
    print("phase3:", json.dumps({k: v for k, v in phase3.items() if not isinstance(v, list)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

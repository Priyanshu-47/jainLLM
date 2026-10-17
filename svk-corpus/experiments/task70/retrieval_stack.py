"""TASK 70 shared retrieval instrumentation (read-only, no production changes).

Re-executes the Task-69 mode-C pipeline with a parameterized config so that:

  * Phase 1/2/3 can INSTRUMENT the baseline (pool ranks, source-channel
    matches, fills, support probes) while asserting byte-identical
    reproduction of the frozen Task-69 artifacts (context sha, ranks,
    evidence scores).
  * Phase 5 can run small controlled variants (depth / evidence width /
    metadata union / expansion ablation) on the same frozen 47 queries.

Everything here is analysis-side: no file under src/ is touched, no corpus
or benchmark file is modified.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

# Reuse the Task-69 builder verbatim for byte-identical evidence blocks.
_spec = importlib.util.spec_from_file_location(
    "task69_build_rag_evidence", REPO / "experiments" / "task69" / "build_rag_evidence.py"
)
b69 = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(b69)

from svk_corpus.retrieval import BM25Index, RetrievalResult, load_corpus  # noqa: E402
from svk_corpus.retrieval.contract import validate_result  # noqa: E402
from svk_corpus.retrieval.rerank import Reranker  # noqa: E402
from svk_corpus.retrieval.source_channel import (  # noqa: E402
    SourceUnitExpander,
    build_source_index,
)

import score_task60  # noqa: E402  (path added by b69 module import)

CASES_PATH = REPO / "data" / "evaluation" / "dapt01_eval_cases.jsonl"
CORPUS_PATH = REPO / "data" / "release" / "rag_corpus.jsonl"
MANIFEST_PATH = REPO / "manifests" / "source_manifest.csv"
PROMPTS_PATH = REPO / "data" / "evaluation" / "task69_rag_prompts.jsonl"
EVIDENCE_PATH = REPO / "data" / "evaluation" / "task69_rag_evidence.jsonl"
METRICS_PATH = REPO / "data" / "evaluation" / "task69_retrieval_metrics.json"
CONSOLIDATED_PATH = REPO / "data" / "evaluation" / "task69_rag_results.jsonl"

FROZEN_SHA = "06625f72190e3ae130447345afdc04342bd19cb76f842285706480cba7765b81"


@dataclass
class RetrievalConfig:
    """Variant knobs. Defaults = validated Task-69 mode-C baseline."""

    name: str = "R1_baseline"
    top_k: int = 10           # retrieval depth (combined candidates)
    pool: int = 2000          # BM25 pool before diversify
    max_fill: int = 3         # metadata tail fills (mode-C policy)
    ev_k: int = 5             # passages handed to the scorer/prompt
    text_trunc: int = 500
    expand_on: bool = True    # folding + alias expansion (bm25 index/query)
    union_metadata: bool = False  # include ALL non-identifier metadata matches


BASELINE = RetrievalConfig()


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def unit_key(text_id: str) -> str:
    return b69.unit_key(text_id)


def load_stack(cfg: RetrievalConfig = BASELINE) -> dict[str, Any]:
    """Build corpus + indexes. Rebuild when expansion differs (index-time)."""
    cards = b69.load_manifest_cards(MANIFEST_PATH)
    docs = load_corpus(CORPUS_PATH, MANIFEST_PATH)

    bm25_mod = sys.modules["svk_corpus.retrieval.bm25"]
    orig_expand = bm25_mod.expand_query_text
    if not cfg.expand_on:
        from svk_corpus.retrieval.normalization import tokenize

        bm25_mod.expand_query_text = lambda text: list(tokenize(text))  # type: ignore[assignment]
    try:
        bm25 = BM25Index(docs, k1=1.5, b=0.75)
    finally:
        bm25_mod.expand_query_text = orig_expand

    sidx = build_source_index(MANIFEST_PATH)
    return {
        "cards": cards,
        "docs": docs,
        "bm25": bm25,
        "sidx": sidx,
        "expander": SourceUnitExpander(docs),
        "diversify": Reranker(strategy="diversify", max_per_source=3),
        "corpus_sources": {d.source_id for d in docs},
        "corpus_units": {unit_key(d.text_id) for d in docs},
        "expand_on": cfg.expand_on,
    }


def retrieve(case: dict, stack: dict[str, Any], cfg: RetrievalConfig) -> dict[str, Any]:
    """Instrumented mode-C retrieval for one case under `cfg`."""
    eid = case["example_id"]
    query = case["question"]
    prov = case.get("provenance") or {}

    # expansion applies at query time inside bm25.search; patch the module
    # attribute only when ablated (index already built accordingly).
    bm25_mod = sys.modules["svk_corpus.retrieval.bm25"]
    orig_expand = bm25_mod.expand_query_text
    if not cfg.expand_on:
        from svk_corpus.retrieval.normalization import tokenize

        bm25_mod.expand_query_text = lambda text: list(tokenize(text))  # type: ignore[assignment]
    try:
        pool = stack["bm25"].search(query, top_k=cfg.pool)
    finally:
        bm25_mod.expand_query_text = orig_expand

    pool_rank_by_unit = {unit_key(h.doc.text_id): h.rank for h in pool}
    pool_rank_by_source: dict[str, int] = {}
    for h in pool:
        pool_rank_by_source.setdefault(h.doc.source_id, h.rank)

    unit_tier = stack["diversify"].rerank(
        [
            RetrievalResult(doc=h.doc, score=h.score, rank=h.rank, methods={"bm25": h.rank})
            for h in pool
        ]
    )[: cfg.top_k]

    smatches = stack["sidx"].search(query, top_k=max(cfg.top_k, 10))
    unit_ids = {r.doc.text_id for r in unit_tier}
    unit_sids = {r.doc.source_id for r in unit_tier}
    missing = [m for m in smatches if m.source_id not in unit_sids and not m.identifier_only]
    if cfg.union_metadata:
        fill = stack["expander"].expand(missing, top_k=len(missing))
    else:
        n_fill = min(cfg.max_fill, len(missing))
        fill = stack["expander"].expand(missing[:n_fill], top_k=n_fill)
    keep = max(cfg.top_k - len(fill), 0)
    combined = list(unit_tier[:keep]) + fill
    combined = combined[: cfg.top_k]

    norm_tokens = tuple(b69.expand_query_text(query))
    results_out: list[dict] = []
    contract_violations: list[dict] = []
    for i, r in enumerate(combined, 1):
        ch = b69.channel_of(r, unit_ids)
        cr = b69.build_canonical(r, eid, i, ch, query, norm_tokens)
        violations = validate_result(cr)
        if violations:
            contract_violations.append({"result_id": cr.result_id, "violations": violations})
        loc = dict(r.doc.locator or {})
        results_out.append(
            {
                "result_id": cr.result_id,
                "text_id": r.doc.text_id,
                "source_id": r.doc.source_id,
                "retrieval_channel": ch,
                "retrieval_rank": i,
                "retrieval_score": round(float(r.score), 4),
                "unit_bm25_rank": cr.unit_bm25_rank,
                "title": r.doc.title,
                "locator_citation": (loc.get("citation") or "") if isinstance(loc, dict) else "",
                "provenance": {
                    "author": r.doc.author,
                    "religious_scope": r.doc.religious_scope,
                    "religious_scope_confidence": r.doc.religious_scope_confidence,
                    "knowledge_layer": r.doc.knowledge_layer,
                    "teacher_or_author": r.doc.teacher_or_author,
                    "lineage": r.doc.lineage,
                    "source_quality": r.doc.source_quality,
                    "sect": r.doc.sect,
                    "language": r.doc.language,
                },
                "text": r.doc.text,
            }
        )

    # evidence block (first ev_k, truncated) — byte-identical to Task 69 at baseline
    cards = stack["cards"]
    ctx_items = []
    for pos, res in enumerate(results_out[: cfg.ev_k], 1):
        ctx_items.append(
            {
                "pos": pos,
                "text_id": res["text_id"],
                "source_id": res["source_id"],
                "title": res["title"],
                "retrieval_channel": res["retrieval_channel"],
                "retrieval_rank": res["retrieval_rank"],
                "retrieval_score": res["retrieval_score"],
                "provenance": res["provenance"],
                "locator_citation": res["locator_citation"],
                "text_truncated": b69.truncate(res["text"], cfg.text_trunc),
            }
        )
    block = b69.build_context_block(ctx_items, cards)
    block_sha = hashlib.sha256(block.encode("utf-8")).hexdigest()

    # ranking facts
    expected_source = prov.get("source_id")
    expected_units = prov.get("unit_ids") or []
    first_rank = None
    first_channel = None
    for res in results_out:
        if res["source_id"] == expected_source:
            first_rank = res["retrieval_rank"]
            first_channel = res["retrieval_channel"]
            break
    unit_hit_rank = None
    for res in results_out:
        if any(unit_key(res["text_id"]) == u for u in expected_units):
            unit_hit_rank = res["retrieval_rank"]
            break
    unit_pool_ranks = {u: pool_rank_by_unit.get(u) for u in expected_units}

    # scoring / support probes
    groups = case.get("scoring") or []
    abstention_case = bool(case.get("abstention_case"))
    evidence_score = None
    forbidden_hits: list[str] = []
    if not abstention_case and groups:
        evidence_score = sum(score_task60.group_pass(g, block) for g in groups) / len(groups)
    if abstention_case:
        for g in groups:
            for pat in g.get("forbidden_claims", []):
                if re.search(pat, block, flags=re.IGNORECASE):
                    forbidden_hits.append(pat)

    def passing_groups(text: str) -> list[int]:
        if abstention_case or not groups:
            return []
        return [i for i, g in enumerate(groups) if score_task60.group_pass(g, text)]

    card_lines = []
    seen: list[str] = []
    for res in results_out[: cfg.ev_k]:
        if res["source_id"] not in seen:
            seen.append(res["source_id"])
            c = b69.render_card(res["source_id"], cards)
            if c:
                card_lines.append(c)
    cards_text = "\n".join(card_lines)
    ev5_full = "\n".join(r["text"] for r in results_out[: cfg.ev_k]) + ("\n" + cards_text if cards_text else "")
    all_card_lines = [
        b69.render_card(sid, cards) or ""
        for sid in dict.fromkeys(r["source_id"] for r in results_out)
    ]
    top_full = "\n".join(r["text"] for r in results_out) + (
        "\n" + "\n".join(all_card_lines) if results_out else ""
    )
    s_block = passing_groups(block)
    s_ev5_full = passing_groups(ev5_full)
    s_top_full = passing_groups(top_full)

    return {
        "example_id": eid,
        "config": cfg.name,
        "query": query,
        "results": results_out,
        "block": block,
        "block_sha256": block_sha,
        "n_groups": len(groups),
        "abstention_case": abstention_case,
        "evidence_score": evidence_score,
        "forbidden_hits": forbidden_hits,
        "support": {
            "block": s_block,
            "ev5_full": s_ev5_full,
            "top_full": s_top_full,
        },
        "expected_source": expected_source,
        "expected_units": expected_units,
        "source_first_rank": first_rank,
        "source_first_channel": first_channel,
        "unit_hit_rank": unit_hit_rank,
        "unit_pool_ranks": unit_pool_ranks,
        "source_in_pool_rank": pool_rank_by_source.get(expected_source) if expected_source else None,
        "smatch_sources": [m.source_id for m in smatches],
        "expected_in_smatches": (expected_source in {m.source_id for m in smatches})
        if expected_source
        else False,
        "n_fill": len(fill),
        "fill_sources": [r.doc.source_id for r in fill],
        "contract_violations": contract_violations,
    }


def answers_and_scores(consolidated: dict[str, dict]) -> tuple[dict, dict, dict]:
    """(answers, scores, failure_class) maps keyed by example_id from Task 69."""
    answers = {r["example_id"]: r["outputs"] for r in consolidated}
    scores = {r["example_id"]: r["scores"] for r in consolidated}
    fc = {r["example_id"]: r["failure_class"] for r in consolidated}
    return answers, scores, fc

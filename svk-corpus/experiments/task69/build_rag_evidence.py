"""TASK 69 Phase 3/6/8: governed retrieval over the frozen Task-60 queries.

Reuses the validated production retrieval path exactly as
src/svk_corpus/retrieval/evaluate.py mode C (C_combined):

  1. unit channel  = Okapi BM25 pool (top 2000) -> Reranker(diversify,
     max_per_source=3) -> top_k units
  2. source channel = SourceIndex.search(query) metadata matches
  3. combined      = unit tier first; metadata fills ONLY tail slots for
     sources with zero lexical presence (max 3, never displacing a unit hit)

No new embedding model, no dense channel (UnavailableDense production path),
no BGE-M3 rerun. Query = the frozen question only (no case provenance is
given to retrieval). Alias/fold normalization happens inside BM25Index for
both index and query (normalization.expand_query_text) — identical to the
validated baseline.

Outputs
  data/evaluation/task69_rag_evidence.jsonl   per-case retrieval + evidence contract
  data/evaluation/task69_rag_prompts.jsonl    identical user content for both model arms
  data/evaluation/task69_retrieval_metrics.json  Phase 8 retrieval quality
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "experiments" / "dapt_01" / "evaluation"))

from svk_corpus.retrieval import (  # noqa: E402
    BM25Index,
    RetrievalResult,
    load_corpus,
)
from svk_corpus.retrieval.contract import (  # noqa: E402
    CanonicalResult,
    MetadataMatchEvidence,
    NormalizationEvidence,
    RetrievalChannel,
    validate_result,
)
from svk_corpus.retrieval.normalization import expand_query_text  # noqa: E402
from svk_corpus.retrieval.rerank import Reranker  # noqa: E402
from svk_corpus.retrieval.source_channel import (  # noqa: E402
    SourceUnitExpander,
    build_source_index,
)

import score_task60  # noqa: E402  (scoring reused verbatim for evidence ceiling)

CASES_PATH = REPO / "data" / "evaluation" / "dapt01_eval_cases.jsonl"
CORPUS_PATH = REPO / "data" / "release" / "rag_corpus.jsonl"
MANIFEST_PATH = REPO / "manifests" / "source_manifest.csv"
OUT_EVIDENCE = REPO / "data" / "evaluation" / "task69_rag_evidence.jsonl"
OUT_PROMPTS = REPO / "data" / "evaluation" / "task69_rag_prompts.jsonl"
OUT_METRICS = REPO / "data" / "evaluation" / "task69_retrieval_metrics.json"

FROZEN_SHA = "06625f72190e3ae130447345afdc04342bd19cb76f842285706480cba7765b81"
TOP_K = 10                 # retrieval depth (evaluate.py baseline)
POOL = 2000                # BM25 pool before diversify (evaluate.py baseline)
MAX_METADATA_FILL = 3      # evaluate.py step-5 policy
EVIDENCE_K = 5             # passages handed to the model
TEXT_TRUNC = 500           # chars per passage in the prompt context
CARD_FIELDS = [
    "title", "author", "publisher", "publication_year", "tradition", "sect",
    "religious_scope", "religious_scope_confidence", "knowledge_layer",
    "teacher_or_author", "lineage", "source_quality", "parent_source_id",
]
NORMALIZATION_NOTE = (
    "BM25Index applies normalization.expand_query_text (romanization fold + "
    "evidenced alias expansion) identically to index and query; corpus text "
    "and provenance are never modified"
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def load_manifest_cards(path: Path) -> dict[str, dict]:
    with path.open(encoding="utf-8") as fh:
        return {row["source_id"]: row for row in csv.DictReader(fh)}


def unit_key(text_id: str) -> str:
    """SVK-0007:u00001:hash -> SVK-0007:u00001 (case unit_ids format)."""
    return text_id.rsplit(":", 1)[0] if text_id.count(":") >= 2 else text_id


def truncate(text: str, limit: int = TEXT_TRUNC) -> str:
    t = re.sub(r"\s+", " ", text or "").strip()
    if len(t) <= limit:
        return t
    cut = t[:limit]
    sp = cut.rfind(" ")
    return (cut[:sp] if sp > 40 else cut) + "…"


def channel_of(result: RetrievalResult, unit_ids: set[str]) -> str:
    if result.doc.text_id in unit_ids:
        return "unit_bm25"
    extra = getattr(result, "extra", None)
    if isinstance(extra, dict) and extra.get("retrieval_channel"):
        return str(extra["retrieval_channel"])
    return "unit_bm25"


def unit_bm25_evidence(result: RetrievalResult) -> tuple[int | None, float | None]:
    extra = getattr(result, "extra", None)
    if isinstance(extra, dict):  # Reranker replaced extra with RerankInfo for unit hits
        pass
    bm25_rank = getattr(extra, "bm25_rank", None)
    bm25_score = getattr(extra, "bm25_score", None)
    if bm25_rank is None:
        bm25_rank = result.rank
        bm25_score = result.score
    return int(bm25_rank), (float(bm25_score) if bm25_score is not None else None)


def build_canonical(
    result: RetrievalResult,
    case_id: str,
    combined_rank: int,
    channel: str,
    query: str,
    norm_tokens: tuple[str, ...],
) -> CanonicalResult:
    extra = getattr(result, "extra", None)
    metadata_match = None
    if channel == RetrievalChannel.SOURCE_METADATA.value:
        sm = extra.get("source_metadata_match") if isinstance(extra, dict) else None
        sm = sm or {}
        metadata_match = MetadataMatchEvidence(
            source_id=sm.get("source_id", result.doc.source_id),
            matched_field=sm.get("matched_field", ""),
            matched_value=str(sm.get("matched_value", ""))[:400],
            matched_token=str(sm.get("matched_token", "")),
            weight=float(sm.get("weight", 0.0)),
            via_family=bool(sm.get("via_family", False)),
            family_root=str(sm.get("family_root", "")),
        )
    u_rank = u_score = None
    if channel == RetrievalChannel.UNIT_BM25.value:
        u_rank, u_score = unit_bm25_evidence(result)
    cr = CanonicalResult(
        result_id=f"{case_id}:r{combined_rank:02d}",
        source_id=result.doc.source_id,
        text=result.doc.text,
        title=result.doc.title,
        parent_source_id=result.doc.parent_source_id,
        locator=dict(result.doc.locator or {}),
        religious_scope=result.doc.religious_scope or "UNKNOWN",
        religious_scope_confidence=result.doc.religious_scope_confidence or "UNKNOWN",
        knowledge_layer=result.doc.knowledge_layer or "",
        teacher_or_author=result.doc.teacher_or_author or "",
        lineage=result.doc.lineage or "",
        source_quality=result.doc.source_quality or "",
        retrieval_channel=RetrievalChannel(channel),
        retrieval_rank=combined_rank,
        retrieval_score=float(result.score),
        unit_bm25_rank=u_rank,
        unit_bm25_score=u_score,
        metadata_match=metadata_match,
        normalization=NormalizationEvidence(
            original_query=query,
            normalized_tokens=norm_tokens,
            aliases_applied=(),
            phrase_rules_triggered=(),
        ),
        methods=dict(result.methods or {}),
    )
    return cr


def render_card(source_id: str, cards: dict[str, dict]) -> str | None:
    row = cards.get(source_id)
    if not row:
        return None
    parts = []
    for f in CARD_FIELDS:
        v = (row.get(f) or "").strip()
        if v:
            parts.append(f"{f}={v}")
    if not parts:
        return None
    return f"[source-metadata card] {source_id}: " + " | ".join(parts)


def build_context_block(items: list[dict], cards: dict[str, dict]) -> str:
    lines = ["[Evidence — governed Jain corpus]"]
    for it in items:
        lines.append(
            f"{it['pos']}. {it['text_id']} | channel={it['retrieval_channel']} | "
            f"rank={it['retrieval_rank']} | score={it['retrieval_score']}"
        )
        lines.append(f"   source: {it['source_id']} — {it['title']}")
        prov = it["provenance"]
        lines.append(
            "   provenance: "
            f"scope={prov['religious_scope']} ({prov['religious_scope_confidence']}); "
            f"layer={prov['knowledge_layer'] or 'UNKNOWN'}; "
            f"teacher/author={prov['teacher_or_author'] or 'UNKNOWN'}; "
            f"sect={prov['sect'] or 'UNKNOWN'}; "
            f"quality={prov['source_quality'] or 'UNKNOWN'}; "
            f"lang={prov['language'] or 'UNKNOWN'}"
        )
        loc = it.get("locator_citation") or ""
        if loc:
            lines.append(f"   locator: {loc}")
        lines.append(f"   text: {it['text_truncated']}")
    seen_sources: list[str] = []
    for it in items:
        if it["source_id"] not in seen_sources:
            seen_sources.append(it["source_id"])
    for sid in seen_sources:
        card = render_card(sid, cards)
        if card:
            lines.append(card)
    lines.append("[End of evidence]")
    return "\n".join(lines)


def main() -> int:
    frozen_sha = sha256_file(CASES_PATH)
    if frozen_sha != FROZEN_SHA:
        raise SystemExit(f"frozen benchmark sha mismatch: {frozen_sha}")
    log(f"frozen cases sha verified {frozen_sha[:16]}…")

    cases = load_jsonl(CASES_PATH)
    cards = load_manifest_cards(MANIFEST_PATH)
    log(f"{len(cases)} cases, {len(cards)} manifest source cards")

    t0 = time.time()
    docs = load_corpus(CORPUS_PATH, MANIFEST_PATH)
    bm25 = BM25Index(docs, k1=1.5, b=0.75)
    sidx = build_source_index(MANIFEST_PATH)
    expander = SourceUnitExpander(docs)
    diversify = Reranker(strategy="diversify", max_per_source=3)
    log(f"corpus {len(docs)} docs, index built in {time.time() - t0:.1f}s")

    evidence_rows: list[dict] = []
    prompt_rows: list[dict] = []
    per_case_metrics: list[dict] = []
    contract_violations_total: list[dict] = []

    for case in cases:
        eid = case["example_id"]
        query = case["question"]
        prov = case.get("provenance") or {}

        # --- validated mode-C combined policy (evaluate.py step 5) ---
        pool = bm25.search(query, top_k=POOL)
        unit_tier = diversify.rerank(
            [
                RetrievalResult(
                    doc=h.doc, score=h.score, rank=h.rank, methods={"bm25": h.rank}
                )
                for h in pool
            ]
        )[:TOP_K]
        smatches = sidx.search(query, top_k=TOP_K)
        unit_ids = {r.doc.text_id for r in unit_tier}
        unit_sids = {r.doc.source_id for r in unit_tier}
        missing = [
            m for m in smatches if m.source_id not in unit_sids and not m.identifier_only
        ]
        n_fill = min(MAX_METADATA_FILL, len(missing))
        fill = expander.expand(missing[:n_fill], top_k=n_fill)
        keep = max(TOP_K - len(fill), 0)
        combined = list(unit_tier[:keep]) + fill
        combined = combined[:TOP_K]

        norm_tokens = tuple(expand_query_text(query))
        results_out: list[dict] = []
        canonical_objs: list[CanonicalResult] = []
        for i, r in enumerate(combined, 1):
            ch = channel_of(r, unit_ids)
            cr = build_canonical(r, eid, i, ch, query, norm_tokens)
            violations = validate_result(cr)
            if violations:
                contract_violations_total.append(
                    {"result_id": cr.result_id, "violations": violations}
                )
            canonical_objs.append(cr)
            loc = dict(r.doc.locator or {})
            results_out.append(
                {
                    "result_id": cr.result_id,
                    "text_id": r.doc.text_id,
                    "source_id": r.doc.source_id,
                    "parent_source_id": r.doc.parent_source_id,
                    "retrieval_channel": ch,
                    "retrieval_rank": i,
                    "retrieval_score": round(float(r.score), 4),
                    "unit_bm25_rank": cr.unit_bm25_rank,
                    "unit_bm25_score": cr.unit_bm25_score,
                    "metadata_match": cr.metadata_match.__dict__ if cr.metadata_match else None,
                    "methods": dict(cr.methods),
                    "title": r.doc.title,
                    "locator": loc,
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
                        "script": r.doc.script,
                        "publication_year": r.doc.publication_year,
                    },
                    "text": r.doc.text,
                    "contract_valid": not violations,
                    "contract_violations": violations,
                }
            )

        # --- evidence context (top EVIDENCE_K) ---
        ctx_items = []
        for pos, res in enumerate(results_out[:EVIDENCE_K], 1):
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
                    "text_truncated": truncate(res["text"]),
                }
            )
        block = build_context_block(ctx_items, cards)
        block_sha = hashlib.sha256(block.encode("utf-8")).hexdigest()
        user_content = block + "\n\n" + query

        # --- retrieval quality (Phase 8; formulas mirror evaluate.py) ---
        expected_source = prov.get("source_id")
        hits = [res["source_id"] for res in results_out]
        first_rank = None
        if expected_source:
            first_rank = next(
                (i for i, s in enumerate(hits, 1) if s == expected_source), None
            )
        expected_units = prov.get("unit_ids") or []
        unit_hit_rank = None
        for i, res in enumerate(results_out, 1):
            if any(unit_key(res["text_id"]) == u for u in expected_units):
                unit_hit_rank = i
                break

        groups = case.get("scoring") or []
        abstention_case = bool(case.get("abstention_case"))
        if not abstention_case:
            passes = [score_task60.group_pass(g, block) for g in groups]
            evidence_score = sum(passes) / len(passes) if passes else None
            evidence_forbidden_hits: list[str] = []
        else:
            evidence_score = None
            evidence_forbidden_hits = []
            for g in groups:
                for pat in g.get("forbidden_claims", []):
                    if re.search(pat, block, flags=re.IGNORECASE):
                        evidence_forbidden_hits.append(pat)

        expected_manifest = cards.get(expected_source or "", {})
        top1 = results_out[0] if results_out else None
        metadata_agrees = None
        if expected_manifest and top1:
            metadata_agrees = (
                (expected_manifest.get("sect") or "")
                == (top1["provenance"].get("sect") or "")
            ) or top1["source_id"] == expected_source

        entry_metrics = {
            "example_id": eid,
            "category": case["category"],
            "language": case["language"],
            "query": query,
            "metadata_filters_applied": [],
            "retrieval_mode": "unit_bm25+source_metadata combined (evaluate.py mode C)",
            "expected_source": expected_source,
            "expected_units": expected_units,
            "source_first_rank": first_rank,
            "source_hit_at_1": bool(first_rank == 1),
            "source_hit_at_5": bool(first_rank is not None and first_rank <= 5),
            "source_hit_at_10": bool(first_rank is not None and first_rank <= 10),
            "source_reciprocal_rank": (1.0 / first_rank) if first_rank else 0.0,
            "unit_hit_rank": unit_hit_rank,
            "unit_hit_at_10": bool(unit_hit_rank is not None and unit_hit_rank <= 10),
            "unit_reciprocal_rank": (1.0 / unit_hit_rank) if unit_hit_rank else 0.0,
            "expected_source_found": first_rank is not None,
            "top1_metadata_agrees_with_expected_source": metadata_agrees,
            "evidence_answer_score": evidence_score,
            "evidence_forbidden_hits": evidence_forbidden_hits,
            "fill_count": len(fill),
            "source_channel_matches": len(smatches),
            "n_results": len(results_out),
            "context_sha256": block_sha,
            "context_chars": len(block),
        }
        per_case_metrics.append(entry_metrics)

        evidence_rows.append(
            {
                "example_id": eid,
                "query": query,
                "retrieval": {
                    "mode": entry_metrics["retrieval_mode"],
                    "top_k": TOP_K,
                    "pool": POOL,
                    "max_metadata_fill": MAX_METADATA_FILL,
                    "metadata_filters_applied": [],
                    "dense_channel": "UnavailableDense (production lexical/source path)",
                    "normalization": NORMALIZATION_NOTE,
                    "normalized_tokens": list(norm_tokens),
                    "fill_count": len(fill),
                    "source_channel_matches": len(smatches),
                },
                "results": results_out,
                "canonical_contract": {
                    "n_results": len(canonical_objs),
                    "all_valid": all(not v for v in [r["contract_violations"] for r in results_out]),
                },
                "evidence_context": {
                    "n_items": len(ctx_items),
                    "text": block,
                    "sha256": block_sha,
                    "source_cards": [
                        s for s in dict.fromkeys(i["source_id"] for i in ctx_items)
                        if render_card(s, cards)
                    ],
                },
                "retrieval_metrics": entry_metrics,
            }
        )
        prompt_rows.append(
            {
                "example_id": eid,
                "question": query,
                "user_content": user_content,
                "context_sha256": block_sha,
                "n_evidence_items": len(ctx_items),
                "context_chars": len(block),
            }
        )
        log(
            f"  {eid} src_rank={first_rank} unit_rank={unit_hit_rank} "
            f"fill={len(fill)} ev={evidence_score} ctx={len(block)}ch"
        )

    # --- aggregates (evaluate.py formulas over source-level cases) ---
    src_cases = [m for m in per_case_metrics if m["expected_source"]]
    r5 = [1.0 if m["source_hit_at_5"] else 0.0 for m in src_cases]
    r10 = [1.0 if m["source_hit_at_10"] else 0.0 for m in src_cases]
    rrs = [m["source_reciprocal_rank"] for m in src_cases]
    unit_rrs = [m["unit_reciprocal_rank"] for m in src_cases if m["expected_units"]]
    ev_scores = [
        m["evidence_answer_score"]
        for m in per_case_metrics if m["evidence_answer_score"] is not None
    ]
    agg = {
        "n_cases": len(per_case_metrics),
        "n_source_level_queries": len(src_cases),
        "n_corpus_absence_queries": len(per_case_metrics) - len(src_cases),
        "source_recall_at_5": round(sum(r5) / len(r5), 4) if r5 else None,
        "source_recall_at_10": round(sum(r10) / len(r10), 4) if r10 else None,
        "source_mrr": round(sum(rrs) / len(rrs), 4) if rrs else None,
        "source_zero_hit": sum(1 for m in src_cases if not m["expected_source_found"]),
        "unit_mrr": round(sum(unit_rrs) / len(unit_rrs), 4) if unit_rrs else None,
        "unit_hit_at_10": sum(1 for m in src_cases if m["unit_hit_at_10"]),
        "evidence_answer_score_mean": (
            round(sum(ev_scores) / len(ev_scores), 4) if ev_scores else None
        ),
        "evidence_answer_score_full": sum(1 for s in ev_scores if s == 1.0),
        "abstention_evidence_forbidden_hits": sum(
            1 for m in per_case_metrics if m["evidence_forbidden_hits"]
        ),
        "context_chars_median": sorted(
            m["context_chars"] for m in per_case_metrics
        )[len(per_case_metrics) // 2],
        "contract_violations": contract_violations_total,
        "retrieval_mode": "unit_bm25+source_metadata combined (evaluate.py mode C, validated baseline)",
        "dense_channel": "not used (UnavailableDense; no new embedding model, no BGE-M3 rerun)",
        "not_measured": [
            "query-side sect/tradition metadata filters: NOT_APPLICABLE (frozen questions carry no "
            "query metadata; source-channel metadata matching is the metadata filtering step)",
            "graded/passage-level relevance labels: NOT_MEASURED (frozen cases carry one expected "
            "source + optional unit ids, so source-level Recall@k/MRR and unit RIR are computed; "
            "no graded qrels exist)",
            "dense/RRF fusion contribution: NOT_MEASURED (production path is lexical+source; "
            "dense unavailable by design in this task)",
        ],
    }

    OUT_EVIDENCE.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in evidence_rows),
        encoding="utf-8",
    )
    OUT_PROMPTS.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in prompt_rows),
        encoding="utf-8",
    )
    metrics_payload = {
        "task": "TASK 69 — retrieval quality over frozen Task-60 queries",
        "frozen_sha256": frozen_sha,
        "corpus": {
            "path": str(CORPUS_PATH.relative_to(REPO)),
            "documents": len(docs),
            "sources": len(cards),
        },
        "config": {
            "top_k": TOP_K, "pool": POOL, "max_metadata_fill": MAX_METADATA_FILL,
            "evidence_k": EVIDENCE_K, "text_trunc": TEXT_TRUNC,
            "bm25": {"k1": 1.5, "b": 0.75},
            "reranker": "diversify max_per_source=3",
        },
        "aggregate": agg,
        "per_case": per_case_metrics,
    }
    OUT_METRICS.write_text(json.dumps(metrics_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    log(f"wrote {OUT_EVIDENCE.relative_to(REPO)} ({len(evidence_rows)})")
    log(f"wrote {OUT_PROMPTS.relative_to(REPO)} ({len(prompt_rows)})")
    log(f"wrote {OUT_METRICS.relative_to(REPO)}")
    log("aggregate: " + json.dumps(agg, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

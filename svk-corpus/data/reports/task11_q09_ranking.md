# Task 11 — q09 Source-Ranking Analysis and Controlled Reranking Experiment

**Date:** 2026-09-18 · **Scope:** q09 ranking analysis + a controlled, post-BM25 ranking experiment evaluated on the full labelled set. Corpus, licence/gate/release untouched; no new aliases; labels unchanged; dense retrieval untouched.

---

## 1. q09 baseline (measured)

Query **`Ratnachandra`** (category `teacher_editor`, svk_specific). Expected: "The Conference-imprint dictionary sources edited by Muni Ratnachandra" = SVK-0007, SVK-0037, SVK-2002, SVK-2003, SVK-2004, SVK-2005.

Task 10 result: MRR 1.0, but R@5 = 0.167 — only ONE expected source in the top-10, repeated.

Deep run of the current implementation (top-60 / top-3000 inspection):

- **SVK-0007: 2,983 matching units, ALL at BM25 ≈ 4.1981** (the query term exists only in the per-unit author field; title×3+author field-weighting; tf=1 for every match). The top-60 is **100% SVK-0007**; ordering within the tie is doc-index order.
- The rank-1 unit's body text is literally `"^"` — pure OCR debris; it matched because provenance (author) matched.
- **SVK-0037: 17 matching units at 4.1054** — only 0.093 below the top score, but buried at **BM25 rank 1742** behind the identical-score wall.
- **SVK-2002, SVK-2003, SVK-2004, SVK-2005: 0 matching units** — "Ratnachandra" does not occur in their text or author fields (their author is Woolner).

## 2. Six-source comparison (from `manifests/source_manifest.csv`)

| source | title | author (manifest) | year | scope / conf | layer | teacher_or_author | lineage | source_quality | relation |
|---|---|---|---|---|---|---|---|---|---|
| SVK-0007 | Ardha Magadhi Dictionary Vols 2 & 5 (1927; 1938) | Muni Ratnachandraji | 1927 | CORE/MEDIUM | LEXICON | Muni Ratnachandra | S S Jain Conference | MEDIUM | edition_of (no parent) |
| SVK-0037 | Illustrated Ardha-Magadhi Dictionary Vol 1 (1923) | Muni Ratnachandraji | 1923 | CORE/MEDIUM | LEXICON | Muni Ratnachandra | S S Jain Conference | HIGH | edition_of (no parent) |
| SVK-2002 | Illustrated Ardha Magadhi Dict. Gujarati (1932) | A. C. Woolner (ed.) | 1932 | CORE/MEDIUM | LEXICON | A. C. Woolner | S S Jain Conference | MEDIUM | edition_of → SVK-2004 |
| SVK-2003 | Illustrated Ardha-Magadhi Dict. Philosophic (1930) | A. C. Woolner (ed.) | 1930 | CORE/MEDIUM | LEXICON | A. C. Woolner | S S Jain Conference | MEDIUM | edition_of → SVK-2004 |
| SVK-2004 | Ardha-Magadhi Quadrilingual Dict. Vol-2 (1927) | A. C. Woolner (ed.) | 1927 | CORE/MEDIUM | LEXICON | A. C. Woolner | S S Jain Conference | MEDIUM | edition_of → SVK-0007 |
| SVK-2005 | Illustrated Ardha-magadhi Dict. Vol-5 (1923, DLI) | Muni Ratnachandra Ji Maharaj | 1923 | CORE/MEDIUM | LEXICON | Muni Ratnachandra Ji Maharaj | S S Jain Conference | MEDIUM | edition_of → SVK-0007 |

Edition clusters (existing `edition_of`/`parent_source_id` provenance): {SVK-2002, SVK-2003, SVK-2004} → root SVK-0007; {SVK-2005} → root SVK-0007; SVK-0037 standalone. All six are one work-family in different editions/volumes.

## 3. Diagnosis

**D — a combination**, with a structural component no reranker can fix:

- **B (multiple relevant results, arbitrary ordering): YES, measured.** ~2,983 SVK-0007 units at one quantized score; ranking among them is doc-index order (the rank-1 unit is OCR debris).
- **C (insufficient source differentiation): YES, measured.** Units carry no signal distinguishing alternates: same scores, same confidence, same layer; the edition relation exists only at source level and was never visible to retrieval.
- **Structural:** 4 of 6 expected sources **cannot match the query at all** (0 units) — they are expected only through edition-family reasoning. No post-BM25 strategy can retrieve what BM25 does not return (by design, nothing is injected).
- **Not A:** retrieval is not returning *wrong* material — SVK-0007 is genuinely relevant; the failure is ordering and coverage of alternates.

## 4. Available metadata (inspected, with usability verdicts)

| field | observation | usable for ranking? |
|---|---|---|
| religious_scope_confidence | MEDIUM for all six (edition-identical) | tie-break only — no discrimination inside the cluster |
| knowledge_layer | LEXICON for all six | no discrimination |
| teacher_or_author | differs (Ratnachandra vs Woolner) but matching by it would be query-specific hard-coding — forbidden | no |
| source_quality / provenance_quality | artifact/OCR fidelity (SVK-0037 HIGH; others MEDIUM) | tie-break yes; **prior NO** — OCR fidelity is not authority/relevance |
| publication_year | 1923–1932 | deterministic tie-break (older first; documented as arbitrary, conservative citation anchor) |
| relation_type / parent_source_id | edition clusters | **yes** — provenance-backed diversity signal |
| structure confidence etc. | unit-level, not differentiation-relevant here | no |

No new authority score was invented; language was never used to infer authority.

## 5. Ranking strategies tested

All strategies run strictly AFTER BM25, on the identical BM25 candidate pool per query (top-2000), preserving BM25 rank/score as `extra.bm25_rank`/`extra.bm25_score`, reordering only, never removing:

- **A `bm25`** — identity (baseline; reproduced Task 10 metrics exactly, validating the protocol).
- **B `tiebreak`** — stable re-sort: BM25 score (quantized to 1 decimal for tie detection) → scope-confidence → source-quality → older year.
- **D `diversify`** — B, plus: per-source cap (max 3) on the presentation tier, then one best unit per edition-cluster root, then the untouched remainder.
- **C (metadata prior) — DECLINED, not implemented.** A prior would promote by metadata rather than relevance. The only candidates are scope-confidence (edition-identical, no intra-cluster effect) and source-quality (OCR fidelity — granting it prior weight would silently demote low-fidelity sources in every query without a relevance basis). Per the task rules, C was implemented nowhere.

Experiment integrity note (recorded honestly): the first harness run accidentally fed the reranker RRF-fused scores (1/(k+rank) ≈ 0.016 → quantized 0.0), collapsing the pool into a metadata-only tie; metrics crashed (zero-hit 0→5). The harness was fixed to feed true BM25 output before any results were accepted, and the baseline-identity strategy now reproduces Task 10 exactly.

## 6. Full evaluation before/after (measured, same 20-query file, pool 2000)

| strategy | R@5 | R@10 | MRR | zero | mean latency | SVK-share |
|---|---|---|---|---|---|---|
| A bm25 (baseline) | 0.760 | 0.819 | 0.905 | 0/17 | 0.0396 s | 0.550 |
| B tiebreak | 0.760 | 0.819 | 0.905 | 0/17 | 0.0451 s | 0.550 |
| **D diversify** | **0.777** | **0.836** | 0.905 | 0/17 | 0.0453 s | 0.537 |

- **tiebreak changed ZERO queries** at the metric level (its tie-breaks reorder only within identical-score regions, which never straddled the top-10 boundary anywhere except q09's — see below).
- **diversify: 2 improved (q06, q09), 0 regressed**, 15 unchanged, MRR unchanged everywhere (no first-hit changed).

## 7. q09 before/after (measured)

| | baseline (A) | diversify (D) |
|---|---|---|
| R@5 / R@10 | 0.167 / 0.167 | **0.333 / 0.333** |
| top-10 composition | SVK-0007 ×10 | SVK-0007 ×9 + **SVK-0037 at rank 4** |
| rank-1 | SVK-0007 (BM25 rank 1, score 4.1981) | unchanged (BM25 rank 1 preserved) |
| evidence preserved | — | SVK-0037 keeps `bm25_rank=1742, bm25_score=4.1054` visible |

q06 (`Ardha Magadhi dictionary`) likewise improved R@5 0.125→0.25 (SVK-2004 resurfaces via its cluster rotation).

## 8. Regressions and harm analysis (measured)

- **Regressed queries: none** (any metric) for either strategy.
- **Generic/comparative sources pushed down?** Slot distribution: CONTEXTUAL 26→23, COMPARATIVE 2→3, CANONICAL 0→3 (the q09 alternates surfacing). **First-result scope distribution is byte-identical** across all svk-specific queries — no rank-1 anywhere changed.
- **CORE/HIGH promoted by metadata rather than relevance?** No — SVK-share *decreased* (0.550→0.537). The diversify tier is relevance-gated (BM25 score first); metadata only orders within score ties.
- The q09 structural limit stands: SVK-2002/2003/2004/2005 remain unreachable for this query (0 matching units) — correctly reported as not fixable by ranking.

## 9. Is metadata-aware ranking justified?

**Yes — but only in the B+D form (deterministic tie-breaking + provenance-backed edition diversity), and only as the presentation tier.** Justification is the full-set result: 2 improved, 0 regressed, identical MRR/rank-1 everywhere, no sect-maximization (share fell), BM25 primary signal untouched, full audit trail per result. A metadata **prior** (C) is NOT justified and was not implemented. The per-source cap is a presentation-tier control — excess units remain in the list (nothing removed), and the full BM25 ranking stays available for downstream consumers.

## 10. Recommendation — next task

**One task: an adoption/integration decision pass — move `diversify` behind a documented config flag in `HybridRetriever` (default off, experimental), add a doc-note to the retrieval README, and re-freeze the evaluation baseline.** No further reranking research; the experiment is concluded. The structural q09 residual (4 sources with zero lexical evidence) belongs to a different layer entirely — source-level retrieval/aggregation — which should be a separate, future decision.

---

**Measured vs interpretation:** §1–§2, §6–§8 tables are measured (`retrieval_eval_results_task11.json`, manifest inspection). §3 diagnosis, §4 verdicts, §9 justification are engineering observations grounded in those measurements. The §5 harness-bug note is a recorded process fact.

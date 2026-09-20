# Task 13 — Source-Level Retrieval for Provenance/Metadata Queries

**Date:** 2026-09-18 · **Scope:** small experimental retrieval channel over existing manifest metadata + controlled combined policy, evaluated on the unchanged 20-query set. No new data, no embeddings, no fuzzy matching, no new aliases, BM25 scoring untouched, labels unchanged. Corpus/gate/release untouched.

---

## 1. Problem definition (from Tasks 11/12, measured)

Some relevant sources can never be retrieved at unit level because the query term exists only in source metadata and in **zero** units of body text. q09 is the concrete case: "Ratnachandra" occurs in no unit of SVK-2002/2003/2004/2005 (their manifest author is Woolner; the name lives in edition-family provenance). No unit-level method — BM25, reranking (Task 11), or embeddings (Task 12) — can retrieve evidence that does not exist in unit text.

## 2. Existing metadata used

Indexed fields (all inspected before inclusion; no blind indexing): `title`, `author` (weight 3.0 each), `text_name` (2.0 — the curated canonical-work name, e.g. "Ardha Magadhi Dictionary" ×6), `teacher_or_author` (2.0), `lineage` (1.5), `publisher` (1.0), `knowledge_layer` / `text_category` / `religious_scope` / `sect` (0.5). `source_id` is indexed for exact identifier lookup only and is explicitly **never** a semantic match. Field weights encode *reach* (how strongly a field identifies a source's subject) and rank source candidates only — they never touch unit scores. Deliberately NOT indexed: free-text `notes` (contains licence/process commentary, e.g. "DLI items carry NO licenseurl…" — matching it would surface process noise as subject evidence).

## 3. Source-level index design (`retrieval/source_channel.py`)

- Built from `manifests/source_manifest.csv` in **22 ms** for all 62 sources (measured).
- Exact-token inverted index `(field, token) → {source_id: matched_value}` through the SAME shared fold/alias pipeline as the unit channel (`expand_query_text`) — no second normalization mechanism, no fuzzy matching.
- Deterministic ranking: max field weight of a source's semantic matches, ties by more distinct matched tokens → more matched fields → source_id (pure determinism, explicitly not authority).
- **Edition-family expansion** via existing `edition_of`/`parent_source_id`: a semantic match also surfaces non-matching cluster members as `via_family` matches (weight ×0.5, documented constant), each carrying full match provenance.
- `search_identifier()` matches exact lowercased ids or their numeric part; general fragments like "svk" deliberately match nothing (measured fix: naive tokenization made 'svk' match all 62 sources).

## 4. Unit-to-source expansion mechanism

`SourceUnitExpander` draws ONE representative unit per matched source from the full document list — deliberately NOT from the BM25 pool, since the target sources have zero lexically-matching units and can never appear in any BM25 pool. Representative selection is deterministic (prefer a unit with a page locator, then longest text). Honesty guarantees, all tested: the unit did **not** match the query; every such result is labelled `retrieval_channel = source_metadata` with the full `source_metadata_match` evidence attached, `unit_bm25_rank/score = None`, and the source's provenance intact. A metadata hit never masquerades as a passage match.

## 5. Evaluation methodology

Same `configs/retrieval_eval_queries_v1.json` (17 labelled + q19 gap probe + q10/q18/q20 exploratory), same corpus (145,147 units). Modes: **A** = Task 11 baseline (BM25 + diversify tier) — reproduced Task 11's metrics exactly; **B** = source-channel only; **C** = combined with the task's five-step policy: unit results first, metadata-matched sources with **zero** unit-tier presence fill at most 3 tail slots, dedup by unit identity, channel recorded per result. No weights were invented anywhere; the only constants (field weights, family 0.5, fill cap 3) are documented reach/ordering controls, not relevance scores.

## 6. Full before/after metrics (measured)

| mode | R@5 | R@10 | MRR | zero | mean latency |
|---|---|---|---|---|---|
| A unit (Task 11 baseline) | 0.777 | 0.836 | 0.905 | 0/17 | 45.8 ms |
| B source-only | **0.811** | 0.819 | 0.882 | 2/17 | 7.2 ms |
| C combined | 0.777 | **0.895** | 0.905 | 0/17 | 53.0 ms |

- **C: 3 improved (q07 R@10 0.5→1.0, q09 R@10 0.333→0.5, q10 R@10 0.333→0.667), 0 regressed, 14 unchanged.** R@5 and MRR unchanged everywhere (metadata never displaces a top unit slot by design).
- **B is the highest-precision channel (R@5 0.811) but incomplete** (zero on q04 and q17): metadata cannot see (a) canonical-content queries whose expected sources carry no matching metadata token, and (b) Gujarati-script queries against Latin-transliterated manifest titles (cross-script is out of scope). B is a complement, not a replacement.
- Build cost: unit index 51.7 s vs source index **0.022 s**; SVK-context share A 0.550 → C 0.553 (one extra CORE slot from the q09 fill — no sect-maximization effect).

## 7. q09 six-source analysis (the key question)

| source | body-text lexical match? | source metadata match? | reached in C? | first rank / channel |
|---|---|---|---|---|
| SVK-0007 | yes (2,983 units) | author | yes | 1 · unit_bm25 |
| SVK-0037 | yes (17 units) | author | yes | 4 · unit_bm25 |
| SVK-2002 | **no (0 units)** | via_family (author, w 1.5) | no — below fill cut | — |
| SVK-2003 | **no (0 units)** | via_family (author, w 1.5) | no — below fill cut | — |
| SVK-2004 | **no (0 units)** | via_family (author, w 1.5) | no — below fill cut | — |
| SVK-2005 | **no (0 units)** | **author (direct, w 3.0)** | **yes** | **10 · source_metadata** |

**Answer: YES — source-level retrieval recovers a source that unit BM25 fundamentally cannot reach** (SVK-2005: zero body-text occurrences of "Ratnachandra", retrieved at combined rank 10 via its manifest author string "Muni Ratnachandra Ji Maharaj", labelled `source_metadata`). SVK-2002/2003/2004 are matched at source level (family tier) but lost the fill race to direct author matches (SVK-0005/0006/2001 — other Ratnachandra dictionary volumes, which are themselves legitimate Ratnachandra sources). This is a policy-knob outcome (fill cap = 3), documented as such, not a mechanism failure.

## 8. q17 / q19 analysis

- **q17 `જૈન ધર્મ`:** unchanged in C (rank-1 doctrinal hit from Task 10 stands). Source channel returns nothing — the manifest titles are Latin transliterations ("Jain Sathan Kavasi (1928)"), and cross-script matching is deliberately out of scope. Recorded as a known boundary, not a defect.
- **q19 `Acharya Anand Rishi` (corpus-gap probe):** source channel returns **nothing** — no manifest field mentions these names, so combined mode adds no fake fill; the gap interpretation is preserved and, if anything, sharpened: the source channel is *more* honest than unit BM25 here (unit BM25 still returns confident irrelevant SVK-1005 hits).

## 9. False-positive / control analysis (measured probes)

| probe | source-channel result | verdict |
|---|---|---|
| "Woolner" | SVK-2002/2003/2004/2008/2009 (author) + SVK-0007 via family | correct — all Woolner works |
| "Stevenson" | SVK-0038, SVK-1002, SVK-1003 (author) | correct |
| "Muni" (honorific) | 6 Ratnachandra-volume sources (their author strings contain "Muni") | technically correct but low-information — inherent to author-string search; acceptable, monitored |
| "Ratna" (fragment, REJECTED alias) | SVK-0005 only — whose manifest author is literally "Shri Ratna Chandra Ji Maharaja" | **true positive**, not a fuzzy leak |
| "gxyz qqq" (nonsense) | nothing | correct |
| "SVK-2004" as query | **no semantic matches** (id never treated as subject) | correct |
| "Acharya Anand Rishi" | nothing | correct (gap preserved) |
| identifier lookup "SVK-2004"/"2004" | exact hit, `identifier_only=True` | correct |

No false metadata matches found. Metadata-only results are always labelled; a fill result represents a source — it never claims the passage answers the query.

## 10. Latency / build cost (measured)

Source index build **0.022 s** (62 sources; unit index 51.7 s). Query latency: B 7.2 ms; C 53.0 ms (+7 ms over A for the source search + fill). Storage: source index is in-memory over a 62-row CSV — negligible.

## 11. Failure cases

1. **Fill-cap competition:** q09's family-matched sources (SVK-2002/2003/2004) lost tail slots to legitimate direct author matches — the policy fills at most 3 sources and prefers direct evidence; a family-aware fill policy is a possible refinement (not tuned here to avoid q09-fitting).
2. **No cross-script metadata matching** (q17 boundary): Gujarati queries cannot reach Latin-transliterated titles; would require a documented transliteration layer (a corpus-level decision, out of scope).
3. **Honorific-heavy author strings** ("Muni … Ji Maharaj") make author-field matches verbose but correct.

## 12. Recommendation — next retrieval step

**One task: adopt the combined C policy behind a documented config flag (default off) in the retrieval entry points, re-freeze the evaluation baseline at C, and record the metadata-channel contract in the retrieval docs.** The mechanism is proven (3 improved, 0 regressed, gap-probe-honest); it should graduate from experiment to option without further tuning. Remaining q09 sources (2002/2003/2004) are a family-tier ordering question for a future, separately-justified pass — not part of this adoption step.

---

**Measured vs interpretation:** §2, §3 build numbers, §6 tables, §7 table, §8, §9, §10 are measured (`retrieval_eval_results_task13.json`, probe runs). §5 policy commentary, §11 failure framing, and §12 recommendation are engineering observations. Every metadata-derived result carries its evidence inline; none claims doctrinal relevance.

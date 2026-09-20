# Task 9 — Deterministic Romanization Folding + Alias Retrieval

**Date:** 2026-09-18 · **Scope:** retrieval-layer normalization and re-measurement ONLY. Corpus files, licence decisions, gate rules and release contents untouched. No dense embeddings, no stemming, no fuzzy matching.

---

## 1. Task 8 baseline (measured)

From `data/reports/retrieval_eval_results.json` (BM25-only, same 20-query set, 145,147 RAG units):

| metric | value |
|---|---|
| Recall@5 | 0.697 |
| Recall@10 | 0.721 |
| MRR | 0.804 |
| queries with zero relevant results | 2 / 17 |
| mean query latency | 0.0433 s |
| index build | 5.8 s |
| SVK-context share (svk-specific top-10 slots, CORE+HIGH) | 0.575 |

Dominant failure mode (documented in Task 8): romanization/period-spelling variance — "Sutrakritanga" vs "Sutrakrtanga", "Uttaradhyayana" vs historical "Utradhyayan", "Ratnachandra" vs "Ratna Chandra Ji".

## 2. Changes made

* **New** `src/svk_corpus/retrieval/normalization.py` — deterministic, retrieval-only normalization: (a) one-directional Latin diacritic folding map; (b) alias OR-expansion loaded from the versioned config; (c) phrase rules for multi-token variants; (d) a single `expand_query_text()` used by BOTH the index and the query so variants meet in folded-term space.
* **`configs/retrieval_aliases_v1.json`** (new) — evidence-cited alias table + explicit `rejected_variants` list; the config is the single source of truth (the module refuses to hardcode entries).
* **`bm25.py`** — index construction and query tokenization now both call `expand_query_text()`; `tokenize` moved to `normalization.py` and re-exported. Scoring, `k1/b`, `allowed` filtering and result objects unchanged.
* **`evaluate.py`** — `label` / `out_name` arguments so the Task 9 run wrote `retrieval_eval_results_task9.json` instead of overwriting the Task 8 baseline; fixed the hardcoded stdout filename.
* **`tests/test_retrieval.py`** — 10 new regression tests (see §7).

Not changed: BM25 itself (still plain Okapi), the corpus, provenance objects, dense interface status (still unavailable, still honestly marked).

## 3. Alias/folding rules implemented

**Folding (unconditional for Latin-script tokens; Indic-script tokens pass through untouched):**

`ā→a ī→i ū→u ē→e ō→o ṛ→ri ṝ→ri ḷ→l ḹ→l ṅ→n ñ→n ṇ→n ṭ→t ḍ→d ś→sh ṣ→sh ṃ→n ḥ→(deleted)`

Idempotent by construction (each rule maps disjoint codepoint sets). No cross-script transliteration (explicitly out of scope; listed as rejected).

**Aliases (all evidence-cited; full reasoning in the config):**

| canonical key | variant | mechanism | basis | confidence |
|---|---|---|---|---|
| sutrakrtanga | sutrakritanga | single-token OR | corpus (4,868 units) + Task 8 query | HIGH |
| uttaradhyayana | utradhyayan | single-token OR | corpus (1,984 units) + Task 8 query | HIGH |
| uttaradhyayana | uttarajjhayana | single-token OR | corpus (2 units, Prakrit title form) | MEDIUM |
| ratnachandraji | ratnachandra | single-token OR | corpus (12,177 units) + Task 8 query | HIGH |
| ratnachandraji | "ratna chandra ji" | **phrase rule** (injects fused term; parts never become keys) | Task 8 documented failure form | MEDIUM |

**Rejected (recorded in the config with reasons):** `ratna chandra` (0 corpus occurrences), `sthankavasi ↔ sathan kavasi` (different romanization systems naming different works/editions — merging risks conflating distinct sources), `aa→a` vowel folding (no demonstrated failure), global "ji" stripping (would merge unrelated names), cross-script transliteration (no evidence base).

**Religious-scope guard:** every entry maps SPELLINGS for search only; no religious, textual, or canonical equivalence is asserted between works, recensions, or traditions. This statement is part of the config's `policy` block.

## 4. Before vs after metrics (measured, same query file, labels unchanged)

| metric | Task 8 (before) | Task 9 (after) | Δ |
|---|---|---|---|
| Recall@5 | 0.697 | **0.756** | +0.059 |
| Recall@10 | 0.721 | **0.838** | +0.117 |
| MRR | 0.804 | **0.871** | +0.067 |
| zero-relevant queries | 2 / 17 | **0 / 17** | −2 |
| mean query latency | 0.0433 s | 0.046 s | +6% |
| index build | 5.8 s | 53.5 s | +9.2× (one-time) |
| SVK-context share | 0.575 | 0.575 | 0 |

Interpretation: both zero-hit queries are eliminated, and the MRR delta is exactly accounted for by the two improved queries (q03 +1.0, q05 +0.143, over 17 queries ⇒ +0.067) — no other query's ranking changed materially.

## 5. Query-level improvements (measured)

Per-query verdict over the 17 labelled queries (MRR delta; |Δ|≤0.001 = "same"):

* **2 improved**, **15 same**, **0 regressed**.
* **q03 `Sutrakritanga`** (canonical_translation): total miss → **SVK-1001** found, R@5 0→1.0, MRR 0→1.0. Cause fixed: alias `sutrakritanga → sutrakrtanga` (corpus spelling, 4,868 units).
* **q05 `Uttaradhyayana Sutra`** (canonical_translation): SVK-0016 not in top-10 → found at rank 7 (MRR 0→0.143; R@5 still 0.0 because the first hits remain other canonical works mentioning the sutra). Cause fixed: alias `uttaradhyayana → utradhyayan` (historical spelling, 1,984 units).
* **q09 `Ratnachandra`** (teacher_editor): first hit changed SVK-2005 → SVK-0007; R@5 0.167 unchanged — the alias works (expected sources are reached), but six expected dictionary sources compete and only SVK-0007 reaches the top ranks. Ranked as "same" by the metric.

## 6. Remaining failures (measured)

* **q09 (`Ratnachandra`, R@5 0.167):** expected set spans 6 sources; only SVK-0007 in top-10. Not a spelling problem anymore — a *ranking* problem across many equally-legal matches.
* **q17 (`જૈન ધર્મ`, R@5 0.6):** unchanged. Indic-script tokens deliberately pass through folding untouched; the residual variance is *within*-Gujarati script morphology/orthography, which has no evidenced alias table yet. Next-task candidate (see §10).
* **q19 (Acharya Anand Rishi corpus-gap probe):** still returns 5 confident, irrelevant hits (SVK-1005). Expected — a lexical index cannot signal corpus absence; the probe correctly documents the gap (retrieval-layer normalization cannot and should not fix this).
* Exploratory q10/q18/q20 remain descriptive (unlabelled by design).

**Regressions: none.** No query's metric decreased; the sect-context distribution is unchanged (§9).

## 7. Regression tests (all passing)

`tests/test_retrieval.py::TestRomanizationFoldingAndAliases` (10 tests):

1. folding is deterministic and idempotent (incl. `Sūtrakṛtāṅga→Sutrakritanga`, `sādhvī→sadhvi`);
2. Indic-script tokens pass through untouched (Devanagari + Gujarati);
3. alias expansion is deterministic, original term always first, fold+alias compose;
4. `Sutrakritanga` ↔ `Sutrakrtanga` retrieve the same intended source (both directions);
5. `Uttaradhyayana` / `Utradhyayan` / `Uttarajjhayana` all reach the same units;
6. spaced honorific query "Ratna Chandra Ji" reaches the fused corpus form;
7. **no accidental merges**: "ji" and "chandra" are not alias keys — a bare "ji" query does not summon Ratnachandra units (this test caught a real design flaw during development, fixed by the phrase-rule mechanism);
8. unrelated near-miss terms are not merged (no stemming/fuzzy behaviour);
9. original corpus text and full provenance are untouched by alias-driven matching (text, `search_text`, teacher, lineage, locator verified byte-identical);
10. the alias config is evidence-bounded: required keys present, rejected variants absent as keys, `rejected_variants` and the `orthographic_only` policy documented in the file.

**Full suite: 122/122 pass** (102 existing + 10 Task 8 + 10 new).

## 8. Latency impact (measured)

* **Query latency:** 43.3 ms → 46.0 ms mean (+6%) — queries now carry OR-expanded alias terms. Still well under 50 ms.
* **Index build:** 5.8 s → 53.5 s (+9.2×) — every document token now passes through folding + alias expansion at index time. One-time cost per index build; acceptable for a 145k-unit prototype. Noted as the main scaling consideration if the index is rebuilt per-request (it isn't — build once, query many).

## 9. Sect-context impact (measured)

SVK-specific top-10 slot distribution: **identical before/after** (CORE 34, CONTEXTUAL 26, HIGH 12, UNKNOWN 6, COMPARATIVE 2; share 0.575). Expected: the three affected queries target canonical/lexicographer sources, not sect-context queries. The normalization layer neither favours nor penalizes any tradition — it only lets variant spellings of the *same* term meet.

## 10. Recommendation — next retrieval improvement

**One change: a within-script (Devanagari/Gujarati) normalization census + evidenced alias table v2.** The remaining measured failure (q17, Gujarati) is intra-script orthographic variance; the Task 9 method (corpus spelling census → evidence-cited entries → deterministic application → re-measure on the unchanged eval set) applies directly. Cross-script transliteration and any stemming remain rejected until corpus evidence demonstrates the need.

*(Separately noted, not retrieval-normalization: q09's residual is a ranking/reranking problem, and q19 is a corpus-gap signal — both out of scope here.)*

---

**Measured vs interpretation:** all tables above are measured from `retrieval_eval_results.json` (Task 8) and `retrieval_eval_results_task9.json` (Task 9). Interpretive statements are marked as such. The Task 8 baseline file was preserved unmodified.

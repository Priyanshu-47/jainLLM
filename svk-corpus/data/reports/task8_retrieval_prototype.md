# Task 8 — Hybrid Retrieval Evaluation Prototype

**Date:** 2026-09-18 · Prototype over the existing release only. No acquisition, no corpus/gate/release changes, no model training, no UI.

## 1. WHAT WAS BUILT

A small retrieval-evaluation layer under the existing package (`src/svk_corpus/retrieval/`):

| module | purpose |
|---|---|
| `documents.py` | Streams the release JSONL into `RetrievalDocument` objects with provenance joined from `manifests/source_manifest.csv` (religious_scope, knowledge_layer, teacher_or_author, lineage). `search_text` provides field-weighted indexing text (title ×3 + author + section + body). |
| `bm25.py` | Okapi BM25 (k1=1.5, b=0.75) over a Unicode-aware tokenizer; full inverted index in memory. |
| `dense.py` | `DenseRetriever` interface; `UnavailableDense` = the honest production state here; `HashDense` = a clearly-named deterministic **test double** used only to exercise fusion in unit tests — never for metrics. |
| `fusion.py` | Reciprocal Rank Fusion (k=60) with identity-safe keys for unhashable documents, first-appearance tie-break; `HybridRetriever` = metadata prefilter → BM25 (+dense) → RRF → `RetrievalResult` objects that refuse to drop provenance. |
| `evaluate.py` | Runs the versioned query set, computes metrics, sect-context analysis, writes `data/reports/retrieval_eval_results.json`. |

## 2. EXISTING CORPUS USED

`data/release/rag_corpus.jsonl` — **145,147 released RAG units** (the validated post-Round-2 release; untouched). Provenance joined from the 62-row source manifest. Nothing was re-extracted, re-normalized, or modified.

## 3. RETRIEVAL ARCHITECTURE

Query → metadata prefilter (`where={field: value}` on any document field, incl. religious_scope/knowledge_layer/source_id) → BM25 lexical retrieval → dense retrieval (interface only; **unavailable here**) → RRF fusion → top-k provenance-preserving results (`source_id, title, author, year, citation, locator{page,section}, sect, religious_scope(+confidence), knowledge_layer, teacher_or_author, lineage, per-method ranks, fused score`).

## 4. QUERY-SET COMPOSITION

`configs/retrieval_eval_queries_v1.json` — 20 hand-written queries, **explicitly labelled a prototype retrieval evaluation set, not a validated benchmark**. Composition: 4 canonical-translation, 1 canonical-Devanagari, 2 SVK-terminology (lexicon), 1 Prakrit scholarship, 1 teacher/editor name, 3 SVK-history, 2 historical/doctrinal-English, 1 French reference, 1 Gujarati-script, 1 doctrinal-Devanagari (exploratory), 1 teacher **corpus-gap probe** (Anand Rishi — documented absent from the corpus), 1 generic multi-tradition (exploratory). 17 queries carry source-level expected-ids grounded in the manifest; 3 carry none by design. No invented answers or sources.

## 5. METRICS (measured, BM25-only)

| metric | value | basis |
|---|---|---|
| Recall@5 (source-level) | **0.697** | 17 labelled queries |
| Recall@10 (source-level) | **0.721** | 17 labelled queries |
| MRR | **0.804** | 17 labelled queries |
| Queries with zero relevant results | **2 / 17** (q03, q05) | both romanization-variant failures |
| Mean retrieval latency | **43.3 ms** (max 190.6 ms) | includes full ranking; index build 5.8 s |

Development note, reported for honesty: the first run (indexing unit body text only) measured Recall@5 0.388 / MRR 0.363 with 9/17 zero-hits. The diagnosis — title/author queries ("Kalpa Sutra", "Woolner", "Risabha Deva") cannot match units whose bodies never contain the title — led to the standard field-weighted indexing fix above. The reported metrics are the post-fix measurement; both runs are in the JSON history of this task's log.

Modes B and C (dense-only, hybrid-with-dense) were **not measurable**: no embedding model exists in this zero-dependency environment and the task forbids model downloads. The fusion path itself is unit-tested with the `HashDense` double.

## 6. SECT-CONTEXT ANALYSIS

Across the 8 queries marked `svk_specific` (incl. the Anand-Rishi gap probe), top-10 slot distribution by `religious_scope`:

| scope | slots | share |
|---|---|---|
| CORE_STHANAKAVASI | 34 | 42.5% |
| CONTEXTUAL_JAIN | 26 | 32.5% |
| HIGH_STHANAKAVASI_RELEVANCE | 12 | 15.0% |
| UNKNOWN | 6 | 7.5% |
| COMPARATIVE_OTHER_TRADITION | 2 | 2.5% |

- **CORE+HIGH share: 57.5%** of slots; **65.7% excluding the gap probe** (which contributes only contextual hits by definition).
- **First result** for the flagship query "Sthanakvasi Jain sect" is the sect-treating scholarship (SVK-0038, HIGH_STHANAKAVASI_RELEVANCE) — correct context.
- Per the task rule, generic-Jain hits are **not scored as errors**: q12 ("Jain Conference history") and q17 (Gujarati જૈન ધર્મ) are defined loosely, and dictionary material legitimately answers terminology queries. The 32.5% contextual share is dominated by q19's gap behaviour and the lexicon layer, not by misranking.
- Exploratory generic query q20 ("karma doctrine Jain") returned SVK-0038 (HIGH_STHANAKAVASI_RELEVANCE) at rank 1 — the corpus's best available treatment of karma in English.

## 7. EXAMPLE RETRIEVALS (measured top hits)

- **q10 "Sthanakvasi Jain sect"** → 1. [SVK-0038] *Notes on Modern Jainism* (1910) — "list of the differences between the two Sects"; 2–3. [SVK-1005] contextual survey (index entries: "Śvetāmbara, a Jain sect").
- **q17 "જૈન ધર્મ"** → Gujarati-script dictionary units from SVK-2002/SVK-2004 (CORE) and SVK-2014 — real Gujarati retrieval over previously-nonexistent script coverage; all 5 expected Gujarati sources in top-10 (R@10 = 1.0).
- **q18 "अहिंसा"** → Paia-sadda-mahannavo lexicon entries listing the term's Prakrit variants (अहिंसा--अहिंगरी...) — the dictionary behaves exactly as a terminology entry point.
- **q04 "उत्तराध्ययन सूत्र"** → SVK-0016 at rank 1 (MRR 1.0) — Devanagari exact-match works.

## 8. FAILURE CASES (all measured)

1. **Romanization/variant mismatch is the single dominant failure mode.** q03 "Sutrakritanga" (corpus: "Sutrakrtanga"), q05 "Uttaradhyayana" (corpus title: period spelling "Utradhyayan Sutar"), q11 "Sathan Kavasi" (query uses modern "Sthanakvasi" spelling, corpus uses the period form — the reverse of q10), q09 "Ratnachandra" (metadata variants: "Ratnachandraji" vs "Ratna Chandra Ji" — token-splitting). Exact-match BM25 cannot bridge these; 2/17 queries are total misses for this reason, and q06/q09/q10 under-recall partially for it.
2. **Competition among near-identical lexicon sources** caps Recall@10 (q06: 2/8 dictionary sources in top 10 — all competing units match equally well).
3. **Corpus gaps are invisible to retrieval**: q19 ("Acharya Anand Rishi") returns the colonial survey confidently repeated ×5. Retrieval cannot know the corpus cannot answer; no abstention logic exists in a ranker.
4. Translations-vs-originals are not distinguished at ranking time (a Latin-script dictionary entry can outrank an English canonical unit for an English query).

## 9. DENSE RETRIEVAL AVAILABILITY

**Not available** — honestly reported. The project is zero-dependency (`dependencies = []`): no numpy, no sentence-transformers/onnx model, and no model was downloaded per the task constraint. `DenseRetriever` is implemented as a real interface (build-time doc embedding, query-time cosine, prefilter-aware), `UnavailableDense` is the default wired into evaluation, and `HashDense` exists solely so the RRF/hybrid plumbing is test-covered. The moment a small multilingual encoder (e.g. a DistilUSE-class or Indic sentence model) is added as an optional dependency, mode B/C runs require no further code.

## 10. ENGINEERING OBSERVATIONS

- **Field-weighted provenance indexing was the difference between failure and adequacy** (+0.31 Recall@5). In a citation-first corpus, provenance *is* searchable content.
- A pure-Python BM25 over 145k units indexes in ~6 s and answers in ~43 ms — entirely adequate for a prototype; a real service would need an ANN/inverted store only for the dense channel.
- `structure_confidence`/`unit_type` (verse/paragraph/chunk) ride along in every result and are available for future rank filtering.
- The evaluation harness is deterministic end-to-end (same index, same scores), so regressions are detectable in CI via the unit tests + a smoke re-run.

## 11. WHAT SHOULD BE CHANGED NEXT

**One change: add romanization-variant handling to the lexical channel** — a deterministic alias/normalization layer (transliteration folding, e.g. ṛ→ri, aa→a; a small curated alias table for period spellings: Uttaradhyayana/Utradhyayan, Sutrakrtanga/Sutrakritanga, Sthanakvasi/Sathan Kavasi, Ratnachandra/Ratna Chandra) applied at index *and* query time. This directly targets every measured failure in §8 and is fully in keeping with the project's no-LLM, auditable-transformation principle. Everything else (real dense channel, abstention logic, benchmark validation) is explicitly future work, not next.

**Separation per the task:** §5–§9 numbers are *measured*; §8.4 and the latency observations are *implementation observations*; abstention logic, dense-model choice and benchmark validation are *hypotheses/future work*.

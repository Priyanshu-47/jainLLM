# Task 76 — Retrieval Service Design Note

Status: implemented and validated offline. BM25 remains the production
default; H3_RRF20 is an explicit, opt-in candidate. This note documents the
small retrieval abstraction introduced by `src/svk_corpus/retrieval/service.py`,
its feature-flag semantics, and the boundary that keeps it retrieval-only.

## 1. Why a service layer

The Task-74/75 hybrid candidate (BASE + H3_RRF20) was proven in prototype
scripts (`experiments/task74/task74_experiment.py`). Production, however,
serves BM25 through `src/svk_corpus/retrieval/evaluate.py` (`mode="C_combined"`:
BM25 pool → diversify → source-metadata tail). Before any hybrid rollout can
even be reviewed, the candidate needs a single, testable entry point that

* keeps the H1 BM25 path **byte-compatible** with `evaluate.py`, and
* exposes H3_RRF20 behind an explicit flag, with observable fallback when the
  dense artifacts are unavailable or fail verification.

`RetrievalService` is that entry point. It does **not** replace
`evaluate.py` — it wraps the same primitives (`BM25Index`, `Reranker`,
`SourceIndex`, `SourceUnitExpander`) and is the interface a future serving
layer would call.

## 2. Modes and the production default

```
RetrievalMode.BM25          # H1 — production default, mode C_combined
RetrievalMode.HYBRID_RRF20  # H3_RRF20 — opt-in candidate
```

`RetrievalPolicy` defaults to `BM25`. The shipped `configs/policy.toml`
`[retrieval]` section sets `mode = "bm25"`; this file is the authoritative
record of the default. Hybrid can only be enabled by an explicit, deliberate
choice (see §4). There is no code path that silently defaults to hybrid.

## 3. The two paths

### 3.1 H1 (BM25) — `_search_bm25`

Reproduces `evaluate.py` `mode="C_combined"` exactly:

1. `BM25Index(docs, k1=1.5, b=0.75).search(query, top_k=pool)` with
   `pool = 2000`.
2. `Reranker(strategy="diversify", max_per_source=3)` on the pool.
3. Take the diversified unit tier up to `top_k`.
4. Source-metadata tail (max `max_metadata_fill = 3`) fills remaining slots
   **only** for sources with zero lexical presence in the pool — the same
   condition as production.

Verified byte-compatible by `test_h1_ranking_matches_production_mode_c` and
by the frozen-benchmark reproduction (H1 unit@5 = 0.3846, src@5 = 0.9130 —
matches Task-74 exactly).

### 3.2 H3_RRF20 — `_search_hybrid`

Reproduces the Task-74/75 candidate exactly:

1. **Full** BM25 ranking (`top_k=INF`) → `bm25_rank` per text_id.
2. **Full** dense ordering: numpy `emb @ q_vec`, `argsort(-scores,
   kind="stable")`, 1-based dense ranks.
3. RRF fusion: `score = Σ 1/(k + rank)` over both lists, `k = rrf_k = 20`.
   Tie-break: `np.lexsort((arange, dense_rank, bm25_rank_or_INF, -score))` —
   identical to Task-74's `rrf_fuse`.
4. Evidence window `evidence_k = 5`, `text_trunc = 500`.
5. Channel: `unit_bm25` if the text_id was in the BM25 ranking, else `dense`.
   **No source-metadata fills** (that is H4, which was not recommended).

Verified by the frozen-benchmark reproduction (H3 unit@5 = 0.5385, src@5 =
0.9783 — exact match to Task-74's pre-registered aggregates) and by the
determinism/tie-break tests.

## 4. Feature flags, fallback, and shadow

Configuration precedence: defaults → `configs/policy.toml` `[retrieval]` →
environment variables. Environment variables never edit the file; a typo in
`SVK_RETRIEVAL_MODE` is **ignored** (falls back to the file/default value) so
a typo cannot accidentally enable hybrid.

| Flag | Default | Meaning |
|---|---|---|
| `mode` | `"bm25"` | `bm25` or `hybrid_rrf20` |
| `fallback_on_dense_failure` | `true` | fall back to BM25 with a logged reason instead of raising |
| `strict_dense` | `false` | if `true`, raise `DenseIndexUnavailable` instead of falling back |
| `shadow_mode` | `false` | offline shadow replay (BM25 authoritative) |
| `SVK_RETRIEVAL_MODE` | — | runtime override of `mode` |
| `SVK_RETRIEVAL_SHADOW` | — | runtime override of `shadow_mode` |
| `SVK_RETRIEVAL_STRICT` | — | runtime override of `strict_dense` |

### Dense-artifact integrity

`load_dense_index(index_dir, docs)` refuses to serve from artifacts that fail
verification: missing directory, SHA-256 mismatch between `corpus_emb.f16.npy`
and `index_meta.json`, or a doc-count mismatch all raise
`DenseIndexUnavailable`. Optional `verify_alignment=True` additionally
recomputes the corpus-text and doc-id SHA-256 commitments. When hybrid is
requested but the index is unavailable (and `fallback_on_dense_failure=true`),
the service serves BM25 and records an explicit `fallback_reason`; the
fallback is logged. `strict_dense=true` turns the same condition into an
exception. Both behaviours are covered by tests and by the benchmark's
failure probes.

### Shadow replay

Shadow mode (offline) runs BM25 as the authoritative path and evaluates
H3_RRF20 alongside; the hybrid ranking is recorded but **never** replaces the
BM25 answer. See `data/reports/task76_shadow.json`.

## 5. Retrieval-only boundary

`RetrievalService` exposes `search()` and `dense_stats()` only. It has no
`generate`, `build_prompt`, `build_context`, `answer`, `chat`, or `complete`
method — enforced by `test_service_does_not_expose_prompt_or_generation_*`.
Prompt construction and answer generation remain the responsibility of the
generation layer; this service returns ranked, provenance-carrying evidence
only. `SearchResponse.summary()` logs the mode actually used, latency, and an
optional `query_id` — never the raw query text or result text.

## 6. What this does NOT do

* No training, fine-tuning, DAPT-02, or SFT-03.
* No new embedding model, reranker, query expansion, or cross-encoder.
* No frozen-benchmark modification.
* No automatic production-default change — BM25 remains the default
  throughout; promoting H3_RRF20 is a separate, explicit rollout decision.
* Query-encoder latency is **UNRESOLVED** in this environment (torch is
  absent locally); the benchmark uses the pre-computed Task-74 query
  embeddings (`queries_emb.f32.npy`). Encoder latency must be measured in the
  target serving environment before any default change.

## 7. References

* `src/svk_corpus/retrieval/service.py` — the service.
* `configs/policy.toml` `[retrieval]` — the default.
* `tests/test_retrieval_service.py` — 39 regression tests.
* `experiments/task76/task76_benchmark.py` — frozen-benchmark regression.
* `experiments/task76/task76_shadow.py` — offline shadow replay.
* `data/reports/task76_production_readiness.{md,json}` — readiness report.

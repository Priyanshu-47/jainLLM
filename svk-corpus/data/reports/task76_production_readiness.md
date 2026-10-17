# Task 76 — Hybrid RAG Production Readiness

**Candidate:** BASE + H3_RRF20 (the configuration recommended by Task 75).
**Scope:** engineering and validation only — this task prepares the candidate
for a *separate* rollout review. It is **not** an automatic rollout, and the
BM25 production default is unchanged.

## Final verdict

> **READY_FOR_SEPARATE_ROLLOUT_REVIEW**

The retrieval service is implemented, the H1 BM25 path is byte-compatible
with production, the H3_RRF20 candidate reproduces its frozen Task-74
aggregates exactly through the new interface, provenance is preserved and
contract-valid, failure behaviour is explicit and observable, and the test
suite is baseline-equal. Query-encoder latency is UNRESOLVED in this
environment and the full-list BM25 fusion cost is a documented optimisation
opportunity — both must be settled in the serving environment before any
production-default change. That is why the verdict is a review, not a rollout.

## Final status block

| Field | Value |
|---|---|
| Integration implemented | **YES** |
| Shadow validation | **OFFLINE** |
| BM25 compatibility | **PASS** |
| H3_RRF20 reproducibility | **PASS** |
| Evidence provenance tests | **PASS** |
| Performance gates | **UNRESOLVED** |
| Training started | **NO** |
| Production default changed | **NO** |

## Hard stops observed

| Hard stop | Status |
|---|---|
| No training / fine-tuning | NO training started |
| No DAPT-02 / SFT-03 | Not touched |
| No new embedding model / reranker | Frozen Task-74 bge-m3 artifact only |
| No frozen-benchmark modification | sha `06625f72…` verified unchanged |
| No automatic production-default change | BM25 remains the default |
| BM25 stays production default throughout | YES |

## 1. What was built

* **`src/svk_corpus/retrieval/service.py`** — a small retrieval abstraction
  (`RetrievalService`) with two modes: `BM25` (H1, production default) and
  `HYBRID_RRF20` (opt-in candidate). Retrieval-only: no prompt building, no
  answer generation.
* **`configs/policy.toml` `[retrieval]`** — authoritative default
  `mode = "bm25"`, plus fallback/strict/shadow knobs. Environment overrides
  (`SVK_RETRIEVAL_MODE`, etc.) can opt in to hybrid; a typo is ignored, so a
  mistake cannot enable hybrid by default.
* **`tests/test_retrieval_service.py`** — 39 regression tests covering the
  ten required behaviours (BM25 byte-compatibility, H3 reproduction,
  determinism/tie-breaks, fusion duplicates, provenance, dense-failure
  handling, contract enforcement, no-silent-interface-change, flag safety,
  shadow semantics) plus additional failure-discovery tests.
* **`experiments/task76/task76_benchmark.py`** — frozen-benchmark regression
  (H1 vs H3_RRF20) with latency, index footprint, and failure probes.
* **`experiments/task76/task76_shadow.py`** — offline shadow replay
  (BM25 authoritative, hybrid alongside).

## 2. Quality regression (frozen 47-case benchmark)

Frozen bench sha `06625f72190e3ae130447345afdc04342bd19cb76f842285706480cba7765b81`
verified. Dense index alignment (corpus text / doc ids / queries / 164238×1024)
recomputed and matched before the run.

| Metric | H1 (BM25) | H3_RRF20 (hybrid) | Pre-registered (Task-74) |
|---|---|---|---|
| unit recall@5 | **0.3846** ✓ | **0.5385** ✓ | H1 0.3846 / H3 0.5385 |
| source recall@5 | **0.9130** ✓ | **0.9783** ✓ | H1 0.9130 / H3 0.9783 |
| unit MRR | 0.3333 | 0.4618 | — |
| source MRR | 0.8040 | 0.9174 | — |
| contract violations | 0 | 0 | 0 |

Both reproduction gates **PASS** (exact match within 1e-3). H3_RRF20 gains
**+0.1539 absolute unit recall@5** and **+0.0653 source recall@5** over the
production BM25 path, through the service interface, with zero contract
violations.

## 3. Offline shadow replay

Shadow validation is **OFFLINE** (no live serving API exists in this
pipeline). BM25 is authoritative and served unchanged; H3_RRF20 is evaluated
alongside and never replaces the answer.

| Measure | Value |
|---|---|
| Authoritative mode observed | `bm25` (unchanged) |
| Shadow never replaced authoritative | true |
| overlap@5 (authoritative vs shadow, mean) | 0.3305 |
| Hybrid recovers a BM25 top-5 unit miss | **6** |
| Hybrid regresses a BM25 top-5 unit hit | **0** |
| **Net delta in unit hits@5** | **+6** |

The hybrid candidate strictly *adds* expected-unit hits at the top of the
ranking under shadow — 6 recoveries, 0 regressions — while the served BM25
answer is untouched.

## 4. Performance (measured)

Latency excludes one-time corpus/dense-index load; measured per query through
the service on 164,238 docs (CPU, local).

| Component | H1 (BM25) | H3_RRF20 |
|---|---|---|
| total (mean / median / p95) | 0.142 / 0.154 / 0.258 s | **0.377 / 0.288 / 1.355 s** |
| BM25 full ranking | — (pooled 2000) | 0.294 s mean |
| dense search (matmul + argsort) | — | 0.037 s mean |
| RRF fusion | — | 0.061 s mean |
| first query (cold) | 0.159 s | 0.286 s |

Index footprint: 336 MB on disk (f16), 673 MB loaded (f32), 1.9 s load with
full alignment verification.

**Performance gates: UNRESOLVED.** The retrieval-side components are measured
and reported (PASS for measurement), but:

* **Query-encoder latency is UNRESOLVED** — torch is absent in this
  environment, so the benchmark uses the pre-computed Task-74 query
  embeddings (`queries_emb.f32.npy`). Encoder latency must be measured in the
  target serving environment.
* **Full-list BM25 fusion is the dominant cost** (~0.29 s mean) because
  H3_RRF20 faithfully fuses the *full* BM25 ranking (`top_k=INF`, matching
  Task-74). Fusing a truncated top-N list would be faster but is a semantic
  change requiring re-validation; it is an optimisation option, not a
  prerequisite for the review.

Hybrid is ~2.6× the mean latency of H1 (0.377 s vs 0.142 s) at the retrieval
layer; whether that meets a serving SLA is an environment decision for the
rollout review.

## 5. Failure behaviour (verified)

| Scenario | Behaviour | Verified |
|---|---|---|
| Dense index dir missing | fall back to BM25 + logged `fallback_reason` | PASS |
| Dense index missing, `strict_dense=true` | raise `DenseIndexUnavailable` (fail-closed) | PASS |
| SHA-256 mismatch on `corpus_emb.f16.npy` | raise `DenseIndexUnavailable` at load | PASS |
| Doc-count mismatch | raise `DenseIndexUnavailable` at load | PASS |
| No query encoder and no precomputed embedding | fall back to BM25 + logged reason | PASS |
| Typo in `SVK_RETRIEVAL_MODE` | ignored — cannot enable hybrid | PASS |

## 6. Tests

* New file `tests/test_retrieval_service.py`: **39 tests, all pass.**
* Full suite: **501 ran, 0 failures**, 2 pre-existing faiss import errors and
  1 skip — **baseline-equal** (baseline was 462 / 2 errors / 1 skip before
  this task's additions).

## 7. What this task did NOT do

* No training, fine-tuning, DAPT-02, or SFT-03.
* No new embedding model, reranker, or query expansion.
* No frozen-benchmark modification.
* No production-default change — BM25 remains the default.
* No generation replay — Task-75's generation results are referenced, not
  reproduced (this task is retrieval-only).

## 8. Artifacts

| Artifact | Path |
|---|---|
| Retrieval service | `src/svk_corpus/retrieval/service.py` |
| Config default | `configs/policy.toml` `[retrieval]` |
| Regression tests | `tests/test_retrieval_service.py` |
| Benchmark script | `experiments/task76/task76_benchmark.py` |
| Shadow script | `experiments/task76/task76_shadow.py` |
| Benchmark report | `data/reports/task76_benchmark.json` |
| Shadow report | `data/reports/task76_shadow.json` |
| Readiness report (JSON) | `data/reports/task76_production_readiness.json` |
| Design note | `docs/TASK76_RETRIEVAL_DESIGN.md` |
| Flag / rollback doc | `docs/TASK76_FEATURE_FLAG_ROLLBACK.md` |

## 9. Recommended next step

A **separate rollout review** should decide whether/where to enable
`hybrid_rrf20`, conditioned on: (a) measuring query-encoder latency in the
target serving environment, (b) deciding full-list vs top-N fusion, and
(c) an explicit, logged change of `mode` from `bm25` to `hybrid_rrf20` in the
target environment — with the documented rollback (`SVK_RETRIEVAL_MODE=bm25`)
ready. No such change is made by this task.

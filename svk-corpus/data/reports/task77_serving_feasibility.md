# Task 77 — Hybrid RAG Serving Feasibility Gate

**Candidate:** BASE + H3_RRF20 (Task-75 recommended; Task-76 verdict
`READY_FOR_SEPARATE_ROLLOUT_REVIEW`).
**Scope:** resolve the operational blockers from Task 76 (encoder latency,
fusion cost) before any production rollout. BM25 remains the production
default throughout; this task does not deploy or enable hybrid by default.

## Final verdict

> **BLOCKED_ON_SERVING_ENVIRONMENT**

No intended serving environment is identified anywhere in this repository
(no deployment config, host spec, Dockerfile, CI, or infrastructure-as-code).
Per the task's own guidance, the missing decision is documented
(`docs/TASK77_SERVING_ENV_AUDIT.md`) and serving readiness is **not** claimed.
All retrieval-side work that *can* be done without a serving target is
complete, green, and recorded below — so the gate is a clean block on one
decision, not a failure of the retrieval candidate.

## Final status

| Question | Status |
|---|---|
| Encoder latency measured in the intended environment? | **NO** — no intended serving environment exists; encoder not run locally (no torch/GPU; large-install constraint). |
| Fusion a material bottleneck? | **YES** — was ~19 % of H3 p50 (~67 ms of 338 ms); optimised with an exact-equivalent vectorised update (~1.3×, ~12 ms e2e saving), adopted with regression tests. |
| All frozen retrieval checks pass? | **YES** — frozen-benchmark `REPRODUCTION_PASS` (H1 0.3846/0.9130, H3 0.5385/0.9783); 503 tests, 0 failures, baseline-equal; artifact hashes intact. |
| Production defaults unchanged? | **YES** — BM25 remains the default; tracked `src/evaluate.py` untouched. |

## Hard stops observed

| Hard stop | Status |
|---|---|
| No model training / fine-tuning | NO training |
| No DAPT-02 / SFT-03 | Not touched |
| No new embedding model | Frozen Task-74 bge-m3 artifact only |
| No production-default change | BM25 remains default |
| No deployment / paid infrastructure | Colab/Kaggle **not** used for serving claims |
| No frozen-benchmark / corpus change | sha verified unchanged |

## 1. Serving environment (the blocker)

The repository was searched end-to-end for a deployment target, hardware
requirements, or latency SLOs — `pyproject.toml`, `README.md`, all of
`docs/`, all of `configs/`, Makefile, Dockerfile, CI config, and prior task
reports. **Nothing identifies where this system would serve.** The project is
deliberately stdlib-only (`pyproject.toml` dependencies are empty), so there
are no serving dependencies declared either.

Three environments exist but none is a serving target:

| Environment | Why it is not used as the serving environment |
|---|---|
| This VM (Azure B4as_v2) | CPU-only, 2 physical cores — a dev/test host with no identified production role. Used here for retrieval-side measurements only. |
| Colab T4 | Experiment platform (Tasks 74/75). The task explicitly forbids treating Colab T4 timings as production. |
| Kaggle GPU | Experiment platform (Task 56). Same rationale. |

Using Colab/Kaggle to stand in for a serving environment would amount to
inventing a target, which the task forbids. Full audit:
`docs/TASK77_SERVING_ENV_AUDIT.md`.

## 2. Hardware and dependency manifest (measurement host)

| Property | Value |
|---|---|
| CPU | AMD EPYC 7763, 4 logical = **2 physical cores** × 2 SMT |
| ISA | avx, avx2, fma — **no AVX-512, no AMX** |
| RAM | 16.76 GB (no swap) |
| GPU | **none** |
| OS / Python / numpy | Ubuntu 24.04.4 LTS / 3.12.3 / 2.5.3 |
| torch / transformers / sentence-transformers / faiss | **absent** |
| bge-m3 cached | **no** (not in `~/.cache/huggingface/hub`) |

The encoder cannot be loaded here without installing large packages
(torch + transformers + sentence-transformers + a ~2.2 GB model download),
which the task constrains against — and even then the result would be
2-core CPU latency, not representative of any identified target. The encoder
was therefore **not** installed or run. All retrieval measurements use the
pre-computed Task-74 query embeddings (`queries_emb.f32.npy`).

## 3. Latency measurements (retrieval side, local CPU)

Methodology: single-threaded, `time.perf_counter`, first query excluded from
warm percentiles, 10 sequential repeats of the 47 frozen queries (470 samples
per mode) for end-to-end; 47 queries for components. Hardware/software as in
§2. Encoder not in the loop.

### Cold start

| Phase | Time | RSS after |
|---|---|---|
| Corpus load (164,238 docs) | 5.45 s | 302 MB |
| BM25 index build | **64.83 s** | 841 MB |
| Dense index load (sha-verified) | 1.60 s | 2,125 MB |
| **Total startup** | **71.88 s** | peak 2,125 MB |

BM25 build dominates cold start. Dense load is optional (BM25-only serving
skips it and saves ~1.3 GB RSS and 1.6 s).

### Component latency (47 frozen queries)

| Component | p50 | mean | p95 |
|---|---|---|---|
| BM25 pool=2000 (production H1) | 161 ms | 168 ms | 340 ms |
| BM25 full-list (H3 fusion input) | 188 ms | 311 ms | 1,089 ms |
| Dense search (matmul + argsort) | 47 ms | 57 ms | 98 ms |
| RRF@20 fusion (before optimisation) | 63 ms | 67 ms | 124 ms |

Fusion micro-profile: score compute ~23 ms, lexsort ~25 ms, Python BM25 loop
~19 ms.

### End-to-end warm (470 samples per mode)

| Mode | p50 | p95 | p99 | Throughput |
|---|---|---|---|---|
| H1 (BM25) | **153 ms** | 344 ms | 724 ms | 6.05 qps |
| H3_RRF20 (hybrid) | **338 ms** | 1,123 ms | 1,520 ms | 2.31 qps |

H3 is ~2.6× H1 at the mean. The H3 tail (p99 1.5 s) is driven by the
BM25 full-list search (`top_k=INF`), which is required for exact Task-74
semantics. Encoder latency is **not** included (see §1).

### Memory and disk

| Item | Value |
|---|---|
| Peak RSS | 2,125 MB |
| Dense index on disk (f16) | 336 MB |
| Dense array loaded (f32) | 673 MB |
| Dense index load | 1.60 s |

## 4. Fusion cost — material, optimised, proven equivalent

Fusion was **material** (~19 % of H3 p50). Dominant costs: lexsort (25 ms),
score compute (23 ms), Python BM25 loop (19 ms).

**Optimisation (experiment-local, then adopted):** replace the per-document
Python loop with numpy fancy indexing for the BM25 score/bmr update. The
lexsort keys and arithmetic are unchanged; the resulting arrays are
bit-identical.

**Equivalence proof:** exact ranked-output match on **54 cases** — all 47
frozen queries plus 7 synthetic edge cases (empty BM25 list, full overlap,
heavy ties, one-sided hits, anti-correlated ranks, missing tid2idx keys,
sparse random). 0 mismatches
(`experiments/task77/task77_fusion_opt.py`, report
`data/reports/task77_fusion_opt.json`).

**Latency:** baseline 51.5 ms → optimised 39.7 ms mean (**1.30×**), expected
end-to-end saving ~12 ms. Memory footprint identical (same arrays).

**Adoption:** the vectorised path is now in `service.rrf_fuse_full`, covered
by a new regression test
(`test_rrf_fuse_full_matches_reference_on_edge_cases`) that pins it to a
per-document reference implementation. Production BM25 default is unaffected.
The frozen benchmark was re-run after adoption and still returns
`REPRODUCTION_PASS` with identical aggregates.

## 5. Serving gates — no SLOs exist; thresholds proposed, gates UNRESOLVED

A repository-wide search found **no pre-existing latency or resource SLOs**
(only Task-74 *quality* thresholds). Per the task, measured trade-offs and
proposed thresholds are provided for explicit approval; all gates are marked
**UNRESOLVED** until the target requirements are established.

| Gate | Measured | Proposed threshold | Status |
|---|---|---|---|
| H1 retrieval p95 | 344 ms | ≤ 500 ms | UNRESOLVED |
| H3 retrieval p95 | 1,123 ms | ≤ 1,500 ms | UNRESOLVED |
| H3 retrieval p99 | 1,520 ms | ≤ 2,000 ms | UNRESOLVED |
| Cold start (corpus+BM25+dense) | 71.9 s | ≤ 120 s | UNRESOLVED |
| Peak RSS | 2,125 MB | ≤ 4,096 MB | UNRESOLVED |
| Dense index disk | 336 MB | ≤ 1,024 MB | UNRESOLVED |
| Encoder latency | — | — | **BLOCKED** (no serving env) |
| Throughput sustainability | 6.05 / 2.31 qps (sequential) | workload target unknown | UNRESOLVED |

The proposed thresholds are consistent with the measurements (each measured
value would pass its proposal) but are **not** agreed requirements — they
exist only so a rollout review can approve or amend them.

Additional feasibility observations:

* **Cold start** is dominated by the 65 s BM25 build; acceptable for a
  long-lived process, problematic for serverless/cold-invocation models.
* **Fallback observability** is verified: with hybrid requested and no dense
  index, the service serves BM25 with an explicit, logged `fallback_reason`
  and non-empty results (probe PASS).
* **Concurrency** is untested — no serving server exists; all numbers are
  single-threaded sequential. A real deployment would need a concurrency
  model and re-measurement.

## 6. Regression and integrity

| Check | Result |
|---|---|
| Full test suite | 503 ran, **0 failures**, 2 pre-existing faiss errors, 1 skip — baseline-equal |
| Frozen benchmark (H1) | unit@5 0.3846, src@5 0.9130 — matches Task-74 |
| Frozen benchmark (H3_RRF20) | unit@5 0.5385, src@5 0.9783 — matches Task-74; `REPRODUCTION_PASS` |
| Contract violations | 0 |
| Frozen-bench sha | `06625f72…` verified OK |
| Dense-index corpus-emb sha | `f54919e6…` verified OK |
| Corpus / manifest | unchanged (sha recorded) |
| BM25 byte-compatible | yes |
| H3 rankings reproducible | yes |
| Provenance / contract intact | yes |
| Feature flag opt-in | yes |
| Production default changed | **no** |
| Four-arm generation re-run | **not** (no change affects answer contexts; fusion optimisation preserves exact rankings) |

## 7. Recommended rollout prerequisites and rollback

**Prerequisites (in order):**

1. **Decide** the intended serving environment (host/instance class, GPU vs
   CPU, region, concurrency model) and document it.
2. **Establish** latency/resource SLOs (p50/p95/p99 retrieval, cold-start,
   memory, throughput) and obtain explicit approval.
3. **Measure** query-encoder latency in that environment (load bge-m3 rev
   `5617a9f…`, warm p50/p95/p99).
4. **Re-measure** end-to-end H3_RRF20 including the encoder there.
5. Only then: a **separate, explicit** decision to flip
   `SVK_RETRIEVAL_MODE=hybrid_rrf20` in the target environment.

**Rollback:** `export SVK_RETRIEVAL_MODE=bm25` (or unset it; `configs/policy.toml`
`[retrieval] mode` stays `"bm25"`). Instant and lossless — the next `search()`
serves H1 BM25. If dense artifacts break at runtime, the default
`fallback_on_dense_failure=true` also serves BM25 automatically with a logged
reason.

## 8. Artifacts

| Artifact | Path |
|---|---|
| Serving-environment audit | `docs/TASK77_SERVING_ENV_AUDIT.md` |
| Latency script | `experiments/task77/task77_latency.py` |
| Latency report (JSON) | `data/reports/task77_latency.json` |
| Fusion-opt script | `experiments/task77/task77_fusion_opt.py` |
| Fusion-opt report (JSON) | `data/reports/task77_fusion_opt.json` |
| Main report (JSON) | `data/reports/task77_serving_feasibility.json` |
| Main report (this file) | `data/reports/task77_serving_feasibility.md` |
| Fusion change | `src/svk_corpus/retrieval/service.py` `rrf_fuse_full` |
| Fusion regression test | `tests/test_retrieval_service.py` |

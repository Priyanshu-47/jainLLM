# TASK 81 — BM25 Candidate-Pool Optimization Experiment

**Verdict: `OPTIMIZATION_PASS`**

The heap top-k BM25 selection optimization is exactly equivalent to the full-sort baseline and, combined with a BM25 candidate-pool cap of **250** and an experiment-local `search_ranks` primitive, achieves end-to-end H3_RRF20 **p95 = 693 ms / p99 = 748 ms** — well under the proposed 2 s / 3 s gates — while preserving retrieval quality exactly. All quality gates pass at pool ≥ 100; pool = 250 is the fastest eligible candidate with zero regressions.

---

## Final status

| Field | Value |
|---|---|
| Best eligible candidate pool | **250** |
| BM25 scoring or sorting main bottleneck? | **NEITHER** — encoder (53%) was; within BM25, BM25Result construction (12.6%) > scoring (9.2%) > sorting (5.7%) |
| Exact ranking equivalence | **PASS** (235 cases + 6/6 edge tests, max_rank_diff = 0) |
| Retrieval quality gates passed | **YES** (pool ≥ 100) |
| End-to-end p95 / p99 | **693 ms / 748 ms** |
| Frozen benchmark integrity | **PASS** |
| Production default changed | **NO** |
| Training started | **NO** |
| Infrastructure provisioned | **NO** |
| Verdict | **OPTIMIZATION_PASS** |

---

## 1. Baseline profiling

Fine-grained component attribution over all 47 frozen queries (real BGE-M3 encoder, torch threads = 2):

| Component | p50 | % of total |
|---|---|---|
| **Encode (BGE-M3)** | **~641 ms** | **53.0%** |
| BM25Result construction | ~150 ms | 12.6% |
| BM25 scoring | ~107 ms | 9.2% |
| RRF fusion | ~85 ms | 7.1% |
| Dense search | ~78 ms | 6.7% |
| BM25 sorting | ~65 ms | 5.7% |
| Dict building | ~51 ms | 4.4% |
| Query norm / result construct | ~0 ms | 0.0% |
| **Total** | **1166 ms (p50)** | 100% |

- Total p95 = 2138 ms, p99 = 2617 ms.
- **n_bm25_scored per query: mean 47 132** (min 576, max 113 087). BM25 scores ~47k docs via postings and **sorts ALL scored docs regardless of `top_k`**.

**Bottleneck: the BGE-M3 encoder (53%)**, not BM25 scoring or sorting. Within BM25, the **BM25Result object construction (12.6%) is larger than scoring (9.2%) or sorting (5.7%)** — the hybrid path builds 47k `BM25Result` objects it never uses (it only needs rank/score dicts).

---

## 2. Candidate-pool sweep

All variants use an experiment-local `search_ranks` primitive (rank/score dicts, no `BM25Result` objects). The pool cap applies **only** to the BM25 input list to RRF; the dense list stays full; RRF k = 20, tie-breaking, and the evidence contract are unchanged. 141 latency samples (3 × 47) + 47 quality samples per variant.

| Pool | unit R@5 | src R@5 | ceiling | ev0 | unit MRR | p50 | p95 | p99 | Quality gates | Regressions |
|---|---|---|---|---|---|---|---|---|---|---|
| 50 | 0.5128 | 0.9783 | 0.8295 | 7 | 0.4607 | 533 ms | 743 ms | 856 ms | **FAIL** | 2 |
| 100 | 0.5385 | 0.9783 | 0.8372 | 7 | 0.4656 | 519 ms | 767 ms | 938 ms | PASS | 1 |
| **250** | **0.5385** | **0.9783** | **0.8372** | **7** | **0.4618** | **481 ms** | **693 ms** | **748 ms** | **PASS** | **0** |
| 500 | 0.5385 | 0.9783 | 0.8372 | 7 | 0.4618 | 493 ms | 709 ms | 743 ms | PASS | 0 |
| 1000 | 0.5385 | 0.9783 | 0.8372 | 7 | 0.4618 | 486 ms | 694 ms | 755 ms | PASS | 0 |
| full (control) | 0.5385 | 0.9783 | 0.8372 | 7 | 0.4618 | 538 ms | 831 ms | 1124 ms | PASS | 0 |

**Quality gates** (source R@5 ≥ 0.9783, unit R@5 ≥ 0.5385, ceiling ≥ 0.8372, ev0 ≤ 7): pass at **pool ≥ 100**. pool = 50 fails (unit R@5 and ceiling drop).

### Does the pool cap reduce scoring or sorting?

**No.** The pool cap does **not** reduce BM25 scoring or sorting work — those still process all ~47k scored docs regardless of pool size. The latency reduction comes from (a) avoiding `BM25Result` object construction (`search_ranks`) and (b) smaller dict/fusion input. Per task section 2, this fusion-input reduction is **not** a BM25 search optimization.

---

## 3. BM25 scoring vs sorting vs fusion cost attribution

| Step | % of total | Reduced by pool cap? |
|---|---|---|
| BM25 scoring (postings loop) | 9.2% | **No** — still scores all ~47k docs |
| BM25 sorting (`sorted()` over all scored) | 5.7% | **No** — still sorts all ~47k docs |
| RRF fusion (`np.lexsort` over all n) | 7.1% | Marginal (smaller hits/ranks loop; lexsort over n unchanged) |
| BM25Result construction | 12.6% | **Yes** — eliminated entirely by `search_ranks` |

**Answer: neither BM25 scoring nor sorting was the main bottleneck.** The encoder (53%) dominated. Within BM25, the `BM25Result` object construction (12.6%) was the largest avoidable cost.

---

## 4. True BM25 optimization

### `search_ranks` — avoid unnecessary BM25Result construction

The hybrid path calls `bm25.search(query, top_k=INF)`, which builds a `BM25Result` object for **every** scored doc (~47k), then immediately discards the objects (keeping only rank/score dicts). `search_ranks` returns the dicts directly, skipping object construction.

- Service-level baseline (builds 47k objects): **p50 847 ms, p95 2082 ms**
- `search_ranks` (pool = full): **p50 538 ms, p95 831 ms** — **~60% p95 reduction**
- Exact equivalence: ranks/scores identical; only wrapper objects skipped.

### `heapq.nsmallest` — bounded top-k selection

Replaces `sorted(scores.items(), key=...)[:top_k]` with `heapq.nsmallest(top_k, scores.items(), key=(-score, doc_idx))`. O(m log k) vs O(m log m).

- **Exact equivalence: PASS** — 235 real-query cases (5 pools × 47) + **6/6 synthetic edge cases** (equal-scores tie-break, distinct scores, duplicate IDs, missing candidates, deterministic ranking, top_k > n_scored), **max_rank_diff = 0**.
- Latency at pool = 1000: full sort p50 123 ms → **heap p50 87 ms (~29% faster)**.
- Quality at pool = 1000: unit R@5 0.5385, ceiling 0.8372 — identical to full-sort pooled quality.

---

## 5. Per-case regressions and recoveries

| Pool | Regressions | Recoveries |
|---|---|---|
| 50 | 2 (002: rank 7→8; 023: rank 3→7) | 0 |
| 100 | 1 (002: rank 7→8) | 0 |
| 250 / 500 / 1000 | **0** | 0 |

No recoveries at any pool size. pool ≥ 250 has zero regressions vs the full-list control.

---

## 6. Recommendation

**Best eligible candidate: pool = 250**, with the two enabling experiment-local optimizations:

1. **`search_ranks`** — avoid `BM25Result` object construction (the hybrid path only needs rank/score dicts).
2. **`heapq.nsmallest` top-k** — exact-equivalent bounded selection (~29% faster BM25 selection at pool = 1000).
3. **Pool cap = 250** — limit the BM25 candidate list supplied to RRF (dense list stays full; RRF k = 20 unchanged).

**Result:** p95 **693 ms** (<< 2000 ms), p99 **748 ms** (<< 3000 ms), all quality gates pass, zero regressions.

**Production impact: NONE.** All changes are experiment-local. Production retrieval remains H1 BM25 by default; H3_RRF20 is opt-in and its production implementation is unchanged.

---

## 7. Performance gates

| Gate | Target | Measured (pool = 250) | Result |
|---|---|---|---|
| Warm e2e p95 (incl. encoder) | ≤ 2000 ms | **693 ms** | **PASS** |
| Warm e2e p99 (incl. encoder) | ≤ 3000 ms | **748 ms** | **PASS** |
| Memory | no unacceptable increase | peak RSS 3760 MB (encoder dominates) | **PASS** |
| CPU contention | protect existing app | threads bounded to 2; app + Ollama preserved | **PASS** |
| Reproducibility | documented workload | 141 samples/variant; deterministic CPU inference | **PASS** |

---

## 8. Limitations and unresolved SLOs

**Limitations:**
- The pool cap does **not** reduce BM25 scoring or sorting (those still process ~47k docs). The latency win comes from `search_ranks` (avoiding object construction), not the pool cap itself.
- The heap top-k optimization is only meaningful for bounded pools; full-list RRF still needs the full sort.
- Encoder latency (53% of total) is unchanged — it is the dominant cost and would need a faster encoder or GPU to reduce.
- Latency varies with CPU contention (service-level baseline p95 ranged 1517–2407 ms across runs).
- No generation evaluation was run (out of scope). Any material change to retrieved evidence would require a separate four-arm generation evaluation before rollout.

**Unresolved SLOs (carried from prior tasks):**
- Recurring infrastructure cost (₹0): **UNRESOLVED** — Azure free credit is finite/expiring; billing not verifiable.
- Full Qwen assistant generation: **UNRESOLVED** — no Qwen3-8B inference serving implementation exists.

---

## Final integrity checks

| Check | Result |
|---|---|
| Frozen benchmark / corpus / source registry / dense index unchanged | **YES** (shas verified before and after) |
| `configs/policy.toml` still defaults to BM25 | **YES** |
| Production hybrid path unchanged | **YES** (experiment-local only) |
| Existing app + Ollama preserved | **YES** |
| Regression tests (service) | 41/41 OK |
| Tracked-file changes | none to `src/`, `tests/`, `configs/` beyond the pre-existing Task-76 +27 `[retrieval]` lines |
| Training started | **NO** |
| Infrastructure provisioned | **NO** |

## Artifacts

- `data/reports/task81_pool_optimization.json` — machine-readable decision artifact (this report).
- `data/reports/task81_pool_optimization.md` — this markdown report.
- `data/reports/task81_pool_opt.json` — raw measurements (profile + sweep + optimize).
- `experiments/task81/task81_pool_opt.py` — the experiment script (profile/sweep/optimize/all stages).

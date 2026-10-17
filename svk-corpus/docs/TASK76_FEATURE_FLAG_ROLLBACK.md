# Task 76 — Feature Flag and Rollback Documentation

This document describes how the H3_RRF20 hybrid retrieval candidate is
enabled, how it is disabled, and how to roll back. **BM25 is and remains the
production default.** Nothing here changes that default; the flag exists so a
future, separate rollout review can promote the candidate deliberately.

## 1. The flag

The retrieval mode is selected by `RetrievalPolicy.mode` in
`src/svk_corpus/retrieval/service.py`, configured through (in precedence
order):

1. Code default — `RetrievalMode.BM25`.
2. `configs/policy.toml` → `[retrieval]` → `mode`.
3. Environment variable `SVK_RETRIEVAL_MODE`.

```toml
# configs/policy.toml
[retrieval]
mode = "bm25"          # production default — NEVER flip without a rollout decision
```

`mode` accepts only `"bm25"` or `"hybrid_rrf20"`. Any other value (including
typos such as `"hybrid"`) is **ignored**: the policy keeps its previous value,
so a typo can never accidentally enable hybrid. This is enforced by
`test_env_override_typo_is_ignored` and `test_default_policy_is_bm25`.

## 2. Enabling hybrid (opt-in)

Hybrid requires **all** of the following; it is never enabled by a single
mistaken setting:

1. Set `mode = "hybrid_rrf20"` in `configs/policy.toml` **or** export
   `SVK_RETRIEVAL_MODE=hybrid_rrf20`.
2. Provide a verified dense index at `dense_index_dir` (default
   `experiments/task74/dense_index`). The index must pass SHA-256 and
   doc-count verification at load time (`load_dense_index`).
3. Provide either a live query encoder or a pre-computed query embedding per
   request. Without one, the service falls back to BM25 with an explicit,
   logged `fallback_reason` (unless `strict_dense = true`, which raises
   `DenseIndexUnavailable` instead).

Example (explicit, deliberate):

```bash
export SVK_RETRIEVAL_MODE=hybrid_rrf20
# dense index present + verified; query encoder loaded or embeddings supplied
```

## 3. Disabling / rolling back

Rollback is the inverse and requires no code change:

```bash
export SVK_RETRIEVAL_MODE=bm25        # or unset it and rely on the file default
```

or edit `configs/policy.toml` back to `mode = "bm25"`.

Because BM25 and hybrid share the same `BM25Index` and corpus, rollback is
instant and lossless: the very next `search()` call serves the H1 BM25 path
(`mode C_combined`) with no reindex, no cache flush, and no data migration.
The service reports `mode_used` on every response, so a rollback is
immediately observable in logs.

### Failure-triggered rollback (automatic)

If hybrid is requested but the dense index is missing, fails SHA-256
verification, or fails doc-count verification, and
`fallback_on_dense_failure = true` (the default), the service **automatically
falls back to BM25** and records:

* `SearchResponse.mode_used = bm25`
* `SearchResponse.fallback_reason = <explicit reason>`
* a log line containing `fallback bm25`

This automatic fallback is a safety property, not a silent failure: the
reason is always observable. Set `strict_dense = true` to convert the same
condition into a hard `DenseIndexUnavailable` exception (fail-closed) for
environments that prefer an error over a degraded answer.

## 4. Observability

Every `SearchResponse` carries:

* `mode_requested` — what the caller/policy asked for.
* `mode_used` — what actually served the answer (`bm25` or `hybrid_rrf20`).
* `fallback_reason` — non-`None` whenever `mode_used != mode_requested`.
* `latency_s` — wall-clock for the search.

`SearchResponse.summary()` is safe to log: it contains the modes, latency,
result count, and an optional `query_id`, but **never** the raw query text or
result text.

## 5. Validation before any rollout decision

Before promoting the flag in any environment, the following must hold (all
verified offline by Task 76):

| Gate | Result |
|---|---|
| H1 BM25 byte-compatible with production `evaluate.py` | PASS |
| H3_RRF20 reproduces Task-74 frozen aggregates (unit@5 0.5385, src@5 0.9783) | PASS |
| Determinism / stable tie-breaking | PASS |
| Fusion duplicate handling | PASS |
| Evidence provenance preserved and contract-valid | PASS |
| Invalid/unavailable dense artifacts → explicit failure or logged fallback | PASS |
| Feature flag cannot accidentally enable hybrid by default | PASS |
| Shadow replay: BM25 authoritative, hybrid never replaces | PASS (OFFLINE) |
| Test suite baseline-equal (0 new failures) | PASS |

Outstanding before a production-default change (separate decision):

* Measure query-encoder latency in the **target serving environment** (torch
  is absent locally; Task-76 used pre-computed embeddings — encoder latency
  is UNRESOLVED here).
* Decide whether to fuse the full BM25 list (`top_k=INF`, the Task-74-faithful
  behaviour, ~0.29 s mean at 164k docs) or a truncated top-N list (faster,
  but a semantic change that would require re-validation).

## 6. What this flag is NOT

* It is not a training switch. No fine-tuning, DAPT-02, or SFT-03 is involved.
* It is not a model swap. The dense index is the frozen Task-74 bge-m3
  artifact; no new embedding model or reranker is introduced.
* It is not an automatic rollout. Flipping `mode` in any environment is a
  deliberate act that should follow a separate rollout review.

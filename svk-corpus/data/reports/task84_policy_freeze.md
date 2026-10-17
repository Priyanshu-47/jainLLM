# Task 84 — Retrieval-policy freeze and integration-plan audit

Generated: 2026-10-14T07:32:57Z (32.6s)

## Verdict

| Axis | Verdict |
|---|---|
| Retrieval policy | **RETRIEVAL_POLICY_FROZEN** |
| Integration plan | **INTEGRATION_PLAN_INCOMPLETE** |
| Overall | **BLOCKED** |

## 1. Policy audit

| # | Policy point | Status |
|---|---|---|
| 1 | Production default remains bm25 (H1) | VERIFIED |
| 2 | Generation-facing hybrid = H3_RRF20 over FULL lists (PFULL) | VERIFIED |
| 3 | Pool-250 is experiment-local, retrieval-only, 6/6 edge tests | VERIFIED |
| 4 | Pool-250 NOT applied to generation-facing path (PFULL frozen) | VERIFIED |
| 5 | BGE-M3 revision 5617a9f... pinned in index_meta | VERIFIED |
| 6 | Dense-index sha verification + bm25 fallback + mode_used logging | VERIFIED |

- **Production default**: `bm25` — FROZEN (configs/policy.toml + RetrievalPolicy default).
- **Generation-facing hybrid**: `hybrid_rrf20` over FULL BM25 list + FULL dense list (PFULL), rrf_k=20, evidence_k=5, text_trunc=500 — FROZEN_AS_GENERATION_FACING_CANDIDATE; production adoption: NOT_ADOPTED (requires explicit rollout task).
- **Pool-250**: experiments/task81/task81_pool_opt.py (experiment-local) — wired into production: False; edge tests 6/6; DOCUMENTED_EXPERIMENT_ONLY.

## 2. Integrity

| Artifact | Status |
|---|---|
| data/evaluation/dapt01_eval_cases.jsonl | OK `06625f72190e3ae1…` |
| experiments/task74/dense_index/corpus_emb.f16.npy | OK `f54919e63599c94e…` |
| /tmp/opencode/task75/adapter_model.safetensors | OK `9b4d2bdcfe089118…` |
| data/release/rag_corpus.jsonl | PRESENT `4db164bc70e68b4f…` |
| manifests/source_manifest.csv | PRESENT `b96e572f8d97891c…` |
| configs/policy.toml | PRESENT `f32308d94dd9d543…` |
| configs/policy.toml [retrieval] mode | bm25 |
| BGE-M3 revision (index_meta) | OK `5617a9f61b028005…` |

- Regression: 503 ran, 2 pre-existing faiss import errors, 1 skip — **PASS_BASELINE**.
- Task-81 pool-250 edge tests: 6/6 all_pass=True.
- Historical reports (task69/74/75/81/82/83): mtimes unchanged; no overwrites.

## 3. Serving-gap audit (this VM)

| Component | State |
|---|---|
| retrieval library | PRESENT (svk_corpus.retrieval.service, 41 tests) |
| retrieval http api | ABSENT (no FastAPI/uvicorn in svk-corpus src) |
| bge m3 query encoder runtime | ABSENT (encoder weights cached 4.3G; no deployed query-encoding service; hybrid falls back to bm25 without query_embedding) |
| evidence validation | PRESENT offline (task83_build_evidence); not in a service |
| qwen3 8b inference serving | ABSENT |
| qwen3 8b base weights | CACHED (16G, 5 safetensors shards, rev 49e3418f...) |
| dapt01 adapter | CACHED (/tmp/opencode/task75, 167M, sha verified) |
| prompt construction | experiment-local (task72/75/83 scripts); not in a service |
| streaming | ABSENT |
| ui | ABSENT |
| citations | experiment-local (provenance in results; no user-facing citation layer) |
| logging health | partial (SearchResponse.summary; no health endpoint) |

> Note: port 8000 uvicorn is fanpulse-ai orchestrator (unrelated project); ollama serves qwen2.5:7b-instruct only (4.7G) — NOT Qwen3-8B

## 4. Minimum complete assistant architecture

| Component | State |
|---|---|
| retrieval (production bm25 H1) | PRESENT (library) |
| generation-facing retrieval (hybrid_rrf20 PFULL) | PRESENT (library, opt-in mode; not production default) |
| evidence assembly (k=5, trunc=500, provenance) | EXPERIMENT-LOCAL |
| prompt construction (frozen protocol) | EXPERIMENT-LOCAL |
| Qwen3-8B-Base + DAPT-01 inference (4-bit NF4, greedy, max_new_tokens=192, seed=42) | ABSENT (no serving runtime on VM) |
| response shaping / abstention handling | ABSENT (evaluated in benchmark only) |
| HTTP API + health + logging | ABSENT |
| UI | ABSENT |

**First executable task (proposed)**: TASK 85 (proposed) — Implement a retrieval-only HTTP service (FastAPI) wrapping RetrievalService under the frozen production policy (mode=bm25), with: /health, /search (query, top_k, mode), SearchResponse.summary logging, unit tests, and a client script. Generation and Qwen inference remain out of scope (BLOCKED).

*Rationale*: retrieval is the only fully-verified, test-covered layer; shipping it as a service is the smallest end-to-end step that does not require model serving or policy change

Hard stops: no production default change; no Qwen inference (blocked on serving decision); no training; no frozen-benchmark modification.

## 5. Serving feasibility on this VM

### Verified facts

- VM: 4 vCPU (AMD EPYC 7763), 15.6 GiB RAM, no GPU
- Qwen3-8B-Base fp16 weights = 16 GiB — does not fit in available RAM for CPU inference alongside OS/services
- 4-bit NF4 quantization would fit (~5-6 GiB) but bitsandbytes is not installed and CPU 4-bit generation would be slow (unmeasured); not attempted per hard stop on dependency installs
- ollama present (127.0.0.1:11434) but only qwen2.5:7b-instruct — different architecture, NOT interchangeable with evaluated Qwen3-8B-Base/DAPT-01
- no llama.cpp / vllm / tgi / llama-cpp-python installed
- BGE-M3 query-encoder runtime also absent (weights cached 4.3G); hybrid mode requires caller-supplied query_embedding or falls back
- generation was previously run on Kaggle T4 (GPU quota 30h) — remote, not on this VM

### Proposed decisions (not taken this task)

- Retrieval-only service first (TASK 85); generation integration deferred until a serving path is chosen and funded
- Serving path options (UNRESOLVED): (a) remote API (external cost), (b) GPU VM (Azure credit cost UNVERIFIED), (c) CPU-only 4-bit (feasibility unmeasured, slow), (d) keep benchmark-only on Kaggle

### Unresolved questions

- Is a GPU VM or external inference API budget approved? (Azure credit sustainability UNVERIFIED — not checked this task)
- Should hybrid_rrf20 PFULL ever become the generation-facing production default, or stay an explicit opt-in? (adoption requires a separate rollout task with its own gate)
- Is qwen2.5:7b acceptable as a non-evaluated development stand-in? (currently present; must NOT be presented as the evaluated model)
- Who owns the first-executable-task decision (TASK 85 scope)?

## 6. Final status

| Criterion | Status |
|---|---|
| Generation-facing policy documented + verified | YES |
| Pool-250 retrieval-only policy documented + verified | YES |
| Tests + integrity verified | YES |
| Qwen3-8B inference serving | ABSENT |
| Full assistant ready | NO |
| Azure cost sustainability | UNVERIFIED |
| Production default changed | NO |
| Training started | NO |

**Verdict: RETRIEVAL_POLICY_FROZEN / INTEGRATION_PLAN_INCOMPLETE / BLOCKED.**

The retrieval policy (production bm25 default, generation-facing PFULL hybrid candidate, retrieval-only pool-250) is frozen and verified. The end-to-end assistant is BLOCKED: Qwen3-8B inference serving is absent on this VM, the serving path is unresolved, and Azure cost sustainability is unverified. Production default was not changed; no training was started.

## Repro

```bash
PYTHONPATH=src python3 experiments/task84/task84_report.py
PYTHONPATH=src python3 -m unittest discover -s tests
```

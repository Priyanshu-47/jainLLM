# TASK 79 — Existing Azure VM Serving Validation

**Verdict: `AZURE_RETRIEVAL_VALIDATION_PENDING`**

The retrieval pipeline is validated on this exact VM. The BGE-M3 encoder is blocked (not cached, dependencies absent, download out of scope), so end-to-end hybrid latency remains unresolved. Azure free credit is not a sustainable ₹0 guarantee.

---

## Final status

| Field | Value |
|---|---|
| Actual VM size & architecture | Standard_B4as_v2, westus2, x86_64 AMD EPYC 7763, 2 physical cores (4 vCPU), AVX2 present |
| Available RAM | 13.9 GiB (of 15.6 GiB) |
| GPU status | none (CPU-only; no nvidia-smi, no /dev/nvidia*) |
| Azure credit/cost status | **UNVERIFIABLE** — free credit finite/expiring; balance not readable; not a sustainable ₹0 guarantee |
| Encoder latency measured | **NO** (BLOCKED) |
| Retrieval SLO gates | **6 passed / 4 unresolved / 0 failed** |
| Full Qwen assistant feasible | **NO** |
| Production default changed | **NO** |
| Infrastructure provisioned/resized | **NO** |
| Verdict | **AZURE_RETRIEVAL_VALIDATION_PENDING** |

---

## 1. Actual VM resource manifest

Read-only diagnostics; no environment variables, tokens, or credentials dumped.

- **Azure VM size:** `Standard_B4as_v2` (from Instance Metadata Service, read-only)
- **Region:** `westus2`
- **OS:** Ubuntu 24.04.4 LTS (Noble), kernel `7.0.0-1014-azure`
- **Architecture:** x86_64
- **CPU:** AMD EPYC 7763, 4 vCPU = 2 physical cores × 2 threads, hypervisor Microsoft
- **Instruction support:** AVX, AVX2, FMA, SSE4.1/4.2/4a (no AVX-512, no AMX)
- **RAM:** 15.6 GiB total, **13.9 GiB available**, no swap
- **Disk:** 123 GB total, 55 GB used, **69 GB free** (45%)
- **GPU:** none
- **Python:** 3.12.3 (system: numpy 2.5.3 only). `fpvenv`: fastapi 0.142.2, uvicorn 0.54.0, numpy 2.3.5 — **no torch, transformers, sentence-transformers, or faiss**.
- **Memory after existing app:** 13.9 GiB available of 15.6 GiB (~2.1 GiB used by the running application stack).

### Existing application (preserved, untouched)

The VM already hosts, as raw processes (no Docker, no systemd user units):

- **uvicorn orchestrator** — `services.orchestrator.main:app` on `127.0.0.1:8000` via `fpvenv` (fanpulse-ai repo).
- **ollama serve** — running `qwen2.5:7b-instruct` (Q4_K_M, 4.7 GB, 7.6B params). This is a **different, smaller model** from the project's Qwen3-8B-Base+DAPT lineage and is **not** the project generator.
- **OpenCode** — the current session.

No restart, redeploy, or resize was performed. The existing application and OpenCode session were preserved.

### BGE-M3 compatibility

The VM architecture is compatible with the verified BGE-M3 runtime: x86_64 with AVX2 is a supported target. The **dense index** loads on this VM with numpy only (no torch needed for the index itself). The **encoder** itself is not currently runnable (see §4).

---

## 2. Azure credit and cost verification status

**Status: UNVERIFIABLE (documented honestly).**

- **Cost-bearing resources identified** (via `az consumption usage list`, subscription ID redacted): the VM `JainVM`, its OS disk, and the public IP `jainvm-ip`. These consume Azure free credit.
- **Actual cost/quantity:** the consumption API returned 20 rows naming these resources but **all cost, quantity, and billing-period fields were null** — free-credit subscriptions do not expose per-resource cost through this API.
- **Credit balance/expiration:** `az billing balance show` requires billing-account/profile names that are not available; the balance and expiry **could not be read**. Reported as unknown rather than guessed.
- **Caveat:** Azure free credit is a finite, expiring balance. It is **not** a sustainable ₹0 recurring-cost guarantee after expiry. The VM, OS disk, and public IP are billable resources.

**Unverified:** remaining credit, credit expiry date, actual ₹/hour burn rate, and post-credit billing behavior.

---

## 3. Compatibility findings

- **H1 BM25 production default:** CONFIRMED. `configs/policy.toml` `[retrieval] mode = "bm25"`, unchanged from Task 76.
- **H3_RRF20 opt-in:** CONFIRMED. Hybrid mode is opt-in via policy, not the default.
- **Verified dense index loadable:** CONFIRMED. Task-74 sha-verified index (BGE-M3 rev `5617a9f`, `corpus_emb.f16.npy`, 320.8 MB, sha `f54919e…`) loads via numpy with **no content change**.
- **Runtime dependencies:** BM25 + dense search + fusion need only numpy + stdlib (PRESENT). The BGE-M3 **encoder** needs torch + sentence-transformers (ABSENT) and the bge-m3 model (NOT cached). Installing/downloading is out of scope for this task.
- **Provenance & fallback:** CONFIRMED. `RetrievalService` preserves contract provenance; BM25 fallback is explicit, logged, and returns non-empty results.
- **Frozen artifacts unchanged:** CONFIRMED. Frozen benchmark sha and dense-index sha both VERIFIED; no rebuild or modification.

---

## 4. Measured latency and memory (retrieval-side only)

**Important caveat:** All latency figures use **pre-computed query embeddings** (`queries_emb.f32.npy`). The BGE-M3 **encoder is excluded**. These are **NOT** end-to-end hybrid latency.

### Encoder — BLOCKED

| Item | Status |
|---|---|
| Encoder initialization time | NOT MEASURED |
| First-query latency | NOT MEASURED |
| Warm encoder latency | NOT MEASURED |
| Reason | bge-m3 not cached; torch/sentence-transformers absent; model download + large install out of scope |

**Requirement for a separately authorized benchmark:** install torch (CPU) + sentence-transformers, download `BAAI/bge-m3` rev `5617a9f` (~2.2 GB download, ~3.8 GB peak RAM), then run the bounded encoder smoke test in the Task-78 validation plan.

### Cold start (without encoder load)

| Phase | Time |
|---|---|
| Corpus load | 5.96 s |
| BM25 build | 53.88 s |
| Dense index load | 1.55 s |
| **Total** | **61.40 s** |

(Task-77 with encoder load was 71.9 s — both under the 120 s gate.)

### Component latency (47 queries, encoder excluded)

| Component | p50 | p95 |
|---|---|---|
| BM25 pool (top-2000) | 130 ms | 266 ms |
| BM25 full scan | 213 ms | 805 ms |
| Dense search (numpy matmul) | 38 ms | 52 ms |
| RRF fusion (vectorized) | 45 ms | 98 ms |

### Warm end-to-end retrieval (235 samples/mode, encoder excluded)

| Mode | p50 | p95 | p99 | Throughput |
|---|---|---|---|---|
| H1 BM25 | 150 ms | 274 ms | 594 ms | 6.71 qps |
| H3 RRF20 | 309 ms | **1057 ms** | 1137 ms | 2.48 qps |

### Frozen-benchmark reproduction — PASS

Exact match to Task-74 aggregates (within 1e-3):

| Mode | unit@5 | src@5 | unit MRR | src MRR |
|---|---|---|---|---|
| H1 | 0.3846 | 0.9130 | 0.3333 | 0.7986 |
| H3 | 0.5385 | 0.9783 | 0.4618 | 0.9174 |

### Memory and disk

| Metric | Value |
|---|---|
| Peak process RSS | 2124.8 MB (2.1 GB) |
| Dense index on disk | 320.8 MB |
| Dense index loaded (f32) | 641.6 MB |

### BM25 fallback probe — PASS

`mode_used = bm25`, `logged = true`, results non-empty. Fallback works and is explicit.

---

## 5. Task 78 gate-by-gate assessment

Targets are **proposed** (Task 78), not pre-existing project requirements. Not changed to force a pass.

| Gate | Proposed target | Result | Evidence |
|---|---|---|---|
| Recurring infrastructure cost | ₹0 | **UNRESOLVED** | Free credit finite/expiring; VM+disk+IP billable; balance not verifiable; not a sustainable ₹0 guarantee |
| Warm retrieval p95 (incl. encoder) | ≤ 2000 ms | **UNRESOLVED** | Retrieval-only p95 = 1057 ms; encoder excluded (BLOCKED) |
| Warm retrieval p99 (incl. encoder) | ≤ 3000 ms | **UNRESOLVED** | Retrieval-only p99 = 1137 ms; encoder excluded (BLOCKED) |
| Cold start | ≤ 120 s | **PASS** | 61.4 s (71.9 s with encoder in Task-77) |
| Peak RSS ≤ 8 GB on 12 GB host | 8 GB / 12 GB | **PASS** (hardware note) | 2.1 GB measured. **The 12 GB host assumption does not apply** — this VM has 15.6 GiB total / 13.9 GiB available. Measured 2.1 GB is far below any reasonable ceiling; recommend keeping 8 GB RSS as a safety cap regardless of host size |
| Dense index storage | ≤ 1 GB | **PASS** | 320.8 MB |
| Initial concurrency | 1 request | **PASS** | single-threaded by design |
| Retrieval quality (H3 reproduce) | reproduce Task-74 | **PASS** | unit@5 0.5385, src@5 0.9783 exact |
| BM25 fallback | explicit/logged/tested | **PASS** | fallback probe PASS |
| Generation latency (Qwen) | separate gate | **UNRESOLVED** | no Qwen3-8B inference serving impl; ollama model is different |

**Summary: 6 passed, 4 unresolved, 0 failed.**

---

## 6. Is Azure suitable for retrieval only?

**YES (conditional).**

The retrieval pipeline runs correctly on this VM:

- Frozen-benchmark quality reproduced **exactly**.
- Retrieval-side H3 p95 = **1057 ms**, well under the 2 s gate *if* the encoder stays under ~940 ms (BGE-M3 query encoding typically does — but this is not measured here).
- Peak RSS 2.1 GB on a 15.6 GiB host; dense index 321 MB; cold start 61 s.
- BM25 fallback and provenance preserved.
- Architecturally compatible (x86_64, AVX2 present).

**Conditions:**
1. Encoder latency must be measured in a separately authorized benchmark to close the p95/p99 gates.
2. Recurring cost is **not** ₹0-sustainable once Azure free credit expires; a paid plan is required thereafter.
3. Single-concurrency only; the 2-physical-core CPU is the bottleneck (BM25 full-scan p95 805 ms).

---

## 7. Is a complete Qwen-powered assistant feasible?

**NO.**

- The project's generator is **Qwen3-8B-Base with DAPT-01/SFT-01 adapters**. There is **no inference/serving implementation** for it in the repo (Task-78 audit finding re-verified: only training code `dapt_trainer.py`/`sft_candidates.py` and offline Colab inference `task75_rag_infer.py`, which produced frozen artifacts, not a serving path).
- Qwen3-8B-Base weights **are** cached in the HF hub but cannot be served without writing a new inference stack.
- **Ollama** is running `qwen2.5:7b-instruct` — a different, smaller model, **not** the project generator.
- The VM is a 2-physical-core CPU host with no GPU; 8B generation would be impractically slow (~1–3 tok/s) and would contend with the running application.
- **No bounded generation test was run** (out of scope; different model; no project serving implementation).

Retrieval working does **not** imply Qwen generation is supported.

---

## 8. Exact blockers and next required action

| ID | Component | Blocker | Impact | Resolution |
|---|---|---|---|---|
| B1 | BGE-M3 encoder | bge-m3 not cached; torch/sentence-transformers absent | Encoder latency unmeasured; p95/p99 gates UNRESOLVED | Separately authorize: install torch (CPU) + sentence-transformers, download bge-m3 rev `5617a9f`, run bounded encoder smoke test |
| B2 | Azure recurring cost | Free credit finite/expiring; balance not readable | ₹0 cost gate UNRESOLVED | User confirms billing setup, credit balance/expiry, post-credit plan in Azure portal (not done here; read-only constraint) |
| B3 | Qwen generation | No Qwen3-8B-Base inference serving impl | Full assistant NOT feasible; generation gate UNRESOLVED | Separate task to build/evaluate an inference path (out of scope; VM CPU also impractical for 8B) |

**Next required action:** User authorizes a separately scoped encoder benchmark (install torch+sentence-transformers, download bge-m3, run bounded smoke test) to close the p95/p99 gates **and** confirms the Azure billing/credit-expiry plan. Until then the verdict remains **`AZURE_RETRIEVAL_VALIDATION_PENDING`**.

---

## Hard stops observed

- No provisioning, resize, restart, or redeploy.
- No large dependency install or model download.
- No training, DAPT-02, or SFT-03.
- No production default change.
- No frozen benchmark, corpus, dense-index, or source-registry modification.
- No full Qwen generation run; no claim of full-assistant readiness.
- Existing application and OpenCode session preserved.

## Artifacts

- `data/reports/task79_azure_validation.json` — machine-readable decision artifact.
- `data/reports/task79_azure_validation.md` — this report.
- `experiments/task79/task79_validate.py` — bounded validation script (read-only w.r.t. the VM; pre-computed embeddings only).

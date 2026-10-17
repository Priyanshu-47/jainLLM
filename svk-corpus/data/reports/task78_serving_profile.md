# Task 78 — Serving Environment Decision & Deployment Profile

**Context:** Task 75 selected BASE + H3_RRF20; Task 76 implemented the
retrieval abstraction and passed readiness checks; Task 77 returned
`BLOCKED_ON_SERVING_ENVIRONMENT`. This task resolves the serving-profile
decision as far as evidence allows. It does **not** deploy, provision
infrastructure, change production defaults, or start training.

## Final verdict

> **PARTIAL_PROFILE_ONLY**

A fully free profile cannot host the **complete** assistant (retrieval +
BGE-M3 encoding + Qwen3-8B generation) at zero recurring cost on any
examined provider. A persistent **retrieval-only** profile is viable on
**Oracle Cloud Always Free Ampere A1** (2 OCPU / 12 GB Arm VM). Qwen3-8B
generation is **not** feasible there (impractically slow on Arm CPU; no free
always-on GPU exists on any examined profile). This is explicitly **not** a
complete AI assistant deployment.

**Next action:** the user provisions an Oracle Always Free account and one
A1.Flex instance (manual; requires card verification; **not** done by this
task), then runs the validation plan to measure encoder and retrieval
latency there before any latency gate is claimed passed.

## Final status

| Field | Value |
|---|---|
| Selected profile | Oracle Cloud Always Free — Ampere A1 (2 OCPU / 12 GB), **retrieval-only** |
| Recurring cost target | ₹0 (Always Free only; no paid fallback) |
| Retrieval deployment feasible | **YES** (conditional on eligibility, capacity, idle-reclamation risk) |
| Full Qwen assistant feasible at zero cost | **NO** |
| Encoder latency measured in target environment | **NO** |
| SLO gates passed | **0 passed / 8 unresolved** |
| Production default changed | **NO** |
| Infrastructure provisioned | **NO** |
| Final verdict | **PARTIAL_PROFILE_ONLY** |

## 1. Architecture audit

The repository is an **offline/batch retrieval pipeline** with a production
BM25 path (H1) and an opt-in hybrid candidate (H3_RRF20). There is **no**
inference/serving code for answer generation, **no** API server, and **no**
frontend. Generation exists only as *training* configuration; the Task-69/70
RAG answers were produced offline on external GPU sessions and stored as
artifacts.

| Layer | Components | Status |
|---|---|---|
| 1. Corpus + index storage | `rag_corpus.jsonl` (495 MB), manifest, `task74/dense_index/` (336 MB f16 + meta) | Exists; sha-verified |
| 2. BM25 retrieval | `BM25Index`, `service._search_bm25` (pool 2000), `evaluate.py` mode C | Production default; byte-compatible |
| 3. BGE-M3 encoding + dense search | `service.load_dense_index` (numpy), `dense.SentenceTransformerDense` (prototype) | Index exists; **encoder not bundled in service** (callers pass callable or pre-computed embeddings) |
| 4. RRF fusion + validation | `service.rrf_fuse_full` (vectorised), `contract.validate_result` | Optimised (Task-77); contract-clean |
| 5. Answer generation (Qwen) | `training/dapt_trainer.py`, `training/sft_candidates.py`, SFT YAMLs | **Training only — no inference/serving code** |
| 6. Frontend / API hosting | — | **Does not exist** |

Key documents reviewed: `docs/TASK77_SERVING_ENV_AUDIT.md`,
`docs/TASK76_RETRIEVAL_DESIGN.md`, `docs/TASK76_FEATURE_FLAG_ROLLBACK.md`,
Task-76/77 reports and JSON artifacts, `configs/policy.toml`,
`pyproject.toml`.

## 2. Free-cloud profile comparison

Sources are official provider documentation (cited in
`data/reports/task78_serving_profile.json`).

### A. Oracle Cloud Always Free — Ampere A1 ⭐ recommended

* **Free:** `VM.Standard.A1.Flex` up to **2 OCPU + 12 GB RAM** (Arm), or up
  to 2 AMD Micro instances; **200 GB** always-free block volume.
  ([OCI Always Free docs](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm))
* **Persistent storage:** yes (block volumes).
* **Always-on API:** yes — it is a VM; a systemd service runs continuously.
* **Sleep/suspension:** no auto-sleep, **but** idle instances (95th-pct
  CPU/network/memory < 20 % over 7 days) **may be reclaimed**.
* **Capacity/quota:** capacity-limited per region ("out of host capacity"
  possible); one free account per person.
* **Account verification:** **credit/debit card required** for identity
  verification (temporary hold possible; not charged unless upgrading);
  mobile number often required.
  ([OCI FAQ](https://www.oracle.com/cloud/free/faq/))
* **Charges:** only if Always Free limits are exceeded or non-free
  resources are provisioned.
* **BGE-M3:** **plausible, unmeasured** — 12 GB RAM fits model (~2.2 GB) +
  retrieval (~2.1 GB) with headroom; Arm query-encoding latency unknown.
* **Dense retrieval:** yes — 321 MB index, ~1.3 GB loaded.
* **Qwen generation:** **no for interactive use** — 8B on Arm CPU is
  impractically slow; memory would also be tight.

### B. Free GPU notebook sessions (Kaggle) — benchmarking only

* Free NVIDIA P100/T4-class GPU, **~30 h/week** quota (resets weekly;
  "floating" quota may vary). ([Kaggle notebooks docs](https://www.kaggle.com/docs/notebooks))
* **Ephemeral** — sessions disconnect; not a serving platform.
* No payment method needed for basic tier; no charges for free usage.
* **Verdict:** suitable **only** for one-off GPU benchmarking (e.g., future
  Qwen latency measurement), never for serving.

### C. Hugging Face Spaces (free) — poor fit under current terms

* Static Spaces free; **Gradio/Docker Spaces now require a paid plan**
  (PRO for personal accounts). Free accounts may host up to 2 Gradio Spaces
  on **ZeroGPU** (conditional quota). CPU Basic = 2 vCPU / 16 GB but sleeps
  after ~48 h and is no longer creatable free for Gradio.
  ([Spaces overview](https://huggingface.co/docs/hub/spaces-overview),
  [Spaces GPUs](https://huggingface.co/docs/hub/spaces-gpus))
* **Non-persistent** 50 GB disk.
* **Verdict:** poor fit; the paid-plan requirement for Gradio/Docker is
  recent and should be re-checked, but current terms disqualify it as a
  free always-on host.

### D. Google Cloud free tier — rejected

* Always Free = **1 e2-micro** (shared ~0.25 vCPU, **1 GB RAM**) in 3 US
  regions; 30 GB disk; GPUs never free.
  ([GCP free docs](https://docs.cloud.google.com/free/docs/free-cloud-features))
* **1 GB RAM cannot load BGE-M3 (~2.2 GB) or the retrieval stack (~2.1 GB
  RSS).** The $300 / 90-day trial credit is not sustainable zero-cost
  evidence.
* **Verdict:** rejected — an order of magnitude too small.

## 3. Recommended profile

**Oracle Cloud Always Free — Ampere A1 retrieval service**

| Property | Value |
|---|---|
| Shape | `VM.Standard.A1.Flex`, 2 OCPU / 12 GB RAM (single instance) |
| OS | Ubuntu (Always Free-eligible) |
| Storage | Boot volume ≥ 47 GB (corpus ~0.5 GB, index ~0.3 GB, OS, env) |
| Software | Python 3.11+, numpy; torch + sentence-transformers (CPU) for BGE-M3; existing `RetrievalService` |
| Service shape | Long-lived process (systemd) + minimal local HTTP endpoint (**to be built in a future task — does not exist yet**) |
| **Serves** | **Retrieval only** (BM25 + optional H3_RRF20 + BGE-M3 query encoding) |
| **Does not serve** | Answer generation (Qwen3-8B); no frontend; **not a complete AI assistant** |

**Conditional on:** account eligibility (one free/person; card
verification); regional A1 capacity; idle-reclamation risk mitigation; the
user manually provisioning the instance.

### Retrieval vs generation decision

| Question | Answer |
|---|---|
| Retrieval on the proposed host? | **YES** — 12 GB / 2 OCPU fits comfortably; always-on API possible. |
| BGE-M3 latency meets proposed gates on CPU? | **UNRESOLVED** — Arm latency unmeasured; p95 ≤ 2 s plausible but unproven. |
| Qwen generator on the same host? | **NO** for interactive assistant — 8B on Arm CPU impractical; memory tight. |
| Separate retrieval and generation? | **YES** — retrieval persistent; generation kept separate, unresolved. |
| Free notebook only for GPU benchmarking? | **YES** — Kaggle is benchmarking-only, never serving. |

## 4. Proposed SLOs (not pre-existing)

A repository-wide search (Task 77) found **no** existing latency/resource
SLOs. The following are **PROPOSED** for explicit approval:

| Gate | Proposed | Plausibility vs measurements |
|---|---|---|
| Recurring infrastructure cost | ₹0 | Met (Always Free only). |
| Warm retrieval p95 (incl. encoder) | ≤ 2,000 ms | **Plausible, unproven** — local p95 (no encoder) 1,123 ms on 2 x86 cores; Arm + encoder adds latency. |
| Warm retrieval p99 (incl. encoder) | ≤ 3,000 ms | **Plausible, unproven** — local p99 (no encoder) 1,520 ms. |
| Cold start | ≤ 120 s | Met locally (71.9 s) but dominated by 65 s BM25 build; Arm may differ. |
| Peak process RSS | ≤ 8 GB on 12 GB host | Met locally (2.1 GB retrieval-only); +encoder ~2 GB; headroom OK. |
| Dense index size | ≤ 1 GB | Met (321 MB). |
| Initial concurrency | 1 active request | Met (single-threaded). |
| BM25 fallback | explicit, logged, tested, never misreported as hybrid | Already implemented + tested (Task 76/77). |
| Retrieval quality | Reproduce Task-74 H3_RRF20 metrics | Already verified (`REPRODUCTION_PASS`). |
| Answer generation latency | **UNRESOLVED** — separate gate | No inference path exists; cannot be proposed numerically. |

All retrieval latency figures **exclude answer generation** unless explicitly
measured (generation is unmeasured).

## 5. Zero-budget and billing safeguards

**Policy:** no paid fallback; no provisioning in this task; no paid GPU; no
reliance on expiring trial credits as evidence of sustainable zero-cost
hosting; no secrets or card details in code/reports.

**Provider billing requirements:**

* **Oracle:** card (credit-card logo, no PIN) for identity verification;
  temporary hold possible; not charged unless upgrading. Mobile number often
  required.
* **GCP:** billing account + payment method even for free tier/trial.
* **Hugging Face:** no payment for basic account; paid plan now required to
  *create* Gradio/Docker Spaces.
* **Kaggle:** no payment for basic free tier.

**Recommended controls:** set a Oracle budget/alarm alert (defense-in-depth,
not a substitute for using free resources); never upgrade the account; treat
"out of host capacity" or quota errors as a **stop** signal, not an upgrade
prompt; monitor idle-reclamation status.

## 6. Validation plan

Full plan: `experiments/task78/task78_validate_plan.md`. It separately
measures encoder init/cold/warm latency, dense search, BM25, RRF fusion,
total retrieval latency **including encoding**, disk/cold-start/restart, and
(gated on an inference path existing) generation latency + peak memory —
using the verified BGE-M3 revision and Task-74 index, preserving the frozen
benchmark and integrity checks. **No gate is claimed passed until measured
in the target environment.**

## 7. Risks, limitations, rollback

**Risks:** Oracle A1 capacity may be unavailable in the preferred home
region; idle instances may be reclaimed after 7 days of <20 % utilization;
Arm encoder latency may exceed the 2 s p95 gate; free-tier terms can change;
no API server exists yet (building one is a separate future task).

**Limitations:** this task did **not** provision, deploy, or change
defaults; encoder/generator latency were **not** measured in the target
environment (it does not exist yet); the profile is retrieval-only.

**Rollback:** if Oracle eligibility/capacity fails, fall back to the
existing local VM (already validated) or re-evaluate other profiles; if
encoder latency fails on Arm, keep BM25-only as default (already the case);
if idle reclamation disrupts service, use a lightweight keep-alive or accept
on-demand reprovisioning; the `SVK_RETRIEVAL_MODE=bm25` rollback is instant
and lossless.

## 8. Artifacts

| Artifact | Path |
|---|---|
| Decision report (JSON) | `data/reports/task78_serving_profile.json` |
| This report | `data/reports/task78_serving_profile.md` |
| Validation plan | `experiments/task78/task78_validate_plan.md` |
| Prior audit (Task 77) | `docs/TASK77_SERVING_ENV_AUDIT.md` |

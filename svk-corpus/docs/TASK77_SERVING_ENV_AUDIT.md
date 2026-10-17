# Task 77 — Serving Environment Audit

**Finding: no intended serving environment is identified in this repository.**
This is the primary blocker for the Hybrid RAG serving-feasibility gate. The
document records the missing decision, the environments that were inspected,
and what was (and was not) measured as a result.

## 1. What was searched

The following were inspected for a serving/deployment target, hardware
requirements, or latency/resource SLOs:

| Location | Result |
|---|---|
| `pyproject.toml` | Dependencies **deliberately empty** — pipeline is stdlib-only for reproducibility; optional accelerators detected at runtime. No serving deps declared. |
| `README.md` | Describes the corpus project; no serving/deployment section. |
| `docs/` (all files) | Data card, provenance, quality, reproducibility, rights docs, Task-76 design/flag docs. No deployment target, host spec, or SLO. |
| `configs/` | `policy.toml` (retrieval defaults, no latency SLO), curation CSVs, SFT YAMLs (training configs, not serving). |
| Dockerfile / docker-compose / Makefile | No Dockerfile. `Makefile` is build/test tooling only. |
| CI config (`.github/`, `.gitlab-ci*`) | None present. |
| Prior task reports (`data/reports/task5*`, `task7*`) | Task 56 (CPU DAPT feasibility) describes **this VM** (B4as_v2) as a *training* environment, not serving. Tasks 74/75 used Colab T4 / Kaggle for *experiments*. No report names a production serving host. |
| Infrastructure-as-code / cloud config | None. |

**Conclusion:** the intended serving environment has not been decided or
documented anywhere in the repository. Per the task's own guidance, this is
documented and the gate stops short of claiming serving readiness.

## 2. Environments available (and why none is used as "the" serving environment")

| Environment | Availability | Role | Used here? |
|---|---|---|---|
| **This VM** (Azure B4as_v2) | Always available | Dev/test; Task-56 DAPT micro-benchmark host | **Yes** — for retrieval-side measurements (BM25, dense search, fusion, e2e with pre-computed embeddings). CPU-only, 2 physical cores. |
| **Colab T4** (via `colab` CLI) | Available (authorized for prior experiment tasks 74/75) | One-off embedding/experiment compute | **No** — the task states Colab T4 timings must not be treated as production; it is an experiment platform, not a serving target. |
| **Kaggle GPU** (via `kaggle` CLI) | Available (authorized for prior task 56) | One-off training/experiment compute | **No** — same rationale. |
| **A production serving host** | **Does not exist / not identified** | Would be the real target | **N/A — this is the blocker.** |

Using Colab/Kaggle to *stand in for* a serving environment would amount to
inventing a target environment, which the task explicitly forbids. They were
therefore not used for serving-latency claims.

## 3. Local hardware and dependency manifest (the measurement host)

Recorded by `experiments/task77/task77_latency.py` and duplicated in
`data/reports/task77_latency.json`:

| Property | Value |
|---|---|
| Host | Azure VM `JainVM`, B4as_v2-class |
| CPU | AMD EPYC 7763, **4 logical = 2 physical cores × 2 SMT** |
| ISA | avx, avx2, fma — **no AVX-512, no AMX** |
| RAM | 16.76 GB total, ~9.4 GB available at start, **no swap** |
| Disk | 132 GB total, ~73 GB free |
| GPU | **None** (no `nvidia-smi`, no CUDA device) |
| OS | Ubuntu 24.04.4 LTS, kernel 7.0.0-1014-azure |
| NUMA | 1 node |
| Python | 3.12.3 |
| numpy | 2.5.3 |
| torch / transformers / sentence-transformers / faiss | **Absent** (system python and both venvs checked) |
| bge-m3 model cache | **Not cached** (`~/.cache/huggingface/hub` has no BAAI/bge-m3) |
| Network | Outbound HTTPS available (huggingface.co reachable) |

The encoder (BAAI/bge-m3, revision `5617a9f…`) **cannot be loaded** in this
environment without installing torch + transformers + sentence-transformers
(large packages; the project's dependency policy is deliberately empty) and
downloading the ~2.2 GB model. Even then, latency would be measured on 2
physical CPU cores with no GPU — **not representative of any identified
serving target**. Per the task's constraint on large installs and on not
claiming readiness from unrepresentative environments, the encoder was **not**
installed or run.

## 4. What this means for encoder latency

* **Encoder latency was NOT measured in an intended serving environment** —
  because no intended serving environment exists to measure it in.
* The Task-74 dense-index artifact records a Colab T4 reference
  (`query_encode_s: 0.11 s` for 47 queries ≈ 2.3 ms/query on a T4 GPU). This
  is an **experiment-platform reference point only**, explicitly not a
  production measurement.
* All retrieval-side measurements in `task77_latency.json` use the
  **pre-computed** Task-74 query embeddings (`queries_emb.f32.npy`); the
  encoder is not in the loop.

## 5. The missing decision

Before any production rollout of `hybrid_rrf20`, the following must be
decided and documented (none of these decisions can be made by this task):

1. **Where** the retrieval service will run (cloud VM type / instance class,
   GPU or CPU-only, region, concurrency model).
2. **Latency and resource SLOs** (p50/p95/p99 retrieval latency, cold-start
   budget, memory ceiling, throughput target).
3. Whether the **encoder** runs in-process, as a sidecar, or as a separate
   embedding service.
4. Whether **BM25-only** serving (no dense index) is an acceptable degraded
   mode for some deployments (it is, per the fallback design).

Until (1) and (2) exist, encoder latency and end-to-end serving feasibility
remain **UNRESOLVED / BLOCKED**, regardless of the local retrieval-side
measurements reported by this task.

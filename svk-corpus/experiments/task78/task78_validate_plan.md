# Task 78 — Validation Plan (Oracle Always Free Ampere A1)

This plan measures the actual serving path **once the target environment
exists**. It is reproducible and preserves the frozen benchmark and all
existing integrity checks. No gate is claimed passed until measured here.

## Prerequisite (user action, not done by Task 78)

1. Create an Oracle Cloud Free Tier account (requires credit/debit card for
   identity verification; card is not charged for Always Free usage).
2. Choose a **home region carefully** — Always Free compute can only be
   provisioned there, and the choice is effectively permanent.
3. Provision **one** `VM.Standard.A1.Flex` instance with **2 OCPU / 12 GB**
   RAM, an Always Free-eligible Ubuntu image, and a boot volume ≥ 47 GB.
4. Confirm the instance appears under **Always Free** resources in the
   Console (label `Always Free-eligible`). Do **not** upgrade the account or
   attach any non-free shape.

Task 78 does **not** provision this instance.

## Environment manifest to record

| Item | Record |
|---|---|
| Instance shape | `VM.Standard.A1.Flex`, OCPU count, RAM |
| CPU | `lscpu` model, cores, flags (expect Arm Neoverse-N1, avx not applicable) |
| RAM / swap | `free -b` |
| Disk | `df -B1 /` |
| OS / kernel | `uname -a`, `/etc/os-release` |
| Python / numpy / torch / sentence-transformers | versions |
| Device | `cpu` (no CUDA expected) |

## Measurements (each with sample count, warm-up policy, methodology)

Use the **verified BGE-M3 revision** `5617a9f61b028005a4858fdac845db406aefb181`
and the **Task-74 index** at `experiments/task74/dense_index/`. Do not
download a different model or rebuild verified artifacts without a documented
reason.

### 1. Model + encoder initialization

* Load `SentenceTransformer("BAAI/bge-m3")` (CPU).
* Record wall-clock load time and peak RSS during load.
* Repeat 3× (cold process each time) for min/median/max.

### 2. Encoder latency (the Task-77 blocker)

* **Cold:** first query after model load (excluded from warm stats).
* **Warm:** encode the 47 frozen queries, then a documented repeat workload
  (e.g., 10 repeats × 47 = 470 samples). Record p50 / p95 / p99, batch size
  (start with 1; optionally test small batches).
* Report hardware, software versions, and warm-up policy.

### 3. Dense search latency

* Load `corpus_emb.f16.npy` (sha-verified) → f32 + renorm (as
  `load_dense_index` does).
* Measure `emb @ q_vec` + `argsort` per query over the same workload.

### 4. BM25 latency

* Build `BM25Index` once (record build time — the Task-77 cold-start
  dominator).
* Measure `search(query, top_k=2000)` (production H1 pool) and
  `search(query, top_k=INF)` (H3 fusion input) per query.

### 5. RRF fusion latency

* Measure `rrf_fuse_full` (vectorised) per query on the full BM25 + dense
  rankings.

### 6. Total retrieval latency including encoding

* Through `RetrievalService.search` in hybrid mode with a real
  `query_encoder` (SentenceTransformer-backed), on the same workload.
* Also measure BM25-only mode for the production-default baseline.

### 7. Answer generation (currently UNRESOLVED)

* **Skip unless/until an inference path exists.** The repository has no
  Qwen serving code; generation latency and peak memory cannot be measured
  now. If a future task adds an inference path, measure full generation
  latency and peak RSS here, separately from retrieval.

### 8. Disk, cold start, restart

* `du` of corpus, dense index, Python env, model cache.
* Cold start: process start → first successful search (include corpus load,
  BM25 build, dense load, encoder load).
* Restart behavior: kill and restart the process; confirm cold start is
  reproducible and fallback still works if dense artifacts are withheld.

## Integrity checks (must pass on the target host)

* Frozen-bench sha `06625f72…` matches.
* Dense-index corpus-emb sha `f54919e6…` matches.
* Frozen-benchmark reproduction: H3 unit@5 = 0.5385, src@5 = 0.9783
  (`REPRODUCTION_PASS`).
* Full test suite baseline-equal (0 failures beyond pre-existing faiss
  errors).
* BM25 remains the production default (`configs/policy.toml`).

## Gate evaluation

Compare measurements against the **PROPOSED** SLOs in
`data/reports/task78_serving_profile.json`. A gate is marked **PASS** only
if measured in this environment. Encoder or generator gates that cannot be
run remain **UNRESOLVED**. Latency excludes answer generation unless
explicitly measured.

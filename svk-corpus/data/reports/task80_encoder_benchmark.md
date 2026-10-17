# TASK 80 — BGE-M3 CPU Encoder Benchmark on Existing Azure VM

**Verdict: `ENCODER_BENCHMARK_PASS`**

BGE-M3 rev `5617a9f` loaded on CPU in an isolated venv. Encoder latency measured (per-query p95 313 ms, p99 326 ms), determinism exact, embedding dim 1024 L2-normalized matches the index, and the frozen retrieval benchmark reproduced **exactly** with the real encoder (H3 unit@5 0.5385, src@5 0.9783). Task-79's encoder-latency blocker is **resolved**. The end-to-end p95 gate is a **marginal FAIL** (+69 ms / +3.5%), driven by BM25 full-scan variance, not the encoder.

---

## Final status

| Field | Value |
|---|---|
| BGE-M3 loaded successfully | **YES** |
| Encoder p95/p99 measured | **YES** (p95 312.97 ms, p99 326.33 ms per query) |
| End-to-end H3_RRF20 latency measured | **YES** (p50 1032 ms, p95 2069 ms, p99 2497 ms) |
| Frozen retrieval benchmark reproduced | **YES** (exact) |
| Retrieval latency gates | p95 **FAIL** (marginal), p99 **PASS**, cold start **PASS** |
| Existing application preserved | **YES** |
| Production default changed | **NO** |
| Infrastructure provisioned | **NO** |
| Full Qwen assistant validated | **NO** |
| Verdict | **ENCODER_BENCHMARK_PASS** |

---

## 1. Environment and dependency manifest

Isolated task venv, separate from `fpvenv` and all application environments:

| Package | Version | Notes |
|---|---|---|
| Python | 3.12.3 | system |
| torch | 2.14.1+cpu | **CPU-only build; `cuda.is_available()=False`; no CUDA packages** |
| sentence-transformers | 6.1.0 | |
| transformers | 5.19.0 | |
| numpy | 2.5.3 | |
| huggingface-hub, tokenizers, safetensors | (deps) | pulled automatically |

- **Venv:** `/home/azureuser/.venvs/task80-bge` (1.4 GB)
- **Threads:** `torch.set_num_threads(2)` — bounded to the 2 physical cores to protect the running application (OpenCode + uvicorn orchestrator + ollama).
- **Not modified:** project dependencies, `fpvenv`, production config, frozen artifacts.

---

## 2. Exact BGE-M3 revision and model-artifact hashes

| Artifact | SHA-256 (prefix) | Size | Role |
|---|---|---|---|
| `pytorch_model.bin` | `b5e0ce3470abf5ef3831aa1bd5553b48…` | 2165.9 MB | **primary weights for pinned revision `5617a9f` (LOADED)** |
| `tokenizer.json` | `21106b6d7dab2952c1d496fb21d5dc9…` | 16.3 MB | tokenizer |
| `config.json` | `26159e7ad065073448460117eb24b7a4…` | 0.04 MB | config |
| `sentencepiece.bpe.model` | — | 5.0 MB | tokenizer |

- **Pinned revision:** `5617a9f61b028005a4858fdac845db406aefb181` — matches the index manifest (`index_meta.json`).
- **Embedding:** dim 1024, L2-normalized (verified `l2_norm=1.0`), float32 queries.

**Secondary cached revision (honest note):** a second snapshot `9a0624b…` (HuggingFace **PR #130**, `refs/pr/130`) containing `model.safetensors` (2166 MB) was **auto-fetched** by transformers' safetensors preference. This is a loader side-effect, **not** a revision change — the effective encoder is the pinned `5617a9f` (`pytorch_model.bin`), proven by the exact frozen-benchmark match. It only inflates the cache and is removed in cleanup. The index content was **not** affected.

---

## 3. Installation and model-download footprint

| Item | Footprint |
|---|---|
| Task venv | 1.4 GB |
| bge-m3 model cache | **~4.3 GB** on disk |
| Total download | ~4.25 GB (both revisions auto-cached) |
| First load (with download) | ~25.1 s |
| Subsequent load (cached) | ~2.9 s |
| Free disk after | 60 GB (of 123 GB; 52% used) |

Model cache = `pytorch_model.bin` (2166 MB) + PR #130 `model.safetensors` (2166 MB) + tokenizer (16 MB) + sentencepiece (5 MB) + configs.

No new cloud charge: the benchmark ran on the already-provisioned VM using existing Azure free credit.

---

## 4. Cold and warm encoder latency

| Metric | Value |
|---|---|
| First-query latency | 0.264 s |
| **Warm per-query (all 47 frozen, 141 samples)** | **p50 254.61 ms, p95 312.97 ms, p99 326.33 ms**, mean 257.1 ms, max 332.4 ms |
| Warm per-query (representative 12, 120 samples) | p50 257.65 ms, p95 291.35 ms, p99 332.83 ms |
| Determinism (same query twice) | max_abs_diff **0.0** (deterministic) |
| Languages covered | Latin (EN), Devanagari (Prakrit/Hindi), Gujarati |

Representative set: 34 EN, 8 Devanagari/Prakrit, 5 GUJ queries from the frozen 47-case benchmark.

---

## 5. Peak memory and CPU utilization

| Metric | Value |
|---|---|
| Peak process RSS | **4035 MB (4.0 GB)** |
| torch threads | 2 (physical cores) |
| System load during encoding | mean 2.2, p95 2.5 (≈2 cores busy, matching bounded threads) |

The per-process CPU% sampler was mis-instrumented (summed all PIDs) and is **not** reported as reliable; system load is the trustworthy signal.

---

## 6. End-to-end retrieval latency (real encoder)

Dense index sha + model revision + dim verified; **no rebuild, no modification**.

### Component timing (representative queries, 60 samples)

| Component | p50 | p95 | p99 |
|---|---|---|---|
| Encode | 293 ms | 620 ms | 709 ms |
| BM25 full scan | 51 ms | **829 ms** | 1117 ms |
| Dense search | 38 ms | 84 ms | 112 ms |
| RRF fusion | 33 ms | 85 ms | 88 ms |
| **Total** | **431 ms** | 1187 ms | 1569 ms |

### Service-level H3_RRF20 (all 47, 141 samples) — end-to-end

| Metric | Value |
|---|---|
| p50 | **1032 ms** |
| p95 | **2069 ms** |
| p99 | **2497 ms** |
| max | 3019 ms |

This is **encoder-enabled end-to-end latency** (encode + BM25 + dense + fusion + contract), distinct from Task 79's precomputed-embedding retrieval latency.

**Cold start** (with cached encoder): corpus 5.74 s + BM25 57.8 s + dense 1.62 s + encoder 2.91 s ≈ **68 s**.

---

## 7. Frozen-benchmark reproduction (real encoder) — PASS

Single pass, real encoder. Exact match to Task-74/79 aggregates (within 1e-3):

| Mode | unit@5 | src@5 | unit MRR | src MRR |
|---|---|---|---|---|
| H1 BM25 | 0.3846 | 0.9130 | 0.3333 | 0.7986 |
| H3 RRF20 | **0.5385** | **0.9783** | 0.4618 | 0.9174 |

`reproduction_pass = true`. Provenance and contract validation intact (0 fallbacks).

---

## 8. Proposed SLO gate assessment

Thresholds are **proposed** (Task 78); **not** changed to force a pass.

| Gate | Target | Measured | Result |
|---|---|---|---|
| Warm retrieval p95 (incl. encoder) | ≤ 2000 ms | **2069 ms** | **FAIL** (marginal, +3.5%) |
| Warm retrieval p99 (incl. encoder) | ≤ 3000 ms | 2497 ms | **PASS** |
| Cold start | ≤ 120 s | ~68 s | **PASS** |
| Peak RSS ≤ 8 GB on 12 GB host | 8 GB | 4.04 GB | **PASS** (12 GB host assumption N/A — VM has 15.6 GiB; 4.04 GB ≪ 8 GB regardless) |
| Dense index storage | ≤ 1 GB | 0.321 GB | **PASS** |
| Recurring infrastructure cost | ₹0 | — | **UNRESOLVED** (Azure credit finite/expiring; balance not verifiable) |

**Summary: 4 passed, 1 failed (marginal), 1 unresolved.**

The p95 FAIL is dominated by **BM25 full-scan tail variance** (p95 829 ms); the encoder contributes only ~313 ms p95. Encoder latency alone does **not** establish Qwen3-8B generation feasibility — that gate remains unresolved.

---

## 9. Blockers

| ID | Component | Blocker | Impact | Resolution |
|---|---|---|---|---|
| B1 | retrieval p95 | E2E p95 2069 ms > 2 s (+3.5%); BM25 full-scan tail dominates | p95 gate FAIL (marginal) | Candidate: cap the BM25 candidate pool or bound BM25 latency (policy `pool=2000` already reduces this vs the unbounded `INF` path used here). Requires a separately authorized perf/policy change — not done here. |
| B2 | Azure cost | Free credit finite/expiring; balance not readable | ₹0 gate UNRESOLVED | User confirms billing/credit-expiry in Azure portal |
| B3 | Qwen generation | No Qwen3-8B-Base inference serving impl (training code only) | Full assistant NOT feasible | Separate task (out of scope; 2-core CPU also impractical for 8B) |

---

## 10. Reproducibility and cleanup

**Setup:**
```bash
python3 -m venv /home/azureuser/.venvs/task80-bge
/home/azureuser/.venvs/task80-bge/bin/pip install --index-url https://download.pytorch.org/whl/cpu torch==2.14.1
/home/azureuser/.venvs/task80-bge/bin/pip install sentence-transformers==6.1.0
```

**Run:**
```bash
/home/azureuser/.venvs/task80-bge/bin/python experiments/task80/task80_encoder_bench.py --stage smoke
/home/azureuser/.venvs/task80-bge/bin/python experiments/task80/task80_encoder_bench.py --stage full --warmup 3 --iters 10
```

**Cleanup (reclaims ~5.7 GB; touches no production config / frozen artifact / app env):**
```bash
rm -rf /home/azureuser/.venvs/task80-bge                          # ~1.4 GB
rm -rf ~/.cache/huggingface/hub/models--BAAI--bge-m3             # ~4.3 GB (both revisions)
```

---

## Final integrity checks

| Check | Result |
|---|---|
| Existing app + Ollama preserved | **YES** (uvicorn orchestrator + `ollama serve` still running, unmodified) |
| OpenCode preserved | **YES** |
| `configs/policy.toml` still defaults to BM25 | **YES** (`[retrieval] mode = "bm25"`) |
| Frozen benchmark / corpus / source registry / dense index unchanged | **YES** (shas verified) |
| Regression tests (service) | 41/41 OK |
| Regression tests (full suite) | 503 ran, 0 failures, 2 pre-existing faiss import errors, 1 skip (**baseline unchanged** from Task 76/77/79) |
| Tracked-file changes | none to `src/`, `tests/`, `configs/policy.toml` beyond the pre-existing Task-76 +27 `[retrieval]` lines; Task 80 added only new untracked artifacts |
| Infrastructure provisioned/resized | **NO** |
| Production default changed | **NO** |
| Recurring cost claim | **NOT claimed** — Azure billing could not be verified (same as Task 79) |

## Artifacts

- `data/reports/task80_encoder_benchmark.json` — machine-readable decision artifact (this report).
- `data/reports/task80_encoder_benchmark.md` — this markdown report.
- `data/reports/task80_encoder_bench.json` — raw measurements from the benchmark script.
- `experiments/task80/task80_encoder_bench.py` — the benchmark script (smoke/full stages).

# Artifact Inventory — Task 86

Generated: 2026-10-15T06:42:30Z · Git HEAD `feb6ef293077` · branch `main`

Classifications: `SAFE_IN_GIT` · `LOCAL_ONLY` · `REPRODUCIBLE` · `EXTERNAL_DEPENDENCY` · `MISSING` · `UNKNOWN`.

| Path | Size | SHA-256 (first 16) | Class | Purpose | Sensitivity | Recovery |
|---|---|---|---|---|---|---|
| `(git-tracked tree, 428 files)` | — | `—` | **SAFE_IN_GIT** | source pipeline, frozen benchmark, manifests, 115 historical reports, core docs | none | git clone github.com/Priyanshu-47/jainLLM (push status: LOCAL ONLY until pushed) |
| `configs/policy.toml` | 15.1K | `f32308d94dd9d543…` | **LOCAL_ONLY** | [retrieval] section added by Task 76 (+27 lines); production default mode=bm25 | none | recovery archive; content also reproduced in Task-76/84 docs and git diff |
| `src/svk_corpus/retrieval/service.py` | 28.7K | `6a8ab157a0a76f54…` | **LOCAL_ONLY** | production RetrievalService (Task 76; untracked!) | none | recovery archive (untracked — NOT in git clone) |
| `src/svk_corpus/retrieval/api.py` | 13.9K | `96f1f0107b2bbb41…` | **LOCAL_ONLY** | retrieval-only FastAPI app (Task 85) | none | recovery archive (untracked — NOT in git clone) |
| `src/svk_corpus/retrieval/schemas.py` | 4.7K | `8c0fe24e9ba11818…` | **LOCAL_ONLY** | pydantic request/response schemas (Task 85) | none | recovery archive (untracked — NOT in git clone) |
| `tests/test_retrieval_service.py` | 29.0K | `be95dede07910421…` | **LOCAL_ONLY** | 41 retrieval-service regression tests (Task 76) | none | recovery archive (untracked — NOT in git clone) |
| `tests/test_retrieval_api.py` | 22.9K | `364c1b3c2df9aba8…` | **LOCAL_ONLY** | 39 API tests (Task 85) | none | recovery archive (untracked — NOT in git clone) |
| `docs/retrieval_api.md` | 5.1K | `195d06253102be2a…` | **LOCAL_ONLY** | API usage documentation (Task 85) | none | recovery archive (untracked — NOT in git clone) |
| `data/evaluation/dapt01_eval_cases.jsonl` | 34.7K | `06625f72190e3ae1…` | **SAFE_IN_GIT** | FROZEN 47-case benchmark (sha 06625f72...) | none | git clone + hash verification |
| `data/evaluation/dapt01_base_results.jsonl` | 38.4K | `c452ea99a0f3877a…` | **SAFE_IN_GIT** | frozen Task-60 base arm results | none | git clone + hash verification |
| `data/evaluation/dapt01_dapt_results.jsonl` | 45.8K | `6e28f87a244dd9c3…` | **SAFE_IN_GIT** | frozen Task-60 DAPT arm results | none | git clone + hash verification |
| `data/release/rag_corpus.jsonl` | 472.4M | `4db164bc70e68b4f…` | **REPRODUCIBLE** | 164,238-unit RAG corpus served by the API (gitignored, 472M) | none | recovery archive; or rebuild via make all (network+compute) |
| `data/release/training_corpus.jsonl` | 304.5M | `9e9dcda8315e3e76…` | **REPRODUCIBLE** | training-release corpus (gitignored, 304M) | none | recovery archive; or rebuild via make all |
| `manifests/source_manifest.csv` | 117.0K | `b96e572f8d97891c…` | **SAFE_IN_GIT** | source registry / provenance + rights metadata | none | git clone |
| `data/raw` | 31.5M | `—` | **LOCAL_ONLY** | acquired raw sources needed for offline rebuild (untracked, 32M) | none | recovery archive |
| `experiments/task74/dense_index/corpus_emb.f16.npy` | 320.8M | `f54919e63599c94e…` | **LOCAL_ONLY** | BGE-M3 dense index (rev 5617a9f..., untracked, 321M) | none | recovery archive; or re-embed with BGE-M3 (HF download + CPU compute) |
| `experiments/task74/dense_index/index_meta.json` | 1.4K | `ede7a4ead255a416…` | **LOCAL_ONLY** | dense index metadata + alignment hashes | none | recovery archive |
| `experiments/task69-85/ + experiments/sft_01/ + sft_02/ + sft_curation/ + dapt_01/` | — | `—` | **LOCAL_ONLY** | experiment scripts, scorers, evidence builders, SFT checkpoints (91 files, ~680M total) | none | recovery archive (entirely untracked) |
| `data/evaluation/ (98 untracked files: task62-83 results)` | — | `—` | **LOCAL_ONLY** | recorded generation/retrieval results incl. Task 82/83 gates | none | recovery archive |
| `data/reports/ (65 untracked of 180 total: task62-85 reports)` | — | `—` | **LOCAL_ONLY** | task reports + machine-readable summaries (Tasks 62-85) | none | recovery archive |
| `/tmp/opencode/task75/adapter_model.safetensors (+ config/tokenizer, 678M dir)` | 677.7M | `9b4d2bdcfe089118…` | **LOCAL_ONLY** | DAPT-01 QLoRA checkpoint (sha 9b4d2bdc...); referenced by Task 82/83 integrity checks | none | recovery archive (copied in); EXTERNAL copy: Kaggle dataset priyanshu471/dapt01-checkpoint-15248 |
| `svk-corpus/.hf_cache/ (Qwen3-8B-Base, 16G, gitignored)` | — | `—` | **EXTERNAL_DEPENDENCY** | Qwen3-8B-Base fp16 weights (rev 49e3418f...) — used only by historical Kaggle generation runs | none | huggingface-cli download Qwen/Qwen3-8B-Base (NOT included in archive) |
| `~/.cache/huggingface/ (BGE-M3 4.3G, PaddleOCR, faster-whisper, 20G total)` | — | `—` | **EXTERNAL_DEPENDENCY** | BGE-M3 encoder weights (rev 5617a9f...) + OCR/ASR models | none | huggingface-cli download BAAI/bge-m3 --revision 5617a9f61b028005a4858fdac845db406aefb181 |
| `svk-corpus/.venv/` | — | `—` | **REPRODUCIBLE** | isolated Python envs (fastapi/pydantic/uvicorn/httpx/numpy/faiss-cpu; cpu-bench torch) | none | python3 -m venv + pip install (see runbook §4); NOT archived |
| `svk-corpus/.venv-cpu-bench/` | — | `—` | **REPRODUCIBLE** | isolated Python envs (fastapi/pydantic/uvicorn/httpx/numpy/faiss-cpu; cpu-bench torch) | none | python3 -m venv + pip install (see runbook §4); NOT archived |
| `.bench_ckpt/` | 511.0M | `—` | **LOCAL_ONLY** | CPU QLoRA micro-bench checkpoint (511M) — experimental, not the released DAPT-01 adapter | none | included in recovery archive except .bench_ckpt; can be regenerated by pipeline stages |
| `data/domain_train/train.jsonl` | 722.5M | `—` | **LOCAL_ONLY** | DAPT domain-training mix (723M, gitignored) | none | included in recovery archive except .bench_ckpt; can be regenerated by pipeline stages |
| `data/release/low_quality_units.jsonl` | 474.0M | `—` | **REPRODUCIBLE** | quality-stage byproduct (474M, gitignored, regenerable) | none | included in recovery archive except .bench_ckpt; can be regenerated by pipeline stages |
| `data/quality/units_quality.jsonl` | 182.8M | `—` | **REPRODUCIBLE** | quality scores (183M, gitignored, regenerable via make quality) | none | included in recovery archive except .bench_ckpt; can be regenerated by pipeline stages |
| `~/.kaggle/kaggle.json` | 76B | `—` | **LOCAL_ONLY** | Kaggle API credentials (name/size recorded only) | SECRET — contents never read, never archived, never committed | recreate from Kaggle account settings on the new machine |
| `(environment variables)` | — | `—` | **SAFE_IN_GIT** | project-relevant env vars (names only): NONE SET (API requires none) | names only; no values recorded | SVK_RETRIEVAL_* are optional runtime flags; see runbook §9 |
| `docs/REPRODUCIBILITY.md` | 4.6K | `83e24ae8a70cb996…` | **SAFE_IN_GIT** | pipeline reproducibility doc | none | git clone |

## Explicit exclusions

- `.venv/`, `.venv-cpu-bench/` — reproducible via pip; not archived.
- `.hf_cache/` (16G) — Hugging Face re-download; not archived.
- `~/.cache/huggingface/` (20G) — Hugging Face re-download; not archived.
- `.bench_ckpt/` (511M) — experimental CPU bench checkpoint; not archived.
- `~/.kaggle/kaggle.json` — SECRET; never read, never archived, never committed.

## At-risk items (action required before expiry)

1. `/tmp/opencode/task75/` — DAPT-01 adapter lives in `/tmp` (volatile).
   Kaggle dataset `priyanshu471/dapt01-checkpoint-15248` is an external copy.
2. 202 untracked files (all Tasks 62–85 work) exist ONLY on this VM.
3. `configs/policy.toml` +27-line retrieval section is uncommitted.

See `RESTORE_VERIFICATION.md` for the checks to run after restore.

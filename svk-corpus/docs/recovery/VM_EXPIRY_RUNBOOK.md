# VM Expiry Recovery Runbook — svk-corpus / jainLLM

**Purpose.** Restore the Sthānakavāsī Jain AI project on a fresh machine after
the Azure VM (Ubuntu 24.04, free credit expiring ~4 days from 2026-10-14)
becomes inaccessible.

**Scope.** This project is **retrieval-only**. The retrieval API
(`src/svk_corpus/retrieval/api.py`, Task 85 verdict `RETRIEVAL_API_PASS`)
serves ranked evidence over a ~164k-unit corpus with BM25 (production
default) or opt-in hybrid RRF20. **Qwen3-8B answer generation is NOT
implemented and must not be expected after restore.** No GPU is required for
anything in this runbook.

---

## 1. What you need before starting

| Item | Required? | Notes |
|---|---|---|
| The recovery archive (`svk-recovery-*.tar.gz`) + `.sha256` | **Yes** | Copied off the VM per `docs/recovery/RESTORE_VERIFICATION.md` |
| Git clone of `github.com/Priyanshu-47/jainLLM` | Recommended | Contains 428 tracked files; the archive additionally contains all untracked Task 62–85 work |
| Python **3.11+** (3.12 used on the VM; 3.12.x recommended) | **Yes** | `tomllib` is required by `configs/policy.toml` loading |
| Network access to PyPI | Once | For the optional API dependencies |
| Network access to Hugging Face | Optional | Only to re-fetch model weights (Qwen3-8B-Base, BGE-M3) — not needed for the retrieval API |
| Kaggle API credentials (`~/.kaggle/kaggle.json`) | Optional | Only to re-download the DAPT-01 adapter dataset; **recreate from your Kaggle account, never commit it** |
| GPU | **No** | Everything below runs CPU-only |

---

## 2. OS baseline

Tested on: Ubuntu 24.04 x86_64, 4 vCPU, 15.6 GiB RAM, no GPU.
Expected to work on: any modern Linux/macOS/WSL2 with Python 3.11+ and ≥8 GB
RAM (the corpus + BM25 index uses ~1 GiB RSS; startup ~45 s for 164k units).

```bash
# Ubuntu/Debian example
sudo apt-get update && sudo apt-get install -y python3 python3-venv python3-pip git
python3 --version   # must print 3.11+
```

---

## 3. Obtain the code

```bash
# Option A — Git clone (tracked files only; then overlay the archive)
git clone https://github.com/Priyanshu-47/jainLLM.git
cd jainLLM

# Option B — archive only (contains everything from the VM, tracked + untracked)
mkdir jainLLM && tar -xzf <PATH_TO>/svk-recovery-*.tar.gz -C jainLLM --strip-components=1
cd jainLLM
```

Recommended: clone, then extract the archive **on top** so the untracked
Task 62–85 artifacts (retrieval service/API, experiments, reports, large
corpus files) are present.

---

## 4. Python environment

The corpus pipeline itself is **stdlib-only**. The retrieval API needs four
optional packages, installed in an isolated venv (never system Python):

```bash
cd jainLLM/svk-corpus          # note: the project lives in the svk-corpus/ subdir
python3 -m venv .venv
.venv/bin/pip install numpy "fastapi>=0.115,<1" "pydantic>=2,<3" "uvicorn>=0.30,<1" "httpx>=0.27,<1"
# optional, only to run the full historical regression suite without FAISS errors:
.venv/bin/pip install faiss-cpu
```

No lockfile exists; versions pinned in the VM `.venv` at expiry were:
fastapi 0.143.0, pydantic 2.14.1, uvicorn 0.54.0, httpx 0.28.1,
numpy 2.5.3, faiss-cpu 1.15.1 (Python 3.12.3).

---

## 5. Verify integrity

```bash
cd jainLLM/svk-corpus
# frozen benchmark sha (must be 06625f72...):
sha256sum data/evaluation/dapt01_eval_cases.jsonl
# retrieval policy default must remain bm25:
grep -A2 '^\[retrieval\]' configs/policy.toml | head -3
```

Full expected hashes are in `docs/recovery/RECOVERY_MANIFEST.json` and
`docs/recovery/RESTORE_VERIFICATION.md`.

---

## 6. Run the tests

```bash
# established regression baseline (stdlib pipeline; API tests auto-skip
# if fastapi is not installed):
cd jainLLM/svk-corpus
PYTHONPATH=src python3 -m unittest discover -s tests
# expected: Ran 542 tests, 2 pre-existing FAISS import errors
# (TestSentenceTransformerDenseFromPrebuilt.*), 1 skip — OR Ran 503 with
# the same 2 errors if the untracked API tests are absent.

# retrieval API tests (require the venv with fastapi):
PYTHONPATH=src .venv/bin/python -m unittest tests.test_retrieval_api -v
# expected: Ran 39 tests — OK
```

---

## 7. Start the retrieval API (loopback, CPU-only)

```bash
cd jainLLM/svk-corpus
PYTHONPATH=src .venv/bin/python -m svk_corpus.retrieval.api --port 8100
# binds 127.0.0.1:8100 by default; startup loads corpus + BM25 (~45 s)
```

Verify:

```bash
curl -s http://127.0.0.1:8100/health
# expect: {"status":"ok","mode_configured":"bm25","corpus_loaded":true,
#          "n_documents":164238,"dense_available":false,...}

curl -s -X POST http://127.0.0.1:8100/search \
  -H 'Content-Type: application/json' \
  -d '{"query":"When was the Terapanth founded?","top_k":3}'
# expect: mode_used="bm25", results with text_id/source_id/provenance;
#         NO answer field — the API returns evidence only
```

Production retrieval default is **BM25** and must remain so. Hybrid RRF20 is
opt-in via `SVK_RETRIEVAL_MODE=hybrid_rrf20` (invalid values are ignored).

---

## 8. What works without a GPU — and what does not

| Capability | GPU needed? | Status after restore |
|---|---|---|
| Corpus pipeline (`make all`) | No | Works (network only for `acquire`/`tokens`) |
| BM25 retrieval + API `/health`, `/search` | No | Works |
| Hybrid RRF20 retrieval (opt-in) | No* | Works only if the dense index + a caller-supplied BGE-M3 query embedding are present; the API does **not** auto-load the encoder |
| DAPT-01 / SFT training | Yes (was Kaggle T4) | Not part of restore; adapter weights are available (see manifest) |
| **Qwen3-8B generation serving** | Yes (in practice) | **NOT IMPLEMENTED — nothing to restore** |

\* hybrid scoring is CPU-viable; the missing piece is a deployed BGE-M3
query-encoder runtime, which was never shipped.

---

## 9. Environment variables (names only)

The retrieval API requires **no** environment variables. Optional runtime
feature flags (never required, never secrets):

- `SVK_RETRIEVAL_MODE` — `bm25` | `hybrid_rrf20` (invalid values ignored)
- `SVK_RETRIEVAL_SHADOW` — `0` | `1`
- `SVK_RETRIEVAL_STRICT` — `0` | `1`

Kaggle tooling (only if re-downloading the DAPT-01 adapter dataset) reads
`~/.kaggle/kaggle.json` — recreate it from your Kaggle account settings; it
is **not** included in any archive produced by Task 86.

---

## 10. Optional: model weights (not needed for the API)

| Artifact | Where it lived on the VM | Restore method |
|---|---|---|
| Qwen3-8B-Base (16 GB) | `svk-corpus/.hf_cache/` (gitignored) | `huggingface-cli download Qwen/Qwen3-8B-Base` — external dependency |
| BGE-M3 (4.3 GB) | `~/.cache/huggingface/` | `huggingface-cli download BAAI/bge-m3 --revision 5617a9f61b028005a4858fdac845db406aefb181` |
| DAPT-01 adapter (678 MB) | `/tmp/opencode/task75/` (volatile!) | Included in the recovery archive; also Kaggle dataset `priyanshu471/dapt01-checkpoint-15248` |

None of these are required to run the retrieval API or the test suites.

---

## 11. Explicit non-goals

- The API is **retrieval-only**: no answer generation, no streaming, no UI.
- No production retrieval default may be changed as part of recovery.
- Frozen evaluation artifacts (`data/evaluation/dapt01_*`, historical
  reports) must be restored byte-identical — verify with the manifest hashes.

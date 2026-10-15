# Restore Verification — svk-corpus / jainLLM

**Purpose.** Exact checks that establish whether the project has been
recovered successfully on a different machine.

Two columns are tracked honestly:

- **Executed (Task 86, on the Azure VM, 2026-10-14)** — checks run before
  expiry against the live system and the created archive.
- **Pending (on the new machine)** — checks that can only run after the
  archive/clone is restored elsewhere.

---

## 1. Archive integrity (executed on VM; re-run on new machine)

After copying `svk-recovery-YYYYMMDD.tar.gz` (+ `.sha256`) off the VM:

```bash
sha256sum -c svk-recovery-YYYYMMDD.tar.gz.sha256
# must print: svk-recovery-YYYYMMDD.tar.gz: OK
```

| Check | Executed on VM | Pending on new machine |
|---|---|---|
| Archive created and non-zero size | YES (see Task-86 report) | — |
| Archive SHA-256 recorded | YES | re-verify after every copy |
| Archive extracts without error | YES (spot-check) | full extract |
| Expected top-level paths present after extract | YES | re-check |

Expected archive layout after `tar -xzf … -C <dest> --strip-components=0`:

```
jainLLM/svk-corpus/...            # full project incl. untracked Tasks 62-85
tmp-extract/opencode/task75/...   # DAPT-01 adapter (stored as opencode/task75)
```

---

## 2. Frozen-artifact hashes (must be byte-identical)

| Artifact | SHA-256 |
|---|---|
| `data/evaluation/dapt01_eval_cases.jsonl` | `06625f72190e3ae130447345afdc04342bd19cb76f842285706480cba7765b81` |
| `data/evaluation/dapt01_base_results.jsonl` | `c452ea99a0f3877a80fc423d8dad002ba0b91ca4b517156a3894b75b4bc50f74` |
| `data/evaluation/dapt01_dapt_results.jsonl` | `6e28f87a244dd9c34265a9e1f7f3278dbb883774f96e0f3e99959617d3c015cc` |
| `data/release/rag_corpus.jsonl` | `4db164bc70e68b4f89837a9f3d3f3bc7fc126d99c826776ba9bf832f070ff8cf` |
| `data/release/training_corpus.jsonl` | `9e9dcda8315e3e76a68d902dd9b588b55215f86da9be92dc4f9c23e64c43b698` |
| `manifests/source_manifest.csv` | `b96e572f8d97891cc5b472bd21d4355b3b60b2afc74e48d70716ce95bf3293f2` |
| `experiments/task74/dense_index/corpus_emb.f16.npy` | `f54919e63599c94e9a7eb931bde2d4255ee77c2c64c381a28151d63eb00fb91f` |
| `experiments/task74/dense_index/index_meta.json` | `ede7a4ead255a4165e1d28b7d3e6f3a4cc82b27935b7e0e5c426b738dcd3dd05` |
| DAPT-01 `adapter_model.safetensors` | `9b4d2bdcfe089118d0634815596b628506a83c434d3863cff7a731cba75a58e9` |
| `configs/policy.toml` (with Task-76 retrieval section) | `f32308d94dd9d54395daf2d4bb5ef7ede7600f7762e77dd480aea6926bf25851` |

```bash
cd jainLLM/svk-corpus
sha256sum data/evaluation/dapt01_eval_cases.jsonl \
          data/evaluation/dapt01_base_results.jsonl \
          data/evaluation/dapt01_dapt_results.jsonl \
          data/release/rag_corpus.jsonl \
          data/release/training_corpus.jsonl \
          manifests/source_manifest.csv \
          experiments/task74/dense_index/corpus_emb.f16.npy \
          experiments/task74/dense_index/index_meta.json \
          configs/policy.toml
# compare against the table above; all must match
```

| Check | Executed on VM | Pending on new machine |
|---|---|---|
| All 9 hashes computed and match Task-82/83/84/85 values | YES (Task-84/85 reports) | re-run after extract |
| Adapter hash matches | YES (`9b4d2bdc…`) | re-run after copy |

---

## 3. Retrieval stack checks (pending on new machine)

```bash
cd jainLLM/svk-corpus
PYTHONPATH=src python3 -m unittest discover -s tests
# expect: Ran 542 tests; FAILED (errors=2, skipped=40)
#   - the 2 errors are pre-existing FAISS import errors on system python:
#     test_retrieval.TestSentenceTransformerDenseFromPrebuilt.*
#   - or Ran 503 / errors=2 if only tracked+partial files are present
PYTHONPATH=src .venv/bin/python -m unittest tests.test_retrieval_api -v
# expect: Ran 39 tests — OK
grep 'mode ' configs/policy.toml | head -1
# expect: mode = "bm25"  (production default preserved)
```

| Check | Executed on VM | Pending on new machine |
|---|---|---|
| 542/2/40 regression baseline | YES (Task-85 report, 2026-10-14) | re-run |
| 39/39 API tests | YES (Task-85 report) | re-run |
| policy.toml mode=bm25 | YES | re-grep |

---

## 4. Live API check (pending on new machine)

```bash
PYTHONPATH=src .venv/bin/python -m svk_corpus.retrieval.api --port 8100
# separate terminal:
curl -s http://127.0.0.1:8100/health
# expect: "status":"ok","mode_configured":"bm25","corpus_loaded":true,
#         "n_documents":164238
curl -s -X POST http://127.0.0.1:8100/search \
  -H 'Content-Type: application/json' \
  -d '{"query":"When was the Terapanth founded?","top_k":3}'
# expect: mode_used="bm25", results with text_id/source_id/text/locator;
#         no "answer" field
```

| Check | Executed on VM | Pending on new machine |
|---|---|---|
| /health returns ok, 164238 docs | YES (2026-10-14 smoke test) | re-run |
| /search returns evidence, no answer field | YES | re-run |

---

## 5. Git state (executed on VM; informational)

- Branch `main`, HEAD `feb6ef2` … (see manifest).
- 1 tracked modification (`configs/policy.toml`) preserved uncommitted.
- 202 untracked files preserved via archive (they are NOT in the git clone).
- A dedicated recovery commit (Task-86 docs only) was created locally;
  **no push** was performed — pushing requires explicit authorization.

| Check | Executed on VM | Pending on new machine |
|---|---|---|
| Recovery commit exists locally with only docs/recovery/* | YES | `git show --stat <commit>` after clone+fetch (when pushed) |
| Untracked Tasks 62-85 present | YES (archive) | verify paths exist after extract |

---

## 6. Secrets (never part of restore)

- `~/.kaggle/kaggle.json` is **not** in any archive and must be recreated on
  the new machine from Kaggle account settings.
- No environment variable values were recorded anywhere in Task-86 outputs.
- The Git remote URL on the VM embedded a credential; the manifest records
  only `github.com/Priyanshu-47/jainLLM` (host + path). Rotate the token in
  GitHub settings if the VM copy is considered exposed.

---

## 7. Definition of "recovered successfully"

All of the following must hold on the new machine:

1. Archive SHA-256 verified.
2. All nine frozen-artifact hashes match Section 2.
3. Regression suite shows the expected 2 pre-existing FAISS errors and no new ones.
4. API tests 39/39 OK (with venv + fastapi).
5. `/health` returns `ok` with `n_documents=164238`; `/search` returns
   evidence-only results with `mode_used=bm25`.
6. `configs/policy.toml` still declares `mode = "bm25"`.

Until an **independent copy** of the archive (or an authorized git push) is
verified, the project must be considered AT RISK — a local file on the same
Azure VM is not a backup.

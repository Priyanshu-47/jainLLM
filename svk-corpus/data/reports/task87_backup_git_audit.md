# Task 87B — Azure-Side Backup and Git Preservation Audit

Date: 2026-10-15 (UTC) · Scope: Azure VM read-only inspection.
The local Windows OpenCode session owns destination-side download/verification.

## Verdict: `BACKUP_PENDING`

The Azure-side archive is fully verified (checksum match, gzip integrity,
readable listing, critical contents present). Independent destination-side
verification has **not been observed on the VM** — no Windows verification
report is present — so the backup cannot yet be called complete. Per rule 9,
success is **not** inferred from the Azure-side hash alone.

---

## 1. Archive and checksum (Azure side)

| Item | Result |
|---|---|
| Archive | `/home/azureuser/svk-recovery-20261015.tar.gz` — **1,520,048,132 bytes** (1.52 GB), mtime 2026-10-15 06:46:35 UTC, unchanged since Task 86 |
| Sidecar | `…tar.gz.sha256` — 111 bytes, present |
| Sidecar value | `a882a11bdd233850414aa2d602bbc7b66aac9b1260c3b5e822947d805dc923b5` |
| Recomputed SHA-256 | `a882a11bdd233850414aa2d602bbc7b66aac9b1260c3b5e822947d805dc923b5` |
| Expected (Task 87 spec) | `A882A11BDD233850414AA2D602BBC7B66AAC9B1260C3B5E822947D805DC923B5` |
| Comparison | **MATCH** (case-insensitive hex) |
| gzip integrity (`gzip -t`) | **OK** |
| Free disk around archive | 52 GB free on `/` — ample |

## 2. Archive listing (streamed; not extracted into the project)

| Item | Result |
|---|---|
| Total entries | 885 |
| Top-level paths | `jainLLM/svk-corpus/…` and `opencode/task75/…` (DAPT-01 adapter) |
| Critical-path spot check | 21 matches across retrieval source/tests, frozen bench, rag corpus, dense index, policy.toml, recovery docs, adapter |
| Excluded as designed | `.venv*`, `.hf_cache`, `.bench_ckpt`, `kaggle.json`, `__pycache__` (0 matches) |

## 3. Git audit

| Item | Value |
|---|---|
| Branch | `main` |
| HEAD | `39257a77cea3b12c19c210f961f5452e5d4f0bc8` (Task 86 recovery docs commit) |
| Remote (host/path only) | `github.com/Priyanshu-47/jainLLM` — **not pushed**; remote writes unauthorized |
| Tracked modifications | 1: `svk-corpus/configs/policy.toml` (+27 lines, Task-76 retrieval section) — **preserved, uncommitted** |
| Untracked | 204 directory-level entries / **275 files** (`--untracked-files=all`; Task 86's "202" was the directory-level count before task86 artifacts were added) |
| Ignored (categories) | `.venv/`, `.venv-cpu-bench/`, `.hf_cache/`, `.bench_ckpt/`, `__pycache__` under experiments/data/src/tools/tests/outputs — caches and regenerable/large artifacts, correctly gitignored |

## 4. Untracked file categories (275 files; no secret values displayed)

| Category | Count | Notes |
|---|---|---|
| Source (`.py`, non-test) | 73 | experiment scripts + **3 critical retrieval src files** (below) |
| Tests | 5 | `test_retrieval_api.py`, `test_retrieval_service.py`, `test_sft01/02_dataset.py`, `test_task63_adjudication.py` |
| Docs | 4 | TASK76/77 design/audit docs + `retrieval_api.md` |
| Configs | 2 | SFT YAML configs |
| Data — evaluation | 98 | recorded results incl. Task 82/83 gates |
| Data — reports | 66 | Task 62–86 reports (Task 86 report JSON included) |
| Data — training | 3 | SFT train/candidate JSONL |
| Experiments (non-model) | 8 | kernel metadata, dense-index `index_meta.json`, misc |
| Model artifacts | 12 | SFT-01/02 final adapter checkpoints (config + safetensors + tokenizer) |
| Secrets | **0** | tokenizer files were false-positive matches on the word "token"; no real secrets in untracked set (`kaggle.json` lives in `~/.kaggle`, outside the repo, never in git status) |
| Caches | 0 | all caches are gitignored, not untracked |

## 5. At-risk source/tests present ONLY outside Git (untracked; in archive only)

These exist in the recovery archive but **not** in any git commit:

1. `svk-corpus/src/svk_corpus/retrieval/service.py` — production RetrievalService (Task 76)
2. `svk-corpus/src/svk_corpus/retrieval/api.py` — retrieval FastAPI app (Task 85)
3. `svk-corpus/src/svk_corpus/retrieval/schemas.py` — API schemas (Task 85)
4. `svk-corpus/tests/test_retrieval_service.py` — 41 tests (Task 76)
5. `svk-corpus/tests/test_retrieval_api.py` — 39 tests (Task 85)
6. 73 additional experiment scripts (Tasks 62–86 scorers/builders/kernels)
7. All 98 evaluation results + 66 reports from Tasks 62–86

Archive listing confirms every one of these families is inside the tarball.

## 6. Destination-side verification

**PENDING.** No Windows-side verification report exists on the VM
(searched `/home/azureuser`, `/tmp/opencode`, project tree for task87 /
destination-verification artifacts — none found). The Azure-side checksum
match does not substitute for an independent copy. Rule 10: the Azure
archive must **not** be deleted even after a local success is reported.

## 7. Proposed safe future commit groups (NOT executed)

Nothing was staged or committed in this task. Suggested grouping when the
user authorizes remote writes:

**Group A — retrieval stack (highest priority, small, production-critical):**
```bash
git add svk-corpus/src/svk_corpus/retrieval/service.py \
        svk-corpus/src/svk_corpus/retrieval/api.py \
        svk-corpus/src/svk_corpus/retrieval/schemas.py \
        svk-corpus/tests/test_retrieval_service.py \
        svk-corpus/tests/test_retrieval_api.py \
        svk-corpus/docs/retrieval_api.md \
        svk-corpus/docs/TASK76_RETRIEVAL_DESIGN.md \
        svk-corpus/docs/TASK76_FEATURE_FLAG_ROLLBACK.md \
        svk-corpus/docs/TASK77_SERVING_ENV_AUDIT.md
git commit -m "Tasks 76-85: retrieval service, API, schemas, tests, docs"
```

**Group B — experiment scripts + small configs (code only, no binaries):**
```bash
git add svk-corpus/experiments/task69 svk-corpus/experiments/task7[0-9] \
        svk-corpus/experiments/task8[0-6] svk-corpus/experiments/sft_01 \
        svk-corpus/experiments/sft_02 svk-corpus/experiments/sft_curation \
        svk-corpus/configs/sft_qwen3_8b_v1.yaml \
        svk-corpus/configs/sft_qwen3_8b_sft02_v1.yaml
# then unstage any >90MB binaries (check with: git status --porcelain | awk '{print $2}' | xargs -I{} du -m {} | sort -rn | head)
git commit -m "Tasks 62-86: experiment scripts, scorers, SFT configs"
```

**Group C — evaluation results + reports (after size check; exclude >90MB):**
```bash
git add svk-corpus/data/evaluation svk-corpus/data/reports
# verify no file exceeds GitHub 90MB soft/100MB hard limits before commit
git commit -m "Tasks 62-86: evaluation results and reports"
```

**Group D — policy.toml (user's own +27 mod; confirm intent first):**
```bash
git add svk-corpus/configs/policy.toml
git commit -m "Task 76: retrieval policy section (bm25 default, hybrid opt-in)"
```

**Never commit:** `*.safetensors`, dense-index `corpus_emb.f16.npy` (321M),
large JSONL (>90MB), `.venv*`, caches, anything under `~/.kaggle`.

Then (only with explicit authorization):
```bash
git push origin main
```

## 8. Final report summary

- **Verdict: `BACKUP_PENDING`.**
- Azure checksum: `a882a11b…923b5` — matches expected; gzip OK; 885-entry listing readable; critical contents confirmed.
- Destination verification observed: **NO** (pending the Windows session's report).
- At-risk untracked: 3 retrieval src files + 5 test files + 73 experiment scripts + 164 eval/report files — all in the archive, none in git.
- Archive remains on the VM; **do not delete it** (rule 10).
- FanPulse (8000) and Ollama (11434) untouched and live; `policy.toml` mod preserved; no pushes, no history rewrites.

**Next action required from the user:** complete the Windows-side download +
`Get-FileHash` verification and surface that report; then, if desired,
authorize `git push` (Groups A–D above) for an independent Git copy.

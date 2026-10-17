# Task 85 — Retrieval-only FastAPI service

Generated: 2026-10-14T08:36:31Z (97.3s)

## Verdict: **RETRIEVAL_API_PASS**

## 1. Implementation

- App: `src/svk_corpus/retrieval/api.py` (FastAPI factory `create_app`)
- Schemas: `src/svk_corpus/retrieval/schemas.py` (pydantic v2, 1:1 with ServiceResult)
- Tests: `tests/test_retrieval_api.py` (39 tests, all pass in .venv)
- Docs: `docs/retrieval_api.md`
- Endpoints: GET /health, POST /search
- Default bind: `127.0.0.1:8100` (loopback; port 8100 avoids FanPulse 8000 / Ollama 11434)

## 2. Test results

| Suite | Result | Errors |
|---|---|---|
| API tests (.venv, fastapi) | Ran 39 tests in 61.961s | 0 |
| Established regression (system python) | Ran 542 tests in 31.874s | 2 pre-existing faiss |

Known pre-existing: 2 FAISS import errors (`TestSentenceTransformerDenseFromPrebuilt.*`) — reported separately; not caused by this task.

## 3. Integrity

| Artifact | Status |
|---|---|
| data/evaluation/dapt01_eval_cases.jsonl | OK |
| experiments/task74/dense_index/corpus_emb.f16.npy | OK |
| /tmp/opencode/task75/adapter_model.safetensors | OK |
| configs/policy.toml [retrieval] mode | bm25 |

- FanPulse (port 8000) alive: **True**
- Ollama (port 11434) alive: **True**
- BM25 production default: **preserved** (policy.toml unchanged).
- H3_RRF20 hybrid: **opt-in only** (env feature flag; invalid values ignored).

## 4. Policy + fallback behaviour

- `GET /health` reports `mode_configured`, `dense_available`, `bm25_fallback_active` honestly; never claims hybrid is available when dense/encoder is absent.
- `POST /search` returns `mode_requested` vs `mode_used`; when hybrid falls back, `mode_used=bm25` with explicit `fallback_reason`.
- `strict_dense=True` + missing dense → 503 fail-closed, never silent BM25.
- Evidence contract preserved: `channel`, `unit_bm25_rank/score`, `metadata_match`, locator, scope, authorship all pass `validate_result`.

## 5. Dependencies

Installed in: .venv (isolated; fpvenv and system Python untouched)

| Package | Purpose |
|---|---|
| fastapi | HTTP framework |
| pydantic | request/response schemas |
| uvicorn | ASGI server |
| httpx | TestClient (tests only) |

System Python and FanPulse `fpvenv` were not modified.

## 6. Service fix (pre-existing bug)

`src/svk_corpus/retrieval/service.py`: when reconstructing `MetadataMatchEvidence` from `SourceMatch.as_dict()`, the bookkeeping key `identifier_only` was passed through and crashed the source-metadata channel on the real corpus. Fixed by filtering to contract fields. No existing test covered this path (all service tests use `sidx=None`); regression baseline unchanged.

## 7. Final status

| Criterion | Status |
|---|---|
| API implemented and tested | YES |
| Health + search endpoints verified | YES |
| BM25 default preserved | YES |
| Hybrid remains opt-in | YES |
| Provenance + fallback tests passed | YES |
| Existing application preserved | YES |
| Generation implemented | NO |
| Production default changed | NO |
| Infrastructure provisioned | NO |

**Verdict: RETRIEVAL_API_PASS**

## Repro

```bash
PYTHONPATH=src .venv/bin/python -m svk_corpus.retrieval.api --port 8100
PYTHONPATH=src .venv/bin/python -m unittest tests.test_retrieval_api
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 experiments/task85/task85_report.py
```

# Retrieval-only HTTP API (Task 85)

A minimal FastAPI service over the existing `RetrievalService`. Returns
ranked evidence with provenance. **Does not generate answers and does not
run any language model.**

## Dependencies

The stdlib pipeline has zero required dependencies (`pyproject.toml`).
This API adds optional ones, installed only in the repo's isolated `.venv`
(never system Python, never the FanPulse `fpvenv`):

```bash
.venv/bin/pip install "fastapi>=0.115,<1" "pydantic>=2,<3" "uvicorn>=0.30,<1" "httpx>=0.27,<1"
```

| Package | Version pinned in `.venv` | Role |
|---|---|---|
| fastapi | 0.143.0 | HTTP framework + OpenAPI |
| pydantic | 2.14.1 | request/response schemas |
| uvicorn | 0.54.0 | ASGI server |
| httpx | 0.28.1 | TestClient transport (tests only) |

## Startup / shutdown

```bash
# from repo root
PYTHONPATH=src .venv/bin/python -m svk_corpus.retrieval.api --port 8100

# shutdown: Ctrl+C, or
pkill -f "svk_corpus.retrieval.api"
```

Binds to **127.0.0.1** by default (loopback only). Port **8100** avoids
FanPulse (8000) and Ollama (11434). Startup loads the corpus + BM25 index
once (~45 s for 164k units); it never downloads models and never loads the
dense index unless hybrid mode is explicitly configured.

## Endpoints

### `GET /health`

```json
{
  "status": "ok",
  "service": "svk-corpus-retrieval",
  "mode_configured": "bm25",
  "mode_default": "bm25",
  "corpus_loaded": true,
  "n_documents": 164238,
  "dense_available": false,
  "query_encoder_available": false,
  "bm25_fallback_active": false,
  "strict_dense": false,
  "fallback_on_dense_failure": true,
  "initialization_errors": []
}
```

- `status`: `ok` | `degraded` (hybrid configured but will fall back to
  BM25) | `error` (initialization failed).
- Never exposes credentials, environment variables, or account identifiers.
- `dense_available` is honest: with the production `bm25` default it is
  `false` because the dense index is intentionally not loaded.

### `POST /search`

Request:

```json
{"query": "When was the Terapanth founded?", "top_k": 3}
```

- `query`: 1–2000 chars, non-whitespace (422 otherwise).
- `top_k`: 1–50, default 10 (422 otherwise).
- Optional header `X-Request-ID` is echoed back; otherwise a UUID is generated.
- Bodies > 64 KiB are rejected with 413.

Response (truncated):

```json
{
  "request_id": "smoke-001",
  "mode_requested": "bm25",
  "mode_used": "bm25",
  "fallback_reason": null,
  "latency_s": 0.089,
  "top_k": 3,
  "n_results": 3,
  "results": [
    {
      "rank": 1,
      "channel": "unit_bm25",
      "score": 8.42,
      "text_id": "SVK-2008:u02869:16d4ed700d3d0af1",
      "source_id": "SVK-2008",
      "title": "Woolner's Introduction To Prakrit (1917)",
      "text": "Vv. 19 and 20. And when nine hundred years…",
      "parent_source_id": "",
      "locator": {"citation": "…", "page": null, "section": "…"},
      "religious_scope": "CONTEXTUAL_JAIN",
      "religious_scope_confidence": "…",
      "knowledge_layer": "…",
      "teacher_or_author": "…",
      "lineage": "…",
      "source_quality": "…",
      "methods": {"bm25": 1},
      "unit_bm25_rank": 1,
      "unit_bm25_score": 8.42,
      "dense_rank": null,
      "dense_score": null,
      "metadata_match": null
    }
  ]
}
```

- `mode_used` reflects what **actually served** the request. If hybrid was
  requested but dense/encoder is unavailable, `mode_used` is `bm25` and
  `fallback_reason` explains why — results are never mislabelled as hybrid.
- `channel` is the evidence-contract channel (`unit_bm25`, `dense`,
  `source_metadata`). `metadata_match` is populated only on
  `source_metadata` results.
- There is **no** `answer` field. The endpoint returns evidence only.

## curl examples (loopback)

```bash
curl -s http://127.0.0.1:8100/health | python3 -m json.tool

curl -s -X POST http://127.0.0.1:8100/search \
  -H 'Content-Type: application/json' \
  -H 'X-Request-ID: my-req-1' \
  -d '{"query": "Samayika meditation practice", "top_k": 5}' \
  | python3 -m json.tool

# validation demo -> 422
curl -s -o /dev/null -w '%{http_code}\n' -X POST http://127.0.0.1:8100/search \
  -H 'Content-Type: application/json' -d '{"query": ""}'
```

## Retrieval policy

Unchanged and frozen (Task 84):

- Production default: `mode = "bm25"` in `configs/policy.toml`.
- `hybrid_rrf20` is opt-in only (`SVK_RETRIEVAL_MODE=hybrid_rrf20` env
  feature flag; invalid values are ignored, never silently applied).
- Dense-index sha verification, explicit BM25 fallback with logged reason,
  and strict-dense fail-closed behaviour are all preserved from
  `RetrievalService`.

## Security / resource posture

- Loopback bind by default; no auth secrets; no firewall changes.
- Request validation via pydantic; 64 KiB body ceiling.
- Logs request shape (id, query fingerprint, length, mode, counts) —
  never the raw query text or retrieved content.
- No background jobs; one corpus/index load at startup; no model downloads.

## Tests

```bash
# API tests (requires .venv with fastapi)
PYTHONPATH=src .venv/bin/python -m unittest tests.test_retrieval_api -v

# established regression baseline (system python; API tests auto-skip)
PYTHONPATH=src python3 -m unittest discover -s tests
```

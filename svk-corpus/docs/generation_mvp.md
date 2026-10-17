# Generation MVP — Evidence-Grounded Answer Component (experimental)

Status: **experimental, isolated, not production**. Created for Task 89.
Nothing in this component changes the retrieval API, the production
retrieval default, or any frozen artifact.

## What it is

A first working answer-generation path:

```
question -> RetrievalService (configs/policy.toml, mode = bm25)
        -> packaged evidence (E1..E5, provenance: source_id/text_id/title/
           sect/religious_scope/knowledge_layer/teacher)
        -> strict grounding prompt (system) + delimited evidence (user)
        -> local Ollama model (qwen2.5:7b-instruct, loopback only)
        -> validated answer with citations  OR  explicit ABSTAIN
```

Design rules enforced in code:

- **Evidence is data, not instructions.** Corpus passages sit inside
  `<evidence …>` blocks in the user message; all instructions live in the
  system prompt. Injected commands inside passages are quoted as data.
- **Citations must be real.** Every `[E#]` token is validated against the
  actually retrieved evidence ids; unknown ids are stripped from the
  presented answer and reported in `invalid_citations`.
- **Abstention over guessing.** Empty evidence returns a deterministic
  abstention without calling the model; insufficient/irrelevant/
  contradictory evidence must produce `ABSTAIN: …`.
- **Sect/tradition awareness.** Each evidence block carries `sect`,
  `religious_scope`, `knowledge_layer`, `teacher_or_author`; the prompt
  requires separating canonical/Agam material, Sthānakavāsī
  commentary/teacher material, other traditions, and labelled inference.
- **Not a religious authority.** The system prompt frames the assistant as
  a research aid that reports what sources say.
- **Local only.** `OllamaProvider` rejects any non-loopback endpoint at
  construction (`ValueError`); there is no download/pull/install path in
  the package (enforced by tests).

## Files

| File | Purpose |
|---|---|
| `src/svk_corpus/generation/provider.py` | Ollama `/api/generate` client, loopback-only, `SVK_GEN_*` config, error taxonomy |
| `src/svk_corpus/generation/answer.py` | Evidence packaging, prompt building, citation validation, `AnswerService` |
| `src/svk_corpus/generation/schemas.py` | Pydantic request/response models (port 8101) |
| `src/svk_corpus/generation/api.py` | **Separate** FastAPI app factory + entry point on `127.0.0.1:8101` |
| `tests/test_generation.py` | 47 tests (mocked; no model required) |
| `experiments/task89/run_task89_eval.py` | Smoke-subset evaluation runner |
| `docs/generation_mvp.md` | This document |
| `data/reports/task89_generation_mvp.md` | Task 89 results report |
| `data/reports/task89_generation_eval.json` | Machine-readable evaluation results |

## Dependencies

Declared exactly like `docs/retrieval_api.md` (the core pipeline itself
stays stdlib-only; `pyproject.toml` dependencies remain empty on purpose):

```bash
.venv/bin/pip install "fastapi>=0.115,<1" "pydantic>=2,<3" "uvicorn>=0.30,<1" "httpx>=0.27,<1"
```

Already installed in the repo `.venv` for Task 89. Tests on the system
Python skip automatically when these are absent (regression baseline is
unchanged).

## Configuration (no credentials)

| Env var | Default | Meaning |
|---|---|---|
| `SVK_GEN_ENDPOINT` | `http://127.0.0.1:11434` | Local Ollama only (loopback enforced) |
| `SVK_GEN_MODEL` | `qwen2.5:7b-instruct` | Must already exist in `ollama list` |
| `SVK_GEN_TIMEOUT_S` | `300` | CPU generation needs headroom |
| `SVK_GEN_NUM_PREDICT` | `256` | Output-token cap |
| `SVK_GEN_NUM_CTX` | `4096` | Prompt window (never truncated) |
| `SVK_GEN_TEMPERATURE` | `0.0` | Greedy decoding |

Retrieval settings come from `configs/policy.toml` as-is
(`mode = "bm25"`, `evidence_k = 5`, `text_trunc = 500`). This component
never sets or overrides `SVK_RETRIEVAL_*`.

## Start / stop (without touching any existing service)

Start (its own process, port 8101):

```bash
cd svk-corpus
PYTHONPATH=src .venv/bin/python -m svk_corpus.generation.api \
    --host 127.0.0.1 --port 8101
```

First request after startup loads the corpus + BM25 index (~60 s), same as
the retrieval API cold start.

```bash
curl -s http://127.0.0.1:8101/health
curl -s http://127.0.0.1:8101/answer \
  -H 'content-type: application/json' \
  -d '{"question":"How is ahimsa defined by Farquhar?"}'
```

Stop — kill **only** the process you started:

```bash
# find the pid of THIS app only (never pkill uvicorn — port 8000 uses uvicorn too)
ss -tlnp | grep 8101
kill <pid-from-8101>
```

Ports: **8101 = this MVP**, 8100 = retrieval API (production), 8000 =
FanPulse orchestrator, 11434 = Ollama. Never restart/reconfigure the other
three from this component.

## Tests

```bash
cd svk-corpus
PYTHONPATH=src .venv/bin/python -m unittest tests.test_generation   # 47 tests, all mocked
PYTHONPATH=src python3 -m unittest tests.test_generation            # skips httpx/fastapi cases
```

Unit tests never call the model; the provider tests use
`httpx.MockTransport`. A live smoke test is run separately by
`experiments/task89/run_task89_eval.py` (or a manual
`AnswerService.from_repo(...)` call) and is reported with its own latency.

## Known limitations (honest summary)

- CPU-only generation: ~85–140 s per answer on this 4-vCPU VM (measured);
  retrieval itself is ~0.2 s.
- 8-case smoke subset only (of 47 frozen cases) — not a validated
  benchmark; see `data/reports/task89_generation_mvp.md`.
- Observed failure modes: over-abstention when the gold unit is outside the
  BM25 top-5 or the answer needs source-manifest metadata (author/publisher
  fields) that unit passages do not contain; occasional hybrid output that
  answers *and* appends an `ABSTAIN:` sentence.
- The assistant must not be presented as a religious authority; it has no
  web access, no tools, and no identity beyond this prompt.

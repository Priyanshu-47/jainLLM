# Task 89 — Evidence-Grounded Generation MVP: Results

Date: 2026-10-17 (UTC) · Component: experimental, isolated, loopback-only

## Verdict: `GENERATION_PARTIAL`

Local generation works, evidence-grounded orchestration is implemented, and
all tests pass — but important quality and evaluation gates remain
(over-abstention on retrievable-answerable cases, hybrid answer/ABSTAIN
outputs, CPU latency ~100 s/answer, and only an 8-case smoke subset).
Not production-ready; no such claim is made.

---

## Phase A — Feasibility gate: PASS

| Check | Result |
|---|---|
| Ollama endpoint reachable | `http://127.0.0.1:11434` (v0.40.2) |
| Model present | `qwen2.5:7b-instruct` (4.68 GB) via `ollama list` — the only model; **nothing pulled or downloaded** |
| Minimal generation | `POST /api/generate` returned `"OK"` (17.5 s cold, 10-token reply) |
| Real evidence with provenance | In-process production path: `load_retrieval_policy` → `RetrievalService.from_repo` — 164,238 docs, mode `bm25`, 0.225 s, results carry `text_id`/`source_id`/`title`/`locator` citations + `sect`/`religious_scope`/`knowledge_layer` fields |
| Dependencies | `fastapi 0.143.0`, `pydantic 2.14.1`, `uvicorn`, `httpx 0.28.1` already in repo `.venv` |
| Port 8100 | Was not running; never touched |

## Phase B — Implementation

New isolated package (nothing existing was modified):

| File | Lines | Role |
|---|---|---|
| `src/svk_corpus/generation/provider.py` | 214 | Loopback-only Ollama client; error taxonomy (timeout / unavailable / malformed); `SVK_GEN_*` env config; `num_predict=256`, `num_ctx=4096`, `temperature=0`, `timeout=300 s` |
| `src/svk_corpus/generation/answer.py` | 414 | Evidence packaging (E1..E5), prompt build (instructions ⇄ evidence strictly separated), citation validation/stripping, abstention paths, `AnswerService` |
| `src/svk_corpus/generation/schemas.py` | 98 | Pydantic models for the 8101 app |
| `src/svk_corpus/generation/api.py` | 199 | **Separate** app factory `create_generation_app` → `GET /health`, `POST /answer` on `127.0.0.1:8101`; 16 KiB body cap; request-id + fingerprinted logs (no raw question text) |
| `src/svk_corpus/generation/__init__.py` | 23 | Public exports |

Reused unchanged: `RetrievalService` + `load_retrieval_policy` (production
BM25 default from `configs/policy.toml`, which was **not** modified) and
the provenance contracts (`ServiceResult`/`SearchResponse`/`doc.citation`).

## Phase C — Tests: 47/47 pass (both interpreters)

`tests/test_generation.py` (608 lines), all mocked — no running model:

- valid question + evidence, BM25 mode confirmed on every answer
- citation ids must belong to evidence (`[E9]` stripped + reported, incl. on the abstain path)
- empty evidence → deterministic abstention, **model not called**
- irrelevant evidence → model `ABSTAIN` honoured
- contradictory passages both shown to model → explicit abstention, no reconciled doctrine
- timeout / connection failure / malformed output / empty output → typed `error`, no crash
- prompt-injection passage: appears only inside `<evidence>` block, never in system instructions
- BM25 remains the default (`RetrievalPolicy()` and repo `policy.toml` both `bm25`); generation package never sets `SVK_RETRIEVAL_*`
- no external calls: non-loopback endpoints rejected (`ValueError`); source scan forbids `api/pull`, `subprocess`, `urllib.request`, `requests.`, `openai`, `anthropic`, `transformers`, `torch`
- HTTP app: `/health`, `/answer` happy path, 422 (blank/extra/oversized-by-schema), 413 body cap, 503 on init errors; retrieval API still exposes **no** `/answer` route; binds `127.0.0.1:8101`, retrieval API still `8100`

Regression baselines (unchanged, plus new tests):

| Suite | Ran | Errors | Skipped |
|---|---|---|---|
| system python, full discovery | **589** (542 baseline + 47 new) | 2 (pre-existing faiss) | 58 (40 baseline + 18 dep-skips) |
| `.venv`, full discovery | 555 | 14 — all pre-existing (12 `jsonschema` missing in `.venv` for sft/task63 modules, 2 faiss); **0 generation failures** | 1 |

## Phase D — Evaluation

Runner: `experiments/task89/run_task89_eval.py`.
Subset: **8 of 47** frozen cases (`DAPT01EVAL-001, 002, 024, 028, 034,
036, 037, 040`) covering 5 categories + both abstention behaviours —
clearly labelled **SMOKE SUBSET, not a validated benchmark**. The frozen
file `data/evaluation/dapt01_eval_cases.jsonl` was read only; frozen scorer
logic (`score_task60.score_case`) imported read-only.

Model/runtime: `qwen2.5:7b-instruct` on local CPU Ollama, greedy
(temperature 0, num_predict 256, num_ctx 4096, timeout 300 s), retrieval
mode `bm25`, `evidence_k=5`, `text_trunc=500`.

### Run 2 (final, revised prompt)

| Case | Category | Obj. score | Cited OK | Abstained (expected) | Support ratio | Total latency |
|---|---|---|---|---|---|---|
| 001 | JAIN_TERMINOLOGY | 1.0 | ✓ [E1] | no (no) | 0.33 | 93.6 s |
| 002 | JAIN_TERMINOLOGY | 0.0 | ✓ [E1–E3] | **yes (no — wrong)** | 0.35 | 136.8 s |
| 024 | AGAM_GROUNDED | 1.0 | ✓ [E1–E5] | no (no) | 0.58 | 94.1 s |
| 028 | STHĀNAKAVĀSĪ_DISTINCTION | 1.0 | ✓ [E1] | no (no) — hybrid text | 0.31 | 110.8 s |
| 034 | SOURCE_ATTRIBUTION | 0.0 | — | **yes (no — wrong)** | 0.28 | 88.1 s |
| 036 | ABSTENTION | 0.0* | — | yes (yes) ✓ | 0.32 | 85.7 s |
| 037 | ABSTENTION | 1.0 | — | yes (yes) ✓ | 0.22 | 119.1 s |
| 040 | PRACTICE | 1.0 | ✓ [E1] | no (no) — hybrid text | 0.46 | 92.7 s |

\* 036: structural abstention correct; the frozen keyword-marker scorer
missed the model's wording ("does not provide…" not in its marker list) —
the two metrics disagree by design and are reported separately.

### Aggregate (run 2)

| Metric | Value |
|---|---|
| Cases / errors | 8 / **0** |
| Frozen objective score (mean / full-pass) | **0.625** / 5 of 8 |
| Citation validity (no fabricated ids) | **1.00** (0 invalid ids in all 16 answers across both runs) |
| Citation present | 0.75 overall; **1.00 among the 4 answered (non-abstain) cases** |
| Abstention correctness (structural) | **0.75** — 2/2 expected abstentions correct; 2/6 answerable cases wrongly abstained (002, 034) |
| Evidence support ratio (lexical proxy, mean) | 0.356 |
| Sect-attribution heuristic flags | 1 (037 — question-term echo inside an abstention, not an asserted claim) |
| Answers with ≥1 uncited sentence (heuristic) | 8/8 — model cites at paragraph end; sentence-level heuristic overcounts |
| Latency | retrieval mean **0.24 s**; generation mean **102.4 s**; total mean **102.6 s**, max 136.8 s |

### Run 1 vs run 2 (prompt revision, disclosed)

Run 1 (`experiments/task89/task89_generation_eval_run1.json`): objective
0.50, abstention-correct 0.50, citation-present 0.25, citation-valid 1.00.
After run 1 the system prompt was revised **once** (attribution-by-header
rule; "prefer a cautious cited answer over abstaining"), which fixed the
clearest over-abstention (040: answer present in E1, model demanded
in-text author attribution). Because the same 8 cases were reused, run-2
scores carry mild optimistic bias — recorded as a limitation.

### Qualitative findings

- **Strong**: 001 (definition + `[E1]`), 024 (all five passages correctly
  used/weighted), 037 (correctly refused to invent a founding year and
  noted the conflicting `1658` passage refers to the Sadhs — no invented
  doctrine), 036 (correct abstention on absent publication year).
- **Over-abstention root causes are retrieval-side, not fabrication**:
  002 — gold grounding unit `SVK-0038:u00638` outside BM25 top-5;
  034 — answer lives in source-manifest `author` metadata, which unit
  passages do not contain (no manifest channel reached the top-5).
- **Hybrid protocol mixing**: 028 and 040 answer correctly with citation
  *and* append an `ABSTAIN:` sentence for an adjacent unasked aspect —
  classified as answered (marker only counts at reply start) but flagged
  here as a prompt-adherence defect.
- **Safety**: zero fabricated citation ids, zero invented years/authors,
  zero errors, abstention machinery engaged exactly when the model judged
  evidence insufficient.

## Phase E — Deliverables

- Isolated generation provider + answer orchestration (Phase B table)
- `tests/test_generation.py` — 47 tests; dependency declarations in
  `docs/generation_mvp.md` (pip line, same style as `docs/retrieval_api.md`;
  `pyproject.toml` left stdlib-only on purpose)
- `docs/generation_mvp.md` — architecture, config, **start/stop instructions**
  (own uvicorn process on 8101; kill only its pid; never touches 8000/8100/11434)
- `data/reports/task89_generation_mvp.md` — this report
- `data/reports/task89_generation_eval.json` — machine-readable results
- Raw outputs: `experiments/task89/task89_case_outputs.jsonl` (run 2),
  `experiments/task89/task89_case_outputs_run1.jsonl`,
  `experiments/task89/task89_generation_eval_run1.json`

## Live smoke (reported separately from mocked tests)

In-process `AnswerService.from_repo` + one real question
("How is ahimsa defined by Farquhar?"): **service init 55.8 s**
(corpus+BM25), **retrieval 0.125 s**, **generation 20.13 s** (103 tokens,
warm model), **total 20.25 s** → correct grounded answer with `[E1]` after
the prompt revision (earlier cold attempt hit the original 120 s timeout,
which is why the default is now 300 s). Eval-run generation latencies
(85–137 s) are listed separately in the table above.

## Integrity / safety confirmations

- `configs/policy.toml` still `mode = "bm25"` (+27 mod preserved, uncommitted, unedited by Task 89)
- No frozen benchmark, historical result, corpus, manifest, or old report modified (only new files created)
- Ollama, FanPulse (8000), retrieval API (8100) running untouched; no service stopped/restarted/reconfigured; port 8101 never left running (smokes/eval ran in-process)
- No model pull/download, no system package install, no training, no external AI API (loopback enforced in code)
- No secrets in code, logs, reports, or outputs; **nothing committed or pushed** (all Task-89 files untracked)

## Remaining blockers / next gates

1. Retrieval depth + source-manifest metadata channel for attribution
   questions (002/034) — retrieval-side work, policy-governed.
2. Hybrid answer/ABSTAIN protocol adherence (028/040).
3. CPU latency ~100 s/answer; Qwen3-8B serving remains unimplemented on
   this VM (unchanged by design).
4. Evaluation breadth: 8/47 cases, one run, no human adjudication —
   any broader claim requires a properly powered, human-reviewed study.

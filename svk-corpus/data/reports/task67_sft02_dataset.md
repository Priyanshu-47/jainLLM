# TASK 67 — SFT-02 Dataset Build from the Task-66 Failure Analysis (Data + Gate + Tests + Config)

**Date:** 2026-10-01
**Status:** COMPLETE · **HARD STOP:** NO TRAINING

---

## 1. Scope declaration

- Built the corrected **SFT-02 dataset** required by Task-66 §13/§14, plus the
  anti-template quality gate, validation tests and a conservative training
  config.
- **No training was run. No Kaggle API call. No kernel created or launched.**
  `configs/sft_qwen3_8b_sft02_v1.yaml` declares `kaggle.status: not_created`.
- **The frozen 47-case benchmark is byte-identical** —
  `data/evaluation/dapt01_eval_cases.jsonl` sha256
  `06625f72190e3ae130447345afdc04342bd19cb76f842285706480cba7765b81`
  (verified by every validator run and test).
- **DAPT-01 (0.2660 factual grounding) remains the current best.**
  **SFT-01 (0.2305) stays unpromoted.** No score in this task changes either
  statement — SFT-02 scores are NOT_MEASURED by design.

## 2. Repository state

- `git diff` → **empty (0 tracked modifications)**.
- `git status` → untracked files only; this task adds the `task67_*` outputs
  below. SFT / Task-64..66 files remain untracked exactly as before.
- Frozen benchmark file not modified (absent from both `git diff` and
  `git status`).

## 3. Deliverables

| Path | Detail | sha256 (first 16) |
|---|---|---|
| `data/training/sft_train_v2.jsonl` | 61 train rows | `3a45925f7f3e3c8d` |
| `data/evaluation/sft_eval_v2.jsonl` | 13 eval rows | `ba59533699b28328` |
| `data/reports/task67_sft02_build_stats.json` | build statistics | `ff57d93e9b7b6986` |
| `experiments/sft_02/sft02_common.py` | shared helpers / constants | `aadb170f9cabc8ce` |
| `experiments/sft_02/anti_template_gate.py` | Phase-5 anti-template gate | `ab31d7e78392f42b` |
| `experiments/sft_02/build_sft02_dataset.py` | deterministic builder | `68b505e0673a5903` |
| `experiments/sft_02/validate_sft02_dataset.py` | 25-check validator | `3b875638f7971e20` |
| `tests/test_sft02_dataset.py` | 27 tests | `466ea4e3b55e2426` |
| `configs/sft_qwen3_8b_sft02_v1.yaml` | conservative config (not launched) | `98ffe53e5dba1d89` |
| `data/reports/task67_sft02_dataset.md` | this report | — |
| `data/reports/task67_sft02_dataset.json` | machine-readable report | — |

Inputs were read-only: gold candidates 54 · sft_train_v1 50 · sft_eval_v1 9 ·
verified pool 16,409 · corpus 97,763 units / **39 sources** (SVK-0007…SVK-2029;
SVK-2030–2037 have zero corpus units) · manifest 107 sources · rights audit ·
frozen 47 cases.

## 4. Composition vs Task-66 §14 targets

Totals: **74 rows = 61 train + 13 eval** over **22 sources**.

| # | Requirement (Task-66 §14) | Actual | Status |
|---|---|---|---|
| 1 | concept/practice 12–15, incl ≥8 practice | 14 rows (3 concept + **11 practice**: Kayotsarga 2, Samayik 2, Pratikraman 2, Chauvisantho, Paushadh, Pratyakhyan, Vandana + 1 human) | **MET** |
| 2 | source attribution 16–18, incl ≥6 unknown variants | **18** (6 approved + 12 anti-fabrication); **12** unknown-attribution; 24.3% share ≤ 40% cap | **MET** |
| 3 | canonical vs commentary 8–10, incl ≥3 contrast pairs | 9 rows; **4 source-disjoint contrast pairs** (5 approved-like sources vs 4 positive sources, 0 overlap) | **MET** |
| 4 | abstention 10–12 as pairs, ≥4 pairs, ≥4 phrasings | 12 rows; **4 intact answerable/unanswerable pairs**; **4 distinct refusal phrasings** ("The available material…", "The sources do not name…", "The structure of…", "The place of writing…") | **MET** |
| 5 | sect assertion: 8 (4 distinction + 4 discipline) | **8 = 4 `sect_contrast` + 4 `sect_unknown_discipline`** (contrast sources SVK-0037, SVK-1007 ×2, SVK-2009; non-frozen only) | **MET** |
| 6 | anti-fabrication 6–8 **pairs** (false claim → "not recorded") | **6 intact pairs = 12 rows**, each 1 `false_presupposition` + 1 plain, `evidence.method = manifest_absence`, real values borrowed from other eligible sources (nothing invented) | **MET** |
| 7 | multilingual 8–10 (hi/gu) + Prakrit | **9** (HINDI 5 + GUJARATI 4) + 1 PRAKRIT terminology row | **MET** |
| 8 | length discipline: median ≈350 chars cap | median **197** (mean 231, p75 255, max 671) | **MET** |
| 9 | wh breadth ≥10 varied questions | **12 distinct openers** (who 17, how 16, is 13, what 8, in 6, which/according/quote-led …) | **MET** |

Supporting counts: terminology-tagged rows 6 (STK 3 + general 2 + Prakrit 1,
target ≥4) · knowledge layers MIXED 27 / CANONICAL 19 / LEXICON 17 /
SECONDARY 6 / REFERENCE 5 · sect STHANAKAVASI 37 / UNKNOWN 35.

### §14 structural constraints

1. **SOURCE_OVERLAP = 0** — all frozen sources excluded; `frozen_sources_in_dataset = []`
   and no output question reaches Jaccard ≥ 0.80 against any frozen case.
   *Correction:* the frozen set contains **18** unique non-null
   `provenance.source_id` values (Task-66 §13 said "19" because that count
   included a null entry).
2. **Source-level split disjoint** — same protocol as SFT-01, kept (§7).
3. **No frozen-case content** — row gates re-verify verbatim grounding for every
   task67 row against non-frozen corpus units / manifest fields.
4. **Length discipline** applied cross-category (median 197 ≤ 350).
5. **Behaviour-based checkpoint metric pre-registered** in the config
   (`checkpoint_selection: behavioural`, frozen-benchmark behaviour, never
   eval_loss alone) — NOT run in this task.

## 5. Anti-template gate (Phase 5)

`experiments/sft_02/anti_template_gate.py`, run inside the builder *before* the
split is written and re-run by the validator/tests.

- **Result: level = WARN (not FAIL)** — 74 rows, **0 near-duplicate pairs**,
  0 exact duplicate answers, worst sentence template 5.4% (< 10% warn),
  worst 8-gram share 8.1% (< 10% warn), global "the manifest records" opener
  share **6.8%** (< 10% warn).
- **Single flag (accepted residual):**
  `[WARN] category CANONICAL_VS_COMMENTARY: opener 'the manifest records'
  share 55.6% > warn 40%` — the 5 rows are Task-63 **APPROVED** rows kept
  verbatim (approved content is immutable; trimming harder would push
  canonical below the 8-row floor). 55.6% < 60% FAIL threshold; category n = 9.
  Documented here as the sole accepted WARN.
- Severity-tagged flags (`[FAIL]` vs `[WARN]`); categories with n < 4 are
  exempt from opener concentration (MIN_CAT_N = 4).
- **STK-term note:** the STHANAKAVASI_TERMINOLOGY category has n = 3 < 4, so it
  is exempt from concentration checks rather than failing them; terminology as
  a whole (6 rows across 3 categories) meets the ≥4 target. Term rows are
  additionally capped to one row per (category, title, term) and walk a
  global question registry (q_ok, threshold 0.75).
- **Sanskrit target = 0 (data absence):** an IAST-character + Latin-term scan
  over every eligible non-frozen corpus unit found **zero** qualifying
  Sanskrit units; the target was set to 0 with this justification. Multilingual
  mass is carried by hi/gu/Prakrit rows.
- **Practice pool note:** rights-audit sources SVK-2030–2037 have **zero**
  corpus units, so pool practice rows for them cannot be grounded and are
  skipped; the practice target is met from corpus-grounded sources.

## 6. Deduplication and pair atomicity

- Exact + near-duplicate removal (shingle Jaccard ≥ 0.80) on **questions and
  answers**, with `pair_group` atomicity (dropping one member drops the pair)
  and approved rows winning ties.
- Drops: 2 approved near-dup canonical rows compressed at load
  (`svk-2003:…e02efb2e`, `svk-2004:…22a25da8`) + 1 new term row
  (`svk-2023:term:b012a1b4`, near_duplicate_question).
- **Dedup never broke a pair:** 4 abstention + 6 anti-fabrication pairs all
  intact and train-locked.

## 7. Split protocol (seed 42, deterministic)

- Source-level ordering `sha256(seed | source_id)`; **union-find** merges
  sources linked by a `pair_group`; **all 10 pair components are TRAIN-LOCKED**
  (eval abstention comes from approved rows — the SFT-01 9-row protocol
  mirrored); coverage fill picks the densest component for each required
  category, then smallest, then digest.
- **61 train / 13 eval** (target `max(12, 15%) = 12`, got 13);
  eval sources: SVK-0007, SVK-0027, SVK-1003, SVK-1008, SVK-1010, SVK-2009,
  SVK-2019, SVK-2021 (8 sources).
- Coverage required = 3 core categories (abstention, canonical,
  source attribution) — **all achieved, `coverage_missing = []`**.
  Multilingual/practice/terminology/distinction stay train-only because the
  frozen 47-case benchmark already probes languages and sect externally.
- **Source overlap train↔eval = []**; re-running `assign_split` on the output
  rows reproduces the partition exactly (validator check).

## 8. Training config (Phase 6 — not launched)

`configs/sft_qwen3_8b_sft02_v1.yaml` — the only two changes vs SFT-01 per
Task-66 §13:

| Knob | SFT-01 | SFT-02 |
|---|---|---|
| learning_rate | 1e-4 | **3e-5** |
| num_train_epochs | 3 | **2** |

Locked: QLoRA NF4 r16/α32/d0.05, batch 1 × grad-accum 8, seq 2048, fp16,
seed 42, cosine + warmup 0.03, **base `Qwen/Qwen3-8B-Base` + adapter lineage
`priyanshu471/dapt01-checkpoint-15248` (NOT SFT-01)**.
Checkpoint selection is pre-registered as **behavioural** over the frozen 47-case
benchmark (post-training step, never eval_loss alone). Kaggle section is
`status: not_created`.

## 9. Design decisions worth recording

1. **Origin objects are schema objects** — `{synthetic, method, confidence,
   builder}`; approved rows carry the task63 origin + an `sft02` selection
   marker; builder rows carry `origin.builder = task67_sft02:*`.
2. **Anti-fabrication = presupposition pairs** — a false claim built from a
   *real* value belonging to a *different* eligible source (no invented names)
   plus the plain question, both answered from mechanical absence checks
   (`manifest_absence`), correction phrased as not-recorded/not-identified.
3. **Approved attribution cap = 6** — s14 demands attribution 16–18 *and*
   anti-fabrication 6–8 pairs; since anti-fabrication rows are attribution
   rows: 6 approved + 12 anti-fab = 18 (top of range), 12 unknown variants.
4. **Human rows:** 5 HUMAN_VERIFIED ids exist, 3 are frozen-source excluded,
   **2 kept** (svk-2023 ×2); **0 rows newly upgraded** to HUMAN_VERIFIED.
5. **SVK-0026 excluded** from new rows as a third-party synthetic export
   (`SYNTHETIC_SOURCES`); approved rows unaffected.

## 10. Validation

- **Validator** `experiments/sft_02/validate_sft02_dataset.py` →
  **25 checks, 0 failed** (schema, ids, exact/near dups, provenance, rights,
  origin, split separation, deterministic split, pair integrity, eval coverage,
  frozen leakage, messages, answer quality, row gates + grounding re-run,
  gate re-run, §14 targets, abstention balance, attribution balance,
  anti-fabrication, style spread, stats consistency, frozen untouched, config
  consistency, read-only inputs).
- **Tests** `tests/test_sft02_dataset.py` → **27 tests, OK** (3.7 s).
- **Full suite:** `PYTHONPATH=src python3 -m unittest discover -s tests` →
  **462 ran, 0 failures**, 2 errors = pre-existing `faiss` import errors in
  `tests/test_retrieval.py`, 1 skip — baseline before this task was 435;
  all 27 new tests pass, no regressions.
- Builder itself refuses to write outputs unless row gates + grounding pass
  and the anti-template gate is not FAIL.

## 11. NOT_MEASURED / NOT_DETERMINED

- SFT-02 training run: **NOT_RUN** (by design).
- SFT-02 frozen-benchmark score / delta vs DAPT-01: **NOT_MEASURED**.
- Behavioural checkpoint selection: **NOT_RUN** (pre-registered only).
- Per-epoch behavioural trajectory (any arm): **NOT_MEASURED** (carried from Task-66).
- SFT-02 evaluator rubric metrics: **NOT_MEASURED**.
- Training VRAM / wall-clock for SFT-02: **NOT_MEASURED**.
- Significance of category deltas: **NOT_MEASURED** (no run).

---

```
TASK 67 COMPLETE
DELIVERABLES:
  data/training/sft_train_v2.jsonl                  61 train rows
  data/evaluation/sft_eval_v2.jsonl                 13 eval rows
  data/reports/task67_sft02_build_stats.json        build statistics (gate WARN, coverage OK)
  experiments/sft_02/sft02_common.py                shared helpers/constants
  experiments/sft_02/anti_template_gate.py          anti-template gate (PASS/WARN/FAIL)
  experiments/sft_02/build_sft02_dataset.py         deterministic builder (gates enforced)
  experiments/sft_02/validate_sft02_dataset.py      25-check validator
  tests/test_sft02_dataset.py                       27 tests
  configs/sft_qwen3_8b_sft02_v1.yaml                LR 3e-5, epochs 2, DAPT-01 lineage
  data/reports/task67_sft02_dataset.md              this report
  data/reports/task67_sft02_dataset.json            machine-readable report
VALIDATION: validator 25/25 PASS · tests 27/27 OK · suite 462 ran, 0 failures
            (2 pre-existing faiss errors, 1 skip) · gate WARN (1 documented residual)
            · SOURCE_OVERLAP 0 · frozen sha256 unchanged
NO TRAINING RUN · NO KAGGLE API CALL · NO LAUNCH
DAPT-01 (0.2660) REMAINS CURRENT BEST · SFT-01 (0.2305) UNPROMOTED
HARD STOP: YES
```

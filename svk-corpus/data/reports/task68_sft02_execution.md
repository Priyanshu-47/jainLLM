# Task 68 — SFT-02 Execution Report (Train + Frozen Evaluation + 4-Way Comparison)

**Date:** 2026-10-02
**Status:** COMPLETE — HARD STOP reached (no SFT-03 / DAPT-02 started)
**Headline:** SFT-02 trains and runs cleanly and clearly beats SFT-01, but does **not**
beat DAPT-01 on the frozen 47-case benchmark (0.2518 vs 0.2660). **SFT-02 NOT PROMOTED;
DAPT-01 remains the default arm.**

---

## 1. Phase 1 — Preflight (all PASS)

| Check | Result |
|---|---|
| `git pull --ff-only` / `git diff` | already up to date / empty (all task files untracked) |
| `data/training/sft_train_v2.jsonl` sha256 | `3a45925f7f3e3c8d7beaecff4b1a6ac14592dc12b9849c8b70c32bb328b5b7e5` (matches Task-67) |
| `data/evaluation/sft_eval_v2.jsonl` sha256 | `ba59533699b28328e4dc9e5fa3df1c24a0b026824bafc852cfc703f38e6fcc35` (matches Task-67) |
| `configs/sft_qwen3_8b_sft02_v1.yaml` | lr 3e-5, epochs 2, seq 2048, seed 42, batch 1×8, cosine, warmup 0.03, wd 0.01, fp16, NF4, r16/α32/d0.05/7 targets, continue_from `priyanshu471/dapt01-checkpoint-15248`, output `./outputs/sft-02` — all verified |
| `experiments/sft_02/validate_sft02_dataset.py` | 25/25 PASS (0 failed) — re-run this session |
| frozen `dapt01_eval_cases.jsonl` | sha256 `06625f72…65b81` unchanged |
| `python3 tools/train_sft_02.py` (new preflight tool) | **20/20 PASS** |

## 2. Phase 2 — Kaggle environment

- Kaggle CLI **2.2.4**, authenticated (credentials never printed or written to the repo).
- Local machine: no GPU, no torch — all GPU/library versions are recorded in-kernel instead.
- Note: CLI 2.2.4 has no `kaggle kernels run`; **`kaggle kernels push` also starts the run**.
- DAPT-01 checkpoint dataset verified present (11 files incl. `adapter_model.safetensors`).

## 3. Phase 3 — Training (Kaggle T4)

- Dataset `priyanshu471/jainllm-sft02-train` created (`train.jsonl`=61, `eval.jsonl`=13);
  **round-trip download re-verified both sha256 — PASS**.
- Kernel `priyanshu471/sft-02-qlora-on-dapt-01-lineage-task-68`
  (`experiments/sft_02/kaggle/{train.py,kernel-metadata.json}`), **status COMPLETE**.
- In-kernel guards all passed: data sha256 + row counts, adapter LoRA geometry
  (r16/α32/0.05/7 targets), LOCKED lr=3e-5/epochs=2, CUDA/VRAM check.
- **Training result:** 61 train / 13 eval rows, **16 global steps (2 epochs × 8)**,
  309 s total (135 s optimizer), eval_loss 3.0142 → 2.8714 (monotone down),
  train_loss mean 3.005 (start 2.911 / end 2.951 — low-LR regime, not loss-driven selection).
- Versions (in-kernel): python 3.12.13, torch 2.10.0+cu128, transformers 5.0.0,
  peft 0.19.1, bitsandbytes 0.50.2, accelerate 1.13.0, datasets 5.0.0, **GPU Tesla T4**.
- Final adapter uploaded to `priyanshu471/sft02-output`;
  `adapter_model.safetensors` sha256 = `2b22228940f81dc507d9815d919a31fe30bd4a9da1804a33f28b41b70766298d`;
  saved locally at `experiments/sft_02/checkpoints/sft-02-final/` (178 MB);
  checkpoints-8 and -16 downloaded. Report: `sft02_train_report.json`.

## 4. Phase 4 — Inference (blocker + resolution)

- **Blocker:** pushing the infer kernel from `priyanshu471` failed twice with
  `Maximum weekly GPU quota of 30.00 hours reached` (resets Saturday 00:00 UTC).
- **Resolution (user-directed):** a second Kaggle account token was provided in-session;
  introspected server-side as **`priyanshu47`** before any use. The token was used only
  via the `KAGGLE_API_TOKEN` environment variable for this session; **no credential
  value appears in any repo file, kernel, log, or artifact**.
- The training run itself had completed on `priyanshu471` before the quota was hit, so
  no training was repeated.
- Infer kernel pushed under the second account's namespace:
  `priyanshu47/sft-02-infer-task68` (`experiments/sft_02/kaggle_infer/`), **COMPLETE**.
  Attached (public) datasets: `priyanshu471/sft02-output`, `priyanshu471/jainllm-sft02-train`.
- **In-kernel hash assertions all passed before generation:** adapter sha
  `2b222289…298d`, frozen cases sha `06625f72…65b81` (47 packed cases re-verified),
  eval sha `ba595336…cc35`, row counts 47/13.
- Protocol parity with Tasks 60/65 confirmed from metadata: Qwen/Qwen3-8B-Base,
  4-bit NF4 double/fp16, greedy (`do_sample=False`), `max_new_tokens=192`, seed 42,
  chat_template prompt, Tesla T4, transformers 5.0.0, torch 2.10.0+cu128
  (**env parity across task60/65/68 = True**).
- Timing: model load 117.7 s, frozen 47-case infer 911.6 s, held-out 13-row infer 349.7 s.
- Outputs: `dapt01_sft02_results.jsonl` (47), `sft02_eval_results.jsonl` (13),
  `task68_sft02_infer_metadata.json` — row counts and hashes verified.

## 5. Phase 5 — 4-way scoring (frozen 47-case benchmark)

Scorer `experiments/sft_02/evaluation/score_task68_4way.py` imports `score_task60`
and applies `norm/group_pass/score_case` **verbatim** to all four arms →
`data/evaluation/sft02_4way_comparison.json`.

| Arm | macro score | pass-all (score=1) |
|---|---|---|
| BASE | 0.2021 | 6 |
| DAPT-01 | **0.2660** | 8 |
| SFT-01 | 0.2305 | 7 |
| **SFT-02** | **0.2518** | **8** |

- SFT-02 − DAPT-01 = **−0.0142**; SFT-02 − SFT-01 = **+0.0213**; SFT-02 − BASE = +0.0497.
- vs DAPT-01: **1 improved** (023 SANSKRIT) / **2 regressed**
  (034 SOURCE_ATTRIBUTION: sft02 hedges and misses "Stevenson" → 0.5→0;
  040 PRACTICE: sft02 says "at least 15 minutes" instead of 48 → 1.0→0.5).
- vs SFT-01: 4 improved (008, 016, 023, 043) / 2 regressed (034, 036).
- Abstention (4 cases): base 0, dapt 0, sft01 1, **sft02 0** — SFT-02 fabricates on all
  four (e.g. 036 "published in 1918", 037 "founded in 1699", 039 "24 Agams" = the exact
  forbidden claim). Same as DAPT-01 (0), one below SFT-01 (1).
- Category deltas vs DAPT-01: SANSKRIT +0.111, PRACTICE −0.125, SOURCE_ATTRIBUTION −0.125,
  all other categories equal (incl. base-wide failures GUJARATI/JAIN_TERMINOLOGY = 0 for
  **every** arm).

### Behaviour detectors (uniform across all 4 arms; documented in the scorer)

| metric | base | dapt | sft01 | sft02 |
|---|---|---|---|---|
| looped cases (detector, frozen set) | 0 | 1 | **31** | **5** |
| INFRINGEMENT-token outputs | 0 | 0 | **24** | **0** |
| answer len median (chars) | 199 | 330 | **851** | **255** |
| generations at 192-token cap | 12 | 17 | **45** | **17** |

Note: Task-66's 0/2/28 loop counts came from an unpreserved detector and are not
numerically comparable to these; all four arms here use the one documented detector.

### Held-out (13 rows, `sft02_eval_results.jsonl` → `sft02_heldout_analysis.json`)

- median answer 523 chars vs reference 197 (ratio 2.33); **6/13 looped**, 10/13 hit the
  192-token cap, 0 INFRINGEMENT, 0 verbatim-train openers, openers 13/13 distinct.
- **Abstention row failed mechanically**: no abstention marker, answer degenerated into
  echoing the question + "1911" ×17.
- Severe loops include question-echo + `0`×78 and question-echo + `ड`×N (Hindi).
- For pattern context only (rows differ, NOT row-comparable): SFT-01's v1 held-out had
  median 1017, 7/9 looped, 4 INFRINGEMENT → SFT-02 is better but still unstable
  outside the system-prompted frozen format.
- Hindi `reference_coverage=0.0` values are an ASCII-tokeniser artefact of the
  diagnostic (flagged, not evidence of wrongness).

## 6. Phase 6 — Failure-pattern comparison vs SFT-01 (Task-66 taxonomy)

| Task-66 finding for SFT-01 | Status in SFT-02 (evidence) |
|---|---|
| D. generation instability, DOMINANT (28/47 looped; 24/47 INFRINGEMENT; 45/47 at cap) | **Largely fixed on the frozen set**: 5/47 looped (verified genuine), 0 INFRINGEMENT, 17/47 at cap (= DAPT level). **Not fixed on held-out**: 6/13 looped incl. echo-loops, 10/13 at cap. |
| B. behavioural overfitting / template rigidity; answer median 851; held-out fabrications | **Mostly fixed on frozen set** (median 255, no verbatim-train openers), **partially open on held-out** (median 523 vs ref 197; abstention row degenerated). |
| Abstention behaviour: SFT-01 gained 1/4 abstention correct | **Regressed to 0/4** (= BASE/DAPT): all four frozen abstention answers assert fabricated specifics. The 12 anti-fab/abstention training pairs did not transfer. |
| C. memorisation | NOT_DETERMINED (no probe; loss alone proves nothing — pre-declared). |
| SOURCE_OVERLAP (SFT-01 dataset had 1) | Fixed by construction: Task-67 validator = 0 overlaps (already verified in Task 67). |

What changed vs SFT-01: LR 1e-4→3e-5, epochs 3→2, dataset v1(50/9)→v2(61/13) with
abstention/anti-fab pairs, capped attribution, diversified refusals, source-disjoint eval.
Loss trajectory differed accordingly (SFT-01: 4.47→1.55, heavy fit; SFT-02: ~3.0 flat,
eval 3.01→2.87) — per the pre-declaration, loss is **not** used as a success criterion.

## 7. Phase 7 — Promotion decision

**SFT-02 PROMOTED: NO. DAPT-01 remains the default/best arm.**

Pre-declared rule: *DAPT-01 stays default unless SFT-02 shows meaningful improvement
without unacceptable regressions; mixed benchmark → keep DAPT-01.*

Evidence:
1. Factual grounding (the promotion metric): **0.2518 < 0.2660** — no improvement.
2. Case flips vs DAPT-01 are net negative (1 improved / 2 regressed), including a
   factual error (48→15 minutes) and a hedged-out author name.
3. Pass-all ties DAPT-01 (8) but abstention stays 0/4 with fresh fabrications
   (1918/1699/24 Agams) — an *unacceptable regression* risk for a corpus-grounded assistant
   is realised on the held-out abstention row as well (degenerate echo, no refusal).
4. Generation stability vs SFT-01 improved hugely but is still not clean (5/47 frozen,
   6/13 held-out loops).

SFT-02 **is** clearly preferred over SFT-01 (+0.0213, stability restored), i.e. the
Task-66 corrections moved in the right direction, but the incumbent bar (DAPT-01) is
not cleared.

**NOT_MEASURED (never synthesised):** evaluator-based factual_error / unsupported_claims /
sect_confusion / evaluator degenerate_loop for the SFT arms (review file covers base/dapt
only); fluency/grammar; human preference; held-out accuracy (no rubric); BASE/DAPT arms on
`sft_eval_v2` rows (not in protocol — cross-arm attribution uses the frozen set only).

## 8. Deliverables

- `data/evaluation/sft02_4way_comparison.json` — 4-way score, all arms, per-case.
- `data/evaluation/sft02_heldout_analysis.json` — 13-row mechanical analysis.
- `data/evaluation/dapt01_sft02_results.jsonl`, `data/evaluation/sft02_eval_results.jsonl`.
- `data/reports/task68_sft02_metrics.json`, `data/reports/task68_sft02_manifest.json`.
- Code: `tools/train_sft_02.py`, `experiments/sft_02/kaggle/*`,
  `experiments/sft_02/kaggle_infer/*`, `experiments/sft_02/evaluation/*`.
- Logs: `data/reports/task68_sft02_{train_status.json,worker.log,kaggle_run.log,infer.log,infer_metadata.json}`.

## 9. HARD STOP

```
HARD STOP: YES
SFT-02 PROMOTED = NO
DAPT-01 (priyanshu471/dapt01-checkpoint-15248) REMAINS THE DEFAULT ARM
NO SFT-03, NO DAPT-02, NO AUTOMATIC RE-RUN WERE STARTED
```

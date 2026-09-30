# TASK 60 — DAPT-01 BASE vs ADAPTED EVALUATION

Date: 2026-09-29 · repo `svk-corpus` · branch `main` · experiment `dapt_01` (DAPT step 1, `qwen3_8b_base_dapt_01`)
Scope: **evaluation only**. No training, no adapter merge, no dataset/corpus modification, no DAPT-02, no SFT, no invented questions, no single subjective overall score.

---

## 1. Result in brief (category-level; no overall winner declared)

| Category | n | BASE keyterm | BASE+DAPT-01 keyterm | Δ | BASE pass-all | DAPT pass-all |
|---|---:|---:|---:|---:|---:|---:|
| ABSTENTION | 4 | 0.0000 | 0.0000 | +0.0000 | 0 | 0 |
| AGAM_GROUNDED | 4 | 0.2500 | 0.0833 | **−0.1667** | 0 | 0 |
| GUJARATI | 4 | 0.0000 | 0.0000 | +0.0000 | 0 | 0 |
| HINDI | 4 | 0.1667 | 0.2500 | **+0.0833** | 0 | 0 |
| JAIN_TERMINOLOGY | 4 | 0.0000 | 0.0000 | +0.0000 | 0 | 0 |
| MULTILINGUAL_MAPPING | 4 | 0.5000 | 0.5000 | +0.0000 | 2 | 2 |
| PRACTICE | 4 | 0.3750 | 0.6250 | **+0.2500** | 0 | 1 |
| PRAKRIT | 4 | 0.0000 | 0.3750 | **+0.3750** | 0 | 1 |
| SANSKRIT | **3** | 0.1111 | 0.2222 | **+0.1111** | 0 | 0 |
| SOURCE_ATTRIBUTION | 4 | 0.0000 | 0.1250 | **+0.1250** | 0 | 0 |
| STHANAKAVASI_DISTINCTION | 4 | 1.0000 | 0.7500 | **−0.2500** | 4 | 3 |
| STHANAKAVASI_TERMINOLOGY | 4 | 0.0000 | 0.2500 | **+0.2500** | 0 | 1 |

keyterm = objective keyterm-coverage score (§4), mean per category. `pass-all` = cases where every condition group matched. **SANSKRIT has 3 cases, not 4** (§3, §11).

Evaluator-based signals (labelled `evaluator_based`, rubric §4, full per-case data in `dapt01_comparison.json`):

| Signal (all 47 cases ×2 arms) | BASE | BASE+DAPT-01 |
|---|---:|---:|
| factual_error (claims contradicting reference) | 41 | **47** |
| unsupported source-attributed claims | 6 | **20** |
| sect_confusion cases (Sthanakavasi/Svetambara/Digambara) | 1 | **4** |
| degenerate_loop cases (repetition / prompt echo) | 1 | **8** |
| abstention correct (of 4) | 0 | **0** |

**Measured conclusion (category-level only):** the adapter raises keyterm coverage in 7 categories (largest: PRAKRIT +0.375, PRACTICE +0.25, STHANAKAVASI_TERMINOLOGY +0.25, SANSKRIT +0.111, SOURCE_ATTRIBUTION +0.125, HINDI +0.083), leaves 3 categories unchanged, and lowers 2 categories (AGAM_GROUNDED −0.167, STHANAKAVASI_DISTINCTION −0.25). Every evaluator-based error channel is **worse** with the adapter (factual errors, unsupported claims, sect confusion, degenerate loops), and abstention is equally bad in both arms (0/4). No statement of the form "DAPT-01 is better overall" is made, and no single overall score is used to declare a winner.

---

## 2. Experimental design and controls

| Item | Value |
|---|---|
| Base model | `Qwen/Qwen3-8B-Base` |
| Adapter | `priyanshu47/dapt01-checkpoint-15248` (Kaggle dataset, attached read-only at `/kaggle/input/datasets/priyanshu47/dapt01-checkpoint-15248`) |
| Adapter handling | `PeftModel.from_pretrained(..., is_trainable=False)`; `adapter_merged = false`; no weights written |
| Quantisation (both arms) | 4-bit NF4, double-quant, compute dtype fp16 — identical to training `LOCKED["quant"]="4bit-nf4-double"` (`experiments/dapt_01/kaggle/train.py:419-427`) |
| System prompt (both arms) | "You are a careful assistant for Jain studies. Answer the user's question concisely (in 1-3 sentences). If you are unsure or the information is not available, say so." |
| Prompt style | Qwen chat template (verified `has chat_template: True`, `prompt_style = chat_template` for all 94 rows) |
| Decoding | greedy (`do_sample=False`), `max_new_tokens=192`, seed 42 |
| Execution order | arm 1 = base, then attach adapter, arm 2 = base+adapter — single model load, identical prompts |
| Hardware | Kaggle Tesla T4 |
| Environment | python 3.12.13, torch 2.10.0+cu128, transformers 5.0.0, peft 0.19.1, bitsandbytes 0.50.2 (pip-installed at runtime: `[deps] pip install ['bitsandbytes']`, `pip ok attempt=1`) |

Runtime (kernel log `data/evaluation/task60-dapt01-base-vs-dapt-evaluation.log`, session 2026-09-29):

| Phase | Measured |
|---|---|
| model load (incl. HF download) | 119.7 s (14:22:43 → 14:24:42) |
| ARM 1 BASE, 47 cases | 449.0 s (14:24:42 → 14:32:11) |
| adapter attach | 3.1 s (14:32:11 → 14:32:14) |
| ARM 2 BASE+DAPT-01, 47 cases | 993.3 s (14:32:14 → 14:48:48) |
| in-kernel total | 1565.1 s ≈ **26.1 min** |
| session wall clock | ≈ **27 min** (14:22:41 → 14:48:48) |
| this task's total GPU | ≈ **31 min** (successful run 27 min + two aborted attempts ≈ 3.5 min for adapter-path and bitsandbytes fixes) |

Not done (and not needed): training, resume, merge, LoRA re-quantisation, corpus/dataset writes, SFT evaluation, loss comparison.

---

## 3. Case set — 47 cases (48 requested; SANSKRIT shortfall documented)

`data/evaluation/dapt01_eval_cases.jsonl`, built by `experiments/dapt_01/evaluation/build_dapt01_eval_cases.py`, which asserts for every case: provenance unit ids exist in `data/release/training_corpus.jsonl`, every `source_contains` string is present in that unit, manifest fields match `manifests/source_manifest.csv`, abstention absences hold, and `dapt_split` tags match `data/domain_train/{train,val,test}.jsonl`.

- **47 cases** with `example_id` `DAPT01EVAL-001` … `DAPT01EVAL-047` (own ids; they are *not* registered JainBench-v0 ids — the JainBench schema currently contains 0 questions, below its own `minItems: 150`).
- Categories (12/12 present): ABSTENTION 4, AGAM_GROUNDED 4, GUJARATI 4, HINDI 4, JAIN_TERMINOLOGY 4, MULTILINGUAL_MAPPING 4, PRACTICE 4, PRAKRIT 4, **SANSKRIT 3**, SOURCE_ATTRIBUTION 4, STHANAKAVASI_DISTINCTION 4, STHANAKAVASI_TERMINOLOGY 4.
- Languages: `en` 34, `hi` 8, `gu` 5, `sa` 0 (see §11).
- DAPT split tags: train 37, val 3, test 7 — enabling seen-vs-unseen analysis (§9).
- Abstention cases: 4, each justified by an absence verified in the builder (no publication year for *Sthanakvasi Jain Itihas*; Terapanth only "about 150 years ago"; publisher field `unknown` for *Notes on Modern Jainism*; no Digambara Agam count in the governed corpus).
- SFT gold/seed material is excluded (SFT-reserved, `HUMAN_REVIEW_REQUIRED`).

---

## 4. Metric definitions (fixed before scoring, applied identically to both arms)

1. **keyterm coverage (objective).** Each case carries pre-authored `scoring` groups; a group passes iff every `all_of` substring is present, no `none_of` substring is present, and at least one `any_of` substring is present (case-insensitive substring match on whitespace-normalised text). `keyterm score = groups passed / groups`. Abstention cases: `abstention_correct = (≥1 abstention marker present) AND (no forbidden_claims regex matches)`; their score is 1/0. Rules were authored from the corpus/manifest reference text *before* inference and are byte-identical for both arms (`dapt01_eval_cases.jsonl`, field `scoring`).
2. **abstention correctness (objective).** Per §4.1 with per-case `abstention_markers` + `forbidden_claims` (e.g. `\b(18|19|20)\d{2}\b` for the year question).
3. **evaluator-based judgements (labelled `evaluator_based`).** Agent evaluator pass over all 47×2 answers, rubric v1, recorded in `data/evaluation/dapt01_evaluator_review.jsonl`:
   - `factual_error` — count of claims that **contradict** the corpus/manifest-verified reference (wrong author, year, count, term, sect position);
   - `unsupported_claims` — count of source-attributed claims ("according to Stevenson / the corpus / the manifest") whose content is not in the reference;
   - `sect_confusion` — misstates the Sthanakavasi/Svetambara/Digambara relationship vs reference;
   - `degenerate_loop` — repeats a sentence ≥2 times or echoes prompt/user text.
   These are never synthesised by the scorer (`experiments/dapt_01/evaluation/score_task60.py`).

No fluency/grammar score, no pairwise human preference, no verbatim-copy metric — recorded as NOT_MEASURED (§11).

---

## 5. Category results (objective keyterm)

Same table as §1; see `dapt01_comparison.json → category_table` for the machine-readable form, plus `evaluator_category_table` for per-category factual-error/unsupported counts.

Macro-average of per-case keyterm scores (objective, explicitly **not** authoritative and not used to declare a winner): BASE 0.2021 → BASE+DAPT-01 0.2660; pass-all 6/47 → 8/47. Category-level results in §1 are the reported result.

---

## 6. Abstention (4 cases) — both arms fail all four

| case | question | BASE | BASE+DAPT-01 |
|---|---|---|---|
| DAPT01EVAL-036 | publication year of *Sthanakvasi Jain Itihas* | "was published in **1970**" | "was published in **1914**…" |
| DAPT01EVAL-037 | exact year Terapanth founded | "founded in the year **1916**" | "founded in **1669**… Bhagwanlal IndrajI, who was born in 1669…" |
| DAPT01EVAL-038 | who published *Notes on Modern Jainism* (1910) | "published by the **Jain Society of Bombay**" | "published by the **Oxford University Press**. It was written by **Lewis Rice**…" |
| DAPT01EVAL-039 | how many Agams Digambara accept | "accepts **12** Agams" | "accepts **24** Agams… Svetambara … **25**" |

`abstention_correct`: BASE 0/4, BASE+DAPT-01 0/4. The system prompt explicitly instructs "If you are unsure or the information is not available, say so", and neither arm obeyed it. Raw answers in `dapt01_comparison.json → abstention.per_case`.

---

## 7. Evaluator-based totals (label: `evaluator_based`, rubric §4.3, coverage 47/47)

| Signal | BASE | BASE+DAPT-01 | Δ |
|---|---:|---:|---:|
| factual_error (sum of counts) | 41 | 47 | +6 |
| unsupported source-attributed claims | 6 | 20 | +14 |
| sect_confusion cases | 1 (028) | 4 (028, 029, 030, 031) | +3 |
| degenerate_loop cases | 1 (011) | 8 (008, 009, 010, 018, 019, 024, 032, 045) | +7 |

Per-category evaluator counts: `dapt01_comparison.json → evaluator_category_table`. Examples of adapted-arm regressions in this channel: DAPT01EVAL-031 answers "Yes" where the reference says the Sthanakavasi retain their old name; DAPT01EVAL-030 fabricates "the Svetambara Canon was created by the Sthanakavasi community in the 15th century"; DAPT01EVAL-035 names "Dr. J. L. Jaini" as Editor-in-Chief (reference: Shri Amar Muni).

---

## 8. Improvements and regressions (objective keyterm deltas)

- **Improved (8):** 008 STHANAKAVASI_TERMINOLOGY (+1.000), 009 PRAKRIT (+1.000), 011 PRAKRIT (+0.500), 034 SOURCE_ATTRIBUTION (+0.500), 040 PRACTICE (+0.500), 043 PRACTICE (+0.500), 015 HINDI (+0.333), 023 SANSKRIT (+0.333).
- **Regressed (2):** 030 STHANAKAVASI_DISTINCTION (1.000 → 0.000), 026 AGAM_GROUNDED (0.667 → 0.000).
- **Unchanged (37):** all other cases.

---

## 9. Seen vs unseen (DAPT split tags)

| DAPT split | n | BASE keyterm | BASE+DAPT-01 keyterm | Δ |
|---|---:|---:|---:|---:|
| train (source seen during DAPT) | 37 | 0.2162 | 0.3018 | **+0.0856** |
| val | 3 | 0.1667 | 0.3333 | **+0.1666** |
| test (source held out) | 7 | 0.1429 | 0.0476 | **−0.0953** |

By language (keyterm): `en` 34 cases 0.2304 → 0.2647 (+0.0343); `hi` 8 cases 0.2083 → 0.4375 (+0.2292); `gu` 5 cases 0.0000 → 0.0000 (+0.0000).

Measured reading: gains concentrate on material whose sources were seen during DAPT (train/val) and on Hindi term-level questions; the 7 test-split cases get worse. This is reported as an observed split-level result, not as a generalisation claim (n is small).

---

## 10. Regression checks requested by the task

| Check | Measured outcome |
|---|---|
| Terminology vs reasoning | Gains are term/wording-level: PRAKRIT +0.375, STHANAKAVASI_TERMINOLOGY +0.25, SOURCE_ATTRIBUTION +0.125. Reasoning/position categories move the other way: STHANAKAVASI_DISTINCTION −0.25, AGAM_GROUNDED −0.167. |
| Hallucinated / unsupported claims | factual_error 41 → 47; unsupported source-attributed claims 6 → 20 (both evaluator-based). |
| Sthanakavasi / Svetambara / Digambara blending | sect_confusion cases 1 → 4 (BASE: 028; DAPT: 028, 029, 030, 031). |
| Corpus-wording overfit / degeneration | degenerate_loop cases 1 → 8 (DAPT: 008, 009, 010, 018, 019, 024, 032, 045) — sentence repetition and prompt/`user` echo. A verbatim corpus-copy metric at scale was NOT computed. |
| Multilingual change | `hi` +0.229, `en` +0.034, `gu` 0.000 (keyterm). Gujarati answers remain in-language but factually wrong in both arms. |
| Abstention behaviour | unchanged and bad: 0/4 both arms (§6). |

---

## 11. Limitations and coverage

- **SANSKRIT = 3 cases, not 4.** `data/release/training_corpus.jsonl` contains **0** units with `language == "sa"` (lang counts: en 34,357 / unknown 30,895 / gu 14,453 / hi 9,036 / pra 9,022 / sa 0). The 3 cases use manifest provenance for Sanskrit works (`SVK-2015`, `language=san`, *Sri Avasyaka Sutra Part-i (1928)*) and Sanskrit terms attested in English sources. Reported as a corpus coverage limitation, not silently filled with invented material.
- **Gujarati = 0.000 in both arms** despite in-language output: the reference facts are present, but OCR noise (`અહિ'સા`, `ગ્ર'થો`, broken glyphs in `SVK-2012`/`SVK-2024`/`SVK-2027`) and exact-substring matching make the score brittle. Scores are valid as defined but should not be read as "Gujarati understanding is zero".
- **Substring rules are strict.** Example: DAPT01EVAL-001 reference is "non-injury"; both arms answered "non-violence/non-harm" and scored 0 despite being semantically right. Rules were fixed before inference and applied identically to both arms, so the *comparison* is fair, but *absolute* levels are depressed. Rule text is auditable in `dapt01_eval_cases.jsonl`.
- **n = 47, one seed, greedy decoding.** No statistical significance testing; deltas of ±0.125 on a 4-case category are within noise.
- **Arm 2 measured 2.2× slower than arm 1** (993.3 s vs 449.0 s) on the same hardware/prompt length; reported as measured, not explained.
- **NOT_MEASURED:** SANSKRIT 4th case; fluency/grammar score; corpus-wording overlap/verbatim-copy metric; pairwise human preference; any DAPT-02 or SFT comparison; training-loss comparison (explicitly out of scope).

---

## 12. Artifacts

| File | Content |
|---|---|
| `data/evaluation/dapt01_eval_cases.jsonl` | 47 cases, pre-authored scoring rules, provenance, split tags |
| `data/evaluation/dapt01_base_results.jsonl` | 47 base answers (T4, 4-bit, greedy, seed 42) |
| `data/evaluation/dapt01_dapt_results.jsonl` | 47 base+adapter answers (same decode settings) |
| `data/evaluation/dapt01_comparison.json` | category/split/language tables, per-case scores + answers, abstention detail, evaluator-based counts, NOT_MEASURED |
| `data/evaluation/dapt01_evaluator_review.jsonl` | evaluator-based judgements (rubric v1) for 47×2 answers |
| `data/evaluation/task60_run_metadata.json` | model/adapter/env/timing metadata |
| `data/evaluation/task60-dapt01-base-vs-dapt-evaluation.log` | full kernel log |
| `data/reports/task60_dapt01_evaluation.md` | this report |
| `experiments/dapt_01/evaluation/{build_dapt01_eval_cases.py,score_task60.py,build_task60_kernel.py}` | reproducible builder/scorer |
| `experiments/dapt_01/evaluation/kaggle/{task60_infer_kaggle.py,kernel-metadata.json}` | inference kernel (`priyanshu47/task60-dapt01-base-vs-dapt-evaluation`, v3) |

---

## 13. RECOMMENDED_NEXT_STEP (not executed)

Do **not** treat DAPT-01 as an improvement based on this run alone: keyterm gains on seen material are offset by more factual errors, more unsupported source-attributed claims, more sect confusion and more degenerate loops, with zero abstention compliance. Recommended next step for a later task: re-run the same 47 cases after (a) an abstention/instruction-tuning stage (SFT with abstention-positive examples) and (b) a second DAPT round on non-overlapping sources, keeping this exact case set and decode settings as the frozen baseline for a controlled three-way comparison (BASE / +DAPT-01 / +DAPT-01+SFT).

---

HARD STOP — TASK 60 evaluation artifacts are complete; no further task is executed in this step.

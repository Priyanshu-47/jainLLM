# TASK 66 — SFT-01 Failure Analysis + SFT-02 Design (Analysis Only)

**Status: COMPLETE — analysis only.**
Generated: 2026-10-01 14:00:49

## 0. Scope declaration (hard stop)

- **No training was run. No Kaggle API call. No SFT-02 data created. No benchmark/DAPT modification.**
- Frozen benchmark (47 cases, sha256 `06625f72190e3ae130447345afdc04342bd19cb76f842285706480cba7765b81`) **unchanged**.
- **DAPT-01 (0.2660 macro) remains the current best; SFT-01 (0.2305) is NOT promoted.**
- Machine-readable twin: `data/reports/task66_sft01_failure_analysis.json`.

## 1. Repository state & artifact confirmation (Phase 1)

| Artifact | Path | Status |
|---|---|---|
| Frozen eval cases (47) | `data/evaluation/dapt01_eval_cases.jsonl` | confirmed, hash verified |
| BASE results | `data/evaluation/dapt01_base_results.jsonl` | confirmed |
| DAPT-01 results | `data/evaluation/dapt01_dapt_results.jsonl` | confirmed |
| SFT-01 results | `data/evaluation/dapt01_sft_results.jsonl` | confirmed |
| Three-way comparison | `data/evaluation/sft01_3way_comparison.json` | confirmed (spec listed `data/reports/…` — **actual path is `data/evaluation/`**; documented here as the correction) |
| SFT train set (50) | `data/training/sft_train_v1.jsonl` | confirmed (sha256 prefix `77bd61ff`) |
| SFT eval set (9) | `data/evaluation/sft_eval_v1.jsonl` | confirmed (`4ef9d814`) |
| Held-out generations (9) | `data/evaluation/sft01_eval_results.jsonl` | confirmed |
| Task-65 execution report | `data/reports/task65_sft01_execution.md` | confirmed (final block present) |
| SFT-01 final adapter | `experiments/sft_01/checkpoints/sft-01-final/` | local copy, sha256 `65ad9595…81f8` = checkpoint-21 |

Prior state: Task 65 completed with `TRAINING STARTED: YES, SFT-01 COMPLETE: YES, NEXT TRAINING RUN STARTED: NO, HARD STOP: YES`. `git pull --ff-only` → already up to date; `git diff` clean (all SFT/task-64/65 files untracked).

## 2. Method

All numbers below are **measured from the named files** (reproducible via the commands recorded in §17). Heuristics used:

- **Loop detection**: (a) any sentence >15 chars repeated ≥2×; (b) any whitespace-token repeated ≥3× consecutively; (c) any CJK run ≥4 chars. `INFRINGEMENT` counted separately (substring presence).
- **Refusal-like phrases**: fixed substring list (checked per case; false positives manually adjudicated, e.g. case 028's “not available in this corpus” is a content detail, **not** a refusal).
- Unmeasurable items are marked `NOT_MEASURED` / `NOT_DETERMINED` (§16) — never estimated.

## 3. Headline result

| arm | macro (of 47) | pass-all (≥0.5) | abstention score | loops | INFRINGEMENT outputs | median answer len |
|---|---|---|---|---|---|---|
| BASE | 0.2021 | 6 | 0 | 0 | 0 | 199 |
| DAPT-01 | **0.2660** | 8 | 0 | 2 | 0 | 330 |
| SFT-01 | 0.2305 | 7 | 1 | **28** | **24** | **851** |

- sft − dapt = **−0.0355**; sft − base = +0.0284 (SFT-01 helps vs BASE, hurts vs DAPT-01).
- Per-case vs DAPT-01: **improved 1** (036, abstention 0→1), **regressed 5** (008, 016, 023, 040, 043), unchanged 41.

## 4. Failure-flag summary across arms

| signal | BASE | DAPT-01 | SFT-01 |
|---|---|---|---|
| looped outputs (47) | 0 | 2 (008, 024) | **28** |
| `INFRINGEMENT` token runs | 0 | 0 | **24** |
| starts “According to …” | 14 | 5 | 12 |
| “in this corpus” | 0 | 2 | 4 |
| mean answer length | 207 | 368 | 754 |

Key measured facts driving the diagnosis:

1. `INFRINGEMENT` **appears in zero training rows, zero eval rows, zero frozen cases, and the corpus** — the failure mode is induced by the adapter's weight change, not learned text (exact mechanism `NOT_DETERMINED` — no GPU in this task for logit probing).
2. Training data is **100% English-script**; frozen set contains 8 hi + 5 gu cases — those received zero SFT exposure.
3. Answer length nearly **doubles vs DAPT-01** (median 330→851) with loops concentrated at output tails.

## 5. Full 47-case benchmark matrix (Phase 2)

Scores are keyterm-group fractions in {base} / {dapt} / {sft}. `Δ` = sft − dapt. `overlap` = `SOURCE_OVERLAP` (train shares the case's source). `sft loop` = repetition-loop flag on the SFT answer. `likely failure type` combines heuristic flags with manually adjudicated labels (see §6 deep-dives).

| case | cat | lang | src | overlap | exp B/D/S | Δ D→S | verdict | sft loop | likely failure type |
|---|---|---|---|---|---|---|---|---|---|
| 001 | JAIN_TERMINOLOGY | en | SVK-1005 | ✓ | 0.00/0.00/0.00 | 0.00 | unchanged | — | all_arms_fail |
| 002 | JAIN_TERMINOLOGY | en | SVK-0038 | — | 0.00/0.00/0.00 | 0.00 | unchanged | — | all_arms_fail |
| 003 | JAIN_TERMINOLOGY | en | SVK-0038 | — | 0.00/0.00/0.00 | 0.00 | unchanged | word_run:INFRINGEMENTx12 | all_arms_fail; repetition_loop (score-insensitive trailing) |
| 004 | JAIN_TERMINOLOGY | en | SVK-0038 | — | 0.00/0.00/0.00 | 0.00 | unchanged | word_run:INFRINGEMENTx42 | all_arms_fail; repetition_loop (score-insensitive trailing) |
| 005 | STHANAKAVASI_TERMINOLO | en | SVK-0038 | — | 0.00/0.00/0.00 | 0.00 | unchanged | word_run:INFRINGEMENTx69 | all_arms_fail; repetition_loop (score-insensitive trailing) |
| 006 | STHANAKAVASI_TERMINOLO | en | SVK-0038 | — | 0.00/0.00/0.00 | 0.00 | unchanged | sentence_repeat | all_arms_fail; repetition_loop (score-insensitive trailing) |
| 007 | STHANAKAVASI_TERMINOLO | en | SVK-0038 | — | 0.00/0.00/0.00 | 0.00 | unchanged | word_run:INFRINGEMENTx41 | all_arms_fail; repetition_loop (score-insensitive trailing) |
| 008 | STHANAKAVASI_TERMINOLO | en | SVK-0038 | — | 0.00/1.00/0.00 | -1.00 | regressed | sentence_repeat | hallucinated_content + repetition_loop (DAPT also looped; SFT replaced correct 'Sthanakavasi scriptures' with  |
| 009 | PRAKRIT | hi | SVK-2006 | ✓ | 0.00/1.00/1.00 | 0.00 | unchanged | — | none_observed |
| 010 | PRAKRIT | hi | SVK-2007 | — | 0.00/0.00/0.00 | 0.00 | unchanged | — | all_arms_fail |
| 011 | PRAKRIT | hi | SVK-2006 | ✓ | 0.00/0.50/0.50 | 0.00 | unchanged | — | none_observed |
| 012 | PRAKRIT | en | SVK-2008 | — | 0.00/0.00/0.00 | 0.00 | unchanged | word_run:INFRINGEMENTx48 | all_arms_fail; repetition_loop (score-insensitive trailing) |
| 013 | HINDI | hi | SVK-2020 | ✓ | 0.00/0.00/0.00 | 0.00 | unchanged | — | all_arms_fail |
| 014 | HINDI | hi | SVK-2020 | ✓ | 0.00/0.00/0.00 | 0.00 | unchanged | — | all_arms_fail |
| 015 | HINDI | hi | SVK-2020 | ✓ | 0.00/0.33/0.33 | 0.00 | unchanged | — | none_observed |
| 016 | HINDI | hi | SVK-2020 | ✓ | 0.67/0.67/0.33 | -0.33 | regressed | word_run:INFRINGEMENTx3 | contentless_meta_answer (Hindi answer describes that a definition exists without giving it) + minor INFRINGEME |
| 017 | GUJARATI | gu | SVK-2027 | ✓ | 0.00/0.00/0.00 | 0.00 | unchanged | — | all_arms_fail |
| 018 | GUJARATI | gu | SVK-2014 | — | 0.00/0.00/0.00 | 0.00 | unchanged | — | all_arms_fail |
| 019 | GUJARATI | gu | SVK-2010 | — | 0.00/0.00/0.00 | 0.00 | unchanged | — | all_arms_fail |
| 020 | GUJARATI | gu | SVK-2012 | ✓ | 0.00/0.00/0.00 | 0.00 | unchanged | — | all_arms_fail |
| 021 | SANSKRIT | en | SVK-2015 | — | 0.00/0.00/0.00 | 0.00 | unchanged | word_run:INFRINGEMENTx65 | fabricated_author ('Dr. P. S. Jaini') + hedge tail + repetition_loop (all arms score 0) |
| 022 | SANSKRIT | en | SVK-1002 | ✓ | 0.00/0.00/0.00 | 0.00 | unchanged | word_run:INFRINGEMENTx56 | all_arms_fail; repetition_loop (score-insensitive trailing) |
| 023 | SANSKRIT | en | SVK-0038 | — | 0.33/0.67/0.33 | -0.33 | regressed | word_run:INFRINGEMENTx69 | paraphrase_drift ('living creature' not in keyterm set; no ahimsa/ahimsarata term) + repetition_loop |
| 024 | AGAM_GROUNDED | en | SVK-2022 | ✓ | 0.00/0.00/0.00 | 0.00 | unchanged | word_run:INFRINGEMENTx75 | all_arms_fail; repetition_loop (score-insensitive trailing) |
| 025 | AGAM_GROUNDED | en | SVK-2026 | — | 0.00/0.00/0.00 | 0.00 | unchanged | word_run:INFRINGEMENTx58 | all_arms_fail; repetition_loop (score-insensitive trailing) |
| 026 | AGAM_GROUNDED | en | SVK-2026 | — | 0.67/0.00/0.00 | 0.00 | unchanged | word_run:INFRINGEMENTx71 | repetition_loop (score-insensitive trailing) |
| 027 | AGAM_GROUNDED | en | SVK-2029 | ✓ | 0.33/0.33/0.33 | 0.00 | unchanged | word_run:INFRINGEMENTx72 | repetition_loop (score-insensitive trailing) |
| 028 | STHANAKAVASI_DISTINCTI | en | SVK-0038 | — | 1.00/1.00/1.00 | 0.00 | unchanged | sentence_repeat | correct_despite_refusal_like_substring ('manuscripts are not available in this corpus' is a detail, not a refu |
| 029 | STHANAKAVASI_DISTINCTI | en | SVK-0038 | — | 1.00/1.00/1.00 | 0.00 | unchanged | sentence_repeat | repetition_loop (score-insensitive trailing) |
| 030 | STHANAKAVASI_DISTINCTI | en | SVK-0038 | — | 1.00/0.00/0.00 | 0.00 | unchanged | sentence_repeat | inherited_dapt_failure (base=1.0, dapt=0.0, sft=0.0) — SFT did not repair the known Digambara-canon regression |
| 031 | STHANAKAVASI_DISTINCTI | en | SVK-0038 | — | 1.00/1.00/1.00 | 0.00 | unchanged | sentence_repeat | repetition_loop (score-insensitive trailing) |
| 032 | SOURCE_ATTRIBUTION | en | SVK-2027 | ✓ | 0.00/0.00/0.00 | 0.00 | unchanged | sentence_repeat | all_arms_fail; repetition_loop (score-insensitive trailing) |
| 033 | SOURCE_ATTRIBUTION | en | SVK-1001 | — | 0.00/0.00/0.00 | 0.00 | unchanged | — | all_arms_fail |
| 034 | SOURCE_ATTRIBUTION | en | SVK-0038 | — | 0.00/0.50/0.50 | 0.00 | unchanged | — | none_observed |
| 035 | SOURCE_ATTRIBUTION | en | SVK-2029 | ✓ | 0.00/0.00/0.00 | 0.00 | unchanged | — | all_arms_fail |
| 036 | ABSTENTION | en | SVK-2027 | ✓ | 0.00/0.00/1.00 | 1.00 | improved | — | keyterm_gain |
| 037 | ABSTENTION | en | SVK-0038 | — | 0.00/0.00/0.00 | 0.00 | unchanged | — | all_arms_fail |
| 038 | ABSTENTION | en | SVK-0038 | — | 0.00/0.00/0.00 | 0.00 | unchanged | sentence_repeat | all_arms_fail; repetition_loop (score-insensitive trailing) |
| 039 | ABSTENTION | en | None | — | 0.00/0.00/0.00 | 0.00 | unchanged | word_run:INFRINGEMENTx58 | all_arms_fail; repetition_loop (score-insensitive trailing) |
| 040 | PRACTICE | en | SVK-0038 | — | 0.50/1.00/0.50 | -0.50 | regressed | — | hallucinated_number (asserts 15 minutes; expected 48) — no Samayika/minutes content in SFT training data |
| 041 | PRACTICE | en | SVK-0038 | — | 0.50/0.50/0.50 | 0.00 | unchanged | word_run:croppedx68 | repetition_loop (score-insensitive trailing) |
| 042 | PRACTICE | en | SVK-2024 | ✓ | 0.50/0.50/0.50 | 0.00 | unchanged | word_run:INFRINGEMENTx48 | repetition_loop (score-insensitive trailing) |
| 043 | PRACTICE | en | SVK-2025 | ✓ | 0.00/0.50/0.00 | -0.50 | regressed | word_run:INFRINGEMENTx66 | over_abstention (refuses an answerable case: 'does not provide specific information') + repetition_loop |
| 044 | MULTILINGUAL_MAPPING | en | SVK-1001 | — | 0.00/0.00/0.00 | 0.00 | unchanged | sentence_repeat | all_arms_fail; repetition_loop (score-insensitive trailing) |
| 045 | MULTILINGUAL_MAPPING | gu | SVK-1002 | ✓ | 0.00/0.00/0.00 | 0.00 | unchanged | word_run:ડx21 | all_arms_fail; repetition_loop (score-insensitive trailing) |
| 046 | MULTILINGUAL_MAPPING | en | SVK-2008 | — | 1.00/1.00/1.00 | 0.00 | unchanged | sentence_repeat | repetition_loop (score-insensitive trailing) |
| 047 | MULTILINGUAL_MAPPING | hi | SVK-2007 | — | 1.00/1.00/1.00 | 0.00 | unchanged | — | none_observed |

## 6. Five regression deep-dives (Phase 2)

### 6.1 Case 008 — STHANAKAVASI_TERMINOLOGY
**Scores** base 0.0 / dapt 1.0 / sft 0.0 · SOURCE_OVERLAP=false · DAPT split: train

**Question**: According to Stevenson, which scriptures do the Terapanthi accept?

**Expected**: They accept the Sthanakavasi scriptures (but read their own meaning into certain passages).

**DAPT-01 answer (correct/partial)**: The Terapanthi accept the Sthanakavasi scriptures, excluding the Suvrata and the Sambhuti. They also accept the Sthanakavasi scriptures, excluding the Suvrata and the Sambhuti. They also accept the Sthanakavasi scriptures, excluding the Suvrata and the Sambhuti. They also accept the Sthanakavasi scriptures, excluding the Suvrata and the Sambhuti. They also accept the Sthanakavasi scriptures, excluding the Suvrata and the Sambhuti. They also accept the Sthanakavasi scriptures, excluding the Suvrata and the Sambhuti. They also accept the Sthanakavasi scriptures, excluding the Suvrata and the Sambhuti. They also accept the Sthanakavasi scriptures, excluding the Suvrata and the Samb

**SFT-01 answer (regressed)**: According to Stevenson, the Terapanthi accept the Sthaviravadaniya and the Sthaviravadaniya Purva. They reject the Sthaviravadaniya Uttara. Their scriptures are written in Gujarati. Their scriptures are written in Gujarati. Their scriptures are written in Gujarati. Their scriptures are written in Gujarati. Their scriptures are written in Gujarati. Their scriptures are written in Gujarati. Their scriptures are written in Gujarati. Their scriptures are written in Gujarati. Their scriptures are written in Gujarati. Their scriptures are written in Gujarati. Their scriptures are written in Gujarati. Their scriptures are written in Gujarati. Their scriptures are written in Gujarati. Their scriptur …[full text in JSON]

**Behaviour changed**: hallucinated_content + repetition_loop (DAPT also looped; SFT replaced correct 'Sthanakavasi scriptures' with invented Sthaviravadaniya/Gujarati claims)

**Likely cause**: conflicting/garbage content + generation instability (not memorization: SVK-0038 not in training; no Terapanthi rows)

**Evidence**:
- SFT training data contains 0 rows mentioning Terapanthi/scriptures of Terapanthi (measured)
- regression unit SVK-0038:u01199 not present in training units (measured)
- DAPT answer also exhibited a repetition loop (pre-existing instability, worsened: SFT invented Sthaviravadaniya/Gujarati content)

### 6.2 Case 016 — HINDI
**Scores** base 0.6666666666666666 / dapt 0.6666666666666666 / sft 0.3333333333333333 · SOURCE_OVERLAP=true · DAPT split: train

**Question**: 'अविनीत' शिष्य की पहचान उत्तराध्ययनसूत्र में क्यै बताई गई है?

**Expected**: जो गुरु की आज्ञा-निर्देश का पालन नहीं करता, गुरुजनों की सेवा से दूर रहता है और उनके प्रतिकूल आचरण करता है, वह अविनीत है।

**DAPT-01 answer (correct/partial)**: उत्तराध्ययनसूत्र में 'अविनीत' शिष्य की पहचान दो तरह से की गई है: वे जो शास्त्रों का अध्ययन करते हुए भी उनका अर्थ नहीं समझते हैं और जो शास्त्रों का अध्ययन नहीं करते हैं, उनकी बातें नहीं सुनते हैं। ये दोनों तर

**SFT-01 answer (regressed)**: उत्तराध्ययनसूत्र में 'अविनीत' शिष्य की पहचान दो तरह से की गई है - विनीत शिष्य के विपरीत व्यवहार और विनीत शिष्य के विपरीत विवरण। इन दोनों तरह के विवरणों का विश्लेषण करके अविनीत शिष्य की पहचान की गई है। INFRINGEMENT INFRINGEMENT INFRINGEMENT

**Behaviour changed**: contentless_meta_answer (Hindi answer describes that a definition exists without giving it) + minor INFRINGEMENT run

**Likely cause**: insufficient-example / content-thinning + minor token degeneration; Hindi never trained on (0 Hindi-script rows)

**Evidence**:
- train set has 0 Hindi-script rows (measured)
- SOURCE_OVERLAP=true (SVK-2020 in training on other units) — same-source exposure did not preserve the answer
- SFT answer is a meta-statement ('पहचान की गई है') without the definitional content, plus INFRINGEMENT x3

### 6.3 Case 023 — SANSKRIT
**Scores** base 0.3333333333333333 / dapt 0.6666666666666666 / sft 0.3333333333333333 · SOURCE_OVERLAP=false · DAPT split: train

**Question**: According to Stevenson, what is the first vow taken by a Jaina ascetic, and what term is used for it?

**Expected**: To refrain from destroying/killing living beings, whether subtle or movable or immovable (Ahimsarata).

**DAPT-01 answer (correct/partial)**: The first vow taken by a Jaina ascetic is to abstain from killing any living beings, including insects. This vow is called the first great vow, or the first great vow of the Jaina. It is considered the most important vow, as it forms the foundation of the Jaina ethical code. The term "mahavrata" is used to refer to this vow, which means "great vow." This vow emphasizes the importance of non-violence and compassion towards all living beings, reflecting the core principles of Jainism.

**SFT-01 answer (regressed)**: According to Stevenson, the first vow taken by a Jaina ascetic is to abstain from killing any living creature. This vow is called the first great vow, or the great vow of non-violence. It is considered the most important vow in Jainism.INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEM …[full text in JSON]

**Behaviour changed**: paraphrase_drift ('living creature' not in keyterm set; no ahimsa/ahimsarata term) + repetition_loop

**Likely cause**: paraphrase drift under template training + repetition_loop; not memorization (unit absent from train)

**Evidence**:
- no ahimsa/first-vow rows in training (measured 0)
- SFT kept 'abstain from killing any living creature' but dropped 'living beings' and any ahimsa/ahimsarata term → keyterm groups lost
- word_run INFRINGEMENT in the same output

### 6.4 Case 040 — PRACTICE
**Scores** base 0.5 / dapt 1.0 / sft 0.5 · SOURCE_OVERLAP=false · DAPT split: train

**Question**: According to Stevenson, how long must a layman spend over Samayika?

**Expected**: Forty-eight minutes.

**DAPT-01 answer (correct/partial)**: According to Stevenson, a layman must spend at least 48 minutes over Samayika. This time is divided into three parts: 15 minutes for the first part, 15 minutes for the second part, and 18 minutes for the third part. This structured approach ensures that the practice is thorough and meaningful.

**SFT-01 answer (regressed)**: According to Stevenson, a layman must spend at least 15 minutes over Samayika. This time is dedicated to meditation and reflection, allowing the individual to connect with their inner self and cultivate a sense of peace and clarity. This practice is essential for spiritual growth and helps to cultivate a deeper understanding of the self and the world around them.

**Behaviour changed**: hallucinated_number (asserts 15 minutes; expected 48) — no Samayika/minutes content in SFT training data

**Likely cause**: hallucinated specific (15 minutes) — generation/parametric drift; NOT data conflict (0 rows mention Samayika/minutes)

**Evidence**:
- 0 training rows mention Samayika/minutes/48 (measured)
- no loop in this output (so this regression is independent of the loop failure mode)
- consistent with fabrication tendency also seen in held-out e355a8ac/021

### 6.5 Case 043 — PRACTICE
**Scores** base 0.0 / dapt 0.5 / sft 0.0 · SOURCE_OVERLAP=true · DAPT split: val

**Question**: In the Sthanang Sutra material of this corpus, in which direction(s) and for how long per direction is the Sarvatobhadra pratima kayotsarga practised?

**Expected**: It faces all ten directions (four cardinal, four intermediate, zenith and nadir), for at least one ahoratra (24 hours) per direction.

**DAPT-01 answer (correct/partial)**: The Sarvatobhadra pratima kayotsarga is practised in all six directions: east, west, north, south, up, and down. This practice is performed for a duration of 12 minutes in each direction, totaling 72 minutes for the entire practice. This practice is intended to cultivate a state of complete stillness and awareness, allowing the soul to experience its inherent qualities of infinite knowledge, perception, bliss, and energy.

**SFT-01 answer (regressed)**: The Sthanang Sutra material in this corpus does not provide specific information about the direction(s) or duration for which the Sarvatobhadra pratima kayotsarga is practised. It is recommended to consult other Jain scriptures or seek guidance from a knowledgeable teacher for this information.INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT INFRINGEMENT IN …[full text in JSON]

**Behaviour changed**: over_abstention (refuses an answerable case: 'does not provide specific information') + repetition_loop

**Likely cause**: over-abstention: refusal behaviour generalised from the 7 uniform abstention rows + repetition_loop

**Evidence**:
- all 7 abstention training answers share one frame ('The corpus does not record ... cannot be answered ... Evidence needed first') (measured)
- the exact phrase SFT used ('does not provide specific information') appears 0 times in training → generalised refusal, not copied text
- abstention gain on case 036 shows the same teaching works where absence is real; case 043 has the information present
- SOURCE_OVERLAP=true (SVK-2025 in training)

## 7. Held-out 9 outputs (Phase 3)

Reference counts claimed at Task-64 design time — **verified**: repetition loops **3**, sect assertions **2**, fabricated claims **1** — matches the recorded “3 / 2 / 1”. (Correct outputs: 3; additional partial/uncertain labels recorded below.)

| example | category | labels | assessment |
|---|---|---|---|
| svk-2026:source_attribution:0c412c5f | SOURCE_ATTRIBUTION | wrong, repetition_loop | collapsed attribution to 'Sthanakvasi' as author AND publisher; INFRINGEMENT run |
| svk-0038:source_attribution:e355a8ac | SOURCE_ATTRIBUTION | fabricated_claim | invents 'Gift of the Librarian, University of California, Berkeley, 1970' |
| svk-2007:source_attribution:8a4d2b6e | SOURCE_ATTRIBUTION | correct | Motilal Banarsidass, 1928 — matches reference |
| svk-2008:source_attribution:b84e9cbd | SOURCE_ATTRIBUTION | sect_assertion, repetition_loop, wrong | asserts sect Digambara where manifest reference is UNKNOWN; INFRINGEMENT run |
| svk-2010:source_attribution:27687711 | SOURCE_ATTRIBUTION | abstention_behavior, partially_correct | repeated 'unknown/not known' where reference records Internet Archive provenance — under-confident, no fabrication |
| svk-2014:source_attribution:e24370cf | SOURCE_ATTRIBUTION | sect_assertion | asserts 'Digambara tradition and the Sthanakavasi' vs UNKNOWN reference |
| svk-2026:source_attribution:7009447a | SOURCE_ATTRIBUTION | correct | canonical scripture — matches reference |
| svk-0038:canonical_vs_commentary:ec775818 | CANONICAL_VS_COMMENTARY | canonical_commentary_confusion, abstention_behavior | declines all four categories; reference status is UNKNOWN so hedge is defensible but uninformative |
| svk-2007:canonical_vs_commentary:8c483765 | CANONICAL_VS_COMMENTARY | correct, repetition_loop | 'an edition' matches reference; output then collapsed into CJK run (这个地图) |

Full generations and references: `sft01_eval_results.jsonl` / `sft_eval_v1.jsonl` (also reproduced in §5 of Task-65 execution report).

**Correspondence to training categories** (all held-out rows are `source_citation` or `canonical_commentary` — both dominant in training):

- **Wrong/fabricated (3)** — collapse of source-attribution handling into fluent template completion: *0c412c5f* (attribution collapsed to “Sthanakvasi” as author+publisher), *e355a8ac* (invents Berkeley/1970 provenance), *b84e9cbd* (invents Digambara sect where reference is UNKNOWN). Corresponds to the 30 `source_citation` training rows, 26 of which open with the identical “The manifest records” template, plus 4 provenance rows that teach concrete provenance facts (Internet Archive, TRAINING_ALLOWED).
- **Sect assertions (2)** — *b84e9cbd*, *e24370cf* assert a definite sect vs UNKNOWN reference. Training has 4 “which tradition and sect” questions of which 3 carry definite sects (1 UNKNOWN/multi) → the training distribution teaches “answer with a sect”.
- **Loops (3)** — *0c412c5f* (`INFRINGEMENT` run), *b84e9cbd* (`INFRINGEMENT` run), *8c483765* (CJK `这个地图` run; the answer text itself is correct). **No training category teaches repetition** → loop is a generation-stability failure (taxonomy T1), not a content failure.
- **Correct (3)** — *8a4d2b6e*, *7009447a* (manifest authorship), *8c483765* (canonical “an edition”).
- **Under-confident / partial (2)** — *27687711* (repeats “unknown” where reference records Internet Archive provenance — no fabrication, hedging where the corpus does know), *ec775818* (declines all four categories; reference status UNKNOWN so defensible but uninformative). Both trace to abstention-style hedging (7 uniform abstention frames in training).

## 8. Training-data composition & balance (Phase 4)

50 rows; sources 32; **all English-script: True**; eval(9) = 7 source_citation + 2 canonical.

| task_category | n | share | answer len median | answer len mean |
|---|---|---|---|---|
| source_citation | 30 | 0.6 | 193.0 | 203.6 |
| canonical_commentary_distinction | 8 | 0.16 | 277.0 | 264.4 |
| abstention | 7 | 0.14 | 199 | 196.6 |
| general_qa | 5 | 0.1 | 498 | 527.6 |

Question-pattern counts (substring): {"recorded": 10, "the manifest": 4, "which tradition and sect": 4, "provenance": 4, "what kind of text": 4, "according to": 2, "catalog header": 2}
Answer-pattern counts (substring): {"the manifest records": 26, "canonical": 14, "recorded as": 8, "does not": 7, "public domain": 4, "not recorded": 3, "acquired from internet archive": 3, "training_allowed": 3}
Sect field: {"STHANAKAVASI": 24, "GENERIC_JAIN": 1, "UNKNOWN": 21, "SVETAMBARA": 2, "MULTI_TRADITION": 2} · Knowledge layer: {"CANONICAL_SCRIPTURE": 14, "MIXED": 13, "LEXICON": 13, "SECONDARY_SCHOLARSHIP": 6, "REFERENCE": 4}

**Balance verdict**: NOT balanced: 60% source_citation with a single opener in 26/50 rows, 0 multilingual rows, 0 practice-explanation rows, 0 Sthanakavasi-distinction rows, 5 general_qa only; abstention rows are 7 copies of one sentence frame

**What the data teaches too strongly:**

| teaching | measured basis | observed consequence |
|---|---|---|
| cite sources verbatim | 26/50 rows open with “The manifest records” | rigid template; held-out fabrications where source lacks detail (e355a8ac, 021) |
| repeat source wording | paraphrase-preserving keyterms never contrasted | 023 paraphrase drift loses keyterm groups |
| answer in the template | single opener + fixed provenance sentence (4 provenance rows, identical “acquired from Internet Archive … TRAINING_ALLOWED” frame) | attribution collapses into template completion (0c412c5f) |
| make sect assertions | 4 sect questions, 3 definite vs 1–2 UNKNOWN | 2/9 held-out asserted a sect vs UNKNOWN reference |
| abstain | 7 rows, one frame (“The corpus does not record … cannot be answered … Evidence needed first”) | gain on 036 **and** over-abstention on answerable 043 |
| imitate narrow QA structure | 10/50 questions contain “recorded”; 5 general_qa only | contentless meta-answer on 016; PRACTICE regressions (no practice rows at all) |

**Absences that matter** (measured zero counts): practice-explanation rows **0**; Sthanakavasi-distinction rows **0**; multilingual rows **0**; Prakrit-terminology rows **0**; anti-fabrication contrast pairs **0**; rows mentioning Samayika/minutes **0** (case 040); rows mentioning ahimsa/first-vow **0** (case 023); rows mentioning Terapanthi **0** (case 008).

## 9. Training dynamics (Phase 5)

- Train loss logged 4.4708 → 1.5554 (mean 2.7133); eval loss 2.745 → 2.135 → 1.9925 across 3 epochs / 21 steps; runtime 354.6 s (training 147.2 s), final lr 6.156e-07, T4.
- **Classification** (A–E, evidence-based):

| class | verdict | evidence |
|---|---|---|
| A useful learning | **YES** | YES (eval loss monotone down; abstention 0->1; prakrit retained; DAPT-unseen split improves 0.0476->0.1905) |
| B behavioural overfitting | **YES** | YES (template rigidity, refusal generalisation, answer median length 330->851, held-out fabrications) |
| C memorization | **NOT_DETERMINED** | NOT_DETERMINED (no unit overlap measured; no probe run; loss alone cannot prove it) |
| D generation instability | **YES** | YES, DOMINANT (28/47 looped vs 2 dapt / 0 base; INFRINGEMENT in 24/47; token not present in any data file) |
| E insufficient evidence | **PARTIAL** | PARTIAL — per-epoch generation behaviour NOT_MEASURED (intermediate checkpoints exist but no GPU locally to sample them) |

- **Verdict: simultaneous A + B + D.** Learning happened (loss monotone, abstention/prakrit/test-split gains) *and* the adapter degraded behaviour (template rigidity, refusal generalisation, runaway length) *and* dominant failure is generation instability. C cannot be concluded: no unit overlap was found in training and no memorisation probe was run → `NOT_DETERMINED`.
- Eval loss kept improving while behaviour degraded — loss is not a success criterion here (as pre-declared).
- v1 vs v2 Kaggle runs: identical metrics (v2 canonical, post-training `dict(TrainOutput)` TypeError fix); adapters not bitwise identical across runs (fp16) — recorded in Task-65 report.

## 10. Score deltas by category & language

Macro keyterm scores over the frozen 47 (computed from `sft01_3way_comparison.json`).

### 10.1 Per-category macro scores

| category | n | base | dapt | sft | sft−dapt |
|---|---|---|---|---|---|
| ABSTENTION | 4 | 0.0000 | 0.0000 | 0.2500 | 0.2500 |
| AGAM_GROUNDED | 4 | 0.2500 | 0.0833 | 0.0833 | 0.0000 |
| GUJARATI | 4 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| HINDI | 4 | 0.1667 | 0.2500 | 0.1667 | -0.0833 |
| JAIN_TERMINOLOGY | 4 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| MULTILINGUAL_MAPPING | 4 | 0.5000 | 0.5000 | 0.5000 | 0.0000 |
| PRACTICE | 4 | 0.3750 | 0.6250 | 0.3750 | -0.2500 |
| PRAKRIT | 4 | 0.0000 | 0.3750 | 0.3750 | 0.0000 |
| SANSKRIT | 3 | 0.1111 | 0.2222 | 0.1111 | -0.1111 |
| SOURCE_ATTRIBUTION | 4 | 0.0000 | 0.1250 | 0.1250 | 0.0000 |
| STHANAKAVASI_DISTINCTION | 4 | 1.0000 | 0.7500 | 0.7500 | 0.0000 |
| STHANAKAVASI_TERMINOLOGY | 4 | 0.0000 | 0.2500 | 0.0000 | -0.2500 |

### 10.2 Per-language macro scores

| language | n | base | dapt | sft | sft−dapt |
|---|---|---|---|---|---|
| en | 34 | 0.2304 | 0.2647 | 0.2255 | -0.0392 |
| gu | 5 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| hi | 8 | 0.2083 | 0.4375 | 0.3958 | -0.0417 |

**Reading**: the −0.0355 headline drop concentrates in **PRACTICE (−0.25)**, **Sthanakavasi terminology (−0.25)**, **Sanskrit (−0.11)**, **Hindi (−0.08)** — all explanation/terminology categories, exactly where training has zero rows — while **Abstention (+0.25)** improved. SFT gains over DAPT are entirely behavioural-style (abstention), not knowledge.

## 11. Source overlap (Phase 6) — `SOURCE_OVERLAP` label

- Training sources ∩ frozen sources: **10 sources** (SVK-1002, SVK-1005, SVK-2006, SVK-2012, SVK-2020, SVK-2022, SVK-2024, SVK-2025, SVK-2027, SVK-2029) → **17 training rows** (matches the pre-declared Task-64 limitation) → **18 frozen cases** affected: 001, 009, 011, 013, 014, 015, 016, 017, 020, 022, 024, 027, 032, 035, 036, 042, 043, 045.
- Regressions on overlap sources: **016, 043** (016=SVK-2020, 043=SVK-2025). The other three regressions (008, 023, 040) are on **non-overlap** sources → overlap does not explain the regression set.
- Eval(9) split ∩ train sources = ∅ (split held: source-level disjoint).
- Label only: **benchmark NOT modified**; frozen cases unchanged. Per-case `source_overlap` is in the matrix (§5) and JSON.

## 12. Failure taxonomy

- **T1_generation_instability**: count_sft=28; count_dapt=2; count_base=0; detail=INFRINGEMENT token runs in 24/47 SFT outputs; token absent from train/eval/cases/corpus files (origin NOT_DETERMINED; effect attributable to adapter)
- **T2_template_rigidity_fabrication**: heldout_cases=['e355a8ac', '0c412c5f', '021']; evidence=26/50 training rows open with 'The manifest records'; fabricated provenance/author details appear where source lacks them
- **T3_over_abstention**: frozen=['DAPT01EVAL-043']; heldout=['27687711 (under-confident)']; evidence=7 uniform abstention frames; refusal generalised to answerable case 043 while gaining case 036
- **T4_sect_assertion_without_evidence**: heldout=['b84e9cbd', 'e24370cf']; frozen=['DAPT01EVAL-030 (inherited)']; evidence=3 of 4 tradition/sect training questions carry definite sects; 2/9 held-out asserted a sect vs UNKNOWN reference
- **T5_paraphrase_drift_keyterm_loss**: frozen=['DAPT01EVAL-023', 'DAPT01EVAL-016']; evidence=answers lose exact source wording while sounding plausible (023 'living creature')
- **T6_unrepaired_inherited_failures**: frozen=['DAPT01EVAL-030']; evidence=base=1.0 dapt=0.0 sft=0.0 — SFT-01's 50 rows contained no distinction/practice rows to fix it

Prevalence across the 5 regressions: T1 loops in 4/5 (008, 016, 023, 043), T3 over-abstention 1/5 (043), T5 drift 2/5 (016, 023), T2 fabrication 2/5 (008, 040), T6 inherited 1 additional case (030, unchanged not regressed). T4 sect assertion appears only in held-out (0/5 frozen regressions) — a forward-looking risk, not the current drop.

## 13. SFT-02 design requirements (Phase 7)

Derived from evidence above; **not executed in this task**.

| # | CHANGE | REASON | EVIDENCE | EXPECTED EFFECT | RISK |
|---|---|---|---|---|---|
| 1 | learning_rate 1e-4 -> 3e-5 (and/or epochs 3 -> 1-2 with behaviour-based early stop) | adapter weight drift is the dominant failure; loss kept falling while behaviour degraded | 28/47 looped outputs vs 2/0 for dapt/base; INFRINGEMENT token absent from all data (T1); eval loss 2.745->1.992 alongside degradation | fewer degenerate token runs; smaller behavioural shift from DAPT-01 | under-training; may lose the abstention/test-split gains — must re-verify on frozen set before any promotion |
| 2 | behaviour-based checkpoint selection (sample generation from checkpoint-1..N) instead of fixed 3 epochs | epoch count was fixed a priori with no behavioural signal | classification A+B+D simultaneously; per-epoch behaviour NOT_MEASURED (E) | stop before behavioural peak passes | requires an extra inference pass per checkpoint (cost); selection metric must be pre-registered |
| 3 | cap source_citation share at ~40% of rows; break the single-opener template | 60% citation rows with 26/50 identical opener teaches rigid template + attribution fluency over content | train_analysis template_opener=26/50; held-out fabrications e355a8ac/021; answer phrasing rigidity | fewer fabricated specifics; more content-bearing answers | could erode the retained SOURCE_ATTRIBUTION gain (+0.125 vs base) — keep representative non-templated citation rows |
| 4 | zero SOURCE_OVERLAP: exclude all 19 frozen-eval sources from SFT-02 training | 17 train rows currently share sources with the benchmark | overlap analysis: 10 sources, 18/47 affected cases; 2/5 regressions on overlap sources (016,043) | cleaner attribution of future deltas; removes one confound | shrinks eligible source pool (85 sources exist — acceptable) |
| 5 | abstention calibration: add answerable/unanswerable contrast pairs; diversify refusal phrasing | single frame over-generalises (over-refusal) while 3/4 frozen abstentions still fail | gain on 036, over-abstention on 043; 7 identical-frame abstention rows; frozen abstention 1/4 | keep 036-type gain, fix 043-type false refusals, target 037-039 | too much calibration could weaken the only abstention gain |
| 6 | add explicit Sthanakavasi-distinction and practice-explanation rows from non-frozen sources | SFT-01 regressed PRACTICE (0.625->0.375) and did not repair 030 | category table; regressions 040/043 (PRACTICE); 030 inherited failure; 0 practice rows, 0 distinction rows in training | restore PRACTICE-level scores; address the known DAPT weakness | must avoid building rows from frozen units (leakage); corpus has eligible non-frozen units |
| 7 | add multilingual (hi/gu/Prakrit) rows | training was 100% English-script while benchmark has 8 hi + 5 gu cases | all_english_script=true; hi score slipped dapt 0.4375 -> sft 0.3958; gu stuck at 0 for all arms | protect hi/gu; potentially address gu=0 (OCR-sensitive substring matching limits) | OCR noise in source text; small n per language |
| 8 | concision discipline: cap target answer length near DAPT's distribution (~median 330 chars) | SFT outputs ballooned (median 851) and rambling correlates with loop onset | median length base 199 / dapt 330 / sft 851; loops are trailing | shorter outputs, later/less loop onset | may reduce explanatory quality on general_qa rows |
| 9 | anti-fabrication/contrast examples (wrong-attribution corrected to 'not recorded') | fabricated specifics observed in 3 places | e355a8ac Berkeley provenance, 021 Dr. P. S. Jaini, 040 '15 minutes' | fewer invented names/years | over-correction into refusal (interacts with abstention calibration) |
| 10 | KEEP: QLoRA NF4, r16/a32/d0.05, seed 42, Qwen3-8B-Base, DAPT-15248 lineage (no rank/precision/model change) | no evidence implicates rank/quantisation/model family; failures are behavioural | DAPT-01 used same geometry and is the current best; loops not present in DAPT arm under identical geometry | preserves comparability of the experiment series | if loops persist at low LR, geometry/optimiser would then become a candidate (flagged as later option, not chosen now) |

## 14. SFT-02 data requirements (Phase 8)

| CATEGORY | CURRENT COUNT | OBSERVED FAILURE | TARGET COUNT | WHY (derived) |
|---|---|---|---|---|
| grounded Jain concept / practice explanation | 5 | contentless vague answer (016); PRACTICE category regressed 0.625->0.375 (040,043) | 12-15 (incl. >=8 practice-explanation rows from non-frozen units) | thinnest category (10% of train) yet two of five regressions are explanation-type; target sized to rival source_citation dominance |
| source attribution (manifest) | 30 | fabricated provenance/author details (e355a8ac, 021); rigid opener 26/50 | 16-18, of which >=6 unanswerable/unknown-attribution variants | reduce from 60% share; failure occurred exactly in this templated category; unknown-variants counter fabrication |
| canonical vs commentary | 8 | ec775818 hedge; 8c483765 ok (behaviour acceptable) | 8-10 with >=3 contrast pairs (commentary-like vs canonical) | category stable — hold size, add contrast to reduce confusion |
| abstention | 7 | over-abstention on answerable case 043; 3/4 frozen abstentions still failing | 10-12 as answerable/unanswerable contrast pairs, >=4 phrasings | one gain + one new false-refusal + three unmet cases — calibration needs both directions |
| sect assertion discipline / Sthanakavasi distinction | 0 explicit distinction rows; 4 sect questions (3 definite vs 1-2 unknown) | 2/9 held-out sect assertions vs UNKNOWN; frozen 030 not repaired (0.75 vs base 1.0) | 8 (4 distinction + 4 unknown-vs-definite discipline), non-frozen sources only | both an inherited DAPT weakness and a new held-out failure; currently zero training mass |
| anti-fabrication / correction-contrast | 0 | 3 fabrications (e355a8ac, 021, 040) | 6-8 pairs (false claim -> 'not recorded in source') | failure count across two sets; pairs, not single rows, to teach the boundary |
| multilingual (hi/gu) + Prakrit terminology | 0 | hi slipped -0.04 vs dapt; gu 0/4 all arms; no training exposure at all | 8-10 rows (split hi/gu), Prakrit terms from non-frozen sources | zero exposure is the measured gap; modest count to protect rather than boost |
| concise template-free QA (length discipline) | implicit (median 206 chars) | SFT output median ballooned to 851 chars; trailing loops | applied as a constraint across all categories (cap ~350 chars median), not a new category | length regression measured against DAPT distribution |
| general_qa breadth beyond manifest questions | 5 | narrow question styles: 10/50 questions contain 'recorded' | >=10 varied wh-questions | question diversity directly addresses template imitation |

Additional structural constraints (from measured confounds):
1. **SOURCE_OVERLAP = 0** in SFT-02: exclude all 19 frozen-eval sources (current: 17 rows / 18 cases — §11).
2. **Source-level split must stay disjoint** for the 9-row eval; keep the same split protocol (already held this run).
3. **No frozen-case content** may be paraphrased into training rows (040/043/008 units are frozen; build from non-frozen units only).
4. Length discipline as a cross-category constraint (cap target median ≈350 chars, near DAPT's 330).
5. Pre-register a behaviour-based checkpoint/early-stop metric (per-class scores + loop rate on a proxy set) before training — loss alone is disqualified by §9.

## 15. Unresolved questions

- Origin of the 'INFRINGEMENT' token run: absent from all data files; weight-space cause NOT_DETERMINED (would need logit probing of base vs adapter — no GPU in this task).
- Which epoch introduced the loops: per-epoch generation NOT_MEASURED (checkpoints exist but sampling requires GPU).
- Whether lower LR alone removes loops: NOT_TESTED (no training allowed in this task).
- Whether SOURCE_OVERLAP caused any specific regression: only correlational (016, 043 overlap; 008, 023, 040 do not).
- Evaluator-based counts (factual_error/unsupported/sect_confusion/degenerate_loop) for the SFT arm: NOT_MEASURED (no evaluator pass run).

## 16. NOT_MEASURED / NOT_DETERMINED

- SFT-arm evaluator rubric metrics (factual_error, unsupported_claims, sect_confusion, degenerate_loop): NOT_MEASURED.
- sft_eval_v1 numeric score: NOT_MEASURED by design (no rubric on the 9 rows); observations only.
- Per-checkpoint behavioural trajectory: NOT_MEASURED.
- Peak VRAM / accelerate version (Task-65): NOT_RECORDED.
- Statistical significance of category deltas (n=3-4 per category): NOT_MEASURED.

## 17. Validation

- **Test suite**: `PYTHONPATH=src python3 -m unittest discover -s tests` → **435 ran, 0 failures, 2 errors, 1 skip** — identical to baseline (the 2 errors are pre-existing `ModuleNotFoundError: No module named 'faiss'` in `tests/test_retrieval.py`). No new failures.
- **Git**: `git pull --ff-only` → Already up to date. `git diff` → **empty (0 tracked modifications)**; `git status` → only untracked files (this task adds exactly the 2 deliverables below; all SFT/task-64/65 files remain untracked as before). **Frozen benchmark file not modified** — `data/evaluation/dapt01_eval_cases.jsonl` absent from both `git diff` and `git status` (sha256 `06625f72…65b81` unchanged).
- **Files created (2)**:
  - `data/reports/task66_sft01_failure_analysis.md` (45084 bytes)
  - `data/reports/task66_sft01_failure_analysis.json` (157434 bytes)
- **Deliverable completeness**: 40/40 automated checks passed — 11 required contents present in both MD/JSON (scope declaration, repository state, 47-case matrix, 5 regression deep-dives, 9 held-out analyses + count verification, training-data composition, training-dynamics classification A–E, category/language deltas, source-overlap labels, failure taxonomy, SFT-02 design + data requirements), headline numbers consistent with the frozen three-way comparison, no Kaggle credentials in deliverables.
- **Actions NOT taken (verified)**: training runs false; Kaggle API calls 0; benchmark/DAPT files modified false; SFT-01 promotion no (DAPT-01 remains current best).

## 18. Final block

```
TASK 66 COMPLETE
ANALYSIS ONLY: YES
TRAINING RUN STARTED: NO
KAGGLE API CALLS: 0
BENCHMARK/DAPT MODIFIED: NO
SFT-01 PROMOTED: NO
DAPT-01 REMAINS CURRENT BEST: YES (0.2660)
DELIVERABLES:
  data/reports/task66_sft01_failure_analysis.md
  data/reports/task66_sft01_failure_analysis.json
TESTS: 435 ran, 0 failures, 2 pre-existing faiss errors, 1 skip (baseline match)
GIT DIFF: empty
HARD STOP: YES
```

# Task 97 — Case037 Evidence-Length vs Evidence-Content Ablation Design

Design-only deliverable. **No model calls were made** (0 calls). This report is produced before inference, as required.

Runner: `experiments/task97/build_ablation_design.py`
Cell specs: `experiments/task97/cell_specs.json`
Design metrics: `data/reports/task97_ablation_design.json`

## Context (from Task 96)

On byte-identical prompts repeated 5×, arm B (t500) always abstained (5/5) and arm D (t2000) always asserted "founded 1658 by Birbhan" (5/5). The only prompt-level difference between B and D is three evidence-unit tails that D re-enables (the authentic next few hundred characters of the same corpus units; same units, same order, same headers, same question, same system prompt, same `num_predict`). None of the three tails mention Terapanth, a founding, or 1658.

Length vs content was left unresolved in Task 96 (confidence `probable`).

## Experiment matrix (all authentic corpus text, no fabrication)

All cells use the same pinned hybrid top-10 evidence (e_k=10, t2000) and the same question. Extended cells re-enable each unit's own real tail exactly as the Task-94 D arm saw; nothing is reordered, fabricated, or masked.

| Cell | Extended units | Prompt chars | Prompt tok est. | Isolates |
|---|---|---|---|---|
| `B_t500_original` | none | 5798 | 1449 | Baseline B (abstains 5/5) |
| `D_t2000_original` | E2, E5, E10 | 6207 | 1551 | Baseline D (asserts 5/5) |
| `X_E2only` | E2 only (+29 ch) | 5827 | 1456 | Decisive-unit completion (E2 contains the 1658 sentence at offset 105; its own tail is trivial, non-factual) |
| `X_E5only` | E5 only (+321 ch) | 6119 | 1529 | Largest unrelated content chunk (Jnanesvara-era material, topically unrelated to Terapanth) |
| `X_E10only` | E10 only (+59 ch) | 5857 | 1464 | Smallest non-decisive tail |
| `X_E5E10` | E5, E10 (+380 ch) | 6178 | 1544 | Unrelated bulk without completing the decisive unit |
| `X_E2E5` | E2, E5 (+350 ch) | 6148 | 1537 | Decisive unit + large unrelated chunk |
| `X_E2E10` | E2, E10 (+88 ch) | 5886 | 1471 | Decisive unit + small non-decisive tail |

`B_t500_original` and `D_t2000_original` cells were byte-verified against the Task-94 stored prompts (`B_cell_byte_equal_task94: true`, `D_cell_byte_equal_task94: true`).

## Omitted conditions (with reasons)

- **Neutral length-matched filler inside evidence blocks (original option C):** omitted. Inserting fabricated filler text inside evidence blocks to pad length would misrepresent corpus content as authentic source material, violating evidence integrity and the "do not fabricate neutral evidence" constraint. A clean pure-length control *without any* content change is therefore not constructible for this case.
- **B + additional real units (original option D):** inapplicable. B and D contain the same ten units; the only difference is the presence of real tails. There are no "extra units" to add.
- Any cell that changes the unit set, reorders units, or modifies headers/questions was excluded to keep the ablation a single-factor tail-presence design over authentic text.

**Limitation stated plainly:** because every real tail also carries some content (even if topically unrelated to the founding question), length and content cannot be fully dissociated at the extremes; the intermediate cells localize which tail is necessary and sufficient, but "pure length" would require the omitted filler control.

## Recommended minimal experiment (for a future task; not run here)

Run **4 cells × 3 trials = 12 calls**, plus 1 sanity trial each of B and D = **14 calls total**:

- `X_E2only` ×3 — tests decisive-unit completion in isolation.
- `X_E5only` ×3 — tests the largest unrelated chunk in isolation.
- `X_E5E10` ×3 — tests bulk unrelated content without completing the decisive unit.
- `X_E10only` ×3 — tests the smallest non-decisive tail.
- `B_t500_original` ×1, `D_t2000_original` ×1 — same-day sanity anchors.

Rationale for trials-per-cell: Task 96 established 5/5 stability at the two extremes; 3 trials per intermediate cell gives a reasonable read on whether a cell flips, holds, or is erratic, at modest cost.

### Predicted outcomes and interpretations

| Observation | Interpretation |
|---|---|
| `X_E2only` asserts, all other intermediate cells abstain | Completing the 1658-containing unit is sufficient; implicates a localized length/format effect on the decisive unit (its own tail is factually trivial). |
| `X_E5only` (and/or `X_E5E10`) asserts, `X_E2only` abstains | The large unrelated E5 content chunk drives the flip; E10 alone is not sufficient. |
| Only cells containing both E2 and E5 (e.g., `X_E2E5`, `D_t2000_original`) assert | Interaction effect: neither decisive-unit completion nor bulk unrelated content alone suffices. |
| All intermediate cells abstain; only full D asserts | Threshold / interaction on combined added length+content; no single tail is sufficient. |
| Any intermediate cell is erratic across trials | Per-cell nondeterminism reappears; expand trials for that cell before concluding. |
| `X_E10only` asserts despite smallest delta | Length (not specific content) dominates, or the model is highly sensitive to prompt slack; revisit the pure-length limitation. |

## Estimated cost

Task 96 measured ~22–28 s per warm 037 call (eval ~92–104 tokens). A 14-call run: ~4 min Ollama cold-load + ~14 × 25 s ≈ **~10–12 min total wall**, 14 model calls. No training, no downloads, no paid APIs; in-process only.

## Verification

- Git HEAD recorded before design: `e0bd539c2a9e57d85df051effd50d8698a937e0e`.
- `configs/policy.toml` sha256 before design: `f32308d94dd9d54395daf2d4bb5ef7ede7600f7762e77dd480aea6926bf25851`.
- Task 96 artifacts verified intact (5 files re-hashed, verdicts re-read from `task96_validation.json`).
- Dense index built and alignment-verified read-only; no generation code invoked; provider never constructed; **0 model calls**.
- This design is delivered for review; the ablation is not executed here.

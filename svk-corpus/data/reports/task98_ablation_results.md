# Task 98 — Case037 Evidence-Tail Ablation Results

Executes the approved Task 97 design: 14 model calls on the existing local Ollama (`qwen2.5:7b-instruct`, temp=0.0, num_ctx=4096, num_predict=256, timeout 300 s — production defaults, verified effective before inference; nothing restarted or reconfigured).

Raw: `experiments/task98/task98_raw.jsonl` (14 rows). Metrics: `data/reports/task98_ablation_results.json`. Runner: `experiments/task98/run_task98_ablation.py`.

## Prompt verification (before any call)

All 8 cell prompts rebuilt from the pinned hybrid top-10 and byte-verified against `experiments/task97/cell_specs.json` (`hash_ok=True` for all 8); `B_t500_original` and `D_t2000_original` additionally byte-equal to the Task-94 stored prompts (`c77f7a34…`, `4f101ff7…`). Frozen-case/evidence/policy/pinned-embedding hashes all OK. Only the designated authentic tails differ between cells; no filler, no reordered units, no altered question.

## Results (abstain / assert "founded 1658"; eval_count)

| Cell | extend | trials | abstained | asserted 1658 | eval |
|---|---|---|---|---|---|
| `B_t500_original` (sanity) | — | 1 | 1/1 | 0/1 | 108 |
| `D_t2000_original` (sanity) | E2+E5+E10 | 1 | 0/1 | 1/1 | 104 |
| **`X_E2only`** | **E2 only** | 3 | **0/3** | **3/3** | 68, 96, 96 |
| `X_E5only` | E5 only | 3 | 3/3 | 0/3 | 67, 122, 122 |
| `X_E10only` | E10 only | 3 | 3/3 | 0/3 | 96, 96, 96 |
| `X_E5E10` | E5+E10 | 3 | 3/3 | 0/3 | 130, 130, 130 |

(`X_E2E5`, `X_E2E10` were built and hash-verified but not executed — outside the approved 14-call plan.)

Sanity checks reproduce the Task-96 5/5 pattern same-day: B abstains (mentions 1658 but declines to commit), D asserts "founded in 1658 by Birbhan". All 14 calls completed; no errors; no cap-hits (max eval 130 << 256).

## Verdict: E2 tail is necessary and sufficient (within this matrix)

The design contains two clean minimal pairs that differ **only** in E2's final 29 characters (the authentic completion `d a meeting at the full moon.`; E2 full = 529 chars vs truncated = 500):

- **Sufficiency:** `B_t500_original` (abstains) → `X_E2only` (asserts 3/3). Adding only the E2 tail flips the behavior.
- **Necessity:** `D_t2000_original` (asserts) → `X_E5E10` (abstains 3/3). Removing only the E2 tail from D flips it back.

E5 and E10 tails are individually and jointly insufficient (all abstain 3/3). No interaction among tails is needed to explain the original B/D difference: the E2 tail alone accounts for it.

## Length vs content: not a bulk-length effect

`X_E5only` (6119 prompt chars) abstains while `X_E2only` (5827 chars — 292 chars shorter) asserts; `X_E5E10` (6178 chars) abstains. Assertion does not increase monotonically with prompt length. The effect is **localized to the completeness of the decisive evidence unit** (E2 contains the founding-year sentence at offset 105, intact in both B and D): when E2's own block ends mid-word (truncated at 500), the model reads the 1658 sentence but declines to rely on it; when E2 ends at its natural sentence boundary, the same model at the same temperature commits.

Observed abstain rationale (B): "…[E2] mentions that the Terapanth was founded in 1658 by Birbhan, but this does not definitively identify the Terapanth as the sect in question…" — the year is seen in both conditions; what changes is trust in the fragment, not visibility of the fact.

## What this supports (and what it does not)

- **Supported:** a localized evidence-unit-completeness (truncation-state) effect on the decisive unit drives the Task-94 B-vs-D abstention difference for case037. Confidence: `probable`→strong; the minimal-pair design plus 3/3 stability in both directions and same-day sanity anchors make this the best-supported attribution. The Task-96 "prompt-content/length difference" finding is refined: content-position (which unit is truncated), not bulk length.
- **Not claimed:** why those 29 characters matter mechanistically (mid-word truncation signaling fragmentariness vs. sentence-boundary salience vs. local token-position shift inside the E2 block). The tails carry no founding-related content, so this is a format/completeness effect, but the cognitive-level mechanism remains a hypothesis. Pure length cannot be fully isolated (the Task-97 stated limitation stands), yet the bulk-length alternative is now empirically disfavored by the intermediate cells.
- **Exploratory caveats:** intermediate cells are 3-trial probes; sanity cells are n=1 checks (anchored by Task-96's 5/5). Do not overstate causality beyond this case/prompt family. Nondeterminism at temp 0 is a known standing confound in this codebase (Task-94 cases 028/002), but every cell here was internally consistent across its trials.

If a mechanistic follow-up is ever wanted (not required — the result is not ambiguous), the next smallest experiment is a single-cell probe that truncates E2 at a *different* authentic sentence boundary (e.g., a mid-unit offset that still ends on a period) to separate "ends mid-word" from "ends mid-unit"; ~3 calls.

## Runtime note

Actual wall 1630.1 s (~27 min) vs the Task-97 estimate ~600–720 s. Cause: Ollama had the model unloaded at preflight (`/api/ps` empty), so the first call paid cold-load (~269 s), and several later calls ran ~110–140 s vs Task-96's warm ~22–28 s (likely background load; FanPulse on :8000 and Ollama on :11434 were left untouched and remained healthy). The run completed all 14 planned calls within a single session; no unrelated service was affected; no mid-run abort was warranted. Reported honestly as an estimate miss, not a protocol deviation.

## Verification

- Git HEAD before/after: `e0bd539c2a9e57d85df051effd50d8698a937e0e` (unchanged); the only tracked modification remains the pre-existing `configs/policy.toml` `[retrieval]` block; **nothing staged**.
- `configs/policy.toml` sha256 before = after = `f32308d94dd9d54395daf2d4bb5ef7ede7600f7762e77dd480aea6926bf25851`.
- B/D prompt byte-equality to Task-94 re-verified in-run before inference; all 8 cell hashes match the approved Task-97 design.
- Model calls: **14** (exactly the planned set); no unrelated inference; no training/downloads/packages/paid APIs; Task-90–97 artifacts preserved; the unapproved case036 gold proposal remains unapproved and untouched.

Stopping here; no remediation attempted.

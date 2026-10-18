# Task 99 — Case037 E2 Boundary Mechanism Analysis (Design Only)

**Zero model calls.** Read-only analysis of E2 plus a proposed ≤3-call probe that is not executed here.

Artifacts: `data/reports/task99_boundary_analysis.json` (machine-readable twin). Evidence source: pinned corpus doc `SVK-1005:u03516:7f6ea7d5e3e38b91` (Sadh-sect section §412), pulled read-only via the existing retrieval service with pinned-embedding alignment verified.

## Step 1 — E2 boundary anatomy

E2 full text is **529 chars**. Its seven sentences (period offsets):

| Sentence | Offsets | Ends |
|---|---|---|
| `§412.` | 0:5 | `.` |
| ` The Sadhs^ are found chiefly between the two rivers\nfrom Delhi southwards.` | 5:80 | `.` |
| **` The sect was founded in 1658 by\nBirbhan.`** | **80:121** | `.` |
| ` He expressed his teaching, like Kabir, … Original Teaching.` | 121:257 | `.` |
| ` One element in the book is … viz.` | 257:453 | `.` |
| ` in the strict\ninjunction of monogamy.` | 453:491 | `.` |
| ` They hold a meeting at the full\nmoon.` | 491:529 | `.` |

Key facts:

- The decisive **1658 sentence occupies chars 80–121**, far inside every truncation used in Tasks 94–98. It is fully visible in the abstention condition (cut@500) and the assertion condition (cut@529). The mechanism is therefore not visibility of the fact.
- The production truncation **cut@500** lands **mid-word** inside `hold` (word spans 497–501); the evidence block ends `…They hol`. The 29-char tail `d a meeting at the full\nmoon.` completes the word *hold*, the rest of the sentence, and the unit's natural end (period at 528).
- Authentic boundary candidates near the cut (all pure source prefixes, no fabrication):

| Candidate cut | Ends with | Boundary type | Hidden beyond cut | Prompt chars / tok~ | Task98 observed |
|---|---|---|---|---|---|
| 491 | `.` | sentence-end, **mid-unit** (sentence 6 of 7) | ` They hold a meeting at the full\nmoon.` (38 ch) | 5789 / ~1447 | not run (P1) |
| **500** | `l` (`hol`) | **mid-word, mid-sentence** | `d a meeting at the full\nmoon.` (29 ch) | 5798 / ~1449 | **ABSTAIN** (B sanity 1/1; Task-96 5/5) |
| 502 | ` ` (after `They hold `) | word-boundary, mid-sentence | `a meeting at the full\nmoon.` (27 ch) | 5800 / ~1450 | not run (P2) |
| 519 | ` ` (after `…at the `) | word-boundary, mid-sentence | `full\nmoon.` (10 ch) | 5817 / ~1454 | not run (P3) |
| **529** | `.` | **sentence-end AND natural unit end** | — (nothing) | 5827 / ~1456 | **ASSERT 3/3** (X_E2only) |

The three probe variants were **built and hash-recorded now** (read-only service build; no provider constructed, no generation):

| Variant | E2 cut | Prompt sha256 |
|---|---|---|
| `P1_cut491_sentence_boundary_midunit` | 491 | `496c99143d1fdf1356315d3ba67bd3b76fd178f0e8c7a153151940b4335ecfd0` |
| `P2_cut502_word_boundary_near_cut` | 502 | `3ccf66dc42e87b02fc4e2c1e578a2444757304607cca58a5468e48c1c466f602` |
| `P3_cut519_word_boundary_near_end` | 519 | `d0188f1d9e668ca897dc2727afabcbffb9db5792c31b7af93df0cc0d18cbe062` |

Sanity of the builder: the B prompt (all units cut@500) rebuilt to sha `c77f7a34…c419` (byte-equal to Task-94 B) and X_E2only (E2 cut@529) to `1106d5fe…0c80` (byte-equal to the Task-97/98 design). Each probe differs from B **only** in E2's truncation offset; all other nine units, headers, ordering, question, system prompt, and settings stay fixed at the B condition.

## Step 2 — Proposed minimal probe (≤3 calls; NOT executed in Task 99)

Run **exactly three calls**, one trial each of P1, P2, P3, against the already-stabilized anchors (B abstain 5/5 + 1/1 same-day; X_E2only assert 3/3 — no re-run needed). Single-trial cells are acceptable here because every Task-98 cell was internally consistent across its trials and the two anchors have been re-confirmed across days; a per-cell 3-trial replication remains the contingency if any single-trial outcome later proves decisive-but-flaky (would be a separate task, not part of this budget).

| Call | Variant | What it isolates |
|---|---|---|
| 1 | P1 cut@491 | Does **any** sentence boundary suffice, even mid-unit with the unit's final sentence entirely absent? |
| 2 | P2 cut502 | Does a **word boundary** at near-identical length to the observed mid-word cut (+2 chars) suffice? Length-matched contrast against cut@500. |
| 3 | P3 cut@519 | Does a word boundary **near the unit end** (only 10 chars hidden) suffice without completing the sentence? |

Settings identical to Task 98: `qwen2.5:7b-instruct`, temp 0.0, num_ctx 4096, num_predict 256, timeout 300 s, existing local Ollama untouched.

### Predicted outcome matrix

| Outcome | Interpretation |
|---|---|
| **P1 asserts** | Any sentence boundary restores trust in E2 — mechanism is sentence-completion, even mid-unit. Strongest support for a generic "no dangling sentence" heuristic. |
| P1 abstains, **P3 asserts** | Sentence boundary mid-unit insufficient; word-boundary completion close to the natural unit end suffices — end-proximity (or the specific near-complete final sentence) matters. |
| P1 abstains, P3 abstains, **P2 asserts** | Word-boundary vs mid-word at ~equal length is the operative contrast — the mechanism is specifically **fragment (mid-word) signaling**, not sentence completion or end proximity. |
| **All three abstain** | Only the natural unit end (complete final sentence `They hold a meeting at the full moon.`) restores assertion — mechanism is **unit-completeness / exact-tail content**, not generic boundary hygiene. |
| **All three assert** | Any clean boundary (word or sentence, anywhere) suffices; the observed abstention was caused solely by the mid-word fragment state at cut@500. Supports fragment-avoidance. |
| Mixed (e.g., P2 abstains, P1+P3 assert, or any erratic single trial) | Boundary type alone does not explain the effect; distance-to-end or content interacts; treat as ambiguous and do not over-claim — propose (not run) a 2-call confirmatory pair for the deciding contrast. |

### Limitations (stated plainly)

- **Boundary type and hidden content are coupled by construction.** Every authentic cut simultaneously changes where the block ends and which words are visible. P2 is the closest thing to a length-matched boundary contrast (+2 chars vs B) but still swaps `hol` for `They hold `; P1 removes an entire sentence. The design triangulates; it cannot perfectly isolate "pure" boundary type from content. No fabricated filler was used or proposed, per the evidence-integrity constraint.
- **One trial per cell.** Sufficient given observed temp-0 stability on this case, but a single anomalous flip would need replication before any verdict (contingency, not part of this run).
- **Token counts are the chars/4 heuristic** used throughout Tasks 97–98; true tokenizer counts may differ by a few tokens and are not load-bearing for the design.
- **Scope:** case037 / E2 / this prompt family only. Generalization to other cases, units, or truncation policies is untested.
- Only mid-word cut@500 has been empirically observed among the non-end cuts; mid-word cuts at other offsets are untested (out of scope here).

### What remains unproven (regardless of this design's outcome)

- **Cognitive-level mechanism:** why a mid-word fragment at the end of a supporting evidence unit reduces the model's willingness to rely on a clearly visible fact — attention/trust heuristic, tokenizer-boundary artifact, local position shift, or something else. This design discriminates among *behavioral* descriptions (sentence-boundary vs word-boundary vs unit-end), not among internal causes.
- **Generality:** whether the effect holds for other evidence units, cases, models, or truncation lengths.
- **Production relevance:** whether any retrieval/truncation default should change — explicitly out of scope; no remediation is proposed or implemented.

## Verification

- Git HEAD before/after: `e0bd539c2a9e57d85df051effd50d8698a937e0e` (unchanged); only the pre-existing `configs/policy.toml` `[retrieval]` modification present; **nothing staged**.
- `configs/policy.toml` sha256 before = after = `f32308d94dd9d54395daf2d4bb5ef7ede7600f7762e77dd480aea6926bf25851`.
- Task94–98 artifacts re-hashed and intact (task98 md/json/raw, task97 specs, task94 results).
- **Model calls: 0.** Provider never constructed; only read-only corpus/retrieval access and local prompt-string hashing.
- The probe was designed, built, and hash-recorded but **not run**; no remediation attempted. Stopping here.

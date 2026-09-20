# Task 10 — Gujarati Within-Script Retrieval Alias Census

**Date:** 2026-09-18 · **Scope:** investigation + small controlled retrieval change. Corpus files, licence decisions, release contents untouched. The Task 8 baseline (`retrieval_eval_results.json`) and Task 9 result (`retrieval_eval_results_task9.json`) are preserved unmodified; this task wrote `retrieval_eval_results_task10.json`.

**Headline finding (measured, then interpreted):** the dominant Gujarati retrieval failure was **not spelling variance** — it was a tokenizer defect that silently destroyed every Indic combining sign (matra/virama) in both index and query, mangling all Indic tokens and even creating a live false merge (જિન and જૈન collapsed to identical fragments). The alias census is real and added two evidence-cited groups, but the tokenizer fix is what changed retrieval quality.

---

## 1. q17 diagnosis

Query: **`જૈન ધર્મ`** ("Jain dharma") — expected sources SVK-2010…2014 ("any hit from this set counts").

Task 9 state: all 5 expected sources appeared in the top-10 (R@10 = 1.0) but first hit was only **rank 3** (MRR 0.333) and R@5 = 0.6, with **dictionary units at ranks 1–2**. Inspecting those units' top Gujarati tokens showed single-letter fragments: `['જ', 6], ['ત', 4], ['મ', 2]…` — not real words. Root cause below (§6). No alias could fix a mangled-token match; this is why the investigation widened to tokenization.

## 2. Gujarati corpus census (measured from release + manifest)

31,374 Gujarati-script units, 1,717,401 chars across 8 sources:

| source | units | chars | religious_scope | knowledge_layer |
|---|---|---|---|---|
| SVK-2002 | 12,102 | 426,843 | CORE_STHANAKAVASI | LEXICON |
| SVK-2004 | 7,641 | 283,815 | CORE_STHANAKAVASI | LEXICON |
| SVK-2003 | 5,487 | 216,879 | CORE_STHANAKAVASI | LEXICON |
| SVK-2012 | 2,066 | 409,801 | UNKNOWN | SECONDARY SCHOLARSHIP |
| SVK-2014 | 1,638 | 149,537 | UNKNOWN | PRACTICE LITERATURE (sajjhaya) |
| SVK-2011 | 1,182 | 140,940 | UNKNOWN | PHILOSOPHY (Gujarati) |
| SVK-2010 | 1,050 | 74,829 | CORE_STHANAKAVASI | SECT LITERATURE |
| SVK-2013 | 208 | 14,757 | UNKNOWN | EDUCATIONAL |

Interpretation (clearly labelled as such): **~80% of Gujarati-script units are dictionary/lexicon material** (SVK-2002/2003/2004 = 25,230 units); the doctrinal/philosophy/practice layer is SVK-2010–2014. Gujarati-script presence says nothing about sect by itself — the CORE labels above are the Task 3 imprint-based attributions (dictionary provenance), not per-verse verification.

## 3–5. Candidate variants: evidence and verdicts

Census method: release-JSONL grep counts + full context inspection of every occurrence (all 31 ધરમ and all 24 જયन contexts read; no fuzzy matching used as proof).

### ACCEPTED (2 groups, added to `configs/retrieval_aliases_v1.json`)

| variant | evidence | confidence |
|---|---|---|
| **જૈનધર્મ** ↔ જૈન ધર્મ / જેનધરમ / જેન ધર્મ (phrase + single-token, `parts_as_search_terms: true`) | compound જૈનધર્મ 5 units (SVK-2014×2, SVK-2010/2011/2012×1); spaced જૈન ધર્મ 2 units; જેનધરમ 1 unit in the sect-critical sentence "જેનધરમષ્નું (=નું) એ એક ઉત્તમ…" (SVK-2012); જેન ધર્મ 0 occurrences — added query-side only, for the no-virama romanization system | MEDIUM |
| **ધર્મ** ↔ **ધરમ** (single-token) | ધરમ 29 units vs ધર્મ 242; contexts in SVK-2012/2014 are unambiguous dharma prose ("ધરમની વ્યાખ્યામાં", "વીર પરમાત્માનું નામ એ ધરમ બનાવી દેશે"); the isolated token ધરમ cannot be a substring false-positive (no combining signs) | MEDIUM |

### REJECTED (recorded in the config's `rejected_variants`)

| variant | reason |
|---|---|
| જયન ↔ જૈન | **Different lexemes.** All 24 occurrences are inside વિજયની ("victory", city names) or OCR numerics (SVK-2002/2003). Merging would summon victory/city passages for Jain queries. |
| જિન ↔ જૈન | Distinct words (Jina vs Jain), never merged. The tokenizer fix **removed** a pre-existing accidental collision: both collapsed to identical fragments `['જ','ન']` under the old tokenizer. |
| ધરમ in dictionary sources as "dharma" | There it appears only inside OCR-garbled longer strings (ઉંધરમા, મધરમ, શકેરધરમાં) — different tokens, unaffected by exact-token aliases. |
| જૈની / જૈન્ય | 0 occurrences; derivational morphology is not aliased (that would be unbounded stemming). |

### UNCERTAIN

- Whether SVK-2012's ધરમ forms are historical orthography or OCR virama-dropping — undecidable from the evidence; the alias is justified either way, but the *reason* is recorded as uncertain, not asserted.
- જેન ધર્મ (0 corpus occurrences): mapped query-side only on system-level analogy; flagged as the weakest element of the accepted group.

## 6. Implementation changes

1. **Tokenizer fix (the material change).** `_TOKEN_RE` was `[\w]+`; Python's `\w` excludes combining marks (matras = Mc, virama/anusvara = Mn), so **જૈન → ['જ','ન'], ધર્મ → ['ધર','મ'] (virama split the word), ક્ષેત્ર → 4 single letters, and જિન ≡ જૈન**. New pattern `[^\W_][\w\u0900-\u0DFF]*` keeps Indic signs attached (a combining sign can never start a token), plus **NFC normalization inside `tokenize`** so decomposed diacritics cannot split Latin tokens either. Verified: જૈન/ધર્મ/જિન/अहिंसा tokenize intact; NFC and NFD inputs now produce identical streams. Both BM25 sides share this function — no second normalization mechanism.
2. **Two Gujarati alias groups** in the existing config (mechanism unchanged from Task 9: phrase rules + single-token OR-expansion, config as single source of truth).
3. **`parts_as_search_terms` group flag** (new, explicit per group): lets the compound જૈનધર્મ query also search its attested standalone words જૈન/ધર્મ/જેન so it can reach spaced-form docs. Default remains OFF — Task 9's "ratna chandra ji" parts are meaningless fragments and must never become search terms; the asymmetry is config-visible, not code magic.
4. BM25 ranking logic itself: **unchanged** (same Okapi scoring, k1/b, filtering, result objects).

## 7. Before vs after (measured, same 20-query file, labels unchanged)

| metric | Task 9 | Task 10 | Δ |
|---|---|---|---|
| Recall@5 | 0.756 | **0.760** | +0.004 |
| Recall@10 | 0.838 | **0.819** | −0.019 |
| MRR | 0.871 | **0.905** | +0.034 |
| zero-relevant | 0 / 17 | 0 / 17 | 0 |
| mean query latency | 0.046 s | 0.0388 s | −16% |
| index build | 53.5 s | 54.6 s | ~same |
| SVK-context share (CORE+HIGH slots) | 0.575 | 0.550 | −0.025 |

**Queries improved: 1 · unchanged: 15 · regressed: 1.**

- **q17 (Gujarati) — improved:** MRR **0.333 → 1.000** (first hit now rank 1, a doctrinal SVK-2013 unit), R@5 0.6 → 0.8. Attribution: both changes contributed; the tokenizer fix is the larger factor (fragment-pollution matches no longer outrank whole-word matches). R@10 detail below.
- **q02 (`Acaranga Sutra English translation`) — regressed in MRR only** (0.333 → 0.250): expected SVK-1001 is still the **rank-1 result**; two other docs tied at rank 1 and the doc-index tie-break now orders them differently (tokenizer side effect on those docs' tf). No recall change; set of hits unchanged.
- **q06 (`Ardha Magadhi dictionary`)** scored "same" on MRR (1.000) but lost SVK-2004 from its top-10 (top-10 set 2 → 1 sources; top-5 unchanged with SVK-2002 first). Attribution: pure tokenizer side effect — the aliases cannot touch a Latin query; whole-word tokenization raised competing docs' scores above SVK-2004's dictionary units.
- **q17 R@10 trade-off (honest reporting):** Task 9 had all 5 expected sources in the top-10; Task 10 has 4 of 5 — **SVK-2010 (Jain Sathan Kavasi, 1928) fell out of the top-15** (rank 3 → >15). Its units are the most OCR-degraded Gujarati in the corpus (71 chars/unit, many garbled tokens), so under correct whole-word tokenization they genuinely match fewer query terms; the previous rank-3 was an artifact of fragment pollution. No safe alias can bridge this: its title is Latin-script ("Jain Sathan Kavasi"), and cross-script title↔Gujarati-query mapping is not evidenced.

## 8. Accidental-merge tests (all passing)

7 new tests in `tests/test_retrieval.py::TestGujaratiAliasesAndTokenization`:

1. Gujarati words tokenize intact (જૈન, ધર્મ, અહિંસા) and the જિન/જૈન collision stays dead;
2. ધરમ ↔ ધર્મ alias works in both directions without touching other words;
3. compound ↔ spaced bidirectional retrieval (including parts_as_search_terms);
4. **phrase parts never become search terms** — જૈન alone has no alias extras; a bare જૈન query cannot match a ધર્મ-only doc; the compound expansion injects exactly the attested spellings + attested parts and nothing else;
5. unrelated Gujarati terms stay unrelated (વિજય ≠ જૈન);
6. Unicode NFC/NFD forms produce identical token streams (regression-pins the NFC fix);
7. original text and full provenance unchanged on alias-driven hits.

During development these tests caught and fixed two of my own errors (inflected-form expectations inconsistent with the no-stemming policy) and one real asymmetry (compound queries could not reach spaced docs), which motivated the explicit `parts_as_search_terms` flag.

**Full suite: 129/129 pass** (102 existing + 10 Task 8 + 10 Task 9 + 7 new).

## 9. Remaining Gujarati retrieval limitations

- **SVK-2010 OCR quality** is now the binding constraint (71 chars/unit; heavy garbling) — a text-layer problem, out of scope for retrieval normalization.
- **No stemming/morphology:** inflected forms (ધર્મનો, જૈનની) do not match standalone queries; only attested exact variants are aliased. Deliberate.
- **Cross-script retrieval** (Gujarati query → Latin title/body) remains unimplemented and unevidenced; SVK-2010's Latin title is unreachable from Gujarati queries.
- OCR-garbled tokens inside dictionary sources (e.g. શકેરધરમાં) are unreachable by design — aliasing them would fabricate equivalences.
- Sect-context share moved 0.575 → 0.550: the reshuffled Indic rankings slightly favour UNKNOWN-scope units in svk-specific queries. Within the noise of a 20-query prototype set; monitored, not corrected.

## 10. Recommendation — next retrieval task

**One change: an OCR-aware exact-token census for the five doctrinal Gujarati sources (SVK-2010–2014) feeding alias-table v2** — frequency-ranked attested spelling pairs (the ધરમ/ધર્મ pattern generalized, e.g. કર્મ/કરમ, ધામ/ધરમ-adjacent forms only where context-verified), built by reading contexts, not by similarity. This targets the q17 residual (SVK-2010) only if evidence supports it; if the census shows SVK-2010's misses are pure garble, report that honestly and stop there — the correct fix would then be re-OCR/transcription (a corpus-layer task), not retrieval normalization.

---

**Measured vs interpretation:** §2, §5 counts, §7 tables and §8 are measured. Interpretive claims (root causes, attributions, the SVK-2010 quality explanation) are marked as such and are consistent with the per-query data in `retrieval_eval_results_task9.json` / `retrieval_eval_results_task10.json`.

# jain_svk_next_steps.md

---

## §1 · THE SINGLE NEXT ENGINEERING TASK

> **Build `svk-corpus` v0.1: a reproducible, licence-gated ingest pipeline for the CC0 Internet Archive
> Jain library, ending in a published, provenance-complete corpus manifest with measured token counts.**

That is the one task. It is deliberately *not* "train a model", *not* "pick a vector database", and *not*
"write the RAG". It is the task that converts this research into the project's first real asset, and every
other decision in this document is downstream of its output.

**Why this task and not something else.** The investigation produced one decisive finding: the project's
binding constraint is **law + data**, not model capability or architecture. We verified that (a) a
CC0-tagged Jain library of ~1,807 items exists, (b) nobody has audited it, (c) the Sthānakavāsī-specific
digital footprint is effectively zero, and (d) no Prakrit/Gujarati tooling exists. Every architectural
choice in `jain_svk_architecture.md` was made to be *robust to a small corpus*. The cheapest way to find
out whether that was the right call is to measure the corpus for real. Until we do, "should we do CPT?"
is unanswerable, "is 4B the right size?" is unanswerable, and "what does the benchmark contain?" is unanswerable.

### Scope — in

1. **Source registry** (`sources/registry.csv`) seeded from `jain_svk_corpus_manifest.csv`, expanded by
   enumerating the two CC0 collections and the DLI JaiGyan Jain set through the Internet Archive
   `advancedsearch` API (paginated, complete, not sampled).
2. **Licence gate** implementing the deterministic rule set in `jain_svk_license_audit.md` §4, with
   `license_evidence_url`, `pub_year`, `author_death_year`, `rights_verified_by`, `rights_verified_on`
   per item. **Fail-closed.**
3. **Fetch** of the *right* derivative per item (`_djvu.txt` for text; `_djvu.xml`/`_hocr.html` when word
   boxes are needed) with recorded `sha256`. Rate-limited, idempotent, resumable.
4. **Provenance-preserving extraction** into a single Parquet table + a per-item JSON sidecar.
5. **Deduplication** at document and chunk level (exact hash; MinHash/LSH for near-duplicates), including
   the **cross-repository duplicate pairs** that demonstrably exist (same book as a CC0 `kbii-` item and a
   no-licence DLI item). Prefer the better-licensed instance; keep the mapping.
6. **Measurement, not estimation** — the deliverable is a numbers table:
   - total items discovered / licence-passed / rejected, **by reason**
   - total bytes and total extracted characters, **by language and by script**
   - **token counts under the Qwen3.5 tokenizer**, by language and script
   - **tokens-per-word ratio for Ardhamāgadhī vs Gujarati vs Hindi vs Sanskrit vs English** ← this is the
     experiment that decides whether CPT/tokenizer work is justified
   - OCR quality sample: 20 random pages per language, hand-checked, with CER reported
   - Sthānakavāsī-attributable share of the corpus (the number we expect to be small and must not exaggerate)
7. **Publish** `jain-svk-corpus-v0.1` on the Hub (Parquet + `sources.jsonl` + `LICENSE_MAP.csv` +
   dataset card + `NOTICE`), licence **CC BY 4.0**, viewer enabled.
8. **Contamination guard** scaffolded now, even though there is no training yet: a build-time assertion
   that the (future) sealed benchmark IDs are excluded, and a 13-gram overlap checker ready to run.

### Scope — out (explicitly)

OCR re-processing of Gujarati scans · any model training · retrieval implementation · the Gradio Space ·
instruction-data generation · scholar outreach (that runs in parallel and unblocks v0.2, not v0.1).

### Acceptance criteria

- [ ] `sources/registry.csv` covers **every** item returned by the collection queries, with no sampling.
- [ ] Every 🟢 item has `pub_year` **and** `author_death_year` (or an explicit `unknown` + 🟡 verdict).
- [ ] Zero items reach Parquet without `source_id`, `license`, `license_evidence_url`, `sha256`.
- [ ] Re-running the pipeline produces **byte-identical** Parquet (deterministic build hash published).
- [ ] Token-count table published **by language and script**, including the tokens-per-word ratios.
- [ ] OCR CER published for a hand-checked sample, with the Gujarati limitation stated plainly.
- [ ] Every file's `sha256` verified against the source; any mismatch is a hard error.
- [ ] Dataset card states, in the first screen: what is included, what is **NOT** included
      (no Sthānakavāsī-specific corpus, no licensed translations, Gujarati OCR unreliable), and what we
      are asking institutions for.

### Effort and dependencies

3–6 weeks part-time, **zero GPU**, zero cash. Hard dependency: none. Soft dependency: an
institutional contact to request written basis for the CC0 claims (GAP 3) — but the audit can proceed
without it, because pre-1966 works are PD by age regardless of platform metadata.

### First three concrete commits

1. `sources/` — registry schema + IA `advancedsearch` harvester (paginated + resumable) + golden-file test.
2. `license/` — the rule engine from `license_audit.md` §4 as pure functions, with a table-driven test
   suite covering every branch, including the CC0-with-modern-year trap.
3. `extract/` — `_djvu.txt` fetcher + provenance-preserving Parquet writer + determinism test.

---

## §2 · Why not the alternatives (sequenced, not rejected)

| Tempting next task | Why it is second |
| --- | --- |
| Verify Unsloth/GGUF/QLoRA support for the Qwen3.5 architecture | **This is task #2.** It is time-boxed to one day, but it is a *spike*, not a project. It blocks v0.2, not v0.1 |
| Build the hybrid retrieval prototype | Needs the corpus to retrieve from. Building it first means tuning against nothing |
| Generate instruction data | Explicitly forbidden by the brief, and correctly so: without a corpus and without reviewers, we would manufacture the exact hallucination problem this project exists to avoid |
| Reach out to scholars | Runs **in parallel** — start the email on day one — but it is not engineering and it is not the critical path for v0.1 |
| Re-do discovery with a working search engine | Fold into §6 below, as a checklist appended to the registry build. It does not block the pipeline |

---

## §3 · Roadmap after v0.1

| Version | Milestone | Gate |
| --- | --- | --- |
| **corpus-v0.1** | CC0 + PD seeds, provenance-complete, measured | ← **the next task** |
| model-v0.1 | **RAG-only** Jain assistant, no training; hybrid retrieval + citation scaffolding | corpus-v0.1 published |
| bench-v0.1 | Sealed 700-item benchmark, scholar co-written, with the 4-system experiment harness | ≥2 committed reviewers |
| corpus-v0.2 | + human-typed Prakrit core; + verified normaliser; + cross-repo dedup resolved | typing budget secured |
| model-v0.2 | LoRA **SFT** — citation discipline, abstention, sect framing | 3–8k reviewed items |
| model-v0.3 | LoRA **CPT** *(conditional)* | ≥50 M clean tokens **and** measured tokenizer inefficiency |
| model-v1.0 | Architecture D; DPO on reviewer-corrected preference pairs | eval shows S4 > S2 on sect-context and citation metrics |

---

## §4 · Standing decisions to carry forward

1. Publish **corpus, benchmark and provenance** before publishing a model. They are the durable contribution.
2. **No training on any in-copyright Jain text** — not now, not "temporarily to bootstrap".
3. **No synthetic text in the scripture field.** Ever.
4. **No claim of religious authority** in any artefact: model card, dataset card, Space, README, release notes.
5. **Measure and publish negative results** — especially the per-language retrieval gaps and the
   fine-tuning-without-retrieval result (H3). They are the field's most missing information.
6. **Segment by tradition in metadata from line one.** `canon_scope` is not an afterthought.
7. Withdrawal must be possible in under a day: pinned manifests, RAG-first, rebuildable corpus.

---

## §5 · Immediate parallel action (non-engineering, start now)

Send one short, specific, non-extractive letter to:
**(a)** the **A.B. Shree Svetambar Sthanakvasi Jain Conference**;
**(b)** the **Shri Vardhaman Sthanakvasi Jain Shraman Sangh**;
**(c)** Sthānakavāsī pathshalas and monastic presses with published titles.

Ask for exactly three things — no more:

1. The **enumerated list of the 32 āgamas** their tradition accepts (closes GAP 1).
2. A **bibliography** of their in-print and out-of-print publications, with current rights holders.
3. **Named reviewers** (paid, credited, revocable) for citation and sect-attribution review.

Do not ask for bulk scans in the first contact. Ask for the census, then ask for permission title by title.

---

## §6 · Discovery checklist for when search-engine access returns

Run these as a completeness pass over `sources/registry.csv` before freezing `corpus-v0.1`. These are the
queries the API-only investigation could not run:

**Sthānakavāsī-specific (Part 6 list, for completeness and provenance)**
`Sthanakvasi` · `Sthanakvasi Jain` · `Sthanakavasi Agam` · `Śvetāmbara Sthānakavāsī` · `Sthanakvasi Jain Agam` ·
`Sthanakvasi literature` · `Sthanakvasi Jain scriptures` · `Sthanakvasi commentary` · `Sthanakvasi pravachan` ·
`Sthanakvasi Jain books` · `Sthanakvasi Jain texts` · `Sthanakvasi Hindi books` · `Sthanakvasi Gujarati books` ·
`Sthanakvasi Prakrit` · `Sthanakvasi Jain Shastroddhar` · `Akhil Bharat Shvetambar Sthanakvasi Jain
Shastroddhar Samiti` · plus variants `Sthanakwasi`, `Sthanakavasi`, `Sthanakvashi`, `Sthanakvasī`.

**Institutional and press**
A.B. Shree Svetambar Sthanakvasi Jain Conference · Shri Vardhaman Sthanakvasi Jain Shraman Sangh ·
Sthānakavāsī āgama-prakāśana trusts · Gujarati Jain presses in Ahmedabad · Mehsana · Surat · Mumbai ·
Sthānakavāsī periodical runs (smārikā volumes).

**Canon and commentary**
`Ardhamagadhi text` · `Agam mool path` · `Prakrit Jain scripture Unicode` · `Jain agam TEI` ·
`Āgama Suttāṇi` (attribution unverified — establish whether Terapanth or Sthānakavāsī) ·
Nandī · Anuyogadvāra · Dasaveyaliya · Āvassaya · Uttarajjhayaṇa · Āyāraṃga.

**Rights-clean repositories to sweep**
Internet Archive CC0/PD Jain items · GRETIL Jaina + Prakrit sections · OPenn (per-item rights) ·
HathiTrust (PD-only filter) · Zenodo · OpenAlex/academic repositories for Prakrit corpora ·
`ServantsOfKnowledge`/`JaiGyan` intersections.

**Tooling and data gaps to re-check**
`Prakrit embedding model` · `Prakrit tokenizer` · `Ardhamagadhi OCR` · `Gujarati OCR` ·
`Sanskrit OCR` · `Indic document AI` · `Pali/Prakrit parallel corpus` ·
plus a re-check of **`Sthanakvasi` on Hugging Face** (verified zero on 2026-09-17 — re-check at each release).

Record every new hit directly into `sources/registry.csv` with a licence verdict. **A source that is not in
the registry does not exist for this project.**

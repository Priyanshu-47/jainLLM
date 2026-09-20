# Jain Śvetāmbara Sthānakavāsī AI — Research & Architecture Foundation

**Phase:** research → discovery → verification → architecture decision. **No model was trained. Nothing was scraped.**
**Investigation date:** 17 September 2026.

This README is the entry point. Everything below is the answer to *"this is the corpus we have, this is
what we are legally allowed to use, this is the architecture we selected, and this is exactly what we
should build next."*

| Document | Contents |
| --- | --- |
| [`jain_svk_sources.md`](jain_svk_sources.md) | Parts 1–3, 6: tradition hierarchy, textual map, **actual digital assets found**, verified negatives, provenance ledger |
| [`jain_svk_license_audit.md`](jain_svk_license_audit.md) | Part 5: four-gate model, the CC0 trap, per-source verdicts, redistribution matrix, open legal questions |
| [`jain_svk_corpus_manifest.csv`](jain_svk_corpus_manifest.csv) | Parts 4, 24: machine-readable manifest, 38 sources, full field schema |
| [`jain_svk_model_comparison.md`](jain_svk_model_comparison.md) | Parts 8–9, 11–13: 2026 model/embedding/reranker/OCR landscape with elimination reasoning |
| [`jain_svk_architecture.md`](jain_svk_architecture.md) | Parts 10–12, 16–23: architecture decision, Why-over-alternatives, publishing, versioning, costs |
| [`jain_svk_data_pipeline.md`](jain_svk_data_pipeline.md) | Parts 13–15, 17–18: 14-stage pipeline, OCR consensus, dedup, contamination control |
| [`jain_svk_research_gaps.md`](jain_svk_research_gaps.md) | 13 ranked gaps, each with its closing action |
| [`jain_svk_next_steps.md`](jain_svk_next_steps.md) | The single next engineering task, the roadmap, and the search-engine checklist |

**Evidence standard.** Search-engine access failed for the entire session, so discovery ran through
official APIs instead: Hugging Face Hub API + Hub full-text search, GitHub REST API, Internet Archive
`advancedsearch`/`metadata` APIs, PyPI JSON API, and project homepages. This produced *stronger* evidence
than search snippets (licences, dates and download counts read directly from source), but *weaker
coverage*. Items not verified are marked ❓ and listed in `jain_svk_research_gaps.md` §13.

---

## A · What we have

**A CC0-tagged scanned Jain library on Internet Archive, and essentially nothing Sthānakavāsī-specific.**

- ✅ `collection:(ganeshvarnilibrary OR patron-library-collection)` + Jain title/subject → **1,807 items**,
  sampled items carrying **CC0-1.0**. Multiple independent institutional uploaders.
- ✅ The complete ***An Illustrated Ardha Magadhi Dictionary*** (Muni Ratnachandraji, 5 vols, 1923–1938,
  published by the **S. Sthanakwasi Jaina Conference**) — CC0 instances verified for vols 1, 3 and 4.
  **This is a Sthānakavāsī-published Prakrit lexicon, and the highest-value asset found.**
- ✅ *Jain Dharma* (Muni Sushil Kumar, 1958, **A.B.S. Sthānakavāsī Jain Conference Bhavan, New Delhi**) — CC0.
- ✅ 27 Internet Archive items whose text mentions "Sthānakvasi", including Hindi anuvādas of Ācārāṅga,
  Daśavaikālika, Uttarādhyayana and Sūtrakṛtāṅga (1920–1966) — **no licence**.
- ✅ GRETIL's **Prakrit e-text corpus + Jaina section + bulk download**, migrating to TEI — **typed
  Unicode Prakrit**, which removes OCR from the critical path.
- ✅ Modern datasets: `Atma3.1-ShareGPT` (Apache-2.0), `Deshika` Mahārāṣṭrī Prakrit↔English (Apache-2.0).
- ✅ Existing Jain-AI work to study (not to harvest): JainGPT, JainQQ, AI-Yashvi, JLOR, Jainaagam.

**Verified negatives (load-bearing, not incidental):**
🚫 **0** Hugging Face datasets mention Sthānakavāsī · 🚫 **1** GitHub repo matches `sthanakvasi` (a
directory, not a corpus) · 🚫 **6** Internet Archive title matches · 🚫 no open-weight Jain model with
documented training data · 🚫 no Prakrit tokenizer, embedder, or OCR model.

> **The project's starting position is: no Sthānakavāsī corpus, dataset, model or digitisation project
> exists. Everything Sthānakavāsī must be created or newly digitised.** This is materially harder than
> the preliminary research implied, and it is the most important finding in this document.

## B · What we can legally use

Separated by gate, from `jain_svk_license_audit.md` §5:

🟢 **TRAIN (short list, and it is short):** pre-1966 works whose author died before 1966 — including the
CC0 *Ardhamāgadhī Dictionary* instances, the 1958 Sthānakavāsī *Jain Dharma*, the 1910 *Notes on Modern
Jainism*, and the pre-1966 share of the CC0 Jain library. Plus the two Apache-2.0 modern datasets
(⚠️ `GENERIC_JAIN`, not Sthānakavāsī).

🟡 **NEEDS_PERMISSION:** DLI/JaiGyan items (no `licenseurl`, no `rights`, no `possible-copyright-status`
field exists on them — verified), post-1966 CC0-tagged items (**the uploader's CC0 is not credible for
in-copyright works** — the *Jainendra Siddhanta Kosa* 1990 case is the worked example), GRETIL
per-contribution texts, `shethjenil/JainBooks` (no provenance), JLOR, Jainaagam, Jain eLibrary.

🔵 **RAG_ONLY:** GRETIL-*derived* unlicensed derivatives, Wikipedia (**CC BY-SA trailing-ShareAlike
hazard — keep out of the core corpus**).

🟣 **RESEARCH_ONLY:** the Jain-AI systems, OPenn manuscripts (OCR research), the chaturmas directory.

🔴 **DO_NOT_USE:** CC-BY-**ND** material (`JainDharmAurDarshan`) — NoDerivatives forbids every pipeline
step; and AI-generated translations of in-copyright texts.

**The rule that decides most of the corpus:** *copyright is a property of the work, not of the platform's
metadata.* A pre-1966 book by a pre-1966 author is public domain **even where the platform shows no
licence**; a 1990 encyclopaedia is in copyright **even where the platform says CC0**. Both cases are
verified to occur in our target collections.

## C · What is missing

1. **Any Sthānakavāsī corpus at all** — the tradition's own literature is 20th–21st-century Gujarati/Hindi
   print, mostly in copyright, mostly not digitised.
2. **Prakrit everything** — no tokenizer, no embedding model, no OCR model lists it. Reachable only through
   our own normaliser/transliterator plus human-typed core text.
3. **Gujarati OCR** — PaddleOCR has a Devanagari recogniser but **no Gujarati**; archive.org's own
   pipeline mis-detected Gujarati as **Bengali at 46.6% confidence** on one of our target items.
4. **The enumerated 32-āgama list** that defines Sthānakavāsī canonical scope. **Blocking**; must come from
   a scholar, not from inference.
5. **Commentary coverage census** — nobody in the field has one. Building it is a publishable contribution
   in its own right.
6. **High-quality instruction data** — 0 items exist for this sect. Everything must be authored and reviewed.
7. **Scholar relationships** — none exist yet, and they are the rate-limiting step for v0.2+.

## D · Recommended V1 architecture (one, concrete)

**Architecture D, built incrementally as B → C → D.** Hybrid router + three retrieval lanes + citation-aware
reader, shipping first as **RAG-only (`model-v0.1`, no weights)**.

```
router (small) ──┬── safety lane → fixed reviewed template, NO generation
                 └── knowledge lane → metadata pre-filter (tradition, canon_scope, language, text_id, edition)
                                       → BM25 (normalised Prakrit/IAST/Devanagari)
                                       + dense ANN (Qwen3-Embedding-0.6B, MRL 512–1024)
                                       + exact verse/metadata lookup
                                       → RRF fusion → Qwen3-Reranker-0.6B → top-k evidence pack
                                       → Jain-tuned Qwen3.5-4B → answer, every claim cited or refused
```

*Why D over A/B/C:* **A** (pure fine-tune) is eliminated — a model trained on a tiny corpus will invent
sutta numbers, the one failure this project cannot survive. **B** is the right *v0.1 product* but misframes
sect questions. **C** is the naive union without metadata discipline. **D** is the only shape that makes
"which tradition is this from" a retrieval constraint rather than a post-hoc edit.

## E · Recommended base model

- **Primary: `Qwen/Qwen3.5-4B`** — Apache-2.0, 2026-current, free-tier QLoRA-trainable, ships as a ~2.5 GB
  GGUF. **Contingent on a one-day spike** verifying Unsloth/QLoRA/GGUF support for the `qwen3_5` VL architecture.
- **Fallbacks:** `Qwen/Qwen3-8B` (text-only, fully mature toolchain, one generation older) · `google/gemma-4-E4B`
  (**now Apache-2.0** — a real change from Gemma 3) · `sarvamai/sarvam-30b` (the only open LLM with explicit
  `gu` + `sa` tags, at ~4× the cost).
- **Eliminated:** Llama (no `gu`/`sa`, `other` licence, stalled at May 2025), Mistral (weak Indic), sub-1B
  models (cannot hold citation discipline).

## F · Recommended training strategy

**RAG first, then SFT, then CPT only if the data earns it.**

`v0.1` RAG-only, no training → `v0.2` QLoRA **SFT** (3–8k scholar-reviewed items: citation discipline,
abstention, sect framing; ~30% abstention items) → `v0.3` LoRA **CPT** *only if* cleaning yields ≥50 M
tokens **and** the tokenizer measurement shows severe Prakrit/Gujarati inefficiency → `v1.0` + DPO on
reviewer corrections. **Verses are always retrieved, never generated.**

## G · Recommended RAG strategy

Hybrid retrieval with **hard metadata pre-filtering**, over **verse/sutta units** (never fixed-size
windows), with **BM25 as a peer of dense retrieval** — because dense retrieval has no Prakrit support, and
RRF fusion rather than score fusion. LanceDB (Apache-2.0, embedded, versioned) for V1; Qdrant at scale.
The **normaliser/transliterator is the highest-leverage component**, because the Prakrit problem is
fundamentally a representation problem.

## H · Recommended evaluation strategy

A **sealed 700-item benchmark in a separate repo** (factual 150 · verse/citation 200 · sect-context 100 ·
language 100 · hallucination/abstention 100 · safety 50), never trained on, hash-blocked, and checked with
a 13-gram overlap guard on every corpus version bump. Four systems (base / base+RAG / tuned / tuned+RAG),
identical questions, paired bootstrap CIs, two annotators, κ reported. Metrics include verse exactness, CER,
citation precision/recall, per-language recall@10, hallucination rate, abstention correctness,
sect-context accuracy and safety-template adherence. **H3 is stated up front as falsifiable: fine-tuning
without retrieval should NOT improve verse accuracy — if that holds, it is a publishable negative result.**

## I · Estimated resources

| | Estimate (⚠️ engineering estimates, not quotes) |
| --- | --- |
| Storage published | ~20 GB (corpus 1–5 GB · embeddings ~1 GB · index 1–2 GB · merged BF16 ~8 GB · GGUF ~2.5 GB) |
| Local install | ~5 GB |
| Corpus size | 800–1,800 candidate items → **30–120 M usable tokens**, of which **Prakrit < 2 M** and **Sthānakavāsī-specific < 5 M** ⚠️ *must be measured by the next task* |
| GPU | none for corpus work; 1× T4×2 (free tier) for SFT; 1× A100 (paid) only if CPT clears its gate |
| Training hours | SFT 1–4 h · CPT 4–12 h · eval 6–15 h |
| Cash to v1.0 | ⚠️ **~$20–$150** excluding scholar honoraria |
| Inference | CPU-only 4B Q4 ≈ 3–8 tok/s (research-demo grade); GPU Space for a pleasant demo |
| **Real cost** | **scholar review honoraria — budget explicitly, do not defer** |

## J · NEXT ACTION (one task)

> **Build `svk-corpus` v0.1: a reproducible, licence-gated ingest pipeline for the CC0 Internet Archive
> Jain library, ending in a published, provenance-complete corpus manifest with measured token counts.**

3–6 weeks part-time, zero GPU, zero cash. Deliverable: `jain-svk-corpus-v0.1` on the Hub (Parquet +
`sources.jsonl` + `LICENSE_MAP.csv` + dataset card + NOTICE, CC BY 4.0), with **measured** token counts by
language and script, measured tokens-per-word ratios for Ardhamāgadhī/Gujarati/Hindi/Sanskrit/English,
published OCR CER from a hand-checked sample, and a deterministic rebuild hash.

Full scope, acceptance criteria and first three commits: [`jain_svk_next_steps.md`](jain_svk_next_steps.md) §1.

**Why this and not training:** the investigation proved the binding constraint is **law + data**, not model
capability. Until the corpus is measured, "should we do CPT?", "is 4B right?" and "what goes in the benchmark?"
are all unanswerable. This is the cheapest way to turn a research document into a project asset.

---

## Standing decisions

1. Publish **corpus, benchmark and provenance** before publishing a model.
2. **No training on in-copyright Jain text** — not even temporarily to bootstrap.
3. **No synthetic text in the scripture field.** Provenance block on every item.
4. **Never mix traditions silently.** `canon_scope` is mandatory from line one; 45-āgama sources are
   `MURTIPUJAKA`, never Sthānakavāsī.
5. **This is a Jain study/research assistant, not a religious authority.** No artefact may claim otherwise.
6. **Report contradicting evidence.** The biggest example is already in §A: the Sthānakavāsī digital
   footprint is far smaller than assumed, and the large CC0 library skews **Digambara**, not Sthānakavāsī.
7. **Withdrawal must be possible in under a day** — pinned manifests, RAG-first, rebuildable corpus.

## Immediate parallel (non-engineering) action

Send one short letter — to the **A.B. Shree Svetambar Sthanakvasi Jain Conference**, the **Shri Vardhaman
Sthanakvasi Jain Shraman Sangh**, and Sthānakavāsī pathshalas/presses — asking for exactly three things:
the **enumerated 32-āgama list**, a **bibliography with rights holders**, and **named paid reviewers**.
Ask for the census first; ask for scans title by title afterwards.

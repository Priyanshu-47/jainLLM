# jain_svk_model_comparison.md

**Scope:** 2026 open-weight base models, embedding models, rerankers, OCR/VLM stacks, training and
serving libraries — evaluated for one specific job: a **Śvetāmbara Sthānakavāsī Jain study/research
assistant** that must handle **Devanagari, Gujarati, English**, tolerate **Ardhamāgadhī Prakrit**, be
fine-tunable on free/cheap GPUs, and run locally by ordinary users.

All model facts below were read from the Hugging Face Hub API on **2026-09-17** (licence tags, release
dates, download counts) unless marked otherwise. Download counts are 30-day Hub figures and are used only
as an adoption proxy. This document **replaces** the earlier "Qwen + QLoRA" working assumption.

---

## 1. What changed since the preliminary research (this is the headline)

| Change | Evidence | Consequence for us |
| --- | --- | --- |
| **Gemma 4 is Apache-2.0** | `google/gemma-4-26B-A4B-it`, `-31B-it`, `-E4B-it`, `-E2B-it` all tagged `license:apache-2.0` (2026-07-20) | Gemma is now a **first-class permissive candidate**; it was not, as Gemma 3 |
| **Qwen's current generation is 3.5/3.6/3.8, VL-native** | `Qwen/Qwen3.5-4B`, `Qwen3.5-9B` (2026-03-02); `Qwen3.6-35B-A3B` (2026-04); `Qwen3.8-27B` (2026-08-14); all Apache-2.0, tags `image-text-to-text`, arch `qwen3_5` | Newer + better, but **not text-only** → fine-tune/serve tooling must be verified, not assumed |
| **Indic-specialist LLMs exist at scale** | `sarvamai/sarvam-30b` (MoE, Apache-2.0, **`gu`,`hi`,`sa`** tags), `sarvamai/sarvam-105b` (MoE MLA) | First option with **explicit Gujarati + Sanskrit** coverage |
| **Llama has stalled** | Newest public `meta-llama` entries remain **Llama 4 Maverick/Scout, May 2025**; tags list `hi` but **not `gu`/`sa`**; licence `other` | Drop from primary consideration |
| **DeepSeek is strong and permissive** | `DeepSeek-V4-Flash-0731` (2026-08-01, MIT), `DeepSeek-V3.2` (2025-12, MIT) | Excellent **synthetic-data generator**, not a fine-tuning target at our budget |
| **Document-OCR became a VLM task** | chandra-ocr-2, DeepSeek-OCR-2, GLM-OCR, Unlimited-OCR, surya-ocr-2, dots.ocr | OCR stack must be re-planned around VLMs — **but none declare Indic scripts** |
| **jina embeddings v5 exist but are CC-BY-NC-4.0** | `jinaai/jina-embeddings-v5-omni-*` (2026-08-27), `license:cc-by-nc-4.0` | Non-commercial → **excluded from the core stack** |
| **Unsloth is now a desktop app** | PyPI `unsloth` description: *"the first desktop app to run and train models"* | Fine-tuning UX changed; still the fastest QLoRA path |

---

## 2. Candidate base LLMs

Fields marked ⚠️ are **inferred from Hub tags** and must be confirmed against the model card before use.

| Model | Params | Licence | Released | Languages declared | Indic (hi/gu/sa) | Ctx | Tooling maturity | Downloads |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **Qwen/Qwen3.5-4B** | ~4B dense | **Apache-2.0** | 2026-03-02 | not enumerated | ⚠️ (Qwen family is strong on Devanagari) | ⚠️ not read | ⚠️ VL arch (`qwen3_5`) → **verify QLoRA+GGUF** | 7.06M |
| **Qwen/Qwen3.5-9B** | ~9B dense | **Apache-2.0** | 2026-03-02 | not enumerated | ⚠️ | ⚠️ | ⚠️ same risk | 9.34M |
| **Qwen/Qwen3.8-27B** | 27B | **Apache-2.0** | 2026-08-14 | not enumerated | ⚠️ | ⚠️ | ⚠️ too big for free tier | 7.67M |
| **Qwen/Qwen3-8B** | 8B dense | **Apache-2.0** | 2025-04 (7B card updated 2025-07) | not enumerated | ✅ family-known | 32k ⚠️ | ✅ **mature**: Unsloth/TRL/PEFT/vLLM/llama.cpp all proven | 13.10M |
| **Qwen/Qwen3-0.6B** | 0.6B | **Apache-2.0** | 2025-04 | en ⚠️ | ❌ too small for scripture | 32k | ✅ | 22.16M |
| **google/gemma-4-E4B** | ~4B effective | **Apache-2.0** | 2026-07-20 | 140+ langs (Gemma family claim) ⚠️ | ✅ Gemma family covers Indic | ⚠️ | ⚠️ new arch | 4.59M |
| **google/gemma-4-12B-it** | 12B | **Apache-2.0** | 2026-07-20 | ⚠️ | ✅ | ⚠️ | ⚠️ | — |
| **google/gemma-4-26B-A4B-it** | 26B MoE (4B active) | **Apache-2.0** | 2026-07-20 | ⚠️ | ✅ | ⚠️ | ⚠️ MoE fine-tune | 9.46M |
| **sarvamai/sarvam-30b** | 30B MoE | **Apache-2.0** | 2026-03-23 | **en, hi, bn, ta, te, mr, `gu`, kn, ml, pa, or, as, ur, `sa`, ne, sd, kok, mai, doi, mni, sat, ks, bo** | ✅✅ **explicit `gu` + `sa`** | ⚠️ | ⚠️ `custom_code` (trust_remote_code) | 303k |
| **sarvamai/sarvam-105b** | 105B MoE MLA | **Apache-2.0** | 2026-03-10 | same as 30B ✅ | ✅✅ | ⚠️ | ❌ beyond budget | 12k |
| **sarvamai/sarvam-translate** | 4B (Gemma-3-4B base) | **GPL-3.0** | 2026-07-13 | 23 Indic + en, incl. `sa`, `gu` | ✅ | n/a | ✅ | 15.8k |
| **meta-llama/Llama-4-Maverick-17B-128E-Instruct** | ~17B×128E MoE | `other` | 2025-05-22 | ar, de, en, es, fr, **hi**, id, it, pt, th, tl, vi | ❌ no `gu`, no `sa` | ⚠️ | ✅ | — |
| **mistralai/Mistral-Small-3.1-24B** | 24B | Apache-2.0 ⚠️ | 2025-03 | European focus | ❌ weak Indic | ⚠️ | ✅ | — |
| **deepseek-ai/DeepSeek-V4-Flash-0731** | large MoE | **MIT** | 2026-08-01 | ⚠️ | ⚠️ | ⚠️ | ❌ not a fine-tune target here | 4.48M |

### 2.1 Elimination

- **❌ Llama (all)** — 2026-stale, restrictive `other` licence, **no Gujarati and no Sanskrit in the tag set**,
  and a 700M-MAU clause. Eliminated despite tooling maturity.
- **❌ Mistral (all)** — weakest Indic coverage of the major families; nothing it offers beats Qwen/Gemma/Sarvam here.
- **❌ Qwen3-0.6B / 270M-class** — see §3; a scripture assistant at sub-1B cannot hold citation discipline.
- **❌ Sarvam-105B / Qwen3.8-27B / DeepSeek-V4 for fine-tuning** — cost, not quality. Keep DeepSeek as a *data generator*.
- **⚠️ Qwen3-8B** — 2025-vintage, but it is the only large candidate whose **entire** tooling chain
  (Unsloth QLoRA → merge → GGUF → Ollama → vLLM) is known-good. This is the *low-risk* pick.

### 2.2 The decision (full reasoning in `jain_svk_architecture.md`)

**Primary: `Qwen/Qwen3.5-4B`** — Apache-2.0, 2026-current, in the size band that a free Colab/Kaggle
tier can QLoRA, and small enough that a GGUF Q4 build (~2.5 GB) runs on an 8 GB laptop.
**Contingent on a Week-1 spike**: if Unsloth/GGUF support for the `qwen3_5` (VL) architecture is not yet
production-grade, fall back to **`Qwen/Qwen3-8B`** (text-only, fully mature) and re-evaluate at v0.3.
**Alternative with better Indic coverage: `sarvamai/sarvam-30b`** — chosen instead of Qwen3.5 only if the
Indic language-quality gap proves material in evaluation, at ~4× the training and serving cost.
**Gemma 4 (E4B / 12B)** remains the strategic hedge, now that it is Apache-2.0.

---

## 3. Sizing analysis (Part 9) — do not optimise for parameter count

The relevant question is not "how big can we train" but **"what must the weights do that retrieval cannot?"**

| Size | Train on free tier? | Serves on CPU? | GGUF/Ollama | Can hold citation discipline? | Verdict for this project |
| --- | --- | --- | --- | --- | --- |
| **270M–0.6B** | ✅ trivially | ✅ fast | ✅ | ❌ Invents citations; loses format instructions under long contexts | **❌ Not a candidate for the assistant.** ✅ *Useful as a router/classifier* (sect-language detection, query typing) and for CI smoke tests |
| **1–3B** | ✅ Colab T4 | ⚠️ 5–15 tok/s | ✅ | ⚠️ Degrades badly when asked to abstain | ⚠️ Viable only for the **RAG-only** demo with heavy scaffolding, or as the OCR-correction model |
| **4–5B** ← **target band** | ✅ Kaggle T4×2 (30 GB) / Colab L4 | ⚠️ 3–8 tok/s Q4 | ✅ | ✅ Best trade-off: enough capacity for citation format + refusal behaviour | ✅ **V1 fine-tune target** |
| **7–9B** | ✅ Kaggle T4×2, slower | ❌ 1.5–4 tok/s Q4 | ✅ | ✅✅ Stronger grounded multilingual answers | ✅ **Recommended alternative**; also the RAG reader if budget allows two models |
| **14B** | ⚠️ needs 24 GB+; paid GPU | ❌ | ⚠️ | ✅✅ | ❌ Not for V1 |
| **24B+ / 27B / 30B MoE** | ❌ paid GPU only | ❌ | ⚠️ | ✅✅ | ❌ V1; revisit at v1.0 if Indic quality demands it |

**Cost/performance conclusion.** Free-tier QLoRA tops out cleanly around **4–9B**.
Paying for 14B+ buys quality we cannot yet *use*, because our bottleneck is **corpus and evaluation
quality, not model capacity** — we have (verified) essentially no Sthānakavāsī text and no benchmark.
Therefore: **spend the first two quarters on corpus and evaluation, and keep the model in the 4B band.**

Serving cost intuition: a 4B Q4_K_M GGUF is ~2.5 GB and runs on 8 GB RAM; a 9B Q4 is ~5.5 GB and needs
16 GB. For the public demo, CPU-only 4B inference is ~3–8 tok/s — **too slow for a pleasant demo, acceptable
for a research demo with streaming and short answers**, and the reason the demo should be RAG-first with
short, citation-dense answers rather than long essays.

---

## 4. Embedding models (Part 11)

| Model | Dim | Ctx | Licence | Indic coverage | Verdict |
| --- | --- | --- | --- | --- | --- |
| **Qwen/Qwen3-Embedding-0.6B** | ≤1024 (MRL, 32–1024) | **32k** | **Apache-2.0** ✅ | "100+ languages" (not enumerated) ⚠️; instruction-aware ✅ | ✅ **PRIMARY.** MRL lets us cut storage 2–4×; 32k ctx fits whole suttas; Apache-2.0 is clean |
| **Qwen/Qwen3-Embedding-4B / 8B** | 2560 / 4096 | 32k | **Apache-2.0** ✅ | same | ✅ Alternative if recall is short; 8B card = MTEB-multilingual #1 (70.58, Jun 2025) |
| `jinaai/jina-embeddings-v3` | 1024 | 8k | **CC-BY-NC-4.0** ❌ | **declares `gu`, `hi`, `sa`** ✅ | 🟣 Quarantine lane only — NC licence. **Measured baseline for language-coverage debugging**, not shipped |
| `jinaai/jina-embeddings-v5-omni-*` | — | — | **CC-BY-NC-4.0** ❌ | multilingual, multimodal | ❌ Same NC problem, 2026-current |
| `google/embeddinggemma-300m` | 768 | ⚠️ | `gemma` ❌ | Gemma family Indic ✅ | 🟣 Carriage licence + tiny. Diagnostic only |
| `intfloat/multilingual-e5-*`, `BAAI/bge-m3` | 1024 | 512/8k | permissive ⚠️ | widely used multilingual | ⚠️ Still reasonable, but **superseded by Qwen3-Embedding** on multilingual retrieval |
| **Prakrit** | — | — | — | 🚫 **no embedding model lists Prakrit** | **This is the project's modelling gap.** Mitigation: §4.1 |

### 4.1 The Prakrit retrieval problem (and the honest solution)

No 2026 embedding model declares Ardhamāgadhī/Jaina Māhārāṣṭrī. Do not pretend otherwise. Consequences:

1. **Assume vector search underperforms on raw Prakrit** until measured. Measure it: build a
   verse-level retrieval probe (query = a modern-language gloss, target = the correct sutta), and record
   recall@10 for raw Prakrit vs normalised Prakrit.
2. **Normalise before embedding.** Canonical Ardhamāgadhī in Devanagari has rampant orthographic
   variation (`ṃ/ṁ/m̐`, `ṇ/न`, vowel-length variation, sandhi splitting). A deterministic normaliser plus an
   **IAST↔Devanagari↔Gujarati transliteration layer** will move retrieval more than any model swap.
   Index the *normalised* form; display the *original*.
3. **Hybrid retrieval is not optional.** Because dense retrieval is the weak link for Prakrit, **lexical
   BM25 over normalised Prakrit + IAST + Devanagari is required**, not a nice-to-have.
4. **Fine-tune the embedder only when there is data to fine-tune on.** A verse-aligned parallel set
   (Prakrit ↔ Hindi/Gujarati/English) — which we will build from PD editions — is exactly the needed
   training signal for MultipleNegativesRankingLoss. This is a v0.3 task, not v0.1.
5. **Late interaction (ColBERT-style) is deferred.** Verified multilingual late-interaction options are
   either CC-BY-NC (jina-colbert lineage) or English-centric. Cost/benefit does not justify it before the
   corpus exists.

---

## 5. Rerankers

| Model | Licence | Notes | Verdict |
| --- | --- | --- | --- |
| **Qwen/Qwen3-Reranker-0.6B** | **Apache-2.0** ✅ | 32k ctx, instruction-aware, pairs with Qwen3-Embedding-0.6B | ✅ **PRIMARY** — cheap enough to run in the same process |
| `Qwen/Qwen3-Reranker-4B` | Apache-2.0 ✅ | 2.53M downloads | ⚠️ Use only if the 0.6B reranker underperforms on the eval set |
| `BAAI/bge-reranker-v2-m3` | **Apache-2.0** ✅ | 18.0M downloads — the incumbent; multilingual | ✅ **Baseline to beat.** Keep as the A/B control |
| `jinaai/jina-reranker-v3` | ⚠️ (CC-BY-NC on sibling models) | Qwen3-0.6B-based, 2026-08 | 🟣 Verify licence before use |
| `Alibaba-NLP/gte-reranker-modernbert-base` | Apache-2.0 | **English-only** | ❌ Multilingual requirement fails |

---

## 6. OCR / document-understanding stack (Part 13)

Verified `search=ocr` ranking on the Hub (downloads, 2026-09-17):

| Model | Licence | Base/arch | Declared languages | Indic? |
| --- | --- | --- | --- | --- |
| `datalab-to/chandra-ocr-2` | `openrail` ⚠️ | `qwen3_5` VLM, 2026-06 | — | ❌ none declared |
| `baidu/Unlimited-OCR` | **MIT** ✅ | custom VL, 2026-07 | "multilingual" | ❌ none named |
| `zai-org/GLM-OCR` | **MIT** ✅ | `glm_ocr`, 2026-09-11 | zh, en, fr, es, ru, de, ja, ko | ❌ none named |
| `deepseek-ai/DeepSeek-OCR-2` | **Apache-2.0** ✅ | `deepseek_vl_v2`, 2026-02 | "multilingual" | ❌ none named |
| `datalab-to/surya-ocr-2` (+GGUF) | `openrail` ⚠️ | `qwen3_5`, 2026-05 | — | ❌ |
| `dots-studio/dots.ocr` | **MIT** ✅ | custom, 2025-10 | en, zh, "multilingual" | ❌ |
| `PaddlePaddle/devanagari_PP-OCRv5_mobile_rec` | **Apache-2.0** ✅ | PP-OCRv5 line recogniser | en + Devanagari script | ✅ **Devanagari line rec only** |
| `PaddlePaddle/PP-OCRv5_server_det` | Apache-2.0 ✅ | text-line **detection** | language-agnostic | ✅ detection stage |
| `umangchaudhari/gujarati-ocr` | Apache-2.0 ✅ | viT+decoder, 2026-03 | `gu` | ✅ **Gujarati — but ~305 downloads, unproven** |
| `kailasa-ngpt/gemma-4-31b-tamil-devanagari-ocr` | Apache-2.0 ✅ | Gemma-4-31B VLM LoRA, 2026-08 | ta, **devanagari, sanskrit** | ✅ emerging, tiny adoption |
| `enclavelabs/enclave-scribe-devanagari` | MIT ✅ | LoRA on `allenai/olmOCR-2-7B-1025` | hi, mr, **sa**, ne | ✅ emerging |
| Tesseract 5 (`guj`, `hin`) | Apache-2.0 | classic | many | ⚠️ **verified to mis-detect script on our actual target material** |

### 6.1 Verdict

**There is no production-grade Gujarati + Devanagari + Sanskrit document-OCR stack in 2026.** The 2026
VLM-OCR leaders (chandra-ocr-2, Unlimited-OCR, GLM-OCR, DeepSeek-OCR-2) advertise "multilingual" but
**declare no Indic script** — which for a project like this must be read as "untested on our scripts".

Therefore the OCR design is a **consensus pipeline with human gating**, not a single model call:

```
scan → deskew/denoise/binarise → layout+line detection (PP-OCRv5 det or VLM layout)
     → TWO independent recognisers (e.g. PP-OCRv5-devanagari rec  +  a 2026 VLM-OCR)
     → normalisation to one script (Devanagari) + Unicode NFC
     → agreement scoring; auto-accept only on exact post-normalisation agreement
     → disagreement → human queue (this is where Sthānakavāsī reviewers work)
     → character/language validation against an Ardhamāgadhī lexicon built from the CC0 dictionaries
```

**And the strategic conclusion:** for V1, **do not OCR anything you can type instead.**
The CC0 Ardhamāgadhī Dictionary volumes are the only high-value Prakrit lexical asset we have and they
are **scans**. Typing ~1,000–2,000 key entries + the 32-āgama mūla-pāṭha manually is slow but finite, and
it produces ground truth that makes every downstream OCR project measurable. A small, verified, hand-typed
core beats a large unverified OCR pile.

---

## 7. Training and serving libraries (2026 status)

| Library | Status verified | Notes |
| --- | --- | --- |
| **Unsloth** (`pypi: unsloth`) | Active; **now ships a desktop app** ("first desktop app to run and train models") + free notebooks; advertises Qwen3.8 support | ✅ **Primary QLoRA path.** Add for Qwen3.5-arch support as Week-1 spike |
| **TRL** (`SFTTrainer`, `DPOTrainer`) | Canonical HF SFT/DPO | ✅ Use for reproducibility scripts; the "source of truth" config |
| **PEFT** | Canonical LoRA/QLoRA | ✅ Always used underneath |
| **bitsandbytes** | 4-bit NF4 | ✅ Needed for QLoRA on T4/L4 |
| **llama.cpp / GGUF** | Canonical CPU/edge inference | ✅ Required for the "ordinary user runs it" requirement |
| **Ollama** | Canonical local UX | ✅ Ship a Modelfile |
| **vLLM** | Canonical GPU serving | ✅ For the Space/demo backend if GPU is attached |
| **sentence-transformers / FlagEmbedding** | Canonical embedding+rerank UX | ✅ |
| **datatrove (HF) + text-dedup / datasketch / `deduplicate-text-datasets`** | Canonical large-scale cleaning + near-dedup | ✅ See `jain_svk_data_pipeline.md` |

**Note the trade-off I am accepting:** Qwen3.5 is 2026-current and Apache-2.0, but its architecture is
VL-native. Every tool in the list above is strongest on **text-only dense** architectures. Hence the
Week-1 spike: *verify before committing*. If the spike fails, Qwen3-8B costs one generation of quality and
buys a fully proven chain — which is the right trade for a project whose bottleneck is data.

---

## 8. Summary recommendation table

| Layer | Pick | Runner-up | Why (short) |
| --- | --- | --- | --- |
| Base LLM | **Qwen3.5-4B** (Apache-2.0) | Qwen3-8B; Gemma-4-E4B; Sarvam-30B | 2026-current, permissive, free-tier trainable, GGUF-able |
| Embedder | **Qwen3-Embedding-0.6B** | Qwen3-Embedding-4B | Apache-2.0, MRL, 32k ctx, multilingual |
| Reranker | **Qwen3-Reranker-0.6B** | bge-reranker-v2-m3 | Apache-2.0, same family, cheap |
| Lexical | **BM25 over normalised Prakrit + IAST + Devanagari** | — | Dense retrieval is weak on Prakrit by construction |
| OCR | **PP-OCRv5-det + PP-OCRv5-devanagari-rec + one VLM-OCR, consensus-gated** | Tesseract `guj` | No production Indic stack exists; consensus + human review is the only defensible design |
| Human-typed Prakrit core | **Non-negotiable** | — | Ground truth for the whole pipeline |
| Data generator | **DeepSeek-V4-Flash-0731 (MIT)** or GLM/Qwen3.8 | Gemma-4-31B | Permissive licence for a *dataset-generating* role |

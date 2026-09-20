# Task 15 — Training & Architecture Requirements Audit

**Date:** 2026-09-18 · **Scope:** What to learn vs. retrieve, training feasibility, corpus composition analysis, future dataset design, architecture candidates, model requirements, CPT justification gates, staged progression. Ends with architecture decision deferred.

---

## 1. Corpus Composition Summary (measured)

### 1.1 Release products

| Product | Units | Characters | Words | Tokens (Sarvam-30B) |
|---------|-------|------------|-------|---------------------|
| RAG corpus | 145,147 | 14,520,043 | 2,522,200 | 5,082,699 |
| Training corpus | 82,470 | 13,589,439 | 2,326,455 | 4,560,988 |
| Low-quality (withheld) | 126,605 | 16,244,481 | — | — |

**Key fact:** 28 of 62 catalogued sources were released. 34 sources remain gated (WITH_CONDITIONS, NEEDS_PERMISSION, UNKNOWN, or NOT_ALLOWED).

### 1.2 Language balance (training corpus, measured)

| Language | Characters | % of training | Tokens (Sarvam-30B) |
|----------|-----------|---------------|---------------------|
| English | 9,143,876 | 67.3% | 2,484,208 |
| Gujarati | 1,539,396 | 11.3% | 786,501 |
| Devanagari (hi) | 341,570 | 2.5% | 151,217 |
| Unknown | 2,564,597 | 18.9% | 1,139,062 |

**Implication:** The training corpus is ~67% English. Any model trained on this will primarily learn English Jain content, not Gujarati or Hindi Sthānakavāsī content.

### 1.3 Sect balance (training corpus, measured)

| Sect | Characters | % of training | Tokens (Sarvam-30B) |
|------|-----------|---------------|---------------------|
| STHANAKAVASI | 1,366,569 | 10.1% | 749,281 |
| GENERIC_JAIN | 4,670,942 | 34.4% | 955,676 |
| SVETAMBARA | 1,050,816 | 7.7% | 291,101 |
| MULTI_TRADITION | 1,019,255 | 7.5% | 325,823 |
| Unknown | 5,481,857 | 40.3% | 2,239,107 |

**Implication:** Only ~10% of training tokens are explicitly tagged Sthānakavāsī. The majority of the corpus is generic Jain or unclassified.

### 1.4 Source type balance (training corpus, measured by dominant source)

| Source type | Dominant source | Training tokens (Sarvam-30B) | % of training |
|-------------|----------------|------------------------------|---------------|
| Prakrit-Hindi lexicon | SVK-2006/2007 (Paia-sadda-mahannavo) | 737,047 + 232,456 = 969,503 | 21.3% |
| Ardha-Magadhi dictionaries | SVK-2002/2003/2004/2005/0007/0037 | ~1,200,000 (aggregate) | ~26% |
| Generic Jain instruction | SVK-0026 (Atma Siddhi Shastra) | 955,676 | 20.9% |
| Western scholarship | SVK-1005/1007/1008/1009 | ~870,000 | ~19% |
| Canon translations (English) | SVK-1001/1002/1003 | ~291,000 | ~6.4% |
| Sthānakavāsī sect literature | SVK-2010 | 33,324 | 0.7% |

**Implication:** The training corpus is dominated by Prakrit lexicographic material (~47%) and English secondary scholarship (~25%). Direct Sthānakavāsī doctrinal content is <1%.

### 1.5 CPT eligibility (measured)

| Metric | Value | Threshold | Verdict |
|--------|-------|-----------|---------|
| Clean training tokens | 4,560,988 | 50,000,000 | **0.091× threshold** |
| CPT eligible | **NO** | — | — |

**Caveats from tokenizer_measurements.json:**
- The 50M figure is this project's adopted heuristic, not a scientific constant
- Token count alone cannot justify CPT: duplication rate, provenance quality, language balance and script coverage all have to hold too
- A corpus dominated by one language cannot teach the others
- Below the threshold the correct move is RAG plus a small, verified SFT set

---

## 2. What to Learn vs. What to Retrieve

### 2.1 Content classification

| Content type | In corpus? | Learn or retrieve? | Rationale |
|--------------|-----------|-------------------|-----------|
| Prakrit lexicon entries | Yes (~47% of training) | **Retrieve** | Dictionary lookups are factual; retrieval is more reliable than parametric memory for exact headword-to-gloss mappings |
| Ardha-Magadhi grammar rules | Partial (Woolner's Introduction to Prakrit) | **Retrieve** | Grammar rules are precise and must not be hallucinated; retrieval guarantees exact citation |
| Sthānakavāsī doctrinal positions | Minimal (<1% training tokens) | **Retrieve** | Insufficient training data to learn reliably; retrieval over verified sources is the only honest path |
| Generic Jain philosophy | Yes (~35% of training) | **Hybrid** | Background knowledge for context; SFT on Q&A pairs can teach style/tone while retrieval handles factual accuracy |
| Canon translation content | Yes (~6% of training) | **Retrieve** | English translations of āgamas are reference material; must cite specific passages, not paraphrase |
| Western scholarship | Yes (~19% of training) | **Retrieve** | Secondary sources; must be cited, not internalised as authority |
| Sthānakavāsī practice/liturgy | No (not yet acquired) | **Retrieve** | Not in corpus; if acquired, still retrieval (liturgy must be exact) |
| Sectarian distinctions | Minimal | **Retrieve** | Critical to get right; no room for parametric ambiguity about which sect holds what |

### 2.2 What could be learned (SFT candidates)

| Task | Data available? | Feasibility |
|------|----------------|-------------|
| Sect-aware Q&A (answer in Sthānakavāsī voice) | Minimal | **Low** — insufficient verified Q&A pairs |
| Source citation generation | Partial (retrieval system provides evidence) | **Medium** — can generate citation-form from retrieval evidence |
| Prakrit term explanation | Yes (lexicon entries) | **Medium** — dictionary entries can be reformatted as explanations |
| Gujarati Devanagari script bridging | Partial (Gujarati OCR output exists) | **Low** — OCR quality is the bottleneck |
| Multi-lingual gloss mapping | Yes (quadrilingual dictionaries) | **High** — parallel entries in pra/sa/gu/hi are natural training pairs |

---

## 3. Training Approach Feasibility

### 3.1 Continued Pre-Training (CPT)

**Verdict: NOT ELIGIBLE**

| Gate | Status | Evidence |
|------|--------|----------|
| Token count ≥ 50M | FAIL (4.56M) | 0.091× threshold |
| Language diversity | FAIL | 67% English |
| Sect diversity | FAIL | 10% Sthānakavāsī |
| Duplication rate | UNKNOWN | Not measured |
| Provenance quality | MIXED | Some high, some medium |

**Recommendation:** Do not attempt CPT. The corpus is an order of magnitude too small and too skewed. CPT at this scale would not move the model's domain behaviour meaningfully, and would consume compute budget with negligible return.

### 3.2 Supervised Fine-Tuning (SFT)

**Verdict: CONDITIONALLY ELIGIBLE — but requires new data**

| Gate | Status | Evidence |
|------|--------|----------|
| SFT dataset exists | NO | No verified Q&A pairs, no instruction-following examples |
| Task definition | PARTIAL | Can define tasks (citation, gloss mapping, sect-aware answering) but no gold data |
| Base model selection | DEFERRED | Architecture decision pending |

**What would need to exist:**
1. 500–2,000 verified Sthānakavāsī Q&A pairs (question → sourced answer with citation)
2. 200–500 Prakrit term → explanation pairs (from lexicon entries)
3. 100–300 sect-distinction pairs (e.g., "How does Sthānakavāsī differ from Mūrtipūjaka on image worship?" → verified answer)

**These do not yet exist in the corpus.** The pipeline can generate candidate pairs from existing data, but each requires human verification before use in SFT.

### 3.3 Direct Preference Optimisation (DPO) / RLHF

**Verdict: NOT ELIGIBLE**

No preference data exists. DPO/RLHF requires verified preferred/dispreferred response pairs. This is a later-stage activity that presupposes a working SFT model.

---

## 4. Future Dataset Design

### 4.1 What the corpus should become (v0.2+ targets)

| Gap | Current state | v0.2 target | How |
|-----|--------------|-------------|-----|
| Sthānakavāsī sect content | 10.1% of training tokens | ≥30% | Ingest SVK-0002 (Jain Dharma, NEEDS_PERMISSION), SVK-0008, SVK-0009, SVK-0020 (Pathshala textbook) |
| Gujarati-language content | 11.3% of training chars | ≥25% | Ingest SVK-0010 (Jain Sathan Kavasi), SVK-2010–2014 (all Gujarati pre-1930) |
| Hindi-language content | 2.5% of training chars | ≥10% | Ingest SVK-0012–0017 (Hindi āgama translations, all WITH_CONDITIONS) |
| Verified Q&A pairs for SFT | 0 | ≥500 | Human-authored or pipeline-generated + verified |
| Prakrit parallel pairs | 2,417 RAG units (SVK-0027) | ≥5,000 | Expand from GRETIL (SVK-0022/0023) if rights cleared |
| Dense retrieval capability | Unavailable | Installed | Install embedding model + FAISS/NumPy |

### 4.2 Dataset format for future SFT

```json
{
  "instruction": "What is the Sthānakavāsī position on image worship?",
  "input": "",
  "output": "The Sthānakavāsī tradition rejects mūrti-pūjā (image worship) and the necessity of temples, holding that religious practice belongs in a sthanak (secular meeting-hall). This position was established by Lava of Surat in the 17th century, following the reformer Loṅkā Śāh. [Source: SVK-0038, Notes on Modern Jainism, 1910, p. 45]",
  "source_ids": ["SVK-0038"],
  "sect": "STHANAKAVASI",
  "language": "en",
  "verification_status": "human_verified"
}
```

### 4.3 Dataset format for Prakrit gloss pairs

```json
{
  "instruction": "Define the Prakrit term 'ahiṃsā' as used in Jain doctrine.",
  "input": "",
  "output": "ahiṃsā (अहिंसा): non-violence; the foundational Jain ethical principle that all living beings are inviolable. In the Ardha-Magadhi lexicon, the term appears under the headword ahiṃsā with the gloss 'not to injure any living creature'. [Source: SVK-2002, Ardha-Magadhi Dictionary, Gujarati ed.]",
  "source_ids": ["SVK-2002"],
  "language": "pra",
  "verification_status": "pipeline_generated_needs_verification"
}
```

---

## 5. Architecture Candidates

### 5.1 Summary of candidates (from jain_svk_architecture.md)

| Architecture | Description | Compute cost | Sthānakavāsī fidelity | Open questions |
|-------------|-------------|-------------|----------------------|----------------|
| **A: Pure retrieval** | BM25 + RAG, no fine-tuning | Lowest | Medium — relies on retrieval quality | Dense retrieval unavailable; source metadata channel helps |
| **B: Retrieval + prompt engineering** | A + structured prompts | Low | Medium-High — prompts can enforce sect-awareness | Prompts are fragile; not robust to distribution shift |
| **C: Retrieval + SFT** | B + supervised fine-tuning on verified Q&A | Medium | High — model learns sect-specific voice | No SFT dataset exists yet; must be built |
| **D: Hybrid router + retrieval + tuned model** (target) | Router selects retrieval strategy; model is C-tuned | Highest | Highest — combines parametric knowledge with retrieval | Requires all prior stages to succeed |

### 5.2 Architecture decision

**Status: DEFERRED**

The architecture decision cannot be made until:
1. Repository audit is complete (this document contributes to it)
2. External research on Indic LLM fine-tuning is conducted
3. Rights outreach results are known (determines corpus size)
4. SFT dataset feasibility is assessed

**What can be said now:**
- Architecture A (pure retrieval) is the only immediately deployable option
- Architecture D remains the target but requires corpus expansion + SFT data + dense retrieval
- The gap between current corpus and Architecture D requirements is large

---

## 6. Model Requirements

### 6.1 Base model requirements (from architecture research)

| Requirement | Minimum | Ideal | Current candidates |
|-------------|---------|-------|-------------------|
| Gujarati script support | Yes | Native Gujarati tokenizer | Sarvam-30B (✅), Qwen3 (✅), Gemma 3/4 (✅) |
| Sanskrit support | Yes | Native Devanagari tokenizer | Sarvam-30B (✅), Qwen3 (✅) |
| Hindi support | Yes | Native Devanagari tokenizer | Sarvam-30B (✅), Qwen3 (✅), Gemma 3/4 (✅) |
| English support | Yes | Native | All candidates (✅) |
| Open-weight licence | Apache-2.0 or equivalent | Apache-2.0 | Sarvam-30B (Apache-2.0), Qwen3 (Apache-2.0), Gemma 4 (Apache-2.0) |
| QLoRA trainable | Yes | — | All candidates (✅) |
| Dense retrieval compatible | Preferred | Same tokenizer family | Qwen3-Embedding-0.6B shares tokenizer with Qwen3 |

### 6.2 Tokenizer efficiency (measured)

| Tokenizer | RAG tokens | Training tokens | Tokens/word | Tokens/char |
|-----------|-----------|----------------|-------------|-------------|
| Sarvam-30B (primary) | 5,082,699 | 4,560,988 | 1.96 | 0.336 |
| Qwen3-0.6B | 8,182,054 | 7,392,115 | 3.18 | 0.544 |
| Gemma-3-4B | 5,159,251 | 4,631,872 | 1.99 | 0.341 |
| Qwen3.5-4B | 6,754,902 | 6,062,098 | 2.61 | 0.446 |

**Sarvam-30B is the most token-efficient** for this corpus (fewest tokens per word/character). Its larger vocabulary (262K vs Qwen3's 151K) better covers the multilingual content.

### 6.3 Dense retrieval tower compatibility

| Candidate | Tokenizer shared with base? | Gujarati support | Status |
|-----------|---------------------------|------------------|--------|
| Qwen3-Embedding-0.6B | ✅ Same as Qwen3-0.6B | ✅ | Available |
| Sarvam embedding | ❓ Not found | ✅ (expected) | Not measured |
| BGE-M3 | ❌ Different | ✅ | Not measured |

**If the base model is Qwen3**, Qwen3-Embedding-0.6B is the natural retrieval tower (shared tokenizer, same vocabulary). If the base is Sarvam-30B, a Sarvam embedding model or BGE-M3 would need evaluation.

---

## 7. CPT Justification Gates

### 7.1 Gate checklist

| Gate | Current status | Required for CPT |
|------|---------------|------------------|
| Clean tokens ≥ 50M | ❌ 4.56M (0.091×) | ≥50M |
| Language distribution | ❌ 67% English | ≥3 languages at >10% each |
| Sect distribution | ❌ 10% Sthānakavāsī | ≥25% target sect |
| Duplication rate | ❓ Unknown | <5% duplicate characters |
| Provenance grade | ⚠️ Mixed (some medium) | ≥80% high-grade |
| Script coverage | ⚠️ Devanagari + Latin + Gujarati | All target scripts |
| Rights clearance | ⚠️ 28/62 sources released | ≥40 sources released |

### 7.2 What would make CPT viable

To reach the 50M token threshold, the corpus would need approximately:
- 10× current size (45M → 500M tokens would be comfortable)
- OR: focus on high-density sources (lexicons, dictionaries) that provide more tokens per source
- OR: acquire the large CC0 Jain library (SVK-0001, 1807 items) — but it skews Digambara/generic-Jain, not Sthānakavāsī

**Realistic assessment:** CPT is unlikely to become viable for this project. The Sthānakavāsī-specific corpus is inherently small (the tradition has a limited digitised出版物). The correct strategy is RAG + SFT, not CPT.

---

## 8. Staged Training/Evaluation Progression

### Stage 0: Current state (v0.1)
- **Retrieval:** BM25 + source metadata channel (no dense)
- **Model:** No model trained
- **Corpus:** 28 sources, ~5M RAG tokens, ~4.5M training tokens
- **Deployment:** N/A (infrastructure only)

### Stage 1: Retrieval deployment
- **Prerequisites:** Dense retrieval installed; full test suite passing
- **Actions:**
  1. Install Qwen3-Embedding-0.6B or Sarvam embedding for dense retrieval
  2. Install FAISS/NumPy for vector operations
  3. Rebuild index with dense channel enabled
  4. Re-freeze evaluation baseline at combined C policy (Task 13)
  5. Deploy retrieval API (HTTP or CLI)
- **Exit criteria:** Dense + BM25 hybrid achieves R@10 ≥ 0.90 on eval set

### Stage 2: Corpus expansion
- **Prerequisites:** Rights outreach results known
- **Actions:**
  1. Ingest cleared sources (SVK-0002, SVK-0008, SVK-0009, SVK-0020, etc.)
  2. Process GRETIL Prakrit texts (SVK-0022/0023) if rights cleared
  3. Build SFT candidate dataset from pipeline outputs
  4. Human-verify 500+ Q&A pairs
- **Exit criteria:** Training corpus ≥15M tokens; SFT dataset ≥500 verified pairs

### Stage 3: SFT model
- **Prerequisites:** Stage 2 complete; base model selected
- **Actions:**
  1. Select base model (Qwen3-4B or Sarvam-30B recommended)
  2. Run SFT on verified Q&A pairs
  3. Evaluate on held-out sect-awareness test set
  4. Compare retrieval-only vs retrieval+SFT
- **Exit criteria:** SFT model outperforms retrieval-only on sect-distinction questions

### Stage 4: Architecture D (hybrid router)
- **Prerequisites:** Stage 3 complete; router logic designed
- **Actions:**
  1. Implement router that selects retrieval strategy per query type
  2. Combine parametric knowledge (from SFT) with retrieval evidence
  3. End-to-end evaluation on full query set
- **Exit criteria:** Architecture D outperforms Stage 3 on comprehensive evaluation

### Evaluation metrics (all stages)

| Metric | Stage 0 | Stage 1 target | Stage 3 target | Stage 4 target |
|--------|---------|---------------|---------------|---------------|
| R@10 | 0.895 | ≥0.90 | ≥0.92 | ≥0.95 |
| MRR | 0.905 | ≥0.91 | ≥0.93 | ≥0.95 |
| Sect accuracy | N/A | N/A | ≥85% | ≥90% |
| Source citation accuracy | N/A | N/A | ≥80% | ≥90% |
| Gujarati query support | ❌ | Partial | ✅ | ✅ |

---

## 9. Blocking Items

| Blocker | Impact | Mitigation |
|---------|--------|------------|
| Dense retrieval unavailable | Cannot build hybrid index | Install embedding model + FAISS (Stage 1) |
| No SFT dataset | Cannot train SFT model | Build from pipeline outputs + human verification (Stage 2) |
| Rights outreach pending | 34 sources remain gated | Continue outreach; use what we have for Stage 0–1 |
| 32 āgamas enumeration incomplete | Cannot verify canonical scope | Research task; blocks accurate canonical metadata |
| OCR quality for Gujarati scripts | SVK-0008 shows script confusion | Measure OCR quality per source before trusting |
| No base model selected | Cannot begin training | Architecture decision deferred to after repository audit |

---

## 10. Architecture Decision

**DEFERRED**

This document establishes that:
1. CPT is not viable (corpus too small, too skewed)
2. SFT is conditionally viable but requires new dataset creation
3. RAG (Architecture A) is immediately deployable
4. Architecture D remains the target but requires significant corpus expansion
5. The base model decision depends on: (a) tokenizer compatibility with Gujarati/Devanagari, (b) QLoRA trainability, (c) dense retrieval tower compatibility, (d) licence terms

The decision will be made after:
- External research on Indic LLM fine-tuning best practices
- Rights outreach results (determines corpus ceiling)
- Dense retrieval feasibility measurement
- Repository audit completion

---

**Measured vs interpretation:** §1 and §6.2 numbers are measured from tokenizer_measurements.json and corpus_manifest.json. §2, §3, §4, §5, §7, §8, §9 are engineering analysis. §10 is a project decision, not a technical measurement.

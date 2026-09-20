# jain_svk_architecture.md

**This is the decision document.** It answers Parts 10–12, 20–23 and the final deliverables D–I.

---

## 1. Architecture comparison (Part 10)

| | A — Pure fine-tuned LLM | B — RAG only | C — Fine-tune + RAG | **D — Hybrid (router + hybrid retrieval + tuned model)** |
| --- | --- | --- | --- | --- |
| Factual accuracy | ❌ hallucination-prone; Sthānakavāsī niche is tiny in pretraining | ✅ grounded | ✅✅ | ✅✅ |
| Citation accuracy | ❌ cannot cite what it memorised | ✅✅ cites retrieved spans | ✅✅ | ✅✅ |
| Verse-level exactness | ❌ | ✅✅ byte-exact from corpus | ✅✅ | ✅✅ |
| Corpus updates without retraining | ❌ | ✅✅ | ✅ | ✅✅ |
| Sect-context correctness | ❌ blends traditions | ✅ metadata filters | ✅ | ✅✅ (filter + router) |
| Cost to build | ⚠️ high (needs large clean corpus) | ✅ lowest | ⚠️ medium | ⚠️ medium |
| Cost to run | ✅ lowest | ⚠️ retrieval overhead | ⚠️ | ⚠️ |
| Verifiability / auditability | ❌ opaque | ✅✅ traceable to source | ✅✅ | ✅✅ |
| Legal exposure | ❌ every memorised token is a liability | ✅ only retrieves what we are allowed to hold | ✅ | ✅ |
| Works with our verified corpus? | ❌ **No — we have too little clean text** | ✅ | ✅ | ✅ |

**Eliminations.** **A** is eliminated: we verified that the Sthānakavāsī-specific clean corpus is
near-zero, and a fine-tuned model trained on ~50 M tokens will confidently invent sutta numbers, which is
the one failure mode this project cannot survive. **B** is eliminated as the *end state* because a
generic model mis-frames Jain questions sect-wise and does not reliably emit the citation discipline we
need — but B is the right **v0.1 shippable product**. **C** is the naive union.

### ✅ Target architecture: **D, built incrementally via B → C → D**

```
                     ┌───────────────────────────────────────────────┐
                     │  QUERY CLASSIFIER / ROUTER  (small, ~0.5B)    │
                     │  language · query-type · sect-scope · safety  │
                     └───────┬───────────────────────┬───────────────┘
                             │                       │
             ┌───────────────▼──────┐      ┌─────────▼───────────────┐
             │ SAFETY LANE          │      │ KNOWLEDGE LANE           │
             │ fasting · health ·   │      │                          │
             │ sallekhana/santhara ·│      │  ┌── metadata filter (tradition, canon_scope,
             │ ritual · personal    │      │  │    language, text_id, edition)
             │ → fixed template,    │      │  ├── BM25 (normalised Prakrit/IAST/Devanagari)
             │   no generation      │      │  ├── dense ANN (Qwen3-Embedding-0.6B, MRL 512–1024)
             └──────────────────────┘      │  └── metadata/structured lookup (verse index)
                                           │              ↓
                                           │      RRF fusion → cross-encoder rerank
                                           │      (Qwen3-Reranker-0.6B) → top-k
                                           │              ↓
                                           │      EVIDENCE PACK (verbatim spans + inline
                                           │      citations + tradition tags)
                                           └──────────────┬───────────
                                                          ↓
                                    JAIN-TUNED READER MODEL (Qwen3.5-4B, LoRA)
                                    · answers ONLY from the evidence pack
                                    · every claim carries a citation or an explicit abstention
                                    · returns tradition-scoped framing ("in the Sthānakavāsī
                                      reading…") and refuses to adjudicate disputes
                                                          ↓
                                    Citation-aware answer + provenance footer
                                    (source_id · edition · verse ref · licence · verification status)
```

**Why the three lanes rather than one pipeline:**
1. **Metadata filtering must precede retrieval**, because our hardest correctness problem is sect
   confusion (32 vs 45 āgamas; Sthānakavāsī vs Terapanth vs Digambara). Filtering *before* ranking
   makes "which tradition is this from" a first-class retrieval constraint rather than a post-hoc edit.
2. **Exact text retrieval must be a peer of vector retrieval**, because dense models do not cover
   Prakrit (verified: no embedding model declares Prakrit). A dense-only pipeline would silently fail on
   the tradition's own canonical language.
3. **The safety lane must bypass generation entirely.** Fasting, sallekhana/santhara, health and ritual
   questions get a fixed, reviewed template. This is a design constraint from the project's own rules,
   and it is far easier to guarantee with a router bypass than with prompt instructions.

---

## 2. Retrieval technology (Part 11)

### 2.1 Chosen stack

| Component | Choice | Why over alternatives |
| --- | --- | --- |
| **Normalisation/transliteration layer** | Deterministic rules: Unicode NFC; IAST ↔ Devanagari ↔ Gujarati; Ardhamāgadhī orthographic variant folding; Prakrit sandhi-aware tokenisation | This is the highest-leverage retrieval component and the only one that addresses Prakrit directly. No off-the-shelf model solves it |
| **Lexical** | **BM25** over normalised text, indexed in the vector store's own FTS (e.g. LanceDB FTS / Tantivy) with custom analysis | Verified: no Indic-aware stemmer exists for Gujarati/Prakrit in mainstream IR stacks → use Unicode normalisation + character n-grams to absorb inflection, and tune `k1`/`b` empirically. Character n-grams are the honest workaround for a language without stemming |
| **Dense** | **Qwen3-Embedding-0.6B**, Apache-2.0, MRL → 512–1024 dims, 32k ctx | Permissive; MTEB-multilingual-strong at the 8B size; MRL cuts storage 2–4×; 32k ctx fits a whole sutta as one unit when needed |
| **Fusion** | **Reciprocal Rank Fusion (RRF)** over BM25 + dense (+ metadata lane) | Rank-fusion is robust when component scores are incomparable (BM25 vs cosine) and needs no score calibration. Chosen over weighted-score fusion because it has fewer tuning knobs to overfit on a small eval set |
| **Rerank** | **Qwen3-Reranker-0.6B** (Apache-2.0) | Cheap enough to run in-process; `bge-reranker-v2-m3` kept as A/B control |
| **Late interaction** | **Deferred** | Verified multilingual late-interaction options are CC-BY-NC or English-centric. Revisit at v0.3 with a fine-tuned dual encoder |
| **Chunking** | **Verse/sutta-unit primary, passage secondary — never fixed-size tokens** | Scripture retrieval fails on arbitrary windows. Every chunk carries `text_id`, `section`, `verse`, `edition`, `tradition`, `canon_scope`, `language`, `script`, `source_id`. A citation must be reconstructible from the chunk alone |
| **Chunk overlap** | Verse-level units with sutta-level parent context returned to the model | Lets the reader see the verse *and* its immediate context without polluting the index with duplicates |

### 2.2 Embedding-related honest caveats

- Qwen3-Embedding's card claims **"100+ languages"** without enumerating them. It does **not** claim
  Gujarati or Prakrit explicitly. **We must measure Gujarati and Prakrit retrieval ourselves** before
  publishing any claim about the system's language coverage. Record per-language recall@10 in the model card.
- Instruction-aware embedding: the card recommends **English instructions** (its training instructions were
  English). Use an English retrieval instruction even for Gujarati/Prakrit queries.
- **Do not** adopt `jina-embeddings-v3/v5` for the shipped stack: verified `CC-BY-NC-4.0`. It is
  nonetheless the best available *diagnostic* (it declares `gu`/`hi`/`sa`), so keep it in a scratch
  notebook to answer "is our recall bad because of the corpus or because of the model?"

---

## 3. Vector store / database (Part 12)

| Option | Licence | Verified state | Fit for V1 |
| --- | --- | --- | --- |
| **LanceDB** | **Apache-2.0** ✅ | 11.4k ★, pushed 2026-09-17 (daily activity) | ✅ **PRIMARY.** Embedded, serverless, columnar (Lance/Parquet), built-in FTS + vector hybrid, metadata filters, versioned datasets, runs inside a HF Space and inside a laptop |
| **Qdrant** | **Apache-2.0** ✅ | 34.6k ★, 2,679 forks, pushed 2026-09-16 | ✅ **Scale-out path.** Best managed/self-hosted production option, strong payload filtering |
| FAISS | MIT | — | ❌ Library, not a database: no metadata filtering, no persistence model, no FTS |
| Chroma | Apache-2.0 | — | ⚠️ Developer-simple, but weaker large-scale filtering than Qdrant |
| pgvector | PostgreSQL licence ⚠️ | — | ❌ Requires running Postgres — wrong ops cost for a 2-person open-source project |
| Milvus | Apache-2.0 | — | ❌ Cluster-grade ops for a corpus of ~10⁵–10⁶ chunks |
| Weaviate | BSD-3 | — | ❌ Heavier; no advantage at our scale for the ops burden |

**Decision: LanceDB for V1, Qdrant when we outgrow a single process.**
*Why:* at ~10⁵–10⁶ chunks, LanceDB gives us hybrid search + filters + versioned snapshots with **zero
servers**, which is exactly what a HF Space and a laptop both need; and because the index is a
directory of columnar files, a corpus version bump (`jain-svk-corpus-v0.2`) becomes a **data artefact**
we can publish alongside the dataset instead of a service we must migrate.

---

## 4. Fine-tuning method and training strategy (Part 16)

### 4.1 Options assessment

| Option | Verdict |
| --- | --- |
| 1. Raw-text continued pretraining (CPT) | ⚠️ **Conditional.** With < 50 M clean tokens its factual benefit is marginal. Its real value is **script/vocabulary adaptation** (Prakrit and Gujarati token efficiency) and style. Only run it if the cleaning effort yields ≥ 50 M tokens *and* the tokenizer measurement shows a severe token inflation on Prakrit/Gujarati |
| 2. Instruction tuning (SFT) alone | ✅ **Yes** — this is where citation discipline, abstention, and sect-scoping live. Small, high-quality, scholar-reviewed SFT >> large synthetic SFT |
| 3. CPT → SFT | ✅ **Target shape**, triggered by the ≥50 M gate |
| 4. RAG only | ✅ **v0.1 ships this.** It is a legitimate, defensible product |
| 5. CPT + SFT + RAG | ✅ **The v1.0 target** — architecture D |

### 4.2 Recommended plan

```
v0.1  RAG-ONLY            no training. Base Qwen3.5-4B + hybrid retrieval + citation scaffolding.
                          Publishes the CORPUS and the BENCHMARK as the real deliverables.
v0.2  SFT (LoRA, QLoRA)   3–8k scholar-reviewed instruction items. Teaches citation format,
                          sect framing, abstention, and the safety templates. Free-tier GPU.
v0.3  + CPT (conditional) LoRA CPT on the PD corpus IF ≥50M clean tokens exist. Measure tokenizer
                          efficiency before and after; measure Gujarati/Prakrit loss separately.
v1.0  + DPO/ORPO (opt.)   Preference pairs from reviewer corrections: citation-correct > fabricated,
                          abstention > speculation, sect-scoped > over-generalised.
```

**Why LoRA and not full fine-tuning:** full FT of a 4B on a free T4 is impossible; QLoRA is the only
method that fits the budget. **Why not train a small model from scratch:** the corpus cannot support it,
and the deliverable value of this project is the *corpus, benchmark and provenance*, not a novel pretraining run.

**Critical SFT design rules** (each is a direct consequence of §1 of the licence audit and the project rules):

1. **Never generate or train on "verse text".** Verses are *retrieved verbatim* from the corpus.
   SFT targets are explanations, citations, and abstentions.
2. **Every instruction item carries a machine-readable provenance block** (`source_id`, `citation`,
   `original_span`, `generator`, `generator_version`, `reviewer_status`). Publish it — provenance is the
   contribution.
3. **~30% of SFT items must be abstention items** ("this is not in the corpus", "this is a
   Mūrtipūjaka text; the Sthānakavāsī canon does not include it"). Refusal behaviour is trained, not prompted.
4. **Sect-scoping is trained explicitly**, not left to the system prompt: the target text itself names
   the tradition.
5. **The 8 instruction types** to build (from the brief, all justified): scripture QA · concept
   explanation · verse explanation (given a retrieved verse) · translation · summarisation · source
   identification · **citation generation** · sect-context questions · comparison questions ·
   unknown-answer behaviour · hallucination refusal.
6. **No model-of-the-day dependency in the target text.** Where a strong LLM drafts an explanation, a
   reviewer must accept it before it becomes a target, and it is tagged `AI_GENERATED_HUMAN_VERIFIED`.

---

## 5. Synthetic data (`Part 17`) — safe workflow

```
PD/CC0 passage  ──►  generator (DeepSeek-V4-Flash MIT / GLM / Qwen3.8)
                      prompt: "Use ONLY this passage. If the answer is not contained, output ABSTAIN.
                               Never invent a sutta name, number, author or verse."
                          │
                          ▼
            automated validation (deterministic, cheap, no LLM judge for the critical checks)
              · citation resolves to a real source_id and a real verse address
              · every quoted span is a substring of the normalised source passage   ← the key check
              · language/script matches the declared field
              · no numeric/sutta-ID string appears that is absent from the passage
                          │
             ┌────────────┴────────────┐
             ▼                         ▼
     passes all checks          fails any check → discard (never "repair")
             │
             ▼
     stratified sample → scholar review → approved
             │
             ▼
     labelled: AI_GENERATED_HUMAN_VERIFIED  (never bare AI_GENERATED in training targets)
```

**Non-negotiables:** synthetic artefacts never occupy the scripture field; every synthetic item is
regenerable from a pinned `(generator_version, prompt_hash, seed, passage_hash)` tuple; and the
**substring check is the anti-hallucination guarantee** — if a proposed citation is not literally present
in the passage, the item dies. No LLM judge may override a failed substring check.

---

## 6. Scholar review (Part 18)

```
AI generation → automated validation → stratified sample selection →
Sthānakavāsī scholar/teacher review → correction → dual review on disagreement → approved dataset (versioned)
```

| Question | Recommendation |
| --- | --- |
| **Review percentage** | **100% of citation-bearing items** in the V1 benchmark (it is small). **10% stratified sample** of SFT items for v0.2, rising to 25% at v1.0. 100% of anything that touches ritual, fasting, health, sallekhana/santhara |
| **Sampling** | Stratified by `text_category × language × tradition × generator`; never simple random — the failure modes cluster by category |
| **Disagreement handling** | Two reviewers on a 10% subsample; disagreements escalate to a third senior reviewer; record the resolution and *why*. Target **Cohen's κ ≥ 0.8** on the citation-correctness label before scaling |
| **Versioning** | Every review is a row in `reviews.jsonl` keyed by `item_id + reviewer_pseudonym + timestamp + verdict + notes`. Dataset versions are cut from a frozen review state |
| **Annotation schema** | Per item: `citation_correct` (bool/enum), `sect_attribution_correct` (bool/enum), `language_correct`, `authority_level` (SCRIPTURE / TRADITIONAL_COMMENTARY / MODERN_SCHOLARSHIP / AI_EXPLANATION), `safety_flag`, `free_text_correction` |
| **Who reviews** | **We must recruit; we must not invent.** No scholar is named in this document. Outreach targets (institutions already verified to exist): the **A.B. Shree Svetambar Sthanakvasi Jain Conference**, Sthānakavāsī monastic orders and their publishing arms, Sthānakavāsī pathshala teachers, and Jain Studies departments in Gujarat. Budget an honorarium line — this is the project's rate-limiting step |

---

## 7. Evaluation framework (Part 19) and the model-vs-RAG experiment (Part 20)

### 7.1 Sealed benchmark

`jain-svk-bench-v0.1` — **never trained on, never retrieved into a training loop**, hash-blocked in the
pipeline, and stored in a separate repo with a frozen ID list.

| Category | n (target) | What is measured |
| --- | --- | --- |
| Factual knowledge | 150 | Concept accuracy vs a scholar-written reference |
| Scripture / verse | 100 | Verse exactness (normalised exact-match + CER) |
| Citation | 100 | Citation precision / recall / resolvability |
| Sect context | 100 | Correct tradition framing; **trap set** where a Mūrtipūjaka-only text is asked about as if Sthānakavāsī |
| Language | 100 | Hindi / Gujarati / English quality; separate Prakrit comprehension probes |
| Hallucination / abstention | 100 | "Gold absence" probes: correct answer is ABSTAIN |
| Safety | 50 | fasting, health, death, sallekhana/santhara, ritual instruction, personal spiritual decisions |

### 7.2 Metrics (all defined so they can't be fudged)

| Metric | Definition |
| --- | --- |
| `factual_accuracy` | % items matching the scholar reference on the graded rubric |
| `verse_exactness` | % of quoted verses byte-identical after Unicode normalisation |
| `cer` | character error rate vs reference verse |
| `citation_precision` | % of emitted citations that resolve to a real `source_id` **and** correct verse address |
| `citation_recall` | % of required citations actually emitted |
| `retrieval_recall@10` | % of questions whose gold passage is in the top-10, **reported per language** |
| `ndcg@10` | Ranking quality on the retrieval probe |
| `hallucination_rate` | % of responses containing a fabricated verse / citation / author / practice (includes all failures on gold-absence probes that do not abstain) |
| `abstention_correctness` | % of gold-absence probes answered with abstention |
| `sect_context_accuracy` | % of tradition-ambiguous responses carrying the correct tradition tag; and % of trap-set items correctly identified as out-of-canon |
| `language_quality` | Human rubric (fluency, register, script purity) + automated script-mixing / mojibake detector |
| `safety_template_adherence` | % of safety-category items using the approved template, with zero medical/ritual instruction |
| `authority_frame_compliance` | % of responses that do not present the system as a religious authority |

### 7.3 The four-system experiment

Identical sealed question set, identical retriever settings where applicable, 3 seeds where sampling applies:

| System | Configuration |
| --- | --- |
| **S1** | Base `Qwen3.5-4B` (no RAG, no tuning) |
| **S2** | Base + our hybrid retrieval + citation scaffolding |
| **S3** | Jain-tuned (LoRA) model, no retrieval |
| **S4** | Jain-tuned + hybrid retrieval (the target architecture) |

**Analysis plan:** paired bootstrap 95% CIs; report the full metric matrix, not a single "winner".
Two independent annotators on every judged category; κ reported; disagreements adjudicated.

**Hypotheses to falsify (state them before running):**
- H1: S2 > S1 on citation precision and hallucination rate (RAG fixes grounding).
- H2: S4 > S2 on sect-context accuracy and language quality (tuning fixes framing/register).
- H3: S3 ≈ S1 on scripture exactness — **i.e. fine-tuning without retrieval does *not* buy verse accuracy.**
  If H3 is *not* rejected, that is a publishable negative result and the strongest possible argument
  against architecture A.
- H4: All systems degrade on Prakrit-language probes relative to Hindi/Gujarati — the honest expected result.

---

## 8. Hugging Face publishing strategy (Part 21)

### 8.1 Repository layout

```
github.com/<org>/jain-svk                          Apache-2.0 (code)
├── README.md  ·  CONTRIBUTING.md  ·  TAKEDOWN.md  ·  ETHICS.md
├── corpus/            acquisition → licence gate → OCR → normalise → dedup → split
├── retrieval/         normaliser, transliterator, chunker, BM25+dense+RRF, reranker
├── training/          configs + scripts (trl/peft; reproducible from a pinned manifest)
├── eval/              the harness that runs the 4-system experiment
├── app/               Gradio demo
└── LICENSE · NOTICE · licenses/<source_id>.txt

huggingface.co/datasets/<org>/jain-svk-corpus         CC BY 4.0 (+ per-source NOTICE)
    corpus.parquet, sources.jsonl, LICENSE_MAP.csv, README (dataset card), viewer enabled
huggingface.co/datasets/<org>/jain-svk-instructions   CC BY 4.0
    sft.jsonl (+ provenance fields), reviews.jsonl, README
huggingface.co/datasets/<org>/jain-svk-bench          CC BY 4.0
    bench.jsonl, gold_references.jsonl, README, "SEALED — DO NOT TRAIN" banner
huggingface.co/models/<org>/jain-svk-4b-adapter       Apache-2.0  (LoRA adapter weights only)
huggingface.co/models/<org>/jain-svk-4b               Apache-2.0  (merged safetensors + BF16)
    + gguf/  Q4_K_M, Q5_K_M, Q8_0
huggingface.co/spaces/<org>/jain-svk-demo             Apache-2.0  (Gradio)
```

### 8.2 Practices that matter (verified 2026 realities)

- **safetensors + sharded weights**; never pickle. Publish **adapter and merged** forms so users can
  choose cheap LoRA reuse or direct inference.
- **GGUF for the "ordinary user" requirement** — Q4_K_M is the default, with the Modelfile for Ollama in-repo.
- **Dataset card must carry** `license`, `language` (incl. `pra`, `gu`, `hi`, `sa`), `provenance`,
  `source` and a per-row licence ledger; enable the **dataset viewer** (Parquet auto-conversion) — it is
  the cheapest credibility signal we have.
- **Model card must carry** `base_model`, `library_name`, `license`, `datasets`, `language`, plus:
  training tokens, the exact corpus version hash, the eval table, per-language retrieval recall, known
  limitations, and an explicit **"not a religious authority"** statement.
- **Space demo:** RAG-first, short answers, visible citations and provenance footer, mandatory disclaimer.
  Free CPU hosting of a 4B is possible but slow — plan for a GPU Space or a small CPU-friendly
  configuration with streaming, and state the hosted model's identity in the UI.
- **Xet-backed storage** is HF's current storage backend and de-duplicates large repeated artefacts; it
  materially reduces the cost of publishing many model-format variants. ⚠️ Confirm current quotas and
  behaviour for the org before planning storage.

---

## 9. Versioning (Part 22)

```
jain-svk-corpus-v0.1        PD/CC0 seeds only. Scans + archive.org OCR text, licence-gated, provenance-complete.
jain-svk-corpus-v0.2        + human-typed Prakrit core; + verified normalisation; + dedup across DLI/patron dup pairs
jain-svk-corpus-v1.0        + consented Sthānakavāsī educational material; frozen for training
jain-svk-instructions-v0.1  ~3–8k scholar-reviewed SFT items
jain-svk-bench-v0.1         SEALED. Frozen. Never trained. Versioned in its own repo
jain-svk-model-v0.1         RAG-only baseline (NO weights — a retrieval + prompt release)
jain-svk-model-v0.2         first LoRA adapter; v0.3 CPT if the ≥50M-token gate passes; v1.0 = D
```

**Rules for future releases**
1. **Every version is a hash-pinned artefact.** Model cards name the corpus version *by hash*, and
   corpus cards name the source manifest hash.
2. **Additive by default, with a rebuild path.** Withdrawing a source triggers a rebuild downstream of
   it; because V1 is RAG-first, withdrawal is instant in retrieval and requires retraining only for adapters.
3. **Benchmark versions are sealed and never edited in place.** Corrections create `bench-v0.2` and the
   old one stays published so prior results remain reproducible.
4. **Never overwrite a published model.** New adapter, new tag, explicit deprecation note.
5. **A `CHANGELOG` entry per release stating what was added, what was removed and *why*.** In a religious
   project, removals are as important as additions.

---

## 10. Recommended V1 architecture (Part 23) — the single answer

```
BASE MODEL      Qwen/Qwen3.5-4B            Apache-2.0   [fallback: Qwen/Qwen3-8B; hedge: gemma-4-E4B]
FINE-TUNING     QLoRA (NF4) → LoRA r=16–32, α=32, target all attn+MLP projections
                v0.2 = SFT only (citation discipline, abstention, sect framing)
                v0.3 = + LoRA CPT, ONLY if ≥50M clean PD tokens
                tooling: Unsloth for speed, TRL config as the reproducible source of truth
RETRIEVAL       RRF over (a) BM25 on normalised Prakrit/IAST/Devanagari
                          (b) dense ANN
                          (c) exact verse/metadata lookup
                with hard metadata pre-filters: tradition, canon_scope, language, text_id, edition
EMBEDDING       Qwen/Qwen3-Embedding-0.6B (MRL → 512–1024 dims, 32k ctx)
                + our deterministic normaliser & transliterator as a mandatory pre-stage
RERANKER        Qwen/Qwen3-Reranker-0.6B   (A/B control: BAAI/bge-reranker-v2-m3)
VECTOR DB       LanceDB (Apache-2.0, embedded, hybrid, versioned) → Qdrant at scale-out
ROUTER          0.5B classifier for language / query-type / sect-scope / safety-lane routing
OCR STACK       PP-OCRv5 det → PP-OCRv5-devanagari-rec + one 2026 VLM-OCR (consensus, human-gated)
                Gujarati: umangchaudhari/gujarati-ocr as an experiment ONLY, never as ground truth
                plus a HUMAN-TYPED Prakrit core — the actual ground truth
PREPROCESSING   the pipeline in jain_svk_data_pipeline.md (licence gate first, dedup before split)
DATASET FORMAT  Parquet (corpus) + JSONL (instructions, with provenance) + CSV/JSON (manifest)
EVALUATION      4-system experiment on a sealed 700-item benchmark; paired bootstrap CIs; 2 annotators
INFERENCE       GPU: vLLM. CPU/edge: llama.cpp + GGUF Q4_K_M. Local UX: Ollama Modelfile.
                Demo: Gradio on HF Spaces, RAG-first, always-cited, always-disclaimed
PUBLISHING      the repo layout in §8.1; code Apache-2.0; corpus CC BY 4.0 + NOTICE; model Apache-2.0
LOCAL           docker compose: app + LanceDB index + GGUF weights (~3 GB total download)
```

### GPU requirements and expected cost (Part I)

All figures are **ENGINEERING ESTIMATES, not vendor quotes** — cloud prices in particular must be
re-checked before committing; they are marked ⚠️ ESTIMATE.

| Activity | Hardware | Time | Cost |
| --- | --- | --- | --- |
| Corpus acquisition + licence audit + cleaning (no GPU) | laptop | 3–6 weeks part-time | **$0** |
| Human typing of the Prakrit core (~1,500 entries + 32 sutta mūla-pāṭha excerpt) | laptop + human hours | 4–8 weeks | labour only |
| Embedding ~200k–500k chunks @ 512 dim | 1× T4 / CPU | 2–6 h | **$0 (Colab/Kaggle)** |
| **v0.2 QLoRA SFT** (4B, ~3–8k items, 2–3 epochs) | Kaggle T4×2 (30 GB) or Colab L4 | **1–4 h** | **$0–$5** |
| CPT on 50–100M tokens (if the gate passes) | 1× A100 40 GB ⚠️ | **4–12 h** | ⚠️ **$10–$60** at ~$1.5–2.5/h (RunPod/Vast-class) |
| Evaluation runs (4 systems × 700 items) | 1× L4/A10 ⚠️ | 6–15 h | ⚠️ **$5–$30** |
| Demo Space (GPU, intermittent) | HF Spaces GPU ⚠️ | ongoing | ⚠️ **$0–$30/month** |
| **Total cash to v1.0 (excluding scholar honoraria)** | | | ⚠️ **~$20–$150** |
| **Scholar review honoraria** | | | **the real cost — budget explicitly** |

**Storage:** corpus Parquet 1–5 GB · embeddings (500k × 1024 fp16) ≈ 1 GB (≈0.5 GB at 512 dims/int8) ·
index ≈ 1–2 GB · LoRA adapter 50–150 MB · merged BF16 ~8 GB · GGUF Q4_K_M ~2.5 GB → **~20 GB published,
~5 GB for a local install.**

**Expected corpus size:** ⚠️ ESTIMATE — 800–1,800 CC0 items; after licence gating, dedup and quality
filtering, expect **30–120 M usable tokens**, of which **Prakrit is < 2 M tokens** (typed + verified) and
**Sthānakavāsī-specific content is < 5 M tokens**. These are the numbers the ingest task must measure and
replace with facts.

### WHY THIS OVER THE ALTERNATIVES (consolidated)

- **Why Qwen3.5-4B, not a bigger/older model:** Apache-2.0, 2026-current, trainable on free tiers, and
  distributable as a 2.5 GB GGUF. We deliberately refuse the higher-quality 27B/30B options because our
  measured bottleneck is corpus and evaluation, not capacity — buying parameters now would buy nothing
  measurable and would break the "free tier" constraint.
- **Why RAG-first, not fine-tune-first:** we verified that the legally clean Sthānakavāsī corpus is
  tiny. A RAG system degrades gracefully as the corpus grows; a fine-tuned model trained on a tiny
  corpus **silently fabricates**, which is the project's fatal failure mode.
- **Why hybrid retrieval, not dense-only:** verified — no embedding model declares Prakrit. Dense-only
  would fail precisely on the tradition's own language.
- **Why LanceDB, not Qdrant, for V1:** zero servers means it fits both a HF Space and a laptop, and the
  index becomes a publishable data artefact. Qdrant is the planned upgrade, not a rejection.
- **Why CC BY 4.0 for the corpus:** permissive enough for reuse, keeps attribution, and — unlike CC0 —
  gives us a hook to require provenance propagation, which is the thing this project is actually about.
- **Why the safety lane bypasses the model:** a router bypass is auditable; a prompt instruction is not.

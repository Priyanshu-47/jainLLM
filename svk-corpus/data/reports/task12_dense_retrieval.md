# Task 12 — Dense Retrieval Feasibility (Outcome: NOT MEASURABLE in this environment)

**Date:** 2026-09-18 · **Outcome per Step 2:** no embedding model is available locally, and the task forbids downloading one without explicit approval — so the three-way BM25 vs Dense vs Hybrid comparison **was not run** and no metrics are reported. This report documents the check, the ready interface, the minimum requirements for the next experiment, and the BM25-failure-side analysis that existing data *does* support. No baseline files were modified; nothing was downloaded; corpus/gate/release untouched.

---

## 1. Environment feasibility (measured)

Checks performed (2026-09-18):

| check | result |
|---|---|
| `pyproject.toml` dependencies | `dependencies = []` — the project's stated zero-dependency principle |
| installed packages (pip list) | only colorama, iniconfig, packaging, pip, pluggy, Pygments, pytest |
| embedding libraries probed | sentence_transformers, transformers, torch, tensorflow, numpy, fastembed, onnxruntime, gensim, sklearn, scipy, faiss, annoy, hnswlib — **all absent** |
| model artifacts in workspace | none (no .onnx / .safetensors / .h5 anywhere under the project) |
| Hugging Face cache | none |
| prior downloads (Task 2) | tokenizer.json files only (BPE vocab files, ~10–25 MB total), never model weights |

**Conclusion (fact):** there is no usable embedding model, and no tensor library to run one. Substituting random word vectors, TF-IDF, character similarity, or any other lexical technique and calling it "dense" was forbidden and was not done — Task 8's `HashDense` exists as a clearly-labelled deterministic TEST DOUBLE for interface tests only, and it was not used for any claim in this report.

## 2. Model/library used

**None.** No model was downloaded; per the task rules the experiment stops at feasibility.

## 3. Dense indexing method

Not built — the Step 3 precondition (a real embedding model available) was not met. The existing interface (see §12) was left untouched.

## 4. Evaluation methodology

Prepared but unexecuted: the same `configs/retrieval_eval_queries_v1.json` (17 labelled queries + 1 corpus-gap probe + 2 exploratory), same protocol as Tasks 8–11, with a `task12` label writing to a separate results file. All Task 8–11 baseline files verified untouched.

## 5. BM25 vs Dense vs Hybrid metrics

**Not measured — deliberately not fabricated.** What *is* measured and current (Task 11, BM25-only): R@5 0.777 · R@10 0.836 · MRR 0.905 · zero-relevant 0/17 (diversify presentation tier) / 0.760 · 0.819 · 0.905 (pure BM25).

## 6. BM25 failure-side analysis (measured, from Task 10/11 artifacts)

The task's most important analysis can be partially answered from existing evidence without dense retrieval:

- **Known BM25 misses with a documented cause (from Task 9/10 reports):** q03 `Sutrakritanga` and q05 `Uttaradhyayana Sutra` were total lexical misses *caused by romanization variance* and were recovered by the Task 9 alias layer — deterministic, auditable, zero-cost. These are exactly the "lexical mismatch / terminology variation" cases where dense retrieval is hypothesized to help; here the cheaper deterministic fix already succeeded.
- **q19 (`Acharya Anand Rishi`):** a documented corpus-gap probe — no relevant material exists in the corpus. BM25 returns confident irrelevant hits (SVK-1005 ×5). Dense retrieval would *also* return confident irrelevant nearest neighbours (dense indexes cannot signal absence); preserving the gap interpretation is correct.
- **q09 (`Ratnachandra`):** SVK-2002/2003/2004/2005 have **0 matching units** because the person name occurs nowhere in their text (Task 11 measurement). A dense model could in principle match "Ratnachandra"-semantics to related dictionary content — but the missing signal is *provenance-level* (author/editor of an edition family), which semantic similarity of unit text is unlikely to encode reliably. The Task 11 conclusion stands: this needs source-level retrieval, not embeddings.
- **q17 (`જૈન ધર્મ`):** now rank-1 correct (MRR 1.0); residual is SVK-2010's OCR degradation — a text-quality problem, orthogonal to the retrieval method.

**Hypothesis (labelled as such):** the remaining BM25 failure modes in this corpus are mostly *not* paraphrase-shaped; they are romanization variance (solved deterministically), provenance-only evidence (needs source-level structures), OCR garble (needs corpus repair), and genuine corpus gaps (needs acquisition). The one place dense retrieval could plausibly add value is cross-language paraphrase queries (English question → Gujarati/Prakrit passage), which the current 20-query prototype set does not yet test.

## 7. Minimum requirements for the next dense experiment

1. **Model (smallest practical, must be approved before download):** a ~0.5–1 GB multilingual embedding model with Gujarati/Devanagari/Latin coverage (e.g. a multilingual-MiniLM-class or Qwen3-Embedding-0.6B-class model — matching the tokenizer families already measured in Task 2), in an installable-package runtime (sentence-transformers or fastembed/onnxruntime).
2. **Runtime deps:** numpy + one inference runtime — this breaks the zero-dependency principle, so it belongs in an **optional extra** (`pip install .[dense]`), never a hard dependency.
3. **Storage budget:** 145,147 units × ~768–1024 dims × 4 bytes ≈ **450–600 MB** float32 index (or ~110–150 MB at int8 quantization) — needs an explicit storage decision.
4. **Compute budget:** embedding 145k units ≈ hours on CPU — a one-time batch job, not an interactive step.
5. **Determinism plan:** fixed model revision hash recorded in the results file; cosine similarity; fixed round-off policy; index rebuild = re-run from release files.

## 8. Recommendation

**Next retrieval step: not dense.** The measured failure modes are covered better by (a) source-level retrieval cards (q09 residual — Task 11 recommendation, unchanged), and (b) the alias/v2 + OCR-repair track (q17 residual). If paraphrase queries become a requirement, revisit dense retrieval *with approval* using the §7 checklist; the `DenseRetriever` interface is already in place and RRF-compatible, so no redesign would be needed.

## 9. What already exists and is ready (engineering observation)

- `retrieval/dense.py`: `DenseRetriever` interface (embed/search/top_k/allowed), `UnavailableDense` honesty marker, `HashDense` test double.
- `HybridRetriever` already fuses a dense list via the existing RRF implementation — mode C of the task would have worked without modification.
- Provenance contract (`RetrievalResult.provenance()`) is method-agnostic and would carry dense results unchanged.
- Tests already cover: dense-unavailable honesty, test-double fusion, provenance preservation, top-k, metadata prefilter (`tests/test_retrieval.py`).

## 10. Failure cases

None new: nothing was executed beyond inspection. Known unresolved retrieval failures carried forward from Tasks 8–11: q09 structural residual (4 sources, zero lexical evidence), q17 OCR residual (SVK-2010), q19 corpus gap.

## 11. Latency/storage observations

Only projections (labelled as such): CPU embedding of 145k units = hours (one-time); query-time dense search ≈ 10–100 ms with a flat index; storage §7.3. Measured BM25 latency for contrast: 39–45 ms mean, index build ~55 s, zero storage overhead.

## 12. Tests

No new tests were warranted — no new behaviour was implemented. The existing suite (140 tests) already covers the dense interface contract (unavailable-honesty, test-double fusion, provenance, top-k, filtering, RRF compatibility); full suite re-run this session: **140/140 pass**.

---

**Measured vs interpretation:** §1 is measured inspection; §6 first three bullets are measured from Task 9–11 artifacts; §6 last bullet, §7 (except dep facts), §9, §11 are engineering observations/hypotheses and labelled. No metric in this report is invented.

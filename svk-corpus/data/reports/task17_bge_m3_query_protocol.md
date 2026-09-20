# Task 17: BGE-M3 Query Protocol Benchmark

## Goal

Correct the BGE-M3 query encoding: remove the `"Query: "` prefix that Task 16 incorrectly used. Official BGE-M3 guidance says the model does not require query instructions/prefixes.

## Key Insight

Document embeddings are identical regardless of query prefix. Only the 20 evaluation queries need re-encoding. The Task 16 FAISS index (145k doc embeddings) is reused without modification.

## Setup

- **Model**: BAAI/bge-m3 (1024-dim, normalize_embeddings=True, max_seq_length=1024)
- **FAISS index**: Reused from Task 16 (`bge_m3_faiss.index`)
- **Document embeddings**: NOT regenerated
- **Evaluation queries**: Same 20 queries from Task 13/14

## Comparison

| Mode | Query Prefix | Description |
|------|-------------|-------------|
| A | `"Query: "` | Task 16 reference (incorrect) |
| B | `""` | Corrected (no prefix) |
| C | N/A | BM25+source baseline |
| D | `""` | Hybrid RRF with corrected dense |

## Files Changed

| File | Action | Description |
|------|--------|-------------|
| `src/svk_corpus/retrieval/dense.py` | Modified | Added `from_prebuilt()` class method |
| `tools/task17_bge_m3_query_protocol_kaggle.ipynb` | Created | Kaggle GPU notebook |
| `tests/test_retrieval.py` | Modified | Added 3 tests for `from_prebuilt()` |
| `data/reports/task17_bge_m3_query_protocol.md` | Created | This report |

## Tests

- 191 total tests (188 original + 3 new)
- New tests: `TestSentenceTransformerDenseFromPrebuilt` (3 tests)
  - `test_from_prebuilt_loads_index` — loads FAISS index, verifies metadata
  - `test_from_prebuilt_rejects_missing_file` — FileNotFoundError on missing path
  - `test_from_prebuilt_stores_query_prefix` — prefix stored correctly

## Kaggle Execution

See `tools/task17_bge_m3_query_protocol_kaggle.ipynb` for the full benchmark.

**Prerequisites**:
1. Upload `svk-corpus/` to Kaggle
2. Upload `task16_artifacts/` from Task 16 output (contains `bge_m3_faiss.index`)
3. Edit `CORPUS_DIR` and `TASK16_ARTIFACTS_DIR` in Cell 3

**Expected runtime**: ~5 minutes on GPU (model load + 20 query encodings x 2 prefixes)

## Expected Results (placeholder — update after Kaggle run)

Task 16 reference (prefix="Query: "):
- Dense-only: R@5=0.461, R@10=0.531, MRR=0.516

Corrected (prefix=""): TBD after Kaggle execution.

BM25+source baseline:
- R@5=0.744, R@10=0.836, MRR=0.868

## Recommendation

After Kaggle execution, update this report with:
1. Corrected dense-only metrics
2. Delta between prefix="" and prefix="Query: "
3. Corrected hybrid RRF metrics
4. Per-query comparison for q06, q09, q10, q11, q17
5. Final recommendation on query prefix protocol

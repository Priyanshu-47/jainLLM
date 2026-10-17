"""TASK 74 Phase 3 — experiment-local dense index, BAAI/bge-m3 (Colab GPU).

Protocol (measured, recorded in index_meta.json):
  - embedding text = exact RetrievalDocument.search_text replica
    (manifest title/author precedence, normalized_text preferred,
    field order [title x3, author, section, text], empties skipped)
  - queries = raw frozen questions (no lexical query expansion)
  - sentence-transformers SentenceTransformer("BAAI/bge-m3"), fp16 encode
    (fp32 measured 34 docs/s vs fp16 169 docs/s on T4; both recorded),
    normalize_embeddings=True (L2), batch 64 with CUDA-OOM halving,
    max_seq_length 8192, Tesla T4 15360 MiB
  - chunked checkpoint every 20k docs (resume-safe), final fp16 matrix
  - full-corpus text/doc-id/query sha256 emitted for exact local alignment

Outputs -> /content/task74_out (downloaded to experiments/task74/dense_index/):
  corpus_emb.f16.npy  queries_emb.f32.npy  index_meta.json
"""

import csv
import gzip
import hashlib
import json
import os
import resource
import time

IN = "/content/task74_in"
OUT = "/content/task74_out"
CHUNK_DIR = os.path.join(OUT, "chunks")
CHUNK_SIZE = 20000
os.makedirs(CHUNK_DIR, exist_ok=True)

t_start = time.time()


def say(msg):
    print(f"[t74] {msg}", flush=True)


# ---- manifest scope (mirrors load_source_scope) ----
scope = {}
with open(f"{IN}/source_manifest.csv", encoding="utf-8", newline="") as f:
    for row in csv.DictReader(f):
        scope[row.get("source_id", "")] = {"title": row.get("title", "") or "",
                                           "author": row.get("author", "") or ""}
say(f"manifest sources: {len(scope)}")

# ---- corpus: exact search_text replication + alignment hashes ----
t0 = time.time()
texts, doc_ids = [], []
text_sha = hashlib.sha256()
id_sha = hashlib.sha256()
char_lens = []
with gzip.open(f"{IN}/rag_corpus.jsonl.gz", "rt", encoding="utf-8") as f:
    for line_number, line in enumerate(f, 1):
        stripped = line.strip()
        if not stripped:
            continue
        rec = json.loads(stripped)
        src = scope.get(rec.get("source_id", ""), {})
        title = src.get("title") or rec.get("title", "")
        author = src.get("author") or rec.get("author", "")
        text = rec.get("normalized_text") or rec.get("text") or ""
        section = str(rec.get("section") or "")
        text_id = str(rec.get("id") or f"line{line_number}")
        st = " ".join(p for p in (title, title, title, author, section, text) if p)
        texts.append(st)
        doc_ids.append(text_id)
        text_sha.update(st.encode("utf-8"))
        id_sha.update(text_id.encode("utf-8"))
        char_lens.append(len(st))
n_docs = len(texts)
say(f"docs={n_docs} read_s={time.time()-t0:.1f} mean_chars={sum(char_lens)/n_docs:.0f} "
    f"max_chars={max(char_lens)}")

queries, q_ids = [], []
with open(f"{IN}/queries.jsonl", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            r = json.loads(line)
            queries.append(r["question"])
            q_ids.append(r["example_id"])
q_sha = hashlib.sha256()
for q in queries:
    q_sha.update(q.encode("utf-8"))
say(f"queries={len(queries)}")

# ---- model (fp16 encode; fp32 ruled out by bench at 34 vs 169 docs/s) ----
import numpy as np
import torch
from sentence_transformers import SentenceTransformer

t0 = time.time()
model = SentenceTransformer("BAAI/bge-m3", device="cuda")
model.half()
load_s = time.time() - t0
try:
    revision = model[0].auto_model.config._commit_hash
except Exception:
    revision = None
say(f"model loaded load_s={load_s:.1f} rev={revision} max_seq={model.max_seq_length} "
    f"encode_dtype=float16")

# ---- chunked encode with resume ----
torch.cuda.empty_cache()
torch.cuda.reset_peak_memory_stats()
n_chunks = (n_docs + CHUNK_SIZE - 1) // CHUNK_SIZE
bs = 64
t0 = time.time()
resumed = 0
for ci in range(n_chunks):
    path = os.path.join(CHUNK_DIR, f"chunk_{ci:03d}.npy")
    if os.path.exists(path):
        resumed += CHUNK_SIZE
        continue
    lo, hi = ci * CHUNK_SIZE, min((ci + 1) * CHUNK_SIZE, n_docs)
    parts, i = [], lo
    while i < hi:
        with torch.inference_mode():
            try:
                v = model.encode(texts[i:min(i + bs, hi)], batch_size=bs,
                                 normalize_embeddings=True, convert_to_numpy=True,
                                 show_progress_bar=False)
            except torch.cuda.OutOfMemoryError:
                torch.cuda.empty_cache()
                bs = max(16, bs // 2)
                say(f"CUDA OOM -> batch_size={bs}")
                continue
        parts.append(np.asarray(v, dtype=np.float16))
        i += v.shape[0]
    np.save(path, np.concatenate(parts))
    done = hi
    rate = done / (time.time() - t0)
    say(f"chunk {ci+1}/{n_chunks} done={done}/{n_docs} rate={rate:.0f}/s "
        f"eta={(n_docs-done)/rate:.0f}s")
encode_s = time.time() - t0
say(f"encode finished encode_s={encode_s:.1f} resumed_from={resumed} final_bs={bs}")

# ---- assemble ----
corpus_emb = np.concatenate(
    [np.load(os.path.join(CHUNK_DIR, f"chunk_{ci:03d}.npy")) for ci in range(n_chunks)]
).astype(np.float16)
norms = np.linalg.norm(corpus_emb.astype(np.float32), axis=1)
vram_peak = torch.cuda.max_memory_allocated() / 2**20
say(f"assembled {corpus_emb.shape} norm_max_dev={float(np.abs(norms-1).max()):.6f} "
    f"vram_peak_mb={vram_peak:.0f}")

# ---- queries ----
t0 = time.time()
with torch.inference_mode():
    q_emb = np.asarray(model.encode(queries, batch_size=47, normalize_embeddings=True,
                                    convert_to_numpy=True), dtype=np.float32)
query_encode_s = time.time() - t0
say(f"queries encoded s={query_encode_s:.2f} mean_ms={query_encode_s/len(queries)*1000:.0f}")

# ---- save final artifacts ----
np.save(f"{OUT}/corpus_emb.f16.npy", corpus_emb)
np.save(f"{OUT}/queries_emb.f32.npy", q_emb)
with open(f"{OUT}/corpus_emb.f16.npy", "rb") as f:
    emb_sha = hashlib.sha256(f.read()).hexdigest()
meta = {
    "model_id": "BAAI/bge-m3",
    "model_revision": revision,
    "embedding_dim": int(corpus_emb.shape[1]),
    "normalization": "L2 (normalize_embeddings=True); cosine == inner product",
    "encode_dtype": "float16 (fp32 bench 34.4 docs/s vs fp16 169.0 docs/s on T4)",
    "storage_dtype": "float16 corpus / float32 queries; local search casts to float32 and re-normalizes",
    "batch_size": bs,
    "max_seq_length": int(model.max_seq_length),
    "truncated_docs": int(sum(1 for c in char_lens if c > 40000)),
    "device": torch.cuda.get_device_name(0) + f" {torch.cuda.get_device_properties(0).total_memory//2**20} MiB",
    "runtime": {
        "model_load_s": round(load_s, 1),
        "corpus_encode_s": round(encode_s, 1),
        "corpus_docs": n_docs,
        "corpus_docs_per_s": round(n_docs / encode_s, 1),
        "query_encode_s": round(query_encode_s, 2),
        "queries": len(queries),
        "total_s": round(time.time() - t_start, 1),
    },
    "peak_vram_mb": round(vram_peak, 0),
    "peak_ram_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 0),
    "index_type": "flat inner-product over L2-normalized embeddings (numpy matrix)",
    "embedding_text": "RetrievalDocument.search_text replica (title x3, author, section, normalized_text/text)",
    "query_text": "raw frozen question (no lexical query expansion)",
    "alignment": {
        "corpus_text_sha256": text_sha.hexdigest(),
        "doc_ids_sha256": id_sha.hexdigest(),
        "queries_sha256": q_sha.hexdigest(),
        "doc_count": n_docs,
        "query_count": len(queries),
    },
    "corpus_emb_f16_sha256": emb_sha,
}
with open(f"{OUT}/index_meta.json", "w", encoding="utf-8") as f:
    json.dump(meta, f, indent=1)
say("files: " + ", ".join(sorted(os.listdir(OUT))))
print("EMBED_DONE::" + json.dumps(meta["runtime"]) + " vram=" + str(int(vram_peak)))

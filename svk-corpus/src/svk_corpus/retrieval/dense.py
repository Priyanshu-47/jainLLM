"""Dense retrieval interface and implementations.

Components
----------
  * `DenseRetriever`           — the interface any real encoder must satisfy;
  * `SentenceTransformerDense` — real semantic retrieval using sentence-transformers
                                 and FAISS (Task 16). L2-normalised inner product =
                                 cosine similarity. Encodes all corpus units once at
                                 build time; queries encoded at search time.
  * `UnavailableDense`         — honest production state when no model is available;
  * `HashDense`                — DETERMINISTIC TEST DOUBLE for unit-testing the dense
                                 path and RRF fusion. Not semantic; never for metrics.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from svk_corpus.retrieval.documents import RetrievalDocument


class DenseRetriever:
    """Interface for a real dense encoder (e.g. a multilingual sentence model).

    Implementations embed all documents once at build time and embed queries at
    search time; similarity is cosine. Ranking is fully deterministic given the
    same model and texts.
    """

    name = "dense"

    def __init__(self, docs: Sequence[RetrievalDocument]) -> None:
        self.docs = list(docs)
        self._matrix: list[list[float]] = []
        for doc in self.docs:
            self._matrix.append(self.embed(doc.text))

    def embed(self, text: str) -> list[float]:
        raise NotImplementedError

    def search(self, query: str, top_k: int = 10,
               allowed: list[int] | None = None) -> list[tuple[RetrievalDocument, float]]:
        if not self._matrix:
            return []
        q = self.embed(query)
        qn = math.sqrt(sum(x * x for x in q)) or 1.0
        allowed_set = set(allowed) if allowed is not None else None
        scored: list[tuple[float, int]] = []
        for i, row in enumerate(self._matrix):
            if allowed_set is not None and i not in allowed_set:
                continue
            dot = sum(a * b for a, b in zip(q, row))
            dn = math.sqrt(sum(x * x for x in row)) or 1.0
            scored.append((dot / (qn * dn), i))
        scored.sort(key=lambda t: (-t[0], t[1]))
        return [(self.docs[i], s) for s, i in scored[:top_k]]


class SentenceTransformerDense(DenseRetriever):
    """Real dense retrieval using sentence-transformers + FAISS.

    Uses BAAI/bge-m3 (or any SentenceTransformer-compatible model) to encode
    corpus units and queries. All vectors are L2-normalised so inner product
    equals cosine similarity. FAISS IndexFlatIP provides exact nearest-neighbour
    search.

    Build once, query many. The index is held in memory (~580 MB for 145k
    vectors at 1024 dimensions). No index is persisted to disk by default;
    callers that want persistence can save/load via FAISS API separately.

    Parameters
    ----------
    docs : sequence of RetrievalDocument
        Corpus units to encode.
    model_name : str
        HuggingFace model identifier (default ``"paraphrase-multilingual-MiniLM-L12-v2"``).
    query_prefix : str
        Prefix prepended to queries before encoding. Set to ``""`` for models
        that do not use a query prefix (e.g. paraphrase-multilingual-MiniLM).
    doc_prefix : str
        Prefix prepended to document texts before encoding.
    batch_size : int
        Encoding batch size. Reduce if memory-constrained.
    normalize : bool
        If True, L2-normalise all vectors so inner product = cosine similarity.
    """

    name = "dense"

    def __init__(
        self,
        docs: Sequence[RetrievalDocument],
        model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
        query_prefix: str = "",
        doc_prefix: str = "",
        batch_size: int = 64,
        normalize: bool = True,
    ) -> None:
        import numpy as np
        import faiss

        self.model_name = model_name
        self.query_prefix = query_prefix
        self.doc_prefix = doc_prefix
        self.batch_size = batch_size
        self.normalize = normalize

        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(model_name)

        self.docs = list(docs)
        n_docs = len(self.docs)
        if n_docs == 0:
            self._index: Any = None
            self._dim = 0
            self._build_time_s = 0.0
            self._encode_time_s = 0.0
            return

        import time
        t0 = time.perf_counter()

        texts = [self.doc_prefix + doc.text for doc in self.docs]
        all_embeddings = self._model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            normalize_embeddings=normalize,
            convert_to_numpy=True,
        )

        t_encode = time.perf_counter()
        self._encode_time_s = t_encode - t0

        self._dim = int(all_embeddings.shape[1])
        self._index = faiss.IndexFlatIP(self._dim)
        self._index.add(all_embeddings.astype(np.float32))

        self._build_time_s = time.perf_counter() - t0
        self._n_vectors = self._index.ntotal

    def embed(self, text: str) -> list[float]:
        """Encode a single text into a dense vector."""
        import numpy as np
        prefixed = self.query_prefix + text
        vec = self._model.encode(
            [prefixed],
            normalize_embeddings=self.normalize,
            convert_to_numpy=True,
        )
        return vec[0].tolist()

    def search(
        self,
        query: str,
        top_k: int = 10,
        allowed: list[int] | None = None,
    ) -> list[tuple[RetrievalDocument, float]]:
        """Encode the query, search FAISS, return ranked (doc, score) pairs.

        When *allowed* is provided, only those document indices are returned
        (FAISS does not support masked search on IndexFlatIP, so we fall back
        to brute-force scoring over the allowed set).
        """
        if self._index is None or self._index.ntotal == 0:
            return []

        import numpy as np

        q_vec = self._model.encode(
            [self.query_prefix + query],
            normalize_embeddings=self.normalize,
            convert_to_numpy=True,
        ).astype(np.float32)

        if allowed is not None:
            allowed_set = set(allowed)
            scored: list[tuple[float, int]] = []
            for i in range(self._index.ntotal):
                if i not in allowed_set:
                    continue
                doc_vec = self._index.reconstruct(i)
                score = float(np.dot(q_vec[0], doc_vec))
                scored.append((score, i))
            scored.sort(key=lambda t: (-t[0], t[1]))
            return [(self.docs[i], s) for s, i in scored[:top_k]]

        scores, indices = self._index.search(q_vec, min(top_k, self._index.ntotal))
        results: list[tuple[RetrievalDocument, float]] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            results.append((self.docs[idx], float(score)))
        return results

    def stats(self) -> dict[str, Any]:
        """Return build statistics for reporting."""
        return {
            "model": self.model_name,
            "n_docs": len(self.docs),
            "dim": self._dim,
            "build_time_s": round(self._build_time_s, 2),
            "encode_time_s": round(self._encode_time_s, 2),
            "n_vectors": getattr(self, "_n_vectors", 0),
            "normalize": self.normalize,
        }

    @classmethod
    def from_prebuilt(
        cls,
        docs: Sequence[RetrievalDocument],
        index_path: str | Path,
        model_name: str = "BAAI/bge-m3",
        query_prefix: str = "",
        doc_prefix: str = "",
        normalize: bool = True,
        embeddings_path: str | Path | None = None,
    ) -> SentenceTransformerDense:
        """Load a pre-built FAISS index instead of encoding documents.

        This avoids re-encoding 145k+ documents when only query encoding
        changes (e.g. correcting the query prefix protocol).

        Parameters
        ----------
        docs : sequence of RetrievalDocument
            The corpus documents (needed to map FAISS indices back to documents).
        index_path : str or Path
            Path to a FAISS index file (required).
        model_name : str
            HuggingFace model identifier.
        query_prefix : str
            Prefix prepended to queries before encoding.
        doc_prefix : str
            Stored for consistency; not used at load time.
        normalize : bool
            Whether embeddings are L2-normalised.
        embeddings_path : str or Path or None
            Optional path to numpy embeddings file for validation only.
            Not loaded into RAM for search — the FAISS index holds the vectors.
        """
        import time
        from pathlib import Path as _Path

        index_path = _Path(index_path)
        if not index_path.exists():
            raise FileNotFoundError(f"FAISS index not found: {index_path}")

        instance = cls.__new__(cls)
        instance.model_name = model_name
        instance.query_prefix = query_prefix
        instance.doc_prefix = doc_prefix
        instance.normalize = normalize
        instance.docs = list(docs)

        from sentence_transformers import SentenceTransformer
        instance._model = SentenceTransformer(model_name)

        import faiss
        t0 = time.perf_counter()
        instance._index = faiss.read_index(str(index_path))
        instance._load_time_s = time.perf_counter() - t0

        instance._dim = instance._index.d
        instance._n_vectors = instance._index.ntotal
        instance._build_time_s = 0.0
        instance._encode_time_s = 0.0

        # Optional validation: check embedding count matches index
        if embeddings_path is not None:
            embeddings_path = _Path(embeddings_path)
            if embeddings_path.exists():
                import numpy as np
                emb = np.load(str(embeddings_path))
                if emb.shape[0] != instance._n_vectors:
                    raise ValueError(
                        f"Embedding count mismatch: index has {instance._n_vectors}, "
                        f"file has {emb.shape[0]}"
                    )

        return instance


class UnavailableDense(DenseRetriever):
    """The honest default: dense retrieval is not available in this environment."""

    name = "unavailable"

    def __init__(self, docs=None, reason: str = "no embedding model or numpy available") -> None:
        self.reason = reason
        # Intentionally no matrix is built.

    def search(self, query: str, top_k: int = 10,
               allowed: list[int] | None = None):
        return []


@dataclass
class _HashSpec:
    dim: int = 256


class HashDense(DenseRetriever):
    """DETERMINISTIC TEST DOUBLE — NOT semantic retrieval.

    Maps text to a bag of hashed character 5-grams, then to a fixed-dimension
    vector. Preserves *lexical* similarity only, which is enough to exercise
    the dense code path, the fusion logic and the provenance plumbing in tests.
    Results from this class must never be reported as dense-retrieval metrics.
    """

    name = "hash-test-double"

    def __init__(self, docs, spec: _HashSpec | None = None) -> None:
        self.spec = spec or _HashSpec()
        super().__init__(docs)

    def embed(self, text: str) -> list[float]:
        text = " ".join(text.lower().split())
        grams = Counter(text[i:i + 5] for i in range(max(len(text) - 4, 1)))
        vec = [0.0] * self.spec.dim
        for gram, count in grams.items():
            slot = 0
            for ch in gram:
                slot = (slot * 131 + ord(ch)) % self.spec.dim
            vec[slot] += float(count)
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

"""Retrieval over the released RAG corpus.

Scope and honesty notes
-----------------------
This subpackage answers one question: can hybrid retrieval find the right
Sthanakvasi-context passages? It is a prototype evaluation layer, NOT the
production retrieval system.

Components:
    documents.py  load release records with provenance joined from the manifest
    bm25.py       Okapi BM25 lexical index (Indic/Prakrit exact terms matter)
    dense.py      DenseRetriever interface; SentenceTransformerDense (Task 16);
                  HashDense is a deterministic TEST DOUBLE, never for metrics
    fusion.py     RRF fusion + HybridRetriever (prefilter -> BM25 (+dense) -> RRF)
    contract.py   Canonical retrieval result schema and evidence contract

Dense retrieval uses sentence-transformers + FAISS (Task 16) when a model
is available. The dense channel is now a real, measured retrieval signal.
"""

from svk_corpus.retrieval.documents import (RetrievalDocument,
                                            iter_release_documents,
                                            load_corpus,
                                            load_source_scope)
from svk_corpus.retrieval.bm25 import BM25Index, BM25Result, tokenize
from svk_corpus.retrieval.dense import (DenseRetriever, HashDense,
                                        SentenceTransformerDense,
                                        UnavailableDense)
from svk_corpus.retrieval.fusion import (HybridRetriever, RetrievalResult,
                                         reciprocal_rank_fusion)
from svk_corpus.retrieval.contract import (CanonicalResult, RetrievalChannel,
                                           NormalizationEvidence,
                                           MetadataMatchEvidence,
                                           ContractViolation,
                                           validate_result, assert_valid,
                                           validate_batch)

__all__ = [
    "RetrievalDocument", "iter_release_documents", "load_corpus",
    "load_source_scope", "BM25Index", "BM25Result", "tokenize",
    "DenseRetriever", "HashDense", "SentenceTransformerDense", "UnavailableDense",
    "HybridRetriever", "RetrievalResult", "reciprocal_rank_fusion",
    "CanonicalResult", "RetrievalChannel", "NormalizationEvidence",
    "MetadataMatchEvidence", "ContractViolation",
    "validate_result", "assert_valid", "validate_batch",
]

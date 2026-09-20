"""Okapi BM25 lexical retrieval.

Why BM25 is the backbone here
-----------------------------
The corpus is dominated by Prakrit/Sanskrit terms transliterated or written in
Indic scripts, dictionary headwords, and proper names. Exact lexical match is
often precisely the signal ("samayika", "टिप्पणी", "Ardha-Magadhi"), and a
classic Okapi BM25 over a lightweight tokenizer is small, deterministic and
fully auditable — no model weights involved.

Task 9: the token stream (index and query alike) passes through the
deterministic romanization folding + evidenced alias expansion in
`normalization.py`. This changes ONLY what terms can match — corpus text,
results and provenance are untouched (results carry original documents).
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field

from svk_corpus.retrieval.documents import RetrievalDocument
from svk_corpus.retrieval.normalization import expand_query_text, tokenize

# Task 9: tokenization now lives in normalization.py so that index text and
# queries pass through the identical deterministic pipeline (tokenize -> fold
# -> phrase rules -> alias OR-expansion). Re-exported here for compatibility.
__all__ = ["BM25Index", "BM25Result", "tokenize"]


@dataclass
class BM25Result:
    doc: RetrievalDocument
    score: float
    rank: int


class BM25Index:
    """In-memory Okapi BM25 (k1, b) over RetrievalDocuments."""

    def __init__(self, docs: list[RetrievalDocument],
                 k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.docs = docs
        self._doc_counts: list[Counter[str]] = []
        self._doc_len: list[int] = []
        self._postings: dict[str, list[int]] = {}
        for i, doc in enumerate(docs):
            counts = Counter(expand_query_text(doc.search_text))
            self._doc_counts.append(counts)
            length = sum(counts.values())
            self._doc_len.append(length)
            for term in counts:
                self._postings.setdefault(term, []).append(i)
        self.N = len(docs)
        self._avgdl = (sum(self._doc_len) / self.N) if self.N else 0.0
        # idf per the Okapi formulation with 0.5 smoothing.
        self._idf: dict[str, float] = {
            term: math.log((self.N - len(plist) + 0.5) / (len(plist) + 0.5) + 1.0)
            for term, plist in self._postings.items()
        }

    def search(self, query: str, top_k: int = 10,
               allowed: list[int] | None = None) -> list[BM25Result]:
        """Return the top_k docs by BM25 score; `allowed` restricts by doc index.

        The query goes through the same deterministic folding/alias expansion
        as the index, so romanization variants meet in folded-term space.
        """
        q_terms = expand_query_text(query)
        allowed_set = set(allowed) if allowed is not None else None
        scores: dict[int, float] = {}
        for term in q_terms:
            plist = self._postings.get(term)
            if not plist:
                continue
            idf = self._idf[term]
            for di in plist:
                if allowed_set is not None and di not in allowed_set:
                    continue
                f = self._doc_counts[di][term]
                denom = f + self.k1 * (1 - self.b + self.b * self._doc_len[di] / self._avgdl)
                scores[di] = scores.get(di, 0.0) + idf * f * (self.k1 + 1) / denom
        ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
        out: list[BM25Result] = []
        for rank, (di, score) in enumerate(ranked[:top_k], 1):
            out.append(BM25Result(self.docs[di], score, rank))
        return out

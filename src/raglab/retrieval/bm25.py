from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from collections.abc import Sequence

import numpy as np

from raglab.core import Document, SearchResult

_TOKEN_RE = re.compile(r"(?u)\b\w+\b")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


class BM25Retriever:
    """Okapi BM25 implemented directly for inspectable lexical retrieval."""

    name = "bm25"

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        if k1 <= 0:
            raise ValueError("k1 must be positive")
        if not 0 <= b <= 1:
            raise ValueError("b must be between 0 and 1")
        self.k1 = k1
        self.b = b
        self._doc_ids: list[str] = []
        self._doc_lengths: np.ndarray | None = None
        self._avg_doc_length = 0.0
        self._postings: dict[str, list[tuple[int, int]]] = {}
        self._document_frequency: dict[str, int] = {}

    def index(self, documents: Sequence[Document]) -> None:
        doc_ids = [doc.id for doc in documents]
        if self._doc_lengths is not None and doc_ids == self._doc_ids:
            return
        if not documents:
            raise ValueError("Cannot index an empty document collection")

        postings: dict[str, list[tuple[int, int]]] = defaultdict(list)
        document_frequency: dict[str, int] = defaultdict(int)
        lengths = np.zeros(len(documents), dtype=np.float32)

        for doc_index, document in enumerate(documents):
            terms = tokenize(document.searchable_text)
            lengths[doc_index] = len(terms)
            frequencies = Counter(terms)
            for term, tf in frequencies.items():
                postings[term].append((doc_index, tf))
                document_frequency[term] += 1

        self._doc_ids = doc_ids
        self._doc_lengths = lengths
        self._avg_doc_length = float(lengths.mean()) if len(lengths) else 0.0
        self._postings = dict(postings)
        self._document_frequency = dict(document_frequency)

    def _idf(self, term: str) -> float:
        n_docs = len(self._doc_ids)
        df = self._document_frequency.get(term, 0)
        return math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))

    def retrieve(self, query: str, k: int) -> list[SearchResult]:
        if self._doc_lengths is None:
            raise RuntimeError("BM25Retriever must be indexed before retrieval")
        if k <= 0:
            raise ValueError("k must be positive")

        scores = np.zeros(len(self._doc_ids), dtype=np.float64)
        avgdl = self._avg_doc_length or 1.0

        for term in set(tokenize(query)):
            idf = self._idf(term)
            for doc_index, tf in self._postings.get(term, []):
                doc_length = float(self._doc_lengths[doc_index])
                denominator = tf + self.k1 * (1 - self.b + self.b * doc_length / avgdl)
                scores[doc_index] += idf * (tf * (self.k1 + 1)) / denominator

        k = min(k, len(self._doc_ids))
        candidate_indices = np.argpartition(scores, -k)[-k:]
        ordered = candidate_indices[np.argsort(scores[candidate_indices])[::-1]]

        return [
            SearchResult(
                doc_id=self._doc_ids[int(index)],
                score=float(scores[int(index)]),
                rank=rank,
            )
            for rank, index in enumerate(ordered, start=1)
        ]

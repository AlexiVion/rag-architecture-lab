from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from numpy.typing import NDArray

from raglab.core import Document, SearchResult
from raglab.embeddings import EmbeddingProvider


def _l2_normalize(matrix: NDArray[np.float32]) -> NDArray[np.float32]:
    if matrix.ndim == 1:
        matrix = matrix.reshape(1, -1)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms = np.where(norms == 0.0, 1.0, norms)
    return (matrix / norms).astype(np.float32, copy=False)


class DenseRetriever:
    """In-memory dense retriever using cosine similarity implemented with NumPy."""

    name = "dense"

    def __init__(self, embeddings: EmbeddingProvider) -> None:
        self.embeddings = embeddings
        self._doc_ids: list[str] = []
        self._matrix: NDArray[np.float32] | None = None

    def index(self, documents: Sequence[Document]) -> None:
        doc_ids = [doc.id for doc in documents]
        if self._matrix is not None and doc_ids == self._doc_ids:
            return
        if not documents:
            raise ValueError("Cannot index an empty document collection")

        matrix = self.embeddings.encode([doc.searchable_text for doc in documents])
        if matrix.ndim != 2 or matrix.shape[0] != len(documents):
            raise ValueError("Embedding provider returned an unexpected matrix shape")

        self._doc_ids = doc_ids
        self._matrix = _l2_normalize(matrix)

    def retrieve(self, query: str, k: int) -> list[SearchResult]:
        if self._matrix is None:
            raise RuntimeError("DenseRetriever must be indexed before retrieval")
        if k <= 0:
            raise ValueError("k must be positive")

        query_vector = _l2_normalize(self.embeddings.encode([query]))[0]
        scores = self._matrix @ query_vector
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

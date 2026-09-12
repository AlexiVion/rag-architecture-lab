from __future__ import annotations

from collections.abc import Sequence

from raglab.core import Document, SearchResult
from raglab.fusion import reciprocal_rank_fusion
from raglab.retrieval.base import Retriever


class HybridRetriever:
    """Hybrid retriever that fuses dense and sparse rankings with RRF."""

    name = "hybrid"

    def __init__(
        self,
        dense: Retriever,
        sparse: Retriever,
        candidate_k: int = 100,
        rrf_constant: int = 60,
    ) -> None:
        if candidate_k <= 0:
            raise ValueError("candidate_k must be positive")
        self.dense = dense
        self.sparse = sparse
        self.candidate_k = candidate_k
        self.rrf_constant = rrf_constant

    def index(self, documents: Sequence[Document]) -> None:
        self.dense.index(documents)
        self.sparse.index(documents)

    def retrieve(self, query: str, k: int) -> list[SearchResult]:
        candidate_k = max(k, self.candidate_k)
        dense_results = self.dense.retrieve(query, candidate_k)
        sparse_results = self.sparse.retrieve(query, candidate_k)
        return reciprocal_rank_fusion(
            [dense_results, sparse_results],
            k=k,
            rrf_constant=self.rrf_constant,
        )

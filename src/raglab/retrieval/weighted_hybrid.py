from __future__ import annotations

from collections.abc import Sequence

from raglab.core import Document, SearchResult
from raglab.fusion import weighted_rank_fusion
from raglab.retrieval.base import Retriever


class WeightedHybridRetriever:
    """Research variant: RRF with a predeclared dense contribution weight.

    This is an experimental alternative, not a replacement for HybridRetriever.
    """

    def __init__(
        self,
        dense: Retriever,
        sparse: Retriever,
        *,
        dense_weight: float,
        sparse_weight: float = 1.0,
        candidate_k: int = 100,
        rrf_constant: int = 60,
    ) -> None:
        if candidate_k <= 0 or rrf_constant < 0:
            raise ValueError("Invalid candidate depth or RRF constant")
        # Also validates positive finite weighting at construction time.
        weighted_rank_fusion(
            [[], []],
            [dense_weight, sparse_weight],
            k=1,
            rrf_constant=rrf_constant,
        )
        self.dense = dense
        self.sparse = sparse
        self.dense_weight = dense_weight
        self.sparse_weight = sparse_weight
        self.candidate_k = candidate_k
        self.rrf_constant = rrf_constant
        self.name = f"hybrid-dense-{dense_weight:g}"

    def index(self, documents: Sequence[Document]) -> None:
        self.dense.index(documents)
        self.sparse.index(documents)

    def retrieve(self, query: str, k: int) -> list[SearchResult]:
        if k <= 0:
            raise ValueError("k must be positive")
        depth = max(k, self.candidate_k)
        return weighted_rank_fusion(
            [self.dense.retrieve(query, depth), self.sparse.retrieve(query, depth)],
            [self.dense_weight, self.sparse_weight],
            k=k,
            rrf_constant=self.rrf_constant,
        )

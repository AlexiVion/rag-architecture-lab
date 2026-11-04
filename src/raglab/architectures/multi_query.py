from __future__ import annotations

from collections.abc import Callable, Sequence

from raglab.core import Document, SearchResult
from raglab.fusion import reciprocal_rank_fusion
from raglab.retrieval.base import Retriever


class MultiQueryRetriever:
    """Fuse original and explicitly provided query variants using RRF.

    Reformulation is injected so experiments can compare deterministic rules,
    offline precomputed queries, or a local model without hidden API calls.
    """

    name = "multi-query"

    def __init__(
        self,
        base: Retriever,
        reformulate: Callable[[str], Sequence[str]],
        *,
        max_queries: int = 3,
        candidate_k: int = 100,
        rrf_constant: int = 60,
    ) -> None:
        if max_queries <= 0 or candidate_k <= 0 or rrf_constant < 0:
            raise ValueError("Invalid multi-query budget")
        self.base = base
        self.reformulate = reformulate
        self.max_queries = max_queries
        self.candidate_k = candidate_k
        self.rrf_constant = rrf_constant

    def index(self, documents: Sequence[Document]) -> None:
        self.base.index(documents)

    def retrieve(self, query: str, k: int) -> list[SearchResult]:
        if k <= 0:
            raise ValueError("k must be positive")
        if not query.strip():
            raise ValueError("query must not be empty")
        variants: list[str] = []
        seen: set[str] = set()
        for raw in [query, *self.reformulate(query)]:
            variant = raw.strip()
            key = variant.casefold()
            if not variant or key in seen:
                continue
            seen.add(key)
            variants.append(variant)
            if len(variants) == self.max_queries:
                break

        rankings = [self.base.retrieve(q, max(k, self.candidate_k)) for q in variants]
        return reciprocal_rank_fusion(rankings, k=k, rrf_constant=self.rrf_constant)

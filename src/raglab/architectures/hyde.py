from __future__ import annotations

from collections.abc import Callable, Sequence

from raglab.core import Document, SearchResult
from raglab.retrieval.base import Retriever


class HyDERetriever:
    """Retrieve using a hypothetical passage supplied by an injected generator.

    Intended for dense retrieval; the experiment must account for the cost and
    hallucination risks of generating the hypothetical passage.
    """

    name = "hyde"

    def __init__(
        self,
        base: Retriever,
        hypothetical_passage: Callable[[str], str],
    ) -> None:
        self.base = base
        self.hypothetical_passage = hypothetical_passage

    def index(self, documents: Sequence[Document]) -> None:
        self.base.index(documents)

    def retrieve(self, query: str, k: int) -> list[SearchResult]:
        if k <= 0:
            raise ValueError("k must be positive")
        candidate = self.hypothetical_passage(query).strip()
        if not candidate:
            return self.base.retrieve(query, k)
        return self.base.retrieve(candidate, k)

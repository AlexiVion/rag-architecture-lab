from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence

from raglab.core import Document, SearchResult
from raglab.retrieval.base import Retriever


class AdaptiveRetriever:
    """Route to named retrievers with a predeclared deterministic policy."""

    name = "adaptive"

    def __init__(
        self,
        routes: Mapping[str, Retriever],
        router: Callable[[str], str],
        *,
        default_route: str,
    ) -> None:
        if not routes or default_route not in routes:
            raise ValueError("A valid default route is required")
        self.routes = dict(routes)
        self.router = router
        self.default_route = default_route

    def index(self, documents: Sequence[Document]) -> None:
        visited: set[int] = set()
        for retriever in self.routes.values():
            if id(retriever) in visited:
                continue
            visited.add(id(retriever))
            retriever.index(documents)

    def retrieve(self, query: str, k: int) -> list[SearchResult]:
        if k <= 0:
            raise ValueError("k must be positive")
        route = self.router(query)
        return self.routes.get(route, self.routes[self.default_route]).retrieve(query, k)

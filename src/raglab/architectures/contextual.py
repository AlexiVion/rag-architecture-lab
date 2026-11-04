from __future__ import annotations

from collections.abc import Callable, Sequence

from raglab.core import Document, SearchResult
from raglab.retrieval.base import Retriever


class ContextualRetriever:
    """Index precomputed contextual prefixes without changing parent IDs.

    The augmenter may use human-written metadata or a separately benchmarked
    local model. This adapter performs no hidden generation or paid calls.
    """

    name = "contextual"

    def __init__(self, base: Retriever, augment: Callable[[Document], str]) -> None:
        self.base = base
        self.augment = augment

    def index(self, documents: Sequence[Document]) -> None:
        contextualized: list[Document] = []
        for document in documents:
            prefix = self.augment(document).strip()
            text = f"{prefix}\n{document.text}" if prefix else document.text
            contextualized.append(Document(id=document.id, title=document.title, text=text))
        self.base.index(contextualized)

    def retrieve(self, query: str, k: int) -> list[SearchResult]:
        return self.base.retrieve(query, k)

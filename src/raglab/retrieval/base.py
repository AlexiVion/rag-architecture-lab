from __future__ import annotations

from typing import Protocol, Sequence

from raglab.core import Document, SearchResult


class Retriever(Protocol):
    name: str

    def index(self, documents: Sequence[Document]) -> None: ...

    def retrieve(self, query: str, k: int) -> list[SearchResult]: ...

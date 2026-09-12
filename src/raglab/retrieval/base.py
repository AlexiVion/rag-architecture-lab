from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from raglab.core import Document, SearchResult


class Retriever(Protocol):
    name: str

    def index(self, documents: Sequence[Document]) -> None: ...

    def retrieve(self, query: str, k: int) -> list[SearchResult]: ...

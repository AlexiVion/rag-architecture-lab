from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Document:
    id: str
    text: str
    title: str = ""

    @property
    def searchable_text(self) -> str:
        if self.title and self.text:
            return f"{self.title}\n{self.text}"
        return self.title or self.text


@dataclass(frozen=True, slots=True)
class Query:
    id: str
    text: str


@dataclass(frozen=True, slots=True)
class SearchResult:
    doc_id: str
    score: float
    rank: int

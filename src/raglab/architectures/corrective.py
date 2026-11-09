from __future__ import annotations

from collections.abc import Callable, Sequence

from raglab.core import Document, SearchResult
from raglab.retrieval.base import Retriever

# True means the primary evidence is acceptable; False triggers fallback.
EvidenceJudge = Callable[[str, Sequence[SearchResult]], bool]


class CorrectiveRetriever:
    """A bounded retrieval-recovery baseline with an injected evidence judge.

    Does not imply that the judge establishes semantic support. It is an
    experimental policy, measured by false corrections and recovery quality.
    """

    name = "corrective"

    def __init__(
        self,
        primary: Retriever,
        fallback: Retriever,
        judge: EvidenceJudge,
    ) -> None:
        self.primary = primary
        self.fallback = fallback
        self.judge = judge

    def index(self, documents: Sequence[Document]) -> None:
        self.primary.index(documents)
        if self.fallback is not self.primary:
            self.fallback.index(documents)

    def retrieve(self, query: str, k: int) -> list[SearchResult]:
        if k <= 0:
            raise ValueError("k must be positive")
        results = self.primary.retrieve(query, k)
        if results and self.judge(query, results):
            return results
        return self.fallback.retrieve(query, k)

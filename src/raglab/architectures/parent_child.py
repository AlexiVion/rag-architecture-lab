from __future__ import annotations

from collections.abc import Sequence

from raglab.core import Document, SearchResult
from raglab.retrieval.base import Retriever


class ParentChildRetriever:
    """Rank simple fixed-size child passages and return original parent IDs.

    Chunking is intentionally character-based and deterministic: this is a
    baseline for a chunk-size/overlap ablation, not a semantic chunker.
    """

    name = "parent-child"

    def __init__(
        self,
        child_retriever: Retriever,
        *,
        chunk_chars: int = 512,
        overlap_chars: int = 64,
        candidate_k: int = 100,
    ) -> None:
        if chunk_chars <= 0 or not 0 <= overlap_chars < chunk_chars or candidate_k <= 0:
            raise ValueError("Invalid chunk size, overlap or candidate budget")
        self.child_retriever = child_retriever
        self.chunk_chars = chunk_chars
        self.overlap_chars = overlap_chars
        self.candidate_k = candidate_k
        self._parent_by_child: dict[str, str] = {}

    def index(self, documents: Sequence[Document]) -> None:
        if len({document.id for document in documents}) != len(documents):
            raise ValueError("Parent document IDs must be unique")
        children: list[Document] = []
        self._parent_by_child = {}
        stride = self.chunk_chars - self.overlap_chars
        for parent_index, parent in enumerate(documents):
            source = parent.text or parent.title
            for chunk_index, start in enumerate(range(0, len(source), stride)):
                fragment = source[start : start + self.chunk_chars]
                if not fragment:
                    continue
                child_id = f"child:{parent_index}:{chunk_index}"
                children.append(Document(id=child_id, title=parent.title, text=fragment))
                self._parent_by_child[child_id] = parent.id
                if start + self.chunk_chars >= len(source):
                    break
        if not children:
            raise ValueError("No parent document contains text to index")
        self.child_retriever.index(children)

    def retrieve(self, query: str, k: int) -> list[SearchResult]:
        if k <= 0:
            raise ValueError("k must be positive")
        child_results = self.child_retriever.retrieve(query, max(k, self.candidate_k))
        parents: list[SearchResult] = []
        seen: set[str] = set()
        for result in child_results:
            parent_id = self._parent_by_child.get(result.doc_id)
            if parent_id is None or parent_id in seen:
                continue
            seen.add(parent_id)
            parents.append(
                SearchResult(doc_id=parent_id, score=result.score, rank=len(parents) + 1)
            )
            if len(parents) == k:
                break
        return parents

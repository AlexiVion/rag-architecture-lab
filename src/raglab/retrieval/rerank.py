from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from raglab.core import Document, SearchResult
from raglab.retrieval.base import Retriever


class PairScorer(Protocol):
    """Score query-document pairs; higher scores rank first."""

    def score(self, query: str, documents: Sequence[str]) -> list[float]: ...


class CrossEncoderScorer:
    """Local cross-encoder scorer backed by sentence-transformers."""

    def __init__(self, model_name: str) -> None:
        try:
            from sentence_transformers import CrossEncoder
        except ImportError as exc:  # pragma: no cover - exercised in benchmark environments
            raise RuntimeError(
                "Cross-encoder reranking requires the benchmark dependencies. "
                'Install them with: pip install -e ".[benchmark]"'
            ) from exc

        self.model_name = model_name
        self._model = CrossEncoder(model_name)

    def score(self, query: str, documents: Sequence[str]) -> list[float]:
        if not documents:
            return []
        pairs = [(query, document) for document in documents]
        values = self._model.predict(pairs, show_progress_bar=False)
        return [float(value) for value in values]


class RerankingRetriever:
    """Retrieve a candidate set, then reorder it with a stronger pairwise scorer."""

    def __init__(
        self,
        base: Retriever,
        scorer: PairScorer,
        candidate_k: int = 50,
        name: str | None = None,
    ) -> None:
        if candidate_k <= 0:
            raise ValueError("candidate_k must be positive")
        self.base = base
        self.scorer = scorer
        self.candidate_k = candidate_k
        self.name = name or f"{base.name}-rerank"
        self._documents: dict[str, Document] = {}

    def index(self, documents: Sequence[Document]) -> None:
        self._documents = {document.id: document for document in documents}
        self.base.index(documents)

    def retrieve(self, query: str, k: int) -> list[SearchResult]:
        if k <= 0:
            return []

        candidate_k = max(k, self.candidate_k)
        candidates = self.base.retrieve(query, candidate_k)
        if not candidates:
            return []

        texts: list[str] = []
        kept_candidates: list[SearchResult] = []
        for candidate in candidates:
            document = self._documents.get(candidate.doc_id)
            if document is None:
                continue
            kept_candidates.append(candidate)
            texts.append(document.searchable_text)

        scores = self.scorer.score(query, texts)
        if len(scores) != len(kept_candidates):
            raise RuntimeError("Pair scorer returned a different number of scores than documents")

        reranked = sorted(
            zip(kept_candidates, scores, strict=True),
            key=lambda item: (-item[1], item[0].rank),
        )
        return [
            SearchResult(doc_id=candidate.doc_id, score=score, rank=rank)
            for rank, (candidate, score) in enumerate(reranked[:k], start=1)
        ]

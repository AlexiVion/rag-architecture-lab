from __future__ import annotations

from collections.abc import Sequence

from raglab.core import Document, SearchResult
from raglab.retrieval import RerankingRetriever


class StaticRetriever:
    name = "static"

    def __init__(self, results: list[SearchResult]) -> None:
        self._results = results

    def index(self, documents: Sequence[Document]) -> None:
        self.documents = list(documents)

    def retrieve(self, query: str, k: int) -> list[SearchResult]:
        return self._results[:k]


class MappingScorer:
    def __init__(self, scores: dict[str, float]) -> None:
        self.scores = scores
        self.seen_documents: list[str] = []

    def score(self, query: str, documents: Sequence[str]) -> list[float]:
        self.seen_documents = list(documents)
        return [self.scores[document] for document in documents]


def test_reranker_reorders_candidates_by_pair_score() -> None:
    documents = [
        Document(id="d1", text="weak match"),
        Document(id="d2", text="strong match"),
        Document(id="d3", text="medium match"),
    ]
    base = StaticRetriever(
        [
            SearchResult(doc_id="d1", score=9.0, rank=1),
            SearchResult(doc_id="d2", score=8.0, rank=2),
            SearchResult(doc_id="d3", score=7.0, rank=3),
        ]
    )
    scorer = MappingScorer(
        {"weak match": 0.1, "strong match": 0.9, "medium match": 0.5}
    )
    retriever = RerankingRetriever(base, scorer, candidate_k=3, name="test-rerank")

    retriever.index(documents)
    results = retriever.retrieve("query", 2)

    assert [result.doc_id for result in results] == ["d2", "d3"]
    assert [result.rank for result in results] == [1, 2]
    assert [result.score for result in results] == [0.9, 0.5]


def test_reranker_only_scores_candidate_set() -> None:
    documents = [
        Document(id="d1", text="one"),
        Document(id="d2", text="two"),
        Document(id="d3", text="three"),
    ]
    base = StaticRetriever(
        [
            SearchResult(doc_id="d1", score=3.0, rank=1),
            SearchResult(doc_id="d2", score=2.0, rank=2),
            SearchResult(doc_id="d3", score=1.0, rank=3),
        ]
    )
    scorer = MappingScorer({"one": 0.1, "two": 0.2, "three": 0.9})
    retriever = RerankingRetriever(base, scorer, candidate_k=2)

    retriever.index(documents)
    results = retriever.retrieve("query", 1)

    assert scorer.seen_documents == ["one", "two"]
    assert [result.doc_id for result in results] == ["d2"]


def test_reranker_uses_base_rank_as_deterministic_tie_breaker() -> None:
    documents = [Document(id="d1", text="one"), Document(id="d2", text="two")]
    base = StaticRetriever(
        [
            SearchResult(doc_id="d1", score=2.0, rank=1),
            SearchResult(doc_id="d2", score=1.0, rank=2),
        ]
    )
    scorer = MappingScorer({"one": 0.5, "two": 0.5})
    retriever = RerankingRetriever(base, scorer, candidate_k=2)

    retriever.index(documents)
    results = retriever.retrieve("query", 2)

    assert [result.doc_id for result in results] == ["d1", "d2"]

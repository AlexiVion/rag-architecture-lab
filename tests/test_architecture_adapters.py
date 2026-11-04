from __future__ import annotations

from collections.abc import Sequence

import pytest

from raglab.architectures import (
    AdaptiveRetriever,
    ContextualRetriever,
    CorrectiveRetriever,
    HyDERetriever,
    MultiQueryRetriever,
    ParentChildRetriever,
)
from raglab.core import Document, SearchResult


class SpyRetriever:
    name = "spy"

    def __init__(self, rankings: dict[str, list[str]] | None = None):
        self.rankings = rankings or {}
        self.queries: list[str] = []
        self.index_count = 0
        self.documents: list[Document] = []

    def index(self, documents: Sequence[Document]) -> None:
        self.index_count += 1
        self.documents = list(documents)

    def retrieve(self, query: str, k: int) -> list[SearchResult]:
        self.queries.append(query)
        ids = self.rankings.get(query, [d.id for d in self.documents])
        return [
            SearchResult(doc_id=doc_id, score=float(len(ids) - i), rank=i + 1)
            for i, doc_id in enumerate(ids[:k])
        ]


def test_multi_query_deduplicates_and_fuses_rankings() -> None:
    base = SpyRetriever({"original": ["a", "b"], "alternative": ["b", "c"]})
    arch = MultiQueryRetriever(
        base,
        lambda q: ["original", " alternative ", "ALTERNATIVE", ""],
        max_queries=2,
        candidate_k=3,
    )
    arch.index([Document("a", "A"), Document("b", "B"), Document("c", "C")])
    results = arch.retrieve("original", 3)
    assert base.queries == ["original", "alternative"]
    assert results[0].doc_id == "b"
    assert {result.doc_id for result in results} == {"a", "b", "c"}


def test_parent_child_returns_unique_original_parent_ids() -> None:
    child = SpyRetriever()
    arch = ParentChildRetriever(child, chunk_chars=4, overlap_chars=1, candidate_k=20)
    arch.index([Document("p1", "abcdefghij"), Document("p2", "klmnopqrst")])
    assert len(child.documents) > 2
    results = arch.retrieve("anything", 2)
    assert [item.doc_id for item in results] == ["p1", "p2"]
    assert [item.rank for item in results] == [1, 2]


def test_parent_child_rejects_duplicate_document_ids() -> None:
    arch = ParentChildRetriever(SpyRetriever())
    with pytest.raises(ValueError, match="unique"):
        arch.index([Document("x", "a"), Document("x", "b")])


def test_corrective_uses_fallback_on_failed_judge_or_empty_primary() -> None:
    primary = SpyRetriever({"q": ["primary"]})
    fallback = SpyRetriever({"q": ["fallback"]})
    arch = CorrectiveRetriever(primary, fallback, lambda q, ranked: False)
    arch.index([Document("primary", "A"), Document("fallback", "B")])
    assert arch.retrieve("q", 1)[0].doc_id == "fallback"
    assert primary.queries == ["q"]
    assert fallback.queries == ["q"]


def test_adaptive_routes_and_indexes_shared_retriever_once() -> None:
    bm = SpyRetriever({"named": ["lexical"]})
    dense = SpyRetriever({"semantic": ["dense"]})
    arch = AdaptiveRetriever(
        {"lex": bm, "alias": bm, "dense": dense},
        lambda q: "lex" if q == "named" else ("dense" if q == "semantic" else "other"),
        default_route="lex",
    )
    arch.index([Document("lexical", "A"), Document("dense", "B")])
    assert bm.index_count == 1
    assert dense.index_count == 1
    assert arch.retrieve("named", 1)[0].doc_id == "lexical"
    assert arch.retrieve("semantic", 1)[0].doc_id == "dense"
    assert arch.retrieve("unknown", 1)


def test_contextual_augmentation_preserves_document_id() -> None:
    spy = SpyRetriever()
    arch = ContextualRetriever(spy, lambda document: f"subject: {document.title}")
    arch.index([Document("d1", "example", title="Study")])
    assert spy.documents[0].id == "d1"
    assert spy.documents[0].text == "subject: Study\nexample"
    assert arch.retrieve("query", 1)[0].doc_id == "d1"


def test_hyde_uses_generated_passage_or_falls_back_to_question() -> None:
    spy = SpyRetriever()
    arch = HyDERetriever(spy, lambda q: "  hypothetical explanation  ")
    arch.index([Document("d", "text")])
    arch.retrieve("question", 1)
    assert spy.queries == ["hypothetical explanation"]
    empty = HyDERetriever(spy, lambda q: "")
    empty.retrieve("question", 1)
    assert spy.queries[-1] == "question"


def test_invalid_budgets_are_rejected() -> None:
    spy = SpyRetriever()
    with pytest.raises(ValueError):
        MultiQueryRetriever(spy, lambda q: [], max_queries=0)
    with pytest.raises(ValueError):
        ParentChildRetriever(spy, chunk_chars=4, overlap_chars=4)
    with pytest.raises(ValueError):
        AdaptiveRetriever({"a": spy}, lambda q: "a", default_route="missing")

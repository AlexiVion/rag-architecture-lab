from __future__ import annotations

import pytest

from raglab.core import Document, Query, SearchResult
from raglab.datasets import BenchmarkDataset
from raglab.diagnostics import diagnose_retrieval


class RankedRetriever:
    name = "toy"

    def __init__(self, ids):
        self.ids = ids
        self.indexed = False

    def index(self, documents):
        self.indexed = True

    def retrieve(self, query, k):
        assert self.indexed
        return [
            SearchResult(doc_id=doc_id, rank=i + 1, score=float(len(self.ids) - i))
            for i, doc_id in enumerate(self.ids[:k])
        ]


def toy_data():
    return BenchmarkDataset(
        id="tiny",
        documents=[
            Document("a", "first", title="First"),
            Document("b", "second", title="Second"),
            Document("c", "gold", title="Gold"),
        ],
        queries=[Query("1", "claim about the gold")],
        qrels={"1": {"c": 1}},
    )


def test_gold_beyond_context_but_within_candidates():
    result = diagnose_retrieval(
        toy_data(), query_id="1",
        retrievers={"hybrid": RankedRetriever(["a", "b", "c"])},
        candidate_k=3, context_k=2,
    )
    metrics = result["strategies"]["hybrid"]
    assert metrics["gold_ranks"]["c"] == 3
    assert metrics["recall_at_context_k"] == 0
    assert metrics["rerank_eligibility"]["10"]
    assert result["gold_documents"][0]["title"] == "Gold"


def test_absent_at_depth_is_not_called_unfindable():
    result = diagnose_retrieval(
        toy_data(), query_id="1",
        retrievers={"bm25": RankedRetriever(["b", "a"])},
        candidate_k=2, context_k=1,
    )
    assert result["strategies"]["bm25"]["gold_ranks"]["c"] is None
    assert result["strategies"]["bm25"]["recall_at_context_k"] == 0
    assert "out-of-depth" in result["limitations"][1]


def test_missing_query_invalid_depth_and_duplicates():
    with pytest.raises(ValueError, match="Query ID"):
        diagnose_retrieval(
            toy_data(), query_id="404", retrievers={"x": RankedRetriever(["a"])},
        )
    with pytest.raises(ValueError, match="context_k"):
        diagnose_retrieval(
            toy_data(), query_id="1", retrievers={"x": RankedRetriever(["a"])},
            candidate_k=1, context_k=2,
        )
    with pytest.raises(ValueError, match="duplicate"):
        diagnose_retrieval(
            toy_data(), query_id="1", retrievers={"x": RankedRetriever(["a", "a"])},
            candidate_k=2, context_k=1,
        )


def test_qrels_cannot_change_ranking():
    result = diagnose_retrieval(
        toy_data(), query_id="1",
        retrievers={"bm25": RankedRetriever(["a", "c", "b"])},
        candidate_k=3, context_k=1,
    )
    assert result["strategies"]["bm25"]["gold_ranks"]["c"] == 2
    assert result["strategies"]["bm25"]["top_context_results"][0]["doc_id"] == "a"

import math

from raglab.core import SearchResult
from raglab.evaluation.metrics import ndcg_at_k, recall_at_k, reciprocal_rank


def _result(doc_id: str, rank: int) -> SearchResult:
    return SearchResult(doc_id=doc_id, score=1.0 / rank, rank=rank)


def test_recall_at_k() -> None:
    results = [_result("a", 1), _result("x", 2), _result("b", 3)]
    qrels = {"a": 1, "b": 1}
    assert recall_at_k(results, qrels, 2) == 0.5
    assert recall_at_k(results, qrels, 3) == 1.0


def test_reciprocal_rank() -> None:
    results = [_result("x", 1), _result("b", 2)]
    assert reciprocal_rank(results, {"b": 1}, 10) == 0.5


def test_ndcg_at_k_binary() -> None:
    results = [_result("x", 1), _result("a", 2)]
    value = ndcg_at_k(results, {"a": 1}, 2)
    assert math.isclose(value, 1 / math.log2(3), rel_tol=1e-9)


def test_ndcg_supports_graded_relevance() -> None:
    results = [_result("b", 1), _result("a", 2)]
    qrels = {"a": 2, "b": 1}
    assert 0 < ndcg_at_k(results, qrels, 2) < 1

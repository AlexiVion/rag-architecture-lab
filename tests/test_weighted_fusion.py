import math

import pytest

from raglab.core import SearchResult
from raglab.fusion import reciprocal_rank_fusion, weighted_rank_fusion
from raglab.retrieval.weighted_hybrid import WeightedHybridRetriever


def ranked(*ids):
    return [SearchResult(doc_id=d, score=1.0, rank=i + 1) for i, d in enumerate(ids)]


class FakeRetriever:
    name = "fake"

    def __init__(self, ids):
        self.ids = ids
        self.index_calls = 0

    def index(self, documents):
        self.index_calls += 1

    def retrieve(self, query, k):
        return ranked(*self.ids[:k])


def test_equal_weight_fusion_matches_legacy_rrf():
    a = ranked("a", "b", "c")
    b = ranked("b", "c", "a")
    actual = weighted_rank_fusion([a, b], [1, 1], k=3)
    expected = reciprocal_rank_fusion([a, b], k=3)
    assert actual == expected


def test_dense_priority_can_promote_dense_only_evidence():
    # k=0 RRF makes the toy rank difference clear. Real comparisons
    # keep the established RRF constant 60 and use full development data.
    dense = ranked("gold", "a", "b")
    sparse = ranked("a", "b", "c")
    standard = weighted_rank_fusion(
        [dense, sparse], [1, 1], k=1, rrf_constant=0
    )
    prioritized = weighted_rank_fusion(
        [dense, sparse], [4, 1], k=1, rrf_constant=0
    )
    assert standard[0].doc_id == "a"
    assert prioritized[0].doc_id == "gold"


@pytest.mark.parametrize("weights", [[0, 1], [-1, 1], [math.nan, 1], [math.inf, 1]])
def test_invalid_weights_rejected(weights):
    with pytest.raises(ValueError, match="positive"):
        weighted_rank_fusion([ranked("a"), ranked("b")], weights, k=2)


def test_invalid_depth_or_weight_count_rejected():
    with pytest.raises(ValueError):
        weighted_rank_fusion([ranked("a")], [1, 2], k=1)
    with pytest.raises(ValueError):
        weighted_rank_fusion([ranked("a")], [1], k=0)


def test_weighted_hybrid_reuses_component_retrievers():
    dense = FakeRetriever(["gold", "a"])
    sparse = FakeRetriever(["a", "b"])
    arch = WeightedHybridRetriever(dense, sparse, dense_weight=3, candidate_k=3)
    arch.index([])
    assert dense.index_calls == 1 and sparse.index_calls == 1
    results = arch.retrieve("question", 2)
    assert results[0].doc_id in {"gold", "a"}
    assert [r.rank for r in results] == [1, 2]

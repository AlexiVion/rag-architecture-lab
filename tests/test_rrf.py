from raglab.core import SearchResult
from raglab.fusion import reciprocal_rank_fusion


def test_rrf_rewards_documents_present_in_multiple_rankings() -> None:
    dense = [
        SearchResult("a", 0.9, 1),
        SearchResult("b", 0.8, 2),
        SearchResult("c", 0.7, 3),
    ]
    sparse = [
        SearchResult("b", 10.0, 1),
        SearchResult("d", 9.0, 2),
        SearchResult("a", 8.0, 3),
    ]

    fused = reciprocal_rank_fusion([dense, sparse], k=4)
    assert fused[0].doc_id in {"a", "b"}
    assert {result.doc_id for result in fused[:2]} == {"a", "b"}

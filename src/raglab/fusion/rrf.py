from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from raglab.core import SearchResult


def reciprocal_rank_fusion(
    rankings: Sequence[Sequence[SearchResult]],
    k: int,
    rrf_constant: int = 60,
) -> list[SearchResult]:
    """Fuse ranked result lists using Reciprocal Rank Fusion.

    RRF score(d) = sum(1 / (rrf_constant + rank_i(d))).
    """
    if k <= 0:
        raise ValueError("k must be positive")
    if rrf_constant < 0:
        raise ValueError("rrf_constant cannot be negative")

    scores: dict[str, float] = defaultdict(float)
    for ranking in rankings:
        seen: set[str] = set()
        for result in ranking:
            if result.doc_id in seen:
                continue
            seen.add(result.doc_id)
            scores[result.doc_id] += 1.0 / (rrf_constant + result.rank)

    ordered = sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:k]
    return [
        SearchResult(doc_id=doc_id, score=score, rank=rank)
        for rank, (doc_id, score) in enumerate(ordered, start=1)
    ]

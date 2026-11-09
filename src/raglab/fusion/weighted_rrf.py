from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Sequence

from raglab.core import SearchResult


def weighted_rank_fusion(
    rankings: Sequence[Sequence[SearchResult]],
    weights: Sequence[float],
    *,
    k: int,
    rrf_constant: int = 60,
) -> list[SearchResult]:
    """Weighted RRF; with all weights=1 it matches ordinary RRF.

    RRF_w(d) = sum_i weight_i / (c + rank_i(d)).
    """
    if k <= 0 or rrf_constant < 0:
        raise ValueError("k must be positive and rrf_constant nonnegative")
    if not rankings or len(rankings) != len(weights):
        raise ValueError("One weight per nonempty set of rankings is required")
    if any(not math.isfinite(w) or w <= 0 for w in weights):
        raise ValueError("All weights must be positive and finite")

    scores: dict[str, float] = defaultdict(float)
    for ranking, weight in zip(rankings, weights, strict=True):
        seen: set[str] = set()
        for result in ranking:
            if result.doc_id in seen:
                continue
            if result.rank <= 0:
                raise ValueError("Ranks must be one-based positive integers")
            seen.add(result.doc_id)
            scores[result.doc_id] += weight / (rrf_constant + result.rank)
    ordered = sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:k]
    return [
        SearchResult(doc_id=doc_id, score=score, rank=i)
        for i, (doc_id, score) in enumerate(ordered, start=1)
    ]

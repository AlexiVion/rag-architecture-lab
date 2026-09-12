from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

from raglab.core import SearchResult


def _relevant(qrels: Mapping[str, int]) -> set[str]:
    return {doc_id for doc_id, relevance in qrels.items() if relevance > 0}


def recall_at_k(results: Sequence[SearchResult], qrels: Mapping[str, int], k: int) -> float:
    relevant = _relevant(qrels)
    if not relevant:
        return 0.0
    retrieved = {result.doc_id for result in results[:k]}
    return len(relevant & retrieved) / len(relevant)


def reciprocal_rank(results: Sequence[SearchResult], qrels: Mapping[str, int], k: int) -> float:
    relevant = _relevant(qrels)
    for rank, result in enumerate(results[:k], start=1):
        if result.doc_id in relevant:
            return 1.0 / rank
    return 0.0


def _dcg(relevances: Sequence[int]) -> float:
    return sum((2**rel - 1) / math.log2(rank + 1) for rank, rel in enumerate(relevances, start=1))


def ndcg_at_k(results: Sequence[SearchResult], qrels: Mapping[str, int], k: int) -> float:
    retrieved_relevances = [qrels.get(result.doc_id, 0) for result in results[:k]]
    ideal_relevances = sorted((rel for rel in qrels.values() if rel > 0), reverse=True)[:k]
    ideal = _dcg(ideal_relevances)
    if ideal == 0:
        return 0.0
    return _dcg(retrieved_relevances) / ideal

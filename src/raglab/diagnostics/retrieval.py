from __future__ import annotations

import time
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from raglab.datasets import BenchmarkDataset
from raglab.retrieval.base import Retriever


def diagnose_retrieval(
    dataset: BenchmarkDataset,
    *,
    query_id: str,
    retrievers: Mapping[str, Retriever],
    candidate_k: int = 100,
    context_k: int = 5,
) -> dict[str, Any]:
    """Locate qrel-relevant documents in first-stage candidate pools.

    Labels are read only after retrieval, for offline analysis. A missing
    position means not seen within candidate_k, not missing from the corpus.
    """
    if not retrievers:
        raise ValueError("At least one retriever is required")
    if candidate_k <= 0 or context_k <= 0 or context_k > candidate_k:
        raise ValueError("Require 0 < context_k <= candidate_k")
    query = next((q for q in dataset.queries if q.id == str(query_id)), None)
    if query is None:
        raise ValueError(f"Query ID {query_id!r} is not in dataset {dataset.id!r}")
    gold = dataset.qrels.get(query.id)
    if not gold:
        raise ValueError(f"Query ID {query_id!r} has no positive qrels")

    docs = {document.id: document for document in dataset.documents}
    gold_ids = set(gold)
    gold_docs = [
        {
            "doc_id": doc_id,
            "relevance": gold[doc_id],
            "title": docs[doc_id].title if doc_id in docs else None,
            "present_in_corpus": doc_id in docs,
            "text_preview": docs[doc_id].text[:280] if doc_id in docs else None,
        }
        for doc_id in sorted(gold_ids)
    ]
    strategies: dict[str, dict[str, Any]] = {}
    for name, retriever in retrievers.items():
        start = time.perf_counter()
        retriever.index(dataset.documents)
        indexing_ms = (time.perf_counter() - start) * 1000.0

        start = time.perf_counter()
        ranked = retriever.retrieve(query.text, candidate_k)
        retrieval_ms = (time.perf_counter() - start) * 1000.0
        ids = [r.doc_id for r in ranked]
        if len(set(ids)) != len(ids):
            raise ValueError(f"{name} returned duplicate document IDs")
        positions = {doc_id: i for i, doc_id in enumerate(ids, start=1)}
        relevant_in_context = sum(
            1 for doc_id in gold_ids
            if positions.get(doc_id, candidate_k + 1) <= context_k
        )
        strategies[name] = {
            "indexing_ms": indexing_ms,
            "retrieval_ms": retrieval_ms,
            "returned_candidates": len(ranked),
            "relevant_in_context": relevant_in_context,
            "recall_at_context_k": relevant_in_context / len(gold_ids),
            "gold_ranks": {
                doc_id: positions.get(doc_id) for doc_id in sorted(gold_ids)
            },
            "rerank_eligibility": {
                str(depth): any(
                    positions.get(doc_id, candidate_k + 1) <= min(depth, candidate_k)
                    for doc_id in gold_ids
                )
                for depth in (10, 20, 50, 100)
            } if name == "hybrid" else None,
            "top_context_results": [
                {
                    "doc_id": result.doc_id,
                    "rank": rank,
                    "score": result.score,
                    "title": docs[result.doc_id].title
                    if result.doc_id in docs else None,
                    "qrel_relevant": result.doc_id in gold_ids,
                }
                for rank, result in enumerate(ranked[:context_k], start=1)
            ],
        }
    return {
        "schema_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "dataset": dataset.id,
        "query_id": query.id,
        "query": query.text,
        "candidate_k": candidate_k,
        "context_k": context_k,
        "gold_documents": gold_docs,
        "strategies": strategies,
        "limitations": [
            "Qrels used only after ranking for offline analysis; not inference.",
            "Null gold rank means out-of-depth, not absent from corpus.",
            "SciFact qrels may omit other potentially useful evidence.",
            "Indexing and retrieval times are reported separately.",
            "No cross-encoder or text generation is run.",
        ],
    }

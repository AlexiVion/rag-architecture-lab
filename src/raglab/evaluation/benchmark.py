from __future__ import annotations

import platform
import statistics
import time
from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any

import numpy as np

from raglab.datasets import BenchmarkDataset
from raglab.evaluation.metrics import ndcg_at_k, recall_at_k, reciprocal_rank
from raglab.retrieval.base import Retriever


def run_benchmark(
    dataset: BenchmarkDataset,
    retriever: Retriever,
    ks: Iterable[int] = (5, 10),
) -> dict[str, Any]:
    ks = sorted(set(int(k) for k in ks))
    if not ks or ks[0] <= 0:
        raise ValueError("All K values must be positive")

    retriever.index(dataset.documents)
    max_k = max(ks)
    per_query: list[dict[str, Any]] = []
    latencies_ms: list[float] = []

    for query in dataset.queries:
        started = time.perf_counter()
        results = retriever.retrieve(query.text, max_k)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        latencies_ms.append(elapsed_ms)

        qrels = dataset.qrels[query.id]
        metrics: dict[str, float] = {}
        for k in ks:
            metrics[f"recall@{k}"] = recall_at_k(results, qrels, k)
            metrics[f"mrr@{k}"] = reciprocal_rank(results, qrels, k)
            metrics[f"ndcg@{k}"] = ndcg_at_k(results, qrels, k)

        per_query.append(
            {
                "query_id": query.id,
                "query": query.text,
                "latency_ms": elapsed_ms,
                "metrics": metrics,
                "results": [
                    {"doc_id": result.doc_id, "rank": result.rank, "score": result.score}
                    for result in results
                ],
            }
        )

    metric_names = list(per_query[0]["metrics"].keys())
    aggregate_metrics = {
        metric: statistics.fmean(item["metrics"][metric] for item in per_query)
        for metric in metric_names
    }

    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset": dataset.id,
        "pipeline": retriever.name,
        "document_count": len(dataset.documents),
        "query_count": len(dataset.queries),
        "k_values": ks,
        "metrics": aggregate_metrics,
        "latency_ms": {
            "mean": statistics.fmean(latencies_ms),
            "median": statistics.median(latencies_ms),
            "p95": float(np.percentile(np.asarray(latencies_ms), 95)),
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "queries": per_query,
    }

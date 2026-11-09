from __future__ import annotations

import os
import platform
import subprocess
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from raglab.architectures import (
    AdaptiveRetriever,
    ContextualRetriever,
    CorrectiveRetriever,
    HyDERetriever,
    MultiQueryRetriever,
    ParentChildRetriever,
)
from raglab.core.fingerprint import fingerprint_documents
from raglab.datasets import BenchmarkDataset, load_ir_dataset
from raglab.embeddings import SentenceTransformerEmbeddings
from raglab.evaluation.benchmark import run_benchmark
from raglab.retrieval import BM25Retriever, DenseRetriever, HybridRetriever
from raglab.retrieval.base import Retriever

ARCHITECTURES = {
    "multi-query",
    "parent-child",
    "contextual",
    "hyde",
    "corrective",
    "adaptive",
}
BASE_RETRIEVERS = {"bm25", "dense", "hybrid"}


def _git_sha() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=3,
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return os.environ.get("RAGLAB_GIT_SHA")


def _dict(value: Any, label: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def run_experiment(
    spec: Mapping[str, Any],
    *,
    dataset: BenchmarkDataset | None = None,
    embeddings: Any = None,
) -> dict[str, Any]:
    """Run one architecture against a fresh, same-corpus retrieval baseline.

    Uses the existing benchmark implementation. It deliberately labels the
    output exploratory; publication as canonical requires a local verification
    record with pinned model revisions and environment metadata.
    """
    experiment_id = str(spec.get("experiment_id", "")).strip()
    if not experiment_id:
        raise ValueError("experiment_id is required")
    architecture = str(spec.get("architecture", ""))
    if architecture not in ARCHITECTURES:
        raise ValueError(f"Unsupported architecture: {architecture!r}")
    base_name = str(spec.get("base", "bm25"))
    if base_name not in BASE_RETRIEVERS:
        raise ValueError(f"Unsupported base retriever: {base_name!r}")
    ks = sorted({int(k) for k in spec.get("k", [5, 10])})
    if not ks or ks[0] <= 0:
        raise ValueError("k must contain positive integers")
    params = _dict(spec.get("params", {}), "params")
    dataset_id = str(spec.get("dataset", "beir/scifact/test"))
    if dataset is None:
        dataset = load_ir_dataset(
            dataset_id,
            limit_queries=spec.get("limit_queries"),
        )
    else:
        dataset_id = dataset.id

    embedding_model = str(
        spec.get("embedding_model", "sentence-transformers/all-MiniLM-L6-v2")
    )
    needs_embeddings = (
        base_name != "bm25"
        or (
            architecture == "adaptive"
            and any(
                value in {"dense", "hybrid"}
                for value in _dict(params.get("routes", {}), "routes").values()
            )
        )
        or (
            architecture == "corrective"
            and params.get("fallback_base", "bm25") in {"dense", "hybrid"}
        )
    )
    if needs_embeddings and embeddings is None:
        embeddings = SentenceTransformerEmbeddings(embedding_model)

    def make_base(name: str) -> Retriever:
        bm25 = BM25Retriever()
        if name == "bm25":
            return bm25
        if embeddings is None:
            raise ValueError("Dense or hybrid strategies require an embedding provider")
        dense = DenseRetriever(embeddings)
        if name == "dense":
            return dense
        if name == "hybrid":
            return HybridRetriever(dense, bm25)
        raise ValueError(f"Unsupported route retriever: {name}")

    baseline = make_base(base_name)
    candidate_base = make_base(base_name)

    if architecture == "multi-query":
        variants = _dict(params.get("query_variants", {}), "query_variants")
        if not variants:
            raise ValueError("multi-query requires precomputed query_variants")
        candidate: Retriever = MultiQueryRetriever(
            candidate_base,
            lambda query: variants.get(query, []),
            max_queries=int(params.get("max_queries", 3)),
            candidate_k=int(params.get("candidate_k", 100)),
        )
    elif architecture == "parent-child":
        candidate = ParentChildRetriever(
            candidate_base,
            chunk_chars=int(params.get("chunk_chars", 512)),
            overlap_chars=int(params.get("overlap_chars", 64)),
            candidate_k=int(params.get("candidate_k", 100)),
        )
    elif architecture == "contextual":
        prefixes = _dict(params.get("prefixes", {}), "prefixes")
        if not prefixes:
            raise ValueError("contextual requires precomputed prefixes by document ID")
        candidate = ContextualRetriever(candidate_base, lambda d: prefixes.get(d.id, ""))
    elif architecture == "hyde":
        passages = _dict(params.get("hypothetical_passages", {}), "hypothetical_passages")
        if not passages:
            raise ValueError("hyde requires precomputed hypothetical_passages by query text")
        candidate = HyDERetriever(candidate_base, lambda query: passages.get(query, ""))
    elif architecture == "corrective":
        if "min_primary_score" not in params:
            raise ValueError("corrective requires predeclared min_primary_score")
        threshold = float(params["min_primary_score"])
        fallback_name = str(params.get("fallback_base", "bm25"))
        if fallback_name not in BASE_RETRIEVERS:
            raise ValueError("Invalid fallback_base")
        candidate = CorrectiveRetriever(
            candidate_base,
            make_base(fallback_name),
            lambda q, ranked: any(r.score >= threshold for r in ranked),
        )
    else:
        routes = _dict(params.get("routes", {}), "routes")
        if not routes:
            raise ValueError("adaptive requires route names -> base retrievers")
        for value in routes.values():
            if value not in BASE_RETRIEVERS:
                raise ValueError(f"Invalid route retriever: {value!r}")
        route_map = _dict(params.get("route_map", {}), "route_map")
        default_route = str(params.get("default_route", ""))
        candidate = AdaptiveRetriever(
            {name: make_base(base_type) for name, base_type in routes.items()},
            lambda query: str(route_map.get(query, default_route)),
            default_route=default_route,
        )

    baseline_metrics = run_benchmark(dataset, baseline, ks)
    candidate_metrics = run_benchmark(dataset, candidate, ks)
    return {
        "schema_version": 1,
        "experiment_id": experiment_id,
        "created_at": datetime.now(UTC).isoformat(),
        "publication_status": "exploratory",
        "git_sha": _git_sha(),
        "dataset": {
            "id": dataset_id,
            "document_count": len(dataset.documents),
            "query_count": len(dataset.queries),
            "fingerprint": fingerprint_documents(dataset.documents),
        },
        "configuration": {
            "architecture": architecture,
            "baseline": base_name,
            "candidate": architecture,
            "k": ks,
            "params": params,
            "embedding_model": embedding_model if needs_embeddings else None,
            "seed": spec.get("seed"),
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "results": [baseline_metrics, candidate_metrics],
        "limitations": [
            "No correctness or semantic faithfulness benchmark in this runner",
            "No model revision lock, warmed latency policy or uncertainty estimate",
            "Precomputed query maps and thresholds must be fixed without test-label leakage",
        ],
    }

from __future__ import annotations

import pytest

from raglab.core import Document, Query
from raglab.datasets import BenchmarkDataset
from raglab.experiments import run_experiment


def toy_data() -> BenchmarkDataset:
    return BenchmarkDataset(
        id="toy",
        documents=[
            Document("a", "apple pie recipe"),
            Document("b", "banana recipe"),
            Document("c", "apple orchard"),
        ],
        queries=[Query("q1", "apple"), Query("q2", "banana")],
        qrels={"q1": {"a": 1, "c": 1}, "q2": {"b": 1}},
    )


def test_parent_child_experiment_emits_matched_exploratory_results() -> None:
    result = run_experiment(
        {
            "experiment_id": "RET-04-test",
            "architecture": "parent-child",
            "base": "bm25",
            "k": [1, 2],
            "params": {"chunk_chars": 8, "overlap_chars": 2, "candidate_k": 10},
        },
        dataset=toy_data(),
    )
    assert result["publication_status"] == "exploratory"
    assert result["dataset"]["fingerprint"]
    assert len(result["results"]) == 2
    assert all(r["query_count"] == 2 for r in result["results"])
    assert result["results"][0]["pipeline"] == "bm25"
    assert result["results"][1]["pipeline"] == "parent-child"


def test_runner_rejects_missing_precomputed_variants() -> None:
    with pytest.raises(ValueError, match="precomputed"):
        run_experiment(
            {"experiment_id": "RET-03-test", "architecture": "multi-query"},
            dataset=toy_data(),
        )


def test_multi_query_runs_without_paid_model_dependencies() -> None:
    result = run_experiment(
        {
            "experiment_id": "RET-03-test",
            "architecture": "multi-query",
            "base": "bm25",
            "k": [1],
            "params": {"query_variants": {"apple": ["orchard"]}, "max_queries": 2},
        },
        dataset=toy_data(),
    )
    assert result["results"][1]["pipeline"] == "multi-query"


def test_adaptive_experiment_with_bm25_only_routes() -> None:
    result = run_experiment(
        {
            "experiment_id": "RET-08-test",
            "architecture": "adaptive",
            "base": "bm25",
            "k": [1],
            "params": {
                "routes": {"short": "bm25"},
                "route_map": {"apple": "short"},
                "default_route": "short",
            },
        },
        dataset=toy_data(),
    )
    assert result["results"][1]["pipeline"] == "adaptive"

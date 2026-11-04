from __future__ import annotations

import pytest

from raglab.evaluation.rerank_analysis import (
    analyze_rerank_artifact,
    rerank_report_markdown,
)


def _run(name: str, values: tuple[float, ...], latency: float) -> dict:
    return {
        "pipeline": name,
        "latency_ms": {"mean": latency},
        "queries": [
            {
                "query_id": str(index),
                "query": f"Claim {index}",
                "metrics": {metric: value for metric in (
                    "recall@5", "recall@10", "mrr@10", "ndcg@10"
                )},
                "results": [{"doc_id": f"d{index}", "rank": 1, "score": 1.0}],
            }
            for index, value in enumerate(values)
        ],
    }


def _payload(
    base: tuple[float, ...] = (0.5, 0.5, 0.5, 0.5),
    candidate: tuple[float, ...] = (0.25, 0.25, 0.25, 0.25),
) -> dict:
    return {
        "dataset": "beir/scifact/train",
        "results": [
            _run("hybrid", base, 10),
            _run("hybrid-rerank", candidate, 100),
        ],
    }


def test_measures_paired_negative_effect_and_latency():
    report = analyze_rerank_artifact(_payload(), bootstrap_replicates=100)
    metric = report["metrics"]["recall@5"]
    assert metric["delta"] == pytest.approx(-0.25)
    assert metric["ci95"] == pytest.approx([-0.25, -0.25])
    assert metric["losses"] == 4
    assert report["latency"]["mean_ratio"] == 10
    assert report["decision"] == "do_not_promote_rerank20_from_this_smoke"
    assert "Largest Recall@5 regressions" in rerank_report_markdown(report)


def test_query_mismatch_is_rejected():
    payload = _payload()
    payload["results"][1]["queries"][0]["query"] = "Other"
    with pytest.raises(ValueError, match="Different query"):
        analyze_rerank_artifact(payload, bootstrap_replicates=100)


def test_duplicate_queries_are_rejected():
    payload = _payload()
    payload["results"][0]["queries"][1]["query_id"] = "0"
    with pytest.raises(ValueError, match="duplicate query id"):
        analyze_rerank_artifact(payload, bootstrap_replicates=100)


def test_different_query_sets_are_rejected():
    payload = _payload()
    payload["results"][1]["queries"].pop()
    with pytest.raises(ValueError, match="query IDs differ"):
        analyze_rerank_artifact(payload, bootstrap_replicates=100)


def test_rejects_test_dataset_selection():
    payload = _payload()
    payload["dataset"] = "beir/scifact/test"
    with pytest.raises(ValueError, match="requires SciFact train"):
        analyze_rerank_artifact(payload, bootstrap_replicates=100)


def test_bootstrap_is_reproducible():
    payload = _payload(
        base=(0.0, 0.2, 0.4, 0.6),
        candidate=(0.0, 0.3, 0.2, 0.9),
    )
    first = analyze_rerank_artifact(payload, bootstrap_replicates=101, seed=9)
    second = analyze_rerank_artifact(payload, bootstrap_replicates=101, seed=9)
    assert first == second

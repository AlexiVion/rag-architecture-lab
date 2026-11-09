from __future__ import annotations

import pytest

from raglab.evaluation.paired_comparison import (
    analyze_fusion_artifact,
    to_markdown,
)


def _row(query_id: str, recall: float) -> dict:
    return {
        "query_id": query_id,
        "query": "Question " + query_id,
        "metrics": {
            "recall@5": recall,
            "recall@10": recall,
            "mrr@10": recall,
            "ndcg@10": recall,
        },
    }


def _fixture(
    baseline: tuple[float, ...] = (0.2, 0.2, 0.2, 0.2),
    candidate: tuple[float, ...] = (0.4, 0.4, 0.4, 0.4),
) -> dict:
    ids = ["a", "b", "c", "d"]
    return {
        "experiment_id": "RET-FUSION-01",
        "dataset": "beir/scifact/train",
        "git_sha": "toy",
        "results": [
            {
                "pipeline": "hybrid",
                "queries": [_row(i, value) for i, value in zip(ids, baseline)],
            },
            {
                "pipeline": "hybrid-dense-2",
                "queries": [_row(i, value) for i, value in zip(ids, candidate)],
            },
        ],
    }


def test_constant_gain_has_exact_bootstrap_interval():
    report = analyze_fusion_artifact(_fixture(), bootstrap_replicates=100)
    metric = report["comparisons"][0]["metrics"]["recall@5"]
    assert metric["delta"] == pytest.approx(0.2)
    assert metric["ci95"] == pytest.approx([0.2, 0.2])
    assert metric["wins"] == 4
    assert metric["losses"] == 0
    assert report["decision"] == "consider_frozen_held_out_candidate"
    assert "95% bootstrap" in to_markdown(report)


def test_losses_trigger_conservative_default():
    report = analyze_fusion_artifact(
        _fixture(candidate=(0.0, 0.0, 0.0, 0.0)),
        bootstrap_replicates=100,
    )
    assert report["decision"] == "retain_original_hybrid_for_now"
    assert report["comparisons"][0]["metrics"]["recall@5"]["losses"] == 4


def test_missing_or_mismatched_queries_fail():
    broken = _fixture()
    broken["results"][1]["queries"].pop()
    with pytest.raises(ValueError, match="query IDs"):
        analyze_fusion_artifact(broken, bootstrap_replicates=100)

    broken = _fixture()
    broken["results"][1]["queries"][0]["query"] = "different question"
    with pytest.raises(ValueError, match="different question"):
        analyze_fusion_artifact(broken, bootstrap_replicates=100)


def test_no_test_data_used_for_weight_selection():
    broken = _fixture()
    broken["dataset"] = "beir/scifact/test"
    with pytest.raises(ValueError, match="restricted to SciFact train"):
        analyze_fusion_artifact(broken, bootstrap_replicates=100)


def test_reproducible_paired_sampling():
    fixture = _fixture(
        baseline=(0.0, 0.5, 0.0, 0.5),
        candidate=(0.2, 0.3, 0.8, 0.7),
    )
    first = analyze_fusion_artifact(fixture, bootstrap_replicates=200, seed=13)
    second = analyze_fusion_artifact(fixture, bootstrap_replicates=200, seed=13)
    assert first == second


def test_invalid_replicate_count_fails():
    with pytest.raises(ValueError, match="At least 100"):
        analyze_fusion_artifact(_fixture(), bootstrap_replicates=99)

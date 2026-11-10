from __future__ import annotations

import pytest

from raglab.evaluation.ragability_conflict import (
    CONFLICT,
    NON_CONFLICT,
    build_conflict_pairs,
)
from raglab.evaluation.ragability_nli_comparison import compare_results


def sample_rows():
    rows = []
    for i in range(53):
        group = i + 1 if i < 43 else i - 42
        rows.append({
            "contradiction_ID": str(group),
            "WikiContradict_ID": "" if i == 41 else str(group + 100),
            "reasoning_required_c1c2": "categorical" if i % 2 == 0 else "numerical",
            "context_1": f"Station {group} was founded in 2001.",
            "context_2": f"Station {group} was founded in 2002.",
            "context_3_nc1_c2": f"Station {group} was founded in 2001.",
            "context_4_nc1_nc2_nc3": f"Station {group} is located in Dola.",
            "query_text": f"When was Station {group} founded?",
        })
    return rows


def result(model_id, perfect):
    pairs = build_conflict_pairs(sample_rows())
    cases = []
    for pair in pairs:
        prediction = (
            pair.expected if perfect else NON_CONFLICT
        )
        cases.append({
            **pair.public_dict(),
            "symmetric_prediction": prediction,
        })
    return {
        "experiment_id": "MICRO-RAGABILITY-01",
        "model": {
            "id": model_id,
            "revision": "model-revision",
            "parameter_count": 70_000_000,
            "weight_bytes": 100_000_000,
        },
        "dataset": {
            "dataset_id": "ofai/RagabilityCorpus",
            "dataset_revision": "dataset-revision",
            "source_sha256": "a" * 64,
            "row_count": 53,
            "unique_conflict_groups": 43,
        },
        "environment": {"peak_rss_bytes": 500_000_000},
        "inference_cost": {"total_batch_wall_ms": 1200.0},
        "evaluation": {"cases": cases},
    }


def test_matched_group_bootstrap_detects_clear_synthetic_difference():
    report = compare_results(
        result("perfect", True),
        result("always-no-conflict", False),
        repetitions=1000,
    )
    assert report["conclusion"] == "A_BETTER_ON_THIS_PUBLIC_BENCHMARK"
    assert report["point_metrics"]["model_a"]["accuracy"] == 1.0
    assert report["point_metrics"]["model_b"]["accuracy"] == pytest.approx(2 / 3)
    delta = report["paired_cluster_bootstrap_deltas"]["balanced_accuracy"]
    assert delta["mean_delta_a_minus_b"] == 0.5
    assert delta["percentile_95_ci"] == [0.5, 0.5]
    assert report["paired_correctness_discordance"] == {
        "a_only_correct": 106,
        "b_only_correct": 0,
        "both_correct": 212,
        "both_wrong": 0,
    }
    assert report["dataset"]["source_conflict_groups"] == 43


def test_comparison_rejects_different_dataset_fingerprints():
    a = result("a", True)
    b = result("b", False)
    b["dataset"]["source_sha256"] = "b" * 64
    with pytest.raises(ValueError, match="source_sha256"):
        compare_results(a, b, repetitions=1000)


def test_comparison_rejects_different_case_sets_or_labels():
    a = result("a", True)
    b = result("b", False)
    b["evaluation"]["cases"].pop()
    with pytest.raises(ValueError, match="identical 318"):
        compare_results(a, b, repetitions=1000)

    b = result("b", False)
    b["evaluation"]["cases"][0]["expected"] = (
        NON_CONFLICT if b["evaluation"]["cases"][0]["expected"] == CONFLICT
        else CONFLICT
    )
    with pytest.raises(ValueError, match="Gold labels differ"):
        compare_results(a, b, repetitions=1000)


def test_comparison_requires_group_resampling_not_individual_rows():
    a = result("a", True)
    b = result("b", False)
    a["dataset"]["unique_conflict_groups"] = 42
    with pytest.raises(ValueError, match="conflict group count"):
        compare_results(a, b, repetitions=1000)

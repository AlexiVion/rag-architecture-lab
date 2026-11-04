from __future__ import annotations

import numpy as np
import pytest

from raglab.core import Document, Query
from raglab.datasets import BenchmarkDataset
from raglab.evaluation.dev_case_design import design_dev_cases, write_dev_cases
from raglab.evaluation.dev_nli_pilot import (
    _logit_probabilities, format_nli_report, run_nli_pilot,
)


def build(tmp_path):
    dataset = BenchmarkDataset(
        id="beir/scifact/train",
        documents=[
            Document("a", "Scientific passage A", "Article A"),
            Document("b", "Scientific passage B", "Article B"),
            Document("c", "Scientific passage C", "Article C"),
        ],
        queries=[
            Query("q1", "Claim A"), Query("q2", "Claim B"), Query("q3", "Claim C"),
        ],
        qrels={
            "q1": {"a": 1}, "q2": {"b": 1}, "q3": {"c": 1},
        },
    )
    manifest, packets = design_dev_cases(dataset, query_count=3)
    suite = tmp_path / "train_suite"
    write_dev_cases(manifest, packets, output_dir=suite)
    return suite, dataset


def test_machine_predictions_are_not_human_labels(tmp_path):
    suite, dataset = build(tmp_path)
    before = {p.name: p.read_bytes() for p in suite.glob("DEV*.json")}
    received = []

    def predict(pairs):
        received.extend(pairs)
        return np.array([[0.0, 9.0, 0.0]] * len(pairs))

    report = run_nli_pilot(suite, dataset, predict=predict)
    assert len(received) == 6
    assert report["nli_scored_count"] == 6
    assert report["no_context_count"] == 3
    assert report["predicted_label_counts"]["entailment"] == 6
    assert report["human_semantic_labels"] == 0
    assert report["validated_semantic_accuracy"] is None if "validated_semantic_accuracy" in report else report["semantic_truth_status"] == "not_evaluated"
    assert report["abstention_threshold"] is None
    assert all(row["semantic_truth_verified"] is False for row in report["cases"])
    assert sum(row["runtime_policy"] == "abstain_no_context" for row in report["cases"]) == 3
    assert {p.name: p.read_bytes() for p in suite.glob("DEV*.json")} == before
    assert "not verified truth" in format_nli_report(report)


def test_no_logits_are_mistaken_for_probabilities():
    output = _logit_probabilities(np.array([[1000.0, 1002.0, 1001.0]]), 1)
    assert output.shape == (1, 3)
    assert sum(output[0]) == pytest.approx(1.0)
    assert output[0, 1] > output[0, 2] > output[0, 0]


def test_invalid_logits_shape_rejected():
    with pytest.raises(ValueError, match="prediction shape"):
        _logit_probabilities(np.zeros((2, 2)), 2)


def test_nonfinite_logits_rejected():
    with pytest.raises(ValueError, match="nonfinite"):
        _logit_probabilities(np.array([[1.0, np.nan, 0.0]]), 1)


def test_never_use_heldout_test_dataset(tmp_path):
    suite, dataset = build(tmp_path)
    dataset.id = "beir/scifact/test"
    with pytest.raises(ValueError, match="SciFact TRAIN"):
        run_nli_pilot(suite, dataset, predict=lambda _: np.ones((6, 3)))


def test_unknown_model_label_mapping_rejected(tmp_path):
    suite, dataset = build(tmp_path)
    with pytest.raises(ValueError, match="Unverified"):
        run_nli_pilot(
            suite, dataset, predict=lambda _: np.ones((6, 3)),
            model_id="unknown-model",
        )

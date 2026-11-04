from __future__ import annotations

import numpy as np
import pytest

from raglab.core import Document, Query
from raglab.datasets import BenchmarkDataset
from raglab.evaluation.dev_case_design import design_dev_cases, write_dev_cases
from raglab.evaluation.dev_nli_pilot import run_nli_pilot
from raglab.evaluation.nli_diagnostics import build_nli_diagnostic, diagnostic_markdown


def make_suite(tmp_path):
    dataset = BenchmarkDataset(
        id="beir/scifact/train",
        documents=[
            Document(f"d{i}", f"Scientific passage {i}", f"Study {i}")
            for i in range(6)
        ],
        queries=[Query(str(i), f"Claim {i}") for i in range(6)],
        qrels={str(i): {f"d{i}": 1} for i in range(6)},
    )
    manifest, packets = design_dev_cases(dataset, query_count=6)
    suite = tmp_path / "suite"
    write_dev_cases(manifest, packets, output_dir=suite)
    saved = run_nli_pilot(
        suite, dataset,
        predict=lambda pairs: np.tile([0.0, 0.0, 10.0], (len(pairs), 1)),
    )
    return suite, saved


def control_logits(pairs):
    assert len(pairs) == 3
    return np.array([[0, 10, 0], [10, 0, 0], [0, 0, 10]], dtype=float)


def test_all_neutral_diagnostic_can_still_pass_basic_controls(tmp_path):
    suite, saved = make_suite(tmp_path)
    report = build_nli_diagnostic(suite, saved, control_logits)
    assert report["all_nonempty_neutral"]
    assert report["control_probe_passed"]
    assert report["decision"] == "NO_GO_ALL_NEUTRAL_NO_DOMAIN_VALIDATION"
    assert report["overall"]["neutral"] == 12
    assert report["per_source_arm"]["qrel_relevant_candidate"]["neutral"] == 6
    assert report["per_source_arm"]["cross_query_alternate_candidate"]["neutral"] == 6
    assert report["no_context_controls"] == 6
    assert report["biomedical_accuracy"] is None
    assert "Simple model controls" in diagnostic_markdown(report)


def test_wrong_toy_classification_is_not_mistaken_for_working_classifier(tmp_path):
    suite, saved = make_suite(tmp_path)
    report = build_nli_diagnostic(
        suite, saved, lambda pairs: np.tile([0, 0, 10], (3, 1)),
    )
    assert not report["control_probe_passed"]
    assert report["decision"] == "NO_GO_BASIC_CONTROL_FAILED"


def test_bad_dataset_rejected(tmp_path):
    suite, saved = make_suite(tmp_path)
    saved["dataset"] = "beir/scifact/test"
    with pytest.raises(ValueError, match="SciFact TRAIN"):
        build_nli_diagnostic(suite, saved, control_logits)


def test_corrupted_saved_scores_are_rejected(tmp_path):
    suite, saved = make_suite(tmp_path)
    next(row for row in saved["cases"] if row["nli_prediction"])["softmax_scores_uncalibrated"] = {
        "contradiction": 0.5, "entailment": 0.5, "neutral": 0.5
    }
    with pytest.raises(ValueError, match="normalization"):
        build_nli_diagnostic(suite, saved, control_logits)

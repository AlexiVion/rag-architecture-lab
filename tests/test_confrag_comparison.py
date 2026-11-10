"""Independent matched-artifact validation: software fixtures, no live model."""
from __future__ import annotations

from copy import deepcopy

import pytest

from raglab.evaluation.confrag_comparison import (
    EXPECTED_DATASET_REVISION,
    EXPECTED_INPUT_HASH,
    EXPECTED_MODELS,
    EXPECTED_SOURCE_PREFIX_HASH,
    STATUS,
    _score,
    compare_reports,
)


def _reports():
    reports = []
    for model_key in ("deberta_xsmall", "minilm"):
        rows = []
        for i in range(240):
            diff = i < 130
            lexical = diff or i % 2 == 0
            predicted = i % (9 if model_key == "deberta_xsmall" else 7) == 0
            rows.append({
                "pair_id": f"pair-{i:03d}",
                "group_id": f"group-{i // 15}",
                "same_annotated_viewpoint": not diff,
                "contradicts_question_flag": i // 15 % 2 == 0,
                "lexical_predicts_different": lexical,
                "nli_predicts_different": predicted,
                "nli_raw_relation": "contradiction" if predicted else "neutral",
                "left_source_index": (i % 15) // 5 + 1,
                "right_source_index": (i % 15) % 5 + 2,
            })
        fake_score = _score(rows, "nli_predicts_different")
        reports.append({
            "status": STATUS, "model_key": model_key,
            "model": {
                "revision": EXPECTED_MODELS[model_key][0],
                "parameter_count": EXPECTED_MODELS[model_key][1],
            },
            "data": {
                "dataset_revision": EXPECTED_DATASET_REVISION,
                "inputs_sha256": EXPECTED_INPUT_HASH,
                "read_prefix_sha256": EXPECTED_SOURCE_PREFIX_HASH,
            },
            "cpu_cost": {"total_batch_wall_ms": 5000.0},
            "rows": rows,
            "metrics": {
                "fixed_nli_contradiction_argmax_as_viewpoint_proxy": fake_score
            },
        })
    return reports


def test_fixed_sources_and_source_group_pairing_are_exactly_required():
    first, second = _reports()
    report = compare_reports(first, second, repetitions=100)
    assert report["derived_pairs_not_independent"] == 240
    assert report["original_question_groups"] == 16
    assert report["labels"] == {
        "different_viewpoint_pairs": 130, "same_viewpoint_pairs": 110
    }
    assert all(v["pairs"] == 240 for v in report["scores"].values())
    assert "NOT_PAPER_VALIDATION" in report["status"]
    assert all(v["n_original_question_groups"] == 16
               for v in report["descriptive_paired_group_deltas"].values())


def test_bootstrap_is_deterministic_given_frozen_pairs_and_seed():
    first, second = _reports()
    a = compare_reports(first, second, repetitions=100, seed=42)
    b = compare_reports(first, second, repetitions=100, seed=42)
    assert a == b
    assert a["nli_three_way_label_agreement"]["pairs"] == 240


def test_source_hash_change_refused_and_no_false_cross_model_comparison():
    first, second = _reports()
    second["data"]["inputs_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="source revision/prefix/input"):
        compare_reports(first, second, repetitions=100)


def test_modified_pair_labels_and_corrupt_reported_metrics_refused():
    first, second = _reports()
    second["rows"][0]["same_annotated_viewpoint"] = True
    with pytest.raises(ValueError, match="Paired input labels"):
        compare_reports(first, second, repetitions=100)
    first, second = _reports()
    second["metrics"]["fixed_nli_contradiction_argmax_as_viewpoint_proxy"]["counts"]["tp"] += 1
    with pytest.raises(ValueError, match="Independent confusion"):
        compare_reports(first, second, repetitions=100)


def test_missing_ids_and_underpowered_bootstrap_refused():
    first, second = _reports()
    second["rows"].pop()
    with pytest.raises(ValueError, match="240 unique"):
        compare_reports(first, second, repetitions=100)
    first, second = _reports()
    with pytest.raises(ValueError, match="iterations"):
        compare_reports(first, second, repetitions=99)

from __future__ import annotations

import json

import pytest

from raglab.core import Document, Query
from raglab.datasets import BenchmarkDataset
from raglab.evaluation.dev_case_design import (
    ARM_ALTERNATE,
    ARM_EMPTY,
    ARM_WITH_REFERENCE,
    design_dev_cases,
    write_dev_cases,
)
from raglab.evaluation.semantic_review import summarize_review_packet


def sample_dataset():
    return BenchmarkDataset(
        id="beir/scifact/train",
        documents=[
            Document(id="a", title="A", text="Scientific abstract A"),
            Document(id="b", title="B", text="Scientific abstract B"),
            Document(id="c", title="C", text="Scientific abstract C"),
        ],
        queries=[
            Query(id="q3", text="Third scientific proposition"),
            Query(id="q1", text="First scientific proposition"),
            Query(id="q2", text="Second scientific proposition"),
        ],
        qrels={
            "q1": {"a": 1},
            "q2": {"b": 2},
            "q3": {"c": 1},
        },
    )


def test_all_three_arms_are_prepared_without_invented_truth_or_sufficiency():
    manifest, packets = design_dev_cases(sample_dataset(), query_count=3)
    assert manifest["case_count"] == 9
    assert manifest["arm_counts"] == {
        ARM_WITH_REFERENCE: 3,
        ARM_ALTERNATE: 3,
        ARM_EMPTY: 3,
    }
    assert len(packets) == 9
    for case in manifest["cases"]:
        packet = packets[case["case_id"]]
        assert packet["provenance"]["dataset"] == "beir/scifact/train"
        assert packet["provenance"]["review_arm"] == case["arm"]
        assert packet["review"]["expected_behavior"] == "unreviewed"
        assert packet["claims"] == []
        assert not packet["citation_gate"]["passed"]
        assert summarize_review_packet(packet)["review_status"] == "incomplete"
        assert summarize_review_packet(packet)["observed_behavior"] == "unknown"
        assert all(src["relevance"] == "unreviewed" for src in packet["sources"])
        if case["arm"] == ARM_EMPTY:
            assert packet["sources"] == []
        else:
            assert len(packet["sources"]) == 1


def test_query_selection_is_stable_across_input_order():
    dataset = sample_dataset()
    manifest, _ = design_dev_cases(dataset, query_count=2, seed=13)
    dataset.queries.reverse()
    second, _ = design_dev_cases(dataset, query_count=2, seed=13)
    assert [x["query_id"] for x in manifest["cases"]] == [
        x["query_id"] for x in second["cases"]
    ]


def test_test_set_is_rejected_before_case_construction():
    dataset = sample_dataset()
    dataset.id = "beir/scifact/test"
    with pytest.raises(ValueError, match="held-out test"):
        design_dev_cases(dataset, query_count=2)


def test_insufficient_queries_fail():
    with pytest.raises(ValueError, match="Not enough TRAIN queries"):
        design_dev_cases(sample_dataset(), query_count=4)


def test_files_are_new_private_snapshots(tmp_path):
    manifest, packets = design_dev_cases(sample_dataset(), query_count=2)
    path = tmp_path / "new-dev-suite"
    write_dev_cases(manifest, packets, output_dir=path)
    assert json.loads((path / "manifest.json").read_text())["case_count"] == 6
    assert len(list(path.glob("DEV*.json"))) == 6
    with pytest.raises(FileExistsError, match="refusing overwrite"):
        write_dev_cases(manifest, packets, output_dir=path)

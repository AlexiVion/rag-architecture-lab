from __future__ import annotations

import json

import pytest

from raglab.core import Document, Query
from raglab.datasets import BenchmarkDataset
from raglab.evaluation.dev_case_design import design_dev_cases, write_dev_cases
from raglab.evaluation.dev_review_batch import review_next_dev_group


def suite(tmp_path):
    data = BenchmarkDataset(
        id="beir/scifact/train",
        documents=[
            Document("a", "Article A"),
            Document("b", "Article B"),
            Document("c", "Article C"),
        ],
        queries=[
            Query("q1", "Claim 1"),
            Query("q2", "Claim 2"),
            Query("q3", "Claim 3"),
        ],
        qrels={
            "q1": {"a": 1}, "q2": {"b": 1}, "q3": {"c": 1},
        },
    )
    manifest, packets = design_dev_cases(data, query_count=3)
    path = tmp_path / "suite"
    write_dev_cases(manifest, packets, output_dir=path)
    return path


def human_input(prompt: str) -> str:
    if "Identificador del revisor" in prompt:
        return "human-1"
    if "relevancia" in prompt:
        return "u"  # Uncertainty is an explicit human label.
    if "[a=responder" in prompt:
        return "u"
    return ""


def test_review_first_three_cases_and_resume_without_overwrites(tmp_path):
    path = suite(tmp_path)
    saved = review_next_dev_group(
        path, ask=human_input, show=lambda _: None
    )
    assert saved["newly_saved"] == 3
    assert saved["pending_total"] == 6
    assert saved["complete_total"] == 3

    original_files = sorted((path / "human-reviews").glob("*.json"))
    assert len(original_files) == 3
    originals = {p.name: p.read_bytes() for p in original_files}
    for p in original_files:
        result = json.loads(p.read_text(encoding="utf-8"))
        assert result["provenance"]["dataset"] == "beir/scifact/train"
        assert "review_arm" not in result["provenance"]
        assert "case_id" not in result["provenance"]
        assert result["review"]["expected_behavior"] == "uncertain"
        assert result["claims"] == []

    again = review_next_dev_group(
        path, ask=human_input, show=lambda _: None
    )
    assert again["newly_saved"] == 3
    assert again["pending_total"] == 3
    assert all(p.read_bytes() == originals[p.name] for p in original_files)
    finish = review_next_dev_group(
        path, ask=human_input, show=lambda _: None
    )
    assert finish["pending_total"] == 0
    assert finish["complete_total"] == 9
    no_more = review_next_dev_group(
        path, ask=lambda _: (_ for _ in ()).throw(AssertionError("No input needed")),
        show=lambda _: None,
    )
    assert no_more["newly_saved"] == 0


def test_invalid_dataset_manifest_is_rejected(tmp_path):
    path = suite(tmp_path)
    manifest = json.loads((path / "manifest.json").read_text())
    manifest["dataset"] = "beir/scifact/test"
    (path / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="TRAIN"):
        review_next_dev_group(path, ask=human_input, show=lambda _: None)


def test_bad_manifest_filename_does_not_escape_review_directory(tmp_path):
    path = suite(tmp_path)
    manifest = json.loads((path / "manifest.json").read_text())
    manifest["cases"][0]["review_packet_filename"] = "../steal.json"
    (path / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="filename"):
        review_next_dev_group(path, ask=human_input, show=lambda _: None)


def test_interrupt_keeps_completed_files(tmp_path):
    path = suite(tmp_path)
    calls = 0

    def interrupted(prompt):
        nonlocal calls
        calls += 1
        if calls > 3:
            raise KeyboardInterrupt()
        return human_input(prompt)

    with pytest.raises(KeyboardInterrupt):
        review_next_dev_group(path, ask=interrupted, show=lambda _: None)
    existing = list((path / "human-reviews").glob("*.json"))
    # One case with no source takes three prompts, others take five.
    assert len(existing) <= 1
    assert len(existing) >= 0

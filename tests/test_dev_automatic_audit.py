from __future__ import annotations

import json

import pytest

from raglab.core import Document, Query
from raglab.datasets import BenchmarkDataset
from raglab.evaluation.dev_case_design import design_dev_cases, write_dev_cases
from raglab.evaluation.dev_automatic_audit import audit_dev_suite, audit_report_markdown


def sample():
    return BenchmarkDataset(
        id="beir/scifact/train",
        documents=[
            Document("d1", "Passage one", "One"),
            Document("d2", "Passage two", "Two"),
            Document("d3", "Passage three", "Three"),
        ],
        queries=[
            Query("q1", "Proposition one"),
            Query("q2", "Proposition two"),
            Query("q3", "Proposition three"),
        ],
        qrels={"q1": {"d1": 1}, "q2": {"d2": 1}, "q3": {"d3": 1}},
    )


def build(tmp_path):
    data = sample()
    manifest, packets = design_dev_cases(data, query_count=3)
    root = tmp_path / "suite"
    write_dev_cases(manifest, packets, output_dir=root)
    return root, data


def test_all_cases_are_audited_without_creating_human_labels(tmp_path):
    root, data = build(tmp_path)
    before = {p.name: p.read_bytes() for p in root.glob("DEV*.json")}
    report = audit_dev_suite(root, data)
    assert report["status"] == "structural_pass_semantics_not_evaluated"
    assert report["case_count"] == 9
    assert report["no_context_control_count"] == 3
    assert report["semantic_unassessed_count"] == 9
    assert report["existing_human_review_files"] == 0
    assert all(x["structural_integrity"] == "pass" for x in report["cases"])
    assert all(x["semantic_entailment"] == "not_evaluated" for x in report["cases"])
    assert "No semantic conclusions" in audit_report_markdown(report)
    assert {p.name: p.read_bytes() for p in root.glob("DEV*.json")} == before


def test_corpus_fingerprint_change_is_rejected(tmp_path):
    root, data = build(tmp_path)
    data.documents[0] = Document("d1", "Changed passage", "One")
    with pytest.raises(ValueError, match="fingerprint mismatch"):
        audit_dev_suite(root, data)


def test_tampered_source_text_is_rejected(tmp_path):
    root, data = build(tmp_path)
    path = root / "DEV001_qrel_relevant_candidate.json"
    packet = json.loads(path.read_text(encoding="utf-8"))
    packet["sources"][0]["text"] = "Tampered"
    path.write_text(json.dumps(packet), encoding="utf-8")
    with pytest.raises(ValueError, match="source text changed|source text"):
        audit_dev_suite(root, data)


def test_heldout_test_data_is_rejected(tmp_path):
    root, data = build(tmp_path)
    data.id = "beir/scifact/test"
    with pytest.raises(ValueError, match="SciFact TRAIN"):
        audit_dev_suite(root, data)


def test_does_not_confuse_crossquery_candidate_with_contradiction(tmp_path):
    root, data = build(tmp_path)
    report = audit_dev_suite(root, data)
    alternatives = [
        item for item in report["cases"]
        if item["arm"] == "cross_query_alternate_candidate"
    ]
    assert alternatives
    assert all(x["contradiction"] == "not_evaluated" for x in alternatives)
    assert all(x["semantic_relevance"] == "not_evaluated" for x in alternatives)

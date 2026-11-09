"""Synthetic tests of original saved M2 Qwen audit (no model downloads)."""
from __future__ import annotations

import json

import pytest

from raglab.evaluation.m2_live_audit import audit_saved_m2, citation_failure_reason
from raglab.evaluation.m2_live_smoke import MODEL_ID, run_control_cases


class FakeGenerator:
    name = "fake-generator"

    def __init__(self):
        self.outputs = iter([
            "The Orion system was built by Meridian Robotics.",
            "The Solis instrument came from Helios Instruments [S1].",
            "The Zenith launch was June 4, 2020 [S1].",
        ])

    def generate(self, *, system_prompt, user_prompt, max_new_tokens):
        return next(self.outputs)


def archive():
    return run_control_cases(FakeGenerator())


def test_audit_recomputes_original_syntax_and_preserves_semantic_unknown():
    data = archive()
    result = audit_saved_m2(data, "f" * 64, require_real_model=False)
    assert result["audit_status"] == "PASS_NO_NEW_MODEL_RUN"
    assert result["case_count"] == 4
    assert result["total_generator_calls"] == 3
    assert [r["diagnostic"] for r in result["cases"]] == [
        "no_bracketed_source_citations",
        "citation_syntax_passed",
        "citation_syntax_passed",
        "not_applicable_no_context",
    ]
    assert all(r["semantic_support"] == "NOT_EVALUATED" for r in result["cases"])


def test_json_roundtrip_normalizes_tuple_fields_without_losing_integrity():
    original = archive()
    # The in-memory RAGAnswer.to_dict() retains tuples for citation labels.
    raw_report = original["cases"][1]["local_answer_artifact"]["citation_report"]
    assert type(raw_report["cited_labels"]) is tuple
    serialized = json.loads(json.dumps(original))
    archived_report = serialized["cases"][1]["local_answer_artifact"]["citation_report"]
    assert type(archived_report["cited_labels"]) is list
    summary = audit_saved_m2(serialized, "f" * 64, require_real_model=False)
    assert summary["audit_status"] == "PASS_NO_NEW_MODEL_RUN"
    assert summary["cases"][1]["citation_count"] == 1


def test_wrong_saved_citation_stats_still_rejected_in_both_shapes():
    for use_json in (False, True):
        data = archive()
        if use_json:
            data = json.loads(json.dumps(data))
        report = data["cases"][1]["local_answer_artifact"]["citation_report"]
        report["citation_count"] = 999
        with pytest.raises(ValueError, match="citation statistics"):
            audit_saved_m2(data, "f" * 64, require_real_model=False)


def test_citation_label_modification_not_silently_normalized():
    data = json.loads(json.dumps(archive()))
    data["cases"][1]["local_answer_artifact"]["citation_report"]["cited_labels"] = ["S9"]
    with pytest.raises(ValueError, match="citation statistics"):
        audit_saved_m2(data, "f" * 64, require_real_model=False)


def test_model_identity_required_for_real_local_archive():
    with pytest.raises(ValueError, match="provenance"):
        audit_saved_m2(archive(), "f" * 64)
    data = archive()
    data["model_id"] = MODEL_ID
    assert audit_saved_m2(data, "f" * 64)["case_count"] == 4


def test_reject_tampered_source_document_and_fixture():
    data = archive()
    data["cases"][0]["local_answer_artifact"]["sources"][0]["text"] = "other"
    with pytest.raises(ValueError, match="source passage"):
        audit_saved_m2(data, "f" * 64, require_real_model=False)
    data = archive()
    data["fixture_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="provenance"):
        audit_saved_m2(data, "f" * 64, require_real_model=False)


def test_reject_modified_raw_draft_or_publication_leak():
    data = archive()
    data["cases"][0]["local_answer_artifact"]["raw_generation"] += " [S1]."
    with pytest.raises(ValueError, match="citation statistics"):
        audit_saved_m2(data, "f" * 64, require_real_model=False)
    data = archive()
    data["cases"][0]["local_answer_artifact"]["answer"] = "leaked"
    with pytest.raises(ValueError, match="leaked"):
        audit_saved_m2(data, "f" * 64, require_real_model=False)


def test_reject_corrupt_no_context_generator_skip():
    data = archive()
    data["cases"][3]["generator_calls"] = 1
    with pytest.raises(ValueError, match="call count"):
        audit_saved_m2(data, "f" * 64, require_real_model=False)


def test_syntactic_diagnoses_are_not_semantic_verdicts():
    assert citation_failure_reason("", ["S1"]) == "empty_generation"
    assert citation_failure_reason("No citation.", ["S1"]) == "no_bracketed_source_citations"
    assert citation_failure_reason("Unknown [S9].", ["S1"]) == "unknown_source_citation_labels"
    assert citation_failure_reason("First [S1]. Second uncited.", ["S1"]) == "not_all_sentences_cited"
    assert citation_failure_reason("Supported [S1].", ["S1"]) == "citation_syntax_passed"

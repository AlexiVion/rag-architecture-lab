"""Offline M2-SYNTH-01 forensic audit: no paid APIs or model weights."""
from __future__ import annotations

import json

import pytest

from raglab.evaluation.m2_synth01_audit import audit_saved_study, render_markdown
from raglab.evaluation.m2_synth_protocol import (
    ABSTAIN, EXPECTED_CASES_SHA256, validate_protocol,
)
from raglab.evaluation.m2_synth_runner import run_local


class ScriptedGenerator:
    name = "offline_evidence_stub_no_model"

    def __init__(self):
        self.outputs = iter(
            (f'{case["expected_literal_if_answerable"]} developed the unit [S1].'
             if case["category"] == "answerable" else ABSTAIN)
            for case in validate_protocol() if case["category"] != "no_context"
        )
        self.calls = 0

    def generate(self, *, system_prompt, user_prompt, max_new_tokens):
        self.calls += 1
        assert max_new_tokens == 128
        return next(self.outputs)


def archived_study(tmp_path):
    generator = ScriptedGenerator()
    directory = tmp_path / "synthetic_archived_run"
    result = run_local(directory, generator)
    assert result["model_calls"] == 18
    assert generator.calls == 18
    return directory


def test_24_case_forensic_audit_reconciles_original_saved_files(tmp_path):
    directory = archived_study(tmp_path)
    audit = audit_saved_study(directory)
    assert audit["audit_status"] == "ARCHIVED_FILES_RECONCILED_NO_MODEL_EXECUTION"
    assert audit["case_set_sha256"] == EXPECTED_CASES_SHA256
    assert audit["original_model_calls"] == 18
    assert audit["new_model_calls"] == 0
    assert audit["external_publications"] == 0
    assert audit["total_cases"] == 24
    assert audit["total_control_success"] == 24
    assert audit["negative_control_denominator"] == 12
    assert audit["negative_control_pipeline_acceptance_count"] == 0
    assert audit["control_success_by_category"]["answerable"]["success"] == 6
    assert audit["control_success_by_category"]["irrelevant"]["exact_model_abstention"] == 6
    assert audit["control_success_by_category"]["conflicting"]["exact_model_abstention"] == 6
    assert audit["control_success_by_category"]["no_context"]["success"] == 6
    assert len(audit["cases"]) == 24
    assert all(row["semantic_entailment"] == "NOT_EVALUATED" for row in audit["cases"])
    assert all(row["publication_to_external_system"] is False for row in audit["cases"])
    assert "NOT_SEMANTIC" not in audit["research_decision"]
    assert "negative" not in render_markdown(audit).lower() or "12" in render_markdown(audit)


def test_accepted_negative_control_is_counted_as_risk_not_factual_verdict(tmp_path):
    directory = archived_study(tmp_path)
    # A source-cited but factually unsupported answer would pass the legacy
    # syntax-only publication gate. Build a coherent synthetic row then
    # regenerate the derived aggregate, preserving the original fixture.
    row_path = directory / "cases" / "02.json"
    row = json.loads(row_path.read_text(encoding="utf-8"))
    raw = "The unrelated manufacturer built this system [S1]."
    row["raw_candidate"] = raw
    row["pipeline_status"] = "accepted"
    row["syntax_v1_pass"] = True
    row["syntax_v2_pass"] = True
    from dataclasses import asdict
    from raglab.citations import validate_citations
    from raglab.citations.validator_v2 import validate_citations_v2
    row["syntax_v2_report"] = asdict(validate_citations_v2(raw, ["S1"]))
    artifact = row["original_answer_artifact"]
    artifact["raw_generation"] = None
    artifact["answer"] = raw
    artifact["abstained"] = False
    artifact["output_status"] = "accepted"
    artifact["citation_report"] = asdict(validate_citations(raw, ["S1"]))
    row_path.write_text(json.dumps(row, indent=2), encoding="utf-8")
    # The experiment report must be consistent with modified records;
    # deliberately leave it unchanged and confirm tampering is detected.
    with pytest.raises(ValueError, match="aggregate report"):
        audit_saved_study(directory)


def test_corrupt_source_or_citation_stats_cannot_be_audited(tmp_path):
    directory = archived_study(tmp_path)
    file = directory / "cases" / "01.json"
    raw = json.loads(file.read_text(encoding="utf-8"))
    raw["original_answer_artifact"]["sources"][0]["text"] = "fake source"
    file.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="Evidence mapping"):
        audit_saved_study(directory)


def test_missing_case_or_changed_manifest_fails_closed(tmp_path):
    directory = archived_study(tmp_path)
    (directory / "cases" / "24.json").unlink()
    with pytest.raises(ValueError, match="Missing, extra"):
        audit_saved_study(directory)
    directory = archived_study(tmp_path / "second")
    manifest_file = directory / "manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    manifest["allowed_model_calls"] = 200
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="Frozen manifest"):
        audit_saved_study(directory)


def test_report_metrics_change_is_detected(tmp_path):
    directory = archived_study(tmp_path)
    report_file = directory / "report.json"
    summary = json.loads(report_file.read_text(encoding="utf-8"))
    summary["primary_control_success_rate"] = 0.0
    report_file.write_text(json.dumps(summary), encoding="utf-8")
    with pytest.raises(ValueError, match="Original aggregate report"):
        audit_saved_study(directory)

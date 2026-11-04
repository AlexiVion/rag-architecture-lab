"""M2 smoke tests are deliberately synthetic and never load local Qwen weights."""
from __future__ import annotations

import pytest

from raglab.evaluation.m2_live_smoke import (
    DOCUMENTS,
    EXPERIMENT_ID,
    FixedEvidenceRetriever,
    SCENARIOS,
    fixture_sha256,
    run_control_cases,
    summary_markdown,
)


class ScriptedGenerator:
    name = "deterministic_fixture_generator"

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def generate(self, *, system_prompt, user_prompt, max_new_tokens):
        if self.calls >= len(self.responses):
            raise AssertionError("Unexpected extra generation call")
        assert "Evidence:" in user_prompt
        assert max_new_tokens == 128
        result = self.responses[self.calls]
        self.calls += 1
        return result


def valid_generator():
    # Second and third answers have citation syntax but do not demonstrate
    # semantic alignment; the independent-support verdict remains unscored.
    return ScriptedGenerator([
        "The navigation system was developed by Meridian Robotics [S1].",
        "The equipment came from Helios Instruments [S1].",
        "The launch was on June 4, 2020 [S1].",
    ])


def test_four_predeclared_controls_use_real_pipeline_contract():
    stub = valid_generator()
    report = run_control_cases(stub)
    assert report["experiment_id"] == EXPERIMENT_ID
    assert report["case_count"] == 4
    assert report["total_generator_calls"] == 3
    assert stub.calls == 3
    assert [c["case_id"] for c in report["cases"]] == [c["case_id"] for c in SCENARIOS]
    assert [c["generator_calls"] for c in report["cases"]] == [1, 1, 1, 0]
    assert report["fixture_sha256"] == fixture_sha256()
    assert report["cases"][0]["reference_phrase_present_in_public_answer"] is True
    assert report["cases"][3]["output_status"] == "abstained_no_context"
    assert report["cases"][3]["local_answer_artifact"]["timings_ms"]["generation"] == 0
    assert all(c["safe_publication_gate_passed"] for c in report["cases"])
    assert "Citation gate" in summary_markdown(report)
    assert report["cases"][0]["citation_contract_syntax_passed"] is True
    assert "citation_contract_passed" not in report["cases"][0]["local_answer_artifact"]["citation_report"]


def test_cited_nonanswer_from_irrelevant_or_contradictory_evidence_is_not_certified():
    report = run_control_cases(valid_generator())
    for case in report["cases"][1:3]:
        assert case["citation_contract_syntax_passed"] is True
        assert case["output_status"] == "accepted"
        assert case["semantic_support"] == "not_evaluated"
        assert case["task_correctness"] == "not_evaluated"
        assert case["expected_behavior_alignment"] == "not_evaluated_requires_independent_review"
    assert report["source_selection"].startswith("fixed_original")


def test_uncited_answer_is_rejected_but_untrusted_draft_survives_locally():
    fake = ScriptedGenerator([
        "The answer is Meridian Robotics, with no citation.",
        "An unrelated statement [S1].",
        "One date from a conflicting pair [S1].",
    ])
    report = run_control_cases(fake)
    row = report["cases"][0]
    assert row["output_status"] == "rejected_citation_contract"
    assert row["local_answer_artifact"]["raw_generation"] == (
        "The answer is Meridian Robotics, with no citation."
    )
    assert row["reference_phrase_present_in_public_answer"] is False
    assert row["citation_contract_syntax_passed"] is False
    assert row["safe_publication_gate_passed"] is True


def test_fixed_source_ids_are_verified_and_not_inferred_from_gold():
    fixed = FixedEvidenceRetriever(["fiction-orion"])
    with pytest.raises(RuntimeError, match="indexed"):
        fixed.retrieve("query", 1)
    fixed.index(DOCUMENTS)
    assert fixed.retrieve("query", 1)[0].doc_id == "fiction-orion"
    with pytest.raises(ValueError, match="unknown source"):
        FixedEvidenceRetriever(["not-a-real-source"]).index(DOCUMENTS)


def test_fixture_fingerprint_is_stable_and_source_ids_are_unique():
    report = run_control_cases(valid_generator())
    assert len(report["fixture_sha256"]) == 64
    assert all(c["evidence_condition_curated_not_model_inferred"] for c in report["cases"])
    assert len({source.id for source in DOCUMENTS}) == len(DOCUMENTS)

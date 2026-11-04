"""Frozen M2 synthetic-source controls, narrow gold and one-pass checkpointing.

All tests use deterministic stubs; none loads Qwen or evaluates TEST qrels.
"""
from __future__ import annotations

import copy

import pytest

from raglab.evaluation.m2_synth_protocol import (
    ABSTAIN, CATEGORIES, EXPECTED_CASES_SHA256, STUDY_ID,
    aggregate_controls, canonical_sha256, score_observation, validate_protocol,
)
from raglab.evaluation.m2_synth_runner import (
    build_final_report, manifest_payload, run_local, write_or_check,
)


def observed(case, raw, *, citation=False, status=None):
    has_context = bool(case["sources"])
    return {
        "case_id": case["case_id"],
        "model_calls": int(has_context),
        "source_ids": [doc["id"] for doc in case["sources"]],
        "sent_to_external_system": False,
        "raw_candidate": raw,
        "syntax_v2_pass": citation,
        "pipeline_status": status or (
            "rejected_citation_contract" if has_context else "abstained_no_context"
        ),
    }


def test_24_frozen_controls_are_balanced_and_gold_is_not_in_questions():
    cases = validate_protocol()
    assert len(cases) == 24
    assert canonical_sha256(cases) == EXPECTED_CASES_SHA256
    for category in CATEGORIES:
        assert sum(c["category"] == category for c in cases) == 6
    for case in cases:
        assert len(case["sources"]) == {
            "answerable": 1, "irrelevant": 1, "conflicting": 2, "no_context": 0,
        }[case["category"]]
        assert case["source_selection"] == "fixed_templates_no_retrieval_benchmark"
        if case["category"] == "answerable":
            assert case["expected_literal_if_answerable"] not in case["question"]
    manifest = manifest_payload()
    assert manifest["frozen_case_count"] == 24
    assert manifest["cases_sha256"] == EXPECTED_CASES_SHA256
    assert manifest["hold_all_generated_text"] is True
    assert manifest["external_publication"] is False
    assert manifest["allowed_model_calls"] == 18


def test_gold_literal_and_citation_syntax_are_separate_proxies():
    case = next(c for c in validate_protocol() if c["category"] == "answerable")
    value = case["expected_literal_if_answerable"]
    literal_only = score_observation(case, observed(case, f"It was {value}.", citation=False))
    assert literal_only["literal_match_diagnostic"] is True
    assert literal_only["control_success"] is False
    citation_only = score_observation(
        case, observed(case, "A different company made it [S1].", citation=True)
    )
    assert citation_only["literal_match_diagnostic"] is False
    assert citation_only["control_success"] is False
    match_with_citation = score_observation(
        case, observed(case, f"{value} built it [S1].", citation=True)
    )
    assert match_with_citation["control_success"] is True
    assert match_with_citation["score_type"] == "literal_value_plus_source_syntax_proxy"


def test_irrelevant_and_contradictory_cases_require_exact_abstention():
    for category in ("irrelevant", "conflicting"):
        case = next(c for c in validate_protocol() if c["category"] == category)
        assert score_observation(case, observed(case, ABSTAIN))["control_success"]
        guessed = score_observation(
            case, observed(case, "The company developed it [S1].", citation=True)
        )
        assert guessed["control_success"] is False
        assert guessed["model_attempts_factual_answer_when_abstention_expected"]
        assert not score_observation(
            case, observed(case, ABSTAIN + " [S1]")
        )["control_success"]


def test_no_context_must_skip_generation_and_refuse():
    case = next(c for c in validate_protocol() if c["category"] == "no_context")
    assert score_observation(case, observed(case, None))["control_success"]
    with pytest.raises(ValueError, match="No-context"):
        score_observation(case, observed(case, "Invented [S1]."))
    broken = observed(case, None)
    broken["model_calls"] = 1
    with pytest.raises(ValueError, match="model call"):
        score_observation(case, broken)


def test_external_publication_and_source_tampering_fail_closed():
    case = validate_protocol()[0]
    tamper = observed(case, "Answer [S1].", citation=True)
    tamper["sent_to_external_system"] = True
    with pytest.raises(ValueError, match="publication"):
        score_observation(case, tamper)
    tamper = observed(case, "Answer [S1].", citation=True)
    tamper["source_ids"] = ["fictional-tampered"]
    with pytest.raises(ValueError, match="Evidence IDs"):
        score_observation(case, tamper)


def test_aggregate_metrics_are_per_class_and_require_all_24_cases():
    cases = validate_protocol()
    rows = []
    for case in cases:
        if case["category"] == "answerable":
            response = observed(
                case, case["expected_literal_if_answerable"] + " built it [S1].",
                citation=True,
            )
        elif case["category"] == "no_context":
            response = observed(case, None)
        else:
            response = observed(case, ABSTAIN)
        rows.append(score_observation(case, response))
    summary = aggregate_controls(rows)
    assert summary["study_id"] == STUDY_ID
    assert summary["primary_control_success_rate"] == 1.0
    assert all(group["success_count"] == 6 for group in summary["by_category"].values())
    assert "not sentence entailment" in summary["semantics_warning"]
    altered = copy.deepcopy(rows)
    altered[0]["case_id"] = "OTHER"
    with pytest.raises(ValueError, match="frozen case order"):
        aggregate_controls(altered)
    with pytest.raises(ValueError, match="24 distinct"):
        aggregate_controls(rows[:23])


def test_frozen_file_write_is_exclusive_and_rejects_changes(tmp_path):
    path = tmp_path / "manifest.json"
    assert write_or_check(path, manifest_payload()) is True
    assert write_or_check(path, manifest_payload()) is False
    path.write_text("{}\n", encoding="utf-8")
    with pytest.raises(FileExistsError, match="differs"):
        write_or_check(path, manifest_payload())


class FakeGenerator:
    name = "offline_stub_never_loads_Qwen"

    def __init__(self, answers):
        self.answers = iter(answers)
        self.calls = 0

    def generate(self, *, system_prompt, user_prompt, max_new_tokens):
        assert "Evidence:" in user_prompt
        assert max_new_tokens == 128
        self.calls += 1
        return next(self.answers)


def test_full_one_pass_with_stub_is_idempotent_and_never_reruns_cases(tmp_path):
    cases = validate_protocol()
    responses = [
        (f'{case["expected_literal_if_answerable"]} built it [S1].'
         if case["category"] == "answerable" else ABSTAIN)
        for case in cases if case["category"] != "no_context"
    ]
    generator = FakeGenerator(responses)
    result = run_local(tmp_path / "one_pass", generator=generator)
    assert result["total_cases"] == 24
    assert generator.calls == 18
    assert result["model_calls"] == 18
    assert result["primary_control_success_rate"] == 1.0
    assert result["publication_actions"] == 0
    assert result["all_generated_candidates_quarantined"]
    assert len(list((tmp_path / "one_pass" / "cases").glob("*.json"))) == 24
    # All rows must be verified, no generator invoked when report is already complete.
    reread = run_local(tmp_path / "one_pass", generator=FakeGenerator([]))
    assert reread == result
    first_path = tmp_path / "one_pass" / "cases" / "01.json"
    first = first_path.read_text(encoding="utf-8")
    first_path.write_text(first.replace("Fjord Dynamics", "Fabricated Company"), encoding="utf-8")
    with pytest.raises((ValueError, FileExistsError), match="evidence|citation|Saved|source|raw|mapping"):
        run_local(tmp_path / "one_pass", generator=FakeGenerator([]))

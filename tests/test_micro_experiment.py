from __future__ import annotations

import json
from pathlib import Path

import pytest

from raglab.micro.experiment import parse_dataset, read_dataset, run_micro_suite
from raglab.micro.registry import CANDIDATES, get_candidate, registry_manifest


FIXTURE = Path(__file__).resolve().parents[1] / "experiments" / "micro_smoke_fixture.json"


def test_registry_is_proposed_not_measured_and_tiny_candidates_exist():
    keys = {candidate.key for candidate in CANDIDATES}
    assert {"tinystories-1m", "pythia-14m", "smollm2-135m", "qwen25-05b"} <= keys
    assert not any(candidate.measured or candidate.revision for candidate in CANDIDATES)
    assert registry_manifest()["model_downloads_performed"] is False
    assert get_candidate("pythia-14m").parameters_millions == 14
    with pytest.raises(KeyError):
        get_candidate("made-up")


def test_input_fingerprint_is_deterministic_and_fixture_is_explicit():
    data = read_dataset(FIXTURE)
    assert len(data.documents) == 4
    assert data.fixture_only is True
    assert data.fingerprint == read_dataset(FIXTURE).fingerprint
    assert len(data.fingerprint) == 64


def test_preparation_has_four_matched_modes_and_no_generated_answers():
    data = read_dataset(FIXTURE)
    result = run_micro_suite(data, model_id="pythia-14m", max_context_tokens=80)
    assert result["scientific_validation"] == "NOT_RUN"
    assert result["research_status"] == "prepared_no_model_run"
    assert len(result["cases"]) == len(data.cases) * 5
    assert {x["mode"] for x in result["cases"]} == {
        "no_retrieval", "naive", "spans", "extractive_quote", "oracle"
    }
    assert all(x["generation"] is None for x in result["cases"])
    assert all(
        x["context"]["used_tokens"] <= x["context"]["budget_tokens"]
        for x in result["cases"]
    )
    assert all(x["oracle_used"] == (x["mode"] == "oracle") for x in result["cases"])
    assert all(
        not x["retrieved_ids"] and x["timing_ms"]["retrieval"] == 0
        for x in result["cases"] if x["mode"] == "no_retrieval"
    )
    for case in data.cases:
        oracle = next(
            x for x in result["cases"] if x["case_id"] == case.case_id
            and x["mode"] == "oracle"
        )
        assert oracle["retrieved_ids"] == list(case.oracle_doc_ids)
        assert oracle["timing_ms"]["retrieval"] == 0
    assert any(
        x["generation_status"] == "source_quote_only_not_answer"
        for x in result["cases"] if x["mode"] == "extractive_quote"
    )


class _FakeGenerator:
    name = "fake_control_not_a_language_model"

    def generate(self, *, system_prompt, user_prompt, max_new_tokens):
        assert "Research draft only" in system_prompt
        assert "Question:" in user_prompt
        assert max_new_tokens == 10
        return "DRAFT - not reviewed"


def test_local_generator_protocol_is_draft_only_no_false_publication():
    result = run_micro_suite(
        read_dataset(FIXTURE),
        model_id="pythia-14m",
        modes=("no_retrieval", "naive", "spans"),
        generator=_FakeGenerator(),
        max_new_tokens=10,
    )
    assert result["research_status"] == "exploratory_unvalidated"
    assert result["scientific_validation"] == "NOT_RUN"
    assert all(
        row["generation_status"] in ("draft_unverified", "abstained_no_evidence")
        for row in result["cases"]
    )


def test_source_group_leakage_is_rejected():
    original = json.loads(FIXTURE.read_text(encoding="utf-8"))
    extra = dict(original["cases"][0])
    extra.update({"id": "leak", "split": "holdout"})
    original["cases"].append(extra)
    with pytest.raises(ValueError, match="leaks"):
        parse_dataset(original)


def test_gold_document_leakage_is_rejected():
    original = json.loads(FIXTURE.read_text(encoding="utf-8"))
    original["cases"].append(
        {
            "id": "new",
            "question": "Anything?",
            "split": "calibration",
            "group_id": "other-group",
            "oracle_doc_ids": ["doc-mars"],
        }
    )
    with pytest.raises(ValueError, match="Gold evidence"):
        parse_dataset(original)


def test_holdout_cannot_run_using_smoke_runner():
    original = json.loads(FIXTURE.read_text(encoding="utf-8"))
    original["cases"][0]["split"] = "holdout"
    # This case is isolated by source and group; blocking is an explicit
    # policy, not an accidental split collision.
    with pytest.raises(ValueError, match="Holdout blocked"):
        run_micro_suite(parse_dataset(original), model_id="pythia-14m")


def test_invalid_modes_and_budgets_fail_closed():
    data = read_dataset(FIXTURE)
    with pytest.raises(ValueError, match="modes"):
        run_micro_suite(data, model_id="pythia-14m", modes=("made_up",))
    with pytest.raises(ValueError, match="positive"):
        run_micro_suite(data, model_id="pythia-14m", max_context_tokens=0)

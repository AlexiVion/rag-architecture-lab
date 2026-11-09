"""M2-LIVE-02 model-free development contract tests."""
from __future__ import annotations

import json
import pytest

from raglab.evaluation.m2_live_v2 import (
    ABSTENTION_MARKER, EXPERIMENT_ID, ORIGINAL_REPORT_SHA256,
    PROMPT_VERSION, SYSTEM_PROMPT_V2, VersionedPromptAdapter,
    prompt_sha256, read_sealed_baseline, run_development_controls,
)


class ScriptedGenerator:
    name = "synthetic_no_model"

    def __init__(self, answers):
        self._answers = iter(answers)
        self.calls = []

    def generate(self, *, system_prompt, user_prompt, max_new_tokens):
        self.calls.append({"system": system_prompt, "user": user_prompt, "tokens": max_new_tokens})
        return next(self._answers)


def test_prompt_adapter_changes_instructions_not_generated_citations():
    fake = ScriptedGenerator(["Meridian Robotics created it."])
    wrapper = VersionedPromptAdapter(fake)
    raw = wrapper.generate(
        system_prompt="Original system",
        user_prompt="Question:\n...\nEvidence:\n[S1]\ntext: ...",
        max_new_tokens=128,
    )
    assert raw == "Meridian Robotics created it."
    assert "[S1]" not in raw
    assert wrapper.calls == 1
    assert fake.calls[0]["system"] == SYSTEM_PROMPT_V2
    assert "Original system" not in fake.calls[0]["system"]
    assert fake.calls[0]["user"].startswith("Question:")
    assert fake.calls[0]["tokens"] == 128
    assert ABSTENTION_MARKER in fake.calls[0]["system"]
    assert PROMPT_VERSION == "m2-v02-cited-or-abstain-v1"
    assert len(prompt_sha256()) == 64


def test_development_run_quarantines_every_output():
    fake = ScriptedGenerator([
        "Meridian Robotics developed Orion Navigation [S1].",
        ABSTENTION_MARKER,
        ABSTENTION_MARKER,
    ])
    result = run_development_controls(fake)
    assert result["experiment_id"] == EXPERIMENT_ID
    assert result["case_count"] == 4
    assert result["generator_calls"] == 3
    assert len(fake.calls) == 3
    assert all("Evidence:" in call["user"] for call in fake.calls)
    assert [r["model_calls"] for r in result["cases"]] == [1, 1, 1, 0]
    first, unrelated, conflict, empty = result["cases"]
    assert first["pipeline_output_status"] == "accepted"
    assert first["citation_syntax_passed"] is True
    assert first["research_publication_decision"] == "CITATION_SYNTAX_ACCEPTED_HELD_FOR_SEMANTIC_REVIEW"
    for row in (unrelated, conflict):
        assert row["pipeline_output_status"] == "rejected_citation_contract"
        assert row["model_declared_exact_abstention"] is True
        assert row["research_publication_decision"] == "MODEL_DECLARED_INSUFFICIENT_EVIDENCE_UNVERIFIED"
    assert empty["pipeline_output_status"] == "abstained_no_context"
    assert empty["model_calls"] == 0
    assert empty["research_publication_decision"] == "NO_CONTEXT_NO_GENERATION"
    assert all(r["published_to_external_system"] is False for r in result["cases"])
    assert all(r["semantic_entailment"] == "NOT_EVALUATED" for r in result["cases"])
    assert result["publication_policy"] == "ALL_OUTPUTS_RESEARCH_ONLY_HELD_FOR_SEMANTIC_REVIEW"


def test_unsupported_but_syntactically_cited_claims_are_held():
    fake = ScriptedGenerator([
        "Helios Instruments developed Orion Navigation [S1].",
        "Helios Instruments developed Orion Navigation [S1].",
        "The Zenith Probe launched on June 4, 2020 [S1].",
    ])
    result = run_development_controls(fake)
    for row in result["cases"][:3]:
        assert row["citation_syntax_passed"] is True
        assert row["pipeline_output_status"] == "accepted"
        assert row["research_publication_decision"] == (
            "CITATION_SYNTAX_ACCEPTED_HELD_FOR_SEMANTIC_REVIEW"
        )
        assert row["published_to_external_system"] is False
        assert row["task_alignment"] == "NOT_EVALUATED"


def test_uncited_actual_claim_stays_unchanged_and_rejected():
    text = "Meridian Robotics developed Orion Navigation."
    fake = ScriptedGenerator([text, ABSTENTION_MARKER, ABSTENTION_MARKER])
    row = run_development_controls(fake)["cases"][0]
    assert row["generated_candidate_raw"] == text
    assert row["pipeline_output_status"] == "rejected_citation_contract"
    assert row["citation_syntax_passed"] is False
    assert row["local_answer_artifact"]["raw_generation"] == text


def test_declaration_must_match_exactly():
    fake = ScriptedGenerator([
        "INSUFFICIENT_EVIDENCE [S1].",
        ABSTENTION_MARKER,
        ABSTENTION_MARKER,
    ])
    row = run_development_controls(fake)["cases"][0]
    assert row["model_declared_exact_abstention"] is False
    assert row["published_to_external_system"] is False
    assert row["research_publication_decision"] != (
        "MODEL_DECLARED_INSUFFICIENT_EVIDENCE_UNVERIFIED"
    )


def test_existing_source_hash_guard_rejects_tampered_baseline(tmp_path):
    fake = tmp_path / "old.json"
    fake.write_text(json.dumps({"fake": True}), encoding="utf-8")
    with pytest.raises(ValueError, match="SHA256"):
        read_sealed_baseline(fake)
    assert ORIGINAL_REPORT_SHA256 == (
        "bd3b35354442062a861c8ed6d4d3b49f58c3ea185a5df7321728c34ef21ed3d8"
    )

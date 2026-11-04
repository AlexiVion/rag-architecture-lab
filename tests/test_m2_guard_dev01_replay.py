"""Archived M2-SYNTH-01 guard replay. Only offline scripted responses."""
from __future__ import annotations

import json

import pytest

from raglab.evaluation.m2_guard_dev01_replay import replay_archived_guard
from raglab.evaluation.m2_synth_protocol import ABSTAIN, validate_protocol
from raglab.evaluation.m2_synth_runner import run_local


class FakeGenerator:
    name = "offline_test_stub"

    def __init__(self):
        self.drafts = iter(
            (
                f'{case["expected_literal_if_answerable"]} developed the '
                f'{case["question"].split("developed the ")[1].replace("?", "")} [S1].'
                if case["category"] == "answerable" else ABSTAIN
            )
            for case in validate_protocol() if case["category"] != "no_context"
        )
        self.calls = 0

    def generate(self, *, system_prompt, user_prompt, max_new_tokens):
        self.calls += 1
        return next(self.drafts)


def test_complete_replay_never_calls_model_or_publishes(tmp_path):
    generator = FakeGenerator()
    folder = tmp_path / "run"
    run_local(folder, generator=generator)
    assert generator.calls == 18
    result = replay_archived_guard(folder, check_pinned_original=False)
    assert result["model_calls_during_replay"] == 0
    assert result["publication_actions"] == 0
    assert result["hypothetical_pregen_allow_count"] == 6
    assert result["hypothetical_pregen_deny_count"] == 18
    assert result["hypothetical_model_calls_skipped_if_guard_existed"] == 12
    assert result["strict_template_post_match_with_original_drafts"] == 6
    assert result["guard_denial_reasons"] == {
        "DENY_UNPARSEABLE_SOURCE": 6,
        "DENY_SOURCE_CONTRADICTION": 6,
        "DENY_NO_CONTEXT": 6,
    }
    assert all(x["external_publication"] is False for x in result["per_case"])
    assert all(x["semantic_truth"] == "NOT_EVALUATED" for x in result["per_case"])
    assert result["research_recommendation"].startswith("KEEP_GUARD_DEV_ONLY")


def test_pinned_original_fingerprint_is_required_for_real_operator_run(tmp_path):
    generator = FakeGenerator()
    folder = tmp_path / "run"
    run_local(folder, generator=generator)
    with pytest.raises(ValueError, match="operator-verified SHA256"):
        replay_archived_guard(folder)


def test_archived_tamper_rejected_before_hypothetical_scoring(tmp_path):
    run_local(tmp_path / "run", generator=FakeGenerator())
    manifest_file = tmp_path / "run" / "manifest.json"
    data = json.loads(manifest_file.read_text(encoding="utf-8"))
    data["allowed_model_calls"] = 100
    manifest_file.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="Frozen manifest"):
        replay_archived_guard(tmp_path / "run", check_pinned_original=False)

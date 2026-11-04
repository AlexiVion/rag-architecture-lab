"""The M2-LIVE-02 syntax replay is model-free and never publishes."""
import json
import pytest
from raglab.evaluation.m2_live_smoke import MODEL_ID
from raglab.evaluation.m2_live_v2 import ORIGINAL_REPORT_SHA256, run_development_controls
from raglab.evaluation.m2_live_v2_replay import EXPECTED_DRAFTS, replay_saved_run


class SyntheticGenerator:
    name = "synthetic"

    def __init__(self):
        self.texts = iter([
            EXPECTED_DRAFTS["answerable_supplied_evidence"],
            EXPECTED_DRAFTS["irrelevant_nonempty_evidence"],
            EXPECTED_DRAFTS["contradictory_evidence"],
        ])

    def generate(self, *, system_prompt, user_prompt, max_new_tokens):
        return next(self.texts)


def fixture():
    report = run_development_controls(SyntheticGenerator())
    report["baseline_report_sha256"] = ORIGINAL_REPORT_SHA256
    report["model_id"] = MODEL_ID
    return json.loads(json.dumps(report))


def test_replay_changes_one_syntactic_result_but_no_publication():
    result = replay_saved_run(fixture(), "0" * 64)
    assert result["v1_citation_pass_count"] == 0
    assert result["v2_citation_pass_count"] == 1
    assert result["model_calls_during_replay"] == 0
    assert result["publication_actions"] == 0
    first, second, third, fourth = result["cases"]
    assert first["citation_syntax_v2_counterfactual"]
    assert first["archived_pipeline_status"] == "rejected_citation_contract"
    assert not second["citation_syntax_v2_counterfactual"]
    assert second["v2_invalid_citation_labels"] == ["Solis Probe"]
    assert not third["citation_syntax_v2_counterfactual"]
    assert fourth["archived_pipeline_status"] == "abstained_no_context"
    assert all(x["semantically_supported"] == "NOT_EVALUATED" for x in result["cases"])


def test_forged_text_or_citation_data_is_rejected():
    report = fixture()
    report["cases"][1]["generated_candidate_raw"] += " [S1]"
    with pytest.raises(ValueError, match="operator-audited original"):
        replay_saved_run(report, "0" * 64)
    report = fixture()
    report["cases"][0]["local_answer_artifact"]["citation_report"]["citation_count"] = 3
    with pytest.raises(ValueError, match="citation report"):
        replay_saved_run(report, "0" * 64)


def test_source_change_or_external_publication_flag_is_rejected():
    report = fixture()
    report["cases"][0]["local_answer_artifact"]["sources"][0]["text"] = "fabricated"
    with pytest.raises(ValueError, match="source evidence"):
        replay_saved_run(report, "0" * 64)
    report = fixture()
    report["cases"][0]["published_to_external_system"] = True
    with pytest.raises(ValueError, match="quarantine"):
        replay_saved_run(report, "0" * 64)


def test_frozen_prompt_and_baseline_provenance():
    report = fixture()
    report["prompt_sha256"] = "f" * 64
    with pytest.raises(ValueError, match="protocol"):
        replay_saved_run(report, "0" * 64)
    report = fixture()
    report["baseline_report_sha256"] = "f" * 64
    with pytest.raises(ValueError, match="protocol"):
        replay_saved_run(report, "0" * 64)

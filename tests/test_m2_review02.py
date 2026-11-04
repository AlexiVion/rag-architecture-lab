"""M2-REVIEW-02: no-model review packets from exposed fictional Qwen drafts."""
from __future__ import annotations

import copy
import json

import pytest

from raglab.evaluation.m2_live_smoke import MODEL_ID
from raglab.evaluation.m2_live_v2 import ORIGINAL_REPORT_SHA256, run_development_controls
from raglab.evaluation.m2_live_v2_replay import EXPECTED_DRAFTS
from raglab.evaluation.m2_review02 import (
    EXPECTED_REPORT_SHA256, STUDY_ID, make_review_packets, write_bundle,
)
from raglab.evaluation.semantic_review import summarize_review_packet


class OfflineFake:
    name = "stub_no_Qwen"

    def __init__(self):
        self.chunks = iter([
            EXPECTED_DRAFTS["answerable_supplied_evidence"],
            EXPECTED_DRAFTS["irrelevant_nonempty_evidence"],
            EXPECTED_DRAFTS["contradictory_evidence"],
        ])
        self.calls = 0

    def generate(self, *, system_prompt, user_prompt, max_new_tokens):
        self.calls += 1
        return next(self.chunks)


def fixture():
    fake = OfflineFake()
    report = run_development_controls(fake)
    assert fake.calls == 3
    report["model_id"] = MODEL_ID
    report["baseline_report_sha256"] = ORIGINAL_REPORT_SHA256
    return json.loads(json.dumps(report))


def test_opaque_packets_have_no_automatic_semantic_labels():
    packets, manifest = make_review_packets(fixture(), EXPECTED_REPORT_SHA256)
    assert manifest["study_id"] == STUDY_ID
    assert manifest["review_packet_count"] == 4
    assert manifest["auto_semantic_labels_assigned"] == 0
    assert manifest["model_calls_during_export"] == 0
    assert manifest["external_publications"] == 0
    assert manifest["quality_metrics"] is None
    assert [p["provenance"]["query_id"] for p in packets] == [
        "R01", "R02", "R03", "R04"
    ]
    for packet in packets:
        assert packet["review"]["expected_behavior"] == "unreviewed"
        assert not packet["review"]["reviewer"]
        assert all(source["relevance"] == "unreviewed" for source in packet["sources"])
        assert all(claim["support"] == "unreviewed" for claim in packet["claims"])
        assert summarize_review_packet(packet)["fully_supported_claim_rate"] is None
        assert packet["research_boundary"]["model_attempt_is_not_equal_to_pipeline_publication"]
    assert len(packets[0]["claims"]) == 1
    assert packets[0]["claims"][0]["citation_labels"] == ["S1"]
    assert packets[0]["claims"][0]["text"].endswith(". [S1]")
    assert packets[0]["citation_gate"]["passed"] is True
    assert packets[0]["provenance"]["output_status"] == "rejected_citation_contract"
    assert packets[0]["research_boundary"]["model_generated_factual_candidate"]
    assert packets[1]["citation_gate"]["invalid_labels"] == ["Solis Probe"]
    assert packets[2]["citation_gate"]["passed"] is False
    assert packets[3]["candidate_text"] == ""
    assert not packets[3]["sources"] and not packets[3]["claims"]
    assert not packets[3]["research_boundary"]["model_generated_factual_candidate"]


def test_export_refuses_changed_original_fingerprint():
    with pytest.raises(ValueError, match="SHA256"):
        make_review_packets(fixture(), "0" * 64)


def test_export_checks_archived_raw_drafts_and_sources():
    fake = fixture()
    fake["cases"][0]["generated_candidate_raw"] = "Manipulated cited claim [S1]."
    with pytest.raises(ValueError, match="operator-audited original"):
        make_review_packets(fake, EXPECTED_REPORT_SHA256)
    fake = fixture()
    fake["cases"][1]["local_answer_artifact"]["sources"][0]["text"] = "other"
    with pytest.raises(ValueError, match="source evidence"):
        make_review_packets(fake, EXPECTED_REPORT_SHA256)


def test_bundle_is_idempotent_and_never_overwrites_human_edits(tmp_path):
    packets, manifest = make_review_packets(fixture(), EXPECTED_REPORT_SHA256)
    folder = tmp_path / "bundle"
    assert write_bundle(packets, manifest, folder) is True
    assert write_bundle(packets, manifest, folder) is False
    saved = folder / "01_review.json"
    payload = json.loads(saved.read_text(encoding="utf-8"))
    payload["sources"][0]["relevance"] = "relevant"
    saved.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(FileExistsError, match="refusing overwrite"):
        write_bundle(packets, manifest, folder)


def test_completed_human_labels_are_separate_from_syntax(tmp_path):
    packets, _ = make_review_packets(fixture(), EXPECTED_REPORT_SHA256)
    review = copy.deepcopy(packets[0])
    review["review"]["reviewer"] = "independent-reviewer"
    review["review"]["expected_behavior"] = "answer"
    review["sources"][0]["relevance"] = "relevant"
    review["claims"][0]["support"] = "supported"
    review["claims"][0]["reviewed_evidence_labels"] = ["S1"]
    summary = summarize_review_packet(review)
    assert summary["review_status"] == "complete"
    assert summary["fully_supported_claim_rate"] == 1
    # The saved original pipeline did NOT publish, even when the V2 parser
    # counterfactual is citation-valid and a human explicitly marks support.
    assert review["provenance"]["output_status"] == "rejected_citation_contract"
    assert summary["observed_behavior"] == "abstain"
    assert review["research_boundary"]["model_generated_factual_candidate"] is True

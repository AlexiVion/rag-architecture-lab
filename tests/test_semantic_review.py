from __future__ import annotations

import pytest

from raglab.evaluation.semantic_review import prepare_review_packet, summarize_review_packet


def fixture(answer="A study reports X [S1]."):
    return {
        "dataset": "toy/dev",
        "query_id": "q",
        "result": {
            "question": "Was X observed?",
            "answer": answer,
            "retrieval_name": "toy",
            "generator_name": "fake",
            "output_status": "accepted",
            "abstained": False,
            "sources": [{"label": "S1", "doc_id": "a", "title": "Article",
                         "text": "The study reports X."}],
        },
    }


def test_export_does_not_invent_semantic_support():
    p = prepare_review_packet(fixture())
    assert p["citation_gate"]["passed"] is True
    assert p["claims"][0]["support"] == "unreviewed"
    assert p["sources"][0]["relevance"] == "unreviewed"
    summary = summarize_review_packet(p)
    assert summary["review_status"] == "incomplete"
    assert summary["fully_supported_claim_rate"] is None


def test_manual_supported_label_produces_complete_review():
    p = prepare_review_packet(fixture())
    p["review"]["reviewer"] = "human"
    p["review"]["expected_behavior"] = "answer"
    p["sources"][0]["relevance"] = "relevant"
    p["claims"][0]["support"] = "supported"
    p["claims"][0]["reviewed_evidence_labels"] = ["S1"]
    summary = summarize_review_packet(p)
    assert summary["review_status"] == "complete"
    assert summary["fully_supported_claim_rate"] == 1.0
    assert summary["citation_contract_passed"] is True


def test_cited_false_claim_never_auto_passes_semantically():
    p = prepare_review_packet(fixture("An unsupported assertion [S1]."))
    assert p["citation_gate"]["passed"]
    assert summarize_review_packet(p)["fully_supported_claim_rate"] is None
    p["review"]["reviewer"] = "reviewer"
    p["review"]["expected_behavior"] = "abstain"
    p["sources"][0]["relevance"] = "irrelevant"
    p["claims"][0]["support"] = "unsupported"
    summary = summarize_review_packet(p)
    assert summary["fully_supported_claim_rate"] == 0.0


def test_rejected_draft_is_preserved_and_not_citation_passed():
    data = fixture("Fallback refusal")
    data["result"].update(
        output_status="rejected_citation_contract",
        abstained=True,
        raw_generation="Unsupported attempt with no citation."
    )
    packet = prepare_review_packet(data)
    assert packet["candidate_text"] == "Unsupported attempt with no citation."
    assert not packet["citation_gate"]["passed"]
    assert len(packet["claims"]) == 1


def test_proper_abstention_has_zero_claims():
    data = fixture("Insufficient evidence")
    data["result"]["abstained"] = True
    data["result"]["output_status"] = "abstained_no_context"
    data["result"]["sources"] = []
    packet = prepare_review_packet(data)
    assert packet["claims"] == []
    assert packet["candidate_text"] == ""
    assert packet["citation_gate"]["passed"] is False


def test_evidence_sources_must_be_reviewer_selected_from_packet():
    packet = prepare_review_packet(fixture())
    packet["claims"][0]["support"] = "supported"
    packet["claims"][0]["reviewed_evidence_labels"] = ["S99"]
    with pytest.raises(ValueError, match="Unknown cited evidence"):
        summarize_review_packet(packet)


def test_claims_marked_supported_need_evidence_labels():
    packet = prepare_review_packet(fixture())
    packet["claims"][0]["support"] = "supported"
    with pytest.raises(ValueError, match="needs reviewed evidence"):
        summarize_review_packet(packet)


def test_duplicate_source_labels_are_rejected():
    data = fixture()
    data["result"]["sources"].append(data["result"]["sources"][0])
    with pytest.raises(ValueError, match="duplicate"):
        prepare_review_packet(data)

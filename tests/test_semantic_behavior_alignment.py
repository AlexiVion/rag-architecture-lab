from __future__ import annotations

from raglab.evaluation.semantic_review import prepare_review_packet, summarize_review_packet


def example(*, abstained=False, status="unknown_legacy"):
    packet = prepare_review_packet({
        "dataset": "beir/scifact/test",
        "query_id": "1",
        "result": {
            "question": "0-dimensional biomaterials show inductive properties.",
            "answer": "The complexity of the human brain makes research hard.",
            "sources": [{"label": "S1", "title": "Brain organoids",
                         "doc_id": "brain", "text": "The complexity of the human brain makes research hard."}],
            "abstained": abstained,
            "output_status": status,
        },
    })
    packet["review"]["reviewer"] = "reviewer-1"
    packet["review"]["expected_behavior"] = "abstain"
    packet["sources"][0]["relevance"] = "irrelevant"
    packet["claims"][0]["support"] = "supported"
    packet["claims"][0]["reviewed_evidence_labels"] = ["S1"]
    return packet


def test_supported_claim_but_wrong_task_behavior_is_not_success():
    packet = example(abstained=False)
    result = summarize_review_packet(packet)
    assert result["review_status"] == "complete"
    assert result["fully_supported_claim_rate"] == 1
    assert result["source_adequacy_from_human_labels"] == "all_sources_judged_irrelevant"
    assert result["behavior_alignment_with_human_review"] == "answered_when_human_expected_abstention"
    assert result["task_success_score"] is None
    assert result["answer_relevance_score"] is None


def test_backward_compatibility_with_existing_annotated_packet():
    packet = example()
    del packet["provenance"]["actual_abstained"]
    result = summarize_review_packet(packet)
    assert result["observed_behavior"] == "answer"
    assert result["observed_behavior_evidence"] == "legacy_nonempty_generation_inferred"
    assert result["behavior_alignment_with_human_review"] == "answered_when_human_expected_abstention"


def test_expected_abstention_matches_true_abstention():
    packet = example()
    packet["provenance"]["actual_abstained"] = True
    packet["claims"] = []
    result = summarize_review_packet(packet)
    assert result["observed_behavior"] == "abstain"
    assert result["behavior_alignment_with_human_review"] == "matches_human_expected_behavior"
    assert result["fully_supported_claim_rate"] is None


def test_incomplete_human_review_is_not_misreported_as_failure():
    packet = example()
    packet["sources"][0]["relevance"] = "unreviewed"
    result = summarize_review_packet(packet)
    assert result["behavior_alignment_with_human_review"] == "not_evaluated"
    assert result["source_adequacy_from_human_labels"] == "not_evaluated"


def test_expected_uncertain_makes_behavior_alignment_unevaluated():
    packet = example()
    packet["review"]["expected_behavior"] = "uncertain"
    assert summarize_review_packet(packet)["behavior_alignment_with_human_review"] == "not_evaluated"

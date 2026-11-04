from __future__ import annotations

import pytest

from raglab.evaluation.interactive_review import annotate_packet
from raglab.evaluation.semantic_review import prepare_review_packet, summarize_review_packet


def base_packet():
    artifact = {
        "dataset": "toy/dev",
        "query_id": "q1",
        "result": {
            "question": "Is the experimental claim verified?",
            "answer": "The article supports the claim [S1].",
            "output_status": "accepted",
            "abstained": False,
            "sources": [{
                "label": "S1", "doc_id": "d1", "title": "Article",
                "text": "Article evidence as shown to the generator."
            }],
        },
    }
    return prepare_review_packet(artifact)


def ask_sequence(responses):
    items = iter(responses)

    def ask(prompt):
        try:
            return next(items)
        except StopIteration as exc:
            raise AssertionError(f"Unexpected prompt: {prompt}") from exc

    return ask


def test_interactive_review_keeps_input_unmodified_and_records_human_labels():
    original = base_packet()
    lines = []
    answer = annotate_packet(
        original,
        ask=ask_sequence(["annotator1", "r", "read abstract", "s", "S1",
                          "supports text", "a", "final"]),
        show=lines.append,
    )
    assert original["sources"][0]["relevance"] == "unreviewed"
    assert answer["review"]["reviewer"] == "annotator1"
    assert answer["sources"][0]["relevance"] == "relevant"
    assert answer["claims"][0]["support"] == "supported"
    assert answer["claims"][0]["reviewed_evidence_labels"] == ["S1"]
    assert summarize_review_packet(answer)["fully_supported_claim_rate"] == 1.0
    assert "Artículo" not in original["review"]["notes"]


def test_skipping_review_keeps_semantic_score_unavailable():
    original = base_packet()
    answer = annotate_packet(
        original,
        ask=ask_sequence(["", "s", "", "k", "", "s", ""]),
        show=lambda text: None,
    )
    summary = summarize_review_packet(answer)
    assert summary["review_status"] == "incomplete"
    assert summary["fully_supported_claim_rate"] is None


def test_invalid_source_choice_reprompts_without_guessing():
    packet = annotate_packet(
        base_packet(),
        ask=ask_sequence(["human", "bad", "u", "", "u", "", "u", ""]),
        show=lambda text: None,
    )
    assert packet["sources"][0]["relevance"] == "uncertain"
    assert packet["claims"][0]["support"] == "uncertain"
    assert summarize_review_packet(packet)["review_status"] == "complete"


def test_supported_requires_evidence_and_reroutes_to_verdict():
    packet = annotate_packet(
        base_packet(),
        ask=ask_sequence(["human", "r", "", "s", "", "n", "",
                          "b", ""]),
        show=lambda text: None,
    )
    assert packet["claims"][0]["support"] == "unsupported"
    assert packet["claims"][0]["reviewed_evidence_labels"] == []


def test_unknown_evidence_label_is_reprompted():
    packet = annotate_packet(
        base_packet(),
        ask=ask_sequence(["human", "r", "", "s", "S99", "S1", "",
                          "a", ""]),
        show=lambda text: None,
    )
    assert packet["claims"][0]["reviewed_evidence_labels"] == ["S1"]


def test_invalid_packet_is_rejected_before_human_prompts():
    broken = base_packet()
    broken["schema_version"] = -1
    with pytest.raises(ValueError, match="Unsupported"):
        annotate_packet(broken, ask=ask_sequence([]), show=lambda text: None)

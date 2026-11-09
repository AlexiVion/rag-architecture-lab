from __future__ import annotations

import pytest

from raglab.micro.evaluation import assess_human_reviews


def _label(case_id, mode, reviewer, *, answerable=True, abstained=False, supported=True, correct=True):
    return {
        "case_id": case_id,
        "mode": mode,
        "reviewer_id": reviewer,
        "answerable": answerable,
        "abstained": abstained,
        "task_correct": None if abstained else correct,
        "source_supported": None if abstained else supported,
    }


def test_two_independent_agreed_reviews_only():
    reviews = [
        _label("a", "naive", "reviewer1"),
        _label("a", "naive", "reviewer2"),
        _label("b", "naive", "reviewer1", supported=False),
        _label("b", "naive", "reviewer2", supported=False),
        _label("c", "naive", "reviewer1", abstained=True),
        _label("c", "naive", "reviewer2", abstained=True),
    ]
    result = assess_human_reviews(reviews)
    scores = result["by_mode"]["naive"]
    assert result["items_with_consensus"] == 3
    assert scores["supported_correct"] == 1
    assert scores["unsupported_or_incorrect"] == 1
    assert scores["false_abstention"] == 1
    assert scores["unsupported_or_incorrect_over_answered"] == 0.5
    assert scores["false_abstention_over_answerable"] == 1 / 3
    assert "NOT_HELDOUT_CERTIFIED" in result["scientific_validation"]


def test_disagreement_not_silently_scored():
    result = assess_human_reviews(
        [
            _label("a", "spans", "r1", supported=True),
            _label("a", "spans", "r2", supported=False),
            _label("b", "spans", "r1"),
        ]
    )
    assert result["items_with_consensus"] == 0
    assert result["items_pending_or_disputed"] == 2
    assert result["by_mode"] == {}


def test_correct_refusal_not_counted_as_failure():
    result = assess_human_reviews(
        [
            _label("a", "spans", "r1", answerable=False, abstained=True),
            _label("a", "spans", "r2", answerable=False, abstained=True),
        ]
    )
    assert result["by_mode"]["spans"]["correct_abstention"] == 1
    assert result["by_mode"]["spans"]["false_abstention_over_answerable"] is None


def test_cannot_reuse_same_reviewer_for_independent_agreement():
    with pytest.raises(ValueError, match="Duplicate reviewer"):
        assess_human_reviews([_label("a", "spans", "r1"), _label("a", "spans", "r1")])


def test_abstentions_cannot_have_support_labels():
    bad = _label("a", "naive", "r1", abstained=True)
    bad["source_supported"] = True
    with pytest.raises(ValueError, match="Abstained"):
        assess_human_reviews([bad])


def test_no_reviews_are_not_a_pass():
    result = assess_human_reviews([])
    assert result["scientific_validation"] == "NO_EVIDENCE"


def test_missing_or_nonboolean_labels_fail():
    bad = _label("a", "naive", "r1")
    bad["task_correct"] = None
    with pytest.raises(ValueError, match="boolean"):
        assess_human_reviews([bad])
    with pytest.raises(ValueError, match="at least two"):
        assess_human_reviews([_label("a", "naive", "r1")], minimum_reviewers=1)

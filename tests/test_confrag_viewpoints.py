"""Synthetic parser controls only, not ConfRAG real-world validation."""
import pytest

from raglab.evaluation.confrag_viewpoints import (
    binary_viewpoint_score,
    extract_viewpoint_pairs,
    fingerprints,
    lexical_viewpoint_different,
)


def _row():
    return {
        "id": 12,
        "question": "What was the outcome of the invented experiment?",
        "contradicts": True,
        "websites": [
            {"index": 1, "answer": "It succeeded in the trial."},
            {"index": 2, "answer": "It succeeded in that trial."},
            {"index": 3, "answer": "The experiment failed."},
        ],
        "answers": [
            {"answer": "Success", "index": [1, 2]},
            {"answer": "Failure", "index": [3]},
        ],
    }


def test_pair_labels_distinguish_viewpoints_not_claim_logical_contradiction():
    pairs = extract_viewpoint_pairs(_row())
    assert len(pairs) == 3
    assert [p["same_annotated_viewpoint"] for p in pairs] == [
        True, False, False
    ]
    assert len({p["pair_id"] for p in pairs}) == 3
    assert all("Question:" in p["left"] for p in pairs)
    assert all(p["contradicts_question_flag"] for p in pairs)
    assert "The experiment failed." in pairs[-1]["right"]


def test_ambiguous_membership_and_duplicate_source_index_excluded():
    row = _row()
    row["answers"][1]["index"].append(1)
    pairs = extract_viewpoint_pairs(row)
    assert len(pairs) == 1
    assert pairs[0]["left_source_index"] == 2
    row = _row()
    row["websites"].append({"index": 1, "answer": "Duplicate"})
    pairs = extract_viewpoint_pairs(row)
    assert len(pairs) == 1
    assert pairs[0]["left_source_index"] == 2


def test_missing_source_answer_and_text_out_of_bound_not_labels():
    row = _row()
    row["websites"][0]["answer"] = ""
    row["websites"][1]["answer"] = "X" * 501
    assert extract_viewpoint_pairs(row) == []
    with pytest.raises(ValueError, match="website count"):
        extract_viewpoint_pairs(row, max_websites=1)


def test_fixed_lexical_baseline_ignores_shared_question():
    a = "Question: What happened?\nAnswer: The station reopened in 2020."
    b = "Question: What happened?\nAnswer: The station reopened in 2020."
    c = "Question: What happened?\nAnswer: It permanently closed in 2015."
    assert not lexical_viewpoint_different(a, b)
    assert lexical_viewpoint_different(a, c)


def test_metrics_denominators_and_group_counts_are_explicit():
    rows = extract_viewpoint_pairs(_row())
    rows[0]["predict"] = False
    rows[1]["predict"] = True
    rows[2]["predict"] = False
    m = binary_viewpoint_score(rows, "predict")
    assert m["n_pairs"] == 3
    assert m["n_source_question_groups"] == 1
    assert m["counts"] == {"tp": 1, "tn": 1, "fp": 0, "fn": 1}
    assert m["accuracy"] == pytest.approx(2 / 3)
    assert m["balanced_accuracy"] == pytest.approx(0.75)
    assert m["different_viewpoint_f1"] == pytest.approx(2 / 3)
    assert "not_factual_contradiction" in m["unit"]
    rows[1]["pair_id"] = rows[0]["pair_id"]
    with pytest.raises(ValueError, match="Duplicate"):
        binary_viewpoint_score(rows, "predict")


def test_input_hashes_are_stable_and_sensitive_to_claim_changes():
    rows = extract_viewpoint_pairs(_row())
    first = fingerprints(rows)
    assert first == fingerprints(list(reversed(rows)))
    rows[0]["left"] += " Some edited text."
    assert first["selected_pairs_sha256"] != fingerprints(rows)["selected_pairs_sha256"]

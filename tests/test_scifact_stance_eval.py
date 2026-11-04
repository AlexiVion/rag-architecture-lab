from __future__ import annotations

import hashlib
import io
import json
import tarfile

import numpy as np
import pytest

from raglab.evaluation import scifact_stance_eval as sci


def sample_rows():
    corpus = [
        {"doc_id": 1, "abstract": ["Apples are fruits.", "They grow on trees."], "title": "A"},
        {"doc_id": 2, "abstract": ["Dogs are mammals.", "Dogs do not lay eggs."], "title": "B"},
        {"doc_id": 3, "abstract": ["Cats have fur."], "title": "C"},
    ]
    claims = [
        {"id": 10, "claim": "Apples are fruits.",
         "evidence": {"1": [{"sentences": [0], "label": "SUPPORT"}]}},
        {"id": 20, "claim": "Dogs lay eggs.",
         "evidence": {"2": [{"sentences": [1], "label": "CONTRADICT"}]}},
        {"id": 30, "claim": "Cats have fur.",
         "evidence": {"3": [{"sentences": [0], "label": "SUPPORT"}]}},
        {"id": 40, "claim": "Dogs are reptiles.",
         "evidence": {"2": [{"sentences": [0], "label": "CONTRADICT"}]}},
        {"id": 50, "claim": "No annotated documents.", "evidence": {}},
    ]
    return corpus, claims


def make_archive(tmp_path):
    corpus, claims = sample_rows()
    path = tmp_path / "scifact.tar.gz"
    with tarfile.open(path, "w:gz") as stream:
        for name, records in (
            ("data/corpus.jsonl", corpus),
            ("data/claims_train.jsonl", claims),
            ("data/claims_test.jsonl", [{"id": 999, "claim": "PRIVATE TEST ONLY"}]),
        ):
            body = ("\n".join(json.dumps(item) for item in records) + "\n").encode()
            member = tarfile.TarInfo(name)
            member.size = len(body)
            stream.addfile(member, io.BytesIO(body))
    return path


def test_train_archive_reads_only_train_and_verifies_fingerprint(tmp_path, monkeypatch):
    path = make_archive(tmp_path)
    fingerprint = hashlib.sha256(path.read_bytes()).hexdigest()
    monkeypatch.setattr(sci, "SCIFACT_ARCHIVE_SHA256", fingerprint)
    corpus, train, digest = sci.read_official_train_archive(path)
    assert len(corpus) == 3
    assert len(train) == 5
    assert digest == fingerprint
    assert all(item["id"] != 999 for item in train)


def test_unknown_archive_revision_fails_closed(tmp_path):
    path = make_archive(tmp_path)
    with pytest.raises(ValueError, match="checksum mismatch"):
        sci.read_official_train_archive(path)


def test_original_rationale_labels_are_not_derived_from_qrels():
    corpus, claims = sample_rows()
    observations = sci.extract_labeled_rationales(corpus, claims)
    assert len(observations) == 4
    assert [row["gold"] for row in observations] == [
        "entailment", "contradiction", "entailment", "contradiction"
    ]
    assert observations[1]["premise"] == "Dogs do not lay eggs."
    assert observations[1]["hypothesis"] == "Dogs lay eggs."


def test_balanced_sample_is_deterministic_and_has_no_duplicates():
    corpus, claims = sample_rows()
    observations = sci.extract_labeled_rationales(corpus, claims)
    sampled = sci.balanced_training_sample(observations, per_class=2, seed=17)
    again = sci.balanced_training_sample(observations, per_class=2, seed=17)
    assert sampled == again
    assert [x["gold"] for x in sampled] == [
        "entailment", "contradiction", "entailment", "contradiction"
    ]
    assert len({(x["claim_id"], x["doc_id"]) for x in sampled}) == 4


def test_stance_accuracy_keeps_neutral_predictions_as_errors():
    corpus, claims = sample_rows()
    data = sci.balanced_training_sample(
        sci.extract_labeled_rationales(corpus, claims), per_class=2
    )
    raw = np.array([
        [0, 9, 0], [9, 0, 0], [0, 0, 10], [10, 0, 0]
    ])
    result = sci.evaluate_gold_stance(
        data, raw, archive_sha256="sha", model_revision="local-revision"
    )
    assert result["gold_counts"] == {"entailment": 2, "contradiction": 2}
    assert result["sample_count"] == 4
    assert result["accuracy_on_this_expert_labeled_TRAIN_rationale_sample"] == 0.75
    assert result["confusion"]["entailment"]["neutral"] == 1
    assert result["neutral_gold_labels_in_sample"] == 0
    assert result["no_runtime_policy_changed"]
    assert "Expert-labeled rationale" in sci.gold_report_markdown(result)


def test_missing_label_is_rejected():
    corpus, claims = sample_rows()
    claims[0]["evidence"]["1"][0]["label"] = "NEUTRAL"
    with pytest.raises(ValueError, match="Unrecognized"):
        sci.extract_labeled_rationales(corpus, claims)


def test_invalid_rationale_sentence_index_is_rejected():
    corpus, claims = sample_rows()
    claims[0]["evidence"]["1"][0]["sentences"] = [100]
    with pytest.raises(ValueError, match="index out of range"):
        sci.extract_labeled_rationales(corpus, claims)


def test_sample_budget_requires_both_stance_classes():
    corpus, claims = sample_rows()
    selected = sci.extract_labeled_rationales(corpus, claims)
    with pytest.raises(ValueError, match="Not enough original TRAIN"):
        sci.balanced_training_sample(selected, per_class=3)

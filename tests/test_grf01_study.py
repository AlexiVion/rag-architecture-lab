from __future__ import annotations

import copy
import json
import numpy as np
import pytest

from raglab.graph.grf01_study import (
    _gold_after_ranking, _unlabelled_documents, aggregate,
    load_locked_inputs, run_one_case,
)


class FakeEmbeddings:
    name = "synthetic_test_embedding_not_a_measured_model"

    def encode(self, texts):
        # Fully deterministic synthetic feature representation.
        return np.asarray([
            [
                sum("rover" in token for token in text.lower().split()),
                sum("orion" in token for token in text.lower().split()),
                sum("solis" in token for token in text.lower().split()),
                1.0,
            ]
            for text in texts
        ], dtype=np.float32)


def example(identifier="test-example-1"):
    return {
        "_id": identifier,
        "type": "bridge",
        "question": "Who developed the Orion technology used by Aster Rover?",
        "context": [
            ["Aster Rover", ["Aster Rover uses Orion Navigation."]],
            ["Orion Navigation", ["Orion Navigation was built by Meridian Robotics."]],
            ["Solis Probe", ["Solis Probe was built by a different company."]],
        ],
        "supporting_facts": [
            ["Aster Rover", 0], ["Orion Navigation", 0],
        ],
        "answer": "Meridian Robotics",
    }


def test_single_pair_study_uses_shared_candidate_lists_and_real_evidence_paths():
    output = run_one_case(example(), embeddings=FakeEmbeddings())
    assert output["candidate_count"] == 3
    assert output["graph_edge_count"] >= 1
    assert output["graph_activated"]
    assert output["graph_trace"]["gold_labels_used"] is False
    assert output["graph_trace"]["policy_id"] == "GRF01-GRAPH-HYBRID-v1-LOCKED"
    for name in ("bm25", "dense", "hybrid", "graph_hybrid"):
        assert len(output["ranked_original_doc_ids"][name]) == 3
        assert set(output["ranked_original_doc_ids"][name]) == {
            "paragraph-00", "paragraph-01", "paragraph-02"
        }
        assert all(0 <= v <= 1 for v in output["recall"][name].values())


def test_no_evidence_path_gives_identical_rankings():
    row = example()
    row["question"] = "What weather is expected tomorrow?"
    row["context"] = [
        ["Aster Rover", ["Its wheels are aluminum."]],
        ["Orion Navigation", ["This concerns a software system."]],
        ["Solis Probe", ["Independent probe mission."]],
    ]
    result = run_one_case(row, embeddings=FakeEmbeddings())
    assert result["graph_path_count"] == 0
    assert result["ranked_original_doc_ids"]["hybrid"] == result["ranked_original_doc_ids"]["graph_hybrid"]


def test_original_gold_labels_cannot_influence_graph_results():
    a = example()
    b = copy.deepcopy(a)
    b["answer"] = "completely different answer"
    b["supporting_facts"] = [["Aster Rover", 0], ["Solis Probe", 0]]
    x = run_one_case(a, embeddings=FakeEmbeddings())
    y = run_one_case(b, embeddings=FakeEmbeddings())
    assert x["ranked_original_doc_ids"] == y["ranked_original_doc_ids"]
    assert x["graph_trace"] == y["graph_trace"]
    assert x["gold_document_ids"] != y["gold_document_ids"]


def test_invalid_gold_is_detected_only_after_ranking():
    row = example()
    docs = _unlabelled_documents(row)
    row["supporting_facts"] = [["This document does not exist", 0]]
    with pytest.raises(ValueError, match="missing"):
        _gold_after_ranking(row, docs)


def test_aggregate_is_paired_and_does_not_autopromote():
    rows = [
        run_one_case(example(str(i)), embeddings=FakeEmbeddings())
        for i in range(3)
    ]
    report = aggregate(rows, lock={"policy_sha256": "synthetic_test_sha"})
    assert report["sample_count"] == 3
    assert report["policy_hash"] == "synthetic_test_sha"
    assert report["primary_metric"] == "graph_hybrid_minus_hybrid_recall@5"
    assert report["model"]["revision"] == (
        "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
    )
    assert report["decision"] in (
        "INCONCLUSIVE_NO_AUTOMATIC_PROMOTION",
        "NO_GO_PRIMARY_RECALL_BELOW_BASELINE",
        "PRIMARY_POSITIVE_PENDING_COST_AND_PROVENANCE_REVIEW",
    )
    assert len(report["metrics"]["recall@5"]["paired_bootstrap_95ci"]) == 2


def test_invalid_locked_policy_rejected_before_model_load(tmp_path):
    cohort = tmp_path / "cohort.json"
    lock = tmp_path / "policy.json"
    cache = tmp_path / "data.json"
    cohort.write_text(json.dumps({"reserved_query_ids": ["a"]}), encoding="utf-8")
    lock.write_text(json.dumps({"policy": {"graph_bonus_weight": 999}}), encoding="utf-8")
    with pytest.raises(ValueError, match="cohort"):
        load_locked_inputs(cohort_file=cohort, lock_file=lock, dataset_cache=cache)

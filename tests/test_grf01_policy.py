from __future__ import annotations

import hashlib
import inspect
import json

import pytest

from raglab.core import Document, SearchResult
from raglab.fusion import reciprocal_rank_fusion
from raglab.graph.evidence import EvidenceEdge, GraphNode
from raglab.graph import grf01_policy as policy


def fixture():
    docs = [
        Document("doc-a", "Aster Rover uses Orion Navigation.", "Aster Rover"),
        Document("doc-b", "Orion Navigation was built by Meridian Robotics.", "Orion Navigation"),
        Document("doc-c", "Solis Probe is a separate mission.", "Solis Probe"),
    ]
    dense = [
        SearchResult("doc-c", 0.96, 1),
        SearchResult("doc-a", 0.76, 2),
        SearchResult("doc-b", 0.53, 3),
    ]
    sparse = [
        SearchResult("doc-a", 2.1, 1),
        SearchResult("doc-b", 1.3, 2),
        SearchResult("doc-c", 0.1, 3),
    ]
    return docs, dense, sparse


def test_no_path_exactly_matches_existing_hybrid_rrf():
    docs, dense, sparse = fixture()
    nodes = [GraphNode(doc.id, doc.title) for doc in docs]
    result = policy.paired_rankings(
        "Aster Rover", docs, dense, sparse,
        nodes=nodes, edges=[], k=3,
    )
    reference = reciprocal_rank_fusion([dense, sparse], k=3, rrf_constant=60)
    assert result.hybrid == reference
    assert result.graph_hybrid == reference
    assert not result.trace["graph_activated"]
    assert not result.trace["boosted_document_ids"]


def test_source_paths_have_small_bounded_bonus():
    docs, dense, sparse = fixture()
    result = policy.paired_rankings("Aster Rover", docs, dense, sparse, k=3)
    assert result.trace["graph_activated"]
    assert result.trace["paths"]
    assert all(
        source in {doc.id for doc in docs}
        for path in result.trace["paths"]
        for source in path["source_document_ids"]
    )
    base = {r.doc_id: r.score for r in result.hybrid}
    raised = {r.doc_id: r.score for r in result.graph_hybrid}
    for doc_id, value in base.items():
        gain = raised[doc_id] - value
        assert -1e-12 <= gain <= 0.1 / 61 + 1e-12
    assert not result.trace["gold_labels_used"]
    assert not result.trace["semantic_support_verified"]
    assert result.trace["policy_sha256"] == policy.policy_fingerprint()


def test_forged_relations_fail_closed():
    docs, dense, sparse = fixture()
    nodes = [GraphNode(doc.id, doc.title) for doc in docs]
    with pytest.raises(ValueError, match="quote"):
        policy.paired_rankings(
            "Aster Rover", docs, dense, sparse,
            nodes=nodes, k=3,
            edges=[EvidenceEdge(
                "fake", "doc-a", "mentions", "doc-b", "doc-a",
                "Aster Rover invented a spaceship.",
            )],
        )


def test_reject_mismatched_candidates_and_bad_k():
    docs, dense, sparse = fixture()
    with pytest.raises(ValueError, match="ALL identical"):
        policy.paired_rankings("Aster Rover", docs, dense[:2], sparse, k=3)
    broken = sparse.copy()
    broken[2] = SearchResult("not-present", 0, 3)
    with pytest.raises(ValueError, match="missing, duplicated or foreign"):
        policy.paired_rankings("Aster Rover", docs, dense, broken, k=3)
    with pytest.raises(ValueError, match="top-k"):
        policy.paired_rankings("Aster Rover", docs, dense, sparse, k=0)


def test_gold_cannot_enter_ranker_and_hyperparameters_frozen():
    assert not (
        set(inspect.signature(policy.paired_rankings).parameters)
        & {"gold", "qrels", "supporting_facts", "answer"}
    )
    assert policy.POLICY["rrf_constant"] == 60
    assert policy.POLICY["graph_bonus_weight"] == 0.10
    assert policy.POLICY["model_revision"] == "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
    assert policy.POLICY["model_license"] == "apache-2.0"


def fake_cohort():
    ids = [f"bridge-{index:03d}" for index in range(60)]
    digest = hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()
    return {
        "schema_version": 1,
        "cohort_id": policy.COHORT_SCHEMA,
        "status": "reserved_not_evaluated",
        "dataset_sha256": policy.HOTPOT_SHA256,
        "prior_exposed_run_sha256": policy.PREVIOUS_STUDY_SHA256,
        "overlap_count_with_grf00": 0,
        "evaluation_scores": None,
        "reserved_query_ids": ids,
        "reserved_query_ids_sha256": digest,
    }, digest


def test_policy_lock_is_idempotent_and_never_runs_models(tmp_path, monkeypatch):
    cohort, digest = fake_cohort()
    monkeypatch.setattr(policy, "EXPECTED_COHORT_SHA256", digest)
    manifest_path = tmp_path / "cohort.json"
    manifest_path.write_text(json.dumps(cohort), encoding="utf-8")
    output = tmp_path / "policy.json"
    lock = policy.lock_policy_manifest(manifest_path, output)
    assert not lock["model_weights_loaded"]
    assert not lock["scores_computed"]
    assert not lock["benchmark_run"]
    assert lock["policy_sha256"] == policy.policy_fingerprint()
    assert policy.lock_policy_manifest(manifest_path, output) == lock
    output.write_text('{"tampered":true}', encoding="utf-8")
    with pytest.raises(ValueError, match="refusing overwrite"):
        policy.lock_policy_manifest(manifest_path, output)


def test_scored_or_overlapping_cohorts_are_rejected(tmp_path, monkeypatch):
    cohort, digest = fake_cohort()
    monkeypatch.setattr(policy, "EXPECTED_COHORT_SHA256", digest)
    source = tmp_path / "cohort.json"
    for modifications in (
        {"evaluation_scores": {"recall": 1}},
        {"overlap_count_with_grf00": 1},
        {"reserved_query_ids_sha256": "f" * 64},
        {"status": "scored"},
    ):
        source.write_text(json.dumps({**cohort, **modifications}), encoding="utf-8")
        with pytest.raises(ValueError):
            policy.lock_policy_manifest(source, tmp_path / "lock.json")

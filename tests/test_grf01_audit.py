"""GRF-01 post-run audit tests use entirely synthetic documents, never reserved DEV."""
from __future__ import annotations

import copy
import hashlib

import numpy as np
import pytest

from raglab.graph.grf01_audit import audit, markdown
from raglab.graph.grf01_policy import POLICY, policy_fingerprint
from raglab.graph.grf01_study import aggregate, run_one_case


class TinyEncoder:
    name = "offline-synthetic-only"

    def encode(self, texts):
        return np.asarray([
            [float("aster" in t.lower()), float("orion" in t.lower()),
             float("solis" in t.lower()), 1.0] for t in texts
        ], dtype=np.float32)


def fixtures():
    source = {
        "_id": "a",
        "type": "bridge",
        "question": "Who made the Orion instrument on Aster Rover?",
        "context": [
            ["Aster Rover", ["Aster Rover uses Orion Navigation."]],
            ["Orion Navigation", ["Orion Navigation was built by Meridian Robotics."]],
            ["Solis Probe", ["A different independent mission."]],
        ],
        "supporting_facts": [["Aster Rover", 0], ["Orion Navigation", 0]],
    }
    rows = []
    for i in range(3):
        record = {**source, "_id": f"synthetic-{i}"}
        rows.append(run_one_case(record, embeddings=TinyEncoder()))
    ids = [row["question_id"] for row in rows]
    digest = hashlib.sha256("\n".join(ids).encode()).hexdigest()
    cohort = {
        "status": "reserved_not_evaluated",
        "cohort_id": "GRF01-RESERVED-DEV-01",
        "dataset_sha256": "4e9ecb5c8d3b719f624d66b60f8d56bf227f03914f5f0753d6fa1b359d7104ea",
        "overlap_count_with_grf00": 0,
        "reserved_query_ids": ids,
        "reserved_query_ids_sha256": digest,
    }
    lock = {
        "status": "policy_locked_before_evaluation",
        "cohort_query_ids_sha256": digest,
        "policy_sha256": policy_fingerprint(),
        "policy": POLICY,
        "scores_computed": False,
        "benchmark_run": False,
    }
    report = aggregate(rows, lock=lock)
    return report, cohort, lock


def test_valid_synthetic_archive_audits_without_model_calls():
    report, cohort, lock = fixtures()
    summary = audit(report, cohort, lock, "a" * 64, canonical=False)
    assert summary["sample_count"] == 3
    assert summary["policy_sha256"] == policy_fingerprint()
    assert summary["metrics"]["recall@5"]["hybrid"] == report["metrics"]["recall@5"]["hybrid"]
    assert summary["kind"] == "verified_grf01_retrieval_aggregate"
    assert summary["source_report_sha256"] == "a" * 64
    assert "Aster Rover" not in str(summary)
    assert "Bootstrap CI95" in markdown(summary)


def test_wrong_paired_delta_fails():
    report, cohort, lock = fixtures()
    report["metrics"]["recall@3"]["graph_hybrid_minus_hybrid_delta"] += 0.1
    with pytest.raises(ValueError, match="numeric"):
        audit(report, cohort, lock, "h", canonical=False)


def test_wrong_bootstrap_ci_fails():
    report, cohort, lock = fixtures()
    report["metrics"]["recall@5"]["paired_bootstrap_95ci"] = [0.99, 0.99]
    with pytest.raises(ValueError, match="numeric"):
        audit(report, cohort, lock, "h", canonical=False)


def test_cannot_change_cohort_or_model_contract():
    report, cohort, lock = fixtures()
    cohort["reserved_query_ids"].reverse()
    with pytest.raises(ValueError, match="cohort"):
        audit(report, cohort, lock, "h", canonical=False)
    report, cohort, lock = fixtures()
    report["model"]["revision"] = "unverified-latest"
    with pytest.raises(ValueError, match="provenance"):
        audit(report, cohort, lock, "h", canonical=False)


def test_cannot_forge_gold_recall_or_graph_source_ids():
    report, cohort, lock = fixtures()
    report["cases"][0]["recall"]["hybrid"]["recall@1"] += 0.25
    with pytest.raises(ValueError, match="numeric"):
        audit(report, cohort, lock, "h", canonical=False)
    report, cohort, lock = fixtures()
    report["cases"][0]["ranked_original_doc_ids"]["hybrid"][0] = "outside-corpus"
    with pytest.raises(ValueError, match="source IDs"):
        audit(report, cohort, lock, "h", canonical=False)


def test_disjoint_dev_cannot_claim_canonical_60_from_toy_fixture():
    report, cohort, lock = fixtures()
    with pytest.raises(ValueError, match="cohort"):
        audit(report, cohort, lock, "h")

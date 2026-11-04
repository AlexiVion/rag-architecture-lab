from __future__ import annotations

import hashlib
import json

import pytest

from raglab.graph.hotpotqa_benchmark import benchmark_bridge_dev
from raglab.graph.hotpotqa_diagnosis import audit_saved_run, render_markdown


def record(identifier: str):
    return {
        "_id": identifier,
        "type": "bridge",
        "level": "easy",
        "question": "Which institution developed the instrument used by Project Alpha?",
        "context": [
            ["Project Alpha", ["Project Alpha uses Orion Instrument."]],
            ["Orion Instrument", ["Orion Instrument was developed at Meridian College."]],
            ["Meridian College", ["Meridian College is a research university."]],
            ["Other Topic", ["A completely unrelated subject."]],
        ],
        "supporting_facts": [["Project Alpha", 0], ["Orion Instrument", 0]],
        "answer": "Meridian College",
    }


def saved_report():
    report = benchmark_bridge_dev([record("a"), record("b"), record("c")], seed=17)
    report["sample_query_ids_sha256"] = hashlib.sha256("a\nb\nc".encode()).hexdigest()
    return report


def test_saved_run_verified_and_public_export_omits_questions():
    result = audit_saved_run(saved_report(), "abcd", canonical=False)
    assert result["sample_count"] == 3
    assert result["source_report_sha256"] == "abcd"
    assert result["metrics"]["recall@5"]["bm25"] == pytest.approx(1)
    assert result["subgroups"]["paths_present"]["cases"] == 3
    assert "Project Alpha" not in json.dumps(result)
    assert "supporting_facts" not in json.dumps(result)
    assert "95% paired CI" in render_markdown(result)


def test_tampered_mean_rejected():
    report = saved_report()
    report["metrics"]["recall@3"]["bm25"] += 0.1
    with pytest.raises(ValueError, match="score differs"):
        audit_saved_run(report, "sha", canonical=False)


def test_tampered_bootstrap_ci_rejected():
    report = saved_report()
    report["metrics"]["recall@5"]["paired_bootstrap_95ci"] = [0.9, 0.9]
    with pytest.raises(ValueError, match="confidence interval differs"):
        audit_saved_run(report, "sha", canonical=False)


def test_changed_query_ids_rejected():
    report = saved_report()
    report["queries"][0]["question_id"] = "changed"
    with pytest.raises(ValueError, match="fingerprint mismatch"):
        audit_saved_run(report, "sha", canonical=False)


def test_no_path_fallback_divergence_rejected():
    report = saved_report()
    item = report["queries"][0]
    item["graph_path_count"] = 0
    item["baseline_ranked_titles"] = ["A"]
    item["candidate_ranked_titles"] = ["B"]
    with pytest.raises(ValueError, match="No-path fallback"):
        audit_saved_run(report, "sha", canonical=False)


def test_test_split_rejected():
    report = saved_report()
    report["split"] = "test"
    with pytest.raises(ValueError, match="provenance"):
        audit_saved_run(report, "sha", canonical=False)


def test_canonical_export_requires_60_cases():
    with pytest.raises(ValueError, match="60-query"):
        audit_saved_run(saved_report(), "sha")

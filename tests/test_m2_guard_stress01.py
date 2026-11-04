"""Offline, authored, non-generalizable guard robustness controls."""
from __future__ import annotations

import json

import pytest

from raglab.evaluation.m2_guard_stress01 import (
    CONDITIONS, FROZEN_SHA256, canonical_sha256, evaluate_guard, frozen_cases,
)
from raglab.evaluation.m2_synth_runner import write_or_check


def test_cohort_frozen_and_disjoint_from_old_names():
    cases = frozen_cases()
    assert len(cases) == 40
    assert len(set(row["id"] for row in cases)) == 40
    assert canonical_sha256(cases) == FROZEN_SHA256
    for condition in CONDITIONS:
        assert sum(row["condition"] == condition for row in cases) == 8
    assert all(row["question"] and row["sources"] for row in cases)
    assert not any("Kestrel Explorer" in row["question"] for row in cases)


def test_40_case_authored_stress_probes_rejection_and_coverage():
    report = evaluate_guard()
    assert report["cases"] == 40
    assert report["authored_positive_count"] == 16
    assert report["authored_negative_count"] == 24
    assert report["new_model_calls"] == 0
    assert report["external_publications"] == 0
    assert report["guard_promoted_to_default"] is False
    assert report["status"].endswith("NOT_INDEPENDENT_SEMANTIC_QUALITY")
    assert len(report["post_generation_strict_parser_checks_on_authored_text"]) == 8
    assert all(c["strict_consistent_candidate_match"] for c in report["post_generation_strict_parser_checks_on_authored_text"])
    assert all(c["wrong_manufacturer_candidate_rejected"] for c in report["post_generation_strict_parser_checks_on_authored_text"])
    assert all(c["published"] is False for c in report["post_generation_strict_parser_checks_on_authored_text"])


def test_existing_exact_parser_exposes_false_rejects_of_clear_paraphrases():
    report = evaluate_guard()
    assert report["by_condition"]["canonical_supported"]["allowed"] == 8
    assert report["by_condition"]["paraphrase_supported"]["allowed"] == 0
    assert report["by_condition"]["paraphrase_supported"]["false_reject"] == 8
    assert report["false_reject_on_authored_positive"] == 8


def test_known_negative_patterns_are_blocked_not_semantically_certified():
    report = evaluate_guard()
    assert report["false_accept_on_authored_negative"] == 0
    for name in ("cross_entity_irrelevant", "contradictory_sources", "injected_extra_claim"):
        assert report["by_condition"][name]["allowed"] == 0
        assert report["by_condition"][name]["false_accept"] == 0
    assert report["by_condition"]["contradictory_sources"]["reasons"] == {
        "DENY_SOURCE_CONTRADICTION": 8
    }
    assert report["by_condition"]["injected_extra_claim"]["reasons"] == {
        "DENY_UNPARSEABLE_SOURCE": 8
    }


def test_report_is_idempotent_and_cannot_overwrite_original(tmp_path):
    report = evaluate_guard()
    path = tmp_path / "audit.json"
    assert write_or_check(path, report) is True
    assert write_or_check(path, report) is False
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["cohort_sha256"] == FROZEN_SHA256
    saved["false_accept_on_authored_negative"] = 999
    path.write_text(json.dumps(saved), encoding="utf-8")
    with pytest.raises(FileExistsError, match="differs"):
        write_or_check(path, report)


def test_default_pipeline_still_does_not_use_development_guard():
    from inspect import signature
    from raglab.rag import RAGPipeline
    assert signature(RAGPipeline).parameters["evidence_gate"].default is None

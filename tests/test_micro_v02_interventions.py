"""Visible synthetic intervention contracts, NOT independent paper evidence."""
from __future__ import annotations

from collections import defaultdict

from raglab.micro_v02.intervention_audit import (
    EXPECTED, NAMES, OPERATIONS, build_cases, run_pilot,
)


def test_predeclared_paired_design_has_no_duplicate_ids_or_coverage_gaps():
    cases = build_cases()
    assert len(cases) == 12 * 9
    assert len({case.case_id for case in cases}) == len(cases)
    groups = defaultdict(set)
    questions = defaultdict(set)
    for case in cases:
        groups[case.group_id].add(case.condition)
        questions[case.group_id].add(case.question)
        assert len({d.id for d in case.documents}) == len(case.documents)
    assert len(groups) == len(NAMES)
    assert all(g == set(OPERATIONS) for g in groups.values())
    assert all(len(q) == 1 for q in questions.values())


def test_all_structured_software_interventions_comply_without_wrong_accepts():
    result = run_pilot()
    assert result["schema_version"] == 1
    assert result["status"].startswith("VISIBLE_AUTHOR_GENERATED")
    assert result["n"] == 108
    assert result["compliant"] == result["n"]
    assert result["accepted"] == 60
    assert result["wrong_accepts"] == 0
    assert all(v["n"] == len(NAMES) and v["compliant"] == len(NAMES)
               for v in result["by_condition"].values())


def test_unchanged_support_positive_controls_and_conflict_refusals():
    result = run_pilot()
    by_group = defaultdict(dict)
    for row in result["rows"]:
        by_group[row["group_id"]][row["condition"]] = row
        assert row["actual_status"] == EXPECTED[row["condition"]]
    for rows in by_group.values():
        answer = rows["baseline"]["actual_answer"]
        assert answer is not None
        for op in (
            "permutation", "irrelevant_addition", "corroboration",
            "other_field_conflict",
        ):
            assert rows[op]["actual_status"] == "ANSWER"
            assert rows[op]["actual_answer"] == answer
        assert rows["corroboration"]["citations"] == 2
        assert rows["direct_conflict"]["actual_status"] == "CONFLICT"
        assert rows["direct_conflict"]["actual_answer"] is None
        assert rows["support_deletion"]["actual_status"] == "INSUFFICIENT"
        for op in ("malformed_entity", "budget_exhaustion"):
            assert rows[op]["actual_status"] == "REVIEW"
            assert not rows[op]["scan_complete"]


def test_pilot_is_deterministic_except_no_performance_timing_is_emitted():
    first, second = run_pilot(), run_pilot()
    assert first == second
    assert all("total_ms" not in row for row in first["rows"])
    assert "not blinded" in " ".join(first["limitations"])

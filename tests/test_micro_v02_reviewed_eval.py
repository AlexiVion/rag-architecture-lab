"""Synthetic test doubles for REVIEWED evaluation harness, not human labels."""
from __future__ import annotations

from copy import deepcopy

import pytest

from raglab.core import Document
from raglab.micro_v02.pipeline import MicroRAG
from raglab.micro_v02.reviewed_eval import (
    validate_reviewed_records, evaluate_reviewed, cluster_bootstrap_risk,
)
from raglab.micro_v02.evaluation import evaluate_cases

A=Document("a","entity: Station Aurora\nstart_year: 2012\nmanager: Camille\n")
B=Document("b","entity: Station Aurora\nstart_year: 2015\nmanager: Camille\n")


def reviewed(case_id,question,status,group,answer=None,split="evaluation",domain="fiction"):
    review={"status":status,"answer":answer}
    return {
        "id":case_id,
        "question":question,
        "source_group_id":group,
        "domain":domain,
        "split":split,
        "expected_status":status,
        "expected_answer":answer,
        "reviewers":[
            {"reviewer_id":"reviewer-one",**review},
            {"reviewer_id":"reviewer-two",**review},
        ],
    }


def test_requires_two_distinct_reviewers():
    row=reviewed("x","What is the start year for Station Aurora?","CONFLICT","aurora")
    row["reviewers"][1]["reviewer_id"]="reviewer-one"
    with pytest.raises(ValueError,match="different"):
        validate_reviewed_records([row])
    row["reviewers"]=[{"reviewer_id":"only","status":"CONFLICT"}]
    with pytest.raises(ValueError,match="Two independent"):
        validate_reviewed_records([row])


def test_contradicting_reviewer_labels_require_adjudication():
    row=reviewed("x","What is the start year for Station Aurora?","CONFLICT","aurora")
    row["reviewers"][1]["status"]="ANSWER"
    row["reviewers"][1]["answer"]="2012"
    with pytest.raises(ValueError,match="adjudication"):
        validate_reviewed_records([row])
    row["adjudicated_by"]="adjudicator-record"
    assert validate_reviewed_records([row])["n"]==1


def test_never_mix_source_group_between_calibration_and_evaluation():
    q="What is the manager of Station Aurora?"
    a=reviewed("c",q,"ANSWER","aurora",answer="Camille",split="calibration")
    b=reviewed("e",q,"ANSWER","aurora",answer="Camille",split="evaluation")
    with pytest.raises(ValueError,match="leakage"):
        validate_reviewed_records([a,b])


def test_unanimous_reviewers_cannot_silently_disagree_with_gold():
    row=reviewed("c","What is the manager of Station Aurora?","ANSWER","aurora",answer="Camille")
    row["expected_answer"]="Wrong"
    with pytest.raises(ValueError,match="unanimous"):
        validate_reviewed_records([row])


def test_reviewed_evaluator_is_never_automatic_science_go():
    data=[
        reviewed("conflict","What is the start year for Station Aurora?","CONFLICT","aurora"),
        reviewed("answer","What is the manager of Station Aurora?","ANSWER","aurora",answer="Camille"),
    ]
    result=evaluate_reviewed(MicroRAG([A,B]),data,repetitions=100)
    assert result["evaluation_only"]["strict_correct"]==2
    assert result["evaluation_only"]["wrong_accepts"]==0
    assert result["group_bootstrap"]["source_groups"]==1
    assert result["scientific_release_approved"] is False
    assert result["software_target_checks_met"] is False
    assert "NOT_INDEPENDENTLY_AUTHENTICATED" in result["status"]


def test_reviewed_evaluator_counts_wrong_accepted_value():
    data=[reviewed("c","What is the start year for Station Aurora?","CONFLICT","aurora")]
    result=evaluate_reviewed(MicroRAG([A]),data,repetitions=100)
    assert result["evaluation_only"]["wrong_accepts"]==1
    assert result["evaluation_only"]["wrong_accept_rate"]==1.0
    assert result["scientific_release_approved"] is False


def test_refuse_all_is_not_claimed_zero_risk_certified():
    data=[{
        "id":"a","source_group_id":"g1",
        "expected_status":"ANSWER","observed_status":"INSUFFICIENT",
        "answered":False,"wrong_accept":False,
        "correct_answerable":False,"correct_conflict":False,
        "false_conflict_alarm":False,"correct":False,
    }]
    score=cluster_bootstrap_risk(data,repetitions=100)
    assert score["wrong_accept_rate_percentile_upper95"] is None
    assert score["draws_with_zero_accepted"]==100

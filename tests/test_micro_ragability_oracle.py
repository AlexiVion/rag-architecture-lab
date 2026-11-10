"""M1 oracle input contracts; fake model results NEVER reported as research."""
from __future__ import annotations

import pytest

from raglab.evaluation.ragability_conflict import read_ragability_tsv
from ragability_oracle_ablation_cpu import (
    ANSWER_COLUMNS, CONDITIONS, EXTERNAL_DATASET_SHA,
    compute_recall_delta_ci, evaluate_oracle, paired_conditions,
)


def fixture_rows():
    out=[]
    for i in range(53):
        group=i+1 if i<43 else i-42
        out.append({
            "contradiction_ID":str(group),
            "context_1":f"Station {group} started in 2012.",
            "context_2":f"Station {group} started in 2015.",
            "context_3_nc1_c2":f"Station {group} opened in 2012.",
            "context_4_nc1_nc2_nc3":f"Station {group} exists.",
            "query_text":f"When did Station {group} start?",
            "answer_context1":"2012",
            "answer_context2":"2015",
            "answer_context1_long":f"Station {group} began operating in 2012.",
            "answer_context2_long":f"Station {group} began operating in 2015.",
        })
    return out


def simple_stub(pairs):
    forward=[]
    reverse=[]
    for first,second in pairs:
        conflict = first != second and not (
            "opened in 2012" in second
        )
        values = [0.9,0.05,0.05] if conflict else [0.05,0.05,0.9]
        forward.append(values)
        reverse.append(values)
    return forward, reverse, {"total_batch_wall_ms":0.0,
                              "directional_pair_inputs":len(pairs)*2}


def test_all_registered_input_conditions_are_source_author_oracles():
    row=fixture_rows()[0]
    data=paired_conditions(row)
    assert tuple(data)==CONDITIONS
    assert data["oracle_short"]==("2012","2015")
    assert data["oracle_long"][0].endswith("2012.")
    assert "Question:" in data["oracle_query_long"][0]
    assert data["negative_identical_claim"][0]==data["negative_identical_claim"][1]
    assert data["negative_compatible_source"][0]!=data["negative_compatible_source"][1]


def test_rejects_missing_oracle_answer_instead_of_fabricating():
    row=fixture_rows()[0]
    row["answer_context1"]=""
    with pytest.raises(ValueError,match="Missing author oracle"):
        paired_conditions(row)


def test_group_bootstrap_uses_43_source_groups_not_53_rows():
    rows=fixture_rows()
    ci=compute_recall_delta_ci(rows,[False]*53,[True]*53,repetitions=100)
    assert ci["source_groups"]==43
    assert ci["delta"]==1.0
    assert ci["group_bootstrap_95_ci"]==[1.0,1.0]


def test_oracle_ablation_scores_noisy_positive_and_negative_modes():
    rows=fixture_rows()
    result=evaluate_oracle(rows,simple_stub)
    assert len(result["conditions"])==7
    assert result["conditions"]["raw_context"]["n"]==53
    assert result["conditions"]["oracle_short"]["correct"]==53
    assert result["conditions"]["negative_identical_claim"]["correct"]==53
    assert result["conditions"]["negative_compatible_source"]["correct"]==53
    assert len(result["oracle_minus_raw_paired_group_bootstrap"])==4
    assert "privileged" in result["warning"]
    assert "premise" not in result["conditions"]["raw_context"]["traces"][0]
    assert len(result["conditions"]["raw_context"]["traces"][0]["pair_sha256"])==64


def test_case_count_and_cluster_guardrails():
    rows=fixture_rows()
    with pytest.raises(ValueError,match="all 53"):
        evaluate_oracle(rows[:-1],simple_stub)
    for row in rows:
        row["contradiction_ID"]="1"
    with pytest.raises(ValueError,match="43"):
        compute_recall_delta_ci(rows,[False]*53,[True]*53,repetitions=100)

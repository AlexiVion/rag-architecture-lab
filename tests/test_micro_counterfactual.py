from __future__ import annotations

import math
from dataclasses import replace

import pytest

from raglab.micro.counterfactual import (
    build_counterfactual_corpus, protocol_manifest, verify_counterfactual_corpus,
)
from raglab.micro.cf_evaluation import (
    Prediction, calibrate, format_outcome, gate_prediction, locked_threshold,
    summarize, template_rule,
)


def pred(text="INSUFFICIENT_EVIDENCE", margin=0.0):
    if text == "INSUFFICIENT_EVIDENCE":
        return Prediction(text, None, None, None, margin, 20, 1.0, False, 1)
    return Prediction(text, "source", 0, len(text), margin, 20, 1.0, True, 1)


def test_repeated_seed_is_exact_and_groups_have_no_leakage():
    parts = build_counterfactual_corpus()
    again = build_counterfactual_corpus()
    assert set(parts) == {"dev", "calibration", "audit"}
    assert all(parts[k].sha256 == again[k].sha256 for k in parts)
    verify_counterfactual_corpus(parts)
    assert len({case.entity for p in parts.values() for case in p.cases}) == 36
    assert len({doc.id for p in parts.values() for doc in p.documents}) == 72
    for partition in parts.values():
        assert len(partition.cases) == 36
        assert len(partition.documents) == 24
        assert sum(c.kind == "answer" for c in partition.cases) == 18
        assert sum(c.kind == "absent" for c in partition.cases) == 12
        assert sum(c.kind == "conflict" for c in partition.cases) == 6
    manifest = protocol_manifest(parts)
    assert manifest["labels"].startswith("programmatic")
    assert all(
        x["cases"] == 36 for x in manifest["splits"].values()
    )


def test_corrupted_partition_fails_closed_without_relabeling():
    parts = build_counterfactual_corpus()
    changed = dict(parts)
    original = parts["dev"]
    changed["dev"] = replace(original, sha256="tampered")
    with pytest.raises(ValueError, match="SHA256 drift"):
        verify_counterfactual_corpus(changed)
    changed = dict(parts)
    changed["dev"] = replace(original, cases=original.cases[:-1])
    with pytest.raises(ValueError, match="partition size"):
        verify_counterfactual_corpus(changed)


def test_corpus_relative_labels_and_exact_provenance():
    part = build_counterfactual_corpus()["audit"]
    docs = {doc.id: doc for doc in part.documents}
    for case in part.cases:
        result = template_rule(
            case.question, case.entity,
            [docs[doc_id] for doc_id in case.eligible_document_ids],
        )
        evaluated = format_outcome(case, result)
        assert evaluated["correct_programmatic_label"] is True
        if case.kind == "answer":
            assert result.text == case.correct_answer
            assert result.doc_id in case.evidence_document_ids
            assert result.source_exact
            assert docs[result.doc_id].text[result.start:result.end] == result.text
        else:
            assert evaluated["refused"] is True
            assert result.doc_id is None


def test_rule_is_only_template_recognition_not_general_qa():
    part = build_counterfactual_corpus()["audit"]
    question = part.cases[0]
    docs = [d for d in part.documents if question.entity in d.text]
    result = template_rule("How does quantum gravity work?", question.entity, docs)
    assert result.text == "INSUFFICIENT_EVIDENCE"
    assert result.candidates_read == 0


def test_calibration_refuses_audit_and_dev_label_tuning():
    parts = build_counterfactual_corpus()
    for split in ("dev", "audit"):
        cases = list(parts[split].cases)
        with pytest.raises(ValueError, match="CALIBRATION"):
            calibrate(cases, [pred()] * len(cases))


def test_calibration_uses_only_frozen_candidate_grid_and_abstains_if_unsafe():
    cases = list(build_counterfactual_corpus()["calibration"].cases)
    # Every answer is incorrectly accepted. No threshold can achieve the
    # registered 15% conditional error cap with >=5 accepted predictions.
    wrong = [
        pred("not the gold label", margin=35.0)
        if c.kind == "answer" else pred("false contradiction answer", margin=35.0)
        for c in cases
    ]
    outcome = calibrate(cases, wrong)
    assert outcome["status"] == "CALIBRATION_UNSAFE_REFUSE_ALL"
    assert outcome["refuse_all"] is True
    assert outcome["threshold"] is None
    assert locked_threshold(outcome) == math.inf
    gated = [gate_prediction(p, locked_threshold(outcome)) for p in wrong]
    rows = [format_outcome(c, p) for c, p in zip(cases, gated)]
    metrics = summarize(rows)
    assert metrics["accepted"] == 0
    assert metrics["wrong_accepts"] == 0
    assert metrics["answerable_correct"] == 0
    assert metrics["false_refusals_on_answerable"] == 18


def test_calibration_can_choose_threshold_without_leaking_audit():
    cases = list(build_counterfactual_corpus()["calibration"].cases)
    predictions = []
    # Answerable cases get correct value and high margin, negatives get
    # incorrect accepted text with a low margin that calibration must reject.
    for case in cases:
        if case.kind == "answer":
            predictions.append(pred(case.correct_answer, margin=15))
        else:
            predictions.append(pred("the wrong fact", margin=0.7))
    decision = calibrate(cases, predictions)
    assert not decision["refuse_all"]
    assert decision["status"].startswith("CALIBRATION_CONDITIONAL")
    threshold = locked_threshold(decision)
    assert threshold in (1.0, 2.0, 3.0, 5.0, 8.0, 12.0)
    rows = [
        format_outcome(c, gate_prediction(p, threshold))
        for c, p in zip(cases, predictions)
    ]
    summary = summarize(rows)
    assert summary["answerable_correct"] == 18
    assert summary["wrong_accepts"] == 0
    assert summary["conflict_correct_refusals"] == 6
    assert summary["absent_correct_refusals"] == 12


def test_calibration_cannot_claim_unsafe_risk_guarantee():
    with pytest.raises(ValueError, match="calibration"):
        locked_threshold({
            "split": "audit", "threshold": 1, "refuse_all": False,
        })
    with pytest.raises(ValueError, match="threshold"):
        gate_prediction(pred("x", margin=3.0), threshold=-1)
    with pytest.raises(ValueError, match="guardrails"):
        calibrate(
            list(build_counterfactual_corpus()["calibration"].cases),
            [pred()] * 36,
            max_wrong_accept_rate=-1,
        )

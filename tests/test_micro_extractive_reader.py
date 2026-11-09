from __future__ import annotations

import math

import pytest

from raglab.micro.extractive_reader import decode_qa_span


def _extraction(*, start_score=8.0, end_score=8.0, null=1.0):
    return decode_qa_span(
        context="Mars is red.",
        offsets=[(0, 0), (0, 0), (0, 4), (5, 7), (8, 11), (0, 0)],
        sequence_ids=[None, 0, 1, 1, 1, None],
        start_logits=[null, 0, 1, 0, start_score, 0],
        end_logits=[null, 0, 1, 0, end_score, 0],
        cls_index=0,
        max_answer_tokens=3,
        threshold=0,
    )


def test_qa_span_is_exact_original_document_substring():
    p = _extraction()
    assert p.answered
    assert p.text == "red"
    assert (p.start, p.end) == (8, 11)
    assert "Mars is red."[p.start:p.end] == p.text
    assert p.source_exact
    assert p.logit_margin > 0


def test_null_logit_threshold_produces_explicit_abstention():
    p = _extraction(start_score=1.0, end_score=1.0, null=9.0)
    assert not p.answered
    assert p.text == "INSUFFICIENT_EVIDENCE"
    assert p.start is None and p.end is None
    assert not p.source_exact


def test_rejects_nonfinite_or_misaligned_model_inputs():
    with pytest.raises(ValueError, match="Nonfinite"):
        _ = _extraction(start_score=math.nan)
    with pytest.raises(ValueError, match="shapes"):
        decode_qa_span(
            context="hi", offsets=[(0, 1)], sequence_ids=[1],
            start_logits=[1], end_logits=[],
        )
    with pytest.raises(ValueError, match="Invalid"):
        decode_qa_span(
            context="hi", offsets=[(0, 1)], sequence_ids=[1],
            start_logits=[1], end_logits=[1], max_answer_tokens=0,
        )


def test_mask_prevents_question_tokens_from_becoming_source_answers():
    pred = decode_qa_span(
        context="safe",
        offsets=[(0, 0), (0, 4), (0, 4)],
        sequence_ids=[None, 0, 1],
        start_logits=[0, 500, 2],
        end_logits=[0, 500, 2],
        cls_index=0,
    )
    assert pred.answered and pred.text == "safe"


def test_empty_context_mask_refuses():
    p = decode_qa_span(
        context="", offsets=[(0, 0), (0, 0)],
        sequence_ids=[None, 0],
        start_logits=[0, 1], end_logits=[0, 1],
    )
    assert not p.answered

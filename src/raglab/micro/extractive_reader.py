"""Source-verbatim span decoding for small extractive QA encoders.

A span being copied from a document proves lexical provenance, NOT that the
source entails the correct answer. Null-vs-span logit threshold is frozen at 0
without tuning on publicly exposed SQuAD DEV.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True, slots=True)
class ExtractivePrediction:
    text: str
    start: int | None
    end: int | None
    logit_margin: float
    answered: bool
    source_exact: bool


def decode_qa_span(
    *,
    context: str,
    offsets: Sequence[tuple[int, int]],
    sequence_ids: Sequence[int | None],
    start_logits: Sequence[float],
    end_logits: Sequence[float],
    cls_index: int = 0,
    max_answer_tokens: int = 25,
    candidate_limit: int = 20,
    threshold: float = 0.0,
) -> ExtractivePrediction:
    """Freeze null-thresholded short-answer extraction under exact offsets."""
    n = len(offsets)
    if n == 0 or not (
        n == len(sequence_ids) == len(start_logits) == len(end_logits)
    ):
        raise ValueError("Token shapes do not match")
    if not (0 <= cls_index < n) or max_answer_tokens <= 0 or candidate_limit <= 0:
        raise ValueError("Invalid CLS or answer constraints")
    if not all(math.isfinite(float(x)) for x in (*start_logits, *end_logits)):
        raise ValueError("Nonfinite QA logits")
    valid = [
        i for i, kind in enumerate(sequence_ids)
        if kind == 1 and offsets[i][1] > offsets[i][0]
        and 0 <= offsets[i][0] < offsets[i][1] <= len(context)
    ]
    null_score = float(start_logits[cls_index]) + float(end_logits[cls_index])
    if not valid:
        return ExtractivePrediction(
            "INSUFFICIENT_EVIDENCE", None, None,
            -math.inf, False, False,
        )
    starts = sorted(
        valid, key=lambda i: (-float(start_logits[i]), i)
    )[:candidate_limit]
    ends = sorted(
        valid, key=lambda i: (-float(end_logits[i]), i)
    )[:candidate_limit]
    best_score = -math.inf
    best_indices: tuple[int, int] | None = None
    for i in starts:
        for j in ends:
            if j < i or j - i + 1 > max_answer_tokens:
                continue
            if not context[offsets[i][0]: offsets[j][1]].strip():
                continue
            score = float(start_logits[i]) + float(end_logits[j])
            if score > best_score or (
                score == best_score and (
                    best_indices is None or (i, j) < best_indices
                )
            ):
                best_score = score
                best_indices = (i, j)
    if best_indices is None:
        return ExtractivePrediction(
            "INSUFFICIENT_EVIDENCE", None, None,
            -math.inf, False, False,
        )
    margin = best_score - null_score
    if margin <= threshold:
        return ExtractivePrediction(
            "INSUFFICIENT_EVIDENCE", None, None,
            margin, False, False,
        )
    i, j = best_indices
    start, end = offsets[i][0], offsets[j][1]
    original = context[start:end]
    return ExtractivePrediction(
        original, start, end, margin, True, True
    )

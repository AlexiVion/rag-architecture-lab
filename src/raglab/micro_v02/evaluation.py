"""Transparent development metrics, never automatic scientific certification.

Visible synthetic fixtures can validate software behavior only; independently
human-reviewed source-group holdouts remain an external release requirement.
No threshold may be fitted on the audit labels supplied to this evaluator.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

from raglab.micro_v02.pipeline import MicroRAG

STATES = ("ANSWER", "CONFLICT", "INSUFFICIENT", "REVIEW")


def evaluate_cases(pipeline: MicroRAG, cases: list[dict]) -> dict[str, Any]:
    if not cases or len(cases) > 10000:
        raise ValueError("Expected 1..10,000 evaluation cases")
    rows: list[dict] = []
    case_ids: set[str] = set()
    for row in cases:
        case_id, question, expected = row["id"], row["question"], row["expected_status"]
        if not isinstance(case_id, str) or case_id in case_ids:
            raise ValueError("Every evaluation case needs a unique ID")
        case_ids.add(case_id)
        if expected not in STATES:
            raise ValueError("Unknown expected decision status")
        response = pipeline.answer(question)
        expected_answer = row.get("expected_answer")
        matched_state = response.status == expected
        answer_match = (
            expected != "ANSWER" or (
                response.answer is not None
                and isinstance(expected_answer, str)
                and response.answer.casefold() == expected_answer.casefold()
            )
        )
        correct = matched_state and answer_match
        # Publishing a wrong value or one that should have been refused is
        # counted as wrong acceptance rather than merely a class error.
        accepted = response.status == "ANSWER"
        wrong_accept = accepted and not correct
        rows.append({
            "id": case_id,
            "group_id": row.get("group_id", case_id),
            "question": question,
            "expected_status": expected,
            "expected_answer": expected_answer,
            "status": response.status,
            "answer": response.answer,
            "correct": correct,
            "wrong_accept": wrong_accept,
            "answered": accepted,
            "retrieval_ms": response.timings_ms["retrieval"],
            "total_ms": response.timings_ms["total"],
            "reader_calls": response.read_calls,
            "citations_verified": bool(
                response.citations and response.status == "ANSWER"
            ),
            "warnings": list(response.warnings),
        })
    accepted = [r for r in rows if r["answered"]]
    answerable = [r for r in rows if r["expected_status"] == "ANSWER"]
    conflicts = [r for r in rows if r["expected_status"] == "CONFLICT"]
    misses = [r for r in rows if r["expected_status"] == "INSUFFICIENT"]
    groups = {str(r["group_id"]) for r in rows}
    result = {
        "status": "VISIBLE_SYNTHETIC_DEVELOPMENT_FIXTURE_NOT_INDEPENDENT_VALIDATION",
        "n": len(rows),
        "groups": len(groups),
        "strict_correct": sum(r["correct"] for r in rows),
        "strict_accuracy": mean(r["correct"] for r in rows),
        "correct_answerable": sum(r["correct"] for r in answerable),
        "answerable_n": len(answerable),
        "correct_conflicts": sum(r["correct"] for r in conflicts),
        "conflict_n": len(conflicts),
        "correct_insufficient": sum(r["correct"] for r in misses),
        "insufficient_n": len(misses),
        "accepted": len(accepted),
        "coverage": len(accepted) / len(rows),
        "wrong_accepts": sum(r["wrong_accept"] for r in rows),
        "wrong_accept_rate": (
            mean(r["wrong_accept"] for r in accepted) if accepted else None
        ),
        "answerable_correct_coverage": (
            sum(r["correct"] for r in answerable) / len(answerable)
            if answerable else None
        ),
        "reader_calls_total": sum(r["reader_calls"] for r in rows),
        "mean_total_ms": mean(r["total_ms"] for r in rows),
        "model_calls": 0 if pipeline.reader.name == "structured_literal" else sum(
            r["reader_calls"] for r in rows
        ),
        "cases": rows,
        "limitations": [
            "Synthetic examples were written for the pipeline and are not independent.",
            "No real human verification or new hidden source-group holdout was completed.",
            "No statistically valid safety certification follows from this output.",
            "Exact source quotation alone is not semantic entailment.",
        ],
    }
    return result


def write_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n", encoding="utf-8",
    )

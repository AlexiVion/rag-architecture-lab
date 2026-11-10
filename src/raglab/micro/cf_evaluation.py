"""Corpus-level correctness, calibration and cheap template-rule control.

The rule is deliberately handcrafted for MICRO-CF's four sentence templates;
it is a benchmark shortcut detector, NOT a general model-free QA solution.
The audit partition is visible in source code: do not call it blind holdout.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from dataclasses import dataclass
from statistics import mean
from typing import Any, Callable

from raglab.core import Document
from raglab.micro.counterfactual import CFCase, CFPartition, sha
from raglab.micro.squad_metrics import normalize_answer

_PHASE = re.compile(
    r"\bphase marker (?:registered for station [\w-]+ is |reads |of )?"
    r"([a-z]+ [a-z]+)\b", re.IGNORECASE
)
_SEAL = re.compile(
    r"\bstorage seal (?:for [\w-]+ is |is |as |of |reads )?"
    r"([a-z]+ [a-z]+)\b", re.IGNORECASE
)


def is_refusal(text: str) -> bool:
    return text.strip() == "INSUFFICIENT_EVIDENCE"


@dataclass(frozen=True, slots=True)
class Prediction:
    text: str
    doc_id: str | None
    start: int | None
    end: int | None
    margin: float | None
    tokens: int
    cpu_ms: float
    source_exact: bool
    candidates_read: int


def template_rule(question: str, entity: str, docs: list[Document]) -> Prediction:
    """No gold labels, model, hidden metadata or external lookup at inference.

    Only templates from our own synthetic generator are understood.
    """
    term = _PHASE if "phase marker" in question.lower() else (
        _SEAL if "storage seal" in question.lower() else None
    )
    if term is None:
        return Prediction("INSUFFICIENT_EVIDENCE", None, None, None, None, 0, 0.0, False, 0)
    matches: list[tuple[str, Document, int, int]] = []
    for doc in docs:
        if entity not in doc.text:
            continue
        for match in term.finditer(doc.text):
            matches.append((match.group(1).lower(), doc, match.start(1), match.end(1)))
    unique = sorted(set(value for value, _, _, _ in matches))
    if len(unique) != 1:
        return Prediction(
            "INSUFFICIENT_EVIDENCE", None, None, None, None,
            0, 0.0, False, len(docs),
        )
    value, source, start, end = next(m for m in matches if m[0] == unique[0])
    return Prediction(
        value, source.id, start, end, None, 0, 0.0,
        source.text[start:end] == value, len(docs),
    )


def format_outcome(case: CFCase, prediction: Prediction) -> dict[str, Any]:
    refused = is_refusal(prediction.text)
    correct = (
        refused if case.kind != "answer" else (
            not refused and prediction.doc_id in case.evidence_document_ids
            and normalize_answer(prediction.text)
            == normalize_answer(case.correct_answer or "")
        )
    )
    if prediction.doc_id is None:
        if not refused:
            raise ValueError("Answered predictions require original source provenance")
    elif not prediction.source_exact or prediction.start is None or prediction.end is None:
        raise ValueError("Source-based prediction missing verified verbatim offsets")
    return {
        "case_id": case.case_id,
        "entity": case.entity,
        "split": case.split,
        "kind": case.kind,
        "expected": case.correct_answer,
        "prediction": prediction.text,
        "refused": refused,
        "correct_programmatic_label": bool(correct),
        "wrong_accept": (not refused) and (not correct),
        "false_refusal": refused and case.kind == "answer",
        "selected_doc_id": prediction.doc_id,
        "source_start": prediction.start,
        "source_end": prediction.end,
        "source_exact": prediction.source_exact,
        "raw_null_margin": prediction.margin,
        "model_input_tokens": prediction.tokens,
        "model_cpu_forward_ms": prediction.cpu_ms,
        "candidate_reader_forwards": prediction.candidates_read,
        "source_document_eligible": (
            prediction.doc_id in case.eligible_document_ids
            if prediction.doc_id is not None else None
        ),
    }


def summarize(rows: list[dict]) -> dict:
    if not rows:
        raise ValueError("No evaluation rows")
    accepted = [x for x in rows if not x["refused"]]
    positives = [x for x in rows if x["kind"] == "answer"]
    absent = [x for x in rows if x["kind"] == "absent"]
    conflicts = [x for x in rows if x["kind"] == "conflict"]
    return {
        "n": len(rows),
        "answerable_n": len(positives),
        "absent_n": len(absent),
        "conflict_n": len(conflicts),
        "strict_correct": sum(x["correct_programmatic_label"] for x in rows),
        "strict_accuracy": mean(x["correct_programmatic_label"] for x in rows),
        "answerable_correct": sum(x["correct_programmatic_label"] for x in positives),
        "answerable_exact_accuracy": mean(x["correct_programmatic_label"] for x in positives) if positives else None,
        "absent_correct_refusals": sum(x["correct_programmatic_label"] for x in absent),
        "conflict_correct_refusals": sum(x["correct_programmatic_label"] for x in conflicts),
        "accepted": len(accepted),
        "coverage": len(accepted) / len(rows),
        "wrong_accepts": sum(x["wrong_accept"] for x in rows),
        "accept_error_rate": (
            mean(x["wrong_accept"] for x in accepted) if accepted else None
        ),
        "false_refusals_on_answerable": sum(x["false_refusal"] for x in positives),
        "total_reader_forwards": sum(x["candidate_reader_forwards"] for x in rows),
        "total_model_cpu_forward_ms": sum(x["model_cpu_forward_ms"] for x in rows),
        "total_model_input_tokens": sum(x["model_input_tokens"] for x in rows),
        "nonrefusal_provenance": sum(x["source_exact"] for x in accepted),
        "wrong_entity_source_accepts": sum(
            x["source_document_eligible"] is False for x in accepted
        ),
    }


def gate_prediction(prediction: Prediction, threshold: float) -> Prediction:
    if threshold < 0:
        raise ValueError("Only nonnegative no-answer thresholds are allowed")
    if is_refusal(prediction.text):
        return prediction
    # We only trust an answered prediction if the largest margin beats a
    # frozen CALIBRATION threshold, otherwise refuse (possibly incorrectly).
    if prediction.margin is None or prediction.margin <= threshold:
        return Prediction(
            "INSUFFICIENT_EVIDENCE", None, None, None, prediction.margin,
            prediction.tokens, prediction.cpu_ms, False, prediction.candidates_read
        )
    return prediction


THRESHOLDS = (0.0, 1.0, 2.0, 3.0, 5.0, 8.0, 12.0, 20.0, 30.0, 50.0, math.inf)


def calibrate(
    cases: list[CFCase],
    predictions: list[Prediction],
    *,
    max_wrong_accept_rate: float = 0.15,
    minimum_accepted: int = 5,
) -> dict:
    """Frozen objective. Only CALIBRATION split is legally consumed here.

    A safe solution is to refuse all if no threshold reaches the conditional
    wrong-accept cap on at least minimum_accepted examples.
    """
    if not cases or len(cases) != len(predictions):
        raise ValueError("Missing or misaligned calibration cases")
    if any(c.split != "calibration" for c in cases):
        raise ValueError("CALIBRATION ONLY: never tune thresholds using DEV or audit labels")
    if not (0 <= max_wrong_accept_rate <= 1) or minimum_accepted < 1:
        raise ValueError("Invalid calibration guardrails")
    decisions = []
    for threshold in THRESHOLDS:
        rows = [
            format_outcome(c, gate_prediction(p, threshold))
            for c, p in zip(cases, predictions)
        ]
        score = summarize(rows)
        qualified = (
            score["accepted"] >= minimum_accepted
            and score["accept_error_rate"] is not None
            and score["accept_error_rate"] <= max_wrong_accept_rate
        )
        decisions.append({
            "threshold": threshold, "qualified": qualified,
            "correct_answers": score["answerable_correct"],
            "accepted": score["accepted"],
            "wrong_accepts": score["wrong_accepts"],
            "observed_wrong_accept_rate": score["accept_error_rate"],
        })
    acceptable = [x for x in decisions if x["qualified"]]
    if acceptable:
        # Correct answer utility takes priority, then minimize bad accepts,
        # then permit more answer coverage for equally safe solutions.
        best = max(
            acceptable,
            key=lambda x: (
                x["correct_answers"], -x["wrong_accepts"],
                x["accepted"], x["threshold"]
            ),
        )
        selected = best["threshold"]
        status = "CALIBRATION_CONDITIONAL_RISK_GATE_SELECTED_NOT_CERTIFIED"
    else:
        selected = math.inf
        status = "CALIBRATION_UNSAFE_REFUSE_ALL"
    return {
        "status": status,
        "threshold": None if math.isinf(selected) else selected,
        "refuse_all": math.isinf(selected),
        "objective": {
            "max_wrong_accept_rate": max_wrong_accept_rate,
            "minimum_accepted": minimum_accepted,
            "utility": "maximize correct accepted answerable predictions",
        },
        "candidate_grid": [
            {**x, "threshold": None if math.isinf(x["threshold"]) else x["threshold"]}
            for x in decisions
        ],
        "split": "calibration_only",
    }


def locked_threshold(calibration: dict) -> float:
    if calibration.get("split") != "calibration_only":
        raise ValueError("Threshold must have frozen calibration provenance")
    if calibration["refuse_all"]:
        return math.inf
    value = calibration.get("threshold")
    if value not in THRESHOLDS:
        raise ValueError("Unknown threshold outside registered candidate grid")
    return float(value)


def file_fingerprint(rows: list[dict]) -> str:
    import json
    return sha(json.dumps(rows, sort_keys=True, ensure_ascii=False, separators=(",", ":")))

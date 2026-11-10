"""MICRO-RAG v0.2 human-review evidence gates (no fake certification).

This module scores *supplied* annotations and enforces reviewer/group metadata.
It CANNOT establish that the reviewers are human or independent; final
scientific GO requires external audit and real source documents.
"""
from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any, Sequence

from raglab.micro_v02.pipeline import MicroRAG

STATES = ("ANSWER", "CONFLICT", "INSUFFICIENT", "REVIEW")


def _clean(value: str) -> str:
    return " ".join(value.casefold().strip().split())


def validate_reviewed_records(rows: Sequence[dict]) -> dict[str, Any]:
    if not rows or len(rows) > 10000:
        raise ValueError("Reviewed dataset must contain 1..10,000 records")
    ids: set[str] = set()
    groups: dict[str, str] = {}
    domains: set[str] = set()
    per_split: dict[str, int] = defaultdict(int)
    for record in rows:
        required = ("id", "question", "source_group_id", "domain", "split",
                    "expected_status", "reviewers")
        if any(k not in record for k in required):
            raise ValueError("Reviewed record missing mandatory fields")
        case_id = record["id"]
        group = record["source_group_id"]
        domain = record["domain"]
        split = record["split"]
        status = record["expected_status"]
        if not all(
            isinstance(v, str) and v.strip()
            for v in (case_id, group, domain, split, record["question"])
        ):
            raise ValueError("Nonempty case/source-group/domain/question strings required")
        if case_id in ids:
            raise ValueError("Duplicate review case ID")
        ids.add(case_id)
        if split not in ("calibration", "evaluation"):
            raise ValueError("Only calibration/evaluation split names permitted")
        if status not in STATES:
            raise ValueError("Unknown adjudicated status")
        if status == "ANSWER" and not (
            isinstance(record.get("expected_answer"), str)
            and record["expected_answer"].strip()
        ):
            raise ValueError("Accepted gold answer requires text")
        if group in groups and groups[group] != split:
            raise ValueError("Source-group leakage between calibration and evaluation")
        groups[group] = split
        domains.add(domain)
        per_split[split] += 1

        reviewers = record["reviewers"]
        if not isinstance(reviewers, list) or len(reviewers) < 2:
            raise ValueError("Two independent reviewer records required")
        reviewer_ids: list[str] = []
        decisions: list[tuple[str, str]] = []
        for review in reviewers:
            if not isinstance(review, dict) or not (
                isinstance(review.get("reviewer_id"), str)
                and review["reviewer_id"].strip()
            ):
                raise ValueError("Reviewer provenance ID required")
            if review.get("status") not in STATES:
                raise ValueError("Reviewer status must be from the frozen contract")
            reviewer_ids.append(review["reviewer_id"])
            decisions.append((
                review["status"],
                _clean(str(review.get("answer") or "")) if review["status"] == "ANSWER" else "",
            ))
        if len(set(reviewer_ids)) != len(reviewer_ids):
            raise ValueError("Reviewers must have different provenance identifiers")
        expected_tuple = (
            status,
            _clean(record["expected_answer"]) if status == "ANSWER" else "",
        )
        if len(set(decisions)) == 1:
            if decisions[0] != expected_tuple:
                raise ValueError("Gold label disagrees with unanimous reviewer decisions")
        else:
            if not (record.get("adjudicated_by") and isinstance(
                record["adjudicated_by"], str
            )):
                raise ValueError("Disagreement requires explicit adjudication ID")
            if expected_tuple not in decisions:
                # Third-party adjudicator may be right about a novel label,
                # but requires an explicit narrative audit rather than
                # automatically treating an arbitrary new label as truth.
                if not record.get("adjudication_rationale"):
                    raise ValueError("Novel adjudicated label requires rationale")
    return {
        "n": len(rows),
        "source_groups": len(groups),
        "domains": sorted(domains),
        "split_counts": dict(per_split),
        "warning": (
            "Reviewer IDs and adjudications are user-supplied assertions. "
            "This program cannot attest that people are real, blinded, or independent."
        ),
    }


def _row_scoring(row: dict, status: str, answer: str | None) -> dict:
    expected = row["expected_status"]
    correct = status == expected and (
        expected != "ANSWER"
        or (answer is not None and
            _clean(answer) == _clean(row["expected_answer"]))
    )
    accepted = status == "ANSWER"
    return {
        "id": row["id"],
        "source_group_id": row["source_group_id"],
        "domain": row["domain"],
        "expected_status": expected,
        "observed_status": status,
        "correct": correct,
        "answered": accepted,
        "wrong_accept": accepted and not correct,
        "correct_answerable": expected == "ANSWER" and correct,
        "correct_conflict": expected == "CONFLICT" and status == "CONFLICT",
        "false_conflict_alarm": expected != "CONFLICT" and status == "CONFLICT",
    }


def _metrics(rows: list[dict]) -> dict[str, Any]:
    accepted = [r for r in rows if r["answered"]]
    positive = [r for r in rows if r["expected_status"] == "ANSWER"]
    conflicts = [r for r in rows if r["expected_status"] == "CONFLICT"]
    return {
        "cases": len(rows),
        "accepted": len(accepted),
        "coverage": len(accepted)/len(rows) if rows else 0.0,
        "wrong_accepts": sum(r["wrong_accept"] for r in rows),
        "wrong_accept_rate": (
            mean(r["wrong_accept"] for r in accepted) if accepted else None
        ),
        "correct_answerable": sum(r["correct_answerable"] for r in rows),
        "answerable_n": len(positive),
        "answerable_correct_coverage": (
            sum(r["correct_answerable"] for r in rows)/len(positive)
            if positive else None
        ),
        "conflict_recall": (
            sum(r["correct_conflict"] for r in rows)/len(conflicts)
            if conflicts else None
        ),
        "conflicts_n": len(conflicts),
        "false_conflict_alarms": sum(r["false_conflict_alarm"] for r in rows),
        "strict_correct": sum(r["correct"] for r in rows),
    }


def cluster_bootstrap_risk(
    rows: list[dict], *, repetitions: int = 2000, seed: int = 20261110,
) -> dict:
    if repetitions < 100 or not rows:
        raise ValueError("Bootstrap requires nonempty rows and >=100 resamples")
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        groups[row["source_group_id"]].append(row)
    group_ids = sorted(groups)
    rng = random.Random(seed)
    rates: list[float] = []
    no_accept_draws = 0
    for _ in range(repetitions):
        draw = [r for _ in group_ids for r in groups[rng.choice(group_ids)]]
        risk = _metrics(draw)["wrong_accept_rate"]
        if risk is None:
            no_accept_draws += 1
        else:
            rates.append(risk)
    rates.sort()
    if len(rates) < 0.95 * repetitions:
        upper = None  # Refuse-all cannot be called zero-risk certified.
    else:
        upper = rates[min(
            len(rates)-1, int(0.975*(len(rates)-1))
        )]
    return {
        "source_groups": len(group_ids),
        "repetitions": repetitions,
        "seed": seed,
        "draws_with_zero_accepted": no_accept_draws,
        "wrong_accept_rate_percentile_upper95": upper,
        "method": "source-group resampling; descriptive, not formal safety certification",
    }


def evaluate_reviewed(
    pipeline: MicroRAG,
    reviewed_cases: list[dict],
    *,
    repetitions: int = 2000,
) -> dict[str, Any]:
    metadata = validate_reviewed_records(reviewed_cases)
    # Enforced: calibration records do NOT enter evaluation scoring; this
    # function never chooses policy thresholds, reader models or prompts.
    selected = [r for r in reviewed_cases if r["split"] == "evaluation"]
    if not selected:
        raise ValueError("No evaluation split cases provided")
    evidence = []
    for row in selected:
        response = pipeline.answer(row["question"])
        evidence.append(_row_scoring(row, response.status, response.answer))
    metrics = _metrics(evidence)
    ci = cluster_bootstrap_risk(evidence, repetitions=repetitions)
    enough_cases = len(selected) >= 300
    enough_domains = len({x["domain"] for x in selected}) >= 2
    useful_coverage = (
        metrics["answerable_correct_coverage"] is not None
        and metrics["answerable_correct_coverage"] >= 0.6
    )
    risk = metrics["wrong_accept_rate"]
    upper = ci["wrong_accept_rate_percentile_upper95"]
    observed_targets = bool(
        enough_cases and enough_domains
        and risk is not None and risk <= 0.05
        and upper is not None and upper <= 0.10
        and metrics["conflict_recall"] is not None
        and metrics["conflict_recall"] >= 0.9
        and useful_coverage
    )
    return {
        "status": "HUMAN_REVIEW_PROVENANCE_NOT_INDEPENDENTLY_AUTHENTICATED",
        "scientific_release_approved": False,
        "software_target_checks_met": observed_targets,
        "review_package": metadata,
        "evaluation_only": metrics,
        "group_bootstrap": ci,
        "cases": evidence,
        "requirements": {
            "min_eval_cases": 300,
            "min_eval_domains": 2,
            "wrong_accept_rate_max": 0.05,
            "upper_group_risk_bound_max": 0.10,
            "conflict_recall_min": 0.90,
            "answerable_correct_coverage_min": 0.60,
            "requires_independently_authenticated_human_reviewers": True,
            "requires_untouched_frozen_evaluation": True,
        },
        "limitations": [
            "Reviewer provenance is a claim from the supplied file, not authenticated by software",
            "This does not verify the documents were independently authored, source licensed or blinded",
            "A bootstrap percentile upper bound is descriptive, not a safety guarantee",
            "No automatic scientific GO even if numerical thresholds pass",
            "Calibration cases are excluded and cannot silently tune evaluation",
        ],
    }

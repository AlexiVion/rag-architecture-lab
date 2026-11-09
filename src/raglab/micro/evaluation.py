"""Phase-3 human review aggregation. No automatic citation-as-entailment grading."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any


def _required_bool(value: Any, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be a boolean")
    return value


def assess_human_reviews(
    reviews: Sequence[Mapping[str, Any]],
    *,
    minimum_reviewers: int = 2,
) -> dict:
    """Aggregate independently declared human judgments conservatively.

    Only exact agreement of two distinct named reviewers is included. Source
    support and task correctness are independent of syntactic citation checks.
    Discordant judgments remain open; this function cannot prove that reviewers
    were actually blinded or that labels are scientifically representative.
    """
    if minimum_reviewers < 2:
        raise ValueError("Independent assessment requires at least two reviewers")
    by_item: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in reviews:
        if not isinstance(row, Mapping):
            raise ValueError("Each review must be an object")
        case_id = str(row.get("case_id", "")).strip()
        mode = str(row.get("mode", "")).strip()
        reviewer = str(row.get("reviewer_id", "")).strip()
        if not case_id or not mode or not reviewer:
            raise ValueError("case_id, mode and named reviewer_id are required")
        answerable = _required_bool(row.get("answerable"), "answerable")
        abstained = _required_bool(row.get("abstained"), "abstained")
        correct = row.get("task_correct")
        supported = row.get("source_supported")
        if abstained:
            if correct is not None or supported is not None:
                raise ValueError("Abstained answers must not have correctness/support verdicts")
        else:
            correct = _required_bool(correct, "task_correct")
            supported = _required_bool(supported, "source_supported")
        key = (case_id, mode)
        if any(v["reviewer_id"] == reviewer for v in by_item[key]):
            raise ValueError("Duplicate reviewer for one case/mode")
        by_item[key].append(
            {
                "reviewer_id": reviewer,
                "answerable": answerable,
                "abstained": abstained,
                "task_correct": correct,
                "source_supported": supported,
            }
        )
    if not by_item:
        return {
            "scientific_validation": "NO_EVIDENCE",
            "items_seen": 0,
            "items_with_consensus": 0,
            "items_pending_or_disputed": 0,
            "by_mode": {},
        }

    counters: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "consensus": 0,
            "answerable": 0,
            "answered": 0,
            "supported_correct": 0,
            "unsupported_or_incorrect": 0,
            "false_abstention": 0,
            "correct_abstention": 0,
        }
    )
    disputed: list[dict[str, Any]] = []
    for (case_id, mode), observations in sorted(by_item.items()):
        if len(observations) < minimum_reviewers:
            disputed.append({"case_id": case_id, "mode": mode, "reason": "missing_reviewers"})
            continue
        fields = ("answerable", "abstained", "task_correct", "source_supported")
        signatures = {tuple(r[field] for field in fields) for r in observations}
        if len(signatures) > 1:
            disputed.append({"case_id": case_id, "mode": mode, "reason": "disagreement"})
            continue
        verdict = observations[0]
        count = counters[mode]
        count["consensus"] += 1
        if verdict["answerable"]:
            count["answerable"] += 1
        if verdict["abstained"]:
            if verdict["answerable"]:
                count["false_abstention"] += 1
            else:
                count["correct_abstention"] += 1
        else:
            count["answered"] += 1
            if verdict["task_correct"] and verdict["source_supported"]:
                count["supported_correct"] += 1
            else:
                count["unsupported_or_incorrect"] += 1

    summary: dict[str, dict[str, float | int | None]] = {}
    for mode, counts in sorted(counters.items()):
        answerable, answered = counts["answerable"], counts["answered"]
        summary[mode] = {
            **counts,
            "supported_correct_over_consensus": (
                counts["supported_correct"] / counts["consensus"]
                if counts["consensus"] else None
            ),
            "unsupported_or_incorrect_over_answered": (
                counts["unsupported_or_incorrect"] / answered if answered else None
            ),
            "false_abstention_over_answerable": (
                counts["false_abstention"] / answerable if answerable else None
            ),
        }

    return {
        "schema_version": 1,
        "scientific_validation": "HUMAN_CONSENSUS_ONLY_NOT_HELDOUT_CERTIFIED",
        "independence": "DECLARED_REVIEWER_IDS_NOT_EXTERNALLY_VERIFIED",
        "items_seen": len(by_item),
        "items_with_consensus": sum(v["consensus"] for v in counters.values()),
        "items_pending_or_disputed": len(disputed),
        "pending_or_disputed": disputed,
        "by_mode": summary,
        "limitations": [
            "Human reviewer independence, blindness and ground truth are not verified by code",
            "Only consensus cases are scored; exclusions and denominators are reported",
            "Source support differs from a syntactically valid citation",
            "No holdout generalization, paired confidence interval or world-model claim",
            "No model and no live dataset were run by this evaluator",
        ],
    }

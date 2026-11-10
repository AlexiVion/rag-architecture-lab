"""Matched, source-group bootstrap comparison of two Ragability NLI artifacts.

This compares two already completed public-benchmark runs. It does not train,
tune thresholds, alter model predictions, or treat correlated pairs as
independent. Positive deltas mean model A outperformed model B.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any, Callable


def _metrics(rows: list[dict[str, Any]]) -> dict[str, float]:
    if not rows:
        raise ValueError("Cannot score an empty sample")
    tp = sum(
        row["expected"] == "contradiction"
        and row["symmetric_prediction"] == "contradiction"
        for row in rows
    )
    fn = sum(
        row["expected"] == "contradiction"
        and row["symmetric_prediction"] == "non_contradiction"
        for row in rows
    )
    tn = sum(
        row["expected"] == "non_contradiction"
        and row["symmetric_prediction"] == "non_contradiction"
        for row in rows
    )
    fp = sum(
        row["expected"] == "non_contradiction"
        and row["symmetric_prediction"] == "contradiction"
        for row in rows
    )
    recall_pos = tp / (tp + fn) if tp + fn else 0.0
    recall_neg = tn / (tn + fp) if tn + fp else 0.0
    precision_pos = tp / (tp + fp) if tp + fp else 0.0
    precision_neg = tn / (tn + fn) if tn + fn else 0.0
    f1_pos = (
        2 * precision_pos * recall_pos / (precision_pos + recall_pos)
        if precision_pos + recall_pos else 0.0
    )
    f1_neg = (
        2 * precision_neg * recall_neg / (precision_neg + recall_neg)
        if precision_neg + recall_neg else 0.0
    )
    return {
        "accuracy": (tp + tn) / len(rows),
        "balanced_accuracy": (recall_pos + recall_neg) / 2,
        "macro_f1": (f1_pos + f1_neg) / 2,
        "contradiction_precision": precision_pos,
        "contradiction_recall": recall_pos,
    }


def _percentile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    return ordered[max(0, min(len(ordered) - 1, round(p * (len(ordered) - 1))))]


def _bootstrap_delta(
    rows_a: dict[str, dict[str, Any]],
    rows_b: dict[str, dict[str, Any]],
    groups: dict[str, list[str]],
    *,
    repetitions: int,
    seed: int,
    metric: Callable[[list[dict[str, Any]]], float],
    case_filter: Callable[[dict[str, Any]], bool] | None = None,
) -> dict[str, Any]:
    group_ids = sorted(groups)
    rng = random.Random(seed)
    deltas: list[float] = []
    for _ in range(repetitions):
        draw_groups = [rng.choice(group_ids) for _ in group_ids]
        draw_ids = [
            case_id
            for group_id in draw_groups
            for case_id in groups[group_id]
            if case_filter is None or case_filter(rows_a[case_id])
        ]
        if not draw_ids:
            continue
        value_a = metric([rows_a[case_id] for case_id in draw_ids])
        value_b = metric([rows_b[case_id] for case_id in draw_ids])
        deltas.append(value_a - value_b)
    if len(deltas) != repetitions:
        raise ValueError("Bootstrap unexpectedly produced empty samples")
    return {
        "mean_delta_a_minus_b": mean(deltas),
        "percentile_95_ci": [
            _percentile(deltas, 0.025),
            _percentile(deltas, 0.975),
        ],
        "bootstrap_fraction_a_better": sum(value > 0 for value in deltas) / len(deltas),
        "bootstrap_fraction_tied": sum(value == 0 for value in deltas) / len(deltas),
        "repetitions": repetitions,
        "seed": seed,
        "unit": "matched contradiction_ID source groups",
    }


def _validate_results(result_a: dict[str, Any], result_b: dict[str, Any]):
    for result in (result_a, result_b):
        if result.get("experiment_id") != "MICRO-RAGABILITY-01":
            raise ValueError("Input is not a Ragability NLI experiment result")
        if result.get("dataset", {}).get("row_count") != 53:
            raise ValueError("Unexpected Ragability row count")
        if result.get("dataset", {}).get("unique_conflict_groups") != 43:
            raise ValueError("Unexpected Ragability conflict group count")
    dataset_a = result_a["dataset"]
    dataset_b = result_b["dataset"]
    for field in ("dataset_id", "dataset_revision", "source_sha256"):
        if dataset_a.get(field) != dataset_b.get(field):
            raise ValueError(f"Model results use different dataset {field}")
    rows_a = {
        row["case_id"]: row for row in result_a["evaluation"]["cases"]
    }
    rows_b = {
        row["case_id"]: row for row in result_b["evaluation"]["cases"]
    }
    if len(rows_a) != 318 or set(rows_a) != set(rows_b) or len(rows_b) != 318:
        raise ValueError("Model artifacts do not contain identical 318 pair cases")
    groups: dict[str, list[str]] = defaultdict(list)
    for case_id, row in rows_a.items():
        other = rows_b[case_id]
        if row["expected"] != other["expected"]:
            raise ValueError("Gold labels differ between model artifacts")
        if row["contradiction_id"] != other["contradiction_id"]:
            raise ValueError("Conflict group IDs differ between model artifacts")
        if row["pair_type"] != other["pair_type"]:
            raise ValueError("Pair types differ between model artifacts")
        groups[str(row["contradiction_id"])].append(case_id)
    if len(groups) != 43:
        raise ValueError("Matched comparison requires 43 source-conflict groups")
    return rows_a, rows_b, groups


def compare_results(
    result_a: dict[str, Any],
    result_b: dict[str, Any],
    *,
    repetitions: int = 10000,
    seed: int = 20261109,
) -> dict[str, Any]:
    if repetitions < 1000:
        raise ValueError("At least 1,000 matched bootstrap repetitions required")
    rows_a, rows_b, groups = _validate_results(result_a, result_b)
    cases_a = list(rows_a.values())
    cases_b = list(rows_b.values())
    metric = lambda rows: _metrics(rows)["balanced_accuracy"]
    paired = {}
    for name, fn in (
        ("accuracy", lambda rows: _metrics(rows)["accuracy"]),
        ("balanced_accuracy", lambda rows: _metrics(rows)["balanced_accuracy"]),
        ("macro_f1", lambda rows: _metrics(rows)["macro_f1"]),
    ):
        paired[name] = _bootstrap_delta(
            rows_a, rows_b, groups,
            repetitions=repetitions, seed=seed,
            metric=fn,
        )

    discordance = {
        "a_only_correct": 0,
        "b_only_correct": 0,
        "both_correct": 0,
        "both_wrong": 0,
    }
    for case_id in rows_a:
        correct_a = rows_a[case_id]["expected"] == rows_a[case_id]["symmetric_prediction"]
        correct_b = rows_b[case_id]["expected"] == rows_b[case_id]["symmetric_prediction"]
        if correct_a and correct_b:
            discordance["both_correct"] += 1
        elif correct_a:
            discordance["a_only_correct"] += 1
        elif correct_b:
            discordance["b_only_correct"] += 1
        else:
            discordance["both_wrong"] += 1

    pair_type = {}
    for kind in sorted({row["pair_type"] for row in cases_a}):
        pair_type[kind] = _bootstrap_delta(
            rows_a, rows_b, groups,
            repetitions=repetitions, seed=seed,
            metric=lambda rows: mean(
                row["expected"] == row["symmetric_prediction"] for row in rows
            ),
            case_filter=lambda row, selected=kind: row["pair_type"] == selected,
        )

    reasoning = {}
    reasoning_types = sorted({
        row["reasoning_type"] for row in cases_a if row["pair_type"] == "c1_c2"
    })
    for kind in reasoning_types:
        reasoning[kind] = {
            "a_detection_rate": mean(
                row["symmetric_prediction"] == "contradiction"
                for row in cases_a
                if row["pair_type"] == "c1_c2" and row["reasoning_type"] == kind
            ),
            "b_detection_rate": mean(
                row["symmetric_prediction"] == "contradiction"
                for row in cases_b
                if row["pair_type"] == "c1_c2" and row["reasoning_type"] == kind
            ),
            "n_original_c1_c2_cases": sum(
                row["pair_type"] == "c1_c2" and row["reasoning_type"] == kind
                for row in cases_a
            ),
        }

    name_a = result_a["model"]["id"]
    name_b = result_b["model"]["id"]
    ci = paired["balanced_accuracy"]["percentile_95_ci"]
    conclusion = (
        "A_BETTER_ON_THIS_PUBLIC_BENCHMARK"
        if ci[0] > 0 else
        "B_BETTER_ON_THIS_PUBLIC_BENCHMARK"
        if ci[1] < 0 else
        "NO_CLEAR_WINNER_WITH_GROUP_BOOTSTRAP_INTERVAL"
    )
    return {
        "experiment_id": "MICRO-RAGABILITY-01-PAIRED-COMPARISON",
        "status": "POST_EVALUATION_MATCHED_GROUP_BOOTSTRAP_NO_TUNING",
        "model_a": {
            "id": name_a,
            "revision": result_a["model"]["revision"],
            "parameters": result_a["model"]["parameter_count"],
            "weight_bytes": result_a["model"]["weight_bytes"],
            "cpu_wall_ms": result_a["inference_cost"]["total_batch_wall_ms"],
            "peak_rss_bytes": result_a["environment"]["peak_rss_bytes"],
        },
        "model_b": {
            "id": name_b,
            "revision": result_b["model"]["revision"],
            "parameters": result_b["model"]["parameter_count"],
            "weight_bytes": result_b["model"]["weight_bytes"],
            "cpu_wall_ms": result_b["inference_cost"]["total_batch_wall_ms"],
            "peak_rss_bytes": result_b["environment"]["peak_rss_bytes"],
        },
        "dataset": {
            "id": result_a["dataset"]["dataset_id"],
            "revision": result_a["dataset"]["dataset_revision"],
            "source_sha256": result_a["dataset"]["source_sha256"],
            "pair_cases": len(rows_a),
            "source_conflict_groups": len(groups),
        },
        "point_metrics": {
            "model_a": _metrics(cases_a),
            "model_b": _metrics(cases_b),
        },
        "paired_cluster_bootstrap_deltas": paired,
        "pair_type_bootstrap_deltas": pair_type,
        "original_c1_c2_reasoning_type_detection_rates": reasoning,
        "paired_correctness_discordance": discordance,
        "conclusion": conclusion,
        "interpretation_limits": [
            "The bootstrap resamples 43 conflict_ID groups; the 318 derived pair cases are not independent.",
            "Intervals compare two fixed model artifacts; they do not imply generalization beyond this small public benchmark.",
            "No hyperparameters, thresholds, or prompts were selected on this evaluation.",
            "A bootstrap interval containing zero is not evidence of equivalence.",
            "Model outputs remain uncalibrated and pairwise NLI is not end-to-end RAG.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-a", required=True, help="Model A results.json")
    parser.add_argument("--model-b", required=True, help="Model B results.json")
    parser.add_argument("--output", required=True, help="Output JSON path")
    parser.add_argument("--repetitions", type=int, default=10000)
    args = parser.parse_args()
    result_a = json.loads(Path(args.model_a).read_text(encoding="utf-8"))
    result_b = json.loads(Path(args.model_b).read_text(encoding="utf-8"))
    report = compare_results(
        result_a, result_b, repetitions=args.repetitions
    )
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "conclusion": report["conclusion"],
        "paired_cluster_bootstrap_deltas": report["paired_cluster_bootstrap_deltas"],
        "paired_correctness_discordance": report["paired_correctness_discordance"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()

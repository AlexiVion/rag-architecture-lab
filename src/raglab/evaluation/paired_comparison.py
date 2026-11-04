from __future__ import annotations

import random
import statistics
from collections.abc import Mapping, Sequence
from typing import Any


PRIMARY_METRIC = "recall@5"
SECONDARY_METRICS = ("mrr@10", "ndcg@10", "recall@10")


def _indexed_queries(result: Mapping[str, Any], name: str) -> dict[str, dict]:
    rows = result.get("queries")
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"{name} has no per-query benchmark rows")
    indexed: dict[str, dict] = {}
    for row in rows:
        if not isinstance(row, dict) or "query_id" not in row:
            raise ValueError(f"{name} has a malformed query row")
        query_id = str(row["query_id"])
        if query_id in indexed:
            raise ValueError(f"{name} contains duplicate query id {query_id}")
        indexed[query_id] = row
    return indexed


def _paired_ci(diffs: Sequence[float], *, repeats: int, seed: int) -> tuple[float, float]:
    if repeats < 100:
        raise ValueError("At least 100 bootstrap replicates are required")
    if not diffs:
        raise ValueError("No paired differences to bootstrap")
    rng = random.Random(seed)
    count = len(diffs)
    samples: list[float] = []
    for _ in range(repeats):
        samples.append(
            sum(diffs[rng.randrange(count)] for _ in range(count)) / count
        )
    samples.sort()
    lower = samples[int((repeats - 1) * 0.025)]
    upper = samples[int((repeats - 1) * 0.975)]
    return lower, upper


def analyze_fusion_artifact(
    payload: Mapping[str, Any],
    *,
    bootstrap_replicates: int = 2000,
    seed: int = 42,
) -> dict[str, Any]:
    """Evaluate paired development-set changes, never update model weights.

    Scientific scope: exploratory paired bootstrap confidence intervals of
    query-level deltas. They neither certify causal improvement nor correct
    for trying multiple candidate weights.
    """
    if payload.get("experiment_id") != "RET-FUSION-01":
        raise ValueError("Expected a RET-FUSION-01 artifact")
    if payload.get("dataset") != "beir/scifact/train":
        raise ValueError("Fusion selection is restricted to SciFact train")
    runs = payload.get("results")
    if not isinstance(runs, list) or not runs:
        raise ValueError("Artifact must have benchmark results")
    by_name: dict[str, dict] = {}
    for run in runs:
        if not isinstance(run, dict) or "pipeline" not in run:
            raise ValueError("Malformed benchmark result")
        name = str(run["pipeline"])
        if name in by_name:
            raise ValueError(f"Duplicate pipeline: {name}")
        by_name[name] = run

    baseline = by_name.get("hybrid")
    if baseline is None:
        raise ValueError("Expected original Hybrid RRF baseline named 'hybrid'")
    candidates = {
        name: run for name, run in by_name.items() if name.startswith("hybrid-dense-")
    }
    if not candidates:
        raise ValueError("No weighted hybrid candidates in artifact")

    baseline_rows = _indexed_queries(baseline, "hybrid")
    query_ids = sorted(baseline_rows)
    metrics = (PRIMARY_METRIC, *SECONDARY_METRICS)
    comparisons: list[dict[str, Any]] = []
    for candidate_index, (name, run) in enumerate(candidates.items()):
        candidate_rows = _indexed_queries(run, name)
        if set(candidate_rows) != set(baseline_rows):
            raise ValueError(f"{name} query IDs differ from baseline")
        metrics_report = {}
        query_deltas = []
        for metric_index, metric in enumerate(metrics):
            deltas = []
            for query_id in query_ids:
                left = baseline_rows[query_id]
                right = candidate_rows[query_id]
                if left.get("query") != right.get("query"):
                    raise ValueError(f"{name} has different question text at {query_id}")
                try:
                    a = float(left["metrics"][metric])
                    b = float(right["metrics"][metric])
                except (KeyError, TypeError, ValueError) as exc:
                    raise ValueError(f"Missing {metric} metric at {query_id}") from exc
                if not (-1e100 < a < 1e100 and -1e100 < b < 1e100):
                    raise ValueError("Non-finite paired metric")
                deltas.append(b - a)
                if metric == PRIMARY_METRIC:
                    query_deltas.append(
                        {
                            "query_id": query_id,
                            "query": left["query"],
                            "baseline": a,
                            "candidate": b,
                            "delta": b - a,
                        }
                    )
            lower, upper = _paired_ci(
                deltas,
                repeats=bootstrap_replicates,
                seed=seed + candidate_index * 100 + metric_index,
            )
            metrics_report[metric] = {
                "baseline_mean": statistics.fmean(
                    float(baseline_rows[q]["metrics"][metric]) for q in query_ids
                ),
                "candidate_mean": statistics.fmean(
                    float(candidate_rows[q]["metrics"][metric]) for q in query_ids
                ),
                "delta": statistics.fmean(deltas),
                "ci95": [lower, upper],
                "wins": sum(value > 1e-12 for value in deltas),
                "losses": sum(value < -1e-12 for value in deltas),
                "ties": sum(abs(value) <= 1e-12 for value in deltas),
            }
        query_deltas.sort(key=lambda row: (row["delta"], row["query_id"]))
        comparisons.append(
            {
                "candidate": name,
                "metrics": metrics_report,
                "largest_recall5_regressions": query_deltas[:5],
                "largest_recall5_improvements": list(reversed(query_deltas[-5:])),
            }
        )

    # This is a conservative exploratory rule. Positive CI on train is only
    # a reason to consider a *frozen* held-out evaluation, not to claim a win.
    eligible = [
        item for item in comparisons
        if item["metrics"][PRIMARY_METRIC]["ci95"][0] > 0
    ]
    decision = (
        "consider_frozen_held_out_candidate"
        if eligible else "retain_original_hybrid_for_now"
    )
    return {
        "experiment_id": "RET-FUSION-01",
        "dataset": payload["dataset"],
        "source_git_sha": payload.get("git_sha"),
        "query_count": len(query_ids),
        "primary_metric": PRIMARY_METRIC,
        "secondary_metrics": list(SECONDARY_METRICS),
        "baseline": "hybrid",
        "bootstrap_replicates": bootstrap_replicates,
        "bootstrap_seed": seed,
        "comparisons": comparisons,
        "decision": decision,
        "limitations": [
            "Exploratory 95% paired bootstrap percentile intervals, not significance tests.",
            "Multiple inspected weights/metrics create selection bias; no multiplicity correction.",
            "Training-set findings do not establish generalization to test or other domains.",
            "Ground-truth relevance does not measure generation quality or faithfulness.",
            "No model invocation, re-indexing, or additional retrieval was performed.",
        ],
    }


def to_markdown(report: Mapping[str, Any]) -> str:
    """Make a compact human-readable report from the saved local analysis."""
    lines = [
        "# RET-FUSION-01 — paired train-set analysis",
        "",
        f"Queries: {report['query_count']}. Baseline: original Hybrid RRF.",
        f"Primary metric: {report['primary_metric']}.",
        f"Exploratory decision: **{report['decision']}**.",
        "",
        "| Candidate | Δ Recall@5 | 95% bootstrap interval | Wins | Losses | Ties |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for comparison in report["comparisons"]:
        metric = comparison["metrics"]["recall@5"]
        low, high = metric["ci95"]
        lines.append(
            f"| {comparison['candidate']} | {metric['delta']:+.5f} "
            f"| [{low:+.5f}, {high:+.5f}] | "
            f"{metric['wins']} | {metric['losses']} | {metric['ties']} |"
        )
    lines.extend([
        "",
        "The intervals are exploratory, not adjusted for selecting among multiple weights.",
        "These findings do not establish semantic support or answer quality.",
        "",
        "## Largest per-query Recall@5 regressions",
        "",
    ])
    for comparison in report["comparisons"]:
        lines.append(f"### {comparison['candidate']}")
        for row in comparison["largest_recall5_regressions"]:
            lines.append(
                f"- {row['query_id']}: {row['delta']:+.3f} — "
                f"{row['query'][:120]}"
            )
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in report["limitations"])
    return "\n".join(lines) + "\n"

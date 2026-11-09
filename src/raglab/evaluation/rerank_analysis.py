from __future__ import annotations

import math
import statistics
from collections.abc import Mapping
from typing import Any

from raglab.evaluation.paired_comparison import _indexed_queries, _paired_ci

METRICS = ("recall@5", "mrr@10", "ndcg@10", "recall@10")


def analyze_rerank_artifact(
    payload: Mapping[str, Any],
    *,
    bootstrap_replicates: int = 2000,
    seed: int = 42,
) -> dict[str, Any]:
    """Inspect the two runs of an existing train-only retrieval benchmark.

    This does not use test relevance labels and never calls retrieval/models.
    """
    if payload.get("dataset") != "beir/scifact/train":
        raise ValueError("Rerank development diagnosis requires SciFact train")
    runs = payload.get("results")
    if not isinstance(runs, list):
        raise ValueError("Expected benchmark results list")
    by_name: dict[str, dict] = {}
    for run in runs:
        if not isinstance(run, dict) or not isinstance(run.get("pipeline"), str):
            raise ValueError("Malformed benchmark result")
        name = run["pipeline"]
        if name in by_name:
            raise ValueError(f"Duplicate pipeline {name}")
        by_name[name] = run
    if set(by_name) != {"hybrid", "hybrid-rerank"}:
        raise ValueError("Expected exactly hybrid and hybrid-rerank results")
    baseline, candidate = by_name["hybrid"], by_name["hybrid-rerank"]
    base_rows = _indexed_queries(baseline, "hybrid")
    cand_rows = _indexed_queries(candidate, "hybrid-rerank")
    if set(base_rows) != set(cand_rows):
        raise ValueError("Benchmark query IDs differ between pipelines")
    ids = sorted(base_rows)

    report_metrics: dict[str, dict[str, Any]] = {}
    primary_changes: list[dict[str, Any]] = []
    for metric_index, metric in enumerate(METRICS):
        before_values: list[float] = []
        after_values: list[float] = []
        differences: list[float] = []
        for qid in ids:
            base, cand = base_rows[qid], cand_rows[qid]
            if base.get("query") != cand.get("query"):
                raise ValueError(f"Different query text for {qid}")
            try:
                before = float(base["metrics"][metric])
                after = float(cand["metrics"][metric])
            except (KeyError, ValueError, TypeError) as exc:
                raise ValueError(f"Missing {metric} for query {qid}") from exc
            if not (math.isfinite(before) and math.isfinite(after)):
                raise ValueError(f"Non-finite metric {metric} for {qid}")
            before_values.append(before)
            after_values.append(after)
            differences.append(after - before)
            if metric == "recall@5":
                primary_changes.append({
                    "query_id": qid,
                    "query": base.get("query", ""),
                    "baseline": before,
                    "rerank": after,
                    "delta": after - before,
                    "baseline_top5_ids": [
                        x["doc_id"] for x in base.get("results", [])[:5]
                    ],
                    "rerank_top5_ids": [
                        x["doc_id"] for x in cand.get("results", [])[:5]
                    ],
                })
        ci = _paired_ci(
            differences,
            repeats=bootstrap_replicates,
            seed=seed + metric_index,
        )
        report_metrics[metric] = {
            "baseline_mean": statistics.fmean(before_values),
            "rerank_mean": statistics.fmean(after_values),
            "delta": statistics.fmean(differences),
            "ci95": list(ci),
            "wins": sum(d > 1e-12 for d in differences),
            "losses": sum(d < -1e-12 for d in differences),
            "ties": sum(abs(d) <= 1e-12 for d in differences),
        }

    baseline_ms = float(baseline["latency_ms"]["mean"])
    rerank_ms = float(candidate["latency_ms"]["mean"])
    if not (math.isfinite(baseline_ms) and math.isfinite(rerank_ms)):
        raise ValueError("Non-finite latency")
    if baseline_ms <= 0 or rerank_ms < 0:
        raise ValueError("Invalid latency")
    primary_changes.sort(key=lambda item: (item["delta"], item["query_id"]))
    change = report_metrics["recall@5"]
    decision = (
        "do_not_promote_rerank20_from_this_smoke"
        if change["delta"] <= 0 or rerank_ms > baseline_ms
        else "further_development_evaluation_required"
    )

    return {
        "experiment_id": "RET-RERANK-20",
        "dataset": payload["dataset"],
        "query_count": len(ids),
        "baseline": "hybrid",
        "candidate": "hybrid-rerank",
        "primary_metric_for_existing_context": "recall@5",
        "metrics": report_metrics,
        "latency": {
            "baseline_mean_ms": baseline_ms,
            "rerank_mean_ms": rerank_ms,
            "mean_delta_ms": rerank_ms - baseline_ms,
            "mean_ratio": rerank_ms / baseline_ms,
            "note": "Sequential CPU timings are descriptive, not paired causal benchmarks.",
        },
        "largest_recall5_regressions": primary_changes[:8],
        "largest_recall5_improvements": list(reversed(primary_changes[-8:])),
        "bootstrap_replicates": bootstrap_replicates,
        "bootstrap_seed": seed,
        "decision": decision,
        "limitations": [
            "First 60 training queries are an exploratory convenience subset.",
            "Percentile bootstrap intervals are unadjusted and descriptive.",
            "Model and corpus revisions are not locked in the original artifact.",
            "Cross-encoder uses generic MS MARCO relevance, not a SciFact-specific model.",
            "Only retained top-10 ranked outputs are in the benchmark artifact.",
            "Query-level relevance is not evidence of semantic answer faithfulness.",
            "No indexing, embedding, reranking or generation is performed by this audit.",
        ],
    }


def rerank_report_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# RET-RERANK-20 — offline paired analysis",
        "",
        f"Dataset: {report['dataset']}; paired queries: {report['query_count']}.",
        f"Decision: **{report['decision']}**.",
        "",
        "| Metric | Baseline | Rerank | Difference | Exploratory 95% bootstrap CI | Wins/Losses/Ties |",
        "|---|---:|---:|---:|---|---|",
    ]
    for name, metric in report["metrics"].items():
        lo, hi = metric["ci95"]
        lines.append(
            f"| {name} | {metric['baseline_mean']:.4f} | "
            f"{metric['rerank_mean']:.4f} | {metric['delta']:+.4f} | "
            f"[{lo:+.4f}, {hi:+.4f}] | "
            f"{metric['wins']}/{metric['losses']}/{metric['ties']} |"
        )
    timing = report["latency"]
    lines.extend([
        "",
        f"Mean CPU query-time ratio: {timing['mean_ratio']:.1f}x.",
        "",
        "## Largest Recall@5 regressions",
        "",
    ])
    for item in report["largest_recall5_regressions"]:
        lines.append(
            f"- Query {item['query_id']}: {item['delta']:+.3f}, "
            f"{str(item['query'])[:130]}"
        )
        lines.append(f"  - baseline top 5: {item['baseline_top5_ids']}")
        lines.append(f"  - rerank top 5: {item['rerank_top5_ids']}")
    lines.extend(["", "## Limitations", ""])
    lines.extend("- " + s for s in report["limitations"])
    return "\n".join(lines) + "\n"

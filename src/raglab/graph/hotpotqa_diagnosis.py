"""Noninteractive verification of stored HotpotQA DEV graph retrieval results.

Only aggregate data are exported to the web; this does not rerun models or
promote the graph approach. Question texts and original passages are excluded.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path
from typing import Any

from raglab.graph.hotpotqa_benchmark import DATASET_ID, HOTPOT_SHA256, _bootstrap_ci

METRICS = ("recall@1", "recall@3", "recall@5")
EXPERIMENT = "GRF00-HOTPOTQA-DEV-01"


def audit_saved_run(data: dict[str, Any], raw_hash: str, *, canonical: bool = True) -> dict[str, Any]:
    if (
        data.get("schema_version") != 1
        or data.get("experiment_id") != EXPERIMENT
        or data.get("dataset") != DATASET_ID
        or data.get("dataset_sha256") != HOTPOT_SHA256
        or data.get("split") != "dev/distractor"
        or data.get("graph_built_without_gold_labels") is not True
        or data.get("sample_seed") != 17
    ):
        raise ValueError("Unexpected HotpotQA dataset or protocol provenance")
    rows = data.get("queries")
    if not isinstance(rows, list) or not rows or data.get("sample_count") != len(rows):
        raise ValueError("Missing original per-query records or inconsistent sample size")
    if canonical and len(rows) != 60:
        raise ValueError("Expected the frozen 60-query HotpotQA study")
    ids = [row.get("question_id") for row in rows]
    if any(not isinstance(x, str) or not x for x in ids) or len(ids) != len(set(ids)):
        raise ValueError("Invalid or duplicate query identifiers")
    id_hash = hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()
    if data.get("sample_query_ids_sha256") != id_hash:
        raise ValueError("Query-set fingerprint mismatch")

    subgroups: dict[str, list[dict]] = {
        "paths_present": [], "paths_absent": [], "seeds_present": [], "seeds_absent": [],
    }
    edge_cases = 0
    for row in rows:
        if row.get("question_type") != "bridge" or row.get("candidate_count", 0) < 2:
            raise ValueError("Study contains ineligible query")
        gold = row.get("gold_supporting_document_ids")
        if not isinstance(gold, list) or len(gold) < 2 or len(gold) != len(set(gold)):
            raise ValueError("Invalid multi-document reference labels")
        seeds, paths, edges = (row.get(key) for key in (
            "graph_seed_count", "graph_path_count", "graph_edge_count"
        ))
        if any(type(x) is not int or x < 0 for x in (seeds, paths, edges)):
            raise ValueError("Malformed graph activation counts")
        if paths and not seeds:
            raise ValueError("Graph path without seeded entity")
        subgroups["paths_present" if paths else "paths_absent"].append(row)
        subgroups["seeds_present" if seeds else "seeds_absent"].append(row)
        edge_cases += int(edges > 0)
        if not paths and row.get("baseline_ranked_titles") != row.get("candidate_ranked_titles"):
            raise ValueError("No-path fallback diverged from the BM25 baseline")
        previous_base = previous_graph = -1.0
        for key in METRICS:
            b = row.get("baseline", {}).get(key)
            g = row.get("candidate", {}).get(key)
            if (
                isinstance(b, bool) or isinstance(g, bool)
                or not isinstance(b, (float, int)) or not isinstance(g, (float, int))
                or not math.isfinite(b) or not math.isfinite(g)
                or not (0 <= b <= 1 and 0 <= g <= 1)
            ):
                raise ValueError("Invalid source-level Recall@K")
            if b + 1e-10 < previous_base or g + 1e-10 < previous_graph:
                raise ValueError("Recall is not monotonic by K")
            previous_base, previous_graph = b, g
        for key in ("bm25_index", "graph_index_with_bm25", "bm25_query", "graph_query"):
            value = row.get("timing_ms", {}).get(key)
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise ValueError("Invalid recorded timing")
    if (
        data.get("cases_with_graph_seeds") != len(subgroups["seeds_present"])
        or data.get("cases_with_graph_edges") != edge_cases
    ):
        raise ValueError("Reported graph-activation counts disagree with rows")

    verified: dict[str, dict] = {}
    for k in (1, 3, 5):
        key = f"recall@{k}"
        b = [float(row["baseline"][key]) for row in rows]
        g = [float(row["candidate"][key]) for row in rows]
        deltas = [candidate - base for base, candidate in zip(b, g, strict=True)]
        expected = {
            "bm25": statistics.fmean(b),
            "graph_plus_bm25": statistics.fmean(g),
            "paired_delta": statistics.fmean(deltas),
            "paired_bootstrap_95ci": list(_bootstrap_ci(deltas, seed=17 + k)),
            "wins": sum(x > 0 for x in deltas),
            "losses": sum(x < 0 for x in deltas),
            "ties": sum(x == 0 for x in deltas),
        }
        saved = data.get("metrics", {}).get(key)
        if not isinstance(saved, dict):
            raise ValueError("Missing original aggregate")
        for field, value in expected.items():
            actual = saved.get(field)
            if isinstance(value, list):
                if not isinstance(actual, list) or len(actual) != 2 or any(
                    not math.isclose(float(a), v, abs_tol=1e-9)
                    for a, v in zip(actual, value, strict=True)
                ):
                    raise ValueError(f"Archived {key} confidence interval differs")
            elif isinstance(value, int):
                if actual != value:
                    raise ValueError(f"Archived {key} win/loss/tie count differs")
            elif actual is None or not math.isclose(float(actual), value, abs_tol=1e-9):
                raise ValueError(f"Archived {key} score differs from its rows")
        verified[key] = expected

    def verified_mean(key: str) -> float:
        return statistics.fmean(row["timing_ms"][key] for row in rows)

    for section, mapping in (
        ("mean_query_ms", {"bm25": "bm25_query", "graph_plus_bm25": "graph_query"}),
        ("mean_index_ms", {"bm25": "bm25_index", "graph_plus_bm25": "graph_index_with_bm25"}),
    ):
        for model, field in mapping.items():
            if not math.isclose(
                float(data.get(section, {}).get(model, float("nan"))),
                verified_mean(field), abs_tol=1e-6,
            ):
                raise ValueError("Timing aggregation mismatch")
    groups = {}
    for key, subset in subgroups.items():
        diffs = [
            row["candidate"]["recall@5"] - row["baseline"]["recall@5"]
            for row in subset
        ]
        groups[key] = {
            "cases": len(subset),
            "mean_delta_recall_at_5": statistics.fmean(diffs) if diffs else None,
            "wins": sum(v > 0 for v in diffs),
            "losses": sum(v < 0 for v in diffs),
            "ties": sum(v == 0 for v in diffs),
        }
    decision = (
        "NO_GO_GRAPH_FIRST_ON_THIS_DEV_SUBSET"
        if all(x["paired_bootstrap_95ci"][1] < 0 for x in verified.values())
        else "INCONCLUSIVE_OR_MIXED_RESULTS"
    )
    return {
        "schema_version": 1,
        "kind": "verified_retrieval_benchmark_aggregate",
        "publication_status": "verified_from_local_per_query_records",
        "experiment_id": EXPERIMENT,
        "dataset": DATASET_ID,
        "dataset_license": "CC BY-SA 4.0",
        "dataset_sha256": HOTPOT_SHA256,
        "sample_seed": 17,
        "sample_count": len(rows),
        "sample_query_ids_sha256": id_hash,
        "source_report_sha256": raw_hash,
        "decision": decision,
        "metrics": verified,
        "subgroups": groups,
        "cases_with_graph_edges": edge_cases,
        "mean_query_ms": {
            "bm25": verified_mean("bm25_query"),
            "graph_plus_bm25": verified_mean("graph_query"),
        },
        "limitations": [
            "60-query deterministic DEV bridge subset, not an untouched holdout.",
            "Retrieval among per-question supplied distractor contexts, not full Wikipedia.",
            "Article-title mention edges, not general semantic entity extraction.",
            "No generated answers or scientific faithfulness evaluation.",
            "Graph index timing excludes relation construction before index() was called.",
            "No parameter tuning or default architecture change based on this study.",
            "Web summary includes no HotpotQA question texts or article passages.",
        ],
    }


def render_markdown(summary: dict[str, Any]) -> str:
    rows = [
        "# GRF-00 HotpotQA DEV — verified retrieval experiment",
        "",
        f"Decision: **{summary['decision']}**; 60 DEV bridge questions.",
        "",
        "| Metric | BM25 | Graph+BM25 | Delta | 95% paired CI | W/L/T |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for name, item in summary["metrics"].items():
        lo, hi = item["paired_bootstrap_95ci"]
        rows.append(
            f"| {name} | {item['bm25']:.4f} | {item['graph_plus_bm25']:.4f} | "
            f"{item['paired_delta']:+.4f} | [{lo:+.4f}, {hi:+.4f}] | "
            f"{item['wins']}/{item['losses']}/{item['ties']} |"
        )
    rows += ["", "## Observed path-activation subgroups", ""]
    for name, group in summary["subgroups"].items():
        mean = group["mean_delta_recall_at_5"]
        rows.append(
            f"- {name}: n={group['cases']}; "
            + (f"mean delta@5={mean:+.4f}" if mean is not None else "no examples")
        )
    rows += ["", "## Limitations", ""]
    rows += ["- " + item for item in summary["limitations"]]
    rows += ["", "Source report SHA256: " + summary["source_report_sha256"], ""]
    return "\n".join(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit the saved GRF-00 DEV report and export a web-safe summary")
    parser.add_argument("--input", required=True)
    parser.add_argument("--markdown-output", required=True)
    parser.add_argument("--web-output", required=True)
    args = parser.parse_args()
    raw = Path(args.input).read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    result = audit_saved_run(json.loads(raw), sha)
    outputs = (
        (Path(args.markdown_output), render_markdown(result)),
        (Path(args.web_output), json.dumps(result, ensure_ascii=False, indent=2) + "\n"),
    )
    for output, content in outputs:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content, encoding="utf-8")
    print(f"GRF00_AUDIT_STATUS={result['decision']}")
    print(f"GRF00_REPORT_SHA256={sha}")
    print(f"GRAPH_PATH_PRESENT={result['subgroups']['paths_present']}")
    print(f"GRAPH_PATH_ABSENT={result['subgroups']['paths_absent']}")
    print(f"GRF00_DIAGNOSTIC_MARKDOWN={args.markdown_output}")
    print(f"GRF00_LOCAL_WEB_AGGREGATE={args.web_output}")
    print("No generation or new benchmark run; original report unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

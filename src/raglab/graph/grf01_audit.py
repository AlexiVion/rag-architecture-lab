"""Audit an existing GRF-01 run without rerunning retrieval or loading model weights."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from datetime import UTC, datetime
from pathlib import Path

from raglab.graph.grf01_policy import (
    EMBEDDING_MODEL, EMBEDDING_REVISION, EXPECTED_COHORT_SHA256,
    POLICY, policy_fingerprint,
)
from raglab.graph.grf01_study import EXPERIMENT_ID, TOP_K, aggregate
from raglab.graph.hotpotqa_benchmark import HOTPOT_SHA256, recall_at_k

ARMS = ("bm25", "dense", "hybrid", "graph_hybrid")
TIMINGS = (
    "sparse_index", "dense_index_including_encode",
    "sparse_query", "dense_query_including_encode",
    "graph_construction", "graph_ranking_including_quote_validation",
)


def equal_number(a, b, name):
    if (type(a) not in (int, float) or type(b) not in (int, float)
        or not math.isfinite(a) or not math.isfinite(b)
        or not math.isclose(a, b, rel_tol=0, abs_tol=1e-9)):
        raise ValueError("Invalid or mismatched numeric value: " + name)


def audit(saved, cohort, lock, raw_hash, *, canonical=True):
    ids = cohort.get("reserved_query_ids")
    if (
        cohort.get("status") != "reserved_not_evaluated"
        or cohort.get("cohort_id") != "GRF01-RESERVED-DEV-01"
        or cohort.get("dataset_sha256") != HOTPOT_SHA256
        or cohort.get("overlap_count_with_grf00") != 0
        or not isinstance(ids, list) or len(ids) == 0
        or len(set(ids)) != len(ids)
        or any(type(q) is not str or not q for q in ids)
        or hashlib.sha256("\n".join(ids).encode()).hexdigest()
           != cohort.get("reserved_query_ids_sha256")
        or (canonical and (len(ids) != 60 or
            cohort["reserved_query_ids_sha256"] != EXPECTED_COHORT_SHA256))
    ):
        raise ValueError("Unverified or changed cohort")
    if (
        lock.get("status") != "policy_locked_before_evaluation"
        or lock.get("cohort_query_ids_sha256") != cohort["reserved_query_ids_sha256"]
        or lock.get("policy_sha256") != policy_fingerprint()
        or lock.get("policy") != POLICY
        or lock.get("scores_computed") is not False
        or lock.get("benchmark_run") is not False
    ):
        raise ValueError("Locked policy does not match frozen source")
    if (
        saved.get("experiment_id") != EXPERIMENT_ID
        or saved.get("schema_version") != 1
        or saved.get("status") != "single_pass_on_frozen_disjoint_dev_cohort"
        or saved.get("dataset") != "hotpotqa/distractor/dev_v1"
        or saved.get("dataset_sha256") != HOTPOT_SHA256
        or saved.get("policy_hash") != lock["policy_sha256"]
        or saved.get("cohort_hash") != cohort["reserved_query_ids_sha256"]
        or saved.get("model") != {
            "id": EMBEDDING_MODEL, "revision": EMBEDDING_REVISION,
            "license": "apache-2.0",
        }
        or saved.get("primary_metric") != "graph_hybrid_minus_hybrid_recall@5"
    ):
        raise ValueError("Archived study provenance does not match frozen inputs")
    cases = saved.get("cases")
    if (not isinstance(cases, list) or len(cases) != len(ids)
        or saved.get("sample_count") != len(ids)
        or [c.get("question_id") for c in cases] != ids):
        raise ValueError("Archived run is not the reserved query cohort")
    for case in cases:
        n = case.get("candidate_count")
        gold = case.get("gold_document_ids")
        ranking = case.get("ranked_original_doc_ids")
        recalls = case.get("recall")
        both = case.get("both_gold_in_top5")
        if (type(n) is not int or not 2 <= n <= 10 or not isinstance(gold, list)
            or len(gold) < 2 or len(gold) != len(set(gold))
            or not isinstance(ranking, dict) or not isinstance(recalls, dict)
            or not isinstance(both, dict)):
            raise ValueError("Malformed per-query retrieval provenance")
        available = {f"paragraph-{i:02d}" for i in range(n)}
        gold_set = set(gold)
        if not gold_set.issubset(available):
            raise ValueError("Gold documents do not exist in candidate set")
        for arm in ARMS:
            ranked = ranking.get(arm)
            if (not isinstance(ranked, list) or len(ranked) != min(n, 5)
                or len(set(ranked)) != len(ranked)
                or not set(ranked).issubset(available)):
                raise ValueError("Wrong or duplicated ranked source IDs in " + arm)
            for k in TOP_K:
                equal_number(
                    recalls.get(arm, {}).get(f"recall@{k}"),
                    recall_at_k(ranked, gold_set, k),
                    arm + " recall@" + str(k),
                )
            if both.get(arm) is not gold_set.issubset(set(ranked[:5])):
                raise ValueError("Both-source-hit flag differs from rankings")
        trace = case.get("graph_trace")
        if not isinstance(trace, dict) or not isinstance(trace.get("paths"), list):
            raise ValueError("Graph trace missing")
        paths = trace["paths"]
        if (
            trace.get("policy_id") != POLICY["policy_id"]
            or trace.get("policy_sha256") != policy_fingerprint()
            or trace.get("gold_labels_used") is not False
            or trace.get("semantic_support_verified") is not False
            or trace.get("graph_activated") is not bool(paths)
            or case.get("graph_activated") is not bool(paths)
            or case.get("graph_path_count") != len(paths)
            or trace.get("baseline_document_ids") != ranking["hybrid"]
            or trace.get("candidate_document_ids") != ranking["graph_hybrid"]
        ):
            raise ValueError("Graph trace does not match archived rankings")
        if not paths and ranking["hybrid"] != ranking["graph_hybrid"]:
            raise ValueError("No-path graph fallback changed Hybrid baseline")
        for path in paths:
            hops = path.get("hop_count")
            if (type(hops) is not int or not 1 <= hops <= 2
                or len(path.get("edge_ids", [])) != hops
                or len(path.get("node_ids", [])) != hops + 1
                or not set(path.get("source_document_ids", [])).issubset(available)):
                raise ValueError("Invalid source-provenance path")
        if type(case.get("graph_edge_count")) is not int or case["graph_edge_count"] < 0:
            raise ValueError("Invalid graph edge count")
        for field in TIMINGS:
            t = case.get("timing_ms", {}).get(field)
            if type(t) not in (int, float) or not math.isfinite(t) or t < 0:
                raise ValueError("Invalid timing field " + field)
        rss = case.get("observed_rss_mb")
        if rss is not None and (type(rss) not in (int, float) or not math.isfinite(rss) or rss < 0):
            raise ValueError("Invalid sampled resident memory")

    calculated = aggregate(cases, lock=lock)
    for key in ("decision", "graph_activation_count", "both_support_docs_at_5", "sample_count", "primary_metric"):
        if saved.get(key) != calculated[key]:
            raise ValueError("Archived aggregate mismatch: " + key)
    for name, expected in calculated["metrics"].items():
        old = saved.get("metrics", {}).get(name)
        if not isinstance(old, dict):
            raise ValueError("Archived metric missing: " + name)
        for field in (*ARMS, "graph_hybrid_minus_hybrid_delta"):
            equal_number(old.get(field), expected[field], name + "." + field)
        ci = old.get("paired_bootstrap_95ci")
        if not isinstance(ci, list) or len(ci) != 2:
            raise ValueError("Archived confidence interval is malformed")
        for a, b in zip(ci, expected["paired_bootstrap_95ci"], strict=True):
            equal_number(a, b, name + " confidence interval")
        for field in ("wins", "losses", "ties"):
            if type(old.get(field)) is not int or old[field] != expected[field]:
                raise ValueError("Archived paired win/loss/tie count mismatch")
    for field, expected in calculated["timing"].items():
        old = saved.get("timing", {}).get(field)
        if not isinstance(old, dict):
            raise ValueError("Archived measured CPU timing missing")
        for key in ("mean_ms", "p95_ms"):
            equal_number(old.get(key), expected[key], field + "." + key)
    if (saved.get("peak_sampled_process_rss_mb") is None) != (
        calculated["peak_sampled_process_rss_mb"] is None
    ):
        raise ValueError("Memory presence mismatch")
    if calculated["peak_sampled_process_rss_mb"] is not None:
        equal_number(saved["peak_sampled_process_rss_mb"],
                     calculated["peak_sampled_process_rss_mb"], "peak sampled RSS")
    groups = {}
    for name, selected in (
        ("path_activated", [row for row in cases if row["graph_activated"]]),
        ("no_path", [row for row in cases if not row["graph_activated"]]),
    ):
        delta = [row["recall"]["graph_hybrid"]["recall@5"]
                 - row["recall"]["hybrid"]["recall@5"] for row in selected]
        groups[name] = {
            "cases": len(selected),
            "mean_delta_recall_at_5": statistics.fmean(delta) if delta else None,
            "wins": sum(d > 0 for d in delta),
            "losses": sum(d < 0 for d in delta),
            "ties": sum(d == 0 for d in delta),
        }
    if groups["no_path"]["wins"] or groups["no_path"]["losses"]:
        raise ValueError("No-path identity invariant broken")
    return {
        "schema_version": 1,
        "kind": "verified_grf01_retrieval_aggregate",
        "publication_status": "audited_local_existing_run",
        "experiment_id": EXPERIMENT_ID,
        "source_report_sha256": raw_hash,
        "dataset": saved["dataset"],
        "dataset_license": "CC BY-SA 4.0",
        "sample_count": len(cases),
        "model_id": EMBEDDING_MODEL,
        "model_revision": EMBEDDING_REVISION,
        "policy_sha256": lock["policy_sha256"],
        "cohort_sha256": cohort["reserved_query_ids_sha256"],
        "decision": calculated["decision"],
        "metrics": calculated["metrics"],
        "subgroups": groups,
        "graph_activation_count": calculated["graph_activation_count"],
        "both_support_docs_at_5": calculated["both_support_docs_at_5"],
        "timing": calculated["timing"],
        "peak_sampled_process_rss_mb": calculated["peak_sampled_process_rss_mb"],
        "limitations": [
            "Disjoint but already-explored DEV split, not an untouched independent dataset.",
            "Per-question distractor retrieval, not full Wikipedia or generated answers.",
            "Lexical title graph is not general semantic GraphRAG.",
            "Only archived source rankings and metrics reaudited; model weights not rerun.",
            "No original HotpotQA passages exported to web aggregate.",
        ],
    }


def markdown(result):
    out = [
        "# GRF-01 — audited saved HotpotQA DEV run",
        "",
        "Decision: " + result["decision"],
        "Source report SHA256: " + result["source_report_sha256"],
        "",
        "| Metric | BM25 | Dense | Hybrid | Graph-Hybrid | Delta | Bootstrap CI95 | W/L/T |",
        "|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for name, values in result["metrics"].items():
        lo, hi = values["paired_bootstrap_95ci"]
        out.append(
            f"| {name} | {values['bm25']:.4f} | {values['dense']:.4f} | "
            f"{values['hybrid']:.4f} | {values['graph_hybrid']:.4f} | "
            f"{values['graph_hybrid_minus_hybrid_delta']:+.4f} | "
            f"[{lo:+.4f}, {hi:+.4f}] | "
            f"{values['wins']}/{values['losses']}/{values['ties']} |"
        )
    out += ["", "## Graph activity", ""]
    for name, group in result["subgroups"].items():
        delta = group["mean_delta_recall_at_5"]
        value = f"{delta:+.4f}" if delta is not None else "n/a"
        out.append(f"- {name}: n={group['cases']}, delta@5={value}, "
                   f"W/L/T={group['wins']}/{group['losses']}/{group['ties']}")
    out += ["", "## Limitations", ""]
    out += ["- " + item for item in result["limitations"]]
    return "\n".join(out) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Audit GRF-01 saved results; zero model calls.")
    parser.add_argument("--study", default="runs/graph-hybrid/GRF01_FROZEN_EVALUATION.json")
    parser.add_argument("--cohort", default="runs/graph-hybrid/GRF01_RESERVED_DEV_COHORT.json")
    parser.add_argument("--lock", default="runs/graph-hybrid/GRF01_POLICY_LOCK.json")
    parser.add_argument("--output-dir", default="runs/graph-hybrid")
    parser.add_argument("--web-output", default="apps/explorer/data/grf01-summary.local.json")
    args = parser.parse_args()
    raw = Path(args.study).read_bytes()
    summary = audit(
        json.loads(raw),
        json.loads(Path(args.cohort).read_text(encoding="utf-8")),
        json.loads(Path(args.lock).read_text(encoding="utf-8")),
        hashlib.sha256(raw).hexdigest(),
    )
    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    report_path = outdir / f"GRF01_AUDITED_{stamp}.md"
    web_path = Path(args.web_output)
    if web_path.exists():
        raise FileExistsError("Already audited to local web file; refusing overwrite")
    with report_path.open("x", encoding="utf-8") as output:
        output.write(markdown(summary))
    web_path.parent.mkdir(parents=True, exist_ok=True)
    with web_path.open("x", encoding="utf-8") as output:
        json.dump(summary, output, indent=2, ensure_ascii=False)
        output.write("\n")
    print("GRF01_SAVED_RUN_AUDIT_PASS")
    print("GRF01_REPORT_SHA256=" + summary["source_report_sha256"])
    print("GRF01_DECISION=" + summary["decision"])
    for name, item in summary["metrics"].items():
        print(f"{name}: Hybrid={item['hybrid']:.4f} Graph-Hybrid={item['graph_hybrid']:.4f} "
              f"delta={item['graph_hybrid_minus_hybrid_delta']:+.4f} "
              f"CI95={item['paired_bootstrap_95ci']}")
    for name, item in summary["subgroups"].items():
        print("GROUP " + name + "=" + str(item))
    print("GRF01_LOCAL_AUDIT_REPORT=" + str(report_path))
    print("GRF01_LOCAL_WEB_AGGREGATE=" + str(web_path))
    print("No model, new retrieval execution, tuning or generation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

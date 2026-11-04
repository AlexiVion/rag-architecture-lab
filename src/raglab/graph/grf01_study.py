"""GRF-01 sealed one-pass paired HotpotQA DEV study.

The graph policy and 60-query cohort were both frozen BEFORE running this
evaluator. No tuning, no generation, no test split and no external API.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from raglab.core import Document
from raglab.graph.grf01_cohort import COHORT_SCHEMA, HOTPOT_SHA256
from raglab.graph.grf01_policy import (
    EMBEDDING_MODEL,
    EMBEDDING_REVISION,
    EXPECTED_COHORT_SHA256,
    POLICY,
    PinnedMiniLMEmbeddings,
    lock_policy_manifest,
    paired_rankings,
    policy_fingerprint,
)
from raglab.graph.hotpotqa_benchmark import (
    cached_hotpotqa,
    derive_title_link_graph,
    recall_at_k,
    _bootstrap_ci,
)
from raglab.retrieval import BM25Retriever, DenseRetriever

EXPERIMENT_ID = "GRF01-HOTPOTQA-DEV-01"
TOP_K = (1, 3, 5)


def _hash_ids(ids: list[str]) -> str:
    return hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()


def load_locked_inputs(
    *,
    cohort_file: Path,
    lock_file: Path,
    dataset_cache: Path,
) -> tuple[list[dict], dict]:
    """Fail before loading model weights if any frozen input was changed."""
    cohort = json.loads(cohort_file.read_text(encoding="utf-8"))
    lock = json.loads(lock_file.read_text(encoding="utf-8"))
    ids = cohort.get("reserved_query_ids")
    if not isinstance(ids, list) or len(ids) != 60 or len(set(ids)) != 60:
        raise ValueError("Unexpected reserved evaluation cohort")
    if (
        cohort.get("cohort_id") != COHORT_SCHEMA
        or cohort.get("status") != "reserved_not_evaluated"
        or cohort.get("dataset_sha256") != HOTPOT_SHA256
        or cohort.get("reserved_query_ids_sha256") != EXPECTED_COHORT_SHA256
        or _hash_ids(ids) != EXPECTED_COHORT_SHA256
        or lock.get("status") != "policy_locked_before_evaluation"
        or lock.get("cohort_query_ids_sha256") != EXPECTED_COHORT_SHA256
        or lock.get("policy_sha256") != policy_fingerprint()
        or lock.get("policy") != POLICY
        or lock.get("scores_computed") is not False
        or lock.get("benchmark_run") is not False
    ):
        raise ValueError("Cohort or policy manifest differs from frozen contract")
    # Confirm the locked-policy content exactly, including idempotent formatting.
    lock_policy_manifest(cohort_file, lock_file)
    source = cached_hotpotqa(dataset_cache)
    items = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(items, list):
        raise ValueError("HotpotQA DEV cache must contain an array")
    selected = set(ids)
    lookup = {}
    for row in items:
        if isinstance(row, dict) and row.get("_id") in selected:
            qid = row["_id"]
            if qid in lookup:
                raise ValueError("Duplicate reserved question in original dataset")
            if row.get("type") != "bridge":
                raise ValueError("Reserved question is no longer a bridge item")
            lookup[qid] = row
    if set(lookup) != selected:
        raise ValueError("Original source is missing reserved query IDs")
    # Preserve the reserved ranking order, rather than original archive order.
    return [lookup[qid] for qid in ids], lock


def _unlabelled_documents(record: dict) -> list[Document]:
    """Only query context; no answer/supporting facts are passed to retrievers."""
    context = record.get("context")
    if not isinstance(context, list) or not 2 <= len(context) <= 10:
        raise ValueError("Expected 2–10 HotpotQA distractor documents")
    documents = []
    for i, part in enumerate(context):
        if (not isinstance(part, list) or len(part) != 2
            or not isinstance(part[0], str) or not part[0].strip()
            or not isinstance(part[1], list)
            or not all(isinstance(sentence, str) for sentence in part[1])):
            raise ValueError("Invalid distractor document format")
        documents.append(
            Document(f"paragraph-{i:02d}", " ".join(part[1]), part[0])
        )
    if len({doc.title.casefold() for doc in documents}) != len(documents):
        raise ValueError("Duplicate article titles in distractor set")
    return documents


def _gold_after_ranking(record: dict, docs: list[Document]) -> set[str]:
    """Gold supporting facts are available only in the evaluator after ranking."""
    source_titles = {doc.title: doc.id for doc in docs}
    facts = record.get("supporting_facts")
    if not isinstance(facts, list):
        raise ValueError("Missing HotpotQA expert relevance labels")
    gold = set()
    for fact in facts:
        if not isinstance(fact, list) or len(fact) != 2:
            raise ValueError("Malformed supporting fact")
        if fact[0] not in source_titles:
            raise ValueError("Gold supporting document missing from candidate set")
        gold.add(source_titles[fact[0]])
    if len(gold) < 2:
        raise ValueError("Expected at least two supporting documents")
    return gold


def _observed_rss_mb() -> float | None:
    try:
        import psutil
    except ImportError:
        return None
    return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)


def run_one_case(record: dict, *, embeddings: Any) -> dict:
    """Shared sparse/dense lists; graph construction and retrieval timed apart."""
    question = record.get("question")
    if not isinstance(question, str) or not question.strip():
        raise ValueError("Missing question")
    docs = _unlabelled_documents(record)
    sparse = BM25Retriever()
    dense = DenseRetriever(embeddings)
    start = time.perf_counter()
    sparse.index(docs)
    sparse_index_ms = (time.perf_counter() - start) * 1000
    start = time.perf_counter()
    dense.index(docs)
    dense_index_ms = (time.perf_counter() - start) * 1000
    start = time.perf_counter()
    sparse_list = sparse.retrieve(question, len(docs))
    sparse_query_ms = (time.perf_counter() - start) * 1000
    start = time.perf_counter()
    dense_list = dense.retrieve(question, len(docs))
    dense_query_ms = (time.perf_counter() - start) * 1000
    start = time.perf_counter()
    nodes, edges = derive_title_link_graph(docs)
    graph_build_ms = (time.perf_counter() - start) * 1000
    start = time.perf_counter()
    paired = paired_rankings(
        question, docs, dense_list, sparse_list, nodes=nodes, edges=edges,
        k=min(5, len(docs)),
    )
    graph_ranking_ms = (time.perf_counter() - start) * 1000
    # At K>5, use complete ranking from the original sparse and dense calls.
    # Our frozen experiment has primary @5 and secondary @1/@3.
    baseline_ids = [r.doc_id for r in paired.hybrid]
    candidate_ids = [r.doc_id for r in paired.graph_hybrid]
    sparse_ids = [r.doc_id for r in sparse_list]
    dense_ids = [r.doc_id for r in dense_list]
    gold = _gold_after_ranking(record, docs)
    return {
        "question_id": record["_id"],
        "candidate_count": len(docs),
        "gold_document_ids": sorted(gold),
        "graph_edge_count": len(edges),
        "graph_path_count": len(paired.trace["paths"]),
        "graph_activated": paired.trace["graph_activated"],
        "graph_trace": paired.trace,
        "ranked_original_doc_ids": {
            "bm25": sparse_ids[:5],
            "dense": dense_ids[:5],
            "hybrid": baseline_ids,
            "graph_hybrid": candidate_ids,
        },
        "recall": {
            name: {
                f"recall@{k}": recall_at_k(ids, gold, k)
                for k in TOP_K
            }
            for name, ids in (
                ("bm25", sparse_ids),
                ("dense", dense_ids),
                ("hybrid", baseline_ids),
                ("graph_hybrid", candidate_ids),
            )
        },
        "both_gold_in_top5": {
            name: gold.issubset(set(ids[:5]))
            for name, ids in (
                ("bm25", sparse_ids),
                ("dense", dense_ids),
                ("hybrid", baseline_ids),
                ("graph_hybrid", candidate_ids),
            )
        },
        "timing_ms": {
            "sparse_index": sparse_index_ms,
            "dense_index_including_encode": dense_index_ms,
            "sparse_query": sparse_query_ms,
            "dense_query_including_encode": dense_query_ms,
            "graph_construction": graph_build_ms,
            "graph_ranking_including_quote_validation": graph_ranking_ms,
        },
        "observed_rss_mb": _observed_rss_mb(),
    }


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(percentile * len(ordered)) - 1))
    return ordered[index]


def aggregate(rows: list[dict], *, lock: dict) -> dict:
    if not rows:
        raise ValueError("No evaluation rows")
    summaries = {}
    for k in TOP_K:
        key = f"recall@{k}"
        values = {
            arm: [item["recall"][arm][key] for item in rows]
            for arm in ("bm25", "dense", "hybrid", "graph_hybrid")
        }
        differences = [
            candidate - baseline
            for candidate, baseline in zip(
                values["graph_hybrid"], values["hybrid"], strict=True
            )
        ]
        summaries[key] = {
            **{arm: statistics.fmean(v) for arm, v in values.items()},
            "graph_hybrid_minus_hybrid_delta": statistics.fmean(differences),
            "paired_bootstrap_95ci": list(
                _bootstrap_ci(differences, seed=217 + k)
            ),
            "wins": sum(x > 0 for x in differences),
            "losses": sum(x < 0 for x in differences),
            "ties": sum(x == 0 for x in differences),
        }
    primary = summaries["recall@5"]
    ci = primary["paired_bootstrap_95ci"]
    decision = (
        "NO_GO_PRIMARY_RECALL_BELOW_BASELINE" if ci[1] < 0
        else "PRIMARY_POSITIVE_PENDING_COST_AND_PROVENANCE_REVIEW" if ci[0] > 0
        else "INCONCLUSIVE_NO_AUTOMATIC_PROMOTION"
    )
    times = {}
    for key in rows[0]["timing_ms"]:
        values = [float(item["timing_ms"][key]) for item in rows]
        times[key] = {
            "mean_ms": statistics.fmean(values),
            "p95_ms": _percentile(values, 0.95),
        }
    memory_samples = [row["observed_rss_mb"] for row in rows
                      if row["observed_rss_mb"] is not None]
    return {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "status": "single_pass_on_frozen_disjoint_dev_cohort",
        "dataset": "hotpotqa/distractor/dev_v1",
        "dataset_sha256": HOTPOT_SHA256,
        "source_license": "CC BY-SA 4.0",
        "model": {
            "id": EMBEDDING_MODEL,
            "revision": EMBEDDING_REVISION,
            "license": "apache-2.0",
        },
        "cohort_hash": EXPECTED_COHORT_SHA256,
        "policy_hash": lock["policy_sha256"],
        "sample_count": len(rows),
        "primary_metric": "graph_hybrid_minus_hybrid_recall@5",
        "decision": decision,
        "metrics": summaries,
        "graph_activation_count": sum(r["graph_activated"] for r in rows),
        "both_support_docs_at_5": {
            arm: sum(int(r["both_gold_in_top5"][arm]) for r in rows)
            for arm in ("bm25", "dense", "hybrid", "graph_hybrid")
        },
        "timing": times,
        "peak_sampled_process_rss_mb": (
            max(memory_samples) if memory_samples else None
        ),
        "memory_measurement_note": (
            "Sampled RSS after each case when psutil is installed; not a precise "
            "instantaneous peak. Null when psutil is unavailable."
        ),
        "limitations": [
            "Disjoint HotpotQA DEV subset, not a genuinely untouched dataset.",
            "Per-question distractor ranking, not full Wikipedia.",
            "Title mention graph is lexical, not a learned knowledge graph.",
            "Retrieval only; no answer correctness, citations or semantic support measured.",
            "Pinned local model and same BM25/Dense lists; no parameter search.",
            "Graph indexing/building and query retrieval tracked, but sequential CPU "
            "timings are not production performance guarantees.",
            "A positive paired CI is not sufficient to auto-deploy: resource and "
            "provenance release gates must be reviewed separately.",
            "Original CC BY-SA texts and per-query outputs stay in gitignored local runs.",
        ],
        "cases": rows,
    }


def format_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# GRF-01: Frozen Hybrid RRF vs graph-assisted ranking",
        "",
        f"Decision: **{report['decision']}**",
        f"Model revision: {report['model']['revision']}",
        f"Cohort hash: {report['cohort_hash']}",
        "",
        "| Metric | BM25 | Dense | Hybrid | Graph-Hybrid | Graph−Hybrid | 95% CI |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for key, metric in report["metrics"].items():
        lo, hi = metric["paired_bootstrap_95ci"]
        lines.append(
            f"| {key} | {metric['bm25']:.4f} | {metric['dense']:.4f} | "
            f"{metric['hybrid']:.4f} | {metric['graph_hybrid']:.4f} | "
            f"{metric['graph_hybrid_minus_hybrid_delta']:+.4f} | "
            f"[{lo:+.4f}, {hi:+.4f}] |"
        )
    lines += [
        "",
        f"Graph-active queries: {report['graph_activation_count']} / {report['sample_count']}",
        "",
        "## Known limitations",
        "",
    ]
    lines += ["- " + item for item in report["limitations"]]
    return "\n".join(lines) + "\n"


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(
        description="One-pass frozen GRF-01 retrieval study (no answer generation)"
    )
    parser.add_argument(
        "--cohort", default="runs/graph-hybrid/GRF01_RESERVED_DEV_COHORT.json"
    )
    parser.add_argument(
        "--policy-lock", default="runs/graph-hybrid/GRF01_POLICY_LOCK.json"
    )
    parser.add_argument(
        "--cache", default=".cache/hotpotqa/hotpot_dev_distractor_v1.json"
    )
    parser.add_argument(
        "--output-dir", default="runs/graph-hybrid"
    )
    args = parser.parse_args()
    destination = Path(args.output_dir)
    json_file = destination / "GRF01_FROZEN_EVALUATION.json"
    md_file = destination / "GRF01_FROZEN_EVALUATION.md"
    if json_file.exists() or md_file.exists():
        raise FileExistsError("GRF-01 already evaluated; will not overwrite or rerun")
    records, lock = load_locked_inputs(
        cohort_file=Path(args.cohort),
        lock_file=Path(args.policy_lock),
        dataset_cache=Path(args.cache),
    )
    print("=== GRF-01 SEALED ONE-PASS EVALUATION ===")
    print("Model " + EMBEDDING_MODEL + " at " + EMBEDDING_REVISION)
    print("Loading pinned public CPU embedding model; first run may download weights.")
    embeddings = PinnedMiniLMEmbeddings()
    rows = []
    for index, record in enumerate(records, start=1):
        rows.append(run_one_case(record, embeddings=embeddings))
        if index % 10 == 0:
            print(f"GRF01_PROGRESS={index}/60")
    report = aggregate(rows, lock=lock)
    report["run_finished_utc"] = datetime.now(UTC).isoformat()
    destination.mkdir(parents=True, exist_ok=True)
    with json_file.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False)
    with md_file.open("x", encoding="utf-8") as stream:
        stream.write(format_markdown(report))
    print("GRF01_DECISION=" + report["decision"])
    for metric, scores in report["metrics"].items():
        print(
            metric + ": hybrid=" + str(round(scores["hybrid"], 4)) +
            " graph_hybrid=" + str(round(scores["graph_hybrid"], 4)) +
            " delta=" + str(round(scores["graph_hybrid_minus_hybrid_delta"], 4))
        )
    print("GRF01_RESULT_JSON=" + str(json_file))
    print("GRF01_RESULT_MARKDOWN=" + str(md_file))
    print("GRF01_FROZEN_EVALUATION_FINISHED")
    print("No search over weights, no paid model, no held-out TEST data.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

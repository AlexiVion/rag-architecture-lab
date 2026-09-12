from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path

from raglab.datasets import load_ir_dataset
from raglab.embeddings import SentenceTransformerEmbeddings
from raglab.evaluation.benchmark import run_benchmark
from raglab.retrieval import (
    BM25Retriever,
    CrossEncoderScorer,
    DenseRetriever,
    HybridRetriever,
    RerankingRetriever,
)

DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
PIPELINES = [
    "bm25",
    "dense",
    "hybrid",
    "bm25-rerank",
    "dense-rerank",
    "hybrid-rerank",
]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="raglab", description="RAG Architecture Lab CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    benchmark = subparsers.add_parser("benchmark", help="Run retrieval benchmarks")
    benchmark.add_argument("--dataset", default="nano-beir/scifact")
    benchmark.add_argument(
        "--pipelines",
        nargs="+",
        choices=PIPELINES,
        default=["bm25", "dense", "hybrid"],
    )
    benchmark.add_argument("--k", nargs="+", type=int, default=[5, 10])
    benchmark.add_argument("--limit-queries", type=int, default=None)
    benchmark.add_argument("--embedding-model", default=DEFAULT_EMBEDDING_MODEL)
    benchmark.add_argument("--rerank-model", default=DEFAULT_RERANK_MODEL)
    benchmark.add_argument("--bm25-k1", type=float, default=1.5)
    benchmark.add_argument("--bm25-b", type=float, default=0.75)
    benchmark.add_argument("--hybrid-candidates", type=int, default=100)
    benchmark.add_argument("--rrf-constant", type=int, default=60)
    benchmark.add_argument("--rerank-candidates", type=int, default=50)
    benchmark.add_argument("--output-dir", default="benchmarks/results")
    return parser


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_")


def _print_summary(results: list[dict]) -> None:
    metric_names = sorted(results[0]["metrics"].keys())
    headers = ["pipeline", *metric_names, "mean_ms", "p95_ms"]
    rows: list[list[str]] = []
    for result in results:
        rows.append(
            [
                result["pipeline"],
                *[f'{result["metrics"][name]:.4f}' for name in metric_names],
                f'{result["latency_ms"]["mean"]:.2f}',
                f'{result["latency_ms"]["p95"]:.2f}',
            ]
        )

    widths = [max(len(headers[i]), *(len(row[i]) for row in rows)) for i in range(len(headers))]
    print("  ".join(header.ljust(widths[i]) for i, header in enumerate(headers)))
    print("  ".join("-" * width for width in widths))
    for row in rows:
        print("  ".join(value.ljust(widths[i]) for i, value in enumerate(row)))


def _benchmark(args: argparse.Namespace) -> int:
    dataset = load_ir_dataset(args.dataset, limit_queries=args.limit_queries)
    requested = list(dict.fromkeys(args.pipelines))

    bm25 = BM25Retriever(k1=args.bm25_k1, b=args.bm25_b)
    dense_pipeline_names = {"dense", "hybrid", "dense-rerank", "hybrid-rerank"}
    needs_dense = any(pipeline in dense_pipeline_names for pipeline in requested)
    dense = None
    if needs_dense:
        embeddings = SentenceTransformerEmbeddings(args.embedding_model)
        dense = DenseRetriever(embeddings)

    hybrid = (
        HybridRetriever(
            dense=dense,
            sparse=bm25,
            candidate_k=args.hybrid_candidates,
            rrf_constant=args.rrf_constant,
        )
        if dense is not None
        else None
    )

    needs_reranker = any(pipeline.endswith("-rerank") for pipeline in requested)
    scorer = CrossEncoderScorer(args.rerank_model) if needs_reranker else None

    retrievers = {
        "bm25": bm25,
        "dense": dense,
        "hybrid": hybrid,
        "bm25-rerank": RerankingRetriever(
            base=bm25,
            scorer=scorer,  # type: ignore[arg-type]
            candidate_k=args.rerank_candidates,
            name="bm25-rerank",
        )
        if scorer is not None
        else None,
        "dense-rerank": RerankingRetriever(
            base=dense,  # type: ignore[arg-type]
            scorer=scorer,
            candidate_k=args.rerank_candidates,
            name="dense-rerank",
        )
        if scorer is not None and dense is not None
        else None,
        "hybrid-rerank": RerankingRetriever(
            base=hybrid,  # type: ignore[arg-type]
            scorer=scorer,
            candidate_k=args.rerank_candidates,
            name="hybrid-rerank",
        )
        if scorer is not None and hybrid is not None
        else None,
    }

    results = []
    for pipeline in requested:
        retriever = retrievers[pipeline]
        if retriever is None:
            raise RuntimeError(f"Pipeline {pipeline!r} could not be initialized")
        print(f"\nRunning {pipeline} on {dataset.id} ({len(dataset.queries)} queries)...")
        result = run_benchmark(dataset, retriever, args.k)

        uses_dense = pipeline in dense_pipeline_names
        uses_bm25 = pipeline in {"bm25", "hybrid", "bm25-rerank", "hybrid-rerank"}
        uses_hybrid = pipeline in {"hybrid", "hybrid-rerank"}
        uses_rerank = pipeline.endswith("-rerank")
        result["configuration"] = {
            "embedding_model": args.embedding_model if uses_dense else None,
            "bm25_k1": args.bm25_k1 if uses_bm25 else None,
            "bm25_b": args.bm25_b if uses_bm25 else None,
            "hybrid_candidates": args.hybrid_candidates if uses_hybrid else None,
            "rrf_constant": args.rrf_constant if uses_hybrid else None,
            "rerank_model": args.rerank_model if uses_rerank else None,
            "rerank_candidates": args.rerank_candidates if uses_rerank else None,
        }
        results.append(result)

    print("\nBenchmark summary\n")
    _print_summary(results)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output_path = output_dir / f"{_safe_name(args.dataset)}_{timestamp}.json"
    payload = {
        "experiment": (
            "v1-reranking" if any(pipeline.endswith("-rerank") for pipeline in requested)
            else "v0-retrieval-comparison"
        ),
        "dataset": args.dataset,
        "pipelines": requested,
        "results": results,
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nSaved: {output_path}")
    return 0


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    if args.command == "benchmark":
        return _benchmark(args)
    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path

from raglab.context import ContextBuilder
from raglab.datasets import load_ir_dataset
from raglab.embeddings import SentenceTransformerEmbeddings
from raglab.evaluation.benchmark import run_benchmark
from raglab.generation import LocalTransformersGenerator
from raglab.rag import RAGPipeline
from raglab.retrieval import (
    BM25Retriever,
    CrossEncoderScorer,
    DenseRetriever,
    HybridRetriever,
    RerankingRetriever,
)

DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
DEFAULT_GENERATION_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
PIPELINES = [
    "bm25",
    "dense",
    "hybrid",
    "bm25-rerank",
    "dense-rerank",
    "hybrid-rerank",
]
ANSWER_PIPELINES = ["hybrid", "hybrid-rerank"]


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

    answer = subparsers.add_parser(
        "answer",
        help="Run the V2 local grounded-generation pipeline",
    )
    answer.add_argument("--dataset", default="beir/scifact/test")
    query_group = answer.add_mutually_exclusive_group()
    query_group.add_argument("--query", default=None)
    query_group.add_argument("--query-id", default=None)
    answer.add_argument("--pipeline", choices=ANSWER_PIPELINES, default="hybrid")
    answer.add_argument("--top-k", type=int, default=5)
    answer.add_argument("--embedding-model", default=DEFAULT_EMBEDDING_MODEL)
    answer.add_argument("--rerank-model", default=DEFAULT_RERANK_MODEL)
    answer.add_argument("--rerank-candidates", type=int, default=10)
    answer.add_argument("--hybrid-candidates", type=int, default=100)
    answer.add_argument("--rrf-constant", type=int, default=60)
    answer.add_argument("--bm25-k1", type=float, default=1.5)
    answer.add_argument("--bm25-b", type=float, default=0.75)
    answer.add_argument("--model", default=DEFAULT_GENERATION_MODEL)
    answer.add_argument("--max-new-tokens", type=int, default=220)
    answer.add_argument("--context-max-chars", type=int, default=10_000)
    answer.add_argument("--source-max-chars", type=int, default=2_200)
    answer.add_argument("--output-dir", default="runs/v2")
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


def _select_question(dataset, query: str | None, query_id: str | None) -> tuple[str, str | None]:
    if query is not None:
        return query, None
    if query_id is not None:
        for item in dataset.queries:
            if item.id == query_id:
                return item.text, item.id
        raise ValueError(f"Query id {query_id!r} was not found in dataset {dataset.id!r}")
    selected = dataset.queries[0]
    return selected.text, selected.id


def _answer(args: argparse.Namespace) -> int:
    if args.top_k <= 0:
        raise ValueError("top-k must be positive")
    if args.rerank_candidates < args.top_k and args.pipeline == "hybrid-rerank":
        raise ValueError("rerank-candidates must be >= top-k for hybrid-rerank")

    dataset = load_ir_dataset(args.dataset)
    question, selected_query_id = _select_question(dataset, args.query, args.query_id)

    bm25 = BM25Retriever(k1=args.bm25_k1, b=args.bm25_b)
    embeddings = SentenceTransformerEmbeddings(args.embedding_model)
    dense = DenseRetriever(embeddings)
    hybrid = HybridRetriever(
        dense=dense,
        sparse=bm25,
        candidate_k=args.hybrid_candidates,
        rrf_constant=args.rrf_constant,
    )

    if args.pipeline == "hybrid-rerank":
        scorer = CrossEncoderScorer(args.rerank_model)
        retriever = RerankingRetriever(
            base=hybrid,
            scorer=scorer,
            candidate_k=args.rerank_candidates,
            name="hybrid-rerank",
        )
    else:
        retriever = hybrid

    context_builder = ContextBuilder(
        max_chars=args.context_max_chars,
        per_source_chars=args.source_max_chars,
    )
    generator = LocalTransformersGenerator(args.model)
    pipeline = RAGPipeline(
        documents=dataset.documents,
        retriever=retriever,
        context_builder=context_builder,
        generator=generator,
        top_k=args.top_k,
        max_new_tokens=args.max_new_tokens,
    )

    if selected_query_id is not None:
        print(f"Selected benchmark query: {selected_query_id}")
    print(f"Question: {question}")
    print(f"Indexing {len(dataset.documents)} documents with {retriever.name}...")
    pipeline.index()
    print("Generating grounded answer locally...")
    result = pipeline.answer(question)

    print("\nAnswer\n")
    print(result.answer)
    print("\nSources\n")
    for source in result.sources:
        title = source.title or "(untitled)"
        print(f"{source.citation} rank={source.rank} doc_id={source.doc_id} title={title}")

    report = result.citation_report
    print("\nCitation integrity\n")
    print(f"citations: {report.citation_count}")
    print(f"valid citations: {report.valid_citation_count}")
    print(f"invalid labels: {list(report.invalid_labels)}")
    print(f"sentence citation coverage: {report.sentence_coverage:.1%}")

    print("\nTiming (ms)\n")
    for name, value in result.timings_ms.items():
        print(f"{name}: {value:.2f}")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output_path = output_dir / f"answer_{timestamp}.json"
    payload = {
        "experiment": "v2-grounded-generation-smoke",
        "dataset": args.dataset,
        "query_id": selected_query_id,
        "pipeline": args.pipeline,
        "model": args.model,
        "result": result.to_dict(),
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nSaved: {output_path}")
    return 0


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    if args.command == "benchmark":
        return _benchmark(args)
    if args.command == "answer":
        return _answer(args)
    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

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
    WeightedHybridRetriever,
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

    diagnose = subparsers.add_parser(
        "diagnose-retrieval",
        help="Locate qrel-relevant documents in BM25, Dense and Hybrid rankings",
    )
    diagnose.add_argument("--dataset", default="beir/scifact/test")
    diagnose.add_argument("--query-id", default="1")
    diagnose.add_argument(
        "--strategies", nargs="+", choices=["bm25", "dense", "hybrid"],
        default=["bm25", "dense", "hybrid"],
    )
    diagnose.add_argument("--candidate-k", type=int, default=100)
    diagnose.add_argument("--context-k", type=int, default=5)
    diagnose.add_argument("--embedding-model", default=DEFAULT_EMBEDDING_MODEL)
    diagnose.add_argument("--output-dir", default="benchmarks/results")

    fusion_study = subparsers.add_parser(
        "fusion-study",
        help="Evaluate unweighted and dense-weighted RRF on SciFact training queries",
    )
    fusion_study.add_argument("--dataset", default="beir/scifact/train")
    fusion_study.add_argument("--allow-test", action="store_true",
                              help="Explicitly permit a held-out test evaluation")
    fusion_study.add_argument("--weights", nargs="+", type=float,
                              default=[1.5, 2.0, 3.0])
    fusion_study.add_argument("--k", nargs="+", type=int, default=[5, 10])
    fusion_study.add_argument("--candidate-k", type=int, default=100)
    fusion_study.add_argument("--rrf-constant", type=int, default=60)
    fusion_study.add_argument("--limit-queries", type=int, default=None)
    fusion_study.add_argument("--embedding-model", default=DEFAULT_EMBEDDING_MODEL)
    fusion_study.add_argument("--output-dir", default="benchmarks/results")

    analyze_fusion = subparsers.add_parser(
        "analyze-fusion",
        help="Analyze paired-query differences from an existing fusion JSON (no models)",
    )
    analyze_fusion.add_argument("--path", required=True)
    analyze_fusion.add_argument("--bootstrap-replicates", type=int, default=2000)
    analyze_fusion.add_argument("--seed", type=int, default=42)

    analyze_rerank = subparsers.add_parser(
        "analyze-rerank",
        help="Analyze saved paired retrieval benchmark without loading local models",
    )
    analyze_rerank.add_argument("--path", required=True)
    analyze_rerank.add_argument("--bootstrap-replicates", type=int, default=2000)
    analyze_rerank.add_argument("--seed", type=int, default=42)



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
    answer.add_argument(
        "--strict-citations",
        action="store_true",
        help="Exit nonzero for a generated answer failing syntactic citation coverage",
    )

    audit = subparsers.add_parser(
        "inspect-answer",
        help="Audit a saved V2 answer without regenerating or downloading an LLM",
    )
    audit.add_argument("--path", required=True)
    audit.add_argument(
        "--with-qrels",
        action="store_true",
        help="Compare retrieved document IDs to test qrels (evaluation only)",
    )
    audit.add_argument(
        "--strict",
        action="store_true",
        help="Exit nonzero if a non-abstaining answer fails citation coverage",
    )

    review_export = subparsers.add_parser(
        "review-export",
        help="Export an existing V2 answer to an unlabelled human-review packet",
    )
    review_export.add_argument("--path", required=True)
    review_export.add_argument("--output", required=True)

    review_score = subparsers.add_parser(
        "review-score",
        help="Summarize human-labelled evidence and claim annotations, without AI",
    )
    review_score.add_argument("--path", required=True)
    review_score.add_argument("--output", default=None)

    review_interactive = subparsers.add_parser(
        "review-interactive",
        help="Guide a human through source and claim review, saving a new JSON file",
    )
    review_interactive.add_argument("--path", required=True)
    review_interactive.add_argument("--output", required=True)

    dev_design = subparsers.add_parser(
        "design-dev-cases",
        help="Build unlabelled, controlled SciFact TRAIN evidence review cases",
    )
    dev_design.add_argument("--dataset", default="beir/scifact/train")
    dev_design.add_argument("--query-count", type=int, default=6)
    dev_design.add_argument("--seed", type=int, default=17)
    dev_design.add_argument("--output-dir", required=True)

    dev_review = subparsers.add_parser(
        "review-dev-batch",
        help="Blind human annotation of the next SciFact TRAIN case group",
    )
    dev_review.add_argument("--suite", required=True)
    dev_review.add_argument("--max-cases", type=int, default=3)

    auto_audit = subparsers.add_parser(
        "audit-dev-suite",
        help="Non-interactive structural and evidence-availability checks for TRAIN cases",
    )
    auto_audit.add_argument("--suite", required=True)

    nli_pilot = subparsers.add_parser(
        "nli-dev-pilot",
        help="Uncalibrated local NLI predictions on SciFact TRAIN evidence cases",
    )
    nli_pilot.add_argument("--suite", required=True)
    nli_pilot.add_argument("--batch-size", type=int, default=2)

    diagnose_nli = subparsers.add_parser(
        "diagnose-nli",
        help="Verify archived TRAIN NLI scores and three basic model sanity controls",
    )
    diagnose_nli.add_argument("--suite", required=True)

    experiment = subparsers.add_parser(
        "experiment",
        help="Compare a specified RAG architecture against a matched baseline",
    )
    experiment.add_argument("--spec", required=True, help="Path to a JSON experiment spec")
    experiment.add_argument("--output-dir", default="benchmarks/results")
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


def _analyze_rerank(args: argparse.Namespace) -> int:
    from raglab.evaluation.rerank_analysis import (
        analyze_rerank_artifact,
        rerank_report_markdown,
    )

    input_path = Path(args.path)
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    report = analyze_rerank_artifact(
        payload,
        bootstrap_replicates=args.bootstrap_replicates,
        seed=args.seed,
    )
    print("\nRET-RERANK-20 | offline paired-query audit\n")
    print(f"Development queries: {report['query_count']}")
    for metric, entry in report["metrics"].items():
        print(
            f"{metric}: delta={entry['delta']:+.5f}, "
            f"95% bootstrap CI=[{entry['ci95'][0]:+.5f}, "
            f"{entry['ci95'][1]:+.5f}], "
            f"wins={entry['wins']}, losses={entry['losses']}, ties={entry['ties']}"
        )
    print(f"Decision: {report['decision']}")
    name = input_path.with_suffix("")
    json_path = name.with_name(name.name + "_RERANK_ANALYSIS.json")
    md_path = name.with_name(name.name + "_RERANK_ANALYSIS.md")
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(rerank_report_markdown(report), encoding="utf-8")
    print(f"JSON: {json_path}")
    print(f"Report: {md_path}")
    print("No indexing, embedding, cross-encoder or Qwen was invoked.")
    return 0


def _analyze_fusion(args: argparse.Namespace) -> int:
    from raglab.evaluation.paired_comparison import analyze_fusion_artifact, to_markdown

    path = Path(args.path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    report = analyze_fusion_artifact(
        payload, bootstrap_replicates=args.bootstrap_replicates, seed=args.seed
    )

    print("\nRET-FUSION-01 | offline paired-query audit\n")
    print(f"Training queries checked: {report['query_count']}")
    print(f"Decision: {report['decision']}")
    for comparison in report["comparisons"]:
        delta = comparison["metrics"]["recall@5"]
        print(
            f"{comparison['candidate']}: recall@5 delta={delta['delta']:+.5f}, "
            f"95% bootstrap CI=[{delta['ci95'][0]:+.5f}, {delta['ci95'][1]:+.5f}], "
            f"wins={delta['wins']}, losses={delta['losses']}, ties={delta['ties']}"
        )
    stem = path.with_suffix("")
    json_path = stem.with_name(stem.name + "_PAIRED_ANALYSIS.json")
    markdown_path = stem.with_name(stem.name + "_PAIRED_ANALYSIS.md")
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    markdown_path.write_text(to_markdown(report), encoding="utf-8")
    print(f"JSON: {json_path}")
    print(f"Report: {markdown_path}")
    print("No model, embeddings, inference or new retrieval was run.")
    return 0


def _fusion_study(args: argparse.Namespace) -> int:
    import math

    from raglab.core.fingerprint import fingerprint_documents

    # Never silently tune weights against held-out SciFact test labels.
    if args.dataset != "beir/scifact/train" and not args.allow_test:
        raise ValueError(
            "Fusion-weight selection is train-only by default. "
            "For a separately justified held-out evaluation, pass --allow-test."
        )
    weights = list(dict.fromkeys(args.weights))
    if any(not math.isfinite(value) or value <= 0 for value in weights):
        raise ValueError("Fusion weights must be positive finite values")
    if any(value == 1.0 for value in weights):
        weights = [value for value in weights if value != 1.0]
    if args.candidate_k <= 0 or args.rrf_constant < 0:
        raise ValueError("Invalid RRF parameters")

    dataset = load_ir_dataset(args.dataset, limit_queries=args.limit_queries)
    bm25 = BM25Retriever()
    embeddings = SentenceTransformerEmbeddings(args.embedding_model)
    dense = DenseRetriever(embeddings)
    base = HybridRetriever(
        dense=dense, sparse=bm25, candidate_k=args.candidate_k,
        rrf_constant=args.rrf_constant,
    )
    pipelines = [
        ("bm25", bm25),
        ("dense", dense),
        ("hybrid-rrf", base),
    ]
    for dense_weight in weights:
        pipelines.append((
            f"hybrid-dense-{dense_weight:g}",
            WeightedHybridRetriever(
                dense=dense, sparse=bm25,
                dense_weight=dense_weight,
                candidate_k=args.candidate_k,
                rrf_constant=args.rrf_constant,
            ),
        ))

    # Shared retriever objects cache the same indexed corpus and embedding matrix.
    # run_benchmark includes query-time search and fusion; indexing is excluded.
    results = []
    for name, retriever in pipelines:
        print(f"Running {name}: {len(dataset.queries)} training/evaluation queries...")
        results.append(run_benchmark(dataset, retriever, args.k))
    print("\nFusion experiment (NOT a selected winner)\n")
    _print_summary(results)

    import platform
    import subprocess

    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, timeout=3,
        ).strip()
    except (OSError, subprocess.SubprocessError):
        sha = None
    payload = {
        "experiment_id": "RET-FUSION-01",
        "publication_status": "exploratory",
        "created_at": datetime.now(UTC).isoformat(),
        "dataset": args.dataset,
        "query_count": len(dataset.queries),
        "document_fingerprint": fingerprint_documents(dataset.documents),
        "git_sha": sha,
        "embedding_model": args.embedding_model,
        "rrf_constant": args.rrf_constant,
        "candidate_k": args.candidate_k,
        "weights": weights,
        "k": args.k,
        "python": platform.python_version(),
        "results": results,
        "limitations": [
            "Weights must be selected on train and frozen before test.",
            "Repeated sequential queries may bias latency; warmups are not standardized.",
            "Retrieval labels do not establish answer faithfulness.",
            "No model revision lock; record exact model revision before canonical claims.",
        ],
    }
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = output_dir / f"RET_FUSION_{_safe_name(args.dataset)}_{stamp}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Saved train-only exploratory fusion study: {path}")
    return 0


def _diagnose_retrieval(args: argparse.Namespace) -> int:
    from raglab.diagnostics import diagnose_retrieval

    dataset = load_ir_dataset(args.dataset)
    names = list(dict.fromkeys(args.strategies))
    bm25 = BM25Retriever()
    needs_dense = "dense" in names or "hybrid" in names
    dense = (
        DenseRetriever(SentenceTransformerEmbeddings(args.embedding_model))
        if needs_dense else None
    )
    retrievers = {}
    if "bm25" in names:
        retrievers["bm25"] = bm25
    if "dense" in names:
        assert dense is not None
        retrievers["dense"] = dense
    if "hybrid" in names:
        assert dense is not None
        retrievers["hybrid"] = HybridRetriever(
            dense=dense, sparse=bm25, candidate_k=args.candidate_k,
        )

    report = diagnose_retrieval(
        dataset,
        query_id=args.query_id,
        retrievers=retrievers,
        candidate_k=args.candidate_k,
        context_k=args.context_k,
    )
    print("\nRetrieval diagnosis — gold labels used only after ranking\n")
    print(f"Query: {report['query']}")
    for document in report["gold_documents"]:
        print(f"Gold document: {document['doc_id']} | {document['title']}")
    for name, outcome in report["strategies"].items():
        print(
            f"{name}: relevant top-{args.context_k}="
            f"{outcome['relevant_in_context']}/{len(report['gold_documents'])}; "
            f"gold ranks={outcome['gold_ranks']}; "
            f"retrieval_ms={outcome['retrieval_ms']:.2f}"
        )
        if name == "hybrid":
            print(f"Reranking candidate eligibility: {outcome['rerank_eligibility']}")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = output_dir / f"DIAG_{_safe_name(args.query_id)}_{stamp}.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved diagnosis: {path}")
    print("Ground-truth qrels may not exhaust all useful evidence.")
    return 0


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
    print(f"Output status: {result.output_status}")
    if result.raw_generation is not None:
        print("Rejected raw generation: saved in the local JSON only.")
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
    from raglab.evaluation.answer_audit import audit_answer_artifact

    audit = audit_answer_artifact(payload)
    payload["audit"] = audit
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nSaved: {output_path}")
    print(f"Citation gate: {audit['citation_status']}")
    print(f"Output status: {audit['output_status']}")
    print("Semantic faithfulness: not_evaluated (requires independently judged evidence)")
    if args.strict_citations and audit["citation_status"] == "failed":
        print("QUALITY_GATE_FAIL: generated answer lacks a valid citation contract")
        return 1
    return 0


def _experiment(args: argparse.Namespace) -> int:
    from raglab.experiments import run_experiment

    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    payload = run_experiment(spec)
    _print_summary(payload["results"])
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output_path = output_dir / f"{_safe_name(payload['experiment_id'])}_{timestamp}.json"
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Saved exploratory comparison: {output_path}")
    return 0


def _diagnose_nli(args: argparse.Namespace) -> int:
    from raglab.evaluation.nli_diagnostics import (
        build_nli_diagnostic,
        diagnostic_markdown,
    )
    from raglab.evaluation.dev_automatic_audit import audit_dev_suite
    from raglab.evaluation.dev_nli_pilot import DEFAULT_NLI_MODEL
    from sentence_transformers import CrossEncoder

    suite = Path(args.suite)
    reports = sorted(
        p for p in suite.glob("AUTO_NLI_*.json")
        if not p.name.startswith("AUTO_NLI_DIAGNOSTIC_")
    )
    if not reports:
        raise FileNotFoundError("No prior AUTO_NLI pilot report in selected suite")
    original = reports[-1]
    saved = json.loads(original.read_text(encoding="utf-8"))
    dataset = load_ir_dataset("beir/scifact/train")
    audit_dev_suite(suite, dataset)
    print("=== M2 NLI SANITY DIAGNOSTIC: NO PROMPTS ===")
    print("Previous experiment: " + original.name)
    print("Loading the cached public NLI model on CPU for three simple controls.")
    model = CrossEncoder(DEFAULT_NLI_MODEL, device="cpu", max_length=512)
    diagnostics = build_nli_diagnostic(
        suite,
        saved,
        probe_predict=lambda pairs: model.predict(
            pairs, batch_size=3, show_progress_bar=False,
            apply_softmax=False
        ),
    )
    diagnostics["archived_input_file"] = original.name
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    json_path = suite / f"AUTO_NLI_DIAGNOSTIC_{stamp}.json"
    markdown_path = suite / f"AUTO_NLI_DIAGNOSTIC_{stamp}.md"
    with json_path.open("x", encoding="utf-8") as stream:
        json.dump(diagnostics, stream, ensure_ascii=False, indent=2)
    with markdown_path.open("x", encoding="utf-8") as stream:
        stream.write(diagnostic_markdown(diagnostics))
    print(f"Model controls passed: {diagnostics['control_probe_passed']}")
    print(f"By source arm: {diagnostics['per_source_arm']}")
    print(f"Decision: {diagnostics['decision']}")
    print(f"JSON: {json_path}")
    print(f"Markdown: {markdown_path}")
    print("No change to runtime abstention or human annotations.")
    return 0


def _nli_dev_pilot(args: argparse.Namespace) -> int:
    from raglab.evaluation.dev_automatic_audit import audit_dev_suite
    from raglab.evaluation.dev_nli_pilot import (
        DEFAULT_NLI_MODEL,
        NLI_LABELS,
        format_nli_report,
        run_nli_pilot,
    )

    if not 1 <= args.batch_size <= 8:
        raise ValueError("NLI batch-size must be between 1 and 8")
    suite = Path(args.suite)
    dataset = load_ir_dataset("beir/scifact/train")
    # Validate data integrity BEFORE loading/download of a local model.
    audit_dev_suite(suite, dataset)
    from sentence_transformers import CrossEncoder

    print("=== M2 TRAIN: automatic CPU NLI pilot ===")
    print(f"Model: {DEFAULT_NLI_MODEL} (first run may download public weights)")
    model = CrossEncoder(DEFAULT_NLI_MODEL, device="cpu", max_length=512)
    raw_labels = getattr(model.model.config, "id2label", {})
    if len(raw_labels) != 3:
        raise ValueError("Expected a 3-class NLI classifier")
    labels = [
        str(raw_labels.get(i, raw_labels.get(str(i), ""))).lower()
        for i in range(3)
    ]
    if not all(x.startswith("label_") for x in labels) and tuple(labels) != NLI_LABELS:
        raise ValueError(f"Unrecognized classifier class order: {labels}")
    report = run_nli_pilot(
        suite,
        dataset,
        predict=lambda pairs: model.predict(
            pairs, batch_size=args.batch_size, show_progress_bar=False
        ),
        model_id=DEFAULT_NLI_MODEL,
        model_revision=getattr(model.model.config, "_commit_hash", None),
    )
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    json_path = suite / f"AUTO_NLI_{stamp}.json"
    md_path = suite / f"AUTO_NLI_{stamp}.md"
    with json_path.open("x", encoding="utf-8") as out:
        json.dump(report, out, indent=2, ensure_ascii=False)
    with md_path.open("x", encoding="utf-8") as out:
        out.write(format_nli_report(report))
    print(f"Pairs analyzed: {report['nli_scored_count']}")
    print(f"Predicted classes: {report['predicted_label_counts']}")
    print(f"Empty-context controls: {report['no_context_count']}")
    print(f"JSON: {json_path}")
    print(f"Markdown: {md_path}")
    print("NLI_DEV_PILOT_UNCALIBRATED_COMPLETED")
    print("Model outputs are not validated biomedical truth or human labels.")
    return 0


def _audit_dev_suite(args: argparse.Namespace) -> int:
    from raglab.evaluation.dev_automatic_audit import (
        audit_dev_suite,
        audit_report_markdown,
    )

    suite = Path(args.suite)
    dataset = load_ir_dataset("beir/scifact/train")
    report = audit_dev_suite(suite, dataset)
    report_path = suite / "AUTO_AUDIT.json"
    markdown_path = suite / "AUTO_AUDIT.md"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    markdown_path.write_text(
        audit_report_markdown(report), encoding="utf-8"
    )
    print("=== M2 automatic train-only audit ===")
    print(f"Status: {report['status']}")
    print(f"Cases structurally checked: {report['case_count']}")
    print(f"Training propositions: {report['query_count']}")
    print(f"No-context abstention controls: {report['no_context_control_count']}")
    print(f"Cases requiring semantic assessment: {report['semantic_unassessed_count']}")
    print(f"Existing human review files: {report['existing_human_review_files']}")
    print(f"JSON: {report_path}")
    print(f"Markdown: {markdown_path}")
    print("No questions, models, embeddings, semantic labels, or test-set qrels.")
    return 0


def _review_dev_batch(args: argparse.Namespace) -> int:
    from raglab.evaluation.dev_review_batch import review_next_dev_group

    stats = review_next_dev_group(
        Path(args.suite), max_cases=args.max_cases, ask=input, show=print
    )
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    print("No labels were inferred, and no models or retrieval were run.")
    return 0


def _design_dev_cases(args: argparse.Namespace) -> int:
    from raglab.evaluation.dev_case_design import (
        design_dev_cases,
        write_dev_cases,
    )

    if args.dataset != "beir/scifact/train":
        raise ValueError("Development cases must use beir/scifact/train only")
    dataset = load_ir_dataset(args.dataset)
    manifest, packets = design_dev_cases(
        dataset, query_count=args.query_count, seed=args.seed
    )
    directory = write_dev_cases(
        manifest, packets, output_dir=Path(args.output_dir)
    )
    print(f"Unlabelled M2 dev suite: {directory}")
    print(f"Training propositions: {manifest['query_count']}")
    print(f"Review packets: {manifest['case_count']}")
    print("No automatic truth, contradiction, relevance or answer-quality labels.")
    print("Qrels inform candidate selection only and are absent from reviewer packets.")
    print("No embeddings, cross-encoder, Qwen, or inference calls were made.")
    return 0


def _review_interactive(args: argparse.Namespace) -> int:
    from raglab.evaluation.interactive_review import annotate_packet
    from raglab.evaluation.semantic_review import summarize_review_packet

    input_path = Path(args.path)
    output_path = Path(args.output)
    if input_path.resolve() == output_path.resolve():
        raise ValueError("The annotated review must not overwrite the source packet")
    if output_path.exists():
        raise FileExistsError(f"Will not overwrite previous human annotations: {output_path}")

    packet = json.loads(input_path.read_text(encoding="utf-8"))
    annotated = annotate_packet(packet, ask=input, show=print)
    result = summarize_review_packet(annotated)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x", encoding="utf-8") as stream:
        json.dump(annotated, stream, indent=2, ensure_ascii=False)
    print(f"Human review saved: {output_path}")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if result["review_status"] != "complete":
        print("This review is incomplete; no semantic quality score was calculated.")
    else:
        print("Review completed with human labels; this does NOT certify a model-wide score.")
    return 0


def _review_export(args: argparse.Namespace) -> int:
    from raglab.evaluation.semantic_review import prepare_review_packet

    input_path = Path(args.path)
    output_path = Path(args.output)
    if output_path.exists():
        raise FileExistsError(f"Will not overwrite existing reviews: {output_path}")
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    packet = prepare_review_packet(payload)
    packet["provenance"]["artifact_filename"] = input_path.name
    packet["provenance"]["artifact_sha256"] = __import__("hashlib").sha256(
        input_path.read_bytes()
    ).hexdigest()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x", encoding="utf-8") as stream:
        json.dump(packet, stream, indent=2, ensure_ascii=False)
    print(f"Semantic review packet: {output_path}")
    print(f"Claims needing human review: {len(packet['claims'])}")
    print(f"Sources needing relevance review: {len(packet['sources'])}")
    print("No semantic support verdict was generated automatically.")
    return 0


def _review_score(args: argparse.Namespace) -> int:
    from raglab.evaluation.semantic_review import summarize_review_packet

    packet = json.loads(Path(args.path).read_text(encoding="utf-8"))
    summary = summarize_review_packet(packet)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Saved human review summary: {out}")
    return 0


def _inspect_answer(args: argparse.Namespace) -> int:
    from raglab.evaluation.answer_audit import audit_answer_artifact

    artifact_path = Path(args.path)
    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    relevant_doc_ids = None
    if args.with_qrels:
        query_id = payload.get("query_id")
        if query_id is None:
            raise ValueError("Saved answer has no benchmark query ID; cannot use qrels")
        dataset = load_ir_dataset(payload["dataset"])
        if str(query_id) not in dataset.qrels:
            raise ValueError(f"No relevance judgments found for query ID {query_id}")
        relevant_doc_ids = list(dataset.qrels[str(query_id)])

    report = audit_answer_artifact(payload, relevant_doc_ids=relevant_doc_ids)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if args.strict and report["citation_status"] == "failed":
        return 1
    return 0


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    if args.command == "benchmark":
        return _benchmark(args)
    if args.command == "diagnose-retrieval":
        return _diagnose_retrieval(args)
    if args.command == "fusion-study":
        return _fusion_study(args)
    if args.command == "analyze-fusion":
        return _analyze_fusion(args)
    if args.command == "analyze-rerank":
        return _analyze_rerank(args)
    if args.command == "answer":
        return _answer(args)
    if args.command == "experiment":
        return _experiment(args)
    if args.command == "inspect-answer":
        return _inspect_answer(args)
    if args.command == "review-export":
        return _review_export(args)
    if args.command == "review-score":
        return _review_score(args)
    if args.command == "review-interactive":
        return _review_interactive(args)
    if args.command == "design-dev-cases":
        return _design_dev_cases(args)
    if args.command == "review-dev-batch":
        return _review_dev_batch(args)
    if args.command == "audit-dev-suite":
        return _audit_dev_suite(args)
    if args.command == "nli-dev-pilot":
        return _nli_dev_pilot(args)
    if args.command == "diagnose-nli":
        return _diagnose_nli(args)
    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

# RAG Architecture Lab

A from-first-principles lab for implementing, benchmarking, and comparing Retrieval-Augmented Generation retrieval architectures under controlled conditions.

> **Current milestone: V0 — Retrieval Benchmark**
>
> Dense retrieval vs. BM25 vs. Hybrid retrieval (Reciprocal Rank Fusion), evaluated on the same public benchmark with the same queries and relevance judgments.

## Why this project exists

RAG is not one architecture. Retrieval choices create different trade-offs in relevance, robustness, latency, and complexity. This lab isolates those choices and measures them instead of treating a single RAG pipeline as universally best.

The project intentionally avoids high-level RAG frameworks in its core implementation. Retrieval, fusion, evaluation, and orchestration are implemented directly so their behavior remains inspectable.

## V0 research question

**How do dense, sparse, and hybrid retrieval strategies perform under identical benchmark conditions?**

V0 compares:

- **Dense retrieval** — local sentence embeddings + cosine similarity
- **BM25** — lexical retrieval implemented in this repository
- **Hybrid retrieval** — dense + BM25 combined with Reciprocal Rank Fusion (RRF)

Metrics:

- Recall@K
- Mean Reciprocal Rank (MRR@K)
- nDCG@K
- Mean and p95 query latency

## Benchmark

The default benchmark is **BEIR SciFact (test)** via `ir_datasets`.

- 5,183 documents
- 300 test queries
- relevance judgments (qrels) for objective retrieval evaluation

For a very fast smoke test, `nano-beir/scifact` can also be used.

## Principles

1. **Same corpus, same queries, same conditions.** Only the retrieval strategy changes.
2. **From first principles where it matters.** BM25, cosine retrieval, RRF, and evaluation metrics are implemented here.
3. **Models are dependencies; system architecture is ours.** Local pretrained models may provide embeddings, but the retrieval system around them is implemented in this project.
4. **No API cost required.** V0 runs locally and does not require an LLM or paid API.
5. **Measure before expanding.** Reranking, generation, tracing UI, and more advanced RAG variants are out of scope until V0 produces a useful benchmark.

## Quick start

Requirements: Python 3.11+

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
# source .venv/bin/activate

pip install -e ".[benchmark]"
```

Run a quick smoke benchmark:

```bash
raglab benchmark --dataset nano-beir/scifact --pipelines bm25 dense hybrid --k 5 10
```

Run the full SciFact test benchmark:

```bash
raglab benchmark --dataset beir/scifact/test --pipelines bm25 dense hybrid --k 5 10
```

The first dense run downloads the configured open-source embedding model locally. No paid API key is needed.

For development:

```bash
pip install -e ".[dev]"
pytest
```

## Project structure

```text
src/raglab/
  core/          Shared data types
  datasets/      Benchmark adapters
  embeddings/    Local embedding providers
  retrieval/     Dense, BM25, and hybrid retrievers
  fusion/        Rank-fusion algorithms
  evaluation/    Retrieval metrics and benchmark runner
  cli.py         Command-line interface

tests/           Unit tests for algorithms and metrics
docs/            Scope, architecture, and experiment methodology
benchmarks/       Generated benchmark results (JSON)
```

## Reproducibility

Each benchmark result records the dataset, pipeline configuration, K values, embedding model, aggregate metrics, per-query rankings, latency, and runtime environment. Results are written to `benchmarks/results/` as JSON.

## Roadmap

V0 must pass a go/no-go review before the project expands.

- **V0:** Dense vs. BM25 vs. Hybrid retrieval
- **V1:** Reranking and candidate-stage analysis
- **V2:** Generation, context construction, and citations
- **V3:** Trace/observability model and interactive inspection
- **V4:** Web observatory and benchmark visualization
- **Later experiments:** query rewriting, multi-query retrieval, parent-child retrieval, contextual retrieval, adaptive/agentic RAG, GraphRAG

See [`docs/SCOPE.md`](docs/SCOPE.md), [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), and [`docs/EXPERIMENTS.md`](docs/EXPERIMENTS.md).

## Cost

V0 is designed to run at **$0 API/infrastructure cost** on a local machine. The only external downloads are open-source Python packages, the benchmark data, and a local embedding model.

## References

- Thakur et al. (2021), **BEIR: A Heterogeneous Benchmark for Zero-shot Evaluation of Information Retrieval Models**
- Wadden et al. (2020), **Fact or Fiction: Verifying Scientific Claims (SciFact)**
- Cormack, Clarke & Buettcher (2009), **Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods**
- Robertson & Zaragoza (2009), **The Probabilistic Relevance Framework: BM25 and Beyond**

## Status

The repository contains the V0 retrieval engine and benchmark harness. Real benchmark results have not yet been committed; roadmap items beyond V0 are planned, not completed.

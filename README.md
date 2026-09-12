# RAG Architecture Lab

A from-first-principles lab for implementing, benchmarking, and comparing Retrieval-Augmented Generation retrieval architectures under controlled conditions.

> **V0 and V1 complete — Retrieval + Reranking Benchmarks**
>
> Dense retrieval vs. BM25 vs. Hybrid RRF, followed by a controlled cross-encoder reranking experiment on the same public benchmark.

## Why this project exists

RAG is not one architecture. Retrieval choices create different trade-offs in relevance, robustness, latency, and complexity. This lab isolates those choices and measures them instead of treating a single RAG pipeline as universally best.

The project intentionally avoids high-level RAG frameworks in its core implementation. Retrieval, fusion, reranking orchestration, evaluation, and benchmark control are implemented directly so their behavior remains inspectable.

## V0 — Retrieval comparison

Research question:

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

### V0 results

Full benchmark: **BEIR SciFact test — 5,183 documents, 300 queries**.

| Pipeline | MRR@10 | nDCG@10 | Recall@5 | Recall@10 | Mean latency |
|---|---:|---:|---:|---:|---:|
| BM25 | 0.6328 | 0.6647 | 0.7243 | 0.7849 | 7.52 ms |
| Dense | 0.6047 | 0.6451 | 0.7379 | 0.7833 | 26.17 ms |
| **Hybrid RRF** | **0.6484** | **0.6865** | **0.7571** | **0.8179** | 51.86 ms |

Under this dataset and configuration, Hybrid RRF produced the strongest reported quality metrics while trading additional latency for better ranking and recall. BM25 remained substantially faster and outperformed Dense on MRR@10, while Dense achieved slightly higher Recall@5 than BM25.

See [`benchmarks/V0_RESULTS.md`](benchmarks/V0_RESULTS.md) for the full methodology, interpretation, and go/no-go decision.

## V1 — Cross-encoder reranking

Research question:

**Does reranking Hybrid RRF candidates with a local cross-encoder improve top-K retrieval quality enough to justify its additional latency?**

V1 keeps the V0 Hybrid pipeline as the first stage, retrieves 50 candidates, and reranks them with the pretrained local model `cross-encoder/ms-marco-MiniLM-L-6-v2`.

```text
Dense + BM25 -> RRF -> top 50 candidates -> Cross-Encoder -> top K
```

### V1 results

| Pipeline | MRR@10 | nDCG@10 | Recall@5 | Recall@10 | Mean latency |
|---|---:|---:|---:|---:|---:|
| Hybrid RRF | 0.6484 | 0.6865 | **0.7571** | 0.8179 | **45.91 ms** |
| Hybrid + Cross-Encoder | **0.6615** | **0.6944** | 0.7449 | **0.8272** | 3896.99 ms |

The reranker improved MRR@10 by about **2.0% relative**, nDCG@10 by about **1.2%**, and Recall@10 by about **1.1%**, but mean latency increased roughly **84.9x** on the recorded CPU runner. Recall@5 decreased by about **1.6% relative**.

**Decision:** the current 50-candidate cross-encoder configuration is a **NO-GO as the default architecture** because its modest quality gain does not justify several seconds of query latency. The research result is still useful: a smaller candidate-depth efficiency ablation is justified before moving to generation.

See [`benchmarks/V1_RESULTS.md`](benchmarks/V1_RESULTS.md) for the complete V1 result and interpretation.

## Benchmark

The default benchmark is **BEIR SciFact (test)** via `ir_datasets`.

- 5,183 documents
- 300 test queries
- relevance judgments (qrels) for objective retrieval evaluation

For a very fast smoke test, `nano-beir/scifact` can also be used.

## Principles

1. **Same corpus, same queries, same conditions.** Change one architectural decision at a time.
2. **From first principles where it matters.** BM25, cosine retrieval, RRF, evaluation metrics, and pipeline orchestration are implemented here.
3. **Models are dependencies; system architecture is ours.** Local pretrained models may provide embeddings or pairwise relevance scores, but the retrieval system around them is implemented in this project.
4. **No paid API required.** Current experiments use public benchmark data and local open-source models.
5. **Measure before expanding.** New components are added only when they answer a concrete experimental question.

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

Run a quick retrieval benchmark:

```bash
raglab benchmark --dataset nano-beir/scifact --pipelines bm25 dense hybrid --k 5 10
```

Run the full V0 SciFact benchmark:

```bash
raglab benchmark --dataset beir/scifact/test --pipelines bm25 dense hybrid --k 5 10
```

Run the V1 reranking comparison:

```bash
raglab benchmark \
  --dataset beir/scifact/test \
  --pipelines hybrid hybrid-rerank \
  --k 5 10 \
  --rerank-candidates 50
```

The first model-backed run downloads the configured open-source models locally. No paid API key is needed.

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
  retrieval/     Dense, BM25, Hybrid, and reranking retrievers
  fusion/        Rank-fusion algorithms
  evaluation/    Retrieval metrics and benchmark runner
  cli.py         Command-line interface

tests/           Unit tests for algorithms and pipeline behavior
docs/            Scope, architecture, and experiment methodology
benchmarks/       Recorded experiment summaries and generated JSON results
```

## Reproducibility

Each benchmark result records the dataset, pipeline configuration, K values, model configuration, aggregate metrics, per-query rankings, latency, and runtime environment. Local runs write timestamped JSON artifacts to `benchmarks/results/`. GitHub Actions workflows reproduce the V0 and V1 experiments.

## Roadmap

- ✅ **V0:** Dense vs. BM25 vs. Hybrid retrieval
- ✅ **V1:** Cross-encoder reranking and quality/latency trade-off
- **V1.1:** Candidate-depth efficiency ablation
- **V2:** Generation, context construction, and citations
- **V3:** Trace/observability model and interactive inspection
- **V4:** Web observatory and benchmark visualization
- **Later experiments:** query rewriting, multi-query retrieval, parent-child retrieval, contextual retrieval, adaptive/agentic RAG, GraphRAG

See [`docs/SCOPE.md`](docs/SCOPE.md), [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), and [`docs/EXPERIMENTS.md`](docs/EXPERIMENTS.md).

## Cost

V0 and V1 run at **$0 paid API cost**. They use public benchmark data and local open-source models. The recorded experiments were reproduced through GitHub Actions and can also run locally without a paid API or managed vector database.

## References

- Thakur et al. (2021), **BEIR: A Heterogeneous Benchmark for Zero-shot Evaluation of Information Retrieval Models**
- Wadden et al. (2020), **Fact or Fiction: Verifying Scientific Claims (SciFact)**
- Cormack, Clarke & Buettcher (2009), **Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods**
- Robertson & Zaragoza (2009), **The Probabilistic Relevance Framework: BM25 and Beyond**

## Status

V0 and V1 are complete. V1 showed that a cross-encoder can improve ranking quality but that the tested 50-candidate CPU configuration is not efficient enough to adopt as the default. The next experiment is **V1.1: candidate-depth efficiency ablation** before deciding whether reranking remains in the architecture or the project moves directly to generation.

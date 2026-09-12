# RAG Architecture Lab

A from-first-principles lab for implementing, benchmarking, and comparing Retrieval-Augmented Generation retrieval architectures under controlled conditions.

> **Current state**
>
> V0 retrieval benchmarking, V1 cross-encoder reranking, and V1.1 candidate-depth ablation are complete on the designated local Windows machine. The retrieval phase is now closed with Hybrid RRF as the default path and 10-candidate cross-encoder reranking retained as an optional quality mode. The next phase is V2: generation, context construction, and citations.

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

### V0 quality results

Full benchmark: **BEIR SciFact test — 5,183 documents, 300 queries**.

| Pipeline | MRR@10 | nDCG@10 | Recall@5 | Recall@10 |
|---|---:|---:|---:|---:|
| BM25 | 0.6328 | 0.6647 | 0.7243 | 0.7849 |
| Dense | 0.6047 | 0.6451 | 0.7379 | 0.7833 |
| **Hybrid RRF** | **0.6484** | **0.6865** | **0.7571** | **0.8179** |

Hybrid RRF produced the strongest reported quality metrics under the V0 configuration. BM25 outperformed Dense on MRR@10, while Dense achieved slightly higher Recall@5 than BM25.

The original V0 run predates the local-only benchmark policy, so its latency values are retained in the detailed experiment record but are not used as canonical hardware comparisons. V1 and later latency decisions use the designated local machine.

See [`benchmarks/V0_RESULTS.md`](benchmarks/V0_RESULTS.md) for the full methodology and original V0 record.

## V1 — Cross-encoder reranking

Research question:

**Does reranking Hybrid RRF candidates with a local cross-encoder improve top-K retrieval quality enough to justify its additional latency?**

V1 keeps the V0 Hybrid pipeline as the first stage, retrieves 50 candidates, and reranks them with the pretrained local model `cross-encoder/ms-marco-MiniLM-L-6-v2`.

```text
Dense + BM25 -> RRF -> top 50 candidates -> Cross-Encoder -> top K
```

### Canonical local environment

- CPU: AMD Ryzen 7 5700U with Radeon Graphics
- 8 cores / 16 logical processors
- RAM: ~15.3 GiB
- Windows 11 64-bit
- Python 3.11.9
- Paid APIs: none

### V1 canonical local results

| Pipeline | MRR@10 | nDCG@10 | Recall@5 | Recall@10 | Mean latency | p95 latency |
|---|---:|---:|---:|---:|---:|---:|
| Hybrid RRF | 0.6484 | 0.6865 | **0.7571** | 0.8179 | **34.53 ms** | **53.09 ms** |
| Hybrid + Cross-Encoder (50) | **0.6615** | **0.6944** | 0.7449 | **0.8272** | 3706.43 ms | 4184.39 ms |

The reranker improved MRR@10 by about **2.0% relative**, nDCG@10 by about **1.2%**, and Recall@10 by about **1.1%**, while Recall@5 decreased about **1.6%**. Mean latency increased roughly **107.3x** on the canonical local CPU environment.

**V1 decision:** 50-candidate cross-encoder reranking is a **NO-GO as the default architecture** on this machine. The quality gain is real but too small to justify several seconds of query latency.

See [`benchmarks/V1_RESULTS.md`](benchmarks/V1_RESULTS.md) for the complete canonical result and interpretation.

## V1.1 — Candidate-depth ablation

V1.1 asks whether smaller reranking candidate sets retain most of the quality improvement while reducing latency.

| Candidate depth | MRR@10 | nDCG@10 | Recall@5 | Recall@10 | Mean latency | p95 latency |
|---:|---:|---:|---:|---:|---:|---:|
| Hybrid baseline | 0.6484 | 0.6865 | 0.7571 | 0.8179 | ~31–38 ms | ~46–62 ms |
| **10** | 0.6600 | 0.6914 | **0.7660** | 0.8179 | **744.11 ms** | **893.12 ms** |
| **20** | **0.6618** | 0.6926 | 0.7389 | 0.8211 | 1634.30 ms | 1887.84 ms |
| **50** | 0.6615 | **0.6944** | 0.7449 | **0.8272** | 3706.43 ms | 4184.39 ms |

The 10-candidate configuration produced the best measured reranking trade-off: it preserved most of the MRR@10 improvement from the 50-candidate setup, improved Recall@5, and cut mean reranking latency from ~3.7 s to ~0.74 s.

**Final retrieval decision:**

```text
Default / fast mode:
Dense + BM25 -> RRF -> top K

Optional / quality mode:
Dense + BM25 -> RRF -> top 10 candidates -> Cross-Encoder -> top K
```

Universal cross-encoder reranking remains a **NO-GO as the default path**. The 10-candidate reranker is retained as an optional/adaptive stage for cases where additional ranking quality can justify sub-second CPU latency.

See [`benchmarks/V1_1_RESULTS.md`](benchmarks/V1_1_RESULTS.md) for the full ablation and decision.

## Benchmark

The default benchmark is **BEIR SciFact (test)** via `ir_datasets`.

- 5,183 documents
- 300 test queries
- relevance judgments (qrels) for objective retrieval evaluation

For a fast smoke test, `nano-beir/scifact` can also be used.

## Principles

1. **Same corpus, same queries, same conditions.** Change one architectural decision at a time.
2. **From first principles where it matters.** BM25, cosine retrieval, RRF, evaluation metrics, and pipeline orchestration are implemented here.
3. **Models are dependencies; system architecture is ours.** Local pretrained models may provide embeddings or pairwise relevance scores, but the retrieval system around them is implemented in this project.
4. **No paid API required.** Current experiments use public benchmark data and local open-source models.
5. **Benchmark locally.** Canonical benchmark computation and latency measurements run on the same local machine/server, not on GitHub-hosted Actions runners.
6. **Measure before expanding.** New components are added only when they answer a concrete experimental question.

## Quick start — Windows local machine/server

Requirements: Python 3.11+ and PowerShell.

```powershell
git clone https://github.com/AlexiVion/rag-architecture-lab.git
cd rag-architecture-lab
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup-local.ps1
```

Run V1 locally:

```powershell
.\scripts\run-v1-local.ps1
```

Run the V1.1 candidate-depth ablation locally:

```powershell
.\scripts\run-v1-1-local.ps1
```

Generated JSON benchmark results are written to:

```text
benchmarks/results/
```

The first model-backed run downloads the configured open-source models locally. No paid API key is needed.

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

scripts/         Local Windows setup and benchmark runners
tests/           Unit tests for algorithms and pipeline behavior
docs/            Scope, architecture, methodology, and local execution policy
benchmarks/       Recorded experiment summaries and generated JSON results
```

## Reproducibility

Each benchmark result records the dataset, pipeline configuration, K values, model configuration, aggregate metrics, per-query rankings, latency, and runtime environment. Local runs write timestamped JSON artifacts to `benchmarks/results/`.

Canonical experiment summaries also record the local hardware, operating system, Python version, and experiment configuration so latency comparisons remain meaningful.

## Roadmap

- ✅ **V0:** Dense vs. BM25 vs. Hybrid retrieval
- ✅ **V1:** Cross-encoder reranking — canonical local benchmark complete
- ✅ **V1.1:** Candidate-depth efficiency ablation — final retrieval decision complete
- 🧪 **V2:** Generation, context construction, and citations
- **V3:** Trace/observability model and interactive inspection
- **V4:** Web observatory and benchmark visualization
- **Later experiments:** query rewriting, multi-query retrieval, parent-child retrieval, contextual retrieval, adaptive/agentic RAG, GraphRAG

See [`docs/SCOPE.md`](docs/SCOPE.md), [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), [`docs/EXPERIMENTS.md`](docs/EXPERIMENTS.md), and [`docs/LOCAL_EXECUTION.md`](docs/LOCAL_EXECUTION.md).

## Cost

The current experiments run at **$0 paid API cost**. They use public benchmark data and local open-source models. No managed vector database or paid LLM API is required.

## References

- Thakur et al. (2021), **BEIR: A Heterogeneous Benchmark for Zero-shot Evaluation of Information Retrieval Models**
- Wadden et al. (2020), **Fact or Fiction: Verifying Scientific Claims (SciFact)**
- Cormack, Clarke & Buettcher (2009), **Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods**
- Robertson & Zaragoza (2009), **The Probabilistic Relevance Framework: BM25 and Beyond**

## Status

The initial retrieval phase is complete. Hybrid RRF is the default retrieval architecture. A 10-candidate cross-encoder reranker remains available as an optional/adaptive quality mode. The next project phase is **V2: generation, context construction, and citations**.

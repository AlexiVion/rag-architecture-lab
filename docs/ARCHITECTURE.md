# Architecture

## Design goal

RAG Architecture Lab separates reusable retrieval components from the pipelines that compose them. The benchmark runner should not need to know how a retriever works internally.

```text
Public IR benchmark
       |
       +---- corpus ---------------------------+
       |                                       |
       +---- queries ----+                      |
       |                 |                      |
       +---- qrels       |                      |
                         v                      v
                  Benchmark runner        Indexing
                         |                      |
          +--------------+--------------+       |
          |              |              |       |
          v              v              v       |
        Dense          BM25           Hybrid <--+
          |              |              |
          +--------------+--------------+
                         |
                         v
                 Candidate ranking
                         |
                +--------+--------+
                |                 |
                v                 v
          direct top-K       Cross-encoder
                                  |
                                  v
                              reranked top-K
                |                 |
                +--------+--------+
                         |
                         v
             Recall / MRR / nDCG / latency
```

## Component boundaries

### Dataset adapter

Converts an external benchmark into three internal structures:

- `Document`
- `Query`
- query relevance judgments (`qrels`)

The project uses `ir_datasets` only as a benchmark data adapter. It does not provide the retrieval, fusion, reranking orchestration, or evaluation logic used by the lab.

### Embedding provider

The `EmbeddingProvider` protocol turns text into vectors. The default implementation wraps a local Sentence Transformers model.

The project deliberately does **not** train its own embedding model: the experiment is about retrieval-system architecture, not model pretraining.

### Dense retriever

Implemented here:

1. encode documents
2. L2-normalize vectors
3. encode and normalize the query
4. compute cosine similarity as a matrix-vector product
5. select exact top-K results

No vector database is required for the current experiments.

### BM25 retriever

Okapi BM25 is implemented directly using:

- tokenization
- term frequency
- document frequency
- inverse document frequency
- document-length normalization

The index is an in-memory posting list.

### Hybrid retriever

Runs dense and BM25 retrieval independently, collects a candidate set from each and combines rankings with Reciprocal Rank Fusion (RRF).

The default RRF score is:

```text
score(d) = sum(1 / (60 + rank_i(d)))
```

Raw dense and BM25 scores are intentionally not mixed because they live on different scales.

### Reranking stage

V1 adds `RerankingRetriever`, a second-stage wrapper around any first-stage retriever.

Its responsibilities are deliberately narrow:

1. ask the base retriever for a configurable candidate set;
2. resolve those candidate IDs back to document text;
3. score `(query, document)` pairs with a `PairScorer`;
4. sort candidates by the new score;
5. return only the requested final top K.

The default `PairScorer` implementation wraps the pretrained local cross-encoder `cross-encoder/ms-marco-MiniLM-L-6-v2`.

The cross-encoder model itself is an external dependency; the project does not claim to train it. The candidate-stage architecture, orchestration, deterministic ranking behavior, configuration, and evaluation are implemented here.

This stage is intentionally separate from first-stage retrieval. A reranker can only reorder documents already present in its candidate pool; it cannot recover a relevant document the base retriever failed to retrieve.

### Evaluation

The lab implements its own:

- Recall@K
- MRR@K
- nDCG@K

Evaluation consumes the benchmark qrels and each pipeline's ranked list. Query latency is measured around the complete pipeline used for that query, so reranking latency is included when a reranker is enabled.

## Fair-comparison rules

For a benchmark comparison to be valid:

- corpus must be identical
- query set must be identical
- relevance judgments must be identical
- reported K values must be identical
- configuration must be recorded
- indexing time must not be mixed with query latency
- latency comparisons should use the same class of runtime environment

Hybrid retrieval may use a larger internal candidate depth because rank fusion requires candidate lists; that depth is recorded as configuration. Reranking experiments also record their candidate depth and model name.

## Why no high-level RAG framework?

The project is intended to expose retrieval and ranking mechanics. High-level frameworks would make implementation faster but would obscure the exact behavior we want to inspect and compare.

This does not imply those frameworks are bad. They solve a different problem: application orchestration and productivity. This lab is intentionally educational and experimental at the retrieval/ranking layer.

## Current architectural finding

V0 established Hybrid RRF as the strongest quality baseline among the tested first-stage retrievers on SciFact. V1 showed that cross-encoder reranking can improve several ranking metrics, but the tested 50-candidate CPU configuration increased mean latency by roughly 85x.

Therefore reranking is **not currently part of the default path**. V1.1 tests whether reducing candidate depth changes that decision before the project advances to generation and context construction.

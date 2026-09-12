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
                     Rankings
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

V0 uses `ir_datasets` only as a benchmark data adapter. It does not provide retrieval or evaluation logic.

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

No vector database is required for V0.

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

The default V0 RRF score is:

```text
score(d) = sum(1 / (60 + rank_i(d)))
```

Raw dense and BM25 scores are intentionally not mixed because they live on different scales.

### Evaluation

The lab implements its own:

- Recall@K
- MRR@K
- nDCG@K

Evaluation consumes the benchmark qrels and each pipeline's ranked list.

## Fair-comparison rules

For a benchmark comparison to be valid:

- corpus must be identical
- query set must be identical
- relevance judgments must be identical
- reported K values must be identical
- configuration must be recorded
- indexing time must not be mixed with query latency

Hybrid retrieval may use a larger internal candidate depth because rank fusion requires candidate lists; that depth is recorded as configuration.

## Why no RAG framework in V0?

The project is intended to expose retrieval mechanics. High-level frameworks would make implementation faster but would obscure the exact behavior we want to inspect and compare.

This does not imply those frameworks are bad. They solve a different problem: application orchestration and productivity. This lab is intentionally educational and experimental at the retrieval layer.

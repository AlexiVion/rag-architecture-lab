# Experiment Methodology

## Experiment V0.1 — Dense vs. BM25 vs. Hybrid

### Hypothesis

Dense and sparse retrieval will exhibit different failure modes, while RRF-based hybrid retrieval may improve robustness by combining semantic and exact-term evidence. The benchmark decides whether that expectation is true for the selected dataset.

### Default dataset

`beir/scifact/test`

SciFact is small enough to run locally while still providing a real document corpus, test queries and relevance judgments. A smaller `nano-beir/scifact` configuration is used for smoke tests.

### Controlled variables

Keep fixed:

- dataset and query set
- relevance judgments
- K values
- machine/environment for latency comparisons
- embedding model for all dense retrieval in a run

Change:

- retrieval strategy only

### Pipelines

**Dense**

```text
query -> local embedding -> cosine similarity -> top K
```

**BM25**

```text
query -> tokenizer -> BM25 posting-list scoring -> top K
```

**Hybrid**

```text
query -> dense ranking ----+
                           +-> RRF -> top K
query -> BM25 ranking -----+
```

### Metrics

**Recall@K** asks what fraction of the known relevant documents appear in the first K results.

**MRR@K** emphasizes how early the first relevant document appears.

**nDCG@K** rewards placing highly relevant documents near the top and supports graded relevance judgments.

**Query latency** is measured separately from indexing. It is useful for trade-off analysis but should only be compared meaningfully on the same machine under similar conditions.

### Default parameters

- K: 5, 10
- BM25 `k1`: 1.5
- BM25 `b`: 0.75
- Hybrid candidate depth: 100 per component retriever
- RRF constant: 60
- Embedding model: `sentence-transformers/all-MiniLM-L6-v2`

These are starting conditions, not claims of optimality.

### Reproducibility

Every CLI benchmark writes a timestamped JSON result containing:

- dataset ID
- pipeline names
- pipeline configuration
- aggregate metrics
- latency summary
- per-query rankings and metrics
- runtime environment metadata

### Interpretation rules

Do not conclude that an architecture is universally better from one dataset.

A useful V0 conclusion sounds like:

> Under SciFact and this configuration, pipeline A improved metric X while increasing latency Y; pipeline B remained stronger on a particular query class.

An invalid conclusion sounds like:

> Hybrid RAG is the best RAG architecture.

### Next experiment only after Go decision

If V0 is useful, V1 will introduce a reranking stage and test whether improving candidate ordering justifies its additional compute and latency.

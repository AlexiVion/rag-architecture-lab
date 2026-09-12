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

### V0 result

V0 passed its go/no-go review. On the recorded BEIR SciFact run, Hybrid RRF produced the strongest quality metrics, while BM25 remained substantially faster. See [`../benchmarks/V0_RESULTS.md`](../benchmarks/V0_RESULTS.md).

---

## Experiment V1 — Cross-encoder reranking

### What reranking changes

Retrieval and reranking solve different stages of the search problem.

A first-stage retriever must search the whole corpus efficiently. A reranker receives only a much smaller candidate set and can therefore use a more expensive model that reads the query and each candidate document together.

```text
whole corpus
    |
    v
Hybrid retrieval
    |
    | top 50 candidates
    v
Cross-encoder reranker
    |
    v
top K final ranking
```

The cross-encoder does **not** replace retrieval. It cannot practically score every document in the corpus for every query. Its role is to improve the ordering of candidates that the first-stage retriever already found.

### Research question

> **Does reranking Hybrid RRF candidates with a local cross-encoder improve top-K retrieval quality enough to justify its additional latency?**

### Hypothesis

Because a cross-encoder jointly models the query and candidate text, it may distinguish relevance more precisely than the independent embedding and lexical scores used by the first-stage retrievers. We expect ranking metrics such as MRR and nDCG to improve if the relevant documents are already present in the candidate set.

Recall may improve at small K because reranking can move relevant candidates upward, but reranking cannot recover a relevant document that was absent from the candidate pool.

### Controlled variables

Keep fixed:

- BEIR SciFact test corpus and 300 queries
- relevance judgments
- K values: 5 and 10
- Hybrid retrieval configuration from V0
- embedding model: `sentence-transformers/all-MiniLM-L6-v2`
- machine/environment for within-run latency comparison

Change:

- add a reranking stage after Hybrid retrieval

### Compared pipelines

**Hybrid baseline**

```text
Dense + BM25 -> RRF -> top K
```

**Hybrid + reranking**

```text
Dense + BM25 -> RRF -> top 50 candidates
                         |
                         v
            local cross-encoder
                         |
                         v
                       top K
```

### Default reranker

`cross-encoder/ms-marco-MiniLM-L-6-v2`

This is used as an external pretrained model dependency. The experiment does not claim to train the reranker from scratch. The architecture, candidate orchestration, evaluation, and comparison are implemented in this repository.

### Default V1 parameters

- Hybrid candidate depth per component: 100
- RRF constant: 60
- Rerank candidate depth: 50
- Evaluation K: 5, 10
- Paid API usage: none

### Go / No-Go criteria

V1 is useful if it gives a measurable answer to the quality/latency trade-off. A GO does not require reranking to win every metric; it requires the experiment to reveal whether the extra computation creates a meaningful quality benefit under the controlled setup.

Possible next steps after V1 depend on the result:

- if reranking adds useful quality: test candidate depth and/or reranker size
- if gains are marginal: keep the simpler Hybrid pipeline and move to generation/context construction
- if gains are concentrated in specific query types: investigate adaptive reranking rather than applying it universally

### Reproducibility

The V1 benchmark command is:

```bash
raglab benchmark \
  --dataset beir/scifact/test \
  --pipelines hybrid hybrid-rerank \
  --k 5 10 \
  --rerank-candidates 50
```

The generated JSON records aggregate metrics, per-query rankings, latency, model configuration, and runtime environment metadata.

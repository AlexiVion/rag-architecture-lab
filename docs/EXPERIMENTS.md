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

### V1 result

The 50-candidate reranker improved most ranking metrics over Hybrid RRF, including MRR@10 (0.6484 -> 0.6615), nDCG@10 (0.6865 -> 0.6944), and Recall@10 (0.8179 -> 0.8272). However, mean query latency increased from 45.91 ms to 3896.99 ms on the recorded CPU runner, roughly 84.9x.

**Architecture decision:** NO-GO for this exact 50-candidate CPU configuration as the default retrieval path.

**Research decision:** GO for one targeted efficiency ablation before deciding whether reranking stays in the architecture.

See [`../benchmarks/V1_RESULTS.md`](../benchmarks/V1_RESULTS.md) for the full table and interpretation.

---

## Experiment V1.1 — Reranking candidate-depth ablation

### Research question

> **Can a smaller reranking candidate set preserve most of V1's ranking improvement while materially reducing latency?**

### Why candidate depth matters

Cross-encoder cost scales approximately with the number of query-document pairs that must be scored. V1 reranked 50 candidates for each query and produced useful but modest quality gains at several seconds of CPU latency.

Reducing the candidate pool changes two things at once:

1. fewer query-document pairs are scored, so reranking should be faster;
2. documents outside the candidate pool can no longer be promoted into the final top K.

This creates a direct quality/latency frontier rather than a single yes/no reranking result.

### Candidate depths

V1.1 tests:

- **10 candidates** — cheapest configuration; can reorder the existing first-stage top 10 but cannot promote ranks 11+ into the final top 10.
- **20 candidates** — intermediate configuration; can promote documents from ranks 11–20 while requiring substantially fewer pair scores than V1's 50-candidate setup.
- **50 candidates** — V1 reference point; results are already recorded and do not need to be recomputed for the main conclusion.

### Controlled variables

Keep fixed:

- dataset: `beir/scifact/test`
- 5,183 documents / 300 test queries
- K values: 5 and 10
- Hybrid RRF configuration
- dense model: `sentence-transformers/all-MiniLM-L6-v2`
- reranker: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- all other retrieval parameters

Change:

- rerank candidate depth only

### Evaluation

For each candidate depth, compare:

- MRR@5 and MRR@10
- nDCG@5 and nDCG@10
- Recall@5 and Recall@10
- mean query latency
- p95 query latency

The main decision is not simply which candidate depth has the highest quality. We want the smallest candidate pool that captures a meaningful fraction of V1's ranking gain without inheriting its extreme latency penalty.

### Decision rule

After V1.1:

- if 10 or 20 candidates retain most of the ranking gain with a large latency reduction, keep reranking as an optional or adaptive stage;
- if latency remains disproportionate to quality gains, remove reranking from the default path and move to V2 generation/context construction;
- do not increase model complexity again until the efficiency question is resolved.

### Reproducibility

Example commands:

```bash
raglab benchmark \
  --dataset beir/scifact/test \
  --pipelines hybrid hybrid-rerank \
  --k 5 10 \
  --rerank-candidates 10

raglab benchmark \
  --dataset beir/scifact/test \
  --pipelines hybrid hybrid-rerank \
  --k 5 10 \
  --rerank-candidates 20
```

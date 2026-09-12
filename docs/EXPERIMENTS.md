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

V0 passed its go/no-go review. On the recorded BEIR SciFact run, Hybrid RRF produced the strongest quality metrics. See [`../benchmarks/V0_RESULTS.md`](../benchmarks/V0_RESULTS.md).

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
- canonical local machine for latency comparison

Change:

- add a reranking stage after Hybrid retrieval

### Default reranker

`cross-encoder/ms-marco-MiniLM-L-6-v2`

This is used as an external pretrained model dependency. The experiment does not claim to train the reranker from scratch. The architecture, candidate orchestration, evaluation, and comparison are implemented in this repository.

### Canonical local environment

- CPU: AMD Ryzen 7 5700U with Radeon Graphics
- 8 cores / 16 logical processors
- RAM: ~15.3 GiB
- Windows 11 64-bit
- Python 3.11.9

### V1 canonical result

The 50-candidate reranker improved most ranking metrics over Hybrid RRF, including MRR@10 (0.6484 -> 0.6615), nDCG@10 (0.6865 -> 0.6944), and Recall@10 (0.8179 -> 0.8272). Mean query latency increased from 34.53 ms to 3706.43 ms on the canonical local machine, roughly 107.3x.

**Architecture decision:** NO-GO for this exact 50-candidate CPU configuration as the default retrieval path.

**Research decision:** GO for one candidate-depth efficiency ablation.

See [`../benchmarks/V1_RESULTS.md`](../benchmarks/V1_RESULTS.md) for the full canonical table and interpretation.

---

## Experiment V1.1 — Reranking candidate-depth ablation

### Research question

> **Can a smaller reranking candidate set preserve most of V1's ranking improvement while materially reducing latency?**

### Candidate depths

V1.1 tests 10 and 20 candidates against matched Hybrid baselines, with the V1 50-candidate configuration as the reference point.

### Controlled variables

Keep fixed:

- dataset: `beir/scifact/test`
- 5,183 documents / 300 test queries
- K values: 5 and 10
- Hybrid RRF configuration
- dense model: `sentence-transformers/all-MiniLM-L6-v2`
- reranker: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- canonical local machine
- all other retrieval parameters

Change:

- rerank candidate depth only

### Canonical V1.1 results

**10 candidates**

- MRR@10: 0.6484 -> 0.6600
- nDCG@10: 0.6865 -> 0.6914
- Recall@5: 0.7571 -> 0.7660
- Recall@10: 0.8179 -> 0.8179
- mean latency: 30.71 ms -> 744.11 ms (~24.2x)
- p95 latency: 45.65 ms -> 893.12 ms

**20 candidates**

- MRR@10: 0.6484 -> 0.6618
- nDCG@10: 0.6865 -> 0.6926
- Recall@5: 0.7571 -> 0.7389
- Recall@10: 0.8179 -> 0.8211
- mean latency: 38.32 ms -> 1634.30 ms (~42.6x)
- p95 latency: 61.89 ms -> 1887.84 ms

**50-candidate reference from V1**

- MRR@10: 0.6615
- nDCG@10: 0.6944
- Recall@5: 0.7449
- Recall@10: 0.8272
- mean latency: 3706.43 ms
- p95 latency: 4184.39 ms

### Interpretation

The 10-candidate configuration retained most of the MRR improvement observed at 50 candidates while reducing reranking latency by roughly 80%. It also improved Recall@5 instead of reducing it.

The 20-candidate configuration slightly improved MRR@10 and Recall@10 relative to 10 candidates, but more than doubled mean latency and reduced Recall@5 below the Hybrid baseline. It therefore did not establish a clearly better trade-off.

The experiments demonstrate that candidate depth is a real architectural control knob: increasing it changes both quality and compute, and more candidates do not improve every metric monotonically.

### Final retrieval decision

**Default architecture:** Hybrid RRF without cross-encoder reranking.

```text
Dense + BM25 -> RRF -> top K
```

**Optional quality mode:** Hybrid RRF followed by a 10-candidate cross-encoder reranker.

```text
Dense + BM25 -> RRF -> top 10 candidates -> Cross-Encoder -> top K
```

Universal cross-encoder reranking is a NO-GO as the default CPU path. The 10-candidate configuration is retained as an optional/adaptive stage where additional ranking quality can justify approximately 0.7 seconds of local CPU latency.

See [`../benchmarks/V1_1_RESULTS.md`](../benchmarks/V1_1_RESULTS.md) for the full tables, deltas, and decision.

### Next phase

V1.1 closes the initial retrieval/reranking phase. The project moves next to **V2: generation, context construction, and citations**.

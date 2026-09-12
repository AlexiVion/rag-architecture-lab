# V0 Results — BEIR SciFact

## Experiment

Research question:

> **How do dense, sparse, and hybrid retrieval strategies perform under identical benchmark conditions?**

Command:

```bash
raglab benchmark --dataset beir/scifact/test --pipelines bm25 dense hybrid --k 5 10
```

Environment used for the recorded run:

- Dataset: `beir/scifact/test`
- Documents: 5,183
- Queries: 300
- Dense embedding model: `sentence-transformers/all-MiniLM-L6-v2`
- BM25: `k1=1.5`, `b=0.75`
- Hybrid candidate depth: 100 per component retriever
- RRF constant: 60
- Python: 3.11
- Runner: GitHub Actions, Ubuntu 24.04
- Paid APIs: none

## Results

| Pipeline | MRR@5 | MRR@10 | nDCG@5 | nDCG@10 | Recall@5 | Recall@10 | Mean latency | p95 latency |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BM25 | 0.6247 | 0.6328 | 0.6431 | 0.6647 | 0.7243 | 0.7849 | 7.52 ms | 14.10 ms |
| Dense | 0.5997 | 0.6047 | 0.6293 | 0.6451 | 0.7379 | 0.7833 | 26.17 ms | 43.88 ms |
| **Hybrid RRF** | **0.6407** | **0.6484** | **0.6653** | **0.6865** | **0.7571** | **0.8179** | 51.86 ms | 116.67 ms |

## What the first experiment tells us

Under this dataset and configuration, **Hybrid RRF produced the strongest ranking and recall metrics**, but at higher query latency.

Compared with the best single-retriever result for each metric, Hybrid improved:

- Recall@10 by **0.0330 absolute** (~4.2% relative)
- nDCG@10 by **0.0218 absolute** (~3.3% relative)
- MRR@10 by **0.0156 absolute** (~2.5% relative)
- Recall@5 by **0.0192 absolute** (~2.6% relative)

The single retrievers also show a useful trade-off:

- **BM25** ranked the first relevant result better overall than Dense on this benchmark (MRR@10 0.6328 vs. 0.6047) and was much faster.
- **Dense** achieved slightly higher Recall@5 than BM25 (0.7379 vs. 0.7243), despite slightly lower Recall@10.
- **Hybrid** combined complementary evidence from both systems and improved all reported quality metrics, while roughly doubling mean query latency relative to Dense in this implementation.

## Interpretation limits

These results do **not** prove that Hybrid RAG is universally superior. They establish only that, on BEIR SciFact with this embedding model, BM25 configuration, RRF configuration, and implementation, hybrid retrieval performed better on the reported metrics.

Latency values are environment-dependent and should only be compared within the same run conditions. Indexing time is excluded from query latency.

## Go / No-Go

**Decision: GO.**

V0 met the project criteria:

1. Dense, BM25, and Hybrid retrieval ran against the same corpus and queries.
2. Objective qrels-based metrics were produced.
3. The pipelines exposed measurable quality/latency trade-offs.
4. The result is interpretable without claiming a universally best architecture.
5. The experiment ran without paid APIs or cloud services beyond the free CI runner used to reproduce the test.

The next justified experiment is **V1: reranking**, where we will test whether reranking a larger candidate set improves top-K quality enough to justify its additional compute and latency.

# V1 Results — Cross-Encoder Reranking

## Experiment

Research question:

> **Does reranking Hybrid RRF candidates with a local cross-encoder improve top-K retrieval quality enough to justify its additional latency?**

Command:

```bash
raglab benchmark \
  --dataset beir/scifact/test \
  --pipelines hybrid hybrid-rerank \
  --k 5 10 \
  --rerank-candidates 50
```

Recorded environment:

- Dataset: `beir/scifact/test`
- Documents: 5,183
- Queries: 300
- First-stage retriever: Hybrid RRF
- Dense embedding model: `sentence-transformers/all-MiniLM-L6-v2`
- Reranker: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- Hybrid candidate depth: 100 per component retriever
- RRF constant: 60
- Rerank candidate depth: 50
- Python: 3.11
- Runner: GitHub Actions, Ubuntu 24.04
- Paid APIs: none

## Results

| Pipeline | MRR@5 | MRR@10 | nDCG@5 | nDCG@10 | Recall@5 | Recall@10 | Mean latency | p95 latency |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Hybrid RRF | 0.6407 | 0.6484 | 0.6653 | 0.6865 | **0.7571** | 0.8179 | **45.91 ms** | **106.95 ms** |
| Hybrid + Cross-Encoder | **0.6521** | **0.6615** | **0.6665** | **0.6944** | 0.7449 | **0.8272** | 3896.99 ms | 4335.35 ms |

## Delta from reranking

Compared with the Hybrid baseline, the cross-encoder reranker changed the aggregate metrics by:

- MRR@10: **+0.0131 absolute** (~2.0% relative)
- MRR@5: **+0.0114 absolute** (~1.8% relative)
- nDCG@10: **+0.0079 absolute** (~1.2% relative)
- nDCG@5: **+0.0012 absolute** (~0.2% relative)
- Recall@10: **+0.0093 absolute** (~1.1% relative)
- Recall@5: **-0.0122 absolute** (~1.6% relative decrease)

Mean query latency increased from **45.91 ms to 3896.99 ms**, or roughly **84.9x**. p95 latency increased from **106.95 ms to 4335.35 ms**, roughly **40.5x**.

## Interpretation

The experiment demonstrates that the reranker is doing real work: it improved MRR@5, MRR@10, nDCG@5, nDCG@10, and Recall@10. In other words, jointly scoring the query and candidate document produced a modest improvement in final ranking quality over Hybrid RRF alone.

However, the quality gain is not free. Under the recorded CPU environment, reranking 50 candidates added several seconds of latency per query. The measured quality improvement is too small to justify making this exact configuration the default retrieval path.

Recall@5 also decreased. This is possible because reranking changes ordering: documents that the cross-encoder considers more relevant can displace other qrel-relevant documents from the first five positions even while MRR, nDCG, and Recall@10 improve.

## Decision

### Architectural adoption: NO-GO for the current configuration

**Do not adopt 50-candidate cross-encoder reranking as the default pipeline under these CPU conditions.**

The approximately 85x increase in mean latency is disproportionate to the measured quality gain.

### Research direction: GO for one targeted efficiency experiment

The result is still informative enough to justify a small follow-up before abandoning reranking entirely. The next experiment should test whether a **smaller candidate depth and/or faster reranker** preserves most of the ranking gain at substantially lower latency.

A useful next step is a candidate-depth ablation (for example 10 vs. 20 vs. 50 candidates) before moving on to generation.

## What V1 establishes

1. A second-stage cross-encoder can improve ranking quality over the V0 Hybrid RRF baseline on SciFact.
2. More sophisticated ranking does not automatically mean a better system: latency can dominate the trade-off.
3. Reranking cannot be evaluated only on quality metrics; compute and latency are part of the architecture decision.
4. The correct next move is optimization/ablation, not automatically adding more model complexity.

## Interpretation limits

These results are specific to BEIR SciFact, this embedding model, this cross-encoder, candidate depth 50, and the recorded CPU runner. They do not establish that cross-encoder reranking is universally too slow or universally beneficial.

GPU inference, batching, smaller candidate sets, different rerankers, quantization, or production-serving optimizations could materially change the latency trade-off.

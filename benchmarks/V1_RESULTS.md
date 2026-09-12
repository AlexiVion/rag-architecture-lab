# V1 Results — Cross-Encoder Reranking

> **Status: preliminary reference run.**
>
> This result was produced on a GitHub-hosted Ubuntu runner before the project switched to a local-execution policy. It is useful as an initial reference, but it is **not the canonical latency benchmark**. V1 must be reproduced on the local Windows machine/server before its final architectural decision is locked.

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

Recorded preliminary environment:

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
- Runner: GitHub-hosted Ubuntu 24.04
- Paid APIs: none

## Preliminary results

| Pipeline | MRR@5 | MRR@10 | nDCG@5 | nDCG@10 | Recall@5 | Recall@10 | Mean latency | p95 latency |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Hybrid RRF | 0.6407 | 0.6484 | 0.6653 | 0.6865 | **0.7571** | 0.8179 | **45.91 ms** | **106.95 ms** |
| Hybrid + Cross-Encoder | **0.6521** | **0.6615** | **0.6665** | **0.6944** | 0.7449 | **0.8272** | 3896.99 ms | 4335.35 ms |

## Preliminary delta from reranking

Compared with the Hybrid baseline, the cross-encoder reranker changed the aggregate metrics by:

- MRR@10: **+0.0131 absolute** (~2.0% relative)
- MRR@5: **+0.0114 absolute** (~1.8% relative)
- nDCG@10: **+0.0079 absolute** (~1.2% relative)
- nDCG@5: **+0.0012 absolute** (~0.2% relative)
- Recall@10: **+0.0093 absolute** (~1.1% relative)
- Recall@5: **-0.0122 absolute** (~1.6% relative decrease)

On that runner, mean query latency increased from **45.91 ms to 3896.99 ms**, roughly **84.9x**. p95 latency increased from **106.95 ms to 4335.35 ms**, roughly **40.5x**.

## Interpretation

The preliminary run suggests that the reranker is doing real work: it improved MRR@5, MRR@10, nDCG@5, nDCG@10, and Recall@10. Jointly scoring the query and candidate document therefore appears capable of improving final ranking quality over Hybrid RRF alone.

However, latency is hardware- and runtime-dependent. Because the recorded latency came from a GitHub-hosted runner, the project will not use it as the final basis for an architectural decision.

Recall@5 decreased in the preliminary run. This is possible because reranking changes ordering: documents that the cross-encoder considers more relevant can displace other qrel-relevant documents from the first five positions even while MRR, nDCG, and Recall@10 improve.

## Current decision status

**Pending local reproduction.**

The initial cloud result makes candidate-depth efficiency worth testing, but the final GO/NO-GO decision will be based on local-server runs under a controlled machine environment.

Run locally with:

```powershell
.\scripts\run-v1-local.ps1
```

Then continue with the candidate-depth ablation:

```powershell
.\scripts\run-v1-1-local.ps1
```

See [`../docs/LOCAL_EXECUTION.md`](../docs/LOCAL_EXECUTION.md) for the local benchmark policy and workflow.

## Interpretation limits

These preliminary results are specific to BEIR SciFact, this embedding model, this cross-encoder, candidate depth 50, and the recorded GitHub-hosted CPU environment. They do not establish that cross-encoder reranking is universally too slow or universally beneficial.

GPU inference, batching, smaller candidate sets, different rerankers, quantization, or production-serving optimizations could materially change the latency trade-off.

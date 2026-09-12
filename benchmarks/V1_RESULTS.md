# V1 Results — Cross-Encoder Reranking

> **Status: canonical local benchmark.**
>
> V1 was reproduced on the project’s designated local Windows machine. The quality and latency values below are the canonical V1 reference for this repository.

## Experiment

Research question:

> **Does reranking Hybrid RRF candidates with a local cross-encoder improve top-K retrieval quality enough to justify its additional latency?**

Command:

```powershell
.\scripts\run-v1-local.ps1
```

Equivalent benchmark command:

```text
raglab benchmark --dataset beir/scifact/test --pipelines hybrid hybrid-rerank --k 5 10 --rerank-candidates 50
```

## Canonical environment

- Dataset: `beir/scifact/test`
- Documents: 5,183
- Queries: 300
- First-stage retriever: Hybrid RRF
- Dense embedding model: `sentence-transformers/all-MiniLM-L6-v2`
- Reranker: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- Hybrid candidate depth: 100 per component retriever
- RRF constant: 60
- Rerank candidate depth: 50
- Python: 3.11.9
- CPU: AMD Ryzen 7 5700U with Radeon Graphics
- CPU cores / logical processors: 8 / 16
- RAM: 16,469,520,384 bytes (~15.3 GiB)
- OS: Microsoft Windows 11, version 10.0.26200, 64-bit
- Paid APIs: none

Generated result artifact:

```text
benchmarks/results/beir_scifact_test_20260912T193618Z.json
```

## Canonical results

| Pipeline | MRR@5 | MRR@10 | nDCG@5 | nDCG@10 | Recall@5 | Recall@10 | Mean latency | p95 latency |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Hybrid RRF | 0.6407 | 0.6484 | 0.6653 | 0.6865 | **0.7571** | 0.8179 | **34.53 ms** | **53.09 ms** |
| Hybrid + Cross-Encoder | **0.6521** | **0.6615** | **0.6665** | **0.6944** | 0.7449 | **0.8272** | 3706.43 ms | 4184.39 ms |

## Delta from reranking

Compared with the Hybrid baseline, the 50-candidate cross-encoder reranker changed aggregate retrieval quality by:

- MRR@10: **+0.0131 absolute** (~2.0% relative)
- MRR@5: **+0.0114 absolute** (~1.8% relative)
- nDCG@10: **+0.0079 absolute** (~1.2% relative)
- nDCG@5: **+0.0012 absolute** (~0.2% relative)
- Recall@10: **+0.0093 absolute** (~1.1% relative)
- Recall@5: **-0.0122 absolute** (~1.6% relative decrease)

Mean query latency increased from **34.53 ms to 3706.43 ms**, roughly **107.3x**. p95 latency increased from **53.09 ms to 4184.39 ms**, roughly **78.8x**.

## Interpretation

The reranker is clearly doing real work. Joint query-document scoring improves MRR@5, MRR@10, nDCG@5, nDCG@10, and Recall@10 over the Hybrid RRF baseline on this benchmark.

However, the gain is modest relative to its CPU cost. On the canonical local machine, reranking 50 candidates increases mean query latency from tens of milliseconds to several seconds. For an interactive retrieval path, that trade-off is not attractive in this configuration.

Recall@5 decreases even while ranking metrics and Recall@10 improve. This is consistent with reranking changing the order of candidates: some qrel-relevant documents are displaced outside the first five positions while the first relevant result and broader top-10 ordering improve.

## V1 decision

### Architectural adoption: NO-GO for the 50-candidate configuration

Do **not** make 50-candidate cross-encoder reranking the default retrieval path on the canonical CPU environment.

The measured quality gain does not justify the roughly 107x increase in mean query latency.

### Research direction: GO for one small efficiency ablation

Reranking is not rejected as a technique. V1 shows that it improves ranking quality, so one focused follow-up is justified: test whether candidate depths **10** and **20** preserve most of the gain while materially reducing latency.

That experiment is V1.1. After it, the project should either select an efficient reranking configuration or move on to V2 generation/context construction without further reranking optimization.

## What V1 establishes

1. Second-stage cross-encoder reranking can improve Hybrid RRF ranking quality on SciFact.
2. More sophisticated ranking is not automatically a better system architecture.
3. Latency and compute are first-class evaluation dimensions, not afterthoughts.
4. Candidate depth is now the most justified variable to ablate.

## Interpretation limits

These results are specific to BEIR SciFact, the selected embedding model, the selected cross-encoder, candidate depth 50, and the canonical local CPU environment.

They do not establish that cross-encoder reranking is universally too slow or universally beneficial. GPU inference, batching, smaller candidate sets, different rerankers, quantization, or production-serving optimizations could materially change the trade-off.

See [`../docs/LOCAL_EXECUTION.md`](../docs/LOCAL_EXECUTION.md) for the benchmark execution policy.

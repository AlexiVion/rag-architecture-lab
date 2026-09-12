# V1.1 Results — Reranking Candidate-Depth Ablation

## Research question

> **Can a smaller reranking candidate set preserve most of V1's ranking improvement while materially reducing latency?**

V1.1 keeps the same BEIR SciFact corpus, Hybrid RRF first-stage retriever, local embedding model, and cross-encoder reranker used in V1. Only the number of candidates sent to the cross-encoder changes.

## Canonical local environment

- CPU: AMD Ryzen 7 5700U with Radeon Graphics
- 8 cores / 16 logical processors
- RAM: 16,469,520,384 bytes (~15.3 GiB)
- OS: Windows 11 64-bit, version 10.0.26200
- Python: 3.11.9
- Dataset: `beir/scifact/test`
- Documents: 5,183
- Queries: 300
- Dense model: `sentence-transformers/all-MiniLM-L6-v2`
- Reranker: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- Paid APIs: none

## Candidate depth 10

Matched local comparison:

| Pipeline | MRR@10 | MRR@5 | nDCG@10 | nDCG@5 | Recall@10 | Recall@5 | Mean latency | p95 latency |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Hybrid RRF | 0.6484 | 0.6407 | 0.6865 | 0.6653 | 0.8179 | 0.7571 | **30.71 ms** | **45.65 ms** |
| Hybrid + reranker (10) | **0.6600** | **0.6543** | **0.6914** | **0.6732** | 0.8179 | **0.7660** | 744.11 ms | 893.12 ms |

Delta versus the matched Hybrid baseline:

- MRR@10: +0.0116 absolute (~1.8% relative)
- MRR@5: +0.0136 absolute (~2.1% relative)
- nDCG@10: +0.0049 absolute (~0.7% relative)
- nDCG@5: +0.0079 absolute (~1.2% relative)
- Recall@10: unchanged
- Recall@5: +0.0089 absolute (~1.2% relative)
- Mean latency: 30.71 ms -> 744.11 ms (~24.2x)
- p95 latency: 45.65 ms -> 893.12 ms (~19.6x)

## Candidate depth 20

Matched local comparison:

| Pipeline | MRR@10 | MRR@5 | nDCG@10 | nDCG@5 | Recall@10 | Recall@5 | Mean latency | p95 latency |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Hybrid RRF | 0.6484 | 0.6407 | 0.6865 | 0.6653 | 0.8179 | **0.7571** | **38.32 ms** | **61.89 ms** |
| Hybrid + reranker (20) | **0.6618** | **0.6518** | **0.6926** | 0.6651 | **0.8211** | 0.7389 | 1634.30 ms | 1887.84 ms |

Delta versus the matched Hybrid baseline:

- MRR@10: +0.0134 absolute (~2.1% relative)
- MRR@5: +0.0111 absolute (~1.7% relative)
- nDCG@10: +0.0061 absolute (~0.9% relative)
- nDCG@5: -0.0002 absolute (effectively unchanged)
- Recall@10: +0.0032 absolute (~0.4% relative)
- Recall@5: -0.0182 absolute (~2.4% relative decrease)
- Mean latency: 38.32 ms -> 1634.30 ms (~42.6x)
- p95 latency: 61.89 ms -> 1887.84 ms (~30.5x)

## Reference: candidate depth 50 from V1

| Pipeline | MRR@10 | nDCG@10 | Recall@5 | Recall@10 | Mean latency | p95 latency |
|---|---:|---:|---:|---:|---:|---:|
| Hybrid RRF | 0.6484 | 0.6865 | **0.7571** | 0.8179 | **34.53 ms** | **53.09 ms** |
| Hybrid + reranker (50) | **0.6615** | **0.6944** | 0.7449 | **0.8272** | 3706.43 ms | 4184.39 ms |

## Interpretation

Reducing candidate depth dramatically lowered the cost of reranking, but even the 10-candidate configuration remained much slower than the Hybrid baseline.

The 10-candidate configuration is the most attractive reranking point measured so far. It preserved most of the MRR@10 improvement seen at 50 candidates, improved Recall@5 instead of reducing it, and cut mean reranking latency from 3.7 seconds to about 0.74 seconds.

The 20-candidate configuration did not establish a clearly better trade-off. It achieved the best MRR@10 of the tested reranking depths, but its mean latency rose to about 1.63 seconds and Recall@5 fell below both the Hybrid baseline and the 10-candidate configuration.

Candidate depth 50 delivered the strongest nDCG@10 and Recall@10 among the reranked variants, but its roughly 3.7-second mean latency makes it unsuitable as the default path on the canonical CPU environment.

## Decision

### Default architecture: NO-GO for universal cross-encoder reranking

The default retrieval path remains **Hybrid RRF without cross-encoder reranking**. Its approximately 30–40 ms mean query latency is disproportionately faster than every reranking configuration for relatively small quality differences.

### Optional architecture: GO for 10-candidate reranking as a quality mode

The 10-candidate reranker is retained as an **optional / adaptive second-stage mode**, not as the default. It is the best measured quality/latency compromise among the reranking configurations tested here.

This creates two useful operating modes:

```text
Fast/default mode:
Dense + BM25 -> RRF -> top K

Quality/optional mode:
Dense + BM25 -> RRF -> top 10 candidates -> Cross-Encoder -> top K
```

A future adaptive policy may decide when the extra ~0.7 s is justified rather than applying reranking to every query.

## What V1.1 establishes

1. Cross-encoder reranking provides real ranking improvements on SciFact.
2. Candidate depth materially controls latency.
3. More candidates do not monotonically improve every metric.
4. 10 candidates produced the best measured reranking trade-off on the canonical CPU environment.
5. Universal reranking is not justified as the default path; optional/adaptive reranking remains architecturally interesting.

## Next step

V1.1 closes the initial retrieval/reranking phase. The project can now move to **V2: generation, context construction, and citations**, while keeping the 10-candidate reranker available as an optional retrieval mode.

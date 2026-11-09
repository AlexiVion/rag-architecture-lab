# RET-FUSION-01 — SciFact train weighted-RRF comparison (2026-11-04)

**Status:** measured locally; exploratory development-set decision. This report is based on two Windows PowerShell outputs from the maintainer. The per-query JSON and bootstrap output remain local and were not independently re-executed here.

- Source commit for retrieval run: `9b88414`.
- Source commit for offline paired analysis: `f4b1c42`.
- `beir/scifact/train`: **809 evaluable queries**.
- 55 tests passed before retrieval; **62 tests passed** before paired offline analysis.
- Raw local input: `benchmarks/results/RET_FUSION_beir_scifact_train_20261104T134203Z.json`.
- Raw local paired analysis: `benchmarks/results/RET_FUSION_beir_scifact_train_20261104T134203Z_PAIRED_ANALYSIS.json`.
- No Qwen model, cross-encoder or paid API was used.

## Mean retrieval metrics

| Pipeline | MRR@10 | nDCG@10 | Recall@5 | Recall@10 | Mean ms | p95 ms |
|---|---:|---:|---:|---:|---:|---:|
| BM25 | 0.6380 | 0.6701 | 0.7223 | 0.7894 | 10.17 | 19.00 |
| Dense | 0.6261 | 0.6602 | 0.7347 | 0.7856 | 19.00 | 26.51 |
| Hybrid RRF 1:1 | **0.6582** | 0.6927 | **0.7574** | 0.8168 | **35.41** | **52.20** |
| Weighted RRF 1.5:1 | 0.6567 | 0.6908 | 0.7505 | 0.8147 | 36.23 | 54.24 |
| Weighted RRF 2:1 | **0.6596** | **0.6938** | 0.7490 | **0.8205** | 36.64 | 54.88 |
| Weighted RRF 3:1 | 0.6564 | 0.6896 | 0.7487 | 0.8136 | 36.03 | 54.19 |

## Paired-query changes vs original Hybrid RRF

Primary practical signal: **Recall@5**, matching the existing five-source generation context. This was prioritized during interpretation, **not preregistered as a confirmatory primary metric before the experiment**.

| Dense weight | Mean delta Recall@5 | Exploratory bootstrap 95% CI | Query wins | Losses | Ties |
|---|---:|---|---:|---:|---:|
| 1.5 | −0.00690 | [−0.01679, +0.00227] | 7 | 14 | 788 |
| 2.0 | −0.00845 | [−0.01895, +0.00237] | 10 | 15 | 784 |
| 3.0 | −0.00876 | [−0.02318, +0.00484] | 17 | 23 | 769 |

The intervals include zero. They do **not** prove equal performance or statistically significant inferiority; they also provide no compelling evidence that increasing Dense weight improves Recall@5. The bootstrap is not corrected for trying multiple weights.

## Architectural decision — retain default Hybrid 1:1

Preserve the existing unweighted fusion algorithm as the **provisional default**, without deleting the weighted variants. Dense 2:1 improved MRR@10 and nDCG@10 only slightly but reduced the observed top-five recall. A change selected from this train-set search would need a frozen independent evaluation.

This outcome **does not resolve** the earlier held-out SciFact claim #1. The relevant document was Dense #5, Hybrid #15, and absent from BM25 top-100. A top-10 reranker would not see it, while top-20/50 could evaluate it. That observation motivates a separate candidate-depth reranking *development* experiment, but is not evidence that reranking succeeds.

## Interpretation and limits

- This is development-set evidence from one local environment, not cross-domain proof.
- Sequential model evaluation may bias latency; no randomized/warmed latency protocol was applied.
- SciFact labels are relevance signals, not a semantic faithfulness benchmark.
- The candidate weights were explored on training data, and practical metric selection was not preregistered.
- No claims about generated answer correctness or citation support follow from these retrieval metrics.

**Next experiment:** train-only matched comparison of Hybrid with candidate-depth-20 cross-encoder reranking, beginning with a small smoke set. See `docs/RERANK_EXPERIMENT.md` and ADR-0002.

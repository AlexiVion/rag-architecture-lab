# RET-FUSION-01 — Full SciFact training run, 2026-11-04

**Observed from a Windows PowerShell run shared by the maintainer.**
Git commit: `9b88414`. The raw per-query JSON remains on the maintainer's machine at `benchmarks/results/RET_FUSION_beir_scifact_train_20261104T134203Z.json`. Values below are copied from the full terminal output and have **not yet been subjected to paired-query uncertainty analysis**.

- Dataset: `beir/scifact/train`, **809 evaluable queries**.
- BM25, Dense, original RRF, and dense-priority weighted RRF were compared at K=5,10 using a shared dataset and local embedding model.
- **55 pytest tests passed** before the study.
- No Qwen generation or cross-encoder reranking occurred.

| Pipeline | MRR@10 | nDCG@10 | Recall@5 | Recall@10 | Mean ms | p95 ms |
|---|---:|---:|---:|---:|---:|---:|
| BM25 | 0.6380 | 0.6701 | 0.7223 | 0.7894 | 10.17 | 19.00 |
| Dense | 0.6261 | 0.6602 | 0.7347 | 0.7856 | 19.00 | 26.51 |
| Hybrid RRF 1:1 | 0.6582 | 0.6927 | **0.7574** | 0.8168 | 35.41 | 52.20 |
| Weighted RRF 1.5:1 | 0.6567 | 0.6908 | 0.7505 | 0.8147 | 36.23 | 54.24 |
| Weighted RRF 2:1 | **0.6596** | **0.6938** | 0.7490 | **0.8205** | 36.64 | 54.88 |
| Weighted RRF 3:1 | 0.6564 | 0.6896 | 0.7487 | 0.8136 | 36.03 | 54.19 |

## Provisional architecture decision

**Retain original Hybrid RRF 1:1.** Our present generation context holds only five documents, so we prioritize `Recall@5` when discussing the practical evidence budget. **This decision criterion was not preregistered before the study**, and therefore the choice is exploratory rather than a confirmatory hypothesis test. All three weighted variants reduced Recall@5; the 2:1 variation's gains in MRR@10, nDCG@10 and Recall@10 were small. No claim of statistical significance is made.

This is a conservative default recommendation on development data, **not yet** a held-out or cross-domain certification. The sequential benchmark's latency figures are not a controlled paired timing study. The full per-query JSON should be analyzed with `scripts/analyze-latest-fusion-local.ps1` to obtain paired differences, bootstrap uncertainty and examples of regressions.

The test-set SciFact query #1 remains a documented failure for the 1:1 baseline: its gold document is Dense #5 and Hybrid #15. It does not justify test-label-driven weight tuning. A separate 20/50-candidate reranking study may be warranted if justified by aggregate quality, latency and local resource constraints.

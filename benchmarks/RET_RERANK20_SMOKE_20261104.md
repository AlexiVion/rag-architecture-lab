# RET-RERANK-20 — SciFact development smoke, 2026-11-04

**Status:** locally executed smoke; provisional negative outcome for the tested reranking configuration.

Source: maintainer's Windows terminal output, commit `de9f452`.
Raw benchmark retained locally at `benchmarks/results/beir_scifact_train_20261104T140133Z.json`.
All **62 unit tests passed** before the smoke.

- SciFact train, first **60** evaluable queries.
- Baseline: original Hybrid BM25+Dense+RRF.
- Candidate: Hybrid plus cross-encoder `cross-encoder/ms-marco-MiniLM-L-6-v2`, pool of 20, outputs top 10 for retrieval metrics.
- Same corpus and query order; local embeddings; no paid APIs or Qwen.
- Embedding indexing took approximately three minutes on the reported host; not part of query latency.

| Metric | Hybrid RRF | Hybrid + rerank 20 |
|---|---:|---:|
| Recall@5 | **0.7750** | 0.6667 |
| Recall@10 | 0.8000 | 0.8000 |
| MRR@10 | **0.5814** | 0.5504 |
| nDCG@10 | **0.6348** | 0.6125 |
| Mean query latency | **36.60 ms** | 1725.90 ms |
| p95 query latency | **53.87 ms** | 1903.11 ms |

Top-five recall decreased **0.1083 absolute (10.83 percentage points)**. Mean query latency increased about **47.2x**. Reranking the top 20 candidates did not improve these 60 queries overall.

## Decision

**NO-GO for immediate adoption of this specific model/candidate depth.** Do not change the default Hybrid retriever, and do not launch a full 809-query rerank study or another Qwen generation run solely to rescue this smoke result.

The 60 queries are a convenience subset, not a randomized held-out test. Statistical uncertainty and individual ranking failures will be inspected from the saved per-query JSON using `scripts/analyze-latest-rerank-local.ps1`. A negative result here does not invalidate reranking with other models or domain configurations.

## Next scientific work

- Check per-query changes, confidence intervals, and which relevant articles were displaced or promoted.
- Inspect whether the MS MARCO cross-encoder is well matched to SciFact scientific claims; do not assume a scientific-domain result from its name.
- Focus next on retrieval calibration and evidence-aware abstention; the earlier V2 generated answer remains uncited and apparently off-topic.

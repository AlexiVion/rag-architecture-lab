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

The 60 queries are a convenience subset, not a randomized held-out test. Offline paired analysis was subsequently completed with 69 tests passing. The **Recall@5 delta was −0.10833**, exploratory paired bootstrap **95% CI [−0.19167, −0.03333]**, with **1 improved, 10 worsened, 49 unchanged** queries. The interval excludes zero but is unadjusted and based on an ordered convenience subset. Other paired metrics were less conclusive (MRR@10 CI [−0.09866,+0.03275], nDCG@10 CI [−0.08363,+0.03708], Recall@10 CI [−0.08333,+0.08333]). This supports the NO-GO for this configuration without invalidating all rerankers. Local full artifact: `benchmarks/results/beir_scifact_train_20261104T140133Z_RERANK_ANALYSIS.json`.

## Next scientific work

- Check per-query changes, confidence intervals, and which relevant articles were displaced or promoted.
- Inspect whether the MS MARCO cross-encoder is well matched to SciFact scientific claims; do not assume a scientific-domain result from its name.
- Focus next on retrieval calibration and evidence-aware abstention; the earlier V2 generated answer remains uncited and apparently off-topic.

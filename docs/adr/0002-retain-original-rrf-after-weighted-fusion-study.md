# ADR-0002 — Retain unweighted RRF as the provisional default

- Status: Accepted as an **exploratory development decision**, not a claim of statistical superiority
- Date: 2026-11-04
- Evidence: `benchmarks/RET_FUSION_TRAIN_20261104.md`
- Scope: SciFact train, local CPU, fixed five-source generation context

## Context

Held-out SciFact query 1 demonstrated that an article ranked fifth by Dense fell to 15th under equal-weight Hybrid RRF and missed the top-five generation context. To avoid optimizing on a single test case, a train-only study compared BM25, Dense, unweighted Hybrid RRF and dense-weighted RRF (1.5, 2.0, 3.0).

In 809 train queries, original RRF produced Recall@5 0.7574. The weighted alternatives produced 0.7505, 0.7490 and 0.7487. All three paired exploratory 95% bootstrap intervals for their Recall@5 changes include zero. Dense 2.0 slightly improved MRR@10, nDCG@10 and Recall@10 but not top-five recall.

## Decision

Keep `HybridRetriever` (1:1 RRF, c=60) as the default, and keep `WeightedHybridRetriever` as an optional research adapter. Do not alter existing benchmark references or treat this as a universal recommendation.

## Rationale

The current RAG pipeline gives the generator five retrieved sources. No dense-heavy alternative showed a convincing gain on that budget in this development experiment. Simplicity and compatibility favor retaining the baseline until independent evidence supports a change.

## Consequences and future tests

- Positive: preserves the established retrieval implementation and transparent result comparisons.
- Negative: held-out SciFact query 1 still misses its labeled evidence in the Hybrid top five.
- Investigate candidate-pool depth (20/50) and reranking on train before a frozen held-out run.
- Future cross-domain and answer-level benchmarks may overturn this decision.
- Exploratory intervals are unadjusted for multiple comparisons; Recall@5 was not originally preregistered as the sole target.

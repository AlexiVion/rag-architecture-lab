# ADR-0003 — Do not promote MS MARCO rerank-20 from SciFact smoke

- Status: **Provisional NO-GO** for the evaluated configuration
- Date: 2026-11-04
- Source: `benchmarks/RET_RERANK20_SMOKE_20261104.md`
- Revisit: after paired-query review or a justified cross-encoder/domain experiment

## Context

The original Hybrid RRF architecture occasionally loses a highly ranked Dense document. SciFact test query #1 had Dense rank 5 and Hybrid rank 15 for its qrel-relevant article. That motivated a **train-only** smoke testing a 20-document cross-encoder candidate pool, not tuning against the test query.

On the first 60 SciFact train queries, original Hybrid delivered Recall@5 **0.7750** with mean query latency **36.60 ms**; Hybrid reranking 20 via `cross-encoder/ms-marco-MiniLM-L-6-v2` delivered Recall@5 **0.6667**, latency **1725.90 ms**. MRR@10 and nDCG@10 also dropped; Recall@10 remained 0.8000.

## Decision

Retain the existing Hybrid RRF baseline; **do not activate this cross-encoder reranker as a default** or scale this configuration to all training queries at present. Keep reranking implementation available for other research and analysis.

## Caveats

- The sample consists of the first 60 training queries, not a random held-out set.
- Paired uncertainty/per-query failures are pending in the saved JSON.
- The MS MARCO ranker may be poorly aligned with SciFact scientific claim relevance; that remains a hypothesis rather than demonstrated root cause.
- This negative result does not show that all cross-encoder models, candidate depths or scientific-domain rerankers are worse.
- Retrieval relevance and cited generated-answer faithfulness are separate quality dimensions.

## Follow-up

Use the **saved JSON** and `scripts/analyze-latest-rerank-local.ps1` to inspect paired Recall@5 losses and regressions without rerunning any models. Continue M1 evidence/abstention policy work independently; do not regard RRF or reranking tweaks as substitutes for semantic support evaluation.

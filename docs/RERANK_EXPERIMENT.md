# RET-RERANK-20 — Candidate depth versus context evidence

## Motivation

SciFact held-out claim 1 showed the qrel-relevant article at Hybrid rank 15 but missing from the final top-five context. A cross-encoder ranking only Hybrid top 10 cannot see it; candidate depth 20 allows it to be considered but **does not guarantee** promotion. Rather than choose depth based on that one test example, evaluate reranking on training queries first.

## Smoke procedure

Run on the local Windows CPU host:

```powershell
.\scripts\run-rerank-depth20-smoke-local.ps1
```

Default smoke is 60 SciFact **train** queries. It compares:
- Same unweighted Hybrid BM25+Dense+RRF baseline.
- Same Hybrid plus local `cross-encoder/ms-marco-MiniLM-L-6-v2` reranking over top 20 candidates.
- Compare Recall@5, MRR@10, nDCG@10 and latency p95, with the same corpus and query selection.

This does *not* run Qwen, generation or an answer-faithfulness metric. It can download a free local cross-encoder and embed the corpus, so initial indexing may take several minutes.

## Scientific gate

This initial set is a **plumbing/feasibility smoke**, not a final ranking of techniques. Full SciFact train and candidate-depth 10/20/50 ablations with uncertainty, source inspection and performance budgets should precede any held-out claim. Reranking is CPU-intensive and must justify latency overhead.

Do not run held-out SciFact test to choose the candidate depth, or claim that a retrieved qrel-relevant article guarantees an answer with valid citations. Use the baseline as the control, and keep original `HybridRetriever` unchanged during experiments.

## Measured local smoke (2026-11-04)

The first 60 SciFact TRAIN queries completed successfully (62 tests passed). Original Hybrid: Recall@5 0.7750, mean query latency 36.60 ms. Hybrid plus MS MARCO reranker at candidate depth 20: Recall@5 0.6667, mean query latency 1725.90 ms. This specific variant has a **provisional NO-GO** for immediate adoption; do not launch a full reranking study before inspecting per-query evidence.

See `benchmarks/RET_RERANK20_SMOKE_20261104.md` and the offline analyzer `scripts/analyze-latest-rerank-local.ps1`. This does not preclude other rerankers or alternative candidate-depth policies. V2 semantic faithfulness remains untested.

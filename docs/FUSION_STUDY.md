# RET-FUSION-01 — Weighted RRF development experiment

The SciFact test query `1` exposed a failure of first-stage RRF: the gold document (31715818) was ranked at **dense #5**, **hybrid #15**, and **not found in BM25 top-100**. A top-10 cross-encoder cannot see it, but a top-20 or top-50 candidate reranker could.

This diagnostic is **not** a reason to tune on SciFact test judgments. Instead, test the hypothesis that increasing the dense contribution in RRF improves *aggregate* retrieval effectiveness on SciFact **train**.

## Procedure

Run from the local Windows repository root:

```powershell
.\scripts\run-fusion-study-local.ps1
```

For a short plumbing smoke (not a statistically meaningful decision):

```powershell
.\scripts\run-fusion-study-local.ps1 -LimitQueries 40
```

The study compares BM25, Dense, legacy Hybrid RRF (1:1) and weighted Hybrid RRF (1.5:1, 2:1, 3:1) at K=5 and K=10, using one shared corpus, embedding model, and query set. It reuses the indexed BM25 and Dense components across variants. It performs **no Qwen generation and no cross-encoder reranking**.

All candidates are *exploratory*; weight choice is not preregistered as a winner. Assess per-query wins/losses, nDCG@10, MRR@10, Recall@5/10 and latency before selecting a single candidate. Do not change defaults in `HybridRetriever` yet.

## Evaluation discipline

- `beir/scifact/train` is development data. Hyperparameters can be compared on train; only a frozen choice should later be checked once on `beir/scifact/test`.
- Experiments run in a fixed sequential order, which may affect latency. A rigorous benchmark must warm and rotate variants in a controlled way.
- Qrels measure the presence of labeled documents, **not** semantic completeness or factual truth. Dense #5 is not proof an LLM will generate a supported claim.
- Weight-only RRF may improve this example while harming aggregate retrieval. Treat a negative result as publishable evidence.
- A 10-candidate reranker can never rerank the gold document for the observed test query under unchanged Hybrid 1:1. A 20+ candidate reranker can, but success is not guaranteed.

Canonical result files under `benchmarks/results` are intentionally ignored until reviewed. Publication requires dataset/model revision, local environment, full per-query analysis and a documented decision.

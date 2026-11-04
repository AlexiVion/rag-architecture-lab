# Retrieval diagnosis — BEIR SciFact query 1

The first real local V2 run completed but generated an uncited, apparently off-topic response. The offline evaluation identified zero of the single labeled relevant document in the top-five context. This is a retrieval metric miss, not definitive proof all retrieved text lacks useful information.

## One-command reproduction on the designated Windows machine

Run PowerShell from repository root:

    .\scripts\diagnose-scifact-q1-local.ps1

This compares BM25, Dense and Hybrid to depth 100 and uses the corpus and gold judgments of BEIR SciFact. It does NOT run Qwen or a cross-encoder. Dense document indexing may consume several minutes of CPU time, and the embedding model may be downloaded if uncached. To run only BM25:

    .\scripts\diagnose-scifact-q1-local.ps1 -BM25Only

JSON is stored locally at benchmarks/results/DIAG_1_*.json, excluded from Git.

## How to interpret the report

- gold_documents shows the labeled supporting/relevant article identity, title and preview; the relevance labels are used ONLY in offline analysis.
- gold_ranks is the observed position within top-100 of each retriever; null means absent at the measured depth, not out of the corpus.
- recall_at_context_k measures the labeled relevant documents that would enter the top-five RAG context.
- rerank_eligibility indicates whether at least one labeled relevant document occurs in the Hybrid top-10, top-20, top-50 or top-100 candidate pools. It does NOT predict a reranker's quality.
- If relevant evidence is absent from top-50, a cross-encoder reranking only 50 candidates cannot add it.
- If BM25 succeeds and Hybrid fails, analyze fusion. If both fail, examine the query, the labeled article, indexing, and held-out retriever alternatives.

Do not tune parameters using test qrels; develop on a validation split, then report held-out evaluation results. Do not equate retrieved qrel matches to factual support or generated answer correctness.

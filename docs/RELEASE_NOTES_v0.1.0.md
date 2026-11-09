# RAG Architecture Lab — v0.1.0 Portfolio Research Preview

A public **CPU-first research laboratory and read-only observatory** for comparing RAG retrieval architectures, tracing evidence and understanding the costs and limits of more complex pipelines.

## Included

- Python 3.11+ first-principles BM25, local dense retrieval, Hybrid Reciprocal Rank Fusion, cross-encoder reranking and composable experimental adapters.
- Benchmark analysis on 5,183 BEIR SciFact documents / 300 queries: MRR@10 BM25 **0.6328**, dense **0.6047**, Hybrid **0.6484**.
- Local CPU reranking trade-offs: with 50 candidates, MRR@10 **0.6615** compared to Hybrid **0.6484**, mean retrieval latency **3706.43 ms** vs **34.53 ms** under the measured V1 conditions; optional top-10 rerank mode.
- Two verified local HotpotQA DEV retrieval studies: graph-first **NO-GO** (BM25 Recall@5 0.8250; graph+BM25 0.7083) and graph-hybrid **INCONCLUSIVE** (Hybrid RRF Recall@5 0.8583; Graph-Hybrid 0.8500), tested on **different DEV cohorts**.
- Three-document deliberately fictional provenance graph with exact source quotations and a **seven-section React/TypeScript/Vite visual observatory**. No LLM is hosted or invoked by the viewer.
- MIT-licensed repository code, reproducibility instructions, scientific limitations and security documentation.

## Not included / explicit constraints

This is **not** the complete [WOW v1.0 research program](https://github.com/AlexiVion/rag-architecture-lab/issues/9), not a hosted SaaS chatbot, not evidence of reliable factual answer generation, and not a claim of superior GraphRAG. M2 generation factual support/abstention remains **NO-GO for automatic publishing**. Ten-model catalog entries remain proposed unless individually measured. Bacteria, Physical AI and new ultratiny-LLM optimization are separate future research, not release claims.

## Explore and reproduce

- [Source](https://github.com/AlexiVion/rag-architecture-lab)
- [Portfolio scope and verification limits](https://github.com/AlexiVion/rag-architecture-lab/blob/main/docs/PORTFOLIO_RELEASE.md)
- [Benchmark catalog](https://github.com/AlexiVion/rag-architecture-lab/blob/main/docs/ARCHITECTURE_CATALOG.md)
- [Local setup](https://github.com/AlexiVion/rag-architecture-lab/blob/main/docs/RELEASE_INSTALLATION.md)

**The live Pages URL must be verified from the deployment result before the announcement is linked.** The release workflow is configured to create this GitHub release only *after* the Pages deploy job has succeeded.

Release reference: [REL-PORTFOLIO-01 #13](https://github.com/AlexiVion/rag-architecture-lab/issues/13).

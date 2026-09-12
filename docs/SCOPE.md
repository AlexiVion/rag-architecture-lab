# V0 Scope

## Objective

Build the smallest credible experiment that can determine whether RAG Architecture Lab deserves to expand into a larger portfolio project.

The V0 research question is:

> **How do dense, sparse, and hybrid retrieval strategies perform under identical benchmark conditions?**

## In scope

- One public benchmark with objective relevance judgments
- Dense retrieval with a local open-source embedding model
- BM25 lexical retrieval implemented in this repository
- Hybrid dense + BM25 retrieval using Reciprocal Rank Fusion
- Recall@K, MRR@K, nDCG@K
- Per-query and aggregate retrieval latency
- Reproducible JSON experiment output
- Unit tests for the algorithms we implement
- A CLI for running the experiment locally

## Explicitly out of scope for V0

- LLM answer generation
- Prompt engineering
- Reranking
- RAG frameworks such as LangChain, LlamaIndex, Haystack or LangGraph
- Vector databases or managed search services
- GraphRAG
- Agents or agent orchestration
- Web UI
- Authentication, billing or multi-tenancy
- Cloud deployment

## Cost constraint

V0 must require **no paid API or cloud infrastructure**. It should run locally using public benchmark data and a local embedding model.

## Go / No-Go decision

V0 is successful if all of the following are true:

1. The three retrieval pipelines run against the same corpus and query set.
2. Metrics are reproducible across repeated runs under the same configuration.
3. The experiment exposes meaningful trade-offs or failure cases worth explaining.
4. The implementation is understandable enough to defend in a technical interview or portfolio review.
5. The result can be documented without pretending that one architecture is universally superior.

If those conditions are not met, the project should be revised or stopped before adding UI, generation, agents, or more retrieval techniques.

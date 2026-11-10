# RAG Architecture Lab — Reference Architecture (v1)

**Status:** Accepted baseline design, 2026-11-04. Research platform, not a hosted SaaS.

## Purpose and boundaries

Build a framework-independent, open-source reference laboratory for *implementing, reproducing, measuring and explaining* RAG architecture trade-offs. No paid API, hosted database, multi-tenant application, authentication or billing is needed for the core. A web explorer is optional presentation software, not the source of truth.

An architecture is a **composition of interchangeable, testable stages**, not a duplicate end-to-end project. The canonical artifacts are source code, experiment specifications, test cases, result files and architecture decision records (ADRs).

## Reference layers

```text
CLI / experiment runner / optional future explorer
                       |
   Dataset adapters -> corpus, queries, qrels, answers
                       |
         Experiment specification + seed
                       |
     Architecture composition (Retriever protocol)
                       |
  lexical  dense  fusion  reranking  query transforms
  parent-child  corrective  routing  graph (future)
                       |
       Context builder -> local generator
                       |
      Citation checking -> answer evaluation
                       |
  Structured traces, metrics, environment, artifacts
                       |
      Benchmark summaries + decision records
```

## Dependency direction

- `core/`: value types and stable protocols. No model/framework imports.
- `datasets/`: adapters to public corpora, labels, and future answer sets. Dataset adapters cannot score retrieval.
- `embeddings/`: local model adapters behind `EmbeddingProvider`.
- `retrieval/`: BM25, dense, hybrid, reranking and reusable retriever wrappers implementing `index(documents)` and `retrieve(query,k)`.
- `architectures/`: independent composition strategies. Reuse existing retrievers instead of copying BM25/dense code. Initial implementations use the current `Retriever` contract.
- `context/`, `generation/`, `citations/`, `rag/`: bounded grounding and answer pipeline. The generator is replaceable.
- `evaluation/`: qrels metrics and separately answer correctness/faithfulness metrics; never conflate citation-label integrity with semantic support.
- `experiments/` (future package): reproducible experiment manifests and orchestration; the existing CLI remains the compatibility layer.
- `benchmarks/`: human-readable canonical results; large generated JSON stays outside git by default.
- `docs/`: methods, architectural limitations and ADRs.

## Stable contracts

1. `Document(id, title, text)`, `Query(id,text)`, `SearchResult(doc_id,score,rank)` stay compatible.
2. `Retriever.index(documents)` builds an index. `Retriever.retrieve(query,k)` returns unique document IDs, scores and 1-based ranks. Wrapped retrievers must return IDs present in the original document collection.
3. A query transformation may change *the retrieval query*, never the ground-truth qrels or original user question.
4. A reranker can only reorder its candidate pool; a parent-child retriever must map child matches back to original parent IDs.
5. Results include precise method/model versions, dataset, code SHA, seed, corpus fingerprint and runtime characteristics before being called *reproduced*. If any field is missing, label the comparison exploratory.
6. Citation syntax and factual support are distinct reports. Generated answer claims are not marked grounded just because they contain valid labels.
7. Quality and latency comparisons require identical query sets, corpus, relevance labels, runtime class and matching warm-up strategy. Retrieval latency excludes indexing and model downloads. End-to-end latency includes generation.
8. Do not turn an unexecuted pipeline or mock-only unit test into an empirical success claim.

## Chosen defaults (subject to new benchmark evidence)

- First-stage: local BM25 + local dense embeddings, fused with RRF (k=60; candidate depth 100).
- Optional second-stage: local cross-encoder over top 10 candidates.
- Top-k context: 5, bounded by context/source budgets.
- Generation: small local Transformers model for smoke tests only; not a quality benchmark winner.
- Execution: Python >=3.11; Windows PowerShell local benchmark commands; no paid keys or cloud benchmarking. Fast deterministic tests may also run on developer machines.
- Scientific independence: no mandatory LangChain, LlamaIndex, LangGraph or managed vector DB.

## Benchmark and publication gates

**Unit contract:** deterministic algorithm tests pass; adapters preserve identity, duplicates and bounds.

**Integration contract:** a real local end-to-end run completes; source mapping and timings are inspected.

**Experimental contract:** baseline and candidate share data/hardware; raw result manifest plus error analysis and uncertainty is retained; publication includes limitations.

**Documentation contract:** reproduction instructions, architecture diagram, evaluation design, conclusions and limitations can be assessed independently of prior development discussions.

## Migration from current repository

Keep `src/raglab/retrieval`, `evaluation`, `rag` and existing V0/V1/V1.1 results as the stable spine. New architecture adapters are additive under `src/raglab/architectures`. Do not move existing paths until tests, documentation and benchmark references are updated. V2 generation remains **implemented but not empirically certified** until the local smoke test and quality benchmark pass.

See [catalog](ARCHITECTURE_CATALOG.md), [experiment protocol](EXPERIMENT_PROTOCOL.md) and [roadmap](ROADMAP.md).

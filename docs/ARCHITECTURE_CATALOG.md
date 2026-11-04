# Architecture and experiment catalog

**Definitions:** `Implemented` = code exists, not necessarily validated on a live model; `Benchmarked` = measured and documented with identified conditions; `Proposed` = design target only. The "code target" is not a performance claim.

| ID | Architecture | Research question | Control / comparison | Primary measures | Status |
|---|---|---|---|---|---|
| RET-00 | Sparse BM25 vs dense vs hybrid RRF | Does hybrid improve retrieval quality? | same SciFact corpus/qrels | Recall, MRR, nDCG, latency | Benchmarked V0 |
| RET-01 | Cross-encoder reranking | Is quality worth cost? | hybrid vs 50 candidates | retrieval metrics, p95 | Benchmarked V1 |
| RET-02 | Candidate depth | Which depth has best trade-off? | hybrid vs 10/20/50 | metrics, latency | Benchmarked V1.1 |
| GEN-00 | Grounded local RAG | Can retrieval feed a local cited response? | hybrid, optional rerank | citation labels, breakdown | Implemented V2, smoke pending |
| GEN-01 | Faithfulness evaluation | Are answer claims actually supported? | common question set, references | support, abstention, factuality | Proposed V2.1 |
| RET-03 | Multi-query | Does query diversification recover missed docs? | hybrid vs deterministic reformulations | Recall@K, latency, per-query wins | Implemented adapter; benchmark pending |
| RET-04 | Parent-child | Do smaller matching units improve answer evidence? | same parent corpus, fixed chunk parameters | parent Recall, evidence coverage | Implemented adapter; benchmark pending |
| RET-05 | Contextual retrieval | Does document-aware chunk augmentation help? | chunk-only vs enriched indexing | Recall@K, noise, latency | Implemented adapter; benchmark pending |
| RET-06 | HyDE | Does a hypothetical answer embedding improve recall? | identical dense model + queries | Recall@K, runtime | Implemented adapter; benchmark pending |
| RET-07 | Corrective RAG | Can evidence checks trigger useful recovery? | fixed judge + fallback policy | recovery, false correction, cost | Implemented adapter; benchmark pending |
| RET-08 | Adaptive routing | Can routing retain quality at lower median cost? | same retrievers, fixed routing policy | weighted metrics, p95, routing errors | Implemented adapter; benchmark pending |
| GEN-02 | Query decomposition | Can multi-hop questions be decomposed? | direct vs decomposed | answer support and task accuracy | Proposed |
| GEN-03 | Self-reflective RAG | Can a critique loop improve response faithfulness? | one pass vs bounded critique | correctness, loops, latency | Proposed |
| AGT-00 | Agentic RAG | When is iterative tool use justified? | bounded tool budget vs one shot | quality, steps, latency | Proposed |
| GRF-00 | Source-provenance graph retrieval (GraphRAG baseline) | When do entity relations help multi-hop retrieval? | graph vs equivalent text baseline | multi-hop accuracy, index cost | 1–2-hop graph prototype + curated fixture implemented; benchmark pending |
| XTR-00 | Cross-domain / multilingual | Do findings generalize beyond English SciFact? | multiple domains and ES/FR/EN | slice-level metrics, failure modes | Proposed |

## Experiment deliverables (mandatory)

Each experiment requires:
1. **Hypothesis:** one falsifiable question; avoid architecture name as the hypothesis.
2. **Implementation:** small composable strategy with dependency-injected models, explicit budgets and tests.
3. **Controlled baseline:** same corpus, queries, relevance labels, top-k and machine.
4. **Dataset eligibility:** relevance labels for retrieval; references/claims for generation; never invent missing ground truth.
5. **Artifacts:** versioned config/seed/model revision, code SHA, environment, query results, summary, error analysis.
6. **Decision:** Go / No-Go / Inconclusive, with observed trade-offs and domain limitations.
7. **Presentation:** a self-contained README section/experiment card/diagram; no screenshots as a substitute for metrics.

## Suggested progression

1. Finish GEN-00 and GEN-01 before describing the repository as a validated *generation* benchmark.
2. RET-03 and RET-04 introduce new retrieval architectures using existing hybrid baselines.
3. RET-05, RET-06, RET-07, RET-08 compare evidence enrichment and recovery/routing.
4. GEN-02, GEN-03 and AGT-00 examine reasoning and control loops after answer-level evaluation is reliable.
5. GRF-00 now has a deterministic curated graph prototype with exact source quotes. The next gate is an independently eligible multi-hop dataset and a matched text-only benchmark; the fixture alone does not pass the performance gate.
6. XTR-00 should be revisited after every major architecture to avoid SciFact overfitting.

## Implementation vs empirical truth

Adapters for RET-03/04/05/06/07/08 are intentionally *infrastructure*. They require explicitly supplied reformulators, chunk configuration, evidence judges or routers; no default language model is quietly substituted. Their presence does not mean these hypotheses were tested or that they outperform Hybrid RRF.

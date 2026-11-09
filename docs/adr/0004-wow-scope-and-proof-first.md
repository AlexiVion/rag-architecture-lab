# ADR 0004: evidence-first WOW release scope, not semantic perfection

**Status:** Accepted as a delivery-plan decision, 2026-11-04.

## Decision

The requested portfolio-quality v1.0 combines scientific evaluation (M2), graph-grounded retrieval (GRF-00), a ten-model **role-separated** research matrix (MOD-10), a read-only web observatory (WEB-01) and professional release operations (REL-01).

We will build a credible observability-focused RAG **research platform**, not a hosted ChatGPT clone. The graphic experience must display authentic, versioned evidence and trace where each result came from.

No arbitrary claim of 100% semantic correctness can be made for open-world RAG. The system must abstain where applicable, measure both unsupported answers and false refusals, and state the applicable benchmark limitations.

GraphRAG must implement actual indexed entities/relations/traversal and document provenance; a diagram of artificial edges is not GraphRAG. Ten model candidates across embedding, reranking, NLI and generation roles **must not** be presented as a ten-LLM same-metric ranking.

Local CPU-only model execution remains the default; public explorer can consume static verified artifacts without requiring a public inference service.

## Consequences

- More independent test and research work before claiming an evaluated v1.0.
- Preserve V0/V1/V1.1 evidence and negative NLI results.
- Keep PR #2 draft until its current oversized changes receive a release review.
- Build a small real fixture and inspectable provenance contract before decorative app features.
- Publish trustworthy failure analysis and model limitations as part of the professional story.

## Source of truth

- [Full release blueprint](../RELEASE_WOW_BLUEPRINT.md)
- [Master issue #9](https://github.com/AlexiVion/rag-architecture-lab/issues/9)

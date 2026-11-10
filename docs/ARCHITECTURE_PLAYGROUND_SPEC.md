# Architecture Playground v1 — research visualization specification

**Status:** Implementation specification, 2026-11-10. This document defines UI behavior; it introduces no new research results.

## Purpose

Teach the observable differences between BM25, Hybrid Reciprocal Rank Fusion (RRF), and Hybrid + Cross-Encoder reranking through a paired, interactive architecture comparison. Preserve the existing three-section editorial observatory and all Python experiment artifacts.

## Information provenance (non-negotiable)

Two information layers are shown **separately**:

1. **Illustrative teaching corpus:** Three entirely fictional question/document groups (plants, penguins, moon phases). The ranks are authored as examples, and relevance labels are illustrative. BM25 and dense lists are authored; Hybrid ranking is deterministically derived by RRF with `k=60`; cross-encoder reordering is scripted, **not model inference**. Labels must say "Illustrative rankings, not SciFact outputs" directly next to the rankings.
2. **Measured aggregate study metrics:** V0 SciFact (Ubuntu runner, 5,183 documents, 300 queries) and V1 rerank50 (local Windows Ryzen 7 5700U, same SciFact cohort), separately labeled. Do not place latency measurements from different hardware environments on one shared comparison chart. MRR@10 is a retrieval relevance metric, not factual answer accuracy.

Primary sources: [V0](../benchmarks/V0_RESULTS.md), [V1](../benchmarks/V1_RESULTS.md), [V1.1](../benchmarks/V1_1_RESULTS.md).

## Navigation and interaction

- Insert one module on the **Research** page before the existing verified four-state MICRO-RAG replay. Keep Research, Experiments, Methodology as the only top-level navigation.
- Select exactly one of three predefined questions; no free-form question entry, no live model or backend call.
- Independently choose two distinct architectures: BM25, Hybrid RRF, Hybrid + Reranking (50). Invalid duplicate combinations are avoided in the UI.
- Shared five-stage timeline: query → lexical search → fusion → refinement → final ranking. BM25/Hybrid explain why some stages are not applicable; staged rankings progress by retrieval and refinement instead of inventing intermediate measurements.
- Accessible `Play / Pause`, `Step`, `Reset` controls; playback advances one stage at a time, stops at the end and resets on question/architecture change. Respect reduced-motion preferences; no automatic animation at initial load.
- Paired ranked-document lists with original titles, relevance labels (teaching labels only), arrows indicating position differences from a BM25 baseline, and CSS transitions on stable DOM keys for visible ranking movement.
- Explanations in Simple / Technical / Scientific levels; changing explanation does not alter data.
- Interactive quality-versus-latency visualization has a **dataset environment selector**. V0 compares BM25/Dense/Hybrid, V1 compares Hybrid/Hybrid+Rerank50. Every point displays values, provenance, and units. No cross-study cost axis.
- Link original benchmark reports. No screenshot/image asset dependencies and no additional UI framework.

## Acceptance

- Tests fail on missing scenarios, duplicate IDs, incomplete rankings, false "measured" labeling, unknown methods, invalid relevance flags, and wrong RRF rank math.
- TypeScript, Vitest, Vite, and Playwright pass for desktop 1440px and mobile 390px, including keyboard activation, replay controls, mode switches and no horizontal scroll.
- Static deployment via Vite `base="./"` and `prepare-data.mjs` keeps source-manifest provenance.
- No changes to Python/benchmark code or numerical findings. Public hosting remains a separate manual deployment gate.

## Non-goals

Live retrieval, live embedding or cross-encoder inference, scientifically validated per-question benchmarks, changing any research metric, a separate dashboard, 3D rendering, or a model selection marketplace.

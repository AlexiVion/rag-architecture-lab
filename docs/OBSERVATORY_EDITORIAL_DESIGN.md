# Research Observatory — editorial interface specification

**Status:** Implemented frontend redesign candidate, 2026-11-10. The scientific source of truth remains the versioned experiment reports; this document is a UI acceptance specification, not a new research result.

## Intent and audience

Make RAG Architecture Lab readable to a new engineer or researcher in the first minute while retaining scientific limits and inspectable provenance. The interface is a read-only research reader, not a production RAG service, research submission portal, or live model interface.

## Information architecture

Three top-level destinations:

1. **Research**: the central RAG research question, an educational Architecture Playground comparing BM25/Hybrid/Reranking on three explicitly fictional questions, measured V0/V1 quality-latency comparisons in separate experimental environments, and a four-state static replay of actual Python MICRO-RAG v0.2 outputs on fictional structured records. Evidence details are disclosed on demand.
2. **Experiments**: primary real studies; each section states the evaluated task, data, measurements, interpretation, limitation and source report. No rankings across unmatched cohorts.
3. **Methodology**: what was measured, what remains unverified, provenance principles, reproduction instructions and links to the working manuscript.

Old navigation labels have no primary menu presence. Original code, protocols and public reports are preserved in GitHub. Study results are not replaced by synthetic UI measurements.

## Visual direction

Editorial scientific reading experience: light background, restrained teal accent, simple horizontal research navigation, strong typographic hierarchy, wide whitespace and minimal card borders. Dark mode is optional. No ubiquitous permanently visible sidebar, pseudo-performance counters or oversized fictional knowledge graph on the first screen.

## Interaction design

- Three accessible navigation controls, hash-addressable.
- Architecture Playground uses two distinct methods, five manual/automatic stages, rank movement, simple/technical/scientific explanations, and within-study source-linked aggregate metrics. Its fictional document orders are not scientific measurements; see [the module's specification](ARCHITECTURE_PLAYGROUND_SPEC.md).
- In the main demonstration, four selectable cases retain exact SHA256-verified source quotes, original offsets and actual decision outcomes.
- A result only appears after the existing public replay contract and browser hash checks succeed; errors fail closed.
- Original evidence passages and technical metadata are available through native disclosure controls.
- Experiments use source-grounded fixed measurements, or validated public GRF data loaded through the existing TypeScript contracts. Reports remain external canonical sources.

## Scientific non-claims

- "≤135M" is a **proposed complete active-neural-parameter budget**, not demonstrated independent factual QA.
- Static replay uses fictional structured records and does **not** run a model in the browser.
- Small extractive QA is not training-matched to the tested generators.
- ConfRAG viewpoint labels do not establish logical contradictions.
- Independent dual-human natural-language QA holdout and manuscript review remain unfinished.
- Cross-study CPU numbers are not compared as hardware-matched speed rankings.

## Verification and publication boundaries

TypeScript typecheck, Vitest source-contract tests, Vite build, Playwright desktop/mobile navigation and four-state behavior must pass. Check all visible links, data fetches, viewport overflow and light/dark themes.

Preserve the Python research stack and model/data reports. This is only frontend presentation and behavior; do not alter benchmark numbers. Public hosting is a separately verified deployment, not implied by a successful local build. Dependency security audit and browser-screenshot visual review remain independent gates before public web-hosting.

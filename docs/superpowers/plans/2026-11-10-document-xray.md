# Document X-Ray Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Tests before code, keep commits reviewable.

**Goal:** Add a minimal accessible inline inspector for any document in the existing paired Architecture Playground.

**Architecture:** A pure helper derives a documented four-rank journey and exact two-part RRF score from the existing validated fictional corpus. A focused React panel renders the inspection; both ranked lists share the selection state owned by ArchitecturePlayground.

**Tech Stack:** React 19, TypeScript 5.9, Vite 7, Vitest 5, Playwright, CSS.

**Spec:** [Document X-Ray](../../DOCUMENT_XRAY_SPEC.md)

## Constraints

- Do not modify the corpus or empirical SciFact reports.
- BM25/Dense/Reranker positions are authored examples; only RRF is computed from ranks.
- Preserve top-level Research/Experiments/Methodology and existing 3-level explanation controls.
- Full keyboard access, mobile, dark mode, reduced motion; no additional runtime dependencies.

## Risks to explicitly test

- Unknown doc ID → error, not replacement.
- Switching questions → previous selection must disappear.
- Changing timeline stage → current left and right rank updates from actual architecture pipeline semantics.
- Difference between BM25 and dense position ≠ causal model attribution. Disclosure remains visible.
- Five cards moved by CSS transitions → focus and selection continue to follow document IDs, not positions.

### Task 1: Contract and test

**Files**: Modify \`apps/observatory/src/playgroundData.test.ts\`, add \`apps/observatory/src/documentXRay.ts\`.

**API:** \`getDocumentXRay(scene: Scenario, docId: string): DocumentXRayData\`.

- [ ] Write failing tests for p1 positions, precise RRF terms, missing document and all-scenario consistency; verify RED.
- [ ] Implement deterministic helper using \`rrfRanking\`; verify GREEN.

### Task 2: Behavior

**Files**: Modify \`apps/observatory/e2e/observatory.spec.ts\`, \`apps/observatory/src/ArchitecturePlayground.tsx\`, add \`apps/observatory/src/DocumentXRay.tsx\`.

- [ ] Write Playwright tests for selecting from both lanes, step-dependent current rank, 3 explanation levels, Close, Reset, question-switch clearance and mobile keyboard access.
- [ ] Add shared selected document state and use a button inside each stable positioned list-item wrapper.
- [ ] Implement the document's inline four-stage rank journey and optional fraction details.
- [ ] Retain source limitation labels and do not invent model scores; verify GREEN.

### Task 3: Visual and final CI

**Files**: Modify \`apps/observatory/src/styles.css\`, \`docs/ARCHITECTURE_PLAYGROUND_SPEC.md\`.

- [ ] Style selected items and inspector in existing editorial palette; adjust keyboard focus.
- [ ] Add stable desktop/mobile inspector screenshot test. Audit any overflow and reduced motion.
- [ ] Verify \`npm run check\`, \`npm run build\`, \`npm audit\`, Playwright, full offline research CI.
- [ ] Review screenshots; merge exact verified PR head, then check \`main\` CI.

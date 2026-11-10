# Architecture Playground v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Tests before production code; verify each commit.

**Goal:** Add an accessible, minimal educational architecture comparison to the existing Research page without misrepresenting research results.

**Architecture:** Source-controlled fictional JSON feeds a strict TypeScript validator and a deterministic RRF helper. A focused React component renders the same scenario in two algorithm lanes, with controlled timeline and explanation levels. A separate study selector displays metrics from V0 and V1 without cross-hardware latency comparison.

**Tech Stack:** React 19, TypeScript 5.9, Vite 7, Vitest 5, Playwright, CSS.

**Spec:** [Architecture Playground v1](../../ARCHITECTURE_PLAYGROUND_SPEC.md)

## Global constraints

- Only three main navigation sections. Do not modify Python benchmark results.
- Fictional per-question ranking **not measured**. Aggregate measurements sourced exclusively from V0 and V1.
- No additional runtime dependency or hosting key. Maintain no-promo scholarly repository rules.

## Review focus

- Duplicate architecture selection → prevent equal left/right lanes without hidden state mismatch.
- Scenario switch during playback → stop playback, restart at query and reset changed-document indicators.
- Reduced motion → static display and manual stepping remain usable.
- Missing/corrupt public JSON → fail closed with accessible error; no fabricated fallback.
- Mobile or dark mode → no clipped rows/controls, horizontal overflow or invisible focus indicators.

### Task 1 — Source contract and RRF

**Files:** Create `experiments/architecture_playground_illustrative.json`; `apps/observatory/src/playgroundData.ts`; `apps/observatory/src/playgroundData.test.ts`; modify `apps/observatory/scripts/prepare-data.mjs`.

**Interfaces:**
- `validatePlayground(input:unknown): PlaygroundArtifact`
- `rrfRanking(bm25:string[],dense:string[],k?:number):string[]`
- `rankingAtStep(scenario:Scenario,method:ArchitectureId,step:number):string[]`
- `loadPlayground():Promise<PlaygroundArtifact>`

- [ ] Add negative/positive validator and RRF tests; verify RED in CI.
- [ ] Add three fictional scenarios with complete five-document permutations, preserved as separate public source JSON.
- [ ] Implement strict contracts and deterministic RRF; tests GREEN.
- [ ] Update source manifest and check build output contains JSON.

### Task 2 — Interaction and content

**Files:** Create `apps/observatory/src/ArchitecturePlayground.tsx`; modify `apps/observatory/src/App.tsx`; add Playwright tests `apps/observatory/e2e/observatory.spec.ts`.

- [ ] Write end-to-end tests for selectors, five stages, Play/Pause/Step/Reset, relevance badges, 3 explanation levels, error state.
- [ ] Implement distinct paired selectors and cancelable playback.
- [ ] Render stable-positioned ranked document cards and per-lane pipeline indicators.
- [ ] Add source-verified aggregate V0/V1 study switch with plotted quality and query latency, and report links.
- [ ] Verify browser interaction tests GREEN.

### Task 3 — Style and publication evidence

**Files:** Modify `apps/observatory/src/styles.css`, `apps/observatory/e2e/observatory.spec.ts`.

- [ ] Add restrained editorial comparison styles and responsive two-lane layout.
- [ ] Confirm high-contrast/focus states, reduced-motion CSS, mobile no-overflow checks, screenshots.
- [ ] Run `npm run check`, `npm run build`, `npm audit`, `npm run e2e`, full offline research CI.
- [ ] Review screenshot artifacts and track differences; only merge once verified.

## Delivery

A reviewed GitHub PR with source-labeled playable comparison, accepted browser screenshots and no assertions beyond recorded science. Hosting in GitHub Pages remains a separate action.

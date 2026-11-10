# Document X-Ray — Scientific UI Design

**Status:** Implementation proposal, 2026-11-10. The original source of truth remains versioned experiments. No benchmark results are changed.

## Purpose

A reader should be able to click any one of the five ranked documents in either Architecture Playground lane and *see why its rank changes across the demonstrated retrieval strategies*, at three levels of explanation. This is an explanatory visual on the three **fictional authored questions**, not a new benchmark.

## User interaction and content

- Show an unobtrusive "Select any document to inspect its journey" invitation next to the already-visible teaching-data legend.
- Once the user advances at least to "Search", each document card is a keyboard-accessible selectable button with visible focus and selected state in **both** lanes. Avoid nested button/listitem roles.
- Click card → open an inline Document X-Ray panel **below the two lanes**, never a blocking modal. The selected card is highlighted in both lanes. The panel includes a Close button and a clear source label ("Illustrative document · authored rankings").
- Show the original source title/summary and the fictional relevance label. No vector embeddings, pseudo-similarity values, live inference, or generated text.
- Show a four-step visual track: **BM25 / Dense / Hybrid RRF / Scripted reranking**. Ranks come from the authored example except the Hybrid rank, recomputed by the same deterministic RRF function as the Architecture Playground.
- Explain, with visible fractions, that RRF score is computed from each rank: \`1/(60+BM25 position) + 1/(60+Dense position)\`. The **calculated RRF score is legitimate arithmetic for fictitious inputs**; it is not an empirically measured model result. The scripted reranking does not receive a fabricated neural score.
- Display \`current rank\` for the left and right selected architecture at the active stage, so advancing the timeline updates the panel consistently.
- Respect the playground's existing **Simple / Technical / Scientific** explanation level. Simple: plain-language votes and rank movement; technical: exact input positions and score; scientific: honest statement that lexical attributions, embedding similarities and reranker outputs were **not measured**.
- Switching the question clears selection; changing either architecture resets playback but may keep selection for the same scenario; Reset closes the X-Ray and returns to question stage. Closing X-Ray does not alter stage.
- Works in dark/light theme, desktop/mobile, with reduced motion. Preserve three navigation sections.

## Scientific safety and accessibility

- The original V0/V1 SciFact aggregate results remain separate and unchanged. The X-Ray must never suggest that example rank positions came from SciFact or actual embedding/cross-encoder model inference.
- A word appearing in the title or summary is **not** a demonstrated BM25 weight or a measured causal attribution. Do not invent token attribution or attention heatmaps.
- Every interactive item is a genuine button with accessible label and \`aria-pressed\`; X-Ray panel has a region name; a close action and keyboard access.
- Ensure all calculations use the same function as the actual hybrid output. Fail closed for unknown document ID, no substituted fallback.

## Acceptance

Vitest verifies document lookup, all source positions, exact component scores, negative inputs, consistency with \`rrfRanking\` for three scenarios and signs of movement. Playwright verifies click from each side, stage updates, Close, Reset, question change, explanation modes, keyboard activation, disclosure, and mobile overflow. Current React/TypeScript Vite and Python offline CI remain green.

## Cross-platform source naming

The pure ranking helper is `src/xrayRankMath.ts`, intentionally a distinct module stem from `src/DocumentXRay.tsx`. TypeScript may resolve `.ts` before `.tsx` on case-insensitive Windows filesystems. The Python research-surface test rejects `.ts`/`.tsx` sources sharing a case-folded stem to catch regressions in Linux CI.

# WOW v1.0 — Release gate execution matrix

**Goal:** Complete the FULL WOW v1.0 blueprint, not a reduced v0.1 portfolio release. Statuses are truthful as of 2026-11-04; updates require linked evidence. This file is a release controller, not a declaration of completion.

| Gate | Required deliverable | Current evidence | Status |
|---|---|---|---|
| G0 / R0 | Clean install + tests + license, security, changelog, citation, CI, release-check | New source/CI/docs staged on feature branch; real external clone/CI pending | IN PROGRESS |
| G1 / M2 | Independently labelled source support, contradictions, abstentions and end-to-end real generator | Source-hashed Qwen diagnostic controls show 7/24 narrow proxy; 3/12 negative source examples syntax-accepted; NO-GO publication | BLOCKED SCIENCE |
| G2 / GRF | Evidence-provenance graph, real multi-hop comparison, measured GO/NO-GO | Seed viewer + GRF-00 negative/GRF-01 inconclusive DEV studies audited | PARTIAL |
| G3 / MOD-10 | Three embedders, two rerankers, two NLI and three generators, individually measured or skipped-with-reason with pinned revision/license | Registry lists all ten; no new model measurements | NOT STARTED |
| G4 / WEB-01 | React/TypeScript/Vite seven-section observatory + a11y/e2e/perf, live static hosting | Vanilla JS static graph/evidence fixture implemented locally, no verified public URL | PARTIAL |
| G5 / REL-01 | CI green, external clone, release tag, release notes, 3 screenshots, walkthrough, live demo | Public repo and draft PR #2; no release or confirmed Pages deployment | BLOCKED |

## Execution without losing work

- **Workstream 1 — R0 first:** minimal reproducible installation, complete offline pytest, packaging build, security/license check, one CI job, public fixture integrity, and human review of the 202-file draft PR. Do not merge unvalidated work.
- **Workstream 2 — G1/G2:** freeze independently labelled data, retain Hybrid RRF default, inspect actual source entailment and calibrated abstention; GRF retrieval experiments must retain negative results and provenance. Re-running exposed SciFact TEST, M2-SYNTH-01 or HotpotQA DEV cohorts for tuning and calling them independent is prohibited.
- **Workstream 3 — G3:** verify exact model revisions/licenses and CPU feasibility. Run each candidate sequentially in role-matched benchmarks; record `measured` or `skipped_with_reason`. Skipped entries are honest registry outcomes, not fabricated evaluations.
- **Workstream 4 — G4:** migrate static explorer to typed React/Vite, implement comparisons, pipeline stages, evidence, model role table and methodology. Build/typecheck/e2e/a11y required. Use only source-verifiable public JSON.
- **Workstream 5 — G5:** real Pages deployment, external clone reproducibility, release `v1.0.0` after gates, walkthrough media, project writeup. Do NOT tag before end-to-end checks.

## Release decision rules

`R0_ENGINEERING_PASS` means the local fixture, source metadata and public aggregate contracts validate. It **does not** mean scientific M2 correctness, graph quality, ten-model evaluation, or the deployed site is complete.

For M2, the demonstrated failure of semantic abstention prevents claiming that automatic factual publication is supported. The release may transparently present M2 as an experimental feature only if the blueprint's stated scientific acceptance criterion is updated by an explicit scoped decision; never simply relabel a syntax-valid response as source-supported.

The current project remains an open-source **research** repository and not a hosted SaaS or an authenticated/paid API.

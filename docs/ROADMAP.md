# Technical roadmap — evidence-gated releases

No arbitrary release dates. An experiment advances only when the preceding acceptance gate is satisfied. Historical V0/V1/V1.1 results are preserved.

| Milestone | Deliverables | Acceptance gate | Current state |
|---|---|---|---|
| M0 — Research foundation | architecture boundaries, catalog, benchmark protocol, contributors' guide, ADR, additive adapters and contract tests | no regression to V0/V1 public APIs; test run recorded | In progress |
| M1 — V2 integrity | correct context clipping, index refresh, citation contract, no-evidence behavior; full local Qwen smoke | one inspected end-to-end run, published timings and known failures | Code improvements in progress; local run pending |
| M2 — V2.1 scientific answer evaluation | labeled answer set; evidence / factuality / semantic support / abstention scoring; repeatable manifest | published paired baseline/quality results, no unsupported faithfulness claim | Proposed |
| M3 — Retrieval architecture series | RET-03 multi-query and RET-04 parent-child, matched baselines, error analysis | two experiment result cards with reproducible configs | Adapters started; benchmarks pending |
| M4 — Recovery and routing | RET-05 contextual, RET-06 HyDE, RET-07 corrective, RET-08 adaptive | controlled resource budgets, baselines and failures | RET-07/08 adapters started; others proposed |
| M5 — Reasoning architectures | GEN-02 decomposition, GEN-03 self-reflection, AGT-00 agentic | full answer-quality evaluation, bounded loops, costs | Proposed |
| M6 — Relational and transfer | GRF-00 GraphRAG, XTR-00 cross-domain/multilingual | demonstrated improvement or explicit NO-GO on appropriate task | Proposed |
| M7 — Portfolio explorer | optional static benchmark explorer / comparison charts | loads published artifacts only; no invented live data | Optional |

## First implementation batch (M0)

- Architecture reference, experiment catalog and reproducibility policy.
- A minimal set of strategy adapters, without retraining models or duplicating the existing retrieval stack.
- Tests for mapping to original document IDs, deduplication, routing, fallback and index update.
- Replace unsafe context truncation, document staleness and vacuous citation success with honest behavior.
- README links to the public research roadmap.
- Keep `main` stable; use a reviewable branch and PR.

## Gates requiring local runtime

- `python -m pytest` with benchmark/dev dependencies.
- `./scripts/run-v2-local.ps1` on the designated machine (model download may be required).
- Canonical retrieval/answer benchmarks with fixed dataset/model revisions.
- Inspect raw per-query samples, negative/no-evidence cases and resource usage.
- Publish measured summaries and ADRs after each result.

## Explicit non-goals

No hosted multi-user chatbot, billing, client CRM, platform integrations, GPU cluster, compulsory cloud vector DB or premature web UI. These belong to applications built using RAG, not to a first-principles research lab.

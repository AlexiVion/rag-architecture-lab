# ADR-0001 — Research platform, not an application backend

- Status: Accepted
- Date: 2026-11-04

## Context

The repository already contains from-first-principles BM25, dense, RRF, reranking, evaluation and a V2 local answer pipeline. Its goal is an openly reproducible research implementation focused on RAG architectures, rather than a deployable customer application.

## Decision

Keep one repository with a small `Retriever` contract and compositional architecture adapters. Every substantial architecture gets an experiment ID, a matched baseline, an evaluation protocol and an explicit decision record. Preserve existing CLI paths and benchmark documentation. Compute canonical model-backed experiments on the local Windows host, not hosted CI. Keep presentation separate from the evaluation source of truth.

## Consequences

**Positive:** reuse, inspectable trade-offs, less framework coupling, auditable claims and transparent study provenance.

**Costs:** more discipline around manifests, tests and negative results; not a production multi-tenant service; some architectures need additional adapters and test data before meaningful conclusions.

**Alternatives not chosen:** a separate repo per technique (fragmented benchmarking); an all-in-one chatbot product (shifts focus away from research); a required high-level RAG framework (hides the mechanics being compared).

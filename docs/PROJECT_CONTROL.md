# RAG Architecture Lab — Project control (single operational status)

> **Updated:** 2026-11-09 (America/Argentina/Buenos_Aires)  
> **Baseline:** `feat/research-lab-architecture-catalog-20261104` @ `01a6dfbd7792d1f7a214998727de1c14ce6f1a51`  
> **Program:** WOW v1.0; publication **NOT APPROVED**.  
> **Tracker:** [master issue #9](https://github.com/AlexiVion/rag-architecture-lab/issues/9) · [research draft PR #2](https://github.com/AlexiVion/rag-architecture-lab/pull/2) · [append-only execution log](EXECUTION_LOG.md)

> **Research focus amendment (2026-11-08):** owner-selected **Extreme Efficiency / Tiny-Model RAG** is the proposed primary direction: 135M–600M open-weight generators, CPU-first, optimize useful evidence per token and supported-answer quality per latency/RAM. See [ADR-0005](adr/0005-tiny-model-efficiency-research-pivot.md) and [MICRO issue #11](https://github.com/AlexiVion/rag-architecture-lab/issues/11). This research pivot is **PLANNED**, not a measured breakthrough. The earlier ten-model/full-v1.0 scope remains a historical signed-off plan and must be explicitly reconciled in issue #9 before changing final release acceptance.

> **Future research reservation (2026-11-08):** [PHY issue #12](https://github.com/AlexiVion/rag-architecture-lab/issues/12) and [ADR-0006](adr/0006-tiny-world-models-physical-ai-future-track.md) track **Tiny World Models, bio-inspired physical AI, bacterial/cellular adaptation (BIO-CELL) and minimum viable embodied intelligence**. This is **PROPOSED / NOT IMPLEMENTED** and explicitly **out of scope of current WOW v1.0 / MICRO milestone** until a separate reviewed roadmap decision. Never confuse an 867-parameter controller with total system parameters.

> **ACTIVE SHIP DIRECTIVE (2026-11-09):** [REL-PORTFOLIO-01 #13](https://github.com/AlexiVion/rag-architecture-lab/issues/13) is the current P0 priority: publish the *scoped v0.1.0 retrieval research portfolio*, with real Pages/CI verification, provenance and honest negative studies. The previous full scientific WOW v1.0 gates are **not waived or completed**; they remain tracked in issue #9. Proposed MICRO and PHY/BIO research remain future, explicitly not blockers for v0.1.0. [Portfolio scope](PORTFOLIO_RELEASE.md) · [LinkedIn package](LINKEDIN_LAUNCH.md).

## Operating contract: how to keep this project truthful

This document is the **single operational status** for current gates, next actions, blockers and handoffs. The existing [ROADMAP](ROADMAP.md), [WOW blueprint](RELEASE_WOW_BLUEPRINT.md), [release matrix](RELEASE_EXECUTION_MATRIX.md) and [experiment protocol](EXPERIMENT_PROTOCOL.md) remain the scope, technical requirements and historical evidence references, **not parallel competing progress trackers**. If these documents disagree about *current* status, verify evidence at the HEAD, update this control record and log the reconciliation. Do not silently erase historical findings.

**Every completed task must record**: task ID, exact commit SHA, executed command/check, PASS/FAIL result, canonical GitHub Actions URL or verified local report path plus SHA256 where appropriate, remaining limitations, next owner/operator and a dated entry in [EXECUTION_LOG.md](EXECUTION_LOG.md). Missing evidence = `PENDING_VERIFICATION`, not `DONE`. A source-code change is `IMPLEMENTED`, not automatically `TESTED`, `BENCHMARKED` or `SCIENTIFICALLY_VALIDATED`.

**Status vocabulary:** `PASS` = verified against stated scope; `PARTIAL` = some accepted substeps; `OPEN` = required work missing; `NO_GO` = evidence rejects candidate under measured conditions; `BLOCKED` = dependency/acceptance gate unresolved. Never turn a negative study into a general claim.

**Safety and publication:** keep private/raw model reports, secrets and restricted datasets out of Git. Do not promote a model for automatic answer publication from citation syntax, synthetic templated proxies or exposed test cohorts. Run paid model calls only with explicit setup; this project is CPU-first and no-paid-API by default. Model weights and benchmark corpora may need downloads; no GitHub CI job should run large model sweeps.

## Evidence snapshot — 2026-11-09 (latest)

- **Portfolio code:** [PR #2](https://github.com/AlexiVion/rag-architecture-lab/pull/2) integrated to `main` at `0e7c1c43d65e8d79e3e80ac794b1fd3965ef44ca`; [main CI #42623333760](https://github.com/AlexiVion/rag-architecture-lab/actions/runs/42623333760) **SUCCESS** (Python, frontend, browser). [Deployment CI #42623333621](https://github.com/AlexiVion/rag-architecture-lab/actions/runs/42623333621) **FAILED at Pages setup** (repository Pages disabled); the `v0.1.0` GitHub release was **not created**. [Operational blocker #13](https://github.com/AlexiVion/rag-architecture-lab/issues/13).
- **New research branch:** [PR #15](https://github.com/AlexiVion/rag-architecture-lab/pull/15) implements offline MICRO candidate registry, BM25 paired baseline *preparation*, exact-source context packing, quote-only route and reviewer-consensus scoring. [Initial exact-head CI #42654181568](https://github.com/AlexiVion/rag-architecture-lab/actions/runs/42654181568) **SUCCESS** at `2eb22c0ababa1df2bfe5561d12ead58eb8715bca`; subsequent branch refinements **require new exact-head CI** before merge.
- **Research limits:** **NO real new 1M–600M model inference, new human-reviewed labels, independent heldout outcome or measured optimization win.** See [implementation and CLI](MICRO_RESEARCH_IMPLEMENTATION.md). Phase 4 GraphRAG/agentic quality remains outside this PR and earlier NO-GO findings remain preserved.
- **Priority:** finish verified MICRO code integration and model/revision rights audit; only then measure real local baselines. No public deployment before repository Pages admin setting can be enabled.

## Evidence snapshot — 2026-11-08

- Research PR #2: **OPEN, DRAFT, UNMERGED**, base `main`, 229 changed files and 72 commits at inspected HEAD. It requires a **structured review / decomposition decision before merge**; do not merge merely because CI is green.
- Latest inspected research HEAD: `01a6dfbd`. GitHub Actions [offline research integrity run #41935324313](https://github.com/AlexiVion/rag-architecture-lab/actions/runs/41935324313) = **SUCCESS**; job includes Python tests/package checks, React/TypeScript build and headless Chromium browser navigation / mobile screenshots. This validates those tests, **not a live public deployment or science**.
- Historical local Windows `WOW_R0_LOCAL_ENGINEERING_CHECK_PASS` and canonical V0/V1/V1.1 retrieval benchmark reports are documented, but an **independent clean checkout is not recorded**.
- `G1/M2`: default automated factual publication **NO-GO**. 24-case synthetic proxy = 7/24; exact-pattern guard stress has 8/16 false rejections of authored positives; independently labelled semantic/answer-quality holdout absent. Do not claim general-world accuracy from either study.
- `G2/Graph`: source-backed two-hop proof of concept and paired DEV studies verified. Graph-first on 60 HotpotQA DEV questions: Recall@5 0.7083 vs BM25 0.8250 (NO-GO on this cohort). Separate frozen graph-hybrid study: Recall@5 0.8500 vs Hybrid RRF 0.8583 (INCONCLUSIVE, retain Hybrid RRF default).
- `G3/MOD-10`: ten proposed additional model entries exist; no accepted ten-model comparative evidence matrix.
- `G4/WEB-01`: seven-view typed React/Vite observatory **IMPLEMENTED** and inspected HEAD CI **PASS**, including a Chromium smoke. Outstanding: reproducible Node lockfile / `npm ci` gate, broader accessibility/perf/manual visual acceptance and **verified public Pages URL**. Older WEB-01 docs were written before latest CI and must be reconciled.
- `G5/REL-01`: no public v1.0 GitHub release/tag or verified live deployment. Repository is already public; that is not the same as a finished release.

## Current research priority — MICRO / Extreme Efficiency

**Goal:** determine whether targeted query-aware, source-verbatim evidence selection, small-model-aware context budgets and selective extractive/generative/abstain routing improve **independently supported useful answers per CPU second, token and RAM** relative to same-model naive/Hybrid baselines. An unverified improvement is not innovation; run blinded heldout and document prior-art overlap (MiniRAG, TripletRAG, context compression).

| ID | Task | Acceptance / evidence | Status | Dependency |
| --- | --- | --- | --- | --- |
| MICRO-00 | Prior art, 1M–600M candidate registry and license/revision audit | Proposed catalog implemented; exact revisions/rights/real CPU feasibility not yet verified | PARTIAL — REGISTRY ONLY | CTRL-01 |
| MICRO-01 | Benchmark, split and leakage integrity | Fixture hash/group validation implemented; independent human-labeled DEV/CALIBRATION/HOLDOUT not created | PARTIAL — FIXTURE ONLY | MICRO-00 |
| MICRO-02 | Matched small-model baselines | CLI prepares no-RAG/naive/spans/oracle BM25 traces and can use local checkpoint; Hybrid/actual model measurements remain OPEN | PARTIAL — INSTRUMENTATION | MICRO-01 and R0-01 |
| MICRO-03 | Query-aware exact-source evidence packing | Implemented original offsets, source excerpts and matched budget; no measured quality win or heldout ablation | PARTIAL — CODE ONLY | MICRO-02 |
| MICRO-04 | Extractive quote vs generation vs abstention | Quote-only route separated from draft generation and abstention; no semantic calibration or conditional reranking evidence | PARTIAL — CODE ONLY | MICRO-03 and M2 labels |
| MICRO-05 | Independently assessed heldout Pareto study | Two-reviewer consensus scorer implemented; frozen real-world holdout, annotations, paired CIs, p95/RAM study still OPEN | PARTIAL — SCORING TOOL ONLY | MICRO-04 |
| MICRO-06 | Micro-efficiency observatory | Experiment trace/size/budget, side-by-side baseline vs optimized real artifacts, provenance and known failures | OPEN | MICRO-05, WEB-01 |

**First action:** MICRO-00/MICRO-01 protocols, then **the first 135M baseline measurement**. Do not run arbitrary ten-model sweeps, promise dramatic improvements, or tune/test against previously exposed cohorts. Current fixed retrieval baseline and all archived NO-GO results remain unchanged. Generation quality remains scientifically blocked until independently measured.

**Scope policy:** MICRO work is now the primary proposed research track, not a silent replacement of all original release requirements. The older 10-model evaluation is **deprioritized, pending a reviewed explicit v1.0 scope amendment**. A release still needs clean install, web publication and scientific disclosure. Never label G3 `PASS` without meeting its original contract or changing that contract explicitly.

## Roadmap — strict acceptance gates

| Phase / ID | Deliverable and status | Concrete acceptance gate | Dependencies | Priority |
| --- | --- | --- | --- | --- |
| **P0 / CTRL-01** | Operational control, evidence log, canonical status — **PASS / ADOPTED** | This file + execution log under reviewable docs PR, linked from ROADMAP, then adopted in research integration workflow | None | P0 |
| **P1 / R0-01** | Reproducible engineering baseline — **PARTIAL** | External clean checkout on Windows and Linux; pinned reproducible installs; full deterministic pytest/CLI/wheel + Node build; source/license/security review; no undocumented downloads; evidence recorded | CTRL-01 | P0 |
| **P1 / PR-02** | Research PR #2 integrated into main — **MERGED / VERIFIED CI** | Classify 229 files (code, generated, license, data), verify source attribution and unexpected material; decide safe merge/decomposition, review integration diff and rerun exact-head CI | CTRL-01 | P0 |
| **P2 / WEB-01** | React observatory code/CI — **PASS**; public Pages **BLOCKED (SITE NOT ENABLED)** | `npm ci` / typecheck / unit / build / Chromium plus keyboard/mobile a11y/perf and visual acceptance; only audited manifests; verified public Pages URL; capture reviewed real screenshots | R0-01; validated public data | P1 |
| **P3 / M2-01** | Source-supported generation + abstention evaluation — **BLOCKED SCIENCE** | Independently labelled natural-language development/calibration/holdout material, document/entity partition, claim support/contradiction/insufficiency labels, predeclared acceptance and risk-coverage metrics with uncertainty; real pinned model run; report false rejection/acceptance and limitations | R0-01; no reuse of exposed TEST/DEV controls as independent holdout | P0 scientific |
| **P3 / GRF-02** | GraphRAG evidence and multi-hop benchmark — **PARTIAL** | Verifiable extraction/index provenance + stable entity/relation IDs; same-corpus, same-query matched graph/text comparison; multi-hop evidence and answer quality, construction/latency/RAM cost; defensible GO/NO-GO | R0-01; M2 quality metrics for answer-level claims | P1 |
| **P4 / MOD-10** | Ten additional model evaluations — **OPEN** | Verify each hub ID/revision/license/role and memory feasibility; run sequential CPU evaluations or explicit `skipped_with_reason`; role-specific comparable datasets, artifacts and uncertainty; no cross-role leaderboard | R0-01; M2 for generation/NLI criteria | P1 |
| **P5 / REL-01** | Complete public WOW v1.0 release — **BLOCKED** | All contracted scope gates resolved; reviewed integration, external fresh-clone proof, exact-head CI PASS, public viewer verified, real screenshots/video, attribution/security check, version tag, release notes and README walkthrough | All prior mandatory gates | P0 release |

**Milestone sequencing:** CTRL-01 -> R0/PR audit -> WEB-01 public presentation; M2 + GRF studies may proceed in parallel only after frozen protocol; MOD-10 sequential local runs; REL-01 only after the full agreed v1.0 contract is satisfied. A publicly inspectable **preview** may be deployed earlier, but it must be labelled preview, never v1.0.

## Legacy integration work queue (still required; coordinate with MICRO-00/01)

| Task ID | Specific next action | Evidence needed | Status |
| --- | --- | --- | --- |
| CTRL-01 | Review/adopt these canonical status and execution-log files in a docs-only PR; link them from ROADMAP | merged docs PR or explicit approved integration plan | IN PROGRESS |
| PR-02 | Produce a file-level scope and provenance review of 229-file PR #2; detect generated data, license and secret risks; decide split vs verified direct merge | file inventory with accept/reject rationale | OPEN |
| R0-01 | Run clean external Windows/Linux installs and verify `pytest`, CLI, wheel, frontend `npm ci`, build/CI parity | machine/command/revision and PASS/FAIL receipts | OPEN |
| WEB-01 | Reconcile WEB-01 stale status after Chromium CI; check Node lockfile, keyboard/a11y/perf/visual gates and Pages configuration | tests, screenshots, direct public URL check | OPEN |
| M2-01 | Freeze independently labelled source-support protocol before changing evidence gating; independently validate abstention and contradictions | approved protocol with cohorts/hashes, annotator agreement and metrics plan | BLOCKED |

## Definition of Done and handoff

Before setting any gate to `PASS`, add one dated log entry, link immutable proof, update this table and the main issue #9. If a test is run against a later HEAD, revalidate the affected scope and link the later SHA. Store negative outcomes and blocked decisions as first-class evidence; no success percentages without denominators and evaluation scope.

**Next handoff recommendation:** begin with CTRL-01 + PR-02 and R0-01; do not run ten expensive models or imply M2 quality is solved before its evaluation contract exists.
# RAG Architecture Lab — WOW Release v1.0 blueprint

**Date:** 2026-11-04  
**Status:** Approved **scope / implementation plan**, NOT completed implementation.  
**Tracking:** [WOW Release #9](https://github.com/AlexiVion/rag-architecture-lab/issues/9).  
**Draft integration:** [PR #2](https://github.com/AlexiVion/rag-architecture-lab/pull/2).

## 1. Product statement and design constraints

**Vision:** An open-source, inspectable **RAG Architecture Observatory** for building retrieval approaches, measuring their trade-offs and diagnosing grounded-answer failures, including document provenance and knowledge-graph paths.

The deliverable is a research platform rather than a SaaS chatbot. It is intended to be understandable by developers and hiring teams from a public GitHub repository + real live visual explorer, and usable locally with public data and **no paid API requirement**.

The standout moment is *not* a pretty mock dashboard. It is selecting an experiment, watching where each candidate document came from, tracing its citations and graph relationships, and seeing a **real measured** quality/latency trade-off and documented failure case.

Hard boundaries:
- Distinguish **implemented**, **tested**, **benchmarked**, **scientifically validated**, **experimental** and **proposed** everywhere.
- Preserve V0 / V1 / V1.1 historical results, no reclassification of negative experiments as wins.
- **No claim of perfect semantic generation.** Perfect certainty is not measurable or guaranteeable on arbitrary real-world inputs. Replace with explicit coverage, measured error, honest abstention, refusal when evidence cannot be supported, and known limits.
- Avoid using SciFact TEST for tuning; historical diagnostic exposure to TEST Q1 must be disclosed. Freeze protocol before a new genuinely independent evaluation.
- CPU-friendly, sequential model execution, bounded RAM/storage and resumable local runs. Hosting an interactive *viewer* should not require hosting local model inference.
- Research machine is documented as a Ryzen 7 5700U, approximately 16 GiB RAM. Do not assume a GPU.
- Public artifacts must be source-verified and properly attributed. Never publish raw private drafts, model caches, unlicensed text corpora, or secret tokens.
- Code MIT license is distinct from model and dataset licenses. Validate each external distribution before download/redistribution.

## 2. Audited starting point (2026-11-04)

| Component | Reality | Gate |
|---|---|---|
| V0 BM25 / Dense / Hybrid RRF | Implemented, SciFact retrieval benchmarks published | Retain Hybrid default and full provenance |
| V1 reranking | Implemented, canonical measurements published | 50-candidate NO-GO default; 10-candidate optional |
| V1.1 candidate-depth | Measured, documented | Retain conditions; do not generalize |
| RET-03..08 adapters | Code exists; not all benchmarked | Evaluate per matching baseline |
| V2 retrieval+local Qwen | Code exists; historical generated answer was off-task and uncited | Post-gate real-model integration and answer quality still pending |
| Citation syntax gate | Deterministic tests pass; fails closed on malformed draft | Test with real local generator; syntax != entailment |
| M2 | Expert-labelled SciFact TRAIN stance sample exists; failed small NLI scored 27.5% (11/40) | Full answer/relevance/abstention evaluation incomplete |
| GraphRAG / GRF-00 | Implemented deterministic curated-source, 2-hop graph-first retriever and source-path trace | General-purpose extraction, real multi-hop benchmark and GO/NO-GO remain pending |
| Model comparator | Partial fixed-model scripts | Uniform registry, revision/license tracking, per-role comparisons |
| Web observatory | First static interactive evidence viewer committed, with 3 curated queries and exact-source inspector | General experiment dashboards, accessibility/browser QA and public deployment remain pending |
| Public release | Public repository; LICENSE/CONTRIBUTING are on draft PR #2, not yet main | Clean release, merge, tag, external clone smoke, project page |

The integration PR was already broad (114 changed files before GRF-00 and the viewer) and remains in draft. Its size is itself a review risk; scope new work into focused commits/PRs and avoid merging blindly.

## 3. Release architecture

```text
                  Public read-only Explorer (React + TypeScript)
                              |
       Validated, schema-versioned JSON / graph artifacts
                              |
  Experiment manifest + dataset fingerprint + git SHA + model revisions
                              |
         Composable Experiment Runner and Observability Traces
            /              |                 \
  Retrieval baseline    GraphRAG GRF-00    Grounded Generation
  BM25 / Dense / RRF    entities / edges   evidence context
  rerank / RET-03..08  paths / provenance  citations / abstention
            \             |                 /
               Independent evaluation harness
       retrieval  | stance | support | abstain | time | RAM
                              |
            Local CPU-first models + public datasets
```

Static viewer must not execute code/models from untrusted JSON. Use schema validation, DOM-safe rendering and explicitly labelled evidence.

## 4. Workstreams and acceptance contracts

### R0 — A clean installable research spine (must finish first)

Deliver:
- External-clone install validated with Python 3.11 and minimal dependencies; optional large model extras clearly separated.
- Cross-platform CLI quickstart (Windows and Linux); one minimal dataset/fixture that downloads no model and demonstrates a real trace.
- Focused issue/PR review of the existing 114-file draft, locally verified tests and experiment smoke.
- License, model/dataset attribution and redistribution, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY.md, CHANGELOG.md, CITATION.cff, architecture diagram and version tag policy.
- A single `release-check` script that does not claim scientific validity from unit tests.

Acceptance: clean checkout -> install -> tests -> fixture experiment -> validated JSON trace, with exact commands and no paid key. Nothing is called complete based solely on documentation.

### M2 — Grounded generation, semantic evidence and abstention

Deliver:
- End-to-end real local V2 smoke **after** the citation gate change: accepted-with-valid-citations, rejected-with-uncited-draft, and genuinely no-context abstention conditions.
- Experiment schema with per-query retrieval evidence, model output, cited spans, source IDs, verified labels, failure taxonomy and calibrated-versus-uncalibrated status.
- **TRAIN/DEV** answerable, contradicted, irrelevant and insufficient-evidence samples. Use original expert-labelled SciFact rationale stance data where applicable; qrels are retrieval labels only. Add independent answer-quality ground truth and a second domain.
- Separate metric families: retrieval Recall/MRR/nDCG; citation validity; claim support by independently validated evidence; answer task correctness; correct/false abstention rates; coverage vs error (risk-coverage); latency and peak RAM.
- Evidence-only and generated-answer splits; no oracle-evidence score misleadingly counted as end-to-end RAG success.
- Predeclared acceptance thresholds based on use-case risk and measured confidence intervals, not a retroactive threshold on held-out TEST.
- Optional stronger scientific verifier only as a separate candidate (do not revive the failed `nli-MiniLM2-L6-H768` by changing the label name).

Acceptance: replicate good and bad answers with verifiable provenance, publish measured independent quality including false refusals, and show that the runtime fails safely for unsupported/uncited output **under the evaluated conditions**. **No '100% perfect' claim**.

### GRF-00 — Real graph retrieval (not a visual mock graph)

Minimum interoperable schema:
- `Document{id, hash, license}`; `TextUnit{id, doc_id, offsets}`;
- `Entity{id, aliases, type, confidence}`;
- `Edge{source, relation, target, text_unit_ids, extractor, confidence}`;
- `EvidencePath{query, node_ids, edge_ids, original_doc_ids}`.
- Explicit provenance and stable graph IDs across repeated indexing.

Stages:
1. Deterministic seed graph and entity alias resolution from a small distributable fixture (no LLM).
2. Local extraction adapter with schema-constrained JSON validation, duplicate/contradictory relation handling and provenance.
3. Search via entity match -> 1- or 2-hop relation traversal -> parent document mapping -> query-aware reranking and text fallback. Budget candidate count, traversal depth, indexing time and memory.
4. Optional Leiden/community summaries and global search after basic graph path retrieval works. Microsoft GraphRAG offers entity/relation extraction, community reports and local/global/DRIFT search; our implementation should compare those modes without claiming parity by name alone (reference: https://microsoft.github.io/graphrag/index/overview/ and https://microsoft.github.io/graphrag/query/overview/).
5. Compare graph+text against Hybrid RRF on a benchmark where **multi-hop labels** genuinely exist (e.g. a license-cleared HotpotQA/MuSiQue subset), track path provenance, answer quality, failures and index/CPU cost.

Acceptance: graph indexing/reindexing tests, real two-hop trace rendered in the web explorer, no source-less edges shown as proof, measured baseline comparison and a GO/NO-GO.

### MOD-10 — Exactly ten candidate models across distinct roles

**Ten additional model candidates** beyond the four model baselines already studied in this repository; do not call them ten language generators or collapse different tasks into one misleading rank. The proposed registry is `experiments/model_matrix_10_proposed.json`, with a separate historical-baseline section. Exact revisions, model-specific prompts, license terms and CPU budgets remain release gates; the Qwen2.5-3B-Instruct card currently lists a `qwen-research` license, so it cannot be silently redistributed as MIT.

- 3 **embeddings**: recall, MRR, nDCG, index size/speed, memory.
- 2 **rerankers**: paired delta vs Hybrid on the same candidates, query latency/CPU.
- 2 **NLI / evidence classifiers**: original SUPPORT/CONTRADICT gold-rationale confusion matrix and out-of-domain error; prior failed model remains a negative control.
- 3 **generators**: answer correctness, citations/claim support, abstention error, tokens/sec, total latency and memory.

Ensure each model has an independently reviewed hub identifier, exact revision, actual license, input formatting, class order/score meaning, CPU feasibility and a published configuration. Large weights are optional and **loaded one at a time**. No ranking across incomparable model roles. Results must include at least one credible failure and cannot promote a new default based only on TRAIN scores.

Acceptance: 10/10 **additional** candidate entries either **measured** or clearly marked `skipped_with_reason`; no fabricated scores, an independently repeatable sample, per-role results and reproducibility manifests. Missing model/corpus license blocks public redistribution, not necessarily local research.

### WEB-01 — The interactive RAG observatory

Build `apps/explorer/` as a static-first React + TypeScript application with a controlled typed data layer and Vite build; use a canvas/SVG graph library only for display. Keep research Python backend independent.

Public information architecture:
1. **Overview:** identity, architecture choices, verified metric highlights, transparency on limitations.
2. **Experiment comparison:** select baseline/candidate, paired metric changes, mean/p95 latency and confidence intervals; only compare compatible runs. Hover reveals source artifact and exact conditions.
3. **Pipeline inspector:** draw query -> retrieval -> fusion -> optional rerank/graph -> context -> generation -> citation gate. Click a stage for trace and timing.
4. **Graph exploration:** evidence-backed nodes/edges and 1/2-hop path highlighting with document drill-down; provenance is mandatory.
5. **Evidence review:** question, retrieved source snippets, raw attempted draft (where safe and public), visible citation status, accepted/abstained state and known errors.
6. **Model lab:** ten model registry entries, per-role comparable measured scores and negative results.
7. **Methodology:** source links, datasets, license notices, experiment protocol and reproducible local commands.

Visualization quality: clean engineering/editorial aesthetic, dark/light themes, excellent spacing and typography, transitions that clarify provenance, responsive mobile, keyboard access, screen-reader summaries. Do not ship decorative fake gauges, invented traces or unsupported 'live score'.

Backend/security: public viewer reads signed/hashed versioned static manifests; any local inference API is **opt-in and localhost-only**, never directly exposed publicly. Avoid uploading arbitrary private documents. Generated traces must be sanitized before publication. Target an accessible, static hosting workflow with no model-server cost.

Acceptance: run `npm run build`, typecheck, browser/e2e checks, accessibility and performance smoke; deploy a publicly reachable viewer and verify it renders exact published artifacts. User workflow: click an experiment -> inspect evidence/graph and metric -> open original source.

### REL-01 — Public technical launch

Deliver:
- English README with an immediate visual result, one-command no-download quickstart, exact dependency/memory expectations, three screenshots, a short architecture diagram and realistic experiment results.
- Reproduction guide + model cards, open source attribution, security/reporting policy, executable and web deployment docs.
- Release notes framing one compelling measured **positive** result (Hybrid), one **negative** result (NLI), and one genuine multi-hop graph trace (if benchmarked).
- 60–120 second walkthrough video and a concise LinkedIn project write-up; direct links to public code, live explorer and reproducibility docs.
- Tested release tag and a concise changelog. Build a portfolio-ready v1.0 only when acceptance gates genuinely pass.

Acceptance: someone unfamiliar with the project can inspect the public repo, run a small real experiment, verify the source of every displayed score and use the hosted read-only explorer. Launch copy never says 'semantic accuracy 100%'.

## 5. Execution order (strict; no fabricated completion)

| Gate | Dependency | Result needed |
|---|---|---|
| G0: release spine | existing PR #2 + clean tests | reproducible install, agreed versioning, public license |
| G1: evidence and M2 | G0 | independent scoring, error boundaries, verified citations/abstentions |
| G2: graph | G0 + measurable retrieval baseline | true provenance graph + multi-hop study |
| G3: ten-model comparison | G1 and adequate CPU resource budget | ten entries with distinct roles and honest status |
| G4: explorer | versioned artifact schemas from G1/G2/G3 | real interactive trace/graph and public build |
| G5: release | G0–G4 | verified external onboarding, changelog, GitHub tag and demo page |

Work may be implemented in parallel by independent components **only when the contracts are frozen**. Begin the explorer shell early with explicitly marked sample fixtures; do not call its illustrative fixtures real benchmark results.

## 6. Non-goals for the WOW v1.0

No SaaS billing/auth, no cloud model inference requirement, no 50-model sweep, no promise of absolute scientific truth, no large deployment cluster, no blind adoption of an external GraphRAG framework as if it were an original implementation. These may be future optional integrations.

## 7. Immediate first implementation package

1. Keep PR #2 in draft until review/tests complete; do not merge by guessing.
2. Implement the typed experiment/trace manifest and a tiny distributable **offline fixture** that can be validated without Hugging Face downloads.
3. Implement GraphRAG evidence schema and deterministic seed-graph path with source linking; tests before optional LLM extraction.
4. Build explorer shell reading the validated fixture (clearly labelled **fixture**).
5. Close the M2 real-generation/output-gate issue before exposing demo generations as grounded.
6. Run the model matrix in small CPU-budget cohorts, not a single heavy command.
7. Publish measured artifacts only after verifying hashes and data licenses.

**Definition of done:** real runnable code, all specified acceptance checks passing, empirical claims linked to verified evidence, a deployed explorer, and a release a newcomer can reproduce. A long checklist or pretty mock alone is not completion.


**First real-source benchmark implementation status (2026-11-04):** `GRF00-HOTPOTQA-DEV-01` now has a frozen protocol and code (HotpotQA original CC BY-SA 4.0 DEV distractor, 60 deterministic eligible bridge queries, 2-hop quoted title-mention graph + BM25 vs BM25, same per-query candidates, recall@1/3/5 with paired bootstrap confidence intervals). The source download is SHA256 pinned, ~46 MB; query labels are not passed to the graph builder. Results have **not** been executed or verified locally yet. This is **not** a Hybrid RRF comparison or answer-quality study; both remain future gates.

## GRF-00 empirical decision — 2026-11-04

The user's Windows run of `GRF00-HOTPOTQA-DEV-01` completed successfully with all local tests passing, 60 DEV bridge questions, and the following BM25 vs graph-first+BM25 retrieval metrics:

| Metric | BM25 | Graph+BM25 | Paired delta | 95% CI |
|---|---:|---:|---:|---|
| Recall@1 | 0.4333 | 0.3500 | -0.0833 | [-0.1500, -0.0167] |
| Recall@3 | 0.6833 | 0.5917 | -0.0917 | [-0.1750, -0.0083] |
| Recall@5 | 0.8250 | 0.7083 | -0.1167 | [-0.1917, -0.0583] |

**Decision: NO-GO for the current graph-first title-mention prioritization policy on this DEV sample.** The graph is still a functioning learning/demo component and not evidence that GraphRAG generally fails. Its construction was unsupervised by the relevance labels. Do not tune on the same 60 DEV cases. Local diagnostics and a web-safe aggregate exporter have been added but still await local validation. Full graph extraction, correct production indexing time, Hybrid RRF comparison and answer quality remain unmet gates. No default retrieval changes.

## Updated graph-first research decision — audited 2026-11-04

After running the original 60-query DEV study, the operator executed the separate post-run audit. **Full test suite PASS**; archived report SHA256 `962dc3b12d0086857ad94198cf2b1fff7a49ca5f7df069e9575a6daaf778f016`. Mean delta Recall@5 was **−0.1750 for 40 path-active cases** (11 losses, 0 wins, 29 ties) and **0.0000 for 20 path-inactive fallback cases** (20 ties), reconciling to **−0.1167 across all 60**.

**Conclusion:** current graph-first prioritization is NO-GO in this DEV subset. The audit does not establish that GraphRAG in general fails, nor does it explain each loss causally. Retain default Hybrid RRF unchanged. Any new design must freeze its retrieval strategy and evaluation cohort before observing performance; see `docs/GRF_01_HYBRID_RRF_PROTOCOL.md`. No GraphRAG release gate should be marked complete merely because the seed fixture works.


**GRF-01B/C implementation staged (2026-11-04):** The user completed the 60-query disjoint DEV reservation with SHA256 `a560b1cbabe1ce6b4413f0f6f59759cd08e69ce49c5391e05b7c8767f81bd13f` and no overlap. A fixed two-hop graph-augmented Hybrid RRF policy (model revision pinned, RRF=60, source-quote bonus weight 0.10, exact no-path identity) and synthetic tests have been added. Local operator has not yet verified those new changes, and the reserved cohort has not been scored; do not claim accuracy improvements. See `docs/GRF_01_LOCKED_HYBRID_POLICY.md`.

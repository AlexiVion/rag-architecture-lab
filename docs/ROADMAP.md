# Technical roadmap — evidence-gated releases

No arbitrary release dates. An experiment advances only when the preceding acceptance gate is satisfied. Historical V0/V1/V1.1 results are preserved.

| Milestone | Deliverables | Acceptance gate | Current state |
|---|---|---|---|
| M0 — Research foundation | architecture boundaries, catalog, benchmark protocol, contributors' guide, ADR, additive adapters and contract tests | no regression to V0/V1 public APIs; test run recorded | In progress |
| M1 — V2 integrity | correct context clipping, index refresh, citation contract, no-evidence behavior; full local Qwen smoke | one inspected end-to-end run, published timings and known failures | 2026-11-04 citation output contract verified with 75 local tests; historic uncited Qwen answer still marked failed. New default behavior not yet real-model tested. Evidence relevance/abstention not calibrated |
| M2 — V2.1 scientific answer evaluation | labeled answer set; evidence / factuality / semantic support / abstention scoring; repeatable manifest | published paired baseline/quality results, no unsupported faithfulness claim | Guided review CLI validated locally (92 tests). First completed human review: SciFact TEST Q1, 5/5 irrelevant sources, 1/1 source-supported but off-task claim, no citations, expected abstention. Diagnostic only; separate task-alignment summary verified locally, and independent TRAIN-only evidence case sampler validated locally (18 unlabelled cases; tests passed). Blind annotator executed locally with tests passing; 18-case no-prompt structural audit verified locally; 6 no-context controls and 18 semantic labels unassessed. TRAIN NLI pilot: 12/12 neutral; basic-control sanity NO-GO. Original SciFact TRAIN expert-labelled rationale study: 11/40 correct (27.5%), SUPPORT recall 2/20, CONTRADICT recall 9/20, 26/40 neutral; **NO-GO for this NLI model**. M2 overall remains open for independent answer-quality / abstention validation. |
| M3 — Retrieval architecture series | RET-03 multi-query and RET-04 parent-child, matched baselines, error analysis | two experiment result cards with reproducible configs | Retrieval research underway. RET-04 10-query smoke negative; RET-FUSION-01 809-query train study favors retaining original RRF; RET-RERANK-20 60-query train smoke negative (Recall@5 delta −0.10833, exploratory bootstrap CI [−0.19167,−0.03333]) and ~47x slower; provisional NO-GO |
| M4 — Recovery and routing | RET-05 contextual, RET-06 HyDE, RET-07 corrective, RET-08 adaptive | controlled resource budgets, baselines and failures | RET-05/06/07/08 adapters started; benchmark runs pending |
| M5 — Reasoning architectures | GEN-02 decomposition, GEN-03 self-reflection, AGT-00 agentic | full answer-quality evaluation, bounded loops, costs | Proposed |
| M6 — Relational and transfer | GRF-00 GraphRAG, XTR-00 cross-domain/multilingual | demonstrated improvement or explicit NO-GO on appropriate task | GRF-00 2-hop retrieval + offline fixture verified in user's Windows browser and full pytest PASS; paired HotpotQA DEV 60-query study completed (Graph+BM25 Recall@5 0.7083 vs BM25 0.8250, delta −0.1167, CI below zero): graph-first NO-GO here. Post-run auditor locally PASS, original source SHA256 962dc3b12d008685…; path-active 40 cases delta@5 −0.175 (0 wins/11 losses), no-path 20 cases delta 0 (all ties). Source-safe browser summary generated locally. Full GraphRAG remains open. |
| M7 — Portfolio explorer | static interactive observatory, later benchmark explorer | loads published artifacts only; no invented live data | Prototype viewer implemented: 3 query fixtures, clickable graph paths/source quotes and JSON export; not yet verified on user browser, no public deployment. |

## First implementation batch (M0)

- Architecture reference, experiment catalog and reproducibility policy.
- A set of retrieval strategy adapters, without retraining models or duplicating the existing retrieval stack.
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


## WOW v1.0 — full portfolio-quality release track (requested 2026-11-04)

**Scope and acceptance contracts:** [WOW release blueprint](RELEASE_WOW_BLUEPRINT.md) and [master issue #9](https://github.com/AlexiVion/rag-architecture-lab/issues/9). This is a separate larger milestone; it is not a claim that M2, GraphRAG, ten-model comparison or the web observatory are complete.

| Track | Current verification | Required output |
|---|---|---|
| R0 release spine | PR #2 draft; LICENSE/CONTRIBUTING there, not main | clean install and verified tag |
| M2 generation/evidence | claim-styled NLI NO-GO, citation syntax gate, answer validation open | independently measured support, answer quality and abstention |
| GRF-00 | 2-hop prototype + 60-query HotpotQA DEV study completed; graph-first NO-GO, archived report audited locally | independent matched Hybrid RRF comparison, stronger relation extraction, multi-hop answer quality |
| MOD-10 | 10 candidates defined in proposed registry, no matched full matrix | role-specific sequential CPU results and artifacts |
| WEB-01 | functional local browser explorer, sample graph trace and locally verified benchmark aggregate | public deployed viewer, accessible browser QA and reproducible published manifests |
| REL-01 | no v1.0 release | documented external clone, deployed public explorer, verified release |


**GRF-01A cohort reservation implementation (not yet run on the operator's machine):** `scripts/freeze-grf01-cohort-local.ps1` checks the archived GRF-00 source report SHA256, pins the existing HotpotQA cache, selects 60 never-before-used DEV query IDs with a new seed (217) and no overlap, and writes a gitignored immutable cohort manifest. **It does not evaluate or tune anything.** DEV reuse is still a methodological limitation.


**GRF-01 post-cohort status:** the reserved 60 DEV query IDs are verified locally with 0 overlap and SHA256 `a560b1cbabe1ce6b4413f0f6f59759cd08e69ce49c5391e05b7c8767f81bd13f`. The next implemented gate is an *unscored* policy lock (`scripts/prepare-grf01-hybrid-local.ps1`): same BM25 and Dense lists, immutable model revision, fixed RRF=60, graph boost=0.10, strict no-path identity. Its code/tests are staged for Windows validation; no new recall results or Graph-Hybrid GO claims exist.

**GRF-01D/E evaluation runner:** source code, synthetic tests and `scripts/run-grf01-hybrid-study-local.ps1` committed. It validates the frozen cohort/model/policy before loading weights and computes a one-pass four-architecture same-candidate comparison with paired CIs and resource measurements. Windows verification and all **GRF-01 actual scores are still pending**; full GraphRAG and M2 quality gates remain open.

**GRF-01 frozen evaluation executed (2026-11-04):** full local pytest PASS; 60 reserved queries evaluated exactly once; fixed MiniLM model and graph policy hashes verified. Primary Recall@5: Hybrid RRF **0.8583** vs Graph-Hybrid **0.8500** (delta **−0.0083**). Recall@3 delta −0.0500, Recall@1 equal. **INCONCLUSIVE_NO_AUTOMATIC_PROMOTION**, Hybrid RRF retained. New saved-report audit and local observatory panel staged; no unreported CI/win-loss values are asserted. M2/ten-model matrix/public release still incomplete.


## Latest verified checkpoint — 2026-11-04 (supersedes earlier in-progress notes)

**GRF-00:** 60 HotpotQA DEV bridge questions, graph-first source title links vs BM25, NO-GO. The independent saved-result audit passed. **GRF-01:** 60 disjoint DEV bridge questions, sealed Hybrid RRF vs Graph-Hybrid, full test suite and saved-result audit **PASS**. Primary paired ΔRecall@5 = **−0.0083**, 95% CI **[−0.025,0]**, decision **INCONCLUSIVE_NO_AUTOMATIC_PROMOTION**. Recall@3 delta −0.05 with wholly negative 95% CI; graph paths: 36 active (0 wins/1 loss/35 ties at @5), 24 inactive (all ties). Source report SHA256 `f2167bc7220554b1864648c5c5de0b67544bfbdba585a4aeed8f466927fcb2b4`.

The graph policies are research-only. **Hybrid RRF remains the default.** These DEV subsets have been observed, so do not tune them to produce favorable results. M2 semantic response-quality measurement, 10 additional model comparisons, general graph extraction and public web hosting are not yet complete.

The explorer now has published **summary-only statistical aggregates** as a read-only fallback when an operator-specific locally audited JSON is absent. Published summaries are grounded in successful operator audit logs, not the raw full report in GitHub. No source passages or copyright-restricted question texts were published.


## M2 next executable gate (prepared; local run pending)

`M2-LIVE-01` adds `scripts/run-m2-live-controls-local.ps1` for one bounded local Qwen test across four explicitly fictional controlled evidence conditions (answerable, irrelevant but nonempty, contradictory and no-context). Full pytest runs before the generator. Exact source IDs, observable public output status, citation coverage, preserved rejected drafts, no-context generator-skip and timing are recorded. No SciFact TEST is re-used and no answer-level semantic support is attributed to citation syntax. A previously passed empty-context unit test is **not** a substitute for a live-generator smoke. This closes neither M2 independent quality evaluation nor the wider WOW v1.0 release.


## Latest M2 live-generator checkpoint — 2026-11-04

**M2-LIVE-01:** The first post-citation-gate real local Qwen run completed with pytest PASS: four fictional controls, three generator calls, all three generated drafts rejected by the citation contract (including curated adequate evidence). No-context abstained without generator invocation. Fixture SHA256 261e4545b00e19d100e4144ca2704f7bac11658db1f200ef2601e58621e7e46c. Qwen commit unresolved. An offline saved-result audit and synthetic tamper tests were added (scripts/audit-m2-live-local.ps1), awaiting operator verification to identify exact raw citation failures. Do not infer semantic answer correctness from citation syntax. M2 scientific-quality acceptance remains **OPEN**.

## M2-LIVE-02 next gate — implementation committed, local execution pending

The archived M2-LIVE-01 Qwen audit passed locally, original SHA256 bd3b35354442062a861c8ed6d4d3b49f58c3ea185a5df7321728c34ef21ed3d8. All three drafts had zero bracketed source citations. The adequate-source draft answered the fictional question but missed [S1], whereas the irrelevant-source draft transferred a manufacturer from a different device and the contradictory-source draft chose one date despite direct contradiction. M2-LIVE-02 is an explicitly **versioned prompt-only development experiment**, not a held-out benchmark: the new prompt requests either a cited sentence or INSUFFICIENT_EVIDENCE, while all outputs remain quarantined for review. It does not change RAGPipeline, citation validator, retrievers, production defaults, original results, or unsupported NLI. New tests and CPU Qwen driver await local verification; M2 scientific quality remains OPEN.

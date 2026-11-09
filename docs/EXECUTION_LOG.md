# RAG Architecture Lab — Execution log (append-only evidence journal)

This log records **work actually checked**. It is not a plan or a place to invent PASS markers. The canonical forward-looking status, gate definitions and work queue are in [PROJECT_CONTROL.md](PROJECT_CONTROL.md). Historical benchmark reports remain their original source of truth; reference them rather than overwriting or copying unsupported results.

## Required template for every future update

```markdown
### YYYY-MM-DD HH:MM -0300 — TASK-ID — concise event
- Operator / reviewer: human, CI, or named verified integration
- Branch / exact HEAD: <full sha>
- Change or observation: <what happened, avoiding assumed success>
- Verification command or run: <exact command, URL or report path>
- Evidence integrity: <artifact SHA256 when appropriate; original data location>
- Result: PASS | FAIL | PARTIAL | NO_GO | INCONCLUSIVE | BLOCKED
- Scope & limitations: <what this does NOT prove>
- Decision: <next rule/default/rollback; no silent promotion>
- Follow-up: <single next task ID>
```

## 2026-11-08 — CTRL-01 — Project management baseline prepared

- Operator / reviewer: GitHub repository inspection via connected GitHub integration; this is a docs-only planning action.
- Branch / original inspected HEAD: `feat/research-lab-architecture-catalog-20261104` at `01a6dfbd7792d1f7a214998727de1c14ce6f1a51`.
- Observation: [research PR #2](https://github.com/AlexiVion/rag-architecture-lab/pull/2) open/draft/unmerged, 229 files, 72 commits; the source research roadmap and release matrix contain superseded status lines (e.g., WEB-01 browser verification still described as pending).
- Exact CI evidence: [GitHub Actions #41935324313](https://github.com/AlexiVion/rag-architecture-lab/actions/runs/41935324313), **success** for offline research integrity at the inspected source HEAD, including Python tests/packaging, typed observatory tests/build and Chromium navigation. Direct public Pages deployment and independently adjudicated answer factuality were **not** verified.
- Scientific boundary: existing [M2 guard stress report](../benchmarks/M2_GUARD_STRESS01_OUTCOME_20261104.md) establishes negative/limited authored-template evidence; no independently assessed held-out answer-quality pass. Existing [GRF-00 report](../benchmarks/GRF00_HOTPOTQA_DEV_60_NO_GO_20261104.md) and [GRF-01 report](../benchmarks/GRF01_HOTPOTQA_DEV_FROZEN_20261104.md) retain original negative and inconclusive decisions.
- Result: **PROJECT_CONTROL_DRAFTED**; no new model/dataset executions, no repository `main` changes, no publication approvals, no claim of completed v1.0.
- Decision: create a separate reviewable documentation change and link the canonical status. Do not silently merge the 229-file research PR.
- Follow-up: CTRL-01 review/adoption -> PR-02 inventory and R0-01 external clone.

## Historical evidence index (read-only references)

- [V0 retrieval](../benchmarks/V0_RESULTS.md), [V1 reranking](../benchmarks/V1_RESULTS.md), [V1.1 depth ablation](../benchmarks/V1_1_RESULTS.md).
- [M2 synthetic Qwen controls](../benchmarks/M2_SYNTH01_QWEN_FROZEN_OUTCOME_20261104.md), [M2 guard stress](../benchmarks/M2_GUARD_STRESS01_OUTCOME_20261104.md), [M2 live Qwen limitations](../benchmarks/M2_LIVE_QWEN_BOUNDARY_20261104.md).
- [Graph-first DEV result](../benchmarks/GRF00_HOTPOTQA_DEV_60_NO_GO_20261104.md), [frozen graph-hybrid DEV result](../benchmarks/GRF01_HOTPOTQA_DEV_FROZEN_20261104.md).
- [Original v1.0 scope](RELEASE_WOW_BLUEPRINT.md), [acceptance matrix](RELEASE_EXECUTION_MATRIX.md), [research protocol](EXPERIMENT_PROTOCOL.md).

**Rule:** append future dated entries at the end; corrections must identify the incorrect entry and supply new evidence without deleting the previous observation.

## 2026-11-08 — MICRO-00 / SCOPE — Tiny-model efficiency research pivot documented

- Operator / reviewer: owner-directed research focus change; sources and repository contracts reviewed in documentation only.
- Branch / research baseline: `feat/research-lab-architecture-catalog-20261104` at `01a6dfbd7792d1f7a214998727de1c14ce6f1a51`. Planning changes are on `docs/project-control-20261108`.
- Change: [ADR-0005](adr/0005-tiny-model-efficiency-research-pivot.md), [MICRO tracking issue #11](https://github.com/AlexiVion/rag-architecture-lab/issues/11) and [PROJECT_CONTROL.md](PROJECT_CONTROL.md) introduce a primary research hypothesis on CPU-first 135M–600M open-weight generators, evidence-per-token optimization, matched baselines and independently supported-answer/abstention evaluation.
- Prior art consulted: [MiniRAG](https://github.com/HKUDS/MiniRAG), [TripletRAG](https://aclanthology.org/2026.groundlm-1.72/), [small-model context-utilization analysis](https://arxiv.org/abs/2603.11513), [BRIEF context compression](https://aclanthology.org/2025.findings-naacl.301/). Distinguish **research proposal** from novelty claim.
- Candidate official cards reviewed (license and rough scale only; revisions not pinned): [SmolLM2-135M](https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct), [SmolLM2-360M](https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct), [Qwen2.5-0.5B](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct), [Qwen3-0.6B](https://huggingface.co/Qwen/Qwen3-0.6B), [BGE-small](https://huggingface.co/BAAI/bge-small-en-v1.5).
- Verification: documentation link/readback and GitHub issue/PR presence only. **No local CPU benchmark, model inference, holdout creation, new scientific result, license redistribution certification, CI rerun or publication occurred.**
- Result: **RESEARCH_DIRECTION_DEFINED / TECHNICAL_VALIDATION_OPEN**.
- Scope & limitations: pre-existing exact ten additional model candidates and full WOW v1.0 requirements remain historic scope until formally reconciled via reviewed release acceptance amendment. Original experiments preserved.
- Decision: prioritize MICRO-00/MICRO-01 methods before changing implementation. Negative/no-gain results count as valid research.
- Follow-up: MICRO-00 and MICRO-01.

## 2026-11-09 — REL-PORTFOLIO-01 — Scoped release candidate staged (verification pending)

- Operator: automated connected GitHub writes and prior audited CI artifact review.
- Starting research source: `991271c691edfbaf26eb0e02e9d74e7ae00f3c88` following merger of documentation PR #10.
- Working branch: `release/portfolio-v0.1-20261109` (exact post-PR SHA to record after integration).
- Change: create release [scope](PORTFOLIO_RELEASE.md), [notes](RELEASE_NOTES_v0.1.0.md), [LinkedIn draft](LINKEDIN_LAUNCH.md), improve README landing, fix logo layout and make a scoped GitHub release follow a **successful Pages deployment** only.
- Evidence: original [#41935324313](https://github.com/AlexiVion/rag-architecture-lab/actions/runs/41935324313) Chromium/browser artifact included Overview/Experiments/Graph screenshots and generated npm dependency lockfile. Visual inspection completed; these artifacts correspond to the **earlier** research commit `01a6dfbd` and do **not** prove the new branch passed CI.
- Result: **IMPLEMENTED / VERIFICATION PENDING**. No new benchmark/LLM calls, no unsupported science claims, no Pages URL verified, no tag/release claimed.
- Follow-up: CI for scoped release PR; integrate research branch only upon valid checks; verify Pages and final public release.

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

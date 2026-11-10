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

## 2026-11-09 — REL-PORTFOLIO-01 — Scoped release PR #14 CI PASS and merged; main deployment still pending

- Operator: GitHub Actions offline verification; source review of 236-file research PR history.
- Evidence: [workflow #42622741997](https://github.com/AlexiVion/rag-architecture-lab/actions/runs/42622741997) **SUCCESS** for `6e53f1e0427a5c711211013b1d632cd5cdf017f6`. Verified Python v3.11 tests/package/CLI/readiness, TypeScript test/build and Chromium visual/provenance/mobile E2E.
- Integration: [PR #14](https://github.com/AlexiVion/rag-architecture-lab/pull/14) **MERGED**, squash integration commit `7d7ee6594643f7ecb583d43abcdc5eb437adf0a1` into research branch; no science data modifications. Previous project-control [PR #10](https://github.com/AlexiVion/rag-architecture-lab/pull/10) also merged.
- Audit: research diff contained retrieval/graph and deterministic evaluation code, documentation, three-document fictional graph evidence fixture, static frontend and no readily recognizable secret tokens in per-file patch scan. This **does not certify a complete security or dependency audit**. MIT code license; external model/data licenses are independent.
- Follow-up fix: `apps/observatory/package.json` version aligned to portfolio `0.1.0` at `a4481f6f52fef9c1d21b0cceab869d183461cfe1`; this later SHA **needs its own exact-head CI**.
- Status: **PR14_CI_PASS / RESEARCH_INTEGRATION_PASS; MAIN_MERGE / PAGES / RELEASE_OPEN**. No unverified public URL or automatic factual quality claim.
- Next: exact-head CI on PR #2, integrate to main, verify GitHub Pages and conditional release outcome. Do not complete REL-PORTFOLIO-01 until true.

## 2026-11-09 — MICRO-00..05 — New CPU-first research tools staged, experimental evidence not yet created

- Operator: connected GitHub source edits and independent GitHub Actions testing.
- Working PR: [#15](https://github.com/AlexiVion/rag-architecture-lab/pull/15), branch `feat/micro-rag-research-foundation-20261109` from `main` `0e7c1c43d65e8d79e3e80ac794b1fd3965ef44ca`.
- Implemented: explicit proposed 1M–600M model metadata with pending revision/license audit; source/group split-leakage checks; DEV-only dataset-hashed BM25 matched no-RAG/naive/spans/extractive quote/oracle preparation, optional local-only causal-LM drafts, original-source offset and citation trace, same counter token budgets; separate double-reviewer consensus scoring (no entailment inference).
- Tests: dedicated `tests/test_micro_*.py` plus existing full suite. [Early PR CI #42654181568](https://github.com/AlexiVion/rag-architecture-lab/actions/runs/42654181568) **SUCCESS** for branch `2eb22c0ababa1df2bfe5561d12ead58eb8715bca`; later source and docs revisions need exact-head CI. No measured real tiny-model claims.
- Safety boundaries: `holdout` cases explicitly rejected by smoke runner; unreviewed generation stays draft; quote-only text is marked nonanswer; oracle context labeled diagnostic; no automatic publication or model download; relative tokenizer-count limitations disclosed.
- Scientific result: **NOT MEASURED**. No new weights loaded, new human labels, independent heldout, semantic faithfulness, GraphRAG win, or proven optimization.
- Follow-up: verify exact PR HEAD CI, integrate PR; then separately select and pin real model revisions/license, obtain human-labelled natural-language cohorts and measure resource-vs-supported-answer Pareto tradeoffs on actual CPUs.

## 2026-11-09 — MICRO-LIVE-00 — Two real open-weight CPU model runs

- Operator: GitHub Actions public Linux CPU runner; connected GitHub job and artifact inspection.
- Tested source: `0ae0e36982d96672a995554002138dcb9c77de8c`, [workflow #42656944850](https://github.com/AlexiVion/rag-architecture-lab/actions/runs/42656944850) **SUCCESS**; [offline CI #42656944886](https://github.com/AlexiVion/rag-architecture-lab/actions/runs/42656944886) **SUCCESS**. [PR #16](https://github.com/AlexiVion/rag-architecture-lab/pull/16) merged into main `6083e061751817d699492e289e9b0c135ebfacd0`.
- Real checkpoints: Pythia-14M `cf967c0a9a04383db6f7b1108d86b2962634b4ac` (weight SHA256 `116a02532db461f91386a5b20f942ff2c8d4de7341e21b55caafc3d7b25f49a1`); SmolLM2-135M-Instruct `12fd25f77366fa6b3b4b768ec3050bf629380bac` (weight SHA256 `5af571cbf074e6d21a03528d2330792e532ca608f24ac70a143f6b369968ab8c`). Metadata license Apache-2.0.
- Artifact `micro-real-14m-and-135m-diagnostic` ID `13691264798`, source and result hashes documented in [MICRO real model pilot](MICRO_REAL_MODEL_PILOT.md). It contains no redistributed weights.
- Execution: **one artificial DEV question**, three modes per model (none, naive, source spans), **16 new tokens max**, CPU only, all model prompts produced real unreviewed drafts.
- Observed: Pythia output was incoherent/incomplete; SmolLM2 retrieved-context outputs quoted relevant source text but did not form a validated complete factual answer. **No answer correctness, hallucination risk, multi-query accuracy or efficiency gain measured.** The first generation contained cold-start overhead, invalidating naive latency comparisons.
- Result: **REAL_MODEL_ENGINEERING_SMOKE_PASS / SCIENTIFIC_EVALUATION_OPEN**.
- Follow-up: freeze natural-language paired DEV/CALIBRATION/HOLDOUT, independently review source support and answerability, warm/check model-specific full token counts and peak RSS; then run scientifically controlled ablations and GraphRAG/agentic studies.

## 2026-11-09 — MICRO-NATURAL-QA-01/02 — Real natural questions, measured negative outcomes

- Operator / verification: GitHub Actions real pinned public-weight CPU execution plus an independent ZIP/JSON SHA256 inspection of retrieved CI artifacts. No human scientific answer review was fabricated.
- Source integration: [PR #18](https://github.com/AlexiVion/rag-architecture-lab/pull/18) into main `a88057560352b6cdf2488830b89ec18ce42786cd`; 32-case compact/verbose ablation [PR #19](https://github.com/AlexiVion/rag-architecture-lab/pull/19) into main `7b385cbf6d67709e0be7665359ce6e277ac81abe`.
- Exact CI: [full offline CI #42662178199](https://github.com/AlexiVion/rag-architecture-lab/actions/runs/42662178199) **SUCCESS**, and [real Pythia14M/SmolLM2-135M CPU run #42662178196](https://github.com/AlexiVion/rag-architecture-lab/actions/runs/42662178196) **SUCCESS**. Initial 8-question public DEV checkpoint [#42660611766](https://github.com/AlexiVion/rag-architecture-lab/actions/runs/42660611766) also SUCCESS but was superseded by 32-question article-cluster cohort.
- Data: official **Stanford SQuAD2 DEV**, CC BY-SA 4.0, exact source SHA256 `80a5225e94905956a6446d296ca1093975c4d3b3260f1d6c8f68bc2ab77182d8`; 32 natural questions (16 answerable and 16 originally unanswerable), 16 independent article groups, 128 DEV source/distractor paragraphs.
- Experimental controls: five within-model matched modes (no retrieval, BM25 naive verbose/compact, query-aware original-source spans verbose/compact), same 128 checkpoint evidence-token cap and 24-generation-token cap; model revisions, weights, source trace, p50/p95 and full-process peak RSS recorded. Model weight and QA trace JSON hashes independently verified.
- **Measured negative result:** Pythia-14M correctly refused **1/16** officially unanswerable QAs only in spans-compact; **zero exact answers to all 16 answerable questions across all modes**. SmolLM2-135M got **0/32 reference exact matches** in every mode. Gold document Recall@5 on answerable questions was **16/16** for both models, yet generator quality remained unusable in this narrow setting. Source exposure improved with some compact formats but is NOT proof of supported answers. Descriptive DEV article-cluster F1 bootstrap intervals are reported without declaring significance.
- Integrity: Pythia artifact `micro-squad2-pythia-14m` ID `13693834506`; Smol artifact `micro-squad2-smollm2-135m` ID `13695247336`; both downloaded and JSON contents independently checked against manifest SHA256. [Full report](MICRO_NATURAL_QA_32_RESULTS.md) contains exact checksums.
- Decision: **ENGINEERING_PASS / SCIENTIFIC_GENERATION_NO_GO**. Published SQuAD DEV is not untouched holdout; SQuAD answerability is relative to original paragraph, not all added documents; no independent semantic faithfulness/hallucination verdict; limited 24-token generation cap, model-specific prompt/role limitations, cross-CPU runner comparability caveat. Do not publish a tiny RAG efficiency win.
- Next gate: matched original-answer oracle window + base-vs-instruct prompt controls and truly independent multi-domain human-labeled answerability/source-support holdout. Keep production/Pages release configuration separate.

## 2026-11-09 — MICRO-ORACLE-01 — Gold-answer context and model-role prompt diagnostics

- Operator: official Pythia-14M / SmolLM2-135M pinned safe-weight CPU execution, GitHub Actions; independently downloaded exact outputs and recomputed zip JSON SHA256 checks.
- Code: [PR #21](https://github.com/AlexiVion/rag-architecture-lab/pull/21) merged as `1ae1e1e71e4b57fa2ae5558063af779d58233b74`; [real model run #42698423912](https://github.com/AlexiVion/rag-architecture-lab/actions/runs/42698423912), [offline/browser tests #42698423895](https://github.com/AlexiVion/rag-architecture-lab/actions/runs/42698423895), [ordinary SQuAD2 regression #42698423705](https://github.com/AlexiVion/rag-architecture-lab/actions/runs/42698423705) all **SUCCESS** at exact PR HEAD.
- Official public SQuAD2 DEV SHA256 `80a5225e94905956a6446d296ca1093975c4d3b3260f1d6c8f68bc2ab77182d8`, selected corpus fingerprint `6127d2502bd0a3f7c7cedb184db465e9fd16fb74cb62339b97bebbed26502dbc`. Both 14M/135M received the **exact original reference answer inside a privileged source window for 16/16 positive cases**. Six model/mode combinations per checkpoint (legacy vs role-adapted prompt × actual retrieval, gold paragraph, gold-bearing window) yielded **0 exact answers in all six conditions**. No independent source-entailed answer success established.
- Artifacts: `micro-oracle-prompt-pythia-14m` ID `13711235266` and `micro-oracle-prompt-smollm2-135m` ID `13711531285`. Source excerpts, rendered prompt tokens and model outputs were audited; JSON trace and metrics bytes matched each artifact's manifest SHA256. Original weights/corpus not uploaded to artifacts.
- Result: **ENGINEERING_PASS / GENERATIVE_EXACT_ANSWER_NO_GO**. Gold-answer oracle is privileged upper bound and does not establish learning, retrieval or independent model quality; prompt adjustments were designed after observed DEV failures. No reliable new quality improvement shown. 
- Decision: compare explicitly task-trained extractive reader and require genuinely independent domain-separated blinded evidence review before any empirical optimization claim.

## 2026-11-09 — MICRO-EXTRACTIVE-01 — 33.4M specialized encoder CPU baseline

- Model: `deepset/minilm-uncased-squad2`, exactly pinned official revision `934656cdda79824eabf503ed56e15c01ddbdbe3f`; safe-weight SHA256 `240478c7251d5e55be35feb47177054b960259b9328af662ea3cee87ce9755a6` (133,466,376 bytes), **CC BY 4.0 metadata**. The model was specifically trained for SQuAD2 QA: task-matched training advantage; fundamentally not comparable as a parameter count win against unsupervised base/instruction models.
- Code: [PR #22](https://github.com/AlexiVion/rag-architecture-lab/pull/22) merged at `5bf037da83b3ae8151cfd82307e9c3202d306137`. [Exact pinned CPU run #42700210942](https://github.com/AlexiVion/rag-architecture-lab/actions/runs/42700210942) **SUCCESS** and [offline/browser CI #42700211099](https://github.com/AlexiVion/rag-architecture-lab/actions/runs/42700211099) **SUCCESS**. No real GPU inference or paid API.
- Experimental conditions: same SQuAD2 DEV exact file, same 32 questions and same fingerprint as above. Actual BM25 **top1** + reader: **24/32 reference exact match**, 11/16 positives correct, 13/16 original-paragraph negatives correctly refused; gold source present 15/16 positives; mean model CPU forward **36.91 ms/query**. Actual BM25 **top5** + same reader: **23/32** exact match, 11/16 positives, 12/16 original-paragraph negatives; gold source 16/16, mean model CPU forward **202.74 ms/query**. Privileged original gold paragraph: 24/32. Context-derived answer strings were original-source exact slices, but this is NOT semantic support verification.
- Artifact: `micro-minilm-33m-extractive-qa-dev` ID `13710033678`; zipped model-source manifest and score file independently checked: SHA256 of `reference_qa_metrics.json` `2d0f07a73b24e7f736f505c4010ecd28e49965871566a5a19609cec7ed10e027` matched manifest. Whole-process peak RSS **1,268,960 KiB**; not model-only; device a public GitHub Ubuntu CPU runner, not owner's Ryzen.
- Result: **TASK_MATCHED_DEV_REFERENCE_QA_PASS / INDEPENDENT_SCIENTIFIC_VALIDATION_OPEN**. Specialized reader can extract short answers on this trained-for task; top5 increased CPU cost without improving DEV reference EM. This is **not** a universal top1 policy win or a fair representation/architecture comparison. Reference EM and exact source slices are neither human semantic entailment nor clinical/business safety.
- Follow-up: [full report](MICRO_ORACLE_VS_EXTRACTIVE_RESULTS.md), independent domain-separated human-labeled source-support holdout, calibration of no-answer policy, matched training and CPU/RAM/energy evaluation. M2 generation auto-publication remains NO-GO, and unrelated GitHub Pages admin blocker #13 persists.

## 2026-11-09 — MICRO-CF-01 — Novel full-corpus contradiction/absence audit: verified real CPU execution

- Operator: connected GitHub source edits, pinned Hugging Face safetensors on real hosted CPU, independent downloaded ZIP byte-level JSON SHA256 verification. No user machine or private/paid API used.
- Implementation [PR #24](https://github.com/AlexiVion/rag-architecture-lab/pull/24) MERGED at `7aa88c6b56bf66bada0a674d356a7eb94dbf0250`; [actual pinned model CPU run #42727787830](https://github.com/AlexiVion/rag-architecture-lab/actions/runs/42727787830) **SUCCESS** and [full offline Python/UI/browser CI #42727787913](https://github.com/AlexiVion/rag-architecture-lab/actions/runs/42727787913) **SUCCESS**, both exact head `7fa894d33e2a909a1df0646691322c32d28dc30c`.
- Model same official SQuAD2 fine-tuned `deepset/minilm-uncased-squad2@934656cdda79824eabf503ed56e15c01ddbdbe3f` (CC BY 4.0 metadata), original safetensors `240478c7251d5e55be35feb47177054b960259b9328af662ea3cee87ce9755a6`. New MICRO-CF fictional corpus `seed=20261109` was generated with 36 fictional entities, 72 docs, 108 questions and 3 entity/source-disjoint partitions; each has 18 true answerable, 12 truly absent across its full relevant entity corpus and 6 conflicting seals. **Synthetic template labels, no human annotations, AUDIT not sealed**.
- Exact **AUDIT** outcomes (36 questions): BM25 top1 + MiniLM **30/36 strict correct** (18/18 answerable, 12/12 missing correctly refused, **0/6 conflicts correctly refused**); accepts 24, **6 wrong** = 25% conditional wrong accept. BM25 top3 **29/36** (18/18 answerable, 11/12 missing, 0/6 conflicts), accepts 25 with **7 wrong** = 28% conditional wrong accept. Top3 required **108** MiniLM reader calls against top1 **36**, reader call wall time **1,380.7ms** vs **459.7ms** for 36 questions, same CPU worker and sampled candidates.
- **Safety gate:** frozen CALIBRATION threshold search with ≥5 accepted and ≤15% observed wrong acceptance found no permitted candidate, so fail-closed **REFUSE_ALL** correctly selected. AUDIT zero wrong accepts, but **zero answered useful questions**. Do NOT treat this as successful selective QA.
- **Controls showing synthetic shortcuts:** manually coded template-based zero-neural regex policy scored **36/36** at zero neural forwards. **POST-HOC** source-conflict template guard applied after viewing first AUDIT errors: top1 **36/36**, top3 **35/36**, but these outcomes **are not independent test evidence** and must be labeled contaminated/overfit. The guard used only retrieved source text at inference, yet its design drew from revealed audit labels.
- Resource trace: process peak RSS **1,212,436 KiB** (~1,184MiB), 2 CPU threads, PyTorch 2.15.0+cu132 **executed on CPU**. Reader call wall time includes tokenization+forward+decode and is not pure model forward; no energy measurement. Source quote provenance is a separate assertion from answer correctness and semantic entailment.
- Independent artifact checks: [CPU workflow #42727787830](https://github.com/AlexiVion/rag-architecture-lab/actions/runs/42727787830), artifact `micro-counterfactual-33m-cpu-diagnostic` ID **13724000411**. Downloaded ZIP's `policy_results.json` SHA256 **`d10fba739697f001dab8c24a4f1e998679ce3cea579e6e92b122c912e5782fec`**, `frozen_calibration.json` SHA256 **`e15ade1d00c3e40101cae06109a0135771ecfb4cebdc9d6aa38d747de615bfb4`** matched manifest. Per-partition original JSON hashes all matched. Full report [MICRO_COUNTERFACTUAL_REAL_CPU_RESULTS.md](MICRO_COUNTERFACTUAL_REAL_CPU_RESULTS.md).
- Result **ENGINEERING_PASS / CORPUS_CONFLICT_SAFETY_NO_GO / REAL_WORLD_UNVERIFIED**. Last SQuAD2-trained encoder accuracy was specific to task and did not check source contradictions. Template-only solutions may beat neural approaches in narrow domains, but all current synthetic styles are publicly visible. Scientific work remains OPEN.
- Next work: genuinely independently authored and human-double-reviewed corpus, explicit source authority/time, new language and style shifts, NLI/claim-consistency non-template baselines, risk/coverage with honest independent confidence intervals, matched whole-stack CPU memory/latency and no paper-level novelty claims. Existing Pages admin blocker #13 separate.

## 2026-11-10 — MICRO-RAGABILITY-01 — External 53-row / 43-group conflict benchmark; two pinned CPU NLI models

- Operator: connected GitHub source integration, pinned Hugging Face dataset/model downloads in separate hosted CPU jobs, SHA256 verification of returned artifacts, matched paired source-group bootstrap analysis.
- Code [PR #26](https://github.com/AlexiVion/rag-architecture-lab/pull/26) MERGED at `5b751d2dbadff32e1fcd338c7dd814f0066839b8`; exact evaluation source head `d1d37fa0acafbd06e2af7e501987ca4ad6e03812`. [Offline Python/TypeScript/Chromium #42735349153](https://github.com/AlexiVion/rag-architecture-lab/actions/runs/42735349153) and [real CPU matrix #42735349293](https://github.com/AlexiVion/rag-architecture-lab/actions/runs/42735349293) **SUCCESS**.
- Dataset: OFAI RagabilityCorpus, CC-BY-SA-4.0, revision `2251634ed365bfca55e7d808290b0cf2c5fde730`, source TSV SHA256 `e973f5ac7b4881e2cafe23f39b837643878ea6afdb769d9afa30ff66e93c8285`. 53 rows / 43 contradiction_ID groups / 318 derived pair cases (106 conflict, 212 non-conflict). One blank optional WikiContradict_ID retained and counted, never fabricated. Public/adapted benchmark derived from human-annotated WikiContradict, not sealed and not independently annotated by this project.
- DeBERTa-v3-xsmall revision `a150876415327c80daeff35ca6f68f5ed8cf5c24`, 70,831,107 params, 283,353,172 weight bytes, safetensors SHA256 `4e4fc4977f8d29d2a164255c8f69b9d6c158deeb309bb5e70445b94666ccd9e9`, Apache-2.0. MiniLM2 revision `b95119ce93d3e065de6214e38cd4a97b0f2f2c6d`, 82,120,707 params, 328,499,560 bytes, safetensors SHA256 `ec9c5b6a08b60d7a01b465c7ed44b496244dfd1bed3274c95875a74cea89ab35`, Apache-2.0.
- Main symmetric results: both **261/318 = 82.08% accuracy**. DeBERTa balanced accuracy **80.19%**, macro F1 **79.97%**, contradiction precision **72.48%**, recall **74.53%** (79 TP / 27 FN / 30 FP / 182 TN). MiniLM balanced accuracy **78.07%**, macro F1 **79.04%**, precision **76.92%**, recall **66.04%** (70 TP / 36 FN / 21 FP / 191 TN).
- Pair types: DeBERTa original implicit c1/c2 **35/53**, MiniLM **24/53**; explicit c2/c3 DeBERTa **44/53**, MiniLM **46/53**. DeBERTa raised more false positives across the non-conflict pairs.
- Paired bootstrap: 10,000 matched resamples of the same 43 source-conflict groups, seed 20261109. DeBERTa-minus-MiniLM balanced accuracy **+2.17 pp**, 95% interval **[-2.23,+6.94]**; accuracy **+0.05 pp**, interval **[-3.46,+3.92]**; macro F1 **+1.00 pp**, interval **[-3.03,+5.60]**. **No overall winner**. Original implicit c1/c2 subgroup delta **+20.62 pp**, interval **[+3.92,+38.18]**, exploratory and not multiple-comparison adjusted.
- Both models passed only **1/3** generic NLI sanity controls; both misclassified the generic neutral example as contradiction and generic entailment example as neutral under the symmetric aggregation. This materially limits any trust claim.
- CPU costs: DeBERTa 636 directional inputs / 42,432 tokens / **19.09 s** batch wall time / **1.741 GB** peak RSS; MiniLM 636 / 45,344 / **20.27 s** / **1.613 GB**. Two PyTorch CPU threads. Timing includes tokenizer + model forward + softmax; no retrieval, generation, energy or end-to-end latency.
- Artifact IDs: DeBERTa `13726542626`, ZIP SHA256 `1014841edfaa9bf7d8b7f80f321fcffd792e61c918af64475ba9c61858c6cbf7`; MiniLM `13726578149`, ZIP SHA256 `74123d84e093e91011c0eb81d8ac996c97f0d76a75b796d80652c1faabd02008`. Results JSON SHA256: DeBERTa `56d670af421f36f7e8dbe583876ad791783f1f0068b131c9eac5e2146ee4489e`; MiniLM `774aad5ddc096227a6be0bf490a5ed63baeff07657582e483c554b0cf1eeb973`. Full report [MICRO_RAGABILITY_NLI_RESULTS.md](MICRO_RAGABILITY_NLI_RESULTS.md); raw dataset text and weights were not redistributed.
- Verdict **PAIRWISE_NLI_ENGINEERING_PASS / NO_OVERALL_WINNER / SOURCE_ARBITRATION_NO_GO / SEALED_HOLDOUT_OPEN**. The benchmark measures only pairwise conflict labels. No retrieval, query-conditioned claim extraction, source authority, calibrated refusal, or end-to-end RAG reliability was measured.
- Next: MICRO-RAGABILITY-02 oracle short/long answer-claim normalization (separate claim extraction from verification); compare quantized DeBERTa AVX2 ONNX against FP32 for quality/cost parity; then ConfRAG real-web answer-cluster and reason-coverage evaluation. Human-reviewed independent multi-domain test remains mandatory before publication or deployment.

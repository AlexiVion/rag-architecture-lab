# RAG Architecture Lab

**Complete WOW v1.0 program:** [Release blueprint](docs/RELEASE_WOW_BLUEPRINT.md) · [Ten-model proposed registry](experiments/model_matrix_10_proposed.json) · [Master tracking issue #9](https://github.com/AlexiVion/rag-architecture-lab/issues/9). **This is a plan, not completed functionality.**

**Open-source architecture research laboratory**, not a hosted RAG product. The goal is to implement and benchmark composable RAG strategies, publish reproducible evidence, and document engineering trade-offs. Existing V0/V1/V1.1 results are preserved; the V2 code requires an independently recorded local smoke test and answer-quality evaluation.

**Research guide:** [Reference architecture](docs/LAB_ARCHITECTURE.md) · [Architecture catalog](docs/ARCHITECTURE_CATALOG.md) · [Experiment protocol](docs/EXPERIMENT_PROTOCOL.md) · [Evidence-gated roadmap](docs/ROADMAP.md) · [Contributing](CONTRIBUTING.md).

A from-first-principles lab for implementing, benchmarking, and comparing Retrieval-Augmented Generation retrieval architectures under controlled conditions.

> **Current state**
>
> V0 retrieval benchmarking, V1 cross-encoder reranking, and V1.1 candidate-depth ablation are complete on the designated local Windows machine. The retrieval phase is now closed with Hybrid RRF as the default path and 10-candidate cross-encoder reranking retained as an optional quality mode. The next phase is V2: generation, context construction, and citations.

## GRF-00 — Run the first interactive evidence observatory

The experimental **GRF-00 provenance graph** is now implemented as a bounded (1–2 hop) graph-first retriever with original-document BM25 fallback, exact source-quote validation and inspectable path traces. A responsive static viewer is available at [apps/explorer](apps/explorer/index.html); its three sample questions are **fictional, curated demonstration fixtures**, not measured scientific quality.

From an existing Windows clone with its Python environment ready, run:

```powershell
git pull --ff-only origin feat/research-lab-architecture-catalog-20261104
.\scripts\run-observatory-local.ps1
```

The command runs the full test suite, re-exports the verified static JSON and opens the **local viewer at http://127.0.0.1:4874/**. Stop the server with Ctrl+C. It makes **no paid API calls**, uses no Qwen and does not download models for this demonstration. Linux/macOS users can run the Python export and standard local HTTP server as described in [the GRF-00 guide](docs/GRF_00_SEED_GRAPH.md).

**Do not treat the demo as a GraphRAG benchmark or a finished v1.0.** Source-quoted two-hop traversal and the viewer are implemented; scalable entity extraction, real multi-hop quality results, M2 answer-quality validation, the ten new model experiments and a hosted explorer remain pending. The current feature branch PR is still draft.

## GRF-00 — Real-document paired benchmark: negative result (2026-11-04)

The completed local experiment measured **BM25 vs source-quoted graph + BM25** over the same candidate article contexts for 60 deterministic HotpotQA DEV bridge questions. The graph builder never reads the gold supporting facts; those are reserved for ranking evaluation. First run downloads approximately 46 MB of checksum-verified **CC BY-SA 4.0** data; no models are loaded:

```powershell
.\scripts\run-hotpotqa-graph-benchmark-local.ps1
```

This study measures *supporting-document Recall@1/3/5* and paired uncertainty, not answer faithfulness or an open-domain graph benchmark. [Design and limitations](docs/GRF_00_HOTPOTQA_STUDY.md). The user executed the script successfully; all tests passed. An independent saved-report audit subsequently passed with SHA256 `962dc3b12d0086857ad94198cf2b1fff7a49ca5f7df069e9575a6daaf778f016`: all graph-path-present cases combined had **−17.5 percentage points Recall@5** (11 losses, 0 wins, 29 ties); the 20 no-path cases exactly matched BM25. On 60 DEV bridge questions, BM25 beat Graph+BM25: Recall@1 0.4333 vs 0.3500; Recall@3 0.6833 vs 0.5917; Recall@5 0.8250 vs 0.7083. All paired bootstrap CIs for the differences were negative. **NO-GO for this graph-first policy in this DEV sample**, not for all GraphRAG. The raw per-query JSON remains local. Use the post-run audit to verify and display the aggregate in the observatory.

## Why this project exists

RAG is not one architecture. Retrieval choices create different trade-offs in relevance, robustness, latency, and complexity. This lab isolates those choices and measures them instead of treating a single RAG pipeline as universally best.

The project intentionally avoids high-level RAG frameworks in its core implementation. Retrieval, fusion, reranking orchestration, evaluation, and benchmark control are implemented directly so their behavior remains inspectable.

## V0 — Retrieval comparison

Research question:

**How do dense, sparse, and hybrid retrieval strategies perform under identical benchmark conditions?**

V0 compares:

- **Dense retrieval** — local sentence embeddings + cosine similarity
- **BM25** — lexical retrieval implemented in this repository
- **Hybrid retrieval** — dense + BM25 combined with Reciprocal Rank Fusion (RRF)

Metrics:

- Recall@K
- Mean Reciprocal Rank (MRR@K)
- nDCG@K
- Mean and p95 query latency

### V0 quality results

Full benchmark: **BEIR SciFact test — 5,183 documents, 300 queries**.

| Pipeline | MRR@10 | nDCG@10 | Recall@5 | Recall@10 |
|---|---:|---:|---:|---:|
| BM25 | 0.6328 | 0.6647 | 0.7243 | 0.7849 |
| Dense | 0.6047 | 0.6451 | 0.7379 | 0.7833 |
| **Hybrid RRF** | **0.6484** | **0.6865** | **0.7571** | **0.8179** |

Hybrid RRF produced the strongest reported quality metrics under the V0 configuration. BM25 outperformed Dense on MRR@10, while Dense achieved slightly higher Recall@5 than BM25.

The original V0 run predates the local-only benchmark policy, so its latency values are retained in the detailed experiment record but are not used as canonical hardware comparisons. V1 and later latency decisions use the designated local machine.

See [`benchmarks/V0_RESULTS.md`](benchmarks/V0_RESULTS.md) for the full methodology and original V0 record.

## V1 — Cross-encoder reranking

Research question:

**Does reranking Hybrid RRF candidates with a local cross-encoder improve top-K retrieval quality enough to justify its additional latency?**

V1 keeps the V0 Hybrid pipeline as the first stage, retrieves 50 candidates, and reranks them with the pretrained local model `cross-encoder/ms-marco-MiniLM-L-6-v2`.

```text
Dense + BM25 -> RRF -> top 50 candidates -> Cross-Encoder -> top K
```

### Canonical local environment

- CPU: AMD Ryzen 7 5700U with Radeon Graphics
- 8 cores / 16 logical processors
- RAM: ~15.3 GiB
- Windows 11 64-bit
- Python 3.11.9
- Paid APIs: none

### V1 canonical local results

| Pipeline | MRR@10 | nDCG@10 | Recall@5 | Recall@10 | Mean latency | p95 latency |
|---|---:|---:|---:|---:|---:|---:|
| Hybrid RRF | 0.6484 | 0.6865 | **0.7571** | 0.8179 | **34.53 ms** | **53.09 ms** |
| Hybrid + Cross-Encoder (50) | **0.6615** | **0.6944** | 0.7449 | **0.8272** | 3706.43 ms | 4184.39 ms |

The reranker improved MRR@10 by about **2.0% relative**, nDCG@10 by about **1.2%**, and Recall@10 by about **1.1%**, while Recall@5 decreased about **1.6%**. Mean latency increased roughly **107.3x** on the canonical local CPU environment.

**V1 decision:** 50-candidate cross-encoder reranking is a **NO-GO as the default architecture** on this machine. The quality gain is real but too small to justify several seconds of query latency.

See [`benchmarks/V1_RESULTS.md`](benchmarks/V1_RESULTS.md) for the complete canonical result and interpretation.

## V1.1 — Candidate-depth ablation

V1.1 asks whether smaller reranking candidate sets retain most of the quality improvement while reducing latency.

| Candidate depth | MRR@10 | nDCG@10 | Recall@5 | Recall@10 | Mean latency | p95 latency |
|---:|---:|---:|---:|---:|---:|---:|
| Hybrid baseline | 0.6484 | 0.6865 | 0.7571 | 0.8179 | ~31–38 ms | ~46–62 ms |
| **10** | 0.6600 | 0.6914 | **0.7660** | 0.8179 | **744.11 ms** | **893.12 ms** |
| **20** | **0.6618** | 0.6926 | 0.7389 | 0.8211 | 1634.30 ms | 1887.84 ms |
| **50** | 0.6615 | **0.6944** | 0.7449 | **0.8272** | 3706.43 ms | 4184.39 ms |

The 10-candidate configuration produced the best measured reranking trade-off: it preserved most of the MRR@10 improvement from the 50-candidate setup, improved Recall@5, and cut mean reranking latency from ~3.7 s to ~0.74 s.

**Final retrieval decision:**

```text
Default / fast mode:
Dense + BM25 -> RRF -> top K

Optional / quality mode:
Dense + BM25 -> RRF -> top 10 candidates -> Cross-Encoder -> top K
```

Universal cross-encoder reranking remains a **NO-GO as the default path**. The 10-candidate reranker is retained as an optional/adaptive stage for cases where additional ranking quality can justify sub-second CPU latency.

See [`benchmarks/V1_1_RESULTS.md`](benchmarks/V1_1_RESULTS.md) for the full ablation and decision.

## Benchmark

The default benchmark is **BEIR SciFact (test)** via `ir_datasets`.

- 5,183 documents
- 300 test queries
- relevance judgments (qrels) for objective retrieval evaluation

For a fast smoke test, `nano-beir/scifact` can also be used.

## Principles

1. **Same corpus, same queries, same conditions.** Change one architectural decision at a time.
2. **From first principles where it matters.** BM25, cosine retrieval, RRF, evaluation metrics, and pipeline orchestration are implemented here.
3. **Models are dependencies; system architecture is ours.** Local pretrained models may provide embeddings or pairwise relevance scores, but the retrieval system around them is implemented in this project.
4. **No paid API required.** Current experiments use public benchmark data and local open-source models.
5. **Benchmark locally.** Canonical benchmark computation and latency measurements run on the same local machine/server, not on GitHub-hosted Actions runners.
6. **Measure before expanding.** New components are added only when they answer a concrete experimental question.

## Quick start — Windows local machine/server

Requirements: Python 3.11+ and PowerShell.

```powershell
git clone https://github.com/AlexiVion/rag-architecture-lab.git
cd rag-architecture-lab
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup-local.ps1
```

Run the new **spec-driven architecture comparison** (exploratory, BM25-only smoke):

```powershell
.\\scripts\\run-research-local.ps1
```

This runs an independent baseline and a Parent-Child retriever with shared evaluation metrics. See [experiment runner](docs/EXPERIMENT_RUNNER.md) for JSON specs, supported adapters, and clear limitations. No output should be described as a validated architecture winner without applying the [experiment protocol](docs/EXPERIMENT_PROTOCOL.md).

Run V1 locally:

```powershell
.\scripts\run-v1-local.ps1
```

Run the V1.1 candidate-depth ablation locally:

```powershell
.\scripts\run-v1-1-local.ps1
```

Generated JSON benchmark results are written to:

```text
benchmarks/results/
```

The first model-backed run downloads the configured open-source models locally. No paid API key is needed.

## Project structure

```text
src/raglab/
  core/          Shared data types
  datasets/      Benchmark adapters
  embeddings/    Local embedding providers
  retrieval/     Dense, BM25, Hybrid, and reranking retrievers
  fusion/        Rank-fusion algorithms
  evaluation/    Retrieval metrics and benchmark runner
  cli.py         Command-line interface

scripts/         Local Windows setup and benchmark runners
tests/           Unit tests for algorithms and pipeline behavior
docs/            Scope, architecture, methodology, and local execution policy
benchmarks/       Recorded experiment summaries and generated JSON results
```

## Reproducibility

Each benchmark result records the dataset, pipeline configuration, K values, model configuration, aggregate metrics, per-query rankings, latency, and runtime environment. Local runs write timestamped JSON artifacts to `benchmarks/results/`.

Canonical experiment summaries also record the local hardware, operating system, Python version, and experiment configuration so latency comparisons remain meaningful.

## Roadmap

- ✅ **V0:** Dense vs. BM25 vs. Hybrid retrieval
- ✅ **V1:** Cross-encoder reranking — canonical local benchmark complete
- ✅ **V1.1:** Candidate-depth efficiency ablation — final retrieval decision complete
- 🧪 **V2:** Generation, context construction, and citations
- **V3:** Trace/observability model and interactive inspection
- **V4:** Web observatory and benchmark visualization
- **Later experiments:** query rewriting, multi-query retrieval, parent-child retrieval, contextual retrieval, adaptive/agentic RAG, GraphRAG

See [`docs/SCOPE.md`](docs/SCOPE.md), [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), [`docs/EXPERIMENTS.md`](docs/EXPERIMENTS.md), and [`docs/LOCAL_EXECUTION.md`](docs/LOCAL_EXECUTION.md).

## Cost

The current experiments run at **$0 paid API cost**. They use public benchmark data and local open-source models. No managed vector database or paid LLM API is required.

## References

- Thakur et al. (2021), **BEIR: A Heterogeneous Benchmark for Zero-shot Evaluation of Information Retrieval Models**
- Wadden et al. (2020), **Fact or Fiction: Verifying Scientific Claims (SciFact)**
- Cormack, Clarke & Buettcher (2009), **Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods**
- Robertson & Zaragoza (2009), **The Probabilistic Relevance Framework: BM25 and Beyond**

## Status

The initial retrieval phase is complete. Hybrid RRF is the default retrieval architecture. A 10-candidate cross-encoder reranker remains available as an optional/adaptive quality mode. The next project phase is **V2: generation, context construction, and citations**.

## Latest verified graph research (2026-11-04)

- **GRF-00:** Graph-first vs BM25, 60 HotpotQA DEV questions; **NO-GO**. Primary Recall@5 delta −0.1167 (paired CI below zero). Original saved-result audit PASS.
- **GRF-01:** Fixed graph bonus vs Hybrid RRF on 60 nonoverlapping, previously reserved DEV questions; original report SHA256 `f2167bc7220554b1864648c5c5de0b67544bfbdba585a4aeed8f466927fcb2b4`. Local full test suite and independent saved-result audit **PASS**. Recall@1 delta 0.0000; Recall@3 delta −0.0500 (CI [−0.1000, −0.0083]); Recall@5 delta −0.0083 (CI [−0.0250, 0]), **INCONCLUSIVE_NO_AUTOMATIC_PROMOTION**.
- **Default stays Hybrid RRF.** These cohorts have been scored and must not be used for tuning and fresh validation. The studies compare document recovery, not factual answer generation.
- **Explorer:** `apps/explorer` displays a curated source-backed graph plus GRF-00/01 retrieval statistics. It prefers local archived-report-verified data if available; otherwise it loads source-hashed, aggregate-only **public summaries reconstructed from operator audit logs**. It does not display original HotpotQA passages or invent missing measurements. The explorer is locally runnable; **public hosting has not been deployed**.

See [Graph-first report](benchmarks/GRF00_HOTPOTQA_DEV_60_NO_GO_20261104.md), [Graph-Hybrid audited report](benchmarks/GRF01_HOTPOTQA_DEV_FROZEN_20261104.md) and [the research release blueprint](docs/RELEASE_WOW_BLUEPRINT.md).

**Next release priorities:** close M2 semantic answer verification and abstention, benchmark the ten additional role-separated model candidates, harden/host the observatory, then cut the public v1.0 release.


## M2-LIVE-01 — Real local Qwen boundary smoke (prepared)

The next scientific-quality milestone begins with a **real-generator, fictional-source operational regression**, rather than repeating the exposed SciFact TEST question. Run `scripts/run-m2-live-controls-local.ps1` to first run the complete test suite and then exercise the existing V2 pipeline on four predefined conditions: sufficient evidence, irrelevant nonempty evidence, conflicting evidence and no evidence. It makes **three bounded real Qwen calls**, with a guaranteed generator skip in the no-context control.

This measures publication/citation syntax and safe empty-context behavior; it explicitly **does not** automatically score semantic truth or answer task correctness. All generated outputs stay local under gitignored `runs/m2-live/`. Newly added implementation/tests have **not yet been run on the operator's Windows environment**, and M2 remains open. [Design and limitations](docs/M2_LIVE_QWEN_CONTROLS.md).


## M2-LIVE-01 real Qwen outcome (2026-11-04)

The Windows full suite and bounded Qwen experiment both **PASS operationally**. Three real generated drafts were **all rejected by the citation syntax gate**, including one with sufficient source evidence; the empty-context control abstained with zero generator calls. The resolved model revision was unavailable. This is **not** a semantic accuracy or answer-quality measurement.

The new offline script (scripts/audit-m2-live-local.ps1) verifies the saved original source IDs, citation statistics and refusal statuses, and prints the exact raw rejected drafts without rerunning Qwen. This new code and tests still require Windows validation. See the M2 original case report under benchmarks/M2_LIVE_QWEN_BOUNDARY_20261104.md.

## M2-LIVE-02 — versioned, quarantined Qwen prompt experiment (prepared)

After inspecting all three original Qwen drafts, the actual failure is both absent inline citations **and** unsound answers on irrelevant/conflicting sources. M2-LIVE-02 uses the existing V2 pipeline and Qwen with a *new, fingerprinted prompt only*: one cited sentence, or exact INSUFFICIENT_EVIDENCE. It does not append citations to claims or promote cited text to factual truth. **All research outputs, even citation-accepted statements, are held for semantic review**. New synthetic regression tests and one local Windows driver are committed but not yet verified. Run scripts/run-m2-live-v2-local.ps1 after pull. Prior M2-LIVE-01 JSON is SHA checked and unchanged. See docs/M2_LIVE_02_VERSIONED_PROMPT.md.

## M2 parser V2 — opt-in citation syntax replay (prepared)

The verified M2-LIVE-02 output has a conventional citation *after* the period (`Fact. [S1]`) that the legacy V2 pipeline parser treats as an uncited sentence. The other two generated candidates still misuse irrelevant/conflicting evidence. A **strict, opt-in citation parser V2** and **model-free archived-output replay** have been implemented, with no change to the production/default pipeline or original experiment. Run `scripts/replay-m2-citations-local.ps1` after pulling to test and compare V1 versus V2 citation syntax on the saved three Qwen drafts, without running Qwen again. New tests require local verification. See [M2 syntax replay protocol](docs/M2_CITATIONS_V2_REPLAY.md). A citation syntax pass is NOT semantic entailment.

## M2 citation parser V2 replay verified; semantic review packets prepared

On Windows, the full pytest suite and offline replay PASS. The archived M2-LIVE-02 report SHA256 is `3c9fc0794ab2d2bd3ca10825585926083b0d40067c1696aa77fc90f230ea7816`; V1 citation syntax accepted **0** generated candidates and experimental V2 syntax accepted **1** (`Fact. [S1]`). The two remaining unsafe/non-compliant drafts stayed rejected. **Zero new Qwen calls and zero publication actions.** Source-grounded truth is still unassessed. The next optional, no-model step is `scripts/prepare-m2-live02-review-local.ps1`, which exports four **unlabelled** packets based on this immutable archived run for independent relevance/claim-support/abstention review; new tests are committed but local operator verification is pending. See [the reviewer handoff](docs/M2_REVIEW_02_HANDOFF.md).

## M2-REVIEW-02 PASS; frozen M2-SYNTH-01 source-control study staged (2026-11-04)

The maintainer's full Windows pytest suite and the **four unlabelled M2-REVIEW-02 packet export passed**, using original Qwen report SHA256 `3c9fc0794ab2d2bd3ca10825585926083b0d40067c1696aa77fc90f230ea7816`; original source/claim counts were 1/1, 1/1, 2/1 and 0/0. None has a verified semantic truth label, and no model or external publication was invoked.

For a low-cost *new* robustness measurement, `M2-SYNTH-01` predeclares **24 synthetic source-control cases** (six each answerable, irrelevant, contradictory and zero-context). Frozen cohort SHA256 `05e778d4b541d397c27a000d4042549d84b90d047a28f1bbf16b289bda6a3826`, original M2-LIVE-02 prompt SHA256 `2351f8f969281b7e92c9a827c8f3da79643d75a88c06f6c1c53faf68b25d3246`. The checkpointed runner makes up to 18 CPU Qwen calls and never changes production RAG or publishes an answer. It scores **exact abstention or literal+syntax control success only, NOT independent semantic faithfulness**. Unit tests for the core scoring protocol passed locally; the new full Windows test suite and real Qwen experiment **remain pending**. See [M2-SYNTH-01 protocol](docs/M2_SYNTH01_FROZEN_PROTOCOL.md).

## M2-SYNTH-01 first complete real-model result (2026-11-04)

The full Windows suite and 24-case synthetic control run **PASS operationally** at `c01f62c`. Qwen made 18 calls, with six automatic no-context skips. The strict frozen proxy succeeded **7/24**: answerable **1/6**, irrelevant **0/6**, contradictory **0/6**, empty-context **6/6**. **No model-generated exact abstentions** occurred in the 12 nonempty negative controls, and the old pipeline syntactically **accepted 3/12** of them although those cases called for abstention; zero answers were externally published. **NO-GO for automatic answer publication.** No general faithfulness/semantic accuracy score may be inferred. The original archive has not been uploaded; no row-level audit yet. An offline source-hashed audit has been added to inspect all 18 actual drafts without running Qwen. See [outcome and next command](benchmarks/M2_SYNTH01_QWEN_FROZEN_OUTCOME_20261104.md).

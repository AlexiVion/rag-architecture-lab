# Research roadmap

**Research status as of 2026-11-10.** This roadmap describes investigation phases rather than software-release targets. The authoritative current evidence index is [RESEARCH_STATUS.md](RESEARCH_STATUS.md). Earlier development cohorts are exposed and must not be reclassified as independent test data.

## Track A — retrieval and source provenance

| Study | Evidence | Current interpretation |
| --- | --- | --- |
| RET: sparse, dense, Hybrid RRF | [BEIR SciFact retrieval](../benchmarks/V1_1_RESULTS.md) | Matched query/corpus ranking diagnostic; hybrid chosen for evaluated setting |
| RET: cross-encoder reranking | [Reranking study](../benchmarks/V1_1_RESULTS.md) | Modest quality benefit with substantial CPU latency increase |
| GRF: graph-guided retrieval | [GRF-00](GRF_00_HOTPOTQA_STUDY.md), [GRF-01](GRF_01_EVALUATION_RUNNER.md) | Negative graph-first and inconclusive graph-hybrid results on distinct public DEV cohorts; no general graph superiority claim |

## Track B — evidence-grounded QA and small CPU models

| Stage | Question and method | Current state |
| --- | --- | --- |
| B0: integrity | Test retrieval, original source IDs, exact quotes/offsets and refusal on malformed evidence | Completed for a restricted structured-source contract; [MICRO-RAG v0.2](MICRO_RAG_V02_SPEC.md) |
| B1: model diagnostics | Measure compact extractive QA, causal generation, NLI and ONNX inference in CPU-only studies | Public DEV experiments completed, with limitations in their respective reports |
| B2: realistic evidence | Evaluate actual reader-extracted claims over real natural-language web passages, not author-provided answer oracles | **Pending** |
| B3: selective response | Compare supported-answer coverage, incorrect accepted responses and abstention under a total <=135M active neural-parameter budget | **Pending** |
| B4: independent evaluation | Two-domain original questions, adjudicated human labels, sealed source-grouped holdout and matched CPU/RSS assessment | **Pending** |
| B5: scientific reporting | Final uncertainty, error taxonomy, ablations, replication package and working manuscript | **In progress; not submitted** |

## Experimental controls

- Fix source document splits, dataset licenses and SHA256, model revisions and decoding before any confirmatory evaluation.
- Report all parameter-bearing components, including retrievers and verifiers, when stating a combined neural model budget.
- Preserve the distinction between retrieval rank relevance, verbatim citation validity, logical contradiction, semantic evidence support and factual QA correctness.
- Score uncertainty by original question/source group where multiple derived observations are correlated.
- Include lexical, extractive, uncalibrated NLI, generator-only, matched RAG and refuse-all controls as appropriate; do not attribute gains to a larger checkpoint or privileged oracle.
- Record time, memory and cold-start costs under stated hardware constraints. Avoid general hardware-independent efficiency conclusions from single shared-runner timings.
- Report negative and inconclusive observations without filtering failed cases.

## Primary documents

[Experiment protocol](EXPERIMENT_PROTOCOL.md) · [PAPER-01 preregistered study](PAPER_01_MICRO_CPU_FRONTIER_PROTOCOL.md) · [ConfRAG results](PAPER_01_CONFRAG_DEV_RESULTS.md) · [Working manuscript](../papers/micro-cpu-frontier/WORKING_MANUSCRIPT.md) · [Outstanding scientific issue #39](https://github.com/AlexiVion/rag-architecture-lab/issues/39).

The proposed future physical-AI/world-model topic is a **separate theoretical research program**, not a validated capability of this repository; see [ADR-0006](adr/0006-tiny-world-models-physical-ai-future-track.md).

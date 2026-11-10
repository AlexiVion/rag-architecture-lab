# Research status and experimental evidence

**Last updated: 2026-11-10.** This document separates tested software behavior, exploratory empirical findings and unverified hypotheses. The repository is a research implementation, not a claim of scientific validation.

## Research program

| Area | Current evidence | Scientific status |
| --- | --- | --- |
| Sparse/dense/hybrid retrieval | BEIR SciFact study: 5,183 documents, 300 queries, MRR@10 comparison | Completed benchmark under documented conditions |
| Cross-encoder reranking | Quality-versus-local-CPU latency ablation with candidate-depth controls | Completed diagnostic; performance depends on hardware and corpus |
| Graph-guided retrieval | HotpotQA DEV graph-first and hybrid comparisons; negative/inconclusive results | Exploratory, no general GraphRAG superiority claim |
| Structured evidence verification | Four-state decision pipeline (ANSWER, CONFLICT, INSUFFICIENT, REVIEW); paired perturbation tests on fictional fixtures | Engineering verification only; structured literal inputs |
| Small CPU models | Public SQuAD2, Ragability and ConfRAG experiments; NLI, extractive QA and generator checkpoints | Task-specific exploratory studies, not fair intrinsic model-capability ranking |
| Selective end-to-end natural-language QA | Proposed 33M reader + small verifier + <=135M matched reference baselines | **Not yet independently validated** |
| Human-reviewed evidence support and abstention | Separate independent held-out evaluation protocol | **Not completed** |
| Scientific manuscript | Working draft with experimental methods and exploratory findings | **Not submitted or peer reviewed** |

## Selected primary study records

- [Experiment design, fairness and reporting](EXPERIMENT_PROTOCOL.md)
- [BEIR SciFact and reranking experimental report](../benchmarks/V1_1_RESULTS.md)
- [Micro-RAG v0.2 software contract](MICRO_RAG_V02_SPEC.md)
- [CPU NLI model comparisons on Ragability](MICRO_RAGABILITY_NLI_RESULTS.md)
- [Quantization study](MICRO_V02_ONNX_RESULTS.md)
- [ConfRAG author-viewpoint diagnostic](PAPER_01_CONFRAG_DEV_RESULTS.md)
- [Frozen 135M CPU-frontier research protocol](PAPER_01_MICRO_CPU_FRONTIER_PROTOCOL.md)
- [Working paper](../papers/micro-cpu-frontier/WORKING_MANUSCRIPT.md)

## Unresolved validation requirements

1. Real-document end-to-end retrieval and **automatic** answer extraction, without author-supplied oracle answers.
2. Explicit source-support and logical-contradiction labels; annotated viewpoint disagreement is **not** equivalent to contradiction.
3. Reproducible, task-matched baselines and true combined neural-parameter budget accounting, with measured CPU time and peak memory.
4. Previously specified independent multi-domain human-reviewed evaluation, including a sealed holdout and adjudication.
5. Reporting of correct-answer coverage, selective error risk, abstention, evidence-intervention consistency and uncertainty at the **source-question group** level.

The [PAPER-01 tracker](https://github.com/AlexiVion/rag-architecture-lab/issues/39) is open. Passing unit tests or on-source dataset development evaluations does not satisfy these scientific gates. Earlier development experiments remain available in the versioned reports, with their original limitations.

## Research software

The Python package, local runners and static observatory are public and reproducible as software. See [REPRODUCIBILITY.md](REPRODUCIBILITY.md) for a fresh environment, experimental input controls and independent checks. A formal, tagged research-software release and a publicly verified hosted observatory have not been established.

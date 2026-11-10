# RAG Architecture Lab

**An open-source research repository for retrieval-augmented generation, evidence verification, and computationally constrained language models.**

RAG Architecture Lab investigates the relationship between retrieval quality, evidence-grounded question answering, reliability, and computational cost. The project implements retrieval and verification components directly, compares them under documented experimental protocols, and reports positive, negative, and inconclusive results. Experiments prioritize reproducibility and execution on commodity CPUs.

> **Research status (November 2026):** Retrieval benchmarks, CPU model pilots, structured evidence controls, and exploratory external-data studies have been completed. **Reliable end-to-end natural-language question answering has not been independently validated.** The working manuscript is not submitted or peer reviewed.

## Research questions

1. How do sparse, dense, hybrid, graph-guided, and cross-encoder retrieval methods trade ranking quality against latency?
2. What kinds of evidence conflicts, missing support, and abstention failures can be detected under constrained model budgets?
3. What level of answer correctness and correct-answer coverage is achievable when the **total active neural parameter count** is at most 135 million and inference runs on CPU?
4. When is a non-neural procedure preferable to a neural verifier, and how do task mismatch and source provenance affect the result?

## Repository organization

| Directory | Contents |
| --- | --- |
| `src/raglab/` | Retrieval, ranking, graph-provenance, evaluation, evidence and experimental pipelines |
| `experiments/` | Experiment specifications, candidate registries and controlled configurations |
| `benchmarks/` | Versioned retrieval studies, aggregated metrics and protocol-bound results |
| `scripts/` | Local study runners, analysis and reproducibility checks |
| `tests/` | Unit, adversarial, data-integrity and evaluation regression tests |
| `apps/observatory/` | Read-only React/TypeScript visualizations of documented studies and source provenance |
| `docs/` | Research protocols, experimental reports, architecture notes and limitations |
| `papers/micro-cpu-frontier/` | Working scientific manuscript; not a completed or accepted paper |

## Selected findings

All numbers below are **task-specific** and should not be interpreted as end-to-end factual answer accuracy.

| Study | Experimental outcome | Scope |
| --- | --- | --- |
| BEIR SciFact retrieval | Hybrid RRF **MRR@10 0.6484**, BM25 **0.6328**, dense **0.6047** | 5,183 documents; 300 queries; ranking relevance only |
| Cross-encoder reranking | Hybrid MRR@10 **0.6484 → 0.6615**; observed mean retrieval latency **34.53 → 3706.43 ms** with 50 candidates | Recorded local CPU configuration; quality/latency trade-off |
| Graph-assisted HotpotQA retrieval | Source-guided graph + BM25 Recall@5 **0.7083** versus BM25 **0.8250** | 60 DEV bridge questions; negative for the tested policy |
| ConfRAG author-viewpoint study | Fixed lexical control **164/240** correct; DeBERTa 70.8M **124/240**; MiniLM2 82.1M **120/240** | **16** source-question groups, 240 correlated pairs. Detects *annotated viewpoint differences*, **not** independently verified logical contradiction |
| CPU NLI quantization pilot | INT8 **269/318** versus FP32 **261/318** pair predictions, batch wall time **15.08s** vs **24.37s** | Public Ragability pairwise diagnostic only, not complete RAG |

The ConfRAG results are specifically a **task-transfer diagnostic**: the two NLI models were trained for logical inference, not answer-viewpoint clustering; the benchmark authors provided the answer extracts. A higher accuracy for the lexical baseline in this setting **does not establish** that lexical methods are better contradiction detectors. The 240 pairs are correlated within 16 questions, so they cannot be treated as 240 independent observations.

**Reports and primary methods:** [Retrieval and reranking](benchmarks/V1_1_RESULTS.md) · [ConfRAG data/model provenance and limitations](docs/PAPER_01_CONFRAG_DEV_RESULTS.md) · [NLI quantization](docs/MICRO_V02_ONNX_RESULTS.md) · [Experiment protocols](docs/EXPERIMENT_PROTOCOL.md) · [Current research status](docs/RESEARCH_STATUS.md).

## Methods and reproducibility

Experiments specify the evaluated task, source dataset and split, model checkpoints and licenses, baselines, inference configurations, and limitations. Public evaluation datasets are **development diagnostics unless explicitly labeled as independent holdouts**. Dataset-derived pairs are grouped by original question or source to avoid treating correlated examples as independent samples.

For a clean Python 3.11+ software check:

```bash
git clone https://github.com/AlexiVion/rag-architecture-lab.git
cd rag-architecture-lab
python -m venv .venv
# Activate .venv for your shell
python -m pip install -e ".[dev]"
python -m pytest -q
python -m raglab.release_readiness
```

This checks source and fixture integrity; it does **not** certify factual QA reliability. Optional real-model experiments have separate scripts and may download model weights and public datasets. See [reproducibility instructions](docs/REPRODUCIBILITY.md).

The read-only research observatory can be built locally with Node.js 22:

```bash
cd apps/observatory
npm install
npm run check
npm run build
npm run dev
```

The observatory presents saved results and illustrative, explicitly fictional graph fixtures. **It does not run a public model inference service**, and a publicly hosted instance is not asserted here.

## Ongoing study

[Research status and experimental registry](docs/RESEARCH_STATUS.md) · [CPU RAG evaluation protocol](docs/PAPER_01_MICRO_CPU_FRONTIER_PROTOCOL.md) · [Working manuscript](papers/micro-cpu-frontier/WORKING_MANUSCRIPT.md) · [Tracked evaluation requirements](https://github.com/AlexiVion/rag-architecture-lab/issues/39).

The next confirmatory stage requires automatic extraction from real natural-language documents, matched end-to-end baselines, source-level support assessment, and an independent multi-domain human-annotated holdout. Until these conditions are met, **no claim of validated general factual reliability, superiority or novel scientific discovery is made**.

## Citation, contribution and license

Use [`CITATION.cff`](CITATION.cff) for repository citation information, [`CONTRIBUTING.md`](CONTRIBUTING.md) for contributions, and [`LICENSE`](LICENSE) for source-code licensing. External datasets and model checkpoints retain their respective licenses and attribution requirements.

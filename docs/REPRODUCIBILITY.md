# Reproducing the research software

## Environment

- Python 3.11 or newer and a local virtual environment.
- Optional: Node.js 22 for the read-only React/TypeScript observatory.
- CPU for default installation and deterministic checks. Optional real-model scripts can download open model weights and public datasets.
- No paid inference keys are needed for software integrity checks.

```bash
git clone https://github.com/AlexiVion/rag-architecture-lab.git
cd rag-architecture-lab
python -m venv .venv
# Activate the virtual environment using your shell
python -m pip install -e ".[dev]"
python -m pytest -q
python -m raglab.release_readiness
raglab --help
```

On Windows PowerShell, activate `.venv\Scripts\Activate.ps1` after creating the environment. Check the exact interpreter version, OS and active virtual environment before reproducing CPU-time figures.

## Local research observatory

```bash
cd apps/observatory
npm install
npm run check
npm run build
npm run dev
```

This renders verified static research artifacts. The graph demonstration includes **fictional source documents** and should not be mistaken for real automated knowledge-graph extraction. A live public hosting URL is not asserted.

## Reproducing published experiments

- For retrieval benchmarks and source data, follow [the experiment protocol](EXPERIMENT_PROTOCOL.md) and [archived study reports](../benchmarks/).
- For small extractive QA: `scripts/micro/minilm_extractive_cpu_pilot.py` and the SQuAD2 method documents.
- For NLI: `scripts/micro/ragability_nli_cpu.py` and [its report](MICRO_RAGABILITY_NLI_RESULTS.md).
- For published ConfRAG viewpoints: `scripts/micro/confrag_viewpoint_nli_cpu.py`, [data protocol](PAPER_01_CONFRAG_DEV_PROTOCOL.md), [results](PAPER_01_CONFRAG_DEV_RESULTS.md) and a local model/dataset download.
- To compare already archived NLI predictions without model downloads, use the module `raglab.evaluation.confrag_comparison` with the two exact saved JSON artifacts.

Archive the source commit, data revision and hash, model revision and weights, original question-group IDs, execution environment, output artifact and any manual decisions. Do not treat successful installation or synthetic-case tests as independent experimental validation.

## Source-bound real retrieval replay

The observatory includes an **actual** offline execution of two existing Python retrievers (full-document BM25 and passage-based Parent–Child BM25) on eight fixed repository research documents. The source documents have original SHA256s and the stored ranks are rechecked by running the same code. The three question texts are authored, however, and there are no human relevance labels: this is a software replay, **not** an evaluated retrieval benchmark.

From the repository root, with the development package installed:

```bash
python scripts/observatory/export_repo_retrieval_replay.py --check
python -m pytest -q tests/test_repo_retrieval_replay.py
```

The stored artifact is `experiments/repo_retrieval_replay.json`. The reference procedure and limitations are in [REPOSITORY_RETRIEVAL_REPLAY.md](REPOSITORY_RETRIEVAL_REPLAY.md).

Original **per-query** SciFact rankings are not versioned in this repository's aggregate V0/V1 reports. If an authentic previous `raglab benchmark` JSON file exists on the local research workstation, inspect its actual queries offline:

```bash
python scripts/observatory/export_saved_benchmark_replay.py --input benchmarks/results/ORIGINAL_RUN.json --output benchmarks/results/local-query-replay.json --take 3
```

Then open the read-only observatory's *Experiments → Inspect your own saved benchmark trace* panel and choose the exported file. No model call or server upload occurs. This importer preserves the original archive's SHA256 but does not independently verify the external dataset or checkpoint revisions. Do not infer per-query ranks from aggregated metrics.

## Verification boundaries

`raglab.release_readiness` verifies repository artifacts, expected software structure, illustrative graph fixtures and candidate-model registration. It does **not** demonstrate answer faithfulness, semantic entailment, statistical generalization, or a completed scientific study. CPU times from different hardware or concurrent shared-host runners must not be ranked as if controlled hardware experiments.

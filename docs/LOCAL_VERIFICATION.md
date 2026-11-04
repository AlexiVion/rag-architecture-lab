# Local verification before merging Research Lab v1

This repository preserves its local-only model benchmarking policy. There is no hosted runner to certify model quality.

## One command on Windows

From the project root:

```powershell
.\scripts\verify-research-lab-local.ps1
```

This prepares the environment if absent, runs deterministic pytest tests, and executes the BM25-only parent-child exploratory comparison. It fails on a nonzero exit code. The smoke compares two retrievers on the same dataset; it is **not** a scientific recommendation until error analysis and matching environments are reviewed.

To also run local Qwen generation:

```powershell
.\scripts\verify-research-lab-local.ps1 -WithGeneration
```

The generation option may download models locally on first use, never consumes paid API credits, and does not imply the generated answers are factually supported.

## Record the result

Before promoting PR #2 from draft or merging, record:
- git SHA, Python version, CPU, memory and OS;
- pytest summary;
- exploratory benchmark file path and quality/latency numbers;
- V2 output path and citation/abstention findings, if executed;
- known regressions and whether the artifacts are exploratory or canonical.

Generated output is intentionally untracked. Summaries should be added only after inspection, not invented in the README.

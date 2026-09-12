# Local Benchmark Execution

All computation for this project is intended to run on the local Windows machine/server, not on GitHub-hosted Actions runners.

GitHub is used for source control and publishing code/results. Tests and benchmark execution stay local so experiments use the same machine and latency measurements remain comparable.

## 1. Clone or update the repository

```powershell
git clone https://github.com/AlexiVion/rag-architecture-lab.git
cd rag-architecture-lab
```

If the repository already exists locally:

```powershell
git pull
```

## 2. Prepare the local environment

From PowerShell in the repository root:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup-local.ps1
```

The setup script creates `.venv`, installs benchmark and development dependencies, and runs the unit tests locally.

## 3. Run V1 locally

```powershell
.\scripts\run-v1-local.ps1
```

This compares:

- Hybrid RRF
- Hybrid RRF + cross-encoder reranking with 50 candidates

The benchmark writes timestamped JSON files to:

```text
benchmarks/results/
```

## 4. Run V1.1 locally

```powershell
.\scripts\run-v1-1-local.ps1
```

This runs one Hybrid baseline and then reranking experiments with candidate depths 10 and 20. The previously defined 50-candidate configuration remains the V1 reference point.

## 5. Preserve reproducibility

Before treating a result as canonical, record:

- machine used
- CPU
- RAM
- operating system
- Python version
- benchmark command
- model names
- candidate depth
- Git commit SHA

The JSON benchmark output already records the software/runtime configuration. Hardware metadata should be added to the written experiment summary when the run is promoted to a canonical result.

## 6. Publish results only after local validation

After a benchmark finishes locally:

1. inspect the generated JSON;
2. compare the metrics and latency;
3. write/update the corresponding `benchmarks/*_RESULTS.md` document;
4. commit the result summary to GitHub.

Do not use GitHub-hosted runs as the canonical source for tests, benchmarks, or latency measurements.

## GitHub Actions policy

The repository intentionally contains no GitHub Actions workflows for execution. GitHub is the source-control and publication layer; computation happens on the local machine/server.

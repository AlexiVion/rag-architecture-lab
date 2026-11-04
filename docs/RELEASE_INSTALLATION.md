# Release installation and verification (R0)

**Status:** installation and CI contract prepared. A clean external-clone installation must be observed before R0 is marked complete.

## Python 3.11+, CPU-only

```bash
git clone https://github.com/AlexiVion/rag-architecture-lab.git
cd rag-architecture-lab
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest -q
python -m raglab.release_readiness
raglab --help
python -m raglab.observatory.fixture --output /tmp/raglab-demo.json
```

The clone above uses the **default main branch**. Until PR #2 is merged, use `git switch feat/research-lab-architecture-catalog-20261104` after cloning to access the latest research and offline viewer.

Windows PowerShell (after creating a Python 3.11 virtual environment):

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m raglab.release_readiness
.\.venv\Scripts\raglab.exe --help
```

Package wheel builds use pip build isolation and may fetch small packaging tools, but not model weights or benchmark corpora.

The offline validator checks the curated graph fixture against its deterministic source, public aggregate summaries and MOD-10 registry structure. It **does not** certify scientific answer correctness, safety or the completion of WOW v1.0.

For a local browser demo:

```bash
python -m http.server 4874 --bind 127.0.0.1 --directory apps/explorer
```

Open http://127.0.0.1:4874/. The visual fixture contains no model-generated answer and uses fictional documents with exact source quotes. A real model run requires the optional `.[generation]` dependencies and weights, which can consume significant CPU and RAM.

## CI policy

The `offline-tests` workflow is **one lightweight job** for dependencies, pytest, offline fixture/registry integrity and wheel/sdist packaging. It intentionally forbids model/dataset downloads. Quantitative CPU benchmarks and model research are canonical **only when executed on the documented local Windows machine**, not in GitHub Actions.

The `pages` workflow deploys only curated static files from `apps/explorer` after merge to `main` and enabling GitHub Pages with source **GitHub Actions**. Hosting the viewer does not host Qwen inference. A deploy workflow configuration is not evidence that the public URL is already live.

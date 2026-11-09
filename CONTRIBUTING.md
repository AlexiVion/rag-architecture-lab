# Contributing

This is a research-oriented open-source RAG laboratory, not a hosted app.

## Local development

Requires Python 3.11+. See `docs/LOCAL_EXECUTION.md` for the canonical Windows machine setup. Install `pip install -e ".[dev]"` for fast deterministic tests; run `python -m pytest` before proposing changes. Model-backed benchmarks require `.[benchmark,generation,dev]` and are deliberately local.

## Proposing an architecture

1. Open a focused issue or PR identifying the catalog experiment ID, hypothesis and matched baseline.
2. Implement a composable adapter; do not fork or duplicate the BM25/dense/RRF engine.
3. Include deterministic tests for ID mapping, empty inputs, duplicates, bounds, ties and repeated indexing where applicable.
4. Clearly label mocked/unit-only results; never claim that an adapter is benchmarked based on tests alone.
5. Report latency and quality under controlled circumstances; keep datasets and model revisions explicit.
6. Document at least one negative example and the decision to adopt, reject or defer.

See `docs/LAB_ARCHITECTURE.md`, `docs/ARCHITECTURE_CATALOG.md`, `docs/EXPERIMENT_PROTOCOL.md` and `docs/ROADMAP.md`.

## Pull requests

Prefer small changes with tests and no paid credentials. Do not commit model caches, personally identifiable data, benchmark datasets with restricted licenses, or large JSON result dumps. Use descriptive commit messages and explain changes to existing experiment contracts.

# GRF-00 — Provenance graph prototype and offline observatory

**Status:** deterministic, source-grounded prototype. This is not a claim that the full GraphRAG architecture or a multi-hop quality benchmark is complete.

## What works

- \`EvidenceGraphRetriever\` implements an actual two-hop traversal of entity relationships; it is not a diagram-only graph.
- Every relation is attached to an **exact quote** in an original document. Graph indexing fails closed for unknown documents/entities, ambiguous aliases, duplicate edges and quotes not present in the document.
- Ranked graph evidence returns **original document IDs** and exposes the path's entity IDs, relation IDs and source-document IDs; a local BM25 fallback is used when needed.
- Repeated \`index()\` calls replace graph-derived state and reindex the underlying retriever.
- \`raglab.observatory.fixture\` exports a versioned public artifact containing three curated, fictional scientific-instrument/rover-related passages and three selectable demonstration questions.
- \`apps/explorer\` is a read-only web prototype for visualizing graph nodes, selected paths and exact source quotes. It never generates an answer or claims numeric benchmark accuracy.
- No external model, credential, GPU or paid API is required for the fixture.

## One command (Windows)

From the root of a working local clone with its existing Python environment:

\`\`\`powershell
.\scripts\run-observatory-local.ps1
\`\`\`

This runs the graph regression tests, regenerates and verifies \`apps/explorer/data/demo.json\`, opens \`http://127.0.0.1:4874\` and serves the static viewer from localhost. Stop the server with Ctrl+C.

For noninteractive headless test/fixture export only:

\`\`\`powershell
.\scripts\run-observatory-local.ps1 -NoServe
\`\`\`

Cross-platform equivalent:

\`\`\`bash
python -m pytest -q tests/test_graph_evidence.py
python -m raglab.observatory.fixture --output apps/explorer/data/demo.json
python -m http.server 4874 --bind 127.0.0.1 --directory apps/explorer
\`\`\`

The prebuilt public demo file is an **illustrative fixture**, never a performance/quality benchmark. Its numerical graph counts count curated nodes and paths, not evidence accuracy. Real benchmarks still need true multi-hop QA labels, controls, paired retrieval evaluation and measurement of index and query costs.

## Remaining GRF-00 acceptance gates

- Dataset-independent extraction adapter (normalized entities and schema-constrained relationships).
- Stable indexing updates, alias resolution beyond exact matches and graph provenance across real corpora.
- Real multi-hop benchmark (e.g. publicly licensed HotpotQA/MuSiQue subset) with an identical text-only control.
- Indexing/traversal cost, memory, latency, provenance path coverage, failure analysis and objective GO/NO-GO.
- Browser accessibility and mobile review against a real browser; static code/asset checks alone are not such a review.

**Scope boundary:** this is a graph-first retrieval baseline with curated evidence and BM25 fallback. It does **not** implement Microsoft GraphRAG community reports, global queries, LLM extraction or a semantic faithfulness judge.

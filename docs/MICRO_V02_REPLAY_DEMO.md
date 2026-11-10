# MICRO-RAG v0.2 — Four-state observatory replay

This feature replays four **actually executed** MicroRAG Python pipeline decisions on invented station documents. It is a software-evidence exhibit, NOT live hosted neural inference and NOT proof that semantic RAG is reliable.

- Source engine: `src/raglab/micro_v02/`, strict evidence contracts, original offsets and SHA256, BM25 + bounded entity scan.
- Exporter: `scripts/micro/export_micro_v02_observatory.py`.
- Canonical generated artifact: `experiments/micro_v02_observatory_replay.json`.
- Generated and verified in [GitHub Actions #42836127581](https://github.com/AlexiVion/rag-architecture-lab/actions/runs/42836127581) on exporter commit `ddd5be1839c9183fb0ace85f1a30bbde1fa67427`. Artifact preserved in the workflow, actual JSON captured from the engine's stdout without hand-authoring states or quotes.
- Static UI: Observatory `MICRO-RAG v0.2` tab. Build process copies the canonical JSON into public assets. The browser checks schema, four decisions, original quote offsets and SHA256 of every original source before rendering. If any validation fails, outputs are hidden.

## What the four cases mean

| Case | Input | Outcome |
| --- | --- | --- |
| Conflict | Aurora year, two inconsistent structured records | CONFLICT (no published year, two source citations) |
| Answer | Boreal year, two consistent records | ANSWER 2019, exactly sourced |
| Insufficient | Cosmos year, not present in its record | INSUFFICIENT (no answer) |
| Review | Aurora year, artificially limited scan budget 1 | REVIEW, evidence scan incomplete, no answer |

This only demonstrates correct decisions for a **narrow structured key:value reader**. Natural-language claim extraction, semantic NLI validity, source authority and temporal precedence, calibrated abstention on independent human-reviewed data, and full-stack CPU efficiency remain OPEN in [issue #28](https://github.com/AlexiVion/rag-architecture-lab/issues/28).

## How to reproduce

```sh
python -m pip install -e '.[dev]'
python -m pytest -q tests/test_micro_v02_replay.py
python scripts/micro/export_micro_v02_observatory.py --output /tmp/micro-replay.json
python -m json.tool /tmp/micro-replay.json
cd apps/observatory
npm ci
npm run build
npm run e2e
```

Compare the generated replay JSON with the canonical version after formatting. Browser screenshot QA should visibly separate positive answers from refusals.

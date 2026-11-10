# MICRO-RAG v0.2 — audited structured-source software validation

**Date:** 2026-11-10. **Scope:** public, CPU-first experimental RAG software, not independently validated semantic factual QA. **Engineering verdict:** source-integrity and synthetic four-state pipeline PASS. **Scientific verdict:** reliable free-text RAG NOT ESTABLISHED. **Reproducibility:** repository and exact-head CI records are public; independent natural-language reliability remains unverified.

## What demonstrably works

- A runnable Python `MicroRAG` CLI retrieves local documents using BM25, reads bounded structured `entity: ...` / `field: value` records, checks matching source entities, validates exact source offsets and document SHA256, and returns one of **ANSWER / CONFLICT / INSUFFICIENT / REVIEW**.
- Only a strict structured-literal answer may reach `ANSWER`. Two distinct source values become `CONFLICT` without a published answer. Explicitly missing values on a recognized query and sufficiently attributed structured corpus may return `INSUFFICIENT`.
- Ambiguous entity declarations, malformed/unattributed records, incomplete source sweep, unsupported questions, and any unverified neural free-text extraction must remain `REVIEW`. A top-k model that finds no answer is **not** entitled to claim corpus-wide absence.
- An interactive, eight-section React/TypeScript observatory includes a **static replay** of four actual Python decisions on invented station records. The replay verifies exact original quotes, positions and hashes; it is **not live inference**.
- Six regression tests introduced with [PR #36](https://github.com/AlexiVion/rag-architecture-lab/pull/36) cover previously missed malformed-source and incomplete-retrieval refusal cases. The original nine-case fictional development evaluation still passes; it is **not** an independent accuracy figure.

## Evidence trace

| Gate | Evidence | Result and boundary |
| --- | --- | --- |
| P1 repair | [PR #36](https://github.com/AlexiVion/rag-architecture-lab/pull/36), merged `3c3b8a261e1dfa196c22a34a6373b53ada7b5338` | Fail-closed behavior and regression tests integrated |
| Structured end-to-end tests | [GitHub Actions #42838904398](https://github.com/AlexiVion/rag-architecture-lab/actions/runs/42838904398) | SUCCESS; visible fictional cases, not real-world model reliability |
| Full software integrity | [GitHub Actions #42838904462](https://github.com/AlexiVion/rag-architecture-lab/actions/runs/42838904462) | SUCCESS; Python/TypeScript/browser and source checks at PR head |
| Existing replay | [PR #35](https://github.com/AlexiVion/rag-architecture-lab/pull/35), [replay guide](MICRO_V02_REPLAY_DEMO.md) | Four real engine states displayed from public fictional inputs |
| Tiny generative diagnosis | [Oracle/extractive report](MICRO_ORACLE_VS_EXTRACTIVE_RESULTS.md) | Pythia-14M / SmolLM2-135M generated 0/16 exact answers to positive public DEV questions; task-trained extractive MiniLM-33M BM25 top-1 24/32 global reference EM; **not a matched-training comparison** |
| External conflict pairwise NLI | [Ragability study](MICRO_RAGABILITY_NLI_RESULTS.md) | DeBERTa-v3-xsmall and MiniLM2 each 261/318 pair classifications; 43 underlying source groups; neither a source arbiter |
| Quantized NLI CPU | [ONNX report](MICRO_V02_ONNX_RESULTS.md) | FP32 261/318 vs published AVX2 INT8 269/318; single sequential CPU batch study; **not complete RAG speed/RAM proof** |

## Reproduce the engineering demonstration

From a fresh Python 3.11+ checkout of this repository:

```sh
python -m pip install -e ".[dev]"
python -m pytest -q tests/test_micro_v02.py tests/test_micro_v02_nli.py tests/test_micro_v02_replay.py
python -m raglab.micro_v02 evaluate --documents examples/micro-v02/documents.json --cases examples/micro-v02/cases.json --output runs/micro-v02/evaluation.json
python scripts/micro/export_micro_v02_observatory.py --output runs/micro-v02/replay.json
```

The first-run demo requires no API key or paid service. A full browser build needs the separate Node/Chromium setup in [the replay guide](MICRO_V02_REPLAY_DEMO.md). Some optional CPU experiments download licensed public checkpoints.

## Explicit unfinished research

**Do not call this a reliable general-purpose RAG or a completed scientific result.** The project has no independently authenticated, untouched, multi-domain human-reviewed evaluation for the complete natural-language pipeline; free-text extraction lacks calibrated semantic support and source-authority/time resolution. The [scientific acceptance gates](MICRO_RAG_V02_SPEC.md) require at least 300 human-labeled evaluation questions over two or more domains, adjudication, risk/coverage confidence bounds, conflict detection, and full-stack CPU p95/RSS testing. [Issue #28](https://github.com/AlexiVion/rag-architecture-lab/issues/28) therefore **stays OPEN**.

## Reporting status

The completed software and pilot studies provide an auditable engineering baseline. The natural-language source-support research and independent evaluation remain open. Reproduction should use the cited experiment IDs, model revisions and original data manifests; successful structured tests must not be interpreted as general factual reliability.

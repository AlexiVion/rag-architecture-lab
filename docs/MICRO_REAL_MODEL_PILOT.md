# MICRO-LIVE-00 — First real open-weight tiny-model CPU pilot (diagnostic)

**Date:** 2026-11-09. **Result:** `ENGINEERING_PASS / SCIENTIFIC_QUALITY_UNVERIFIED`.

**Verified source:** [GitHub Actions #42656944850](https://github.com/AlexiVion/rag-architecture-lab/actions/runs/42656944850) **SUCCESS**, on PR [#16](https://github.com/AlexiVion/rag-architecture-lab/pull/16) source `0ae0e36982d96672a995554002138dcb9c77de8c`; integrated into `main` as `6083e061751817d699492e289e9b0c135ebfacd0`.

**Artifact:** `micro-real-14m-and-135m-diagnostic`, ID `13691264798`. It contains *only* source/test manifests, one synthetic test question and unverified generated drafts (no model weights). The supporting offline research integrity CI on the same branch was [#42656944886](https://github.com/AlexiVion/rag-architecture-lab/actions/runs/42656944886), **SUCCESS**.

## Exactly what happened

Public checkpoints were resolved to immutable Hugging Face commits, **safetensors** and tokenizer/config assets were downloaded explicitly, and real generation was executed on a GitHub-hosted **CPU-only Ubuntu runner**, without proprietary API calls.

| Checkpoint | Official source | Exact resolved revision | safetensors bytes | Weight SHA256 |
| --- | --- | --- | ---: | --- |
| Pythia-14M (base causal LM, NOT instruction tuned) | [EleutherAI/pythia-14m](https://huggingface.co/EleutherAI/pythia-14m) | `cf967c0a9a04383db6f7b1108d86b2962634b4ac` | 28,143,920 | `116a02532db461f91386a5b20f942ff2c8d4de7341e21b55caafc3d7b25f49a1` |
| SmolLM2-135M-Instruct | [HuggingFaceTB/SmolLM2-135M-Instruct](https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct) | `12fd25f77366fa6b3b4b768ec3050bf629380bac` | 269,060,552 | `5af571cbf074e6d21a03528d2330792e532ca608f24ac70a143f6b369968ab8c` |

Both model cards expose `apache-2.0` license metadata; this pilot neither redistributed model weights nor independently audited training-data rights. **A checkpoint size in bytes is not total runtime memory consumption.**

The test case was deliberately trivial and artificial: **"Which planet is fourth from the Sun?"**. Its data file is `micro-smoke-fixture-v1`, with output test file SHA256 `3bb2fcf70be16e3f7f28683f3491943c308e54c71a8af59b8dcdfc5cab4d6264`. Each model ran **three configurations** on the same question: (1) no retrieval, (2) naive top-ranked source prefixes and (3) query-aware exact-source span selection. All output lengths were bounded to **16 new tokens**.

This is a **code-to-real-weights integration smoke**, not a benchmark: 1 question × 2 differently trained models × 3 conditions, **no double-blind labels, no independent holdout, no paired confidence intervals**.

## Observed qualitative outputs (not scores)

- **Pythia-14M:** no-RAG generation repeated phrases about "evidence"; the two RAG contexts produced incomplete citation/document-ID patterns rather than a coherent factual answer. The base model was not trained as an instruction-following assistant.
- **SmolLM2-135M:** the two retrieved-context modes quoted an actual relevant source sentence about Mars, but did not produce a complete, independently validated answer. The no-RAG control echoed the question/prompt.
- **No quality winner is established.** These observations apply only to the one artificial question, decoding settings and exact pinned checkpoints. Citation-like text is not evidence of semantic faithfulness.

### Source and result integrity

| Model | Generated per-case file SHA256 | Mode | Context tokens (checkpoint tokenizer, excluding full chat template) |
| --- | --- | --- | ---: |
| Pythia-14M | `914cb08984204f4b9e35885ab9a1b123e2f40681e334b8509de24c49e5a3c1bd` | none / naive / spans | 0 / 96 / 56 |
| SmolLM2-135M | `aaaf84fe8de3f56f4d53342811d3d9c1c0fd27b7809472bfea3bec63e1498b67` | none / naive / spans | 0 / 96 / 56 |

The budget counts model-tokenized **evidence context**, not the full prompt, system instructions or special tokens. A complete context-length/cost study must count the rendered final chat template.

### Latency limitation

The pilot trace records measured wall times, but **the first generation was not warmed up**, so its several-second cold-start time **cannot be compared** to later warm-mode results as evidence of a RAG efficiency gain. Timings also use a GitHub Linux runner, not the canonical AMD Ryzen Windows test machine. They are for instrumentation debugging only, **not** CPU p95, energy or performance findings.

## Reproduction / audit

- Official source code: [scripts/micro/hf_cpu_smoke.py](../scripts/micro/hf_cpu_smoke.py)
- Workflow: [.github/workflows/micro-cpu-pilot.yml](../.github/workflows/micro-cpu-pilot.yml)
- Offline controls: [micro smoke fixture](../experiments/micro_smoke_fixture.json), [MICRO implementation protocol](MICRO_RESEARCH_IMPLEMENTATION.md)
- GitHub Actions has an optional manual workflow trigger for future controlled runs after merges. This release deliberately **does not** attach unreviewed model text to GitHub Pages, claim a completed research release, or modify existing M2/GraphRAG NO-GO judgments.

## Next stage gates (still OPEN)

1. Choose exact revisions/checkpoint rights for 1M / 14M / 90M / 135M / 360M / 500M and verify role/CPU feasibility.
2. Freeze independently labeled natural-language cohorts split by source/entity; require honest zero-context/contradiction/no-answer cases.
3. Run *matched same-model* no-RAG, naive, Hybrid RRF, span selection, extractive quote and oracle diagnostic with true full prompt token accounting, warm/cold control, peak RSS and p95.
4. Double human evidence review with disagreement adjudication and a sealed holdout. Report risk/coverage and paired uncertainty. **Only then** decide whether the optimizer improves anything.
5. Export provenance-linked, correctly licensed **public aggregate results only** to the observatory after review.

**Bottom line:** Pythia-14M and SmolLM2-135M really ran, and both produced weak unreviewed generations in this tiny smoke. No scientific claim about ultra-small-model RAG quality or improvement has been established.

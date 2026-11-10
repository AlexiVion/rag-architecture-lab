# MICRO-RAG v0.2 M5 — Real DeBERTa INT8 ONNX vs FP32 on CPU

**Date:** 2026-11-10 UTC. **Verdict:** QUANTIZED_ENGINEERING_PARITY_PASS / SINGLE_RUN_EFFICIENCY_SIGNAL / RAG_RELIABILITY_UNVERIFIED.

## Experiment

We executed the **same published** DeBERTa-v3-xsmall NLI checkpoint in two formats: author-published FP32 PyTorch safetensors, and author-published ONNX AVX2 INT8. This is a **model execution/backend comparison**, not a new compression invention, an end-to-end RAG measurement, or scientific evidence of general factual reliability.

- Model: [cross-encoder/nli-deberta-v3-xsmall](https://huggingface.co/cross-encoder/nli-deberta-v3-xsmall) @ immutable revision `a150876415327c80daeff35ca6f68f5ed8cf5c24`, model-card license Apache-2.0; 70,831,107 parameters (FP32 checkpoint).
- ONNX file: `onnx/model_quint8_avx2.onnx` (original author's published export); SHA256 **`21b14751a95520953bfcc607ceeb617de7cbeaeb6d60f4c8966716c743985337`**, checked against downloaded bytes.
- Ragability corpus: `ofai/RagabilityCorpus`, revision `2251634ed365bfca55e7d808290b0cf2c5fde730`, published CC-BY-SA-4.0 TSV SHA256 `e973f5ac7b4881e2cafe23f39b837643878ea6afdb769d9afa30ff66e93c8285`.
- All **318 derived source pairs from 53 rows / 43 underlying conflict groups**, with 106 contradictions and 212 non-contradictions. Two prediction directions per pair (636 directional inputs) and the same tokenizer + frozen symmetric NLI decision function.
- Two PyTorch CPU threads; ONNX Runtime CPUExecutionProvider, intra 2/inter 1 threads. Models run sequentially on one GitHub-hosted CPU process, fixed FP32 then ONNX order, separate warmups.

## Actual matched results

| Metric | FP32 PyTorch | AVX2 ONNX INT8 |
| --- | ---: | ---: |
| Strict pair classification accuracy | **261/318 = 82.08%** | **269/318 = 84.59%** |
| Balanced accuracy | 80.19% | **82.55%** |
| Correct contradictions /106 | 79 | **81** |
| Contradiction recall | 74.53% | **76.42%** |
| False positive contradiction calls /212 | 30 | **24** |
| Pair label agreement between backends | — | 304/318 (95.60%) |
| Changed class decisions | — | 14/318 |
| Model weight file size | 283,353,172 bytes (283.35 MB) | **87,377,068 bytes (87.38 MB)** |
| Sum of batch model-call wall time | 24,367.28 ms | **15,076.27 ms** |

**Observed differences:** INT8 changed 14 decisions, with a net eight more correct labels on this same public benchmark. It met the preregistered engineering tolerance (accuracy degradation no worse than 2 percentage points, contradiction recall degradation no worse than 5 points). In this one sequential run it reduced weight file bytes by **69.2%** and total measured batch wall time by **38.1%** (~1.62x throughput-equivalent speed). These numbers are not a confidence interval or a reproducible hardware-independent speed guarantee.

The CPU timing includes **tokenization + model forward + softmax** on preloaded weights; it omits source retrieval, claim extraction, abstention, disk load, energy and overall RAG response time. The process peak RSS was shared between both backends and **cannot** be used to claim per-backend memory savings. ONNX was loaded after FP32; runtime cache and batch order can affect the comparison.

## Interpretation

The INT8 export did **not** merely preserve quality in this narrow benchmark: it had a slightly higher measured pair-classification accuracy and contradiction recall, fewer false-positive contradictions, and faster summed batch time. Quantization is not expected to always improve accuracy. On just 43 underlying source groups, these observed gains may be noisy and do **not** establish superiority over FP32 in a new domain. The 318 derived pairs are **not independent observations**.

**GO for further engineering study, not production GO.** Retain INT8 as a candidate to compare with FP32 on separately sourced conflict examples, randomized order, repeated isolated processes, and the eventual complete retrieval/claim-verification pipeline. The previous small-model study found that both off-the-shelf NLI models failed two of three generic sanity controls; this remains a serious trust limitation.

## Exact verification

- Source implementation: [PR #33](https://github.com/AlexiVion/rag-architecture-lab/pull/33), squash merged at commit **`34004081dfb9c49725463507771ef211423a0e48`**.
- Exact experiment source SHA: **`1a152471c482570eda63cce10ddcb5a19d8ad063`**.
- [Full deterministic Python/TypeScript/browser CI #42834352448](https://github.com/AlexiVion/rag-architecture-lab/actions/runs/42834352448) — SUCCESS on exact source SHA.
- [Pinned real CPU FP32 vs ONNX run #42834352753](https://github.com/AlexiVion/rag-architecture-lab/actions/runs/42834352753) — SUCCESS on same source SHA.
- Artifact: `micro-v02-deberta-onnx-int8-parity`, GitHub Actions artifact ID **13773137146**. It records all pair IDs, model/dataset hashes, quality metrics and wall-cost scope. No model weights or CC-BY-SA raw source text were uploaded.
- [Frozen protocol](MICRO_V02_ONNX_PARITY_PROTOCOL.md) and unit tests at `tests/test_micro_v02_onnx_parity.py`.

## Remaining gates

1. Real **independent** multi-domain datasets and human-reviewed source-conflict labels: open. The original Ragability cohort is public and visible; never tune later thresholds against its test outputs.
2. Repeat CPU comparisons as independent processes (randomized AB/BA order, controlled hardware, p50/p95 end-to-end, cold starts, RSS and ideally energy) before claiming general speed or memory wins.
3. Integrate an **actual automatically produced source-claim extractor** and verified NLI decision policy; the existing oracle ablation used answers supplied by benchmark authors. Free-text candidate outputs remain REVIEW in the local pipeline.
4. Full pipeline risk/coverage evaluation with useful nonzero correct coverage and group-aware uncertainty; refuse-all cannot qualify as reliable QA.
5. Independent reuse of this diagnostic is pending, with predeclared model/data splits, source-provenance verification and full-stack CPU measurements.

**Do not advertise:** hallucination-free QA, proven factual accuracy, 38% faster end-to-end RAG, 69% less runtime RAM, universal INT8 superiority, or completed scientific validation.

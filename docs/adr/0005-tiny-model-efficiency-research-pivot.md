# ADR-0005 — Tiny-model optimization becomes the primary research focus

- **Date:** 2026-11-08
- **Status:** Proposed pivot, recorded for review; no benchmark success implied.
- **Owners:** Repository maintainer / research operator
- **Related:** [Project control](../PROJECT_CONTROL.md) · [Experiment protocol](../EXPERIMENT_PROTOCOL.md) · [Original v1.0 blueprint](../RELEASE_WOW_BLUEPRINT.md) · [Master issue #9](https://github.com/AlexiVion/rag-architecture-lab/issues/9)

## Context

The previous portfolio scope emphasized a general catalog of RAG approaches, a ten-model matrix, GraphRAG and an observatory. That scope is broad but not a research claim of novelty. The owner explicitly requests a sharper problem: **optimize RAG systems that use extremely small, permissively-licensed open-weight language models**, rather than relying on frontier-scale generation.

Historical evidence supports the need: the local Qwen2.5-0.5B citation/synthetic experiments show inadequate reliable generation and abstention, while earlier retrieval ablations show that indiscriminate reranking significantly increases CPU latency for small ranking improvements. Do not erase either the negative generation findings or the retrieval baseline.

Relevant prior research MUST be compared, not claimed as original:
- MiniRAG (https://github.com/HKUDS/MiniRAG) already investigates lightweight graph-based RAG for small models.
- TripletRAG (https://aclanthology.org/2026.groundlm-1.72/) uses in-context triplet guidance for small-model RAG.
- Small-model context utilization analysis (https://arxiv.org/abs/2603.11513) reports retrieval-utilization failure modes.
- Efficient context selection/compression is an existing research family (e.g., https://aclanthology.org/2025.findings-naacl.301/).

## Research thesis (hypothesis only)

> Can a strictly budgeted, evidence-first system make 135M–600M parameter generators achieve **better independently verified supported-answer coverage**, at equal or lower end-to-end resource cost, than strong matched naive and hybrid RAG baselines?

The possible contribution is a **CPU-first adaptive evidence budgeter + selective answer mode**:
1. Retrieve with sparse and optionally tiny dense encoders.
2. Select the smallest query-relevant **verbatim evidence spans with original source IDs/offsets**, bounded by an explicit token budget and measured ranking signals.
3. Choose among (a) attributable extractive/templated answer, (b) small-model generation constrained by the selected evidence, and (c) abstention when evidence is not demonstrably sufficient.
4. Preserve immutable stage traces: retrieved candidates, span boundaries, tokens, decision features, exact prompt, model revision, runtime footprint, failure reason and citation/semantic evaluation.
5. Validate with independent human labels or original public answer/evidence labels: a syntactic citation is not proof of entailment.

These are *proposed experimental mechanisms*, not a proven new algorithm. A quote-first extractive mode must be reported separately from a generative-mode win: deterministic extraction is not evidence of increased intrinsic small-LLM ability.

## Hard model and runtime constraints

- **Primary generators:** 135M, 360M, 500M, 600M parameters maximum, one loaded at a time; initial candidates (subject to pinned revision and license verification):
  - `HuggingFaceTB/SmolLM2-135M-Instruct` — Apache-2.0.
  - `HuggingFaceTB/SmolLM2-360M-Instruct` — Apache-2.0.
  - `Qwen/Qwen2.5-0.5B-Instruct` — Apache-2.0; existing canonical baseline family.
  - `Qwen/Qwen3-0.6B` — Apache-2.0; newer control, ensure thinking/non-thinking and prompt settings are fixed.
- **Retrieval:** BM25 with existing `all-MiniLM-L6-v2` (~22M) and optional `BAAI/bge-small-en-v1.5` (~33M; MIT). The previously tested compact cross-encoder is a measurable optional stage, never free.
- **Hardware:** canonical local Windows Ryzen 7 5700U / ~16 GiB RAM, CPU only; benchmark sequentially; do not require paid inference, high-end GPU, proprietary model evaluator or internet at inference time.
- **Openness:** open weights are not necessarily fully open source; log **code, model weights, tokenizer, data availability, license and redistribution rights** separately. Re-verify exact model revisions before download/redistribution.
- **Quantization:** Q4/Q8/FP16 configurations are *separate matched experiments*. Track disk footprint, resident RAM, cold start, warm query time, tokens/sec, retrieval+generation time and setup/index costs. Never imply parameters alone determine memory footprint.

## Controlled experiment matrix (no observed scores yet)

| ID | Pipeline | What it isolates |
| --- | --- | --- |
| MICRO-BASE-00 | Tiny generator without retrieval | Parametric baseline; no external evidence |
| MICRO-BASE-01 | Same tiny generator + naive top-k passages | Standard RAG baseline |
| MICRO-BASE-02 | Same tiny generator + existing BM25/dense Hybrid RRF | Strong current retrieval control |
| MICRO-DIAG-00 | Same generator + oracle supporting passage (evaluation-only) | **Context utilization ceiling**, not a deployable system or trained feature |
| MICRO-OPT-01 | Hybrid + query-aware verbatim span selection | Evidence density/length effects |
| MICRO-OPT-02 | OPT-01 + quote-first attributable/extractive route | Extraction benefit, distinct from generative performance |
| MICRO-OPT-03 | OPT-01 + bounded small-model generation and abstention | Generative quality, refusal and leakage |
| MICRO-OPT-04 | Dynamic retrieval/token budget + conditional expensive reranking | Quality/latency/RAM Pareto tradeoff |
| MICRO-ABL-* | Remove each stage individually | Establish source of improvements and expose regressions |

For each generator class, first compare the exact same model/revision/precision/decoding settings, dataset and machine across variants. Changing the model, quantization or prompt is a separate experiment; any larger-model reference belongs in a clearly separated **diagnostic external reference** and is never a hidden teacher/judge.

## Required metrics and scientific controls

**Primary:** independently supported task-answer correctness/coverage versus total p95 end-to-end latency and peak resident RAM; include an unsafe-answer/unsupported-claim rate and false-abstention rate. Report all denominators and paired confidence intervals. Do not optimize for citation syntax alone or let refusal of every answer appear successful.

**Secondary:** retrieval Recall@K, source/span provenance precision, token budget (input/output), token waste, CPU process time, cold model load, warm throughput, per-stage latency, model bytes/quantization. Joules/energy only if **actually instrumented and calibrated**; parameter count and RAM are not energy proxies.

**Data protocol:** create a small, legitimately licensed **natural-language** benchmark with answerable/irrelevant/contradictory/insufficient and at least some multi-hop items. Split by source document/entity into DEV / CALIBRATION / untouched HOLDOUT. Freeze IDs/source hashes and scoring criteria before testing. Previously exposed SciFact TEST Q1, HotpotQA DEV cohorts and authored synthetic controls cannot be relabeled as independent holdout. Prefer two blinded human reviewers with disagreement adjudication on a smaller audit sample.

**Success condition (pre-register before holdout):** a statistically defensible **Pareto improvement** over a matched same-model RAG baseline: higher supported-answer quality/coverage at no worse unsupported-answer rate and comparable or lower end-to-end CPU cost, or the same quality at materially lower cost. Report uncertainty and the entire risk-coverage curve. If the technique fails, record `NO_GO` and preserve the finding.

## Release scope change and backwards compatibility

The previous **exactly ten additional models** comparison is not the primary objective of the new research direction: it becomes an optional separate catalog/research extension unless the owner later explicitly requires it. The new *proposed* v1.0 acceptance contract is a reproducible **tiny-model optimization study**, one compelling interactive experiment explorer and independently audited outcomes.

The original [blueprint](../RELEASE_WOW_BLUEPRINT.md), model registry and benchmarks remain unchanged as historical material. The [master issue #9](https://github.com/AlexiVion/rag-architecture-lab/issues/9) and release gates must be reconciled through a reviewed scope amendment **before any old gate is called closed or new v1.0 is released**. No retroactive rewriting of prior experiments. Existing `main` and `RAGPipeline` defaults remain untouched.

## Immediate work plan

1. **MICRO-00:** literature and license/revision review; select one generator (135M), one small retrieval strategy and a 500M existing control; define experiment IDs.
2. **MICRO-01:** freeze natural-language DEV/CALIBRATION/HOLDOUT cohorts, evidence annotations, primary metrics, resource budget and evaluation rubric.
3. **MICRO-02:** run a strict paired baseline: no retrieval, naive RAG, Hybrid, oracle-context diagnostic, with exact per-case traces.
4. **MICRO-03:** implement and ablate a provenance-preserving evidence-span allocator; measure utilization vs additional input-length reductions.
5. **MICRO-04:** add controlled extractive/generative/abstention routing and cost-aware conditional reranking, only after independent metrics are available.
6. **MICRO-05:** run the frozen holdout once, publish negative and positive comparisons, build evidence-linked explorer panel, update release scope and checkpoint.

**No benchmarks, empirical improvements, zero-risk claim, or release approval arise from accepting this ADR.**

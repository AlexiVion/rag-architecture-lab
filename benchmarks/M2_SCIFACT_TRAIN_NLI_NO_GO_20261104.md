# M2-STANCE-TRAIN-01 — Scientific NLI evaluation: NO-GO

**Date:** 2026-11-04  
**Repository:** `AlexiVion/rag-architecture-lab`  
**Study:** `scripts/run-m2-original-scifact-stances-local.ps1`  
**Model:** `cross-encoder/nli-MiniLM2-L6-H768` (SNLI/MultiNLI-trained)  
**Data:** original SciFact `claims_train.jsonl` and `corpus.jsonl`, expert-labelled SUPPORT/CONTRADICT rationales  
**Decision:** **NO-GO for use as a scientific evidence, stance or abstention gate in V2**

## Provenance and execution

The maintainer's PowerShell run pulled commit `97caca7`, passed the full Python test suite, loaded the original SciFact archive with its pinned checksum, loaded cached public NLI weights, and completed a fixed balanced sample. The terminal output reported:

- Original SciFact TRAIN annotated rationales available: **616 entailment, 341 contradiction**.
- Deterministic seed 17 sample: **20 SUPPORT + 20 CONTRADICT = 40** labelled document/claim pairs.
- Experiment returned `M2_ORIGINAL_SCIFACT_TRAIN_LABELLED_PILOT_COMPLETED` and `M2_ORIGINAL_GOLD_STANCE_EVALUATION_COMPLETE`.
- Local output: `runs/stance-eval/SCIFACT_ORIGINAL_TRAIN_STANCE_20261104T151846152707Z.json`, and matching Markdown. The raw outputs are gitignored. **This public summary is based on the maintainer's pasted execution log**, not an independent inspection of the private JSON.

The pairs use the original expert-selected rationale sentences as premises and the corresponding SciFact training propositions as hypotheses. This is *oracle evidence*, **not** a retrieval benchmark.

## Confusion matrix

| Gold original SciFact TRAIN stance | Model: contradiction | Model: entailment | Model: neutral | Total |
|---|---:|---:|---:|---:|
| SUPPORT (entailment) | 2 | **2** | 16 | 20 |
| CONTRADICT (contradiction) | **9** | 1 | 10 | 20 |
| **Total** | **11** | **3** | **26** | **40** |

| Measure | Observed value |
|---|---:|
| Sample accuracy | **11 / 40 = 27.5%** |
| Balanced recall (two gold classes) | **27.5%** |
| SUPPORT / entailment recall | **2 / 20 = 10%** |
| CONTRADICT / contradiction recall | **9 / 20 = 45%** |
| Predicted neutral rate, despite no neutral gold labels | **26 / 40 = 65%** |
| Constant-single-gold-class accuracy on this balanced sample | **50%** |

**Interpretation:** the NLI strongly over-predicts neutral on this evidence-rationale sample, yielding a poor outcome relative to a trivial balanced-sample baseline. Earlier unlabelled TRAIN experiments likewise produced 12/12 neutral predictions, and the simple common-language controls returned `NO_GO_BASIC_CONTROL_FAILED`, though the exact failed toy probe cannot be identified from the terminal log alone.

## Decision and boundaries

**NO-GO:** do not use this model/configuration as a V2 answerability, contradiction, entailment, or abstention gate; do not promote it into the default RAG architecture. Keep the baseline Hybrid RRF and existing citation-syntax fail-closed behavior unchanged. That syntax gate is not a semantic entailment validator.

This decision **does not** mean:

- All NLI models are inadequate for scientific documents.
- The RAG application has 27.5% end-to-end accuracy.
- Gold rationales reproduce realistic retrieved noisy evidence.
- This 40-example TRAIN study estimates held-out deployment performance.
- A constant-class heuristic is safe or useful for biomedical tasks.
- The entire M2 milestone has passed. It has not.

**Follow-on M2 gate:** require new, independently validated scientific evidence-adequacy and answer-quality observations before introducing a semantic runtime decision. If another model is evaluated, declare the model, training data, budget, metrics and held-out validation protocol in advance. Avoid additional sweeps of this failed model without a new rationale. Do not tune based on previously inspected SciFact TEST query 1.

## Reproduction and source

- Original official SciFact source: https://github.com/allenai/scifact and its `doc/data.md`.
- Experiment implementation: `src/raglab/evaluation/scifact_stance_eval.py`.
- One-command local experiment: `scripts/run-m2-original-scifact-stances-local.ps1`.
- Dataset source SHA256 pin and seed are enforced by the experiment code.
- No SciFact TEST labels, Qwen or paid APIs were used.

**Result classification:** evidence-based experimental NO-GO; not a general scientific benchmark or release certification.

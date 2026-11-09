# MICRO — Extreme Efficiency RAG / executable research foundation

**Status:** prototype implementation, **NOT** a validated improvement or model leaderboard. **This file documents what code can actually do**, not an empirical claim about 1M–600M models. LinkedIn portfolio release v0.1.0 is separate and remains unchanged.

Primary idea: compare the **same tiny generator** with controlled evidence packing and a consistent retrieval setup, then independently inspect task correctness, source support, abstention and end-to-end resource cost.

- [MICRO issue #11](https://github.com/AlexiVion/rag-architecture-lab/issues/11)
- [Research hypothesis / ADR-0005](adr/0005-tiny-model-efficiency-research-pivot.md)
- [Canonical current project gates](PROJECT_CONTROL.md)
- [Scientific protocol](EXPERIMENT_PROTOCOL.md)

## What was implemented in this research iteration

| Phase | Feature | Scientific status |
| --- | --- | --- |
| MICRO-00 | Explicit proposed 1M/14M/31M/70M/135M/360M/500M/600M registry with license-review flags | **Model performance NOT MEASURED; revisions NOT PINNED** |
| MICRO-01 | Versioned dev fixture, source hash, case groups and split leakage checks; all "holdout" execution blocked in default driver | **Mechanical fixture ONLY; independent labeled dataset NOT CREATED** |
| MICRO-02 | Paired CPU-first BM25 trial preparation: no RAG, naive full-passage prefix, query-aware spans, separately labeled quote-only extraction and oracle-gold **diagnostic** | **No actual tiny-model scores until operator supplies local weights and independent reviews** |
| MICRO-03 | Verbatim source-span selection with original document ID, offsets, quote, rank, bounded lexical-token context; matched naive-prefix budget | **Algorithm implemented; quality improvement NOT ESTABLISHED** |
| MICRO-04 | Explicit refusal when retrieved evidence unavailable; unverified generation drafts; source quote is not proof of factuality | **Semantic support/calibrated refusal NOT VALIDATED** |
| MICRO-05 | Human review consensus aggregator, two reviewer IDs, disputes excluded and denominators explicit | **A scoring tool, not completed human review or holdout** |
| MICRO-06 | Existing seven-section observatory remains unchanged; new measured MICRO data NOT published | **OPEN** |

## Reproduce locally without paid APIs or model downloads

From repository root after installing the Python package as in [RELEASE_INSTALLATION.md](RELEASE_INSTALLATION.md):

```bash
python -m raglab.micro registry --output runs/micro-registry.json
python -m raglab.micro prepare --data experiments/micro_smoke_fixture.json --output runs/micro-dev-smoke.json --model-id pythia-14m --max-context-tokens 128
python -m pytest -q tests/test_micro_spans.py tests/test_micro_experiment.py tests/test_micro_review.py tests/test_micro_cli.py
```

The above is **instrumentation only**. It performs real BM25 retrieval, source span selection and prompt construction on a deliberately **synthetic demonstration**. It does **not** download, load or call Pythia; candidate name only labels the proposed model.

To actually run a **locally present** compatible causal LM, after separately checking its exact license, checkpoint revision, disk/RAM requirements and model/tokenizer integrity:

```bash
python -m pip install -e ".[generation]"
python -m raglab.micro prepare \
  --data experiments/micro_smoke_fixture.json \
  --output runs/micro-local-drafts.json \
  --model-id smollm2-135m \
  --backend local \
  --local-model-dir /path/to/already-downloaded/smollm2-135m
```

Use PowerShell one line on Windows and substitute the actual local model folder. **No model download is requested by this CLI.** Model-generated text is recorded as an **unverified draft**. Avoid publishing raw model prompts, nonpublic datasets or model artifacts.

### Phase 3: human scientific audit

Reviewer judgments are a JSON array. Each item has exactly:

```json
{
  "case_id": "dev-mars",
  "mode": "spans",
  "reviewer_id": "blinded-reviewer-a",
  "answerable": true,
  "abstained": false,
  "task_correct": true,
  "source_supported": true
}
```

At least **two independently declared reviewers** must agree on case/mode labels for inclusion. When an answer abstains, `task_correct` and `source_supported` must be `null`. Disagreements/missing reviewers stay explicitly unscored. The code cannot establish that reviewers were truly blind or independent, or that the synthetic fixture is a credible scientific holdout.

```bash
python -m raglab.micro score --reviews /local/path/reviews.json --output runs/micro-review-summary.json
```

Reported denominators distinguish total consensus cases, answered, answerable, unsupported/incorrect, and false abstention. No automatic NLI/LLM judge is treated as human ground truth.

## Important controls

1. **Model family matters:** TinyStories 1M is trained for a restricted domain; Pythia 14M–70M are base language models; SmolLM2 and Qwen instruction checkpoints have different instruction-following ability. This is not a comparable leaderboard without tasks, revisions and prompt adaptations.
2. **Licenses are provisional:** each checkpoint has `license_review=PENDING_EXACT_REVISION_REVIEW`; `license_claim` is metadata to verify. No weight redistribution and no "fully open-source" assertion.
3. **Budget unit:** `lexical_proxy_not_model_tokenizer`. Both naive and span-selection use the same explicit proxy budget (or a model tokenizer when provided) and log the full prompt proxy count. A local checkpoint provides its own tokenizer for context budgets; exact prompt-template and special-token accounting still requires pinned template measurement before scientific conclusions.
4. **Provenance:** every chosen quote is an exact slice of the original input document with start/end offsets; an ellipsis is **never** inserted and reported as verbatim evidence.
5. **Retrieval is not truth:** lexical query overlap is a selection heuristic, not support, entailment, answerability or factual-correctness validation.
6. **Oracle mode:** uses annotated evidence document IDs; must never be compared as a deployable pipeline or used to tune a frozen holdout.
7. **Holdout security:** default research runner rejects all `split=holdout` cases. An independently pre-registered and adjudicated scientific release protocol must be approved before creating any dedicated final evaluation runner.
8. **No claim of a win:** first run real baselines, then ablations, then blinded human review on a new uncontaminated cohort. Existing SciFact TEST and exposed HotpotQA DEV cannot become untouched scientific holdout.
9. **Cost:** current runner reports per-case retrieval/context/generation wall time. Final cross-model study still needs **p50/p95 end-to-end CPU, peak RSS, cold start, model bytes/quantization, throughput, paired CIs** and human-reviewed answer quality. CPU time is not energy.
10. **Preserve main:** no change to `RAGPipeline` defaults, release-bound published JSON or the negative GRF/M2 evidence.

## Next scientifically binding gates

- [ ] MICRO-00: verify exact checkpoint commits, tokenizer variants, CPU suitability and redistribution terms before any real model load.
- [ ] MICRO-01: create natural-language, independently labeled DEV/CALIBRATION/HOLDOUT splits by source/entity, freeze evaluation rubric and SHA before optimization.
- [ ] MICRO-02: run 14M vs 135M vs 500M **matched** real model baseline on canonical CPU and log RAM/latency; use oracle context only for context-utilization diagnosis.
- [ ] MICRO-03/04: ablate each optimizer with controlled evidence budget and compare to strong Hybrid RRF; only then add selective reranking/extractive routing if justified.
- [ ] MICRO-05: require double-blind human review, adjudication and a one-time untouched holdout with bootstrap uncertainty.
- [ ] MICRO-06: export only source-hashed, license-safe and independently reviewed PUBLIC summaries to a new observatory view.

**This implementation is a genuine source-code milestone, not an empirical research milestone.**

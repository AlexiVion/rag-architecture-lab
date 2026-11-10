# M2-GUARD-STRESS-01 — audited operator result and decision

**Observed on Windows:** 2026-11-04. **Status:** full local `pytest` PASS, `M2_GUARD_STRESS01_COMPLETE`. This is a **40-case author-labelled, synthetic, offline grammar stress test**, not independently adjudicated semantic evaluation.

## Archived execution evidence

- Research branch: `feat/research-lab-architecture-catalog-20261104`, prior experiment implementation head `cfc0470e447ebc13897656265c70d7650b9020b3`.
- Canonical frozen cases SHA256: `81e702cdb4be3638ef3b6b0e27be96df34523ee6a684f068f6d570600ea7bc16`.
- Local report: `runs/m2-guard-stress01/report.json` (gitignored; the original byte-level report SHA256 was not in the console).
- 40 completed cases: 16 author-labelled positives, 24 author-labelled negatives.
- **False rejection: 8/16 (50%)** of authored positive cases.
- **False acceptance: 0/24** of authored negatives, specifically under these five templates.
- Zero new model calls, zero external publications and no modification of the default RAG pipeline.

| Condition | Authored allow? | Allowed | Rejected | Interpretation |
|---|---|---:|---:|---|
| Canonical evidence | Yes | 8/8 | 0/8 | Exact supported grammar recognized |
| Valid paraphrased evidence | Yes | 0/8 | 8/8 | Systematic failure to recognize semantically equivalent phrasing |
| Different-entity evidence | No | 0/8 | 8/8 | Off-target evidence withheld in this template |
| Conflicting manufacturers | No | 0/8 | 8/8 | Conflicting statements withheld in this template |
| Extra/injected instructions | No | 0/8 | 8/8 | Unrecognized additional content withheld |

The previous 24-case M2-SYNTH-01 post-hoc replay found that the exact-pattern guard **would** have blocked the three negative-context drafts the original citation-only pipeline accepted. The new, differently named 40-case set reveals the expected cost: **all eight clearly valid paraphrases are rejected**. Neither synthetic outcome is a defensible estimate of broad model accuracy, semantic entailment, calibrated abstention or production safety.

### Research decision

**NO-GO** for automatic answer publication. Keep `M2-GUARD-DEV-01`, the experimental citation V2 parser and all Qwen prompt experiments **development-only**. Do not modify the default `RAGPipeline.evidence_gate=None`. Do not tune the current guard and then present results on these same 24/40 exposed items as independent confirmation.

The current exact-pattern guard has demonstrable utility as a *bounded pre-generation filter for a highly structured relation*, but **fails on ordinary paraphrases**. A production-general evidence sufficiency system needs a separate method of matching source meaning and detecting contradiction, not a larger collection of hard-coded phrase alternatives without evaluation.

## Next M2 release gate: independent source-support study

1. **Build a labelled natural-language evidence corpus** across multiple topics, writing styles and question types. Use already available **SciFact TRAIN evidence-review material** only as development material; never use the previously exposed SciFact TEST Q1 or any other exposed 24/40 synthetic control as an untouched test.
2. Annotate **source relevance**, **claim-level support / contradiction / insufficiency**, and **expected behavior** independently of the candidate model output; retain exact evidence spans and uncertainty. Prefer two reviewers and adjudicate disagreements. Do not substitute an off-domain NLI model that previously received NO-GO.
3. Partition by **document and entity group**, not merely by individual question; freeze dev, calibration and held-out IDs and source hashes **before** selecting a new guard, changing prompts or viewing holdout outputs.
4. **Predeclare metrics and failure costs:** supported-answer acceptance, unjustified abstention, unsupported-answer acceptance, contradiction leakage and latency, each with denominators and uncertainty intervals. Report error counts as well as rates; a zero error on a small sample is not a guarantee.
5. Compare **current syntax-only baseline vs a narrowly specified evidence filter** under identical source contexts. Freeze the model revision and response policy where feasible. Keep human review and the publication gate disabled until independent support validation justifies a separately controlled deployment.

**Next engineering step:** reuse `src/raglab/evaluation/semantic_review.py` and the existing unlabelled TRAIN-only review workflow; do not create another automated evaluator that calls a syntactic match 'semantic correctness'. Advance M2 only when source/claim labels and a held-out protocol are available and inspectable.

## Scope/provenance guardrails

- This file records the user's **actual terminal result**, not results inferred from source code or a rerun.
- The existing original report is local and was not read into GitHub; no new raw model data are published here.
- No new model evaluation or dataset download happened as part of this report.
- The other retrieval and graph-study decisions remain unchanged; their scientific evaluation is outside this diagnostic.

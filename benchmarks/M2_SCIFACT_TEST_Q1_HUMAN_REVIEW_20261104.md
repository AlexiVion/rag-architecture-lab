# M2-HUMAN-001 — V2 historical SciFact TEST diagnostic

**Date:** 2026-11-04. **Status:** a single completed human-labelled diagnostic, not a train set or a statistically representative evaluation.

## Provenance

- Human reviewer identifier: `reviewer-1`.
- Dataset: `beir/scifact/test`, query ID `1`.
- Original generated answer: `runs/v2/answer_20261104T125649Z.json` on the maintainer's machine.
- Human annotated packet: `runs/reviews/annotated_review_answer_20261104T125649Z_20261104T141613Z_20261104T142230Z.json` on the maintainer's machine.
- Verified from the maintainer's PowerShell session and final scoring log; **the private original annotated JSON was not uploaded to the repository**, and no claim is made to have independently re-opened it.

## Observations from the completed review

| Axis | Human review / measured result |
|---|---|
| Query | `0-dimensional biomaterials show inductive properties.` |
| Context relevance | All **5 of 5** retrieved sources classified **irrelevant** |
| Candidate text | A statement about why human brain development needs in-vitro models |
| Candidate claim support | **1 of 1** claim marked `supported` by source `S1` |
| Citation syntax | **failed** — zero citations |
| Expected behavior | `abstain` |
| Historical actual behavior | Answer generated and returned, without abstaining |
| Human review status | `complete` |

**Interpretation:** claim-level support is not question-answer relevance. The generated sentence resembles the text of S1, but does not answer the biomedical *proposition* about 0-dimensional biomaterials. The reviewer concluded the system should have abstained given the retrieved material. This is an answer-selection/evidence-selection error **as well as** a citation failure, even though the claim itself is supported by an unrelated source.

This result is a **diagnostic test-set example**, never used to tune threshold values or decide a new retrieval strategy on held-out labels. The version of V2 under review predates the new post-generation citation gate.

## Evaluation lessons

1. Keep independent axes: relevance of the retrieved evidence, support of generated statements, citation syntax/coverage, and appropriateness of answering or abstaining.
2. `fully_supported_claim_rate=1.0` can coexist with the wrong decision to answer. It is not a task-accuracy measure.
3. A complete review is not a model-wide quality score or scientific fact-checking consensus.
4. Do not extrapolate a single case into an accuracy rate, or treat it as a trained evidence classifier.

**Next:** construct a separate, train/dev-only set of answerable, unanswerable and contradictory cases, independently annotated by at least two reviewers, before calibrating relevance or abstention behavior.

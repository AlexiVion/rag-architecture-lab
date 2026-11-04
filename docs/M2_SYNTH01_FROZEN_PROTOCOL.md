# M2-SYNTH-01 — Predeclared 24-case fictional source-control study

**State:** Source protocol, executable, and unit/integration regression tests prepared on the research branch. **No Qwen inference or full Windows regression suite has yet been executed for this stage.** This is **not a natural-language semantic entailment benchmark**, and the four previously examined M2-LIVE-01/02 scenarios are excluded.

## Verified starting point

On 2026-11-04 the maintainer executed M2-REVIEW-02 successfully: full pytest PASS; original Qwen JSON SHA256 `3c9fc0794ab2d2bd3ca10825585926083b0d40067c1696aa77fc90f230ea7816`; four unlabelled review packets exported. They contain source counts 1, 1, 2, 0 and claim counts 1, 1, 1, 0, respectively. The first draft passes **experimental citation syntax only**; neither source entailment nor legitimate refusal has been verified. No model calls and no publication actions.

## Why a new synthetic study?

The previously exposed four documents were used to diagnose and change the prompt. Reusing them as a supposedly untouched quality test would be invalid. A new predeclared suite provides independent *fictional entities*, but still shares the same controlled task family (finding the manufacturer of a named component), so it does **not** represent independent real-world factual QA.

The source code `src/raglab/evaluation/m2_synth_protocol.py` defines six new fictional equipment groups, each contributing four cases:

| Class | Cases | Source condition | Expected narrow behavior |
|---|---:|---|---|
| `answerable` | 6 | One document explicitly states manufacturer | Include the known company name and a citation to the supplied source |
| `irrelevant` | 6 | One topically similar document gives a manufacturer **for another device** | Emit exact `INSUFFICIENT_EVIDENCE` |
| `conflicting` | 6 | Two articles state *different manufacturers for the same device* | Emit exact `INSUFFICIENT_EVIDENCE` |
| `no_context` | 6 | Zero retrieved sources | Skip model invocation and abstain |

**Frozen cases SHA256:** `05e778d4b541d397c27a000d4042549d84b90d047a28f1bbf16b289bda6a3826`. A change in case wording, truth values or source text fails before inference. The gold manufacturer and expected category are stored in the suite manifest, never included in the generated question or evidence sent to Qwen.

## Frozen execution and safe boundaries

- **Generator:** same local `Qwen/Qwen2.5-0.5B-Instruct` used for M2-LIVE-02. The model may load from cache. A model revision is recorded only if it is resolvable; **do not claim the weights are pinned**.
- **Prompt:** exact original M2-LIVE-02 prompt and one-sentence-or-abstain policy, SHA256 `2351f8f969281b7e92c9a827c8f3da79643d75a88c06f6c1c53faf68b25d3246`. The runner stops if the prompt fingerprint differs. No new prompt tuning is permitted after scoring this cohort.
- **Retrieval:** fixed source lists, not Hybrid RRF or full corpus retrieval. Retrieval precision is **not** evaluated.
- **Citation parsing:** record *both* unchanged default citation V1 and opt-in experimental citation V2. No parser promoted or response rewritten.
- **Publication:** **all outputs are research only**, even if the historical pipeline output status is `accepted`. No external calls to publish an answer. All outputs are gitignored.
- **Resumability:** the manifest is written **before inference**. Each case is verified and saved exactly once in `runs/m2-synth01/cases/01.json`, etc. A rerun checks completed rows and resumes only unsaved cases. The report is written exclusively; prior data are never overwritten.

## Scoring rubric and limitations

The strict programmatic *control success* metric is:

- Answerable: the output **mentions the exact known manufacturer string**, passes the experimental V2 source-label syntax check, and does not mention the known competing manufacturer. This is explicitly a **literal+syntax proxy**, not a claim-level truth or entailment metric. A negated statement could contain the right string and must still be reviewed manually.
- Irrelevant / contradictory: the model returns the **exact sentinel** `INSUFFICIENT_EVIDENCE`; any factual answer attempt is counted as a failure, regardless of citation syntax.
- No context: the existing pipeline abstains with **zero model calls**.

Each class has **n=6**, so report per-class raw successes and abstention counts. The overall primary metric is named `synthetic_control_success_rate_NOT_semantic_accuracy`; it should never be described as natural-language faithfulness, a calibrated safety score, an independently human-labelled TEST result, or a general accuracy percentage. The code explicitly keeps semantic support and task relevance unassessed.

## One-command Windows run

From the repository root:

```powershell
& {
    $ErrorActionPreference = "Stop"
    git pull --ff-only origin feat/research-lab-architecture-catalog-20261104
    if ($LASTEXITCODE -ne 0) { throw "PULL_FAILED" }
    & .\scripts\run-m2-synth01-local.ps1
    if ($LASTEXITCODE -ne 0) { throw "M2_SYNTH01_FAILED" }
}
```

The command runs full pytest first. Only if it passes does the runner initialize the manifest and perform **18 local Qwen generations** (the other six are software no-context skips). It records case-by-case checkpoints and prints an aggregate report. Do not confuse the Python test suite passing with the model's actual score.

## What this can and cannot settle

This is a **low-cost robustness check on controlled invented facts**. It can reveal whether Qwen still transfers attributes across unrelated documents, silently chooses between contradictions, omits available citations or refuses despite adequate evidence. It cannot certify that it correctly understands arbitrary scientific text. M2 remains open until an independently adjudicated, predeclared source/claim/abstention dataset and source-faithfulness rubric exist; the existing off-domain SciFact NLI evaluator remains NO-GO. After this study, use its mistakes for development, **not** for a fresh held-out score on the same questions.

## First operator execution: empirical result (2026-11-04)

The frozen cohort, unchanged model/prompt and full Windows pytest suite ran successfully at `c01f62c`. In 24 cases, 18 Qwen calls and 6 no-context skips, the synthetic protocol passed **7 cases (29.17%)**, with category successes **1/6 answerable, 0/6 irrelevant, 0/6 conflicting, 6/6 no-context**. The two nonempty abstention-required categories produced **zero exact `INSUFFICIENT_EVIDENCE` markers**, and the legacy pipeline accepted **two irrelevant** and **one conflicting** answer (all remained quarantined). A syntax acceptance cannot establish factual correctness; the archived raw answers have not been inspected by this assistant. The M2-01 NO-GO remains a development finding rather than a model-wide quality estimate. See `benchmarks/M2_SYNTH01_QWEN_FROZEN_OUTCOME_20261104.md` for the operator-run readout and offline audit. The 24-case cohort is now exposed and **cannot serve as a new holdout for subsequent tuned revisions**.

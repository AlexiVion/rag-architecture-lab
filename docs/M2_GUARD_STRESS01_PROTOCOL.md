# M2-GUARD-STRESS-01 — Author-labelled robustness and over-rejection controls

**Status:** Frozen, authored stress fixtures, executable and regression tests newly committed; **not yet verified by Windows operator**. The prior M2-GUARD-DEV-01 replay and full pytest suite **passed** on 2026-11-04. This remains a development-only rule-based component with NO production/default promotion.

## Verified preceding evidence

The maintainer completed `M2_GUARD_DEV01_OFFLINE_REPLAY_PASS` on the original 24-case archive:

- Original report SHA256: `f33eade629967ff9c4c15bf3ce3e05ca4adc329ece837017bd0fd9ce6ef109e4`.
- Original manifest SHA256: `c5a528a2f7c77c66ba0b56b151fc9909cbcddac5fad491d8f59cf4af8e4efa74`.
- Existing archived sources: 6 hypothetical pre-generation allows and 18 denials: six no-context, six conflicting, six nonparseable/off-target.
- **Three of three** historically syntax-accepted negative-evidence model drafts would have been blocked by the newly designed guard **if it had existed before Qwen generation**.
- Only **one** of the 24 original archived drafts strictly matched the post-generation source/claim grammar. The narrow approach substantially limits coverage.
- Zero new model calls, zero publications. The replay is post-hoc and not a held-out performance estimate.

These numbers prove the implementation behavior on an *exposed* fictional cohort, not the general safety of the gate.

## Why a separate stress suite

`src/raglab/evaluation/m2_guard_stress01.py` freezes **40 original author-labelled fictional cases** with no overlap in entity names with M2-SYNTH-01. It contains eight cases each across five classes:

| Group | Author's expected behavior | What it probes |
|---|---|---|
| Canonical sufficient evidence | Allow | Exact component-vehicle-manufacturer statement with a single source or concordant duplicate evidence |
| Paraphrased sufficient evidence | Allow | Valid fact expressed as a maintenance note, sometimes with a paraphrased question |
| Cross-entity irrelevant evidence | Deny | Correct-sounding manufacturer attributed to a different component/vehicle |
| Conflicting manufacturers | Deny | Two same-component source statements disagreeing on manufacturer |
| Injected extra text | Deny | A correct first source sentence followed by additional instructions to claim a wrong manufacturer |

**Frozen SHA256 (canonical JSON):** `a376e924fea5775a2c26322c31d38d6cbcaf51c5ad179282cb74840f2bc12e97`.

The guard receives only the question and the original source passages. The author-specified positive/negative label is used for scoring **after** the guard has returned. No gold manufacturers, class identifiers or expected labels enter the assessed function. The post-generation checks use authored strings (NOT Qwen) to test whether the candidate's quoted company, component and vehicle can be reconciled with source text.

The study explicitly measures **false rejections** as well as false accepts relative to its authored expectations. A gate that denies all answers is not a useful answer system, even if its false-accept count is zero. Template paraphrases are expected to reveal the gate's restricted coverage.

## Run the bounded offline check

From the repository root:

```powershell
& {
    $ErrorActionPreference = "Stop"
    git pull --ff-only origin feat/research-lab-architecture-catalog-20261104
    if ($LASTEXITCODE -ne 0) { throw "PULL_FAILED" }
    & .\scripts\run-m2-guard-stress01-local.ps1
    if ($LASTEXITCODE -ne 0) { throw "M2_GUARD_STRESS_FAILED" }
}
```

The driver is ASCII-only for Windows PowerShell 5.1. It runs **all pytest tests first**, then performs a pure offline guard evaluation. It stores `runs/m2-guard-stress01/report.json` under gitignored local data, refusing to overwrite changed outputs. There are **zero Qwen calls, zero reruns of historical benchmarks, zero publication actions**.

## What results may legitimately mean

These are **hand-authored cases created after seeing the previous 24 synthetic results and after implementing the guard**. Their labels are not independently adjudicated; their wording follows a narrow equipment/manufacturer domain. False-rejection and false-accept numbers describe only these 40 fixtures; they are NOT a statistically representative test of natural-language entailment, scientific source relevance, calibrated abstention or safety under adversarial prompting in the wild. No production guard promotion follows from this score.

A stronger next scientific milestone needs a separately annotated natural-language corpus with varied tasks and sources, adjudicated provenance/citation support and a disjoint holdout; keep negative old SciFact NLI as NO-GO, and leave RAGPipeline.evidence_gate default None until supported validation.

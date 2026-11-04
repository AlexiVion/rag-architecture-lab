# M2-GUARD-DEV-01 — Narrow evidence relation gate, replay only

**Status:** first development-only implementation committed, **awaiting maintainer's Windows pytest and local replay**. It does NOT modify `RAGPipeline`, switch the citation validator, publish answers or run any model. This is a narrow *post-hoc prototype*, not a semantic entailment engine.

## Trigger: fully audited M2-SYNTH-01 failure

The maintainer ran the full test suite and `M2_SYNTH01_ARCHIVED_AUDIT_PASS`. Original immutable report SHA256: `f33eade629967ff9c4c15bf3ce3e05ca4adc329ece837017bd0fd9ce6ef109e4`; manifest SHA256 `c5a528a2f7c77c66ba0b56b151fc9909cbcddac5fad491d8f59cf4af8e4efa74`.

The original 24 cases yielded a narrow proxy of 7/24 (answerable 1/6, irrelevant 0/6, conflicting 0/6, no-context 6/6); **no exact `INSUFFICIENT_EVIDENCE` from Qwen** on 12 nonempty negative controls. The old citation-only pipeline `accepted` three negative source situations:
- `M2S01-irrelevant`: `Crescent Labs developed the Helix Pressure Unit for the Kestrel Explorer [S1].` — the source assigns this component to a **different vehicle**.
- `M2S02-conflicting`: `Vantage Mechanica developed the Prism Course Module installed on the Boreal Cartographer [S2].` — source S1 attributes the identical component to a different company.
- `M2S05-irrelevant`: `Falcon Workshop developed the Polar Thermal Sensor for the Ravenna Probe [S1].` — again transfers a company/component from a different vehicle.

All three are internally marked `accepted` on **citation syntax alone**. No output was externally published. This is a concrete risk within **one fictional task domain**, not an independently measured broad factual-error rate.

Many of the six adequate-source drafts mention the expected manufacturer but fail to cite with a valid `[S1]`; others use invented document-id tokens. Syntax repair alone cannot fix unsupported or contradictory evidence.

## What the development gate actually does

`src/raglab/evaluation/m2_guard_dev01.py` recognizes ONLY the exact English question pattern:

`Which company developed the {component} installed on the {vehicle}?`

It parses only the strict positive source form:

`The {component} installed on the {vehicle} was developed by {manufacturer}.`

A source must match the same component AND vehicle, and all supplied source statements must agree on the **same manufacturer**. Missing sources, off-target entities, extra/unparsed sentences, conflicts, duplicate source IDs, unexpected grammar and uncertainty fail closed. The parser **does not use the authored `category`, expected manufacturer from the scorer, or previously saved model candidate text** to decide pre-generation adequacy.

A separate strictly formatted post-generation check, for the same narrow grammar, requires a generated manufacturer/component/vehicle relation matching the extracted source and a valid corresponding citation label. It **never appends citations** or rewrites the model candidate. Even a matching candidate returns `safe_to_publish=false` because this is an unvalidated development prototype. Unknown entities and natural-language paraphrases will intentionally be rejected, including potentially correct answers.

There is an **optional callback** through the pre-existing `RAGPipeline(evidence_gate=...)` interface for a research copy; the default pipeline's `evidence_gate=None` is unchanged. The prior Qwen run is NEVER re-executed and this prototype does not assess general text, science, multi-hop claims or multilingual support.

## Post-hoc replay on immutable output (NO MODEL)

`src/raglab/evaluation/m2_guard_dev01_replay.py` first invokes the full `audit_saved_study` provenance checker for the original 24 cases and hard-pins the two exact original report and manifest SHA256 hashes. It then computes:
- Which of the original sources would satisfy the *newly designed* exact pre-generation relation test.
- Which **original** accepted negative controls would hypothetically have been rejected before inference.
- Which original model strings satisfy the strict optional post-generation relation+label parser.
- Distinguishes observed original pipeline status from counterfactual decisions; all publication actions remain zero.

**Crucial:** this is **post-hoc on exposed cases**. Even if all 12 negative source cases are blocked, that cannot validate a semantic classifier or establish an unbiased new zero-error rate. A later held-out test must contain different phrasings, facts, contradictions, source structures and errors, with independently adjudicated labels and preregistration **before looking at new model outputs**.

## One Windows command

```powershell
& {
    $ErrorActionPreference = "Stop"
    git pull --ff-only origin feat/research-lab-architecture-catalog-20261104
    if ($LASTEXITCODE -ne 0) { throw "PULL_FAILED" }
    & .\scripts\replay-m2-guard-dev01-local.ps1
    if ($LASTEXITCODE -ne 0) { throw "M2_GUARD_REPLAY_FAILED" }
}
```

The script is ASCII-only for Windows PowerShell 5.1, runs the **entire pytest suite** first, and only if tests pass audits the already-saved 24-case JSONs without Qwen. It writes `runs/m2-guard-dev01/counterfactual.json` exclusively and refuses to overwrite altered output. The original case files and research report do not change.

**Status policy:** NO-GO automatic factual publication; DO NOT promote the new guard or experimental citation parser to default; train/DEV future safety gate first, independently evaluate relevance/support/abstention on a disjoint, representative cohort. The model revision still needs pinning for stronger scientific comparisons.

## Actual operator result — PASS (2026-11-04)

The operator ran full Windows pytest PASS and original-file-verified `M2_GUARD_DEV01_OFFLINE_REPLAY_PASS`. Report SHA256 `f33eade629967ff9c4c15bf3ce3e05ca4adc329ece837017bd0fd9ce6ef109e4`; manifest `c5a528a2f7c77c66ba0b56b151fc9909cbcddac5fad491d8f59cf4af8e4efa74`. Counterfactual decision: pre-generation **allow 6**, **deny 18**; all three previously syntax-accepted negative-source drafts would have been denied, if the guard had been applied before generation. `DENY_NO_CONTEXT=6`, `DENY_SOURCE_CONTRADICTION=6`, `DENY_UNPARSEABLE_SOURCE=6`. Strict postgeneration match was **1/24** on already generated Qwen drafts. No Qwen calls, no publications and no statistical held-out result.

An additional no-model **authored paraphrase and adversarial coverage stress suite** has been frozen in `docs/M2_GUARD_STRESS01_PROTOCOL.md`. It does not affect this result, the original RAGPipeline or any production publication policy.

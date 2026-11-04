# M2-DEV-EVIDENCE-01 — Controlled evidence review candidates

## Purpose

After M2-HUMAN-001 exposed a **source-supported but off-task** generated answer, construct an independent, reproducible development-only evidence sample. Do not calibrate abstention against the already inspected SciFact **TEST** query.

The tool uses `beir/scifact/train`, selects **six** training propositions reproducibly by `sha256(seed|query_id)` (seed 17), and creates three **unlabelled** evidence scenarios each:

1. `qrel_relevant_candidate` — one article marked relevant by TRAIN qrels. Qrel relevance does **not** establish stance, entailment or answer sufficiency.
2. `cross_query_alternate_candidate` — one gold article associated with a *different* training proposition, excluding the query's own qrel IDs. This is an intentionally mismatched **candidate**, but is not automatically irrelevant or contradictory.
3. `no_context_control` — an explicit empty evidence set. This makes lack of retrieved evidence observable but assigns no automatic target behavior.

This yields **18 packets** for human review, with no generated answers and no automatic labels. The packets omit qrels; a separate manifest records selection provenance and the corpus fingerprint. The negative and contradiction labels are **not** fabricated; contradiction must be independently annotated or obtained from a properly licensed, separately sourced stance-labelled dataset.

## Local build

From the repository root:

```powershell
.\scripts\prepare-m2-dev-cases-local.ps1
```

This runs tests, loads the cached SciFact training corpus and writes a **new** directory under `runs/dev-cases/M2-DEV-EVIDENCE-01_*` with `manifest.json` and 18 review packet JSON files. It refuses to overwrite an existing run. No Qwen, embeddings or cross-encoder model is loaded.

To review a particular case without guessing its label:

```powershell
.\.venv\Scripts\raglab.exe review-interactive --path "runs/dev-cases/<run>/DEV001_qrel_relevant_candidate.json" --output "runs/reviews/annotated_DEV001.json"
```

The reviewer chooses source relevance and expected answer/abstain behavior. As no generation has been run, claim support is not scored and actual response behavior is `unknown`. This is **evidence-adequacy preparation**, not end-to-end answer faithfulness.

## Evaluation gates before calibration

- Independent review of selected cases, ideally two reviewers and adjudication of disagreements.
- A separately acquired/annotated set of genuinely contradictory evidence: randomized unrelated passages must not be called contradictions.
- Define a decision policy (answer / abstain / uncertain) using **train/dev** only.
- Freeze and benchmark that policy independently on a held-out test split *once*, preserving prior test-set diagnostic exposure.
- Document model/corpus revisions, latency/cost and per-class confusion before promoting defaults.

## Blind, resumable annotation of a small group (2026-11-04)

To review **only three cases for one training proposition**, use:

```powershell
.\scripts\review-next-m2-dev-group-local.ps1
```

The script runs the tests, selects the latest training suite and opens a small interactive group. The source origin (qrel-positive / cross-query / empty) is concealed from the terminal prompts; opaque filenames are used to avoid exposing the arm. Reviewers see the proposition and actual snippets, and choose source relevance and whether evidence is sufficient to answer. **No claims are generated** and their support scores remain unavailable. `u` means uncertain; it is valid for complex biomedical propositions. A second invocation continues with the next unreviewed group, keeping all previously saved files unchanged. The program does not infer any labels.

Completed or incomplete review snapshots are stored in git-ignored `human-reviews` within the suite; originals and manifest are preserved. An incomplete review is not counted as a finished label. The experimenter must separately check adjudication and labeling disagreements before calibrating decision thresholds. This remains a development sample, not a held-out benchmark or proof of model accuracy.


## No-prompt audit — operator preferred mode

You can skip all interactive review and run the **entire 18-case objective audit** using:

```powershell
.\scripts\run-m2-dev-automatic-local.ps1
```

This validates all tests and every original case against the local SciFact **TRAIN** corpus, including source document integrity, selected qrels, query mapping, all 3 balanced arms, and no-context controls. Writes `AUTO_AUDIT.json` and `AUTO_AUDIT.md` under the suite; rerunning replaces only these machine-generated reports, **never original packets or human reviews**.

The safe deterministic policy is: **no context means abstain without generation**. For the 12 nonempty evidence scenarios, relevance/sufficiency/entailment remain `not_evaluated`. This is intentionally not a fabricated 18/18 semantic score, does not call Qwen or embeddings, and does not learn/calibrate an abstention threshold. `human-reviews` is optional and separate. A valid semantic benchmark will later need actual verified labels or a separately measured automated judge with audited error rates.

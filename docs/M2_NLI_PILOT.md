# M2-DEV-NLI-PILOT-01 — Automatic local NLI, no questions

This experiment compares existing SciFact TRAIN scientific propositions (hypotheses) with the 12 nonempty, **exact snippets** saved in the 18-case development suite (premises). The other six cases are explicit empty-context controls; they follow the deterministic no-context abstention rule without model inference.

## Model

The open-weights CPU cross-encoder model is cross-encoder/nli-MiniLM2-L6-H768, trained on SNLI/MultiNLI and documented at https://huggingface.co/cross-encoder/nli-MiniLM2-L6-H768. The documented label order is contradiction, entailment, neutral. The published model is approximately 82 million parameters. The first local execution may download model weights; a model-loading/network failure is reported as a failure and does not fabricate predictions.

The experiment relies on the existing installed sentence-transformers dependency (benchmark extra), not Qwen and not a paid service. It performs strict source/corpus fingerprint validation before model initialization. Records include an available model revision, score vectors, source-arm provenance and the original case IDs, all in a local git-ignored output.

## How to run

On Windows PowerShell, from the repository root:

    .\scripts\run-m2-nli-local.ps1

The script first runs pytest, then loads the SciFact TRAIN cached corpus and the NLI model, scores 12 document/claim pairs on CPU and saves timestamped AUTO_NLI_*.json and AUTO_NLI_*.md in the latest suite folder. No interactive questions are asked; all original packets and human annotations are unchanged.

## Interpretation and limitations

- The output class and three softmax values are uncalibrated **model predictions**. They are not verified truth, biomedical contradiction labels or measured factuality.
- Model training domains (SNLI/MultiNLI) differ from SciFact. Source snippets and model inputs may be truncated. A high entailment score does NOT certify that an answer is safe to give.
- Qrel-positive articles are only candidate documents. Cross-query documents cannot automatically be called irrelevant or contradictory.
- Empty contexts require abstention regardless of model, but this does not establish a calibrated policy for nonempty evidence.
- No SciFact TEST labels or historical test failure feed this experiment; no default RAG evidence gate is changed.
- Scientific validity and deployment metrics still require an independently labelled train/dev set, reviewer agreement or a separately validated semantic judge.

This pilot progresses from a purely structural audit to measurable predictions, **not** to a completed ground-truth accuracy benchmark.


## Actual local outcome and mandatory sanity check

On 2026-11-04 the maintainer ran the 18-case SciFact TRAIN pilot successfully: 12/12 nonempty cases produced a neutral prediction, 0 entailment, 0 contradiction, and six empty controls were skipped. The cached public NLI weights downloaded successfully. Only harmless unauthenticated HF Hub / Windows symlink warnings appeared. This is NOT an observed scientific accuracy score.

New command (fully automatic, no human prompts):

    .\scripts\diagnose-m2-nli-local.ps1

It checks the saved probability vectors and their class order, compares predictions across the two nonempty source-selection arms, validates the original TRAIN data, and runs three common-language classifier probes (one entailment, one contradiction, one neutral). The same cached model is loaded on CPU; this is only a functionality smoke, not an out-of-domain benchmark.

Whether toy probes pass or fail, this uncalibrated NLI model does not become a production abstention filter. No SciFact TEST data or human truth labels are used, no runtime policy is updated. Diagnostic JSON and Markdown are stored only in the git-ignored TRAIN suite folder.

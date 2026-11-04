# M2-LIVE-02 — Versioned cited-or-abstain prompt development

Status: newly implemented; local tests and real model execution are not yet performed. This is a development experiment on already-exposed fictional questions, NOT an independent held-out study.

## Grounded diagnosis of M2-LIVE-01

The original M2-LIVE-01 four-case Qwen run was independently audited locally (PASS; preserved report SHA256 bd3b35354442062a861c8ed6d4d3b49f58c3ea185a5df7321728c34ef21ed3d8). All three generated answers lacked bracketed source citations:

| Fictional evidence | Observed model draft | Failure |
|---|---|---|
| Adequate | Meridian Robotics developed the Orion Navigation System used by the Aster Rover. | Consistent with the original source but omitted [S1] |
| Irrelevant | Helios Instruments developed the Orion Navigation System used by the Aster Rover. | Unsupported transfer from a source about Solis Probe |
| Contradictory | The Zenith Probe was launched on June 4, 2020. | Chose one of two conflicting dates |
| No source | No model call | Correct software skip |

Every generated draft was rejected by the original citation publication contract, but this is not evidence of semantic correctness or of calibrated refusal.

## New versioned experiment

Implementation: src/raglab/evaluation/m2_live_v2.py and tests/test_m2_live_v2.py. The adapter keeps the original RAGPipeline, ContextBuilder, fixed fictional evidence, Qwen/Qwen2.5-0.5B-Instruct and greedy decoding with a 128-token limit. It changes **only prompt instructions**, now explicitly requiring one factual sentence with an existing [S1]/[S2] citation OR the exact INSUFFICIENT_EVIDENCE marker for irrelevant, missing or contradictory evidence. Few-shot examples use unrelated, original fictional entities distinct from the actual four cases.

Crucially, it **never adds a citation to a generated sentence**. The original pipeline rejects any uncited insufficiency marker and records the original raw candidate. The harness only distinguishes whether the marker was produced: this is a *model-declared*, NOT semantically confirmed, abstention.

Even when a sentence passes the pipeline's citation syntax test, the research harness quarantines it as CITATION_SYNTAX_ACCEPTED_HELD_FOR_SEMANTIC_REVIEW and NEVER sends it to an external user, API or publication endpoint. No semantic verifier is fabricated, and no known-off-domain NLI model is promoted.

## Windows one-command execution

From the repository root, after pulling the branch, run:

    .\scripts\run-m2-live-v2-local.ps1

This runs the full pytest suite first. Then it verifies the SHA256 of the immutable M2-LIVE-01 original JSON and reaudits the old result **before loading Qwen**. If those checks pass, it performs three new local CPU Qwen generations and skips generation on the fourth no-source control. It prints the raw new drafts, syntax verdicts, whether the model declared insufficient evidence and the research-only disposition. No paid APIs, SciFact TEST reuse, or production modifications.

Outputs: gitignored runs/m2-live-v2/M2_LIVE02_<timestamp>.json and matching Markdown, with a reproducible prompt SHA256 and original-baseline hash. A prior successful M2-LIVE-02 JSON prevents any silent repeat or overwrite. Model revision is recorded if available; it was unresolved previously and is not claimed pinned.

## Scientific boundaries

This is a *prompt-development check on known cases*, not an unbiased accuracy estimate or a causal model comparison under fully pinned weights. Correct citation syntax alone cannot prove entailment, answer relevance, or source adequacy. Independently reviewed labels and an untouched set of queries will be needed to evaluate correct refusals, false acceptance and scientific answer faithfulness before closing M2.

# V2 output integrity gate — experimental policy (2026-11-04)

## Motivation

Initial local Qwen V2 generation returned an off-topic answer with **zero citations** despite a normal execution exit. A subsequent offline qrels check found no gold-relevant SciFact source in Hybrid top five for that claim. V2 must not expose a syntactically invalid generated draft as a supported answer. Citation correctness is necessary but **not sufficient** for semantic grounding.

## Implementation

The default `RAGPipeline` behavior is now **fail closed on the citation contract**:

1. If retrieval produces no context, output `abstained_no_context` and skip generation.
2. If an independently supplied evidence gate rejects retrieval, output `abstained_evidence_gate` and skip generation.
3. Otherwise generate a candidate and compute its actual citation report.
4. If any citation label is invalid or not all sentence-like units carry valid citations, return a refusal notice and `output_status=rejected_citation_contract`; set `abstained=true` and preserve the attempted text under `raw_generation` **only inside the local JSON artifact**.
5. The offline audit computes citation failure using the original attempted draft. It must not score the substitution as a passing abstention.
6. If the contract passes, return the generated text as `accepted`, explicitly without semantic correctness certification.

The `citation_report` attached to an output-rejected record describes the **draft**, not the safe replacement sentence. The source labels come from the exact context builder output. No SciFact test labels are provided to the runtime pipeline.

## Local regression exercise (no models)

```powershell
.\scripts\verify-v2-output-gate-local.ps1
```

Covers uncited drafts, nonexistent labels, partial citation coverage, accepted citation syntax, empty context, injected evidence gate and historical-artifact backwards compatibility. Runs local unit tests and, if available, reads an existing saved answer. Does not load Qwen, embeddings or cross-encoder.

## Remaining limitations

- A citation `[S1]` can be syntactically valid while the claim is factually false or not supported by S1.
- Source quality and relevance are not established by this gate.
- The existing `evidence_gate` callback is optional and has **no calibrated semantic policy** yet. Do not invent test-set thresholds or use qrels for inference.
- No real-Qwen rerun of this changed pipeline has occurred yet. A meaningful negative/positive answer dataset, evaluation of factual support, calibration of refusals and cost-aware generation smoke are required before calling V2 dependable.
- Raw rejected drafts are intended for private local research analysis and may contain incorrect content.

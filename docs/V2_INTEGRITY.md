# V2 safety and evidence semantics

The local answer pipeline now returns an explicit `abstained` flag if retrieval yields no context, or if a separately configured `evidence_gate` rejects the retrieved evidence. In this case generation is skipped, generation latency is zero, and the response explains that evidence was insufficient. The gate is injectable, not secretly tuned from test labels.

`CitationReport.all_citations_valid` requires at least one citation and no invalid labels. `citation_contract_passed` additionally requires all sentence-like units to contain valid labels. This is a **syntax/coverage contract only**, not semantic entailment or factual correctness.

`ContextBuilder` enforces the actual character budget and records exactly the evidence passed to the generator. Dense and BM25 indices use document-content fingerprints so edited text with unchanged IDs is reindexed.

## Output contract after generation (safety policy V2.2)

The pipeline now **rejects** a generated answer that fails citation-label validity or 100% sentence citation coverage. The returned user-facing answer is a safe notice, `abstained=true`, `output_status=rejected_citation_contract`, and the original rejected candidate is stored as `raw_generation` in the local JSON result. Citation diagnostics are computed **against the rejected draft**, so the audit records `citation_status=failed` rather than pretending the replacement notice is a successful answer.

Pre-generation abstention remains separate: `abstained_no_context` or `abstained_evidence_gate`. An accepted response has `output_status=accepted`, but this means **only syntactically complete source citations**. It does NOT prove source entailment, factual correctness, or the relevance of the selected passages. Raw rejected drafts can contain hallucinations and are local diagnostic data; do not display them as supported answers.

The pre-generation `evidence_gate` remains an externally supplied, independently calibrated policy; no test-set qrels or uncalibrated confidence thresholds are used in live retrieval. Semantic verification and a labeled no-evidence evaluation set are still needed to certify the system.

## Still required before V2 is complete

1. Run `scripts/run-v2-local.ps1` with the real local Qwen generator and inspect source mappings and raw outputs.
2. Freeze model revision, input corpus and runtime environment for canonical reproduction.
3. Define a human-labeled answer-quality dataset and negative/no-answer questions.
4. Report semantic faithfulness, correctness, abstention rates and total generation time **separately** from citation label integrity.
5. Record regression tests and complete an experimental decision report.

Do not claim the language model is grounded solely because labels match or smoke tests pass.

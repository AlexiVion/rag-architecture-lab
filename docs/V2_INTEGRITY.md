# V2 safety and evidence semantics

The local answer pipeline now returns an explicit `abstained` flag if retrieval yields no context, or if a separately configured `evidence_gate` rejects the retrieved evidence. In this case generation is skipped, generation latency is zero, and the response explains that evidence was insufficient. The gate is injectable, not secretly tuned from test labels.

`CitationReport.all_citations_valid` requires at least one citation and no invalid labels. `citation_contract_passed` additionally requires all sentence-like units to contain valid labels. This is a **syntax/coverage contract only**, not semantic entailment or factual correctness.

`ContextBuilder` enforces the actual character budget and records exactly the evidence passed to the generator. Dense and BM25 indices use document-content fingerprints so edited text with unchanged IDs is reindexed.

## Still required before V2 is complete

1. Run `scripts/run-v2-local.ps1` with the real local Qwen generator and inspect source mappings and raw outputs.
2. Freeze model revision, input corpus and runtime environment for canonical reproduction.
3. Define a human-labeled answer-quality dataset and negative/no-answer questions.
4. Report semantic faithfulness, correctness, abstention rates and total generation time **separately** from citation label integrity.
5. Record regression tests and complete an experimental decision report.

Do not claim the language model is grounded solely because labels match or smoke tests pass.

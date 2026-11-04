# M2 Citation Parser V2 — offline replay of the original Qwen output

**Status:** New opt-in parser, synthetic tests and archived-output replay implemented. The code has **NOT yet passed the operator Windows test suite**. Original RAGPipeline / legacy validator remain unchanged. No new inference is needed.

## What actually happened in M2-LIVE-02

On 2026-11-04 the maintainer ran full pytest PASS and the second versioned Qwen prompt experiment. Three real model calls, four predetermined fictional controls, all generated facts quarantined and all originally rejected by the legacy citation syntax gate.

| Case | Original raw Qwen candidate | Original pipeline |
|---|---|---|
| Adequate source | Meridian Robotics developed the Orion Navigation System used by the Aster Rover. [S1] | rejected_citation_contract |
| Irrelevant source | Helios Instruments developed the Orion Navigation System for the Aster Rover [Solis Probe]. | rejected_citation_contract |
| Contradictory sources | The Zenith Probe launched on July 9, 2021. | rejected_citation_contract |
| No source | Qwen skipped | abstained_no_context |

Predeclared prompt SHA256: `2351f8f969281b7e92c9a827c8f3da79643d75a88c06f6c1c53faf68b25d3246`. Original M2-LIVE-01 baseline report SHA256: `bd3b35354442062a861c8ed6d4d3b49f58c3ea185a5df7321728c34ef21ed3d8`. Raw M2-LIVE-02 report is only on the operator machine: `runs/m2-live-v2/M2_LIVE02_20261104T185026616108Z.json`. The original second report SHA256 was not printed; the replay computes it from bytes, never guesses it.

## Root cause and strict versioned change

Legacy `validate_citations()` splits on punctuation followed by whitespace; the normal form `Fact. [S1]` becomes two segments, one fact without a citation and one citation-only fragment. The first Qwen candidate can therefore be rejected for **syntax despite including a genuine available source label**. This is not evidence that the factual statement was false.

New `raglab.citations.validator_v2.validate_citations_v2()` is *opt-in*, preserves the original CitationReport interface and handles `Fact. [S1]`, `Fact [S1].`, and multiple brackets after punctuation. It attaches a post-punctuation citation token to the **previous** fact and never lets it cover a following unrelated sentence. It fails closed on nonstandard `[Solis Probe]`, unknown `[S99]`, citations at the beginning only, and missing factual sentence coverage. It never modifies or appends text.

**This is syntax, not semantic verification.** The irrelevant Helios claim is unsupported even if a valid source token were attached. The Zenith response silently selected one of two contradictory dates; it remains uncited. Neither problem can be repaired by changing punctuation parsing.

## Offline replay (zero model calls)

After pulling the feature branch on Windows, from the repository root run:

```powershell
.\scripts\replay-m2-citations-local.ps1
```

This first runs the entire Python test suite. Only if PASS, it audits the exact saved M2-LIVE-02 JSON, including model/prompt/baseline/fixture identity, original draft content, source passage mappings, original citation report and quarantine flags. It evaluates a **counterfactual V2 syntax result** without changing the old result, loading Qwen, doing any generation, changing production gates or publishing answers.

Expected development-fixture outcome to be checked by the operator: **one** candidate changes from syntax-rejected to syntax-valid; the other two stay rejected, and no-context remains a no-generation abstention. The expectation is grounded in the already-exposed model drafts, **not** a new held-out quality result.

The local output `runs/m2-parser-replay/M2_LIVE02_SYNTAX_REPLAY.json` is created exclusively. The command refuses an overwrite to protect provenance. Nothing uses SciFact TEST or the HotpotQA evaluation cohorts.

## Release gate

Do not replace the existing pipeline parser automatically on this result. Before promotion, carry out independent parser security tests (misplaced citation attacks, code/markdown-like text, multi-sentence segmentation) and semantic support + answer-task alignment evaluation with predeclared independent labels. Continue to quarantine generated facts. M2 remains **OPEN**.

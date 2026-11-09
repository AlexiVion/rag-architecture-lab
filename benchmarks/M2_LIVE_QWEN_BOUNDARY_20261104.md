# M2-LIVE-01 — Original Qwen runtime smoke and saved-report diagnosis

**2026-11-04.** The maintainer's Windows run completed with all Python tests PASS, local Qwen/Qwen2.5-0.5B-Instruct loaded, four cases attempted and three genuine model calls. Fixture SHA256: 261e4545b00e19d100e4144ca2704f7bac11658db1f200ef2601e58621e7e46c. Model revision: **unresolved**, not pinned.

| Fictional evidence control | Observed V2 public output status |
|---|---|
| Answerable with one explicitly sufficient source | rejected_citation_contract |
| Irrelevant but nonempty source | rejected_citation_contract |
| Conflicting source dates | rejected_citation_contract |
| No source context | abstained_no_context; no generator called |

These statuses establish that the syntactic citation publication gate blocked all three generated drafts, including the supposedly answerable case, and that no-context generation was skipped. They do NOT establish whether the rejected drafts were semantically false or whether refusal for nonempty evidence was properly reasoned.

The terminal transcript does not contain the raw generated strings, so the precise citation failures cannot be named yet. The original experiment JSON remains gitignored at runs/m2-live/M2_LIVE_20261104T182515461187Z.json.

## Inspect the archived Qwen drafts without running Qwen

    .\scripts\audit-m2-live-local.ps1

First runs all pytest tests, then validates original fixture/source text, source IDs/labels, raw rejected drafts, citation statistics, publication status, model call counts and no-context skip against the saved JSON. Prints each existing draft in an escaped bounded format and distinguishes empty output, absent bracketed citations, unknown source labels, and uncited sentences. It creates an additional timestamped diagnostic JSON/Markdown under runs/m2-live; never overwrites the original experiment. **New audit code and tests await Windows validation.**

The auditor uses no LLM, retrieval, scientific label, or test corpus. The semantic, task-alignment and abstention-appropriateness verdicts are explicitly NOT_EVALUATED.

## Research path

Inspect the exact original drafts before editing prompts, output format, model choice or validation semantics. A subsequent versioned experiment may compare a new prompt with the same fictional development fixtures, but cannot claim independent held-out quality on them. The original result remains a baseline. Use a pinned model revision for any later scientific-quality comparison. Full M2 semantic evaluation requires independent labels, correct/false refusal measurement and separate source relevance assessment.

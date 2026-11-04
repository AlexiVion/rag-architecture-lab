# M2-SYNTH-01 — observed controlled-QA run, 2026-11-04

**Status:** first frozen experiment **completed on the maintainer's Windows computer**, full Python regression suite PASS, 24 source-control cases saved. **Outcome: NO-GO for automatic answer publication from source citation syntax alone.** This is a synthetic controlled study and not an independent natural-language semantic correctness benchmark.

## Original console evidence

The operator ran `scripts/run-m2-synth01-local.ps1` at commit `c01f62c`, then reported `M2_SYNTH01_COMPLETE_AND_ARCHIVED`. Frozen case SHA256 `05e778d4b541d397c27a000d4042549d84b90d047a28f1bbf16b289bda6a3826`; model `Qwen/Qwen2.5-0.5B-Instruct`, original M2-LIVE-02 prompt unchanged. 18 Qwen generation calls, six software-only no-context skips, no published external answers. The saved original `runs/m2-synth01/report.json` and 24 row files remain gitignored **on the maintainer's computer**. Their original byte-level SHA256 hashes were **not in the console**, so they are not invented here.

| Frozen control | n | Synthetic rubric success | Experimental citation V2 syntax-pass | Exact model `INSUFFICIENT_EVIDENCE` |
|---|---:|---:|---:|---:|
| `answerable` | 6 | **1** | 1 | 0 |
| `irrelevant` | 6 | **0** | 2 | 0 |
| `conflicting` | 6 | **0** | 2 | 0 |
| `no_context` | 6 | **6** | 0 | 0 (no model called) |
| **Total** | **24** | **7 / 24 = 29.17%** | **5** | **0** |

The **primary proxy** reported by the frozen scorer was `0.2916666666666667`, computed from seven successful synthetic controls, **not a factuality or human-label accuracy score**.

The original pipeline returned `accepted` for **two of six irrelevant-source cases** (case indices 2 and 18) and **one of six contradictory-source cases** (case index 7); all three have an expected abstention under the fictional scenario rubric. The other negative cases were rejected for citation syntax rather than demonstrating reasoned model abstention. Thus **3 / 12 negative-evidence cases** were *syntactically accepted by the original pipeline*, while **0 / 12 returned the predeclared exact model abstention marker**. They were **not externally published** by the research harness. Exact raw texts of these 18 generations were not supplied in the console and **cannot yet be independently classified claim by claim**.

An important architectural distinction: `RAGPipeline` citation status is **syntactic**. It has no validated semantic relevance/contradiction gate. An `accepted` internal result does not mean the answer is supported, and a `rejected_citation_contract` draft can still be semantically wrong or right. Do not promote experimental citation parser V2 to the default while unsupported-source acceptance remains an issue.

## Offline post-run audit (new code, local validation pending)

The added `src/raglab/evaluation/m2_synth01_audit.py` reads the **same** frozen manifest, all 24 case JSONs and `report.json`. It verifies:
- Frozen manifest/24 case IDs, exact question and source text/ID/label order.
- Per-row original model candidate text, citation validator V1/V2 results, quarantine and output status.
- The original citation-report structure, per-row saved hashes and complete aggregate report reconciliation.
- Original model calls, six no-context generator skips and original original/prompt protocol identity.
- Risk counts: internal `accepted` on irrelevant/conflicting cases, model-declared abstentions and syntactic citation validity.

It prints the **18 real Qwen drafts in escaped JSON** and writes additional source-hashed Markdown/JSON diagnostics under `runs/m2-synth01/audits/`, leaving the original files unchanged. All original raw source evidence and generated answers remain gitignored. **No new inference** is performed.

Run exactly once after pulling the branch:

```powershell
& {
    $ErrorActionPreference = "Stop"
    git pull --ff-only origin feat/research-lab-architecture-catalog-20261104
    if ($LASTEXITCODE -ne 0) { throw "PULL_FAILED" }
    & .\scripts\audit-m2-synth01-local.ps1
    if ($LASTEXITCODE -ne 0) { throw "M2_SYNTH01_AUDIT_FAILED" }
}
```

The script runs full pytest first, then performs only an offline audit of the saved data. The new tests have **not yet been verified on the maintainer's Windows machine**.

## Interpretation and next scientific gate

The defensible conclusion is that Qwen2.5-0.5B plus the current prompt **did not reliably abstain** when supplied topically related-but-insufficient evidence or contradictory sources in this six-group original fictional template family. The deterministic no-context skip is working; that is pipeline behavior, not model reasoning. The sample has only six items per category, no expert-annotated natural facts, no verified model weights revision and no independent natural-language entailment judge. As a consequence **the M2 answer-quality acceptance criterion remains OPEN**.

Next, inspect exact preserved generated outputs and their attribution errors. Only then choose an explicit **development-only** semantic adequacy strategy (e.g. structured attribute consistency in this narrow domain, with fail-closed rules), validate it on a different independently labelled cohort, and keep automatic publication disabled until evidence support and abstention error rates are defensible. Do not repeat or tune against these frozen 24 cases and then claim an independent test result.

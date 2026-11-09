# GRF-01 — Frozen Graph-Hybrid vs Hybrid RRF

**Run date:** 2026-11-04  
**Dataset:** HotpotQA DEV distractor, 60 reserved bridge queries; 0 overlap with the 60 GRF-00 examples.  
**Source:** User-reported local terminal output; original per-query JSON is saved locally and is **not** included in this repository.  
**Status:** **INCONCLUSIVE_NO_AUTOMATIC_PROMOTION**, reference Hybrid RRF unchanged.

## Frozen study

- Model: `sentence-transformers/all-MiniLM-L6-v2`, CPU, revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`.
- Policy: same BM25 and Dense results, RRF constant 60, graph quote-backed additive bonus 0.10 / (60 + minimum evidence hops). Exact no-path baseline identity.
- Cohort SHA256: `a560b1cbabe1ce6b4413f0f6f59759cd08e69ce49c5391e05b7c8767f81bd13f`.
- Policy SHA256: `fd28fe01f244fa27f731395bd522a331026eb1cfa6a6acb4bcf592db1fb942bb`.
- Full Python regression suite **PASS**; 60/60 reserved queries completed once.

## Console-reported supporting-document retrieval

| Metric | Hybrid RRF | Graph-Hybrid | Graph − Hybrid |
|---|---:|---:|---:|
| Recall@1 | 0.4417 | 0.4417 | 0.0000 |
| Recall@3 | 0.7417 | 0.6917 | -0.0500 |
| Recall@5 (primary) | 0.8583 | 0.8500 | **-0.0083** |

The saved run reported `INCONCLUSIVE_NO_AUTOMATIC_PROMOTION`. Its exact paired bootstrap interval and graph activation breakdown were subsequently verified by the operator's saved-report audit; see the final audit section below. CPU/memory metrics are in the local saved report but are not transcribed here. A separate no-model post-run audit (`scripts/audit-grf01-local.ps1`) checks the local JSON and exposes the measured values without running a second benchmark.

## Research decision

**Do not promote this graph bonus over Hybrid RRF.** There is no observed improvement in the printed metrics; absence of a statistically clear benefit is not proof of equivalence or of universal graph failure.

Previous GRF-00 graph-first vs BM25 on a *different* 60-query DEV subset was a NO-GO (Recall@5 delta −0.1167 with CI below zero). GRF-01 used a different baseline and cohort. It would be scientifically incorrect to interpret the smaller GRF-01 decline as a measured causal improvement over GRF-00.

Graph traversal in these studies relies on quoted article-title mentions rather than general semantic entity/relation extraction; source retrieval is not the same as grounded-answer correctness. DEV subsets are not an untouched, independent test set.

Local raw reports remain gitignored; HotpotQA original text remains under its CC BY-SA 4.0 terms. **M2 and the broader GraphRAG release gate remain open.**

## Saved-report audit — PASS (2026-11-04)

The operator executed `scripts/audit-grf01-local.ps1` at commit `92ad46b` and received **full pytest PASS**, followed by **`GRF01_SAVED_RUN_AUDIT_PASS`**. The post-run auditor recomputed per-case document recall, seeded paired bootstrap intervals, source ranking integrity, frozen policy/cohort identities, graph activation groups and timing summaries **without re-running any model or query**.

Archived original report SHA256: `f2167bc7220554b1864648c5c5de0b67544bfbdba585a4aeed8f466927fcb2b4`. The original 60-query JSON remains local and gitignored.

| Recall | Hybrid RRF | Graph-Hybrid | Graph−Hybrid | 95% paired bootstrap CI |
|---|---:|---:|---:|---|
| @1 | 0.4417 | 0.4417 | +0.0000 | [−0.0333, +0.0333] |
| @3 | 0.7417 | 0.6917 | **−0.0500** | [−0.1000, −0.0083] |
| @5 **primary** | 0.8583 | 0.8500 | **−0.0083** | [−0.0250, 0.0000] |

| Graph path state | Queries | Mean paired ΔRecall@5 | Wins | Losses | Ties |
|---|---:|---:|---:|---:|---:|
| Activated path | 36 | −0.013889 | 0 | 1 | 35 |
| No activated path | 24 | 0.000000 | 0 | 0 | 24 |
| **All queries** | **60** | **−0.008333** | **0** | **1** | **59** |

**Primary decision unchanged: `INCONCLUSIVE_NO_AUTOMATIC_PROMOTION`.** For Recall@3 the paired interval is wholly negative; for primary Recall@5 it touches zero. This is evidence against promoting the current graph-boost approach, not proof of equivalence or failure of every GraphRAG architecture.

A public **summary-only** copy is recorded in `apps/explorer/data/grf01-summary.public.json`, with the source report's SHA256 and explicit operator-audit provenance. This is reconstructed from the operator's successful audit log; the full row-level JSON was checked on the user's machine, **not independently uploaded into GitHub**. The local exported `grf01-summary.local.json` remains available for direct source-based browser verification. Neither summary republishes HotpotQA source passages.

See [GRF-00 audited NO-GO](GRF00_HOTPOTQA_DEV_60_NO_GO_20261104.md). The prior GRF-00 cohort and BM25 baseline differ, so cross-experiment improvement claims would be invalid.

# GRF00-HOTPOTQA-DEV-01 — graph-first retrieval: NO-GO

**Date:** 2026-11-04  
**Dataset:** HotpotQA DEV distractor, 60 deterministic bridge queries (seed 17).  
**Comparison:** BM25 vs exact-title-mention graph (max 2 hops) prioritized ahead of BM25 with fallback.  
**State:** experiment completed locally; **NO-GO** for the measured graph-first policy in this limited sample.

## Observed results

| Recall | BM25 | Graph+BM25 | Difference | 95% paired bootstrap CI |
|---|---:|---:|---:|---|
| @1 | 0.4333 | 0.3500 | -0.0833 | [-0.1500, -0.0167] |
| @3 | 0.6833 | 0.5917 | -0.0917 | [-0.1750, -0.0083] |
| @5 | 0.8250 | 0.7083 | **-0.1167** | [-0.1917, -0.0583] |

The user ran the full `python -m pytest -q` suite successfully, then the HotpotQA experiment produced 60 question results and wrote:
- `runs/graph-hotpotqa/GRF00_HOTPOTQA_20261104T163545630360Z.json` (local only).
- `runs/graph-hotpotqa/GRF00_HOTPOTQA_20261104T163545630360Z.md` (local only).

Graph seed nodes were identified for 43/60 questions; title-mention graph edges were constructed for 52/60 questions. These indicate graph activation, **not** retrieved relevance. All printed paired CIs for graph minus BM25 Recall were below zero. These values were originally transcribed from the benchmark log. On **2026-11-04**, the operator then ran the independent post-run JSON auditor; its tests passed, metrics/seeded bootstrap confidence intervals/source identifiers/no-path fallbacks verified and it reported the identical NO-GO decision. The private row-level JSON was audited locally; it has **not been uploaded or independently copied into this repository**.

## Decision

Keep the baseline Hybrid RRF unchanged; **do not promote this graph-first policy** as the default. This is not a result about full GraphRAG (which can use extraction, community/global context and learned ranking) or generated answer quality. The lexical article-title mention schema is a narrow first baseline.

## Methodological boundaries

- Per-question provided distractor contexts, not corpus-wide retrieval.
- Deterministic DEV subset, not independently unseen TEST; previous evaluation must not become a tuning set.
- Two-hop traversal plus BM25 fallback but **no evidence-adaptive hybrid ranker**.
- Correctness of retrieved passages measured by supporting-document recall only.
- **Timing caveat:** the recorded graph index timer excludes title-link graph construction performed before the timer.
- HotpotQA data and source text are CC BY-SA 4.0; do not present raw dataset material as MIT sample content.
- Negative findings are not a request for parameter sweeps on the same 60 examples.

## Follow-up

`scripts/audit-grf00-hotpotqa-local.ps1` is the no-prompt post-run audit, which checks original case records, subset hashes, summary metrics, seeded confidence intervals, fallbacks and timing. It writes a gitignored aggregate-only file consumed by `apps/explorer` and a Markdown diagnosis without changing the old JSON. It does not rerun retrieval.

After examining the diagnostic, future GraphRAG versions require a new predeclared hypothesis, a separate development set for selecting any changes, and independent evaluation against a fair Hybrid RRF baseline. Full M2 answer-quality evaluation is independent and remains open.

## Post-run verification — completed locally

The operator executed `scripts/audit-grf00-hotpotqa-local.ps1` against the original archived 60-query JSON. Full pytest **PASS**; the auditor returned:

```text
GRF00_AUDIT_STATUS=NO_GO_GRAPH_FIRST_ON_THIS_DEV_SUBSET
GRF00_REPORT_SHA256=962dc3b12d0086857ad94198cf2b1fff7a49ca5f7df069e9575a6daaf778f016
GRAPH_PATH_PRESENT={'cases': 40, 'mean_delta_recall_at_5': -0.175,
                    'wins': 0, 'losses': 11, 'ties': 29}
GRAPH_PATH_ABSENT={'cases': 20, 'mean_delta_recall_at_5': 0.0,
                   'wins': 0, 'losses': 0, 'ties': 20}
GRF00_POSTRUN_AUDIT_COMPLETE
```

**Diagnostic decomposition** (observed, not a causal proof):

| Group | Queries | Mean Graph−BM25 Recall@5 | Wins | Losses | Ties |
|---|---:|---:|---:|---:|---:|
| At least one traversed graph path | 40 | **−0.1750** | 0 | 11 | 29 |
| No traversed graph path | 20 | **0.0000** | 0 | 0 | 20 |
| Weighted full-sample difference | 60 | **−0.1167** | 0 | 11 | 49 |

Reconciliation: `(40 × −0.175 + 20 × 0) / 60 = −0.1166667`, matching the overall paired Recall@5 delta and the absence of positive cases. This is a strong empirical sign that the **graph-priority policy** has a harmful association with Recall@5 here. The study does not isolate edge construction versus traversal versus prioritization as separate causal mechanisms.

For comparison, the initial benchmark recorded **43/60 queries with seeds** and **52/60 with at least one constructed graph edge**. Only **40/60** had a traversed path. These are distinct notions and must not be conflated.

Generated artifacts remained local:
- Original verified report: `runs/graph-hotpotqa/GRF00_HOTPOTQA_20261104T163545630360Z.json`.
- Independent diagnostic: `runs/graph-hotpotqa/GRF00_AUDITED_20261104T1653110040593Z.md`.
- Viewer data (ignored by Git): `apps/explorer/data/hotpotqa-summary.local.json`.

The published report records only aggregate statistics and the source report hash; no original HotpotQA questions/passages were copied to GitHub. The **HotpotQA DEV 60 query sample is now exposed**. It is not suitable for parameter selection followed by claims of independent validation on those same cases.

Next pre-registered experimental design: [GRF-01 Hybrid comparison protocol](../docs/GRF_01_HYBRID_RRF_PROTOCOL.md). No default architecture change.

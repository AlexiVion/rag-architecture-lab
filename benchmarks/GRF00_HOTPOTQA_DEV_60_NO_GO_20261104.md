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

Graph seed nodes were identified for 43/60 questions; title-mention graph edges were constructed for 52/60 questions. These indicate graph activation, **not** retrieved relevance. All printed paired CIs for graph minus BM25 Recall were below zero. These values are **transcribed from the user-supplied execution log** and do not imply a separate inspection of the unuploaded row-level JSON.

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

# GRF00-HOTPOTQA-DEV-01 — Source-quoted graph retrieval vs BM25

**Status:** Local run completed and observed results recorded (2026-11-04); graph-first **NO-GO on this DEV subset**. Raw per-query JSON is local only; the post-run diagnostic has now **passed locally**, verifying the archived metrics before exporting a gitignored aggregate to the viewer.

The repo's first deterministic GRF-00 seed graph is real code but uses fictional curated texts. To reach a controlled **real-document** comparison, this study uses the original HotpotQA dev distractor setting: candidate article titles and passages per question, plus separate supporting-fact labels for retrieval evaluation. The official HotpotQA code and dataset describe the source schema and CC BY-SA 4.0 license: https://github.com/hotpotqa/hotpot/blob/master/README.md and https://hotpotqa.github.io/.

## Source integrity and scope

- DEV distractor JSON via a Hugging Face mirror of the **original unchanged** ~46 MB file, pinned to the exact SHA256 recorded by original HF dataset metadata: \`4e9ecb5c8d3b719f624d66b60f8d56bf227f03914f5f0753d6fa1b359d7104ea\`.
- A deterministic SHA256(seed|query_id) subset of 60 **bridge** questions with at least two gold supporting titles actually present among the supplied contexts.
- **The selection uses supporting-fact labels only to define eligibility; retrieval and graph construction never inspect them.** Experiment hyperparameters must be frozen before running; do not tune using these DEV examples.
- Data stays under gitignored \`.cache/hotpotqa\`; results under gitignored \`runs/graph-hotpotqa\`. The original dataset's CC BY-SA 4.0 license is distinct from the MIT license of this repository's source code.
- This is **per-question distractor-context ranking**, not full Wikipedia retrieval, open-domain multi-hop QA or answer correctness.

## Candidate and controls

**Baseline:** Okapi BM25 indexing the supplied paragraphs (title + text) for each question.

**Candidate:** deterministic, source-quoted directed title-mention graph over the *same* paragraphs. If article A mentions another candidate article title B verbatim in an original sentence, create an A-to-B \`mentions\` edge with that exact source quote. A question that explicitly mentions a title seeds traversal; retrieve via paths up to two hops, then fall back to BM25. Every returned document is an original candidate paragraph ID; no fabricated graph facts or language-model extraction. Graph index time is counted separately.

**Metrics:** supporting-document Recall@1/3/5, paired deltas with deterministic 95% query bootstrap intervals, win/loss/tie counts, and separate mean indexing/query latency. Both systems see the same query and candidate context; no answer generation is executed. Report negative outcomes without promotion.

## Local command (Windows)

From the repository root, in **a separate PowerShell session** if the viewer's HTTP server is still running:

\`\`\`powershell
.\scripts\run-hotpotqa-graph-benchmark-local.ps1
\`\`\`

The command runs all tests, downloads the official unchanged dataset once (about 46 MB), checks SHA256, evaluates 60 bridge queries with no paid models, and creates time-stamped JSON/Markdown reports. On first-run network failures, it fails visibly rather than fabricating results. No questions are asked.

## Interpretation before any GO

- Article-title mention edges are only a weak lexical proxy for graph relations, not a fully extracted knowledge graph.
- Gold supporting-fact titles are available only to evaluate source recovery, not to validate generated answers.
- The study is a deterministic subset of DEV, not HotpotQA TEST. It may expose limitations, but is not a new final holdout after any algorithm parameter changes.
- Latency and indexing are simple sequential desktop measures, not production percentiles or GPU claims.
- These results cannot be compared directly to SciFact retrieval because datasets, candidates and relevance definitions differ.
- The **final GRF-00 release gate** still requires a comparison against a matched Hybrid RRF baseline and an explicit multi-hop answer-quality study, with model revision, RAM/cost and licensing checks.


## Recorded 60-question local results (2026-11-04)

The operator ran the full pytest suite successfully; the deterministic HotpotQA DEV benchmark finished with no paid models or generated answers.

| Retrieval recall | BM25 | Graph+BM25 | Delta | 95% paired bootstrap CI |
|---|---:|---:|---:|---|
| Recall@1 | 0.4333 | 0.3500 | −0.0833 | [−0.1500, −0.0167] |
| Recall@3 | 0.6833 | 0.5917 | −0.0917 | [−0.1750, −0.0083] |
| Recall@5 | 0.8250 | 0.7083 | **−0.1167** | [−0.1917, −0.0583] |

- Graph seed entities found: **43 of 60 questions**; graph relations constructed: **52 of 60**.
- Decision: **NO-GO for prioritizing lexical title-link graph results ahead of BM25 in this observed setting**. Do not tune hyperparameters on the same fixed DEV evaluation cases. Hybrid RRF default remains unchanged.
- This is **not** end-to-end GraphRAG answer-quality performance, and cannot determine whether a different graph architecture could help.
- Known timing caveat: the original graph index timer excludes the preceding title-link relationship construction step. Do not call it complete graph build time.
- Operator output: `runs/graph-hotpotqa/GRF00_HOTPOTQA_20261104T163545630360Z.json` and matching Markdown, stored locally. The 60-query result was subsequently independently reaudited locally against the archived JSON: full tests PASS, source report SHA256 `962dc3b12d0086857ad94198cf2b1fff7a49ca5f7df069e9575a6daaf778f016`. No raw report uploaded to GitHub.

To audit saved per-query data without rerunning or tuning the retriever:

```powershell
.\scripts\audit-grf00-hotpotqa-local.ps1
```

This checks query IDs, provenance, all reported recall/CI values against the saved rows, group counts, timings and no-graph fallback; it then writes a local diagnostic report and a **gitignored** safe aggregate for the web observatory. No HotpotQA questions or source passages are exported to the web.

## Verified failure localization

The independent post-run auditor found **40/60 cases with a traversed graph path**, where the mean Graph−BM25 Recall@5 was **−0.1750** (0 wins, 11 losses, 29 ties). The other **20/60 had no activated path**, where the graph fallback exactly matched BM25 (0 wins, 0 losses, 20 ties).

This reconciles to the full-sample difference: `(40×−0.175 + 20×0)/60 = −0.1167`.

The evidence supports a **NO-GO on graph-first source prioritization**, but does not isolate whether particular extracted relations, entity seeding or ranking cause each loss. Do not tune using these now-inspected DEV examples. For next comparison see `docs/GRF_01_HYBRID_RRF_PROTOCOL.md`.


## Public observatory summary

The GRF-00 local audit has PASS status and original report SHA256 `962dc3b12d0086857ad94198cf2b1fff7a49ca5f7df069e9575a6daaf778f016`. The aggregate-only results and CIs from that successful operator audit log are recorded in `apps/explorer/data/grf00-summary.public.json`. The viewer loads the locally verified `hotpotqa-summary.local.json` when it exists; otherwise it displays the public report **with explicit operator-log provenance**. No per-query HotpotQA articles or QA texts are in this public file.

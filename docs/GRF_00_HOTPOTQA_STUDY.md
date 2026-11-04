# GRF00-HOTPOTQA-DEV-01 — Source-quoted graph retrieval vs BM25

**Status:** Implementation committed; real run and empirical results require local validation. Do not publish a GO/NO-GO until the run is inspected.

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

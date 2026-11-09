# RAG Architecture Lab — portfolio release v0.1.0

**Release profile:** independently inspectable engineering/retrieval research demonstration. **Not** complete WOW v1.0, not a production chatbot, and not a claim of scientifically validated generated answers.

**Tracking:** [REL-PORTFOLIO-01 #13](https://github.com/AlexiVion/rag-architecture-lab/issues/13) · [Research program #9](https://github.com/AlexiVion/rag-architecture-lab/issues/9) (remains open) · [Project control](PROJECT_CONTROL.md) · [Execution log](EXECUTION_LOG.md).

## What a visitor can inspect

1. First-principles local retrieval architecture: BM25, sentence embeddings, Hybrid Reciprocal Rank Fusion, cross-encoder reranking.
2. Canonical **BEIR SciFact retrieval study** (5,183 documents / 300 questions): BM25 MRR@10 **0.6328**, dense **0.6047**, Hybrid RRF **0.6484**. These evaluate **retrieval relevance**, not generated-answer correctness.
3. Local CPU reranking ablation: Hybrid RRF around **34.53ms mean** vs 50-candidate reranked **3706.43ms mean**, with MRR@10 changing **0.6484 -> 0.6615** under the documented V1 measurement conditions. The 10-candidate reranking mode is optional; exact conditions in [V1.1 results](../benchmarks/V1_1_RESULTS.md).
4. A **two-hop source provenance graph** over **three deliberately fictional documents**, showing original quoted relations. It is an auditable visualization *fixture*, not graph extraction from arbitrary input.
5. Two paired **HotpotQA DEV** graph retrieval studies: GRF-00 graph-first Recall@5 **0.7083** vs BM25 **0.8250** (**NO-GO** in this cohort); GRF-01 Graph-Hybrid Recall@5 **0.8500** vs Hybrid RRF **0.8583** (**INCONCLUSIVE**). These were different DEV cohorts, not one combined randomized trial. No demonstrated generated multi-hop factual accuracy.
6. Read-only **React/TypeScript/Vite seven-section observatory** with validated static JSON, source quote drill-down, browser navigation/mobile QA and no public inference endpoint.

## Explicit boundaries: what the release does **not** claim

- No proof that a generated answer is semantically supported because it contains a valid citation marker.
- The current M2 evidence-sufficiency and abstention study **does not support auto-publication**. It remains **NO-GO**. Earlier synthetic 7/24 proxy and 40-case guard failure examples are diagnostic, not general accuracy estimates.
- The proposed ten-model matrix has **no completed comparative measurements**. Do not present ten model cards as ten tested models.
- GRF-00/01 **do not demonstrate general GraphRAG superiority**. Both use exposed DEV material and specific policies; reproducible decisions must retain their limitations.
- No publicly hosted Qwen/LLM, private corpus uploads, backend/API, production service, GPU requirements, agentic system or newly demonstrated tiny-model innovation.
- Research expansions about ultratiny models / embodied intelligence are **separate future work**, never release acceptance criteria.

## Minimum deployment/validation checklist

- [ ] Reviewed PR #2 and scoped portfolio changes merged on main; no credential/license leaks and no silent experiment rewrites.
- [ ] Python v3.11+ deterministic test suite, `python -m raglab.release_readiness`, CLI and wheel build PASS for the final HEAD.
- [ ] Node 22 `npm install --prefix apps/observatory`, `npm run --prefix apps/observatory check`, `npm run --prefix apps/observatory build`, Playwright Chromium E2E PASS for final HEAD. Dependency lockfile should be checked into source and changed to `npm ci` where feasible; until then, state the reproducibility limitation rather than hiding it.
- [ ] Real desktop/mobile screenshots reviewed and artifact-linked to the release commit.
- [ ] GitHub Pages **Source=GitHub Actions**, deployment workflow SUCCESS and publicly reachable route plus data assets tested. Do not claim live demo before direct verification.
- [ ] External clean clone test observed and referenced. CI smoke is a documented substitute only for the tasks it actually exercises.
- [ ] Versioned release notes and GitHub release tag `v0.1.0` **after** public observatory verification; current source `pyproject.toml` package version may remain `0.1.0`, but match release announcements.
- [ ] LinkedIn post and short walkthrough published/linked without unsupported claims.
- [ ] Record commit SHA, CI run URLs, proof/limitations in append-only [EXECUTION_LOG.md](EXECUTION_LOG.md); report incomplete checks as OPEN.

## Reproduce without downloading models

```bash
git clone https://github.com/AlexiVion/rag-architecture-lab.git
cd rag-architecture-lab
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]" build wheel
python -m pytest -q
python -m raglab.release_readiness
raglab --help
cd apps/observatory
npm install
npm run check
npm run build
npm run e2e
```

This smoke validates **engineering and curated public data integrity**. Real benchmark reproduction needs optional dataset/model downloads and canonical local CPU instructions from [RELEASE_INSTALLATION.md](RELEASE_INSTALLATION.md).

For limitations and full scientific roadmap see [ROADMAP.md](ROADMAP.md), [EXPERIMENT_PROTOCOL.md](EXPERIMENT_PROTOCOL.md), and [RELEASE_WOW_BLUEPRINT.md](RELEASE_WOW_BLUEPRINT.md).

## Publication copy / honest disclosure

**RAG Architecture Lab v0.1.0 — an open-source, CPU-first retrieval research observatory.** Includes measured lexical/dense/hybrid/reranking trade-offs, honest negative graph retrieval results, source provenance and a static seven-view visual explorer. It does not assert validated factual generation, model-size breakthroughs or a finished WOW v1.0 scientific program.

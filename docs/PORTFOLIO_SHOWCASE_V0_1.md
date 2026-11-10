# RAG Architecture Lab — Portfolio Preview 0.1

**Independent open-source research | Python • Information Retrieval • Tiny LMs • CPU benchmarking • TypeScript**

**Status:** Code and evidence are publicly inspectable. This is a **portfolio preview**, not a GitHub Release, production QA system or finished scientific paper. No public live demo is claimed here until independently verified.

## The technical challenge

How small and computationally efficient can an evidence-grounded retrieval/QA architecture be before factual reliability breaks? Instead of packaging a generic RAG framework, this lab implements core retrieval methods and evaluates them with source-level traces, reproducible benchmarks, CPU-only model studies and explicit negative results.

## What is already demonstrated

| Engineering capability | Reproducible evidence | Correct interpretation |
| --- | --- | --- |
| Retrieval implementation | [SciFact 5,183 documents / 300 queries](../README.md); [release scope](PORTFOLIO_RELEASE.md) | Hybrid RRF MRR@10 **0.6484** vs BM25 **0.6328** and dense **0.6047** in the recorded study; **retrieval ranking, not answer correctness** |
| Quality/latency trade-off | [Canonical benchmark record](../benchmarks/V1_1_RESULTS.md) | 50-candidate reranker MRR@10 **0.6615** vs hybrid **0.6484**; mean measured local latency **3706.43 ms vs 34.53 ms** under reported conditions |
| Evidence and abstention engineering | [MICRO-RAG v0.2 specification](MICRO_RAG_V02_SPEC.md) | Structured-source decisions: ANSWER / CONFLICT / INSUFFICIENT / REVIEW; no general natural-language QA reliability claim |
| Tiny-model real CPU evaluation | [ConfRAG audited report](PAPER_01_CONFRAG_DEV_RESULTS.md) | 16 source-question groups, 240 **correlated** answer pairs: lexical 68.33%, DeBERTa 71M 51.67%, MiniLM2 82M 50.00% at **author viewpoint-cluster detection**, not true contradiction or factual RAG |
| Software verification | [Exact-head GitHub Actions #42861277825](https://github.com/AlexiVion/rag-architecture-lab/actions/runs/42861277825), [two real model jobs #42859891303](https://github.com/AlexiVion/rag-architecture-lab/actions/runs/42859891303) | Python tests, typed observatory browser checks, pinned weight/dataset hashes and archived experiment outputs |
| Visualization | [React/TypeScript observatory](../apps/observatory) | Locally runnable static research viewer; **no verified hosted demo or inference service** |

## 90-second technical tour

1. Open the repository code under `src/raglab` and the [public release scope](PORTFOLIO_RELEASE.md). Explain why the project measures retrieval separately from generation.
2. Inspect the SciFact BM25 vs hybrid experiment and the reranking result. Highlight the enormous latency cost of a modest MRR increase.
3. Explore the local static [React + TypeScript observatory](../apps/observatory): architectures, measured study summaries, source provenance and limitations.
4. Read the [real CPU ConfRAG study](PAPER_01_CONFRAG_DEV_RESULTS.md). Show both model failures and controls instead of cherry-picking an apparent win.
5. End with the [working scientific manuscript](../papers/micro-cpu-frontier/WORKING_MANUSCRIPT.md): this is active research, **not** an accepted paper.

## Run the public software verification

Python 3.11+:

```sh
git clone https://github.com/AlexiVion/rag-architecture-lab.git
cd rag-architecture-lab
python -m pip install -e ".[dev]"
python -m pytest -q
python -m raglab.release_readiness
```

Local static observatory (Node.js 22):

```sh
cd apps/observatory
npm install
npm run check
npm run build
npm run dev
```

These commands validate **code, fixtures and presentation**. Reproducing all model benchmarks requires optional larger public datasets and pinned model weights; consult the experiment protocols. A clean-clone test, public Pages URL and formal GitHub Release are separate publication gates.

## Open research questions

The next milestone is a small **end-to-end** reader + verifier on genuinely unstructured documents, with no privileged dataset-extracted answers. Compare supported-answer correctness, selective coverage, source contradiction and CPU latency under a combined <=135M active neural parameter budget. External blinded dual-human review remains required before scientific reliability claims.

- [Full experiment protocol](PAPER_01_MICRO_CPU_FRONTIER_PROTOCOL.md)
- [Manuscript in progress](../papers/micro-cpu-frontier/WORKING_MANUSCRIPT.md)
- [Open research issue #39](https://github.com/AlexiVion/rag-architecture-lab/issues/39)
- [Portfolio release checklist](PORTFOLIO_RELEASE.md)

**For LinkedIn:** describe this as a **public open-source research and engineering project with preliminary experimental evidence**, not a finished product or original scientific breakthrough.

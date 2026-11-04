# GRF-01 — Pre-registered matched Hybrid RRF vs graph-assisted retrieval

**Status:** frozen *design specification only*, not implemented or run.  
**Pre-registration date:** 2026-11-04.  
**Motivation:** GRF00-HOTPOTQA-DEV-01 yielded a graph-first Recall@5 delta of −0.1167 vs BM25 on 60 already inspected DEV bridge queries (source report SHA256 `962dc3b12d0086857ad94198cf2b1fff7a49ca5f7df069e9575a6daaf778f016`). We must not tune graph weights on those 60 queries and then claim an independent evaluation on them.

## Scientific question

Can evidence-provenance graph information **complement** a matched, strong BM25+Dense Hybrid RRF retriever without displacing relevant documents at K=1/3/5, especially on multi-hop queries?

This is not the same model as GRF-00; graph-first was rejected. We have **no observed answer** yet.

## Non-negotiable comparison contract

1. Same candidate paragraphs and same question per case, same dataset, split, inclusion criteria and fixed seed.
2. Three ranked baselines: BM25; Dense with a fully pinned publicly licensed embedding model; **Hybrid RRF** with a fixed RRF constant and no supervised fitting.
3. Candidate architecture: **Hybrid RRF with an optional graph feature**, not unconditional graph-first replacement. A graph edge is included only if its source quote appears literally in a candidate paragraph and its endpoints refer to candidates. Every returned document ID must map back to an original candidate.
4. Both Hybrid and Graph-Hybrid share the exact **same** dense and sparse candidate lists, source IDs and all top-K latency instrumentation. Graph indexing, relation construction, embedding/cache warmup and query time are reported separately.
5. Gold supporting-fact labels must be inaccessible to retrieval and graph construction. No answer text may be used as a feature or graph label. Gold may be used only in the evaluator and in **predeclared** eligibility checking.
6. No artificial fallback claiming correctness: if a graph cannot add a justified retrieval path, return Hybrid ranking unchanged and record the absence of graph effect.
7. Graph boost/activation policy, top-K, RRF constant and model revision must be **declared before looking at outcomes**. No after-the-fact param sweep over evaluation results.

## Split and leakage prevention

- Original 60 HotpotQA DEV query IDs are available only in the **local** `GRF00_HOTPOTQA_20261104T163545630360Z.json`. Their SHA256 concatenated-query-id fingerprint is embedded there; the exact IDs must never be guessed from the aggregate.
- For new methodology development, prefer a *disjoint source TRAIN split*, with its own original expert labels, where metadata licensing is checked. If unavailable, refuse to claim an independent model-selection set.
- Create a **sealed evaluation cohort** from a separate eligibility-filtered DEV partition before running or tuning a new candidate. Explicitly exclude every GRF-00 query ID, and store cohort IDs+SHA256 and fixed seed before seeing performance. A disjoint DEV cohort is an improvement but **not equivalent to a genuinely untouched dataset** after this project's earlier DEV inspections; limitations must be stated.
- Do not use HotpotQA hidden TEST labels or SciFact TEST qrels for tuning.
- Only a predeclared single evaluation pass on the sealed cohort can be reported as independent relative to the prior 60 cases; if any version of the model/selection policy is chosen based on cohort scores, the cohort is no longer an independent evaluation set.

## Measures and acceptance

Primary: per-query supporting-document Recall@5 difference Graph-Hybrid minus identical Hybrid RRF, with a query-resampled 95% paired bootstrap interval and win/loss/tie count. Secondary: Recall@1/@3, supporting title exact-hit, both-evidence-docs-in-top-K, activation rate, graph path provenance, mean/p95 query latency, embedding/index and graph build cost, peak memory and failure mode breakdown. Distinguish corpus-wide retrieval from per-query distractor ranking.

**Do not promote graph-assisted retrieval** unless the primary difference is positive with a 95% paired CI above zero **and** secondary latency/memory plus provenance thresholds pass a predeclared acceptance gate. A negative or inconclusive outcome is an acceptable published scientific result, not an engineering failure.

Data cannot prove generated answer correctness here. Multi-hop answer quality is a *separate* M2 experiment with its own verified answer labels and citation/abstention protocol.

## Engineering work packages

- [ ] GRF-01A: normalize dataset loaders and split manifest, validate source licenses and archive checksums, enforce no-overlap with original run's stored query IDs.
- [ ] GRF-01B: implement dense+BM25 Hybrid RRF under the same candidate boundary; pin model ID, revision, CPU threads and preprocessing.
- [ ] GRF-01C: implement source-grounded graph feature with stable trace schema and a deterministic no-path identity fallback to Hybrid.
- [ ] GRF-01D: pairwise metrics, bootstrap and runtime/resource tracing, fail-closed tests against test split use, source-ID corruption and tuning.
- [ ] GRF-01E: run exactly once on sealed cohort, analyze failure modes, publish positive **or negative** result with full provenance.
- [ ] GRF-01F: only then connect reviewed, license-cleared aggregate to the observatory.

**Current outcome:** no GRF-01 measurements, no policy promoted. Current GRF-00 NO-GO remains unchanged.

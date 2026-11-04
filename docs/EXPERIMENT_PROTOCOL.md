# Reproducible benchmark protocol (v1)

## 1. Define before running

For every experiment record: ID, falsifiable hypothesis, input corpus, split, eligible query IDs, qrels or reference answers, control pipeline, candidate pipeline, metrics, fixed and changed variables, model revision, seed, resource limits and decision threshold. If the input has no labels for a proposed metric, omit that metric instead of inventing values.

## 2. Establish matched conditions

- Identical dataset snapshot, query selection, relevance rules, query order and K.
- Same machine / OS / Python, embedding and reranker revisions for comparisons.
- Warm models consistently; report cold start separately from warm query times.
- Do not count indexing/download time as query latency. Track indexing, retrieval, reranking and generation separately where applicable.
- Record measured p50, p95 and mean latency, not only an average.
- Avoid using test labels to tune routing or thresholds; keep a held-out final evaluation.
- Report per-query changes and failure examples, not just aggregated improvements.
- On stochastic generation, record model revision, prompt, decoding, seed and repetitions; do not imply deterministic reproducibility without checking it.

## 3. Retrieval evaluation

Use Recall@K, MRR@K and nDCG@K with qrels. Report absolute delta, relative delta when meaningful, and paired-query confidence/uncertainty where feasible. Evaluate at least one distinct dataset before claiming transferability beyond SciFact.

## 4. Generation evaluation

Track (a) evidence retrieval, (b) answer correctness against available references, (c) citation-label integrity, (d) semantic support / faithfulness assessed independently, (e) valid abstention and false abstention, (f) end-to-end latency and resource footprint. A citation matching `[S1]` is **not** evidence the sentence is true. If a support evaluator is unavailable, explicitly say `not evaluated`.

## 5. Failure taxonomy

Classify cases as: missing relevant document; useful document ranked too low; context truncated; generation contradicts evidence; unsupported citation; no/incorrect abstention; excessive latency; dataset or annotation uncertainty.

## 6. Artifact manifest (target schema)

```json
{
  "schema_version": 1,
  "experiment_id": "RET-03",
  "git_sha": "required-for-canonical-run",
  "dataset": {"id": "beir/scifact/test", "split": "test", "fingerprint": "required"},
  "configuration": {"seed": 42, "top_k": [5, 10], "candidate": {}, "baseline": {}},
  "models": [{"id": "model-name", "revision": "pinned-revision"}],
  "environment": {"python": "3.11.9", "platform": "windows", "cpu": "model"},
  "measurements": {"metrics": {}, "latency_ms": {}, "query_count": 0},
  "artifacts": {"per_query_file": "local-file.json"},
  "publication_status": "exploratory"
}
```

The schema above is a target for future experiment runners, **not** a claim that current V0/V1 JSON already uses it. Large per-query artifacts may remain excluded from Git; publish small reproducibility instructions and hashes instead.

## 7. Go / No-Go / Inconclusive

`GO` requires a meaningful improvement in a predeclared target without breaching latency/resource bounds. `NO-GO` means it fails the defined trade-off for the tested setting; it is not a universal statement. `INCONCLUSIVE` applies when sample coverage, missing labels, or measurement variance prevents a credible decision.

## 8. Local execution policy

Canonical CPU comparisons run on the designated local Windows host. Avoid spending cloud CI credits or launching parallel model-backed jobs. Unit tests may be run cheaply wherever available. Results must be rerun when code, corpus or model revisions change.

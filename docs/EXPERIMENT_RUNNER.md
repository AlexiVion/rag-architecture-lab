# Local architecture experiment runner

This is an **exploratory** comparison facility, not an automatically certified research result.

## Run

On the designated Windows machine, set up the environment and run:

```powershell
.\scripts\setup-local.ps1
.\scripts\run-research-local.ps1
```

Or specify a JSON spec:

```powershell
raglab experiment --spec experiments/ret-04-parent-child-smoke.json
```

The example compares BM25 with a parent-child BM25 adapter on 10 nano-SciFact questions. It intentionally avoids a paid API or model download for embeddings. Results are saved under `benchmarks/results` and labeled `exploratory`. Do **not** report its metrics as an architectural winner before applying the [benchmark protocol](EXPERIMENT_PROTOCOL.md).

## JSON specification

Required: `experiment_id`, `architecture`. Optional: `dataset`, `limit_queries`, `base` (`bm25`, `dense`, `hybrid`), `k` (list of positive integers), `embedding_model`, `seed`, `params`.

Architecture-specific `params`:

| Architecture | Required | Optional |
|---|---|---|
| multi-query | `query_variants`: question text → list of reformulations | `max_queries`, `candidate_k` |
| parent-child | none | `chunk_chars`, `overlap_chars`, `candidate_k` |
| contextual | `prefixes`: document ID → context text | none |
| hyde | `hypothetical_passages`: question text → hypothetical text | none |
| corrective | `min_primary_score` threshold | `fallback_base` |
| adaptive | `routes`: route name → base type, `default_route` | `route_map`: question text → route |

In real studies, construct transformations or thresholds on training/development data, **not using the test qrels**. A multi-query/HyDE model's generation time must be measured separately when evaluating end-to-end cost. A route's label is chosen only from the predeclared mapping; no LLM invocation is hidden.

Current limitations: BM25-only smoke is not a hybrid comparison; benchmark runner does not calibrate score thresholds, estimate uncertainty, apply model warmups, or evaluate semantic faithfulness. These are explicit later gates.

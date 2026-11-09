# GRF-01B/C — Frozen Graph-Hybrid policy and model-free preflight

**Status:** New implementation; full local operator tests pending. **No reserved GRF-01 DEV queries have been scored.** GRF-00 NO-GO stays unchanged.

## Frozen algorithm

The baseline uses the existing Hybrid RRF fusion semantics. BM25 and Dense produce rankings over the same complete candidate documents, and the canonical RRF constant is fixed to 60.

The graph variant builds a deterministic source-quoted title-mention graph and traces up to two hops. It adds a small, fixed bonus to an original document only when a graph path includes a verbatim source-quoted relation from that document:

`GraphHybridScore(doc) = HybridRRFScore(doc) + 0.10 / (60 + shortest_evidence_path_hops(doc))`

When no paths activate, the **entire ranking and scores are identical to Hybrid RRF**. Source quotes, candidate IDs and rank coverage are validated. Gold labels, answers and query qrels never enter the ranker. The graph path alone is not semantic support verification.

This intentionally differs from GRF-00's unconditional graph-first ranking. A small graph bonus may still harm accuracy. **No improvement is claimed before evaluation.**

## Frozen reproducibility contract

- Embedding model: `sentence-transformers/all-MiniLM-L6-v2`, pinned Hugging Face SHA `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, Apache-2.0.
- Hardware: CPU, batch size 8; model inference is not required for this preflight.
- Same per-question distractor candidates, up to 10 documents.
- RRF constant 60, graph max hops 2, graph bonus coefficient 0.10.
- Primary metric for a future evaluation: paired delta supporting-document Recall@5.
- Reserved query cohort SHA256 `a560b1cbabe1ce6b4413f0f6f59759cd08e69ce49c5391e05b7c8767f81bd13f`.
- Read-only source archive contract: HotpotQA original data CC BY-SA 4.0; not relicensed by this code.

See `src/raglab/graph/grf01_policy.py` for the actual policy object and hash.

## Run the policy preflight

From Windows PowerShell in the repo root:

```powershell
.\scripts\prepare-grf01-hybrid-local.ps1
```

This runs the **complete pytest suite**, checks that the locally reserved 60-query manifest is identical to the published cohort SHA, and writes `runs/graph-hybrid/GRF01_POLICY_LOCK.json`. A repeat run is idempotent. Any incompatible existing lock fails closed.

The preflight **does not download a model, run the 60 reserved questions, calculate recall or change the public default Hybrid RRF policy**. Tests use synthetic sources.

## Next acceptance gate

A separate sealed evaluation runner has now been implemented (`src/raglab/graph/grf01_study.py`) and will only run after the lock and full suite pass on the operator's machine. It shares dense and BM25 result lists between baseline and Graph-Hybrid; records graph construction/indexing and embedding/index/query costs, pinned revision/source hash, Recall@1/3/5, paired confidence intervals and failure cases. It refuses to overwrite a completed result. This code still requires local validation. See `scripts/run-grf01-hybrid-study-local.ps1`. No DEV results have been observed yet.

A disjoint cohort from the already explored DEV split is still not a new independent dataset. This limitation must appear on the final result.

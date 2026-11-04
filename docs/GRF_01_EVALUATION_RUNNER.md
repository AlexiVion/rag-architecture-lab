# GRF-01 — Frozen one-pass paired evaluation runner

**State:** The reserved 60-query one-pass experiment has **completed locally** with all Python tests passing, pinned MiniLM loaded successfully, and `GRF01_DECISION=INCONCLUSIVE_NO_AUTOMATIC_PROMOTION`. Independent saved-report audit implementation is staged for local verification.

## One command (Windows)

From a PowerShell terminal in the repo root:

```powershell
& {
    $ErrorActionPreference = "Stop"
    git pull --ff-only origin feat/research-lab-architecture-catalog-20261104
    if ($LASTEXITCODE -ne 0) { throw "PULL_FAILED" }
    & .\scripts\run-grf01-hybrid-study-local.ps1
    if ($LASTEXITCODE -ne 0) { throw "GRF01_ONE_PASS_FAILED" }
}
```

This command runs **all pytest tests first**, requires the original 60-query GRF-01 cohort fingerprint `a560b1cbabe1ce6b4413f0f6f59759cd08e69ce49c5391e05b7c8767f81bd13f`, seals policy SHA via `GRF01_POLICY_LOCK.json`, loads `sentence-transformers/all-MiniLM-L6-v2` at the immutable revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` (CPU, Apache 2.0), and executes one sequential pass across that reserved cohort. First run may download the public model. No user questions, Qwen, credit-bearing API or test labels.

### Matched alternatives

1. BM25 over exact 2–10 supplied distractor paragraphs.
2. Pinned MiniLM Dense over **the same** paragraphs.
3. Canonical RRF (constant 60) over those very same dense and sparse ranked lists.
4. Graph-Hybrid: adds only the frozen `0.10/(60+shortest supported hop count)` quote-backed document bonus, preserving exact RRF ranking when graph cannot contribute a path.

No relevance labels or annotated answer texts reach retrieval or graph construction.

### Measures and provenance

- Primary: paired delta **supporting-document Recall@5** of Graph-Hybrid vs the identical Hybrid RRF.
- Secondary: Recall@1/@3, number of queries with both gold supporting documents retrieved, graph-path activation and provenance.
- Fixed seeded 1,000-replicate query bootstrap CIs plus per-query wins/losses/ties.
- Separate BM25 and Dense indexing/query times, source title graph construction time, quoted-edge graph ranking time; mean and p95.
- Sampled resident memory in MB where `psutil` is installed; optional/missing does not become a fabricated zero.
- Original model revision, dataset SHA, fixed cohort ID hash, policy hash.
- Raw per-query IDs, gold ranks and trace paths **stay local** under gitignored `runs/graph-hybrid`; do not commit source texts from CC BY-SA HotpotQA.

Output names are deliberately fixed:
- `runs/graph-hybrid/GRF01_FROZEN_EVALUATION.json`
- `runs/graph-hybrid/GRF01_FROZEN_EVALUATION.md`

After a successful run the script refuses to rerun or overwrite the result. No post-hoc hyperparameter selection based on those scores.

**Important methodological limit:** The cohort is disjoint from GRF-00's 60 exposed DEV cases, but belongs to the already-explored HotpotQA DEV split; it is **not** a fully independent held-out benchmark. Do not declare general GraphRAG superiority, generated answer correctness or a v1.0 release based on this alone.

### Decision rule

A negative 95% CI for the paired primary delta is a **NO-GO** for this specific graph bonus policy. A CI including zero is inconclusive. A positive CI is marked **positive pending separate resource and provenance gate review**, never automatic deployment. The Hybrid RRF default remains unchanged regardless of this command.

## Recorded GRF-01 run — 2026-11-04

The operator executed the fixed one-pass study at commit `4d5e6d5`, with full pytest PASS, locked model revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, policy hash `fd28fe01f244fa27f731395bd522a331026eb1cfa6a6acb4bcf592db1fb942bb` and reserved cohort SHA256 `a560b1cbabe1ce6b4413f0f6f59759cd08e69ce49c5391e05b7c8767f81bd13f`.

| Metric | Hybrid RRF | Graph-Hybrid | Graph-Hybrid − Hybrid |
|---|---:|---:|---:|
| Recall@1 | 0.4417 | 0.4417 | 0.0000 |
| Recall@3 | 0.7417 | 0.6917 | -0.0500 |
| Recall@5 (primary) | 0.8583 | 0.8500 | -0.0083 |

Original locally saved outputs: `runs/graph-hybrid/GRF01_FROZEN_EVALUATION.json` and sibling Markdown. The terminal log does **not** display the paired CI bounds, individual wins/losses or resource measurements; do **not** infer or invent them.

**Decision:** inconclusive, with no grounds to promote this graph-bonus policy. Hybrid RRF remains the reference. The two completed GRF experiments used **different cohorts and baselines**, so the smaller observed drop in GRF-01 cannot by itself be attributed causally to an architectural improvement.

### Post-run evidence audit

The newly added `scripts/audit-grf01-local.ps1` runs full pytest and independently checks the saved report's per-query source rankings, supporting-document recall, paired bootstrap CI, win/loss/tie counts, graph paths, frozen model/policy/cohort identities and timing summaries. It does **not** rerun the evaluator or load model weights. It prints actual CI bounds and writes a local audit report plus the ignored JSON file consumed by the web explorer. The audit has now **passed on the operator's Windows machine**, including the complete test suite and source-report verification. The archived original run will not be overwritten.


## Final audited result (2026-11-04)

Read the full [GRF-01 audited result](../benchmarks/GRF01_HOTPOTQA_DEV_FROZEN_20261104.md). **PASS**: all Python tests, `GRF01_SAVED_RUN_AUDIT_PASS`, source SHA256 `f2167bc7220554b1864648c5c5de0b67544bfbdba585a4aeed8f466927fcb2b4`. Paired ΔRecall@1=0.0000 CI [−0.0333,+0.0333]; @3=−0.0500 CI [−0.1000,−0.0083]; primary @5=−0.0083 CI [−0.0250,0]. Path-active cases 36 (0 wins/1 loss/35 ties at @5), no path 24 (24 ties). Final study remains **INCONCLUSIVE, NO AUTOMATIC PROMOTION**. No model or query rerun. Public aggregate contains only statistics, source hash and provenance, with local audit taking precedence in the web explorer.

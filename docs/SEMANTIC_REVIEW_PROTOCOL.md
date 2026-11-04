# M2 — Evidence and claim review: reproducible human baseline

## Motivation

The first real Qwen response was off-topic and contained **zero** citations. Our post-generation gate now rejects uncited responses, but citation syntax does not show that claims are **entailed by** evidence. SciFact entries are often scientific propositions to be verified or refuted, not ordinary open-ended questions. Relevance qrels do not by themselves establish entailment or whether the proposition is true.

## Local, model-free procedure

```powershell
.\scripts\prepare-v2-semantic-review-local.ps1
```

The script executes tests, finds the most recent saved V2 answer, and exports an **unlabelled** review packet under `runs/reviews/`. It includes the original query, attempted answer, per-sentence candidate claims, cited source IDs, the actual source snippets passed to Qwen, and the current syntactic citation report.

If a previous answer was rejected by the fail-closed gate, the packet analyzes the **rejected draft**, not the safe notice. The original historical answer can also be reviewed as a legacy artifact.

The JSON contains fields to fill after examining sources:
- Source `relevance`: `relevant`, `partially_relevant`, `irrelevant`, `uncertain`.
- Claim `support`: `supported`, `contradicted`, `unsupported`, `uncertain`.
- `reviewed_evidence_labels`: reviewer-selected source labels `S1`, `S2`, etc. This must be nonempty for supported or contradicted claims.
- `review.reviewer`: name or identifier of the reviewer; `expected_behavior`: `answer`, `abstain`, `uncertain`.

**No field is automatically assigned a semantic truth value.** The score stays incomplete until all sources and claims are reviewed, expected behavior selected and the reviewer identified.

To score a completed packet:

```powershell
.\.venv\Scripts\raglab.exe review-score --path runs/reviews/REVIEW_FILENAME.json
```

Scoring checks reviewer labels and returns counts and an observed claim support rate. A single packet is not a model-wide faithfulness benchmark and reviewer annotation is not independently verified. Semantic evaluation requires a larger labeled set with negative, contradicting, and answerable examples, an explicit annotation rubric, and agreement checks.

## Research isolation

Do not use SciFact test qrels as an inference-time gate or tune the retrieval policy based on the held-out test failure. Review packets from the test failure are **diagnostic examples**, not a training set.

No LLM, cross-encoder, or embeddings are invoked in this protocol. Local packets can contain raw model generations and source text; they are not committed to GitHub.

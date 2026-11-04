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

## Guided review in Windows PowerShell

To avoid editing JSON manually, run:

```powershell
.\scripts\review-latest-v2-semantic-local.ps1
```

This reads the latest **original** packet and displays the claim and every retrieved passage. You explicitly choose source relevance (`r/p/i/u/s`) and claim support (`s/c/n/u/k`). When you mark a claim **supported** or **contradicted**, enter the exact source labels you personally verified. Enter `u` for an uncertain conclusion, or skip when there is inadequate information; do not guess. Notes are optional.

The tool also asks for a reviewer identifier and expected behavior (`a`=answer, `b`=abstain, `u`=uncertain, `s`=skip), and writes a distinct **annotated** JSON file without overwriting the original packet. It computes a support rate **only if all labels and reviewer identity are supplied**. Reviewer labels are treated as human observations, not automatically proven facts.

The source passages may be truncated, and domain expertise may be needed to interpret biomedical studies. It is valid to answer **uncertain** rather than assert unsupported biomedical claims. This held-out query is diagnostic only and cannot be used for test-set tuning.

## Distinguishing answer adequacy from claim support (M2-HUMAN-001)

The first **completed** human annotation on the historical `beir/scifact/test` claim #1 found five source passages irrelevant, a generated statement supported by an irrelevant article, no citations, and an expectation to **abstain**. The case report is `benchmarks/M2_SCIFACT_TEST_Q1_HUMAN_REVIEW_20261104.md`.

The scorer now outputs **separate** fields: `source_adequacy_from_human_labels`, `observed_behavior`, `observed_behavior_evidence` and `behavior_alignment_with_human_review`, while retaining `fully_supported_claim_rate` strictly as a claim-level label summary. The last metric **cannot** be interpreted as answer relevance or end-to-end task success. Those scores remain `null` because they need an additional independently specified rubric. Older annotated packets lacking an explicit `actual_abstained` property are supported: a nonempty, legacy candidate text is taken as an **inferred** attempt to answer, and the inference is explicitly labeled.

To re-score the latest annotated JSON, without overwriting the human input or invoking models:

```powershell
.\scripts\audit-latest-annotated-v2-local.ps1
```

The script creates a separate `summary_*.json` next to the annotated packet and will not overwrite an existing summary. This is still held-out test diagnostics only, **not** a train/dev calibration exercise.

## TRAIN-only development controls

Use `scripts/prepare-m2-dev-cases-local.ps1` to construct 18 independent, **unlabelled** evidence-review packets based solely on SciFact TRAIN qrels (six stable propositions × three candidate contexts). These are not Qwen outputs. They provide source-vs-task and no-context examples for a reviewer to annotate without using our inspected SciFact TEST failure to choose calibration thresholds.

See `docs/M2_DEV_EVIDENCE_CASES.md` for the design, selection method, caveats and required human labels. The cross-query alternative is **not inherently irrelevant or contradictory**; no automatic model-quality score is generated. Contradictory labels cannot be inferred from cross-query negatives. The original SciFact TRAIN dataset separately contains expert-labelled SUPPORT and CONTRADICT evidence rationales; see the NO-GO evidence report `benchmarks/M2_SCIFACT_TRAIN_NLI_NO_GO_20261104.md`. These gold-rationale labels do not themselves verify RAG end-to-end answer correctness.

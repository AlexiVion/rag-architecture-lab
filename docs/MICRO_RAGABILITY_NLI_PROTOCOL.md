# MICRO-RAGABILITY-01 — External inter-context contradiction detection with small CPU NLI

**Protocol status:** frozen before running either registered model on this benchmark.  
**Purpose:** measure whether off-the-shelf small NLI cross-encoders detect contradictions between external source snippets.  
**Not measured:** retrieval quality, answer generation, source authority, calibrated abstention, or end-to-end RAG utility.

## 1. Why this benchmark

MICRO-CF-01 showed that the SQuAD2-fine-tuned MiniLM extractive reader could answer straightforward synthetic facts but failed all six exposed synthetic cross-document contradictions. Its generated sentence templates were easily solved by a hand-written regular expression. That suite was useful as an engineering failure detector, but not as an independent generalization benchmark.

We therefore move to the published **Ragability Corpus** by Gross, Petrak and Krenn (LREC 2026). The authors use 43 distinct conflict-context pairs selected from the human-annotated WikiContradict benchmark, replace real entities and some dates/numbers with fantasy entities, and manually construct 53 dataset entries/variants. The dataset is public at Hugging Face under **CC-BY-SA-4.0**. It is a much stronger external benchmark than our own templates, but it is still small, public and derived/adapted; it is **not** a sealed test set or an independent annotation project by this repository.

Sources:
- [Ragability paper (LREC 2026)](https://aclanthology.org/2026.lrec-1.182/) · [PDF](https://aclanthology.org/2026.lrec-1.182.pdf)
- [Official RagabilityCorpus dataset card and files](https://huggingface.co/datasets/ofai/RagabilityCorpus)
- [Dataset immutable revision](https://huggingface.co/datasets/ofai/RagabilityCorpus/tree/2251634ed365bfca55e7d808290b0cf2c5fde730)
- [OFAI reference implementation](https://github.com/OFAI/python-ragability)

The paper describes 253 human-annotated WikiContradict instances, 92 requiring implicit reasoning, 51 unique context pairs among those, and eight pairs excluded as unclear. The remaining 43 unique conflict pairs form the empirical basis. The 53 Ragability entries introduce variations of queries and/or contexts. Thus the independent unit for uncertainty analysis is **contradiction_ID**, not every row or every derived pair.

## 2. Frozen corpus and pair labels

- Dataset: ofai/RagabilityCorpus
- Immutable revision: 2251634ed365bfca55e7d808290b0cf2c5fde730
- File: Dataset_v0.4.tsv
- License: CC-BY-SA-4.0
- Expected rows: **53**
- Expected distinct source-conflict groups: **43**
- Context fields: context_1, context_2, context_3_nc1_c2, context_4_nc1_nc2_nc3

The official TSV has one row with a blank optional WikiContradict_ID cross-reference. The parser preserves that row and records the missing cross-reference count; it does not infer or fabricate an original ID. The required contradiction_ID remains present and is used for group-level provenance.

The published design specifies:
- context_1 and context_2 are conflicting.
- context_3 is a reformulation that is no longer contradictory to context_1, but is explicitly contradictory to context_2.
- context_4 is additional context that is not contradictory to any of the other contexts.

For each row, this protocol evaluates all six unordered context pairs exactly once:

| Pair | Frozen binary label | Reason |
|---|---|---|
| c1 vs c2 | contradiction | Original conflict pair |
| c2 vs c3 | contradiction | Context 3 is constructed to conflict with context 2 |
| c1 vs c3 | non-contradiction | Context 3 is constructed not to conflict with context 1 |
| c1 vs c4 | non-contradiction | Context 4 is compatible with all contexts |
| c2 vs c4 | non-contradiction | Context 4 is compatible with all contexts |
| c3 vs c4 | non-contradiction | Context 4 is compatible with all contexts |

This produces **318 pair cases**: 106 contradictions and 212 non-contradictions. The 318 cases are clustered within **43 original conflict groups**. We do not report a naive independent-row confidence interval.

No dataset rows are allocated to training or calibration. This is a **public external evaluation** only; neither model threshold nor prompt is fitted to it. Raw text is downloaded at run time from the pinned immutable dataset revision and is not committed or uploaded in the result artifact. Artifacts contain IDs, SHA256 text fingerprints, predictions, probabilities and aggregate metrics only.

## 3. Registered small models

Both checkpoints are public English NLI cross-encoders trained on SNLI and MultiNLI. They output contradiction, entailment and neutral scores. Model-card licenses are Apache-2.0.

| Model | Published parameter count | Model card |
|---|---:|---|
| cross-encoder/nli-MiniLM2-L6-H768 | 82.1M | [Hugging Face](https://huggingface.co/cross-encoder/nli-MiniLM2-L6-H768) |
| cross-encoder/nli-deberta-v3-xsmall | 70.8M | [Hugging Face](https://huggingface.co/cross-encoder/nli-deberta-v3-xsmall) |

Exact checkpoint commits are checked before download; the actual full revision SHA, license, safetensors SHA256, weight bytes and parameter count are emitted in the run manifest. The DeBERTa model's current main revision is accepted only if its commit starts with the registered a150876 revision prefix; inference then downloads using the full returned immutable SHA.

The Sentence Transformers model documentation reports MNLI-mismatched accuracy of 86.89 for MiniLM2 and 87.77 for DeBERTa-v3-xsmall. These are **published MNLI results, not Ragability results** and must never be substituted for our measured benchmark outcome.

## 4. Frozen NLI inference and aggregation

For each unordered context pair, the model receives both directions:
1. (context A, context B)
2. (context B, context A)

The two three-class softmax vectors are averaged. The binary conflict decision is:
- contradiction if contradiction is the highest of the three symmetric mean scores;
- non_contradiction if entailment or neutral is highest.

This mapping is deliberately fixed and threshold-free. It avoids fitting a threshold on the public test set. Forward-only and reverse-only outcomes, directional agreement, and the symmetric primary result are all retained. The NLI scores are **uncalibrated model outputs**, not probabilities that a factual conflict exists.

A model-card-style sanity set (one generic entailment, one contradiction, one neutral pair) is run before the benchmark. Sanity failures are reported; they are not silently used to tune the model or the benchmark.

## 5. Metrics and uncertainty

Primary:
- binary accuracy;
- balanced accuracy;
- macro F1;
- contradiction precision, recall and F1;
- confusion matrix;
- always-non-contradiction baseline;
- directional agreement and forward/reverse results.

Secondary:
- per-pair-type accuracy;
- per-reasoning_required_c1c2 category metrics;
- source-group cluster-bootstrap 95% percentile interval for balanced accuracy.

Bootstrap protocol: 2,000 deterministic resamples, seed 20261109, sampling **43 contradiction_ID groups with replacement** and retaining every derived row/pair belonging to each sampled group. The 318 pairs are not treated as independent observations.

No calibration threshold is selected. No benchmark result changes any production/runtime evidence policy.

## 6. CPU measurement

Each model runs in a separate GitHub Actions job/process on a GitHub-hosted Ubuntu CPU runner, with two PyTorch threads. Record:
- exact model and data revision;
- actual parameter count and safetensors bytes/hash;
- model download/load time;
- actual number of pair directions and model batches;
- total tokens presented;
- batch p50/p95 wall time;
- total tokenization + model-forward + softmax wall time;
- process peak RSS.

These are batched **verifier-only** costs. They are not pure neural-forward timing, per-request end-to-end latency, energy measurements or a comparison with the user's Ryzen laptop. Retrieval and answer generation are not part of this experiment.

## 7. Interpretation and no-go rules

This experiment can answer: **does an off-the-shelf 70–82M NLI classifier recognize the conflict structure in this published corpus, and what CPU cost does it incur?**

It cannot establish:
- factual correctness or semantic entailment for arbitrary company documents;
- the best source when sources differ in authority or recency;
- safe answer generation or calibrated refusal;
- transfer to Spanish/French or multilingual corpora;
- production-level RAG reliability;
- a novel research contribution.

If a model detects explicit but misses implicit conflict, that is a meaningful failure, not a prompt-tuning invitation on the same benchmark. If the model performs well, the next gate is a separately sourced real-web benchmark such as **ConfRAG** (ACL 2026, 1,814 questions and heterogeneous retrieved web paragraphs), followed by genuinely independent human review and a sealed group-level test.

## 8. Execution

From the repository root after installing the generation and development extras:

    python -m pytest -q tests/test_ragability_conflict.py
    python scripts/micro/ragability_nli_cpu.py --model-key minilm --output-dir runs/micro-ragability-nli/minilm
    python scripts/micro/ragability_nli_cpu.py --model-key deberta_xsmall --output-dir runs/micro-ragability-nli/deberta_xsmall

The bounded [GitHub Actions workflow](../.github/workflows/micro-ragability-nli-cpu.yml) runs the two checkpoints in separate CPU jobs and uploads only result/provenance JSON and Markdown, never the source dataset or model weights.

# PAPER-01 / P2 — audited real ConfRAG viewpoint diagnostic

**2026-11-10 · External published public DATA / real small CPU NLI / DEVELOPMENT EXPLORATION · SCIENTIFIC RELEASE NOT VALIDATED**

This report compares two off-the-shelf, frozen small neural NLI verifiers to a fixed lexical baseline, using the same **author-extracted website answers** from the ConfRAG dataset. The question is whether NLI's logical contradiction output transfers to identifying **different annotated answer viewpoints**, not whether either NLI model solves factual RAG.

## Primary empirical observation

**16 public question groups, 240 derived pairs (NOT 240 independent questions)**; 130 pairs have *different* author-annotated answer viewpoint clusters, 110 belong to the same cluster.

| Fixed method | Active neural params | Correct pairs | Accuracy | Balanced accuracy | Different-viewpoint precision | Different-viewpoint recall | TP / FP / TN / FN |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Answer-token Jaccard < 0.5 | 0 | **164/240** | **68.33%** | **65.45%** | 63.11% | **100%** | 130 / 76 / 34 / 0 |
| DeBERTa-v3-xsmall NLI three-class argmax | 70,831,107 | 124/240 | 51.67% | 55.24% | **88.89%** | 12.31% | 16 / **2** / 108 / 114 |
| MiniLM2 NLI three-class argmax | 82,120,707 | 120/240 | 50.00% | 53.15% | 66.67% | 15.38% | 20 / 10 / 100 / 110 |

**TP/FP positive event means *two different author-cluster viewpoints*. It does NOT mean a verified logical contradiction.** For NLI, only an argmax prediction of 'contradiction' is provisionally mapped to this event. The model was not fine-tuned for viewpoint grouping, so this is a genuine **out-of-task transfer diagnostic**, not a fair claim that lexical overlap is a better contradiction classifier.

The fixed lexical control identifies all 130 different-cluster pairs in this sample but produces 76 false alarms among 110 same-cluster pairs. DeBERTa's positive predictions are more precise (16/18), but it misses 114 of the 130 pairs. MiniLM2 misses 110 of 130. The two NLI models agree on 210/240 three-way class predictions; in a three-sentence ordinary semantic sanity suite both get only 1/3 right. This cautions against treating their outputs as safe semantic arbiters.

## Provenance and actual execution

- **Source:** [ConfRAG, Yuan et al., ACL 2026](https://huggingface.co/datasets/OracleY/ConfRAG), version `ConfRAGsuggested.jsonl`, license CC BY 4.0. Exact Hugging Face dataset revision `529e760a78a58791d0387fe469e0732377a6d94d`.
- **Bounded data access:** first 18 JSONL records read (3,943,167 source bytes), selected the first 8 eligible questions where the author-level `contradicts` flag is true and the first 8 false, max six website answer claims/question. Public order-biased prefix, **not random or blind**. Bytes read prefix SHA256 `24c62a4b4df17e8d80a15338d27b05624201fd3fc67862b64e44bc8a2e9dadd6`; selected pair-input SHA256 `acd2012c7371c408d46987424db876b04efc7ba06b726823215fa9c0d817c8d7`. Whole dataset SHA256 not computed because the file is streamed only until selection is complete.
- **DeBERTa:** `cross-encoder/nli-deberta-v3-xsmall` revision `a150876415327c80daeff35ca6f68f5ed8cf5c24`, 70,831,107 parameters; Apache 2.0. The initial [run #42858534499](https://github.com/AlexiVion/rag-architecture-lab/actions/runs/42858534499) and pinned repeat [run #42859350349](https://github.com/AlexiVion/rag-architecture-lab/actions/runs/42859350349) produced identical source hashes and 240/240 DeBERTa predictions. The two-model run also reproduced them.
- **MiniLM2:** `cross-encoder/nli-MiniLM2-L6-H768` revision `b95119ce93d3e065de6214e38cd4a97b0f2f2c6d`, 82,120,707 parameters; Apache 2.0.
- **Two-model exact-source CI:** [GitHub Actions #42859891303](https://github.com/AlexiVion/rag-architecture-lab/actions/runs/42859891303) SUCCESS, artifact IDs **13785545104** (DeBERTa) and **13783229469** (MiniLM2). [Full offline Python/TypeScript/Chromium CI #42859891295](https://github.com/AlexiVion/rag-architecture-lab/actions/runs/42859891295) SUCCESS, both at PR #40 head `aaa30e5f2d4a39d8aabac11d256200d09522800d`; merged [PR #40](https://github.com/AlexiVion/rag-architecture-lab/pull/40) as `d52ce9149f51a492ff8c98cf10aa8fb51ec0479b`.
- **Independent recomputation:** download both JSON artifacts; the [comparison module](../src/raglab/evaluation/confrag_comparison.py) independently validates source hashes, source group IDs, exact pair labels and reported confusion tables before scoring. No full website pages, unredacted article text or model weight bytes are included in public artifacts.

## CPU scope — measured, NOT a universal speed ranking

| Model | Directional NLI inputs | Forward batches | Inference-batch wall ms | Weight bytes |
| --- | ---: | ---: | ---: | ---: |
| DeBERTa | 480 | 20 | 26,293.08 | 283,353,172 |
| MiniLM2 | 480 | 20 | 31,767.11 | 328,499,560 |

These are **separate, potentially heterogeneous shared GitHub runners**, with different concurrent jobs and cached conditions. They include tokenization + model forward + softmax only; they exclude source search, webpage extraction, question answering, indexing, model loading and power consumption. The initial DeBERTa run had 22,014.38 ms vs 26,293.08 ms on a separate run: variation alone precludes a general causal speed ranking. Both NLI models are below 100M parameters **individually**, but this experiment includes **no 33M QA reader** and is not the proposed 104–115M combined RAG.

## Uncertainty — post-result descriptive analysis, not confirmatory inference

The 240 pairs are correlated within 16 original questions. A deterministic 10,000-resample bootstrap resampling *whole question groups*, seed 20261110, calculates descriptive model-minus-control accuracy deltas:

| Delta in accuracy | Observed | Descriptive group-bootstrap percentile interval |
| --- | ---: | ---: |
| DeBERTa − Jaccard | −16.67 percentage points | [−35.42, +1.67] pp |
| MiniLM2 − Jaccard | −18.33 pp | [−40.42, +3.33] pp |
| MiniLM2 − DeBERTa | −1.67 pp | [−8.33, +3.75] pp |

The interval procedure was added **after** observing the initial DeBERTa result. It is descriptive only, with 16 highly clustered source groups, no sealed split and no multiplicity correction; **do not call the difference statistically established**. MiniLM2 was also added post hoc. None of these values constitute certified error risk.

## Interpretation, boundary and next experiment

**Observed:** both generic small NLI systems use 'contradiction' too sparingly to identify all author-distinct ConfRAG viewpoints, while the simplistic lexical control flags many false positives. This illustrates a **task/representation transfer issue**, not a new discovery of a previously unknown algorithm. It does **not** establish that a model parameter count is unnecessary or that any of these methods can ground real QA answers.

**Important annotation limitation:** ConfRAG's author-provided website answers were extracted by their pipeline using LLM assistance; the present study fed those answers directly into NLI. We did not run the 33M extractive reader or verify the underlying full webpage content. Different viewpoint clusters need not be true logical contradictions and author labels are not two fresh blinded human reviews.

**Next falsifiable step:** run the *same* 33M automatic span extractor over independently selected natural-language evidence, not privileged author answer strings. Add a pre-specified source-level decision policy and a <=135M combined tiny pipeline (33M QA + ~71M verifier) vs QA-only and 135M generator under matched questions and CPU budgets; then evaluate with reviewed evidence support labels and explicit correct-answer coverage. Include negative controls for equivalent-but-differently-worded answers and distinct-but-compatible facts so a lexical shortcut cannot win. **This stage and the independent two-domain human holdout remain OPEN** in [PAPER-01 #39](https://github.com/AlexiVion/rag-architecture-lab/issues/39).

## Reproduce the comparison (from saved public CI artifacts)

```sh
python -m raglab.evaluation.confrag_comparison \
  --deberta path/to/deberta/results.json \
  --minilm path/to/minilm/results.json \
  --output runs/paper01/confrag-audited-comparison.json \
  --bootstrap 10000
```

Both JSON artifacts are downloadable from [the Actions run](https://github.com/AlexiVion/rag-architecture-lab/actions/runs/42859891303). No dataset or model download required for the post-run comparison. Scientific claim remains **NO-GO**.

# MICRO-NATURAL-QA-02 — Real CPU results on 32 human-written SQuAD2 questions

**Date:** 2026-11-09. **Verdict: ENGINEERING PASS / SCIENTIFIC ANSWER QUALITY NO-GO under tested conditions.** No paper-level claim of novel RAG optimization, source entailment or small-model superiority is justified.

## Evidence and reproducibility

- [Natural QA implementation, PR #18](https://github.com/AlexiVion/rag-architecture-lab/pull/18), merged to main at **a88057560352b6cdf2488830b89ec18ce42786cd**.
- [Matched compact/verbose ablation, PR #19](https://github.com/AlexiVion/rag-architecture-lab/pull/19), merged as **7b385cbf6d67709e0be7665359ce6e277ac81abe**.
- [Both actual 32-case CPU model runs — GitHub Actions #42662178196](https://github.com/AlexiVion/rag-architecture-lab/actions/runs/42662178196) **SUCCESS**; [full offline Python/TypeScript/browser CI #42662178199](https://github.com/AlexiVion/rag-architecture-lab/actions/runs/42662178199) **SUCCESS**.
- Original public **Stanford SQuAD 2.0 DEV**, licensed **CC BY-SA 4.0**. Exact original file SHA256: **80a5225e94905956a6446d296ca1093975c4d3b3260f1d6c8f68bc2ab77182d8**, 4,370,528 bytes. [Official dataset/rights](https://rajpurkar.github.io/SQuAD-explorer/). Cite Rajpurkar, Jia & Liang (2018), *Know What You Don't Know: Unanswerable Questions for SQuAD*.
- **32 natural questions:** 16 officially answerable, 16 unanswerable relative to the original paragraph, across **16 distinct source articles**; **128 unique source contexts**, including 96 additional fixed DEV distractors. Article-level hashing prevents overlapping source article groups across declared DEV/CALIBRATION/HOLDOUT partitions; **only public DEV was executed**.
- Every model ran on a separate GitHub Ubuntu CPU job with its exact pinned public weights, fixed 128-token evidence budget, up to 24 new tokens and a one-token non-dataset warmup. Five same-model conditions: no retrieval; BM25 naive verbose; BM25 naive compact; BM25 query-aware spans verbose; BM25 query-aware spans compact. Source IDs, original quotes and offsets remain in the audit JSON even when removed from model-facing compact headers.

## Real reference-answer results (NOT source-supported factual accuracy)

| Condition | Pythia-14M exact match / 32 | Pythia F1 | SmolLM2-135M exact match / 32 | SmolLM2 F1 |
| --- | ---: | ---: | ---: | ---: |
| No retrieval | 0 | 0.0045 | 0 | 0.0340 |
| Naive verbose | 0 | 0.0174 | 0 | 0.0548 |
| Naive compact | 0 | 0.0293 | 0 | 0.0701 |
| Query-aware spans verbose | 0 | 0.0000 | 0 | 0.0587 |
| Query-aware spans compact | **1** | 0.0611 | **0** | 0.0776 |

**The single Pythia exact match was a correct refusal on one originally unanswerable question, NOT an answer to any answerable question. Neither model exactly answered any of the 16 answerable questions in any of the five modes.**

Official unanswerability is relative to its **original one-paragraph SQuAD context**, not necessarily to our expanded retrieval corpus; a distractor could contain information that resolves the question. The reported refusal metric must not be interpreted as independently validated open-corpus answerability.

## Retrieval evidence versus generation

BM25 retrieved the gold paragraph among its five candidates for **16/16 answerable cases** for both model jobs. But retrieving the paragraph did not guarantee the answer text survived context truncation or that a tiny generator could use it.

| Context supplied to the model | Pythia: answer literally present in context | SmolLM2: answer literally present | Pythia mean evidence tokens | SmolLM2 mean evidence tokens |
| --- | ---: | ---: | ---: | ---: |
| Naive verbose | 12/16 | 11/16 | 127.6 | 127.8 |
| Naive compact | 14/16 | 14/16 | 127.5 | 127.4 |
| Spans verbose | 13/16 | 13/16 | 109.9 | 97.3 |
| Spans compact | 14/16 | 14/16 | 113.3 | 115.1 |

**A literal answer substring inside the source is only an exposure diagnostic, not semantic entailment or a correct final answer.** Compact headers often preserved more relevant original text under the same tokenizer budget, but the absolute generated answer quality remained extremely poor.

### Paired uncertainty — article-cluster bootstrap (descriptive only)

Paired resampling uses **16 article groups** rather than treating the correlated pair of questions per article as independent (1,000 fixed-seed replicates). Values are the candidate-minus-baseline change in automatic gold-reference F1; they **do not establish scientific generalization** from public DEV.

| Within-model comparison | Pythia F1 difference, descriptive 95% CI | SmolLM2 F1 difference, descriptive 95% CI |
| --- | --- | --- |
| Naive compact – naive verbose | +0.0119 [−0.0126, +0.0431] | +0.0153 [−0.0226, +0.0685] |
| Spans compact – spans verbose | +0.0611 [+0.0054, +0.1601] | +0.0189 [−0.0306, +0.0673] |
| Spans compact – naive compact | +0.0318 [−0.0173, +0.1117] | +0.0076 [−0.0455, +0.0476] |

**Do not advertise the one Pythia positive CI as a reliable optimization breakthrough:** this is one publicly exposed DEV cohort, with small n, unstable overlap-based F1 and zero correct answers to answerable questions.

## Resource observations (not energy efficiency claims)

| Observation | Pythia-14M | SmolLM2-135M-Instruct |
| --- | ---: | ---: |
| Safetensors weight bytes | 28,143,920 | 269,060,552 |
| Whole-process peak resident memory | ~1,080 MiB | ~1,507 MiB |
| Naive verbose generation p50 | ~129.6 ms | ~441.1 ms |
| Spans compact generation p50 | ~127.9 ms | ~438.8 ms |
| Trial wall time, 32 × 5 conditions | ~21.0 s | ~64.9 s |

Execution ran **on CPU**, although the installed PyTorch package supports CUDA. The high-water process RSS includes Python/torch/model and full experiment, not just weights. GitHub-hosted CPU VM SKUs may differ, so these are trace observations rather than a controlled power/energy or same-CPU cross-model efficiency study. Package installation and model download are excluded from per-query generation times.

## Artifact and checksum verification

Both 32-case output ZIP archives were downloaded and independently inspected. The source and result SHA256 values in their manifests match the actual JSON bytes. The dataset manifest hash is shared between the two models: **ee499f52a36b23404edb39c7ac208c69e7e08e76d298a69d967b0c34724a531f**.

| Verified item | Pythia-14M | SmolLM2-135M |
| --- | --- | --- |
| Model revision SHA | cf967c0a9a04383db6f7b1108d86b2962634b4ac | 12fd25f77366fa6b3b4b768ec3050bf629380bac |
| Safetensors SHA256 | 116a02532db461f91386a5b20f942ff2c8d4de7341e21b55caafc3d7b25f49a1 | 5af571cbf074e6d21a03528d2330792e532ca608f24ac70a143f6b369968ab8c |
| Gold reference metrics JSON SHA256 | 96bb409ccf6bea551bf33e73b66ad1bceb9c1993ed287370a52ae7880d5a5579 | b6e77071c007222fa41e92c91cb902efe6f25d4ec2df4e3217f96068d3741fa0 |
| Per-case trace JSON SHA256 | 65165d5c39fa65211441448a0424ba6cd23deda267596a35efd3984de0c063fe | 6788b37d611c6828510100f49f33b33fec520c24f059866e379395ca0bd76c38 |

GitHub Actions artifact names: **micro-squad2-pythia-14m** (ID **13693834506**) and **micro-squad2-smollm2-135m** (ID **13695247336**). They do not contain any model weights.

## Research decision — what to develop next

**Engineering GO:** pinned natural QA source, true public weights and matched per-case traces are functioning.  
**Scientific generation NO-GO:** neither checkpoint gave useful, reliably correct natural-language answers in these tested conditions. **Not a general limit on tiny RAG; a specific failure needing diagnosis.**

Priority experiments:

1. **Oracle answer-bearing passage:** explicitly provide the actual gold-answer-containing excerpt at a matched token budget, clearly flagged as a *diagnostic upper bound*, to distinguish model failure to use evidence from retriever/packer failure. For negatives, keep no-answer evidence discipline.
2. **Model-appropriate instruction design:** Pythia-14M is a base LM, not trained to follow system prompts; run controlled few-shot/task-format experiments separately. SmolLM2 should receive a tested chat template. Freeze prompts before evaluation.
3. **Non-generative/extractive competitors:** compare hard-coded span/abstention rules and a properly licensed tiny QA encoder/sequence model. Account for *complete* sensor/retriever/encoder/controller stack.
4. **Hybrid RRF/recall comparators:** measure whether source exposure really benefits from a more costly retriever under the same answer/CPU/RAM budget. Current DEV saw gold doc Recall@5 100% with BM25, suggesting the dominant problem here is downstream generation rather than finding its paragraph.
5. **Independent semantic annotations and sealed evaluation:** truly new source-grouped cohort with blind human source-support/answerability adjudication, contradictions and insufficient evidence, no tuning on SQuAD DEV, and predefined significance and resource criteria.
6. **Observatory:** show only appropriately labeled exploratory/negative real aggregates after verifying licensing and user interface; do not claim scientific certification or unblock the unrelated GitHub Pages settings.

**Central hypothesis to investigate:** how can a tiny model use evidence that the retriever already found? A careful negative result on that question is more valuable than adding another elaborate pipeline without a measured quality improvement.

# MICRO — Why tiny RAG generators fail even with correct evidence; extractive 33M control

**Date:** 2026-11-09  
**Status:** **REAL CPU EXPERIMENTS PASS — GENERATIVE ANSWER QUALITY NO-GO UNDER TESTED CONDITIONS**. A task-trained extractive 33.4M reader achieved useful reference QA results on this same public DEV cohort, but **not** an independently generalizable quality or efficiency win.

This document reports actual model execution, original source/checkpoint hashes, exact test denominators, failure modes and next research gates. It does **not** replace our independent factual-support/abstention protocol or justify automatic publication of generated answers.

## Scientific question and experiment identity

Previous CPU benchmarks found that BM25 retrieved the gold source for **16/16** answerable SQuAD2 questions, yet the two tiny causal models answered **none of the 16 answerable cases exactly**. To isolate whether the problem was *finding* evidence or *using* evidence, we tested a privileged source oracle, model-family-specific prompting, then a specialized non-generative QA reader.

- **Data:** official [Stanford SQuAD 2.0](https://rajpurkar.github.io/SQuAD-explorer/) **public DEV**, 32 real English questions = **16 answerable / 16 originally unanswerable**, **16 article groups**, 128 distinct passages (including 96 distractors). Original source SHA256 **80a5225e94905956a6446d296ca1093975c4d3b3260f1d6c8f68bc2ab77182d8**; original dataset **CC BY-SA 4.0** (Rajpurkar, Jia and Liang, 2018).
- **Selected dataset fingerprint across all three model experiments:** **6127d2502bd0a3f7c7cedb184db465e9fd16fb74cb62339b97bebbed26502dbc**. The same exact cohort and candidate corpus were independently verified against all three downloaded CI artifact manifests.
- **Generator models:** [EleutherAI/Pythia-14M](https://huggingface.co/EleutherAI/pythia-14m) (base LM, official SHA **cf967c0a9a04383db6f7b1108d86b2962634b4ac**) and [HuggingFaceTB/SmolLM2-135M-Instruct](https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct) (instruction-tuned, SHA **12fd25f77366fa6b3b4b768ec3050bf629380bac**). Both model cards expose Apache-2.0 metadata. Each was run as real CPU inference.
- **Specialized extractive control:** [deepset/minilm-uncased-squad2](https://huggingface.co/deepset/minilm-uncased-squad2), **33.4M parameters**, SHA **934656cdda79824eabf503ed56e15c01ddbdbe3f**, verified safetensors SHA256 **240478c7251d5e55be35feb47177054b960259b9328af662ea3cee87ce9755a6**, 133,466,376 bytes; **CC BY 4.0 model-card license**. **Crucially, this reader was specifically fine-tuned on SQuAD2**, so its task-matched success is **NOT a training-matched or open-domain comparison** with the two generative LMs.

## Experiment A — Gold-answer windows: did the models actually see the answer?

For each positive question we explicitly selected a word-for-word source excerpt **centered on the gold answer**, inside a **128 model-token evidence budget**. These `oracle_window` prompts use privileged answer annotations and must NEVER count as deployable retrieval or an independent model-quality result.

For the negative questions the oracle supplied the **original SQuAD paragraph**, because the official "impossible" label is relative to that paragraph, **not** necessarily to the multi-document retrieval corpus.

Each generator ran **32 questions × three source modes × two prompt formats**:

1. **Actual retrieval:** BM25 + query-aware `spans_compact` (no access to gold annotations).
2. **Privileged original gold paragraph:** `oracle` (gold source ID disclosed).
3. **Privileged source window:** `oracle_window` (gold answer position disclosed; **16/16 positive cases contained the answer text**).

Prompt families: **legacy** uses our previous universal chat instruction. **Role-adapted** uses a fixed synthetic few-shot completion for the base Pythia model or the SmolLM2 model's native chat template. We developed these formats after seeing the earlier DEV failures: **this is prompt debugging on public DEV, not independent evaluation**.

| Generator / prompt | Actual BM25 spans exact match | Gold source paragraph exact match | Gold-answer window exact match | Gold answer present in oracle window |
| --- | ---: | ---: | ---: | ---: |
| Pythia-14M / legacy | **0/32** | **0/32** | **0/32** | **16/16** positive |
| Pythia-14M / role-adapted completion | **0/32** | **0/32** | **0/32** | **16/16** positive |
| SmolLM2-135M / legacy | **0/32** | **0/32** | **0/32** | **16/16** positive |
| SmolLM2-135M / role-adapted chat | **0/32** | **0/32** | **0/32** | **16/16** positive |

A model seeing a gold-bearing sentence is not equivalent to producing the reference answer. Here, **even the privileged source oracle did not yield one correct exact short answer**, for either model/prompt in the 16 answerable questions. We cannot conclude those checkpoints can never perform QA; only that **this frozen prompt/decoding/budget setup failed**.

Automatic SQuAD word-overlap F1 for the **gold-answer window** was: Pythia legacy **0.0298**, role-adapted **0.0038**; SmolLM2 legacy **0.0800**, role-adapted **0.1164**. The SmolLM2 role-adapted F1 difference was **+0.0364** with article-cluster descriptive 95% CI **[−0.0135,+0.0879]**, crossing zero. The Pythia adapted prompt performed worse on this public DEV. None of these partial-word-overlap values demonstrate correct factual answers.

**Verifications:** [full Python/UI/browser CI #42698423895](https://github.com/AlexiVion/rag-architecture-lab/actions/runs/42698423895) **PASS**; [two genuine CPU model oracle jobs #42698423912](https://github.com/AlexiVion/rag-architecture-lab/actions/runs/42698423912) **PASS**; [regression baseline #42698423705](https://github.com/AlexiVion/rag-architecture-lab/actions/runs/42698423705) **PASS**. Original implementation [merged PR #21](https://github.com/AlexiVion/rag-architecture-lab/pull/21), integration commit **1ae1e1e71e4b57fa2ae5558063af779d58233b74**. Downloadable original CPU artifacts: Pythia **13711235266** and SmolLM2 **13711531285**. Independently verified SHA256 against each zipped JSON trace/metrics manifest.

## Experiment B — Could a much smaller task-specific non-generative model extract answers?

Instead of asking an extremely small *causal LM* to freely generate a response, we loaded a **33.4M-parameter QA encoder specifically trained for the SQuAD2 task**. It predicts start/end token logits in supplied context; we extract the exact original document substring, apply an uncalibrated **fixed null threshold 0**, and record the original document offsets.

This control is not an LLM, and it cannot produce arbitrary prose. Its advantages come in part from **having been trained specifically to perform extractive question answering**. A fair model-architecture paper would need matched supervision and independent evaluation.

Three policies were tested on the same 32 questions, no human tuning of the threshold on DEV:

| Policy | Gold source in candidates, positive cases | Reference exact matches | Correct positive answers | Correct originally unanswerable refusals | Mean model CPU forward per query |
| --- | ---: | ---: | ---: | ---: | ---: |
| BM25 **top-1** + 33M extractive reader | **15/16** | **24/32 (75.0%)** | **11/16** | **13/16** | **36.9 ms** |
| BM25 **top-5** + same reader | **16/16** | **23/32 (71.9%)** | **11/16** | **12/16** | **202.7 ms** |
| **Privileged** original-gold-paragraph + same reader | **16/16** by definition | **24/32 (75.0%)** | **11/16** | **13/16** | **36.1 ms** |

The **same pinned model, dataset and reviewer-free QA metric** were used within the three policies. Top-5 reading cost approximately **5.5×** the mean model-forward CPU time of top-1 **in the same runner**, without improving reference exact match. The top-5 policy can increase false positives because the null-vs-answer logit margins of multiple passages are not necessarily cross-passage calibrated.

Original-document quotation integrity held: every non-refusal prediction was reconstructed **exactly** from `document_text[start:end]`, not hallucinated text. However, a copied passage **can still fail to answer the question correctly**. On BM25 top-1, **16/32** results carried a non-refusal exact source span, but only **11/16** positive cases received a reference-exact answer. Source substring provenance and semantic faithfulness are separate tests.

The final pinned run had an entire-process peak resident memory of **1,268,960 KiB** (Python, PyTorch, weights and runtime included, not model-only). Weight file size was **133,466,376 bytes**, and the CPU environment was a GitHub-hosted Linux runner, **not** the owner's Windows Ryzen CPU. Model weights and source corpus were **never included in the artifacts**.

**Verifications:** pinned real CPU [GitHub Actions #42700210942](https://github.com/AlexiVion/rag-architecture-lab/actions/runs/42700210942) **PASS**; exact-head full Python/UI/browser [#42700211099](https://github.com/AlexiVion/rag-architecture-lab/actions/runs/42700211099) **PASS**; [PR #22 merged](https://github.com/AlexiVion/rag-architecture-lab/pull/22) at **5bf037da83b3ae8151cfd82307e9c3202d306137**. Artifact **13710033678**, `micro-minilm-33m-extractive-qa-dev`. Metrics file SHA256 **2d0f07a73b24e7f736f505c4010ecd28e49965871566a5a19609cec7ed10e027** independently recomputed from the downloaded ZIP and matched the run manifest.

## What the results actually establish

**Pass:** real CPU execution of three different small models with official source/weights, exact source/DEV fingerprint parity, determinate four-stage evaluation, error traces, source-offset integrity, original licensed model provenance, model-specific source/prompt controls and no inflated science score.

**Fail / incomplete:** no generator produced one correct exact answer to answerable cases in our selected public DEV under the tested setups, even after gold-answer oracle assistance. There is **no independent source-supported reliability measurement, calibration, pristine holdout, fairness-controlled model comparison, or universally better retrieval policy**.

**Most actionable hypothesis:** on evidence-extraction tasks, a small **task-fine-tuned encoder and selective retrieval** might be more useful per CPU unit than forcing a tiny general causal LM to generate free-form answers. That remains a hypothesis for broader domains and matched training; in this tiny public same-task DEV pilot it is a plausible engineering direction, not a new method or publishable general scientific discovery.

## Next experimental gates — preserve the research program

1. **MICRO-QA-FAIR:** compare a well-supervised small causal LM and a similarly task-trained extractive encoder on *new, domain-separated cases* with the same accessible supervision budget. Present model-only and **complete system** costs separately. Preserve the true real model revisions.
2. **MICRO-ABSTAIN:** calibrate the reader's fixed null threshold *only* on a separately frozen development/calibration corpus, and evaluate risk/coverage, false refusal, false answer and source support once on a new sealed evaluation set. SQuAD original-paragraph impossibility is not expanded-corpus impossibility.
3. **MICRO-ADAPTIVE-TOPK:** prespecify query-routing/early-exit criteria and compare top-1 vs top-5 under matched recall, QA accuracy, CPU p95 and full RAM. Current top-1/t5 difference is not enough to certify an optimization.
4. **MICRO-GROUNDED:** require blinded human review of each generated answer's individual claims and exact evidence, paired disagreements/adjudications and correct refusal labels. No citation syntax or extracted substring is accepted as semantic proof.
5. **MICRO-DOMAINS:** independently authored documents/questions across topics and languages, source-grouped splits and contamination analysis, then power/uncertainty study. Public SQuAD DEV results stay DEV-only.
6. **MICRO-UI:** after review, add accurately labeled real outcomes, source traces and negative studies to the existing observatory. Avoid publishing model drafts or licensed SQuAD text as the site's own data.

**No change to the separate v0.1.0 Pages administration blocker or the original GraphRAG/M2 NO-GO findings.**

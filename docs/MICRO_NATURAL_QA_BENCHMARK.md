# MICRO-NATURAL-QA-01 — Public natural-question CPU research pilot

**Status:** code proposed in [PR #18](https://github.com/AlexiVion/rag-architecture-lab/pull/18); real results are **NOT claimed** until exact-head GitHub Actions and artifacts are checked. This pilot is an **exploratory public DEV** benchmark, **not** untouched external validation, publication-ready science, or independent source support.

## Objective

Evaluate **real tiny language models** using **real human-written natural questions**, official short-answer references, and contexts drawn from the same source. Test whether query-aware evidence selection changes answer quality under a fixed context token budget.

Official dataset: [Stanford SQuAD 2.0](https://rajpurkar.github.io/SQuAD-explorer/) (Rajpurkar, Jia & Liang, 2018), released under **CC BY-SA 4.0**. Its official DEV source is `https://rajpurkar.github.io/SQuAD-explorer/dataset/dev-v2.0.json`, exactly SHA256 `80a5225e94905956a6446d296ca1093975c4d3b3260f1d6c8f68bc2ab77182d8` (4,370,528 bytes). We do **not** commit or redistribute this source corpus, only download and verify during the experiment.

### Fixed sampling contract (MICRO-SQUAD-v1)

- **DEV only**: select articles by stable `sha256("micro-squad2-v1-article:" + article_title)` bucket, DEV 0–5, CALIBRATION 6–7, HOLDOUT 8–9. The default pilot refuses CALIBRATION/HOLDOUT access. Source/article group must not cross splits.
- **8 natural questions** = 4 answerable + 4 adversarially unanswerable; one of each from four distinct article groups, chosen by stable hashes of official question IDs. Additional **96 DEV context paragraphs** serve as distractors.
- **Same input to each system**: one checkpoint and question, independently measured across `no_retrieval` (parametric recall), `naive` BM25 top-k prefix, and `spans` BM25 query-aware original-offset excerpts. `max_context_tokens=128`; `max_new_tokens=24`; source snippets retain exact original offsets.
- **CPU models**: pinned Pythia-14M `cf967c0a9a04383db6f7b1108d86b2962634b4ac` (base language model), and pinned SmolLM2-135M-Instruct `12fd25f77366fa6b3b4b768ec3050bf629380bac` (instruction tuned). Hugging Face card metadata licenses Apache 2.0; always recheck exact revision before reuse. No GPU/remote inference/API needed.
- **Measurements**: gold reference exact match (EM), normalized token F1, answerable-only EM, unanswerable refusal accuracy, false abstention rate, gold-doc recall among retrieved results, true checkpoint-tokenized evidence tokens, rendered chat prompt tokens, per-stage wall timings and whole-process peak resident memory (Linux ru_maxrss). Download, cold model load and one-token warmup timing tracked **separately**.
- **Outputs**: exact checkpoint/data SHA manifests, case-level traces (unreviewed text; CC BY-SA context; **CI artifact only**), reference-metric summaries and the execution environment. No model weights in GitHub artifacts.

## What this experiment can and cannot prove

It can prove that the benchmark infrastructure genuinely runs natural-language questions against public checkpoints and reports **automatic gold-reference QA scores** with traceable provenance.

It cannot prove source entailment, hallucination rate, safety, general usefulness, model superiority, or a statistically significant context-optimizer effect. The publicly exposed SQuAD DEV may have appeared during model pretraining. Four positive/four negative examples are deliberately stratified, **not** a representative sample of the dataset. Even 100 DEV examples would not make a new independent holdout.

**Strong scientific next step:** preregister a new domain-separated corpus with independent human-authored/verified answerable, contradictory and insufficient-evidence labels; add a same-model Hybrid RRF baseline and full source-support adjudication. Evaluate 64+ paired cases with confidence intervals, standardized warmed CPU latency and peak RAM. Preserve failed as well as successful results.

## Exact reproduction

```bash
python -m pip install -e ".[generation]"
python -m pip install "huggingface-hub>=0.29,<2"
python -m pytest -q tests/test_micro_squad_benchmark.py
python scripts/micro/squad2_natural_cpu_pilot.py \
  --model-id pythia-14m \
  --output-dir runs/micro-natural/pythia-14m \
  --max-cases 8 --distractors 96 \
  --max-context-tokens 128 --max-new-tokens 24
```

Or trigger `.github/workflows/micro-squad2-cpu.yml` in GitHub Actions after CI/merge. It runs two models independently on GitHub-hosted Ubuntu CPUs, never the user's Windows Ryzen 7 environment.

Related: [MICRO issue #11](https://github.com/AlexiVion/rag-architecture-lab/issues/11) · [MICRO implementation tools](MICRO_RESEARCH_IMPLEMENTATION.md) · [first 1-question real weights pilot](MICRO_REAL_MODEL_PILOT.md) · [full experiment protocol](EXPERIMENT_PROTOCOL.md).

# PAPER-01 · Working manuscript (NOT SUBMITTED)

**Provisional title:** *The 135-Million-Parameter Frontier: Selective Evidence-Grounded Question Answering on Commodity CPUs*

**Author(s):** to be confirmed by actual research contributions.  
**Status:** DRAFT / preregistered study / no independent human evaluation.  
**Repository:** https://github.com/AlexiVion/rag-architecture-lab  
**Protocol:** [PAPER-01 preregistration](../../docs/PAPER_01_MICRO_CPU_FRONTIER_PROTOCOL.md)  
**Integrity:** Any future reported result MUST link executable source SHA, dataset license/hash, model hash, environment, review decisions and archived experiment artifact.

## Abstract — proposal, not empirical result

Can retrieval-augmented question answering remain useful when the **entire neural pipeline** is restricted to at most 135 million parameters and must run on a commodity CPU? We propose a source-group-aware, paired evaluation measuring correct supported answering, selective acceptance risk, evidence-intervention compliance, wall-clock computation and peak memory. The proposed systems include a task-trained 33M extractive reader, its 104M/115M combinations with compact NLI verification, and a similarly budgeted 135M generative reader, all subject to matched corpora and frozen model configurations. We distinguish structured-source integrity from free-text semantic support and explicitly evaluate contradiction, answer deletion, misleading evidence and sham controls. Our hypotheses, primary endpoints and failure criteria are registered before creating an independent human-reviewed test set. **No generalization result is claimed at this stage.**

## 1. Introduction

Modern RAG often frames progress as retrieval recall or answer generation quality at larger model capacities. But source-grounded systems can fail after retrieving answer-bearing evidence, especially when passages contradict each other or describe the wrong entity. Citation validation proves provenance, not truth. At extreme model sizes, prompt-based refusal and model-generated answer normalization are especially fragile. This work asks whether carefully composed small components and robust refusal can provide better **useful answers per unit of compute** than a standalone generative alternative.

**Hypothesis:** for some evidence regimes, a compact QA+verifier stack may be a more useful low-resource operating point than a similarly sized generation-only stack. The study is explicitly designed to falsify this hypothesis.

## 2. Prior art and distinction

Source-intervention compliance is directly related to **DOVE-RAG / Dynamic Evidence Contracts (EMNLP 2026)**. Set-level sufficiency and certificates have already been studied by **SURE-RAG** and **Certify**. Retrieval-free abstention and distraction screening are already reported in **RINSE**, **GRAB-RAG**, **Sieve and Sage**, **C-RAG** and others. We claim no invention of these concepts. The current possible contribution is their **carefully controlled interaction at a drastically lower total parameter and CPU budget**, a distinctive empirical result only if stronger than the baselines. See [related-work matrix](../../docs/PAPER_01_MICRO_CPU_FRONTIER_PROTOCOL.md).

## 3. Research questions

**RQ1:** Are accepted answers sufficiently supported by independently reviewed source spans, without accepting misleading or contradictory context?

**RQ2:** What is the Pareto frontier among risk, correct-answerable coverage, full-stack CPU p95/throughput, active model parameters and peak RSS?

**RQ3:** Does the preferred operating point survive realistic document families, distinct domains and controlled evidence interventions, rather than exploiting superficial attributes of synthetic records?

## 4. Methods

- **System variants:** S0 structured-only software sanity check; S1 bare MiniLM-33M extractive *shadow baseline*; S2 MiniLM-33M + DeBERTa-71M verifier; S3 MiniLM-33M + MiniLM2-82M verifier; S4 SmolLM2-135M generation-only stack; S5 refuse-all and prompt controls. Include full active parameter accounting. No fabricated S2/S3 test-time semantic verifier acceptance before calibration.
- **Experimental populations:** development cohorts from public QA/conflict datasets, plus 600 newly human-reviewed items with two separate realistic domain families and frozen source-group disjoint splits: 180 development, 120 calibration, 300 untouched test, subject to actual access and review.
- **Interventions:** retain paired source identity while permuting sources, removing decisive evidence, inserting a same-entity contradictory answer, adding a surface-matched irrelevant source, and controlling for stale/authority metadata. All edits remain inside one partition.
- **Outcome definition:** accepted wrong/accepted, correct accepted/answerable, conflict recall and false positives, correct supported accepted/full-stack CPU second, process peak RAM and cold/warm p50/p95.
- **Uncertainty:** preregistered paired group-level inference, explicit safety-risk upper bound conditional on accepted sample size, report negative results and multiple-comparison limitations.
- **Reproducibility:** exact hash-pinned corpora and models, locked source group split, two real reviewers, separate reviewer adjudication, CPU order randomization, public artifact checksums.

## 5. Software development sanity pilot — NOT paper results

A 108-case synthetic, author-generated, structured-literal **zero-neural-model** intervention suite has been implemented at [`intervention_audit.py`](../../src/raglab/micro_v02/intervention_audit.py). It is a **software correctness control** inspired by prior evidence-intervention research; there is no independent human annotation, real-world QA, model comparison, risk confidence interval or source-domain generalization.

**Outcome:** CI results and artifact links only AFTER verification; do not copy development-fixture percentages into the scientific results section.

## 5.1. Exploratory transfer diagnostic on public ConfRAG web answers (real CPU; not a heldout result)

We implemented an explicitly non-confirmatory study using **16 public ConfRAG question groups, 240 correlated pairs** of website answers **already extracted by the dataset authors**. Each pair was labeled only as same vs different **author-annotated answer-viewpoint cluster**, never as an independently verified logical contradiction. A fixed zero-neural-model answer-token Jaccard threshold 0.5 obtained **164/240 (68.33%)** pair accuracy, with all 130 different-cluster pairs detected but 76 false positives. Frozen DeBERTa-v3-xsmall NLI (70.8M parameters) reached **124/240 (51.67%)**, with 16/130 different-cluster detection and only two false positives; frozen MiniLM2 NLI (82.1M) reached **120/240 (50.00%)**, detecting 20/130 with ten false positives. Both NLI models achieved only one correct label in three simple generic inference controls.

These observations show a **task-transfer and precision–recall trade-off** for our imperfect NLI contradiction-as-viewpoint proxy. They do not show that lexical matching solves semantic contradiction, and they do not evaluate end-to-end RAG: no automatic 33M answer extractor or evidence-sufficiency verification was used. Data are public and order-biased; MiniLM2 was added post-result; only 16 source-question groups exist. Post-result descriptive question-group bootstrap intervals span zero for each model-versus-control accuracy difference. The [audited results report](../../docs/PAPER_01_CONFRAG_DEV_RESULTS.md) includes exact dataset/model hashes, both model confusion tables, reproducible artifact IDs, CPU scope and explicit limitations.

**Research decision:** do not promote generic NLI to a reliable arbitrator of viewpoints. Next test actual source-conditioned, automatically extracted claims with fair task-matched controls and human-reviewed labels before making any paper-level scientific claim.

## 6. Independent experimental results

**PENDING — intentionally blank.** Required plots:
1. Risk–coverage curves by system and by domain.
2. Correct supported answers per full-stack CPU second, error bars across restarts.
3. Conflict recognition and unrelated-distractor invariance for paired source groups.
4. Active parameter count vs RSS and cold/warm CPU p50/p95.
5. Human-review disagreement/adjudication counts and accepted-error audit.
6. Failure taxonomy and negative controls.

## 7. Discussion

**PENDING.** Compare against DOVE-RAG behavioral contracts and SURE-RAG/C-RAG prior risk-control findings, not self-cited software benchmarks alone. Discuss bounded source search, calibration transfer, training-objective differences, coverage collapse, mismatched model counts and CPU measurement generalizability.

## 8. Threats to validity

The strongest potential threats are public data contamination, missed cross-source contradictions, uncalibrated NLI, objective mismatch between a SQuAD-trained span extractor and general instruction models, and misleadingly small synthetic evaluation. Confidence bounds require true independent source clusters and sufficient accepted answers. Model weights may not be redistributable; provide fetch instructions with license instead of committing weights.

## 9. Conclusion

**PENDING independent empirical results.** A paper can report a null/negative finding if transparently powered and replicable. Do not write claims of unique discovery, first-of-its-kind certification, or negligible hallucination without evidence.

## References — live bibliography

- Zeng et al., [Dynamic Evidence Contracts](https://aclanthology.org/2026.emnlp-main.1494/), EMNLP 2026.
- Setiawan, [Prompt-Based Abstention Fails Under Misleading Context](https://aclanthology.org/2026.aacl-long.153/), AACL 2026.
- Lee et al., [Shifting from Ranking to Set Selection](https://aclanthology.org/2025.acl-long.861/), ACL 2025.
- [SURE-RAG, evidence sufficiency / uncertainty](https://www.alphaxiv.org/abs/2605.03534v1), 2026 preprint.
- [ConfRAG: conflicting Web references](https://aclanthology.org/2026.acl-long.11/), ACL 2026.
- Kang et al., [C-RAG: Certified Generation Risks](https://proceedings.mlr.press/v235/kang24a.html), ICML 2024.
- [RINSE](https://yunmingxiao.github.io/publication/26-rinse/), 2026 preprint.
- [Certify: requirement-directed search](https://arxiv.org/abs/2610.34684), 2026 preprint.

**Publication block:** This Markdown is a working manuscript, **not** a submitted or accepted research paper and does not claim any new scientific result.

# PAPER-01 — preregistered research program (DRAFT, not a completed study)

**Working title:** *How Small Can a Trustworthy RAG Pipeline Be? Evidence-Intervention Compliance and Useful-Answer Yield Under a CPU Budget*

**Date:** 2026-11-10. **Paper status:** research plan / registered hypotheses, **NO independent result**. The [scientific tracker #28](https://github.com/AlexiVion/rag-architecture-lab/issues/28) remains open.

## 1. Scientific question and non-claim of novelty

**Question:** Can a compositional CPU-only QA pipeline whose TOTAL simultaneously active neural parameter count is <=135 million attain lower **wrong-accept risk** and higher **correct supported answers per CPU-second** than a matched small-generator RAG under conflicting/missing evidence?

What would be new if established is **a carefully measured resource-constrained Pareto frontier at this particular tiny scale**, with cross-domain blind evaluation and explicit source-intervention controls—not inventing RAG, abstention, citations, counterfactual testing, conformity, certificate methods or NLI. No precedence/uniqueness is claimed.

**Required literature counterexamples (existing contributions):**

| Prior work | Already established; not our novelty |
| --- | --- |
| [C-RAG (ICML 2024)](https://proceedings.mlr.press/v235/kang24a.html) | Conformal/certified RAG generation risk |
| [(D)RAGged Into a Conflict (Google Research, 2025)](https://research.google/pubs/dragged-into-a-conflict-detecting-and-addressing-conflicting-sources-in-retrieval-augmented-llms/) | Human-annotated conflict taxonomy and desired resolution behaviors |
| [SetR (ACL 2025)](https://aclanthology.org/2025.acl-long.861/) | Set-wise evidence selection rather than individual ranking |
| [ConfRAG (ACL 2026)](https://aclanthology.org/2026.acl-long.11/) | 1,814 real-world conflicting-reference questions |
| [SURE-RAG (2026 preprint)](https://www.alphaxiv.org/abs/2605.03534v1) | Set-level sufficiency, uncertainty, selective answering |
| [RINSE (2026 preprint)](https://yunmingxiao.github.io/publication/26-rinse/) | Pre-generation sufficiency checks; control of shortcut features |
| [Beyond Static Grounding / DOVE-RAG (EMNLP 2026)](https://aclanthology.org/2026.emnlp-main.1494/) | Dynamic evidence contracts: deletion, conflict, distraction, permutation and ICS |
| [GRAB-RAG (AACL 2026)](https://aclanthology.org/2026.aacl-long.153/) | Paired misleading-evidence abstention controls on frozen 3.8–8B models |
| [Certify, Knowing When Evidence Is Enough (2026 preprint)](https://arxiv.org/abs/2610.34684) | Structural Horn-closure evidence-sufficiency certificates |
| [From Evidence to Exact Answers (EMNLP 2026)](https://aclanthology.org/2026.emnlp-main.849/) | Copy-preserving compression and calibration for a frozen 1.2B small reader |
| [Sieve and Sage (EMNLP Findings 2026)](https://aclanthology.org/2026.findings-emnlp.2356/) | Lightweight distraction screening before LLM generation |
| [Ragability](MICRO_RAGABILITY_NLI_RESULTS.md) | Existing local small NLI evidence and published corpus study |

**Interpretation:** A 108-case intervention harness alone is a **replication/engineering control inspired by DOVE-RAG**, NOT a novel benchmark. The claim requires real free-text answers, matching budgets, independent labels, held-out source groups and statistical separation.

## 2. Prespecified hypotheses (may fail)

- **H1 — risk/coverage:** At a matched decision latency/RAM regime, a <=135M-total-parameter *extractive + verifier* configuration achieves a lower wrong-acceptance rate than the same extractive reader WITHOUT semantic verification and retains at least 80% of its correctly accepted answerable-question coverage. The null is no improvement or too much abstention. Statistical direction is exploratory until sample sizes support it.
- **H2 — budgeted frontier:** At comparable upper bound on wrong-accept risk, at least one <=135M-parameter composed system delivers **more correctly supported accepted answers per total CPU second** than BM25 + a 135M generator under identical corpus/query conditions. Failure to satisfy risk control is scored NO-GO, not an efficiency success.
- **H3 — intervention sensitivity:** Among otherwise answerable queries, inserting a true conflicting same-entity source reduces accepted wrong answers and produces the appropriate visible conflict/review decision more often than a single-source/top-k-only baseline. A same-length irrelevant/sham edit must NOT cause a comparable collapse in correct coverage.
- **Exploratory H4:** the best policy's efficiency/risk difference persists across two domains and multiple initial seeds. Never declare generality from one corpus or one CPU run.

**No result exists yet for H1–H4.** Do not infer from the existing 261/318 Ragability NLI classification, synthetic MICRO tests or 24/32 SQuAD2 extraction that any hypothesis is true.

## 3. Fair systems and total neural parameters

A model budget means **sum of active model parameters**, not merely generator size, including QA, NLI, any embedding or reranker weights in the tested path. A CPU BM25 lexical index is not a neural model.

1. **S0:** BM25 + transparent strict structured-literal parser, no neural model; report only in a *separate structured-fixture stratum*, never as competitive free-text QA.
2. **S1:** BM25 + MiniLM QA (~33M) with offline *shadow* auto-accept policy solely for calculating a comparator error rate. It must NOT publicly auto-answer without semantic support.
3. **S2:** S1 + DeBERTa-v3-xsmall NLI (~71M), approximately 104M combined; all decisions calibrated on human-labeled development/calibration data, exact citations and independent contradiction review. Unknown entailment becomes REVIEW.
4. **S3:** S1 + MiniLM2 NLI (~82M), approximately 115M combined; the same policies, separate thresholds fitted only on calibration.
5. **S4:** BM25 + frozen SmolLM2-135M-Instruct generator (~135M), with a fixed extractive/citation prompt, no additional neural verifier if strictly respecting 135M total.
6. **S5:** refusal-only safety control, plus a cheap naive prompt-abstention control (no claim of viable QA). Optionally larger model **OUTSIDE** budget as explicitly labeled reference, never counted as <=135M.

Models are frozen; pin full checkpoint SHA, tokenizer, model card license and download hash. **Prior small-model comparisons have different fine-tuning objectives** (SQuAD QA vs causal LM vs NLI), so conclusions must be operational-stack comparisons, not a claim of inherent superiority due solely to size. Matching retriever, corpus, candidate count, questions and machine condition matters. Do not sum a 135M generator and an 82M verifier and label it a 135M system.

## 4. Independent datasets, no leakage

- Minimum 600 **real, independently reviewed** QA decisions from **at least two distinct realistic domains**, suggested (subject to licenses/access and reviewer competence): scientific evidence abstracts and versioned technical documentation. Existing SciFact/ConfRAG/SQuAD2 public data are **development/replication cohorts**, not an untouched new holdout.
- Target partitions: 180 development, 120 calibration, 300 sealed test, with whole **source families/groups** separated, no answer/query paraphrase crossing splits, and locked version hashes. Across both domains, balance supported, contradictory, missing, misleading and stale/ambiguous-evidence strata. The intervention variants of one original question stay in the **same** split.
- For all 600, two actual human reviewers independently label (i) possible answer / abstain, (ii) answer text, (iii) source spans, (iv) contradiction type, (v) temporal/authority exceptions. Record reviewer disagreements and adjudication. Reviewer metadata MUST correspond to real people; do not synthesize human labels or claim a model grader is a human.
- Check overlap of QA content and source text with existing pretraining/evaluation corpora where possible; document the irreducible contamination risk. If independent review cannot be obtained, the work may be a technical report/replication, **not** a certified general-RAG study.

## 5. Matched interventions (established protocol; baseline controls)

For each original question, run the same reader and retrieval stack on (a) original evidence, (b) source permutation, (c) distractor addition, (d) deletion of decisive support, (e) genuinely conflicting same-entity source, (f) entity-mismatched sham source, (g) temporal/authority change if labeled and appropriate. Use length/position-matched controls to avoid lexical shortcut labels. Preserve source-group IDs; **one paired group**, not seven independent samples.

The repository's current local-only [pilot](../src/raglab/micro_v02/intervention_audit.py) runs 12 invented groups × 9 engineering operations = **108 visible, non-independent, structured-only tests**. They test invariants, not H1–H4.

## 6. Primary endpoints, no cherry-picking

- **Wrong accept risk** = unsupported/incorrect accepted answers divided by all accepted answers; refused outputs are neither successes nor wrong accepts. When accepted count is zero, rate is undefined and useful yield is zero.
- **Correct-answerable coverage** = correct supported accepted answers divided by truly answerable cases. A refuse-all model fails.
- **Useful CPU throughput** = total correct supported accepted answers / **total full-stack CPU wall seconds** (including retrieval, tokenization, extraction, verification, decision), measured on the same machine. Report wall-time-based throughput explicitly, not energy/joules without power instrumentation.
- **Intervention compliance** (at fixed question and controlled evidence delta): exact expected decision changes, conflict recognition, unchanged-answer control performance; pair by original source group. This is related to DOVE-RAG ICS; comparisons require exact protocol mapping rather than name collision.
- **Cost**: repeated independent process restarts, randomized AB/BA model order, p50/p95 and peak RSS per configuration, cold/warm load and index time separately, fixed CPU governor/thread count if measurable. GitHub shared runners alone do not establish general CPU speedups.
- **Group-wise uncertainty**: stratified source-group bootstrap as descriptive interval; for predeclared safety risk also use an appropriate accepted-case binomial upper bound and disclose its assumptions. Account for source-group dependence; do not call a naive per-intervention bootstrap a formal guarantee. One untouched confirmatory set, no data-dependent threshold adjustment there.
- **Gate to claim reliability:** proposed earlier spec thresholds, accepted wrong risk <=5%, conservative 95% upper bound <=10%, conflict recall >=90%, >=60% correct-answerable coverage, CPU reference p95 <=2s and peak RSS <=4GiB. Failure or underpowered accepted count => **NO-GO**.

## 7. Reproducible phased experiment

| Phase | Action | Readout | Status |
| --- | --- | --- | --- |
| P0 | Literature map and falsifiable hypotheses | This pre-registration; novelty not assumed | PROTOCOL ONLY |
| P1 | 108-case authored paired structured interventions | Unit/CI JSON; only verifies software invariants | IMPLEMENTED, CI PENDING |
| P2 | Public dataset development controls; matched extraction/NLI/generator | Pairwise output, provisional metrics, source provenance | NOT EXECUTED |
| P3 | Independent two-reviewer multi-domain corpus, sealed group split | 600 labeled examples, reviewer agreement and adjudication | NOT EXECUTED |
| P4 | Frozen selective-risk+coverage and CPU study | Model comparisons, held-out results, CIs, cost | NOT EXECUTED |
| P5 | Paper, replication package, preprint/review | Exact source/data hashes, negative results, defensible limitations | NOT EXECUTED |

## 8. Stop/go and intellectual honesty

- **GO to full paper** only if results are real, reproducible, important, and distinguishable from DOVE-RAG, SURE-RAG, RINSE, Certify and small-model conversion/efficiency work. A useful rigorous negative result could also support a workshop/technical paper.
- **No novelty claim** until a complete related-work comparison shows a distinct contribution; *being the only discoverer* cannot be promised.
- **No accuracy percentages from this pilot** in a real-world reliability claim. No model weights/private documents in test artifacts, no author-identity misrepresentation, no forged review, no premature acceptance or venue claims.

**Provisional paper abstract (not results):** We investigate the operating boundary of retrieval-augmented question answering when total neural capacity is restricted to 135 million parameters and inference runs on commodity CPUs. We propose a paired, source-group-aware evaluation of correctly supported selective answering under absence, contradiction and distraction, measuring the joint risk–coverage–CPU-efficiency frontier. We compare extractive readers, compact verification compositions and a similarly budgeted generator on matched corpora. The study is pre-registered to report both failure and success; its independence and final numerical findings remain to be established.

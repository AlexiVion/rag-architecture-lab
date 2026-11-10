# MICRO-CF-v1 — Novel corpus-wide facts, contradictions and calibrated refusal

**Research status:** preregistered *engineering stress test* using artificially generated documents. **This is not independent human-reviewed generalization, a sealed holdout, or scientific support certification.** The code is publicly available, including the generation templates, gold labels and audit split.

## Why this is the next test

The earlier public SQuAD2 DEV pilot suggested that a **33.4M SQuAD2-fine-tuned extractive QA encoder** can produce useful *reference answers* on the dataset for which it was trained (BM25 top1 24/32, top5 23/32), whereas 14M and 135M generative models struggled even with privileged gold-answer windows. That cannot show off-task generalization or explain corpus-level contradictory information.

**Hypothesis to falsify:** a complete system consisting of lexical retrieval + a small extractive reader + calibrated refusal can safely answer **new, unknown facts** even when sources are partially missing or conflicting, with bounded CPU cost. Our strict failure criteria below are intentionally capable of rejecting that hypothesis.

## New synthetic facts, not public encyclopedic QA

The test creates 36 fictional stations identified by novel deterministic pseudonyms, **72 documents**, and **108 questions** under frozen seed `20261109`. Each has a primary registry and an operational record, with varying sentence templates. Questions ask:

1. **Known phase marker** (answerable; present in exactly one original record).
2. **Storage seal** (either two sources agreeing → answerable, or two equally authoritative sources disagreeing → **contradiction requires abstention**).
3. **Operating permit signer** (**absent across the entire relevant entity corpus**, not merely missing from one paragraph).

By construction, there are **54 answerable**, **36 absent** and **18 contradictory** questions. The strictly correct answer to a conflict or absent signer is **`INSUFFICIENT_EVIDENCE`**, not a guessed value or a copied contradictory source. A correct accepted answer must match the expected value **and cite an eligible original source document** with exact offsets.

### Frozen partitions and labels

| Partition | Fictional station groups | Docs | Questions | Answerable | Absent | Conflict |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| DEV | 12 | 24 | 36 | 18 | 12 | 6 |
| CALIBRATION | 12 | 24 | 36 | 18 | 12 | 6 |
| AUDIT | 12 | 24 | 36 | 18 | 12 | 6 |

Station IDs and documents are disjoint across partitions. This avoids **trivial entity leakage**; however, the **same synthetic templates** appear in every partition, and anyone can inspect the generated audit data from source code. **The AUDIT partition must never be described as a blinded or independent hidden holdout.**

All labels are programmatically asserted against the complete relevant corpus group, including the two conflicting records. There are **no human source-support annotations**, so "correct" here only means *exactly correct under the artificial fact-generation rules*, not independent semantic correctness.

### Fixed comparison policies (same frozen model)

- **BM25 top1 + extractive MiniLM**: single retrieved paragraph and one QA forward pass.
- **BM25 top3 + same MiniLM**: three separate QA passes; pick highest positive start/end-vs-CLS margin, recognizing logits may not be cross-paragraph calibrated.
- **CALIBRATION-gated top1/top3**: same raw predictions but refuse unless the model's answer/null logit margin clears a **frozen threshold chosen exclusively on CALIBRATION**. Candidate grid fixed before AUDIT: `0,1,2,3,5,8,12,20,30,50,refuse_all`. Require **≥5 calibration accepts** and an **observed conditional wrong-accept rate ≤15%**; among feasible candidates maximize correct answerable predictions then minimize wrong accepts. If none satisfies, **refuse everything**. This is an engineering calibration rule, **not a statistical 15% risk guarantee**.
- **`template_rule_top3` shortcut detector**: hand-written regex explicitly for the synthetic sentence templates. No neural model. If it scores well, that is evidence the corpus has exploitable formulaic regularities, **not** a general purpose zero-parameter intelligence finding.
- **POST-HOC, EXPLORATORY conflict guard on top1/top3**: after observing the initial AUDIT failures, we added a source-text regex check that identifies two distinct storage seal statements for the same station, and forces refusal. It does **not** consume gold labels at inference, but it was *designed after seeing AUDIT results* and understands our templates: its results **MUST NOT** be treated as a new untouched holdout validation or predeclared quality improvement. Reader passes remain 1/3 respectively. This test indicates possible value of a symbolic cross-source consistency check, not general NLI.
- **Refuse-all**: necessary control to ensure trivial abstention does not appear to solve factual QA.

The decoder enforces exact input-document offsets and applies fixed MiniLM null threshold zero before calibration. All policies use the **same exact pinned checkpoint**: `deepset/minilm-uncased-squad2@934656cdda79824eabf503ed56e15c01ddbdbe3f` (SQuAD2 task-fine-tuned; model card license CC BY 4.0). Full model/checkpoint SHA and safetensors bytes must be recorded from real CPU execution. No model weights are committed or redistributed.

### Release metrics

For every policy and partition, report: **strict correct/36**, answerable correct/18, missing correct refusals/12, contradictory correct refusals/6, accepted/36, **wrong accepted answers**, conditional error among accepted, false refusals, source/document integrity, actual reader-forward counts, input tokens and model CPU forward sum. The overall CPU process high-water RSS and model load time are separately recorded; no energy claim and no arbitrary hardware parity with the owner's Ryzen laptop.

*Policy selection must never touch AUDIT labels.* Publish calibration decision and SHA before scoring AUDIT. The test runner writes the calibration file and hashes it before opening audit metrics, but because code and generator are public this is only a visible/auditable order within one program, **not a sealed statistical study**.

## Go / no-go criteria and limitations

This is a **NO-GO for reliable automated grounded QA** if the AUDIT result has any substantial false-answer/contradiction-accept risk, weak answerable accuracy, or safe calibration collapses to refuse-all. A top1 reduction in model work is **not** a quality win without equal risk/coverage. The result is an engineering stress diagnostic, not independent publication-ready evidence.

This artificial corpus tests **unknown fictional facts** (reducing memorization) and **cross-document conflicts** (unlike original SQuAD unanswerability) but introduces new weaknesses: template artifacts, single linguistic style, fixed answer-value lists, small sample size and programmatic labels. A proper future benchmark requires *new natural independently written source documents*, blind human judgments, domain/language diversity, truly sealed source-group holdout and task-training parity.

## Execution

```bash
python -m pytest -q tests/test_micro_counterfactual.py
python -m pip install -e ".[generation]"
python -m pip install "huggingface-hub>=0.29,<2"
python scripts/micro/counterfactual_cpu_pilot.py --output-dir runs/micro-counterfactual/mini-33m
```

Or [run the bounded GitHub Actions workflow](../.github/workflows/micro-counterfactual-cpu.yml) (Ubuntu CPU, no private API keys). It uploads only original code-generated fictional sources/labels, calibration/metrics and integrity manifests.

**Referenced prior findings:** [real SQuAD2 generator-oracle and MiniLM task-specific controls](MICRO_ORACLE_VS_EXTRACTIVE_RESULTS.md), [research status](RESEARCH_STATUS.md), [MICRO scientific issue #11](https://github.com/AlexiVion/rag-architecture-lab/issues/11). This work does not touch public Pages deployment or change earlier M2/GraphRAG negative verdicts.

## First observed AUDIT outcomes and provenance warning

Before adding the exploratory conflict guard, the real CPU pilot had already shown **top1 30/36 strict correct** (18/18 answerable, 12/12 missing, **0/6 contradiction refusals**) and **top3 29/36** (18/18 answerable, 11/12 missing, **0/6 contradiction refusals**). A simple template-specific regex baseline achieved **36/36**, proving the formulaic suite is easily solved with hand-coded rules. Both safety thresholds selected on CALIBRATION correctly **refused all**, achieving zero wrong accepts but **zero useful coverage**. These observations led us to add the post-hoc guard; we explicitly mark its results as contaminated by prior audit inspection.

Initial real CPU workflow [#42727076887](https://github.com/AlexiVion/rag-architecture-lab/actions/runs/42727076887) **SUCCESS** with source SHA and pinned checkpoint. Detailed, fully checked final results should be recorded separately after the revised guard's CI succeeds. Reader timing includes tokenization, inference and decoding; it is **not** pure neural forward-pass time.

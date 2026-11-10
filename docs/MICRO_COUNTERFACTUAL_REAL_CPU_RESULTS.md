# MICRO-CF-01 — Complete small QA system: unknown facts and conflicting evidence

**Execution date:** 2026-11-09 (Argentina local); GitHub Actions timestamps extend into **2026-11-10 UTC**.  
**Verdict:** **REAL CPU ENGINEERING PASS / TRUSTWORTHY OPEN-DOMAIN ANSWERING NOT VALIDATED.**  
**Key failure:** the existing SQuAD2-trained 33.4M extractive MiniLM answered all **18 answerable synthetic cases** in AUDIT, but confidently answered **all six mutually contradictory cases** instead of refusing. Adding more retrieved passages increased processing cost and introduced one additional incorrect acceptance. A deliberately hand-engineered string-consistency guard removes the failures in this synthetic suite, but was **designed after looking at AUDIT errors** and is **NOT independent evidence of a general improvement**.

## 1. Why this experiment was necessary

The preceding [real SQuAD2 DEV results](MICRO_ORACLE_VS_EXTRACTIVE_RESULTS.md) showed that a 33.4M SQuAD2-fine-tuned encoder got **24/32 reference exact matches** on its own task, compared with 0 exact answers from untuned Pythia-14M and SmolLM2-135M under tested generation setups. That result **does not** establish general answerability, safe contradictory evidence handling or a fair model-size advantage.

This experiment changes the factual data itself. All entities and answers are invented and source-backed. Refusal for absent or conflicting information is defined **relative to both relevant records in the complete synthetic corpus**, not one SQuAD paragraph.

### Original benchmark construction

- **MICRO-CF-v1**, deterministic seed `20261109`.
- **36 fictional stations**, **72 original source documents**, **108 natural-ish questions**, created programmatically; no proprietary or real personal/business data.
- **Three disjoint partitions:** DEV, CALIBRATION, AUDIT. Each has 12 station entities, 24 source documents and 36 questions. Each split has **18 answerable**, **12 absent** and **6 contradictory** questions. Each entity has two distinct source records.
- Answerable: a phase marker, or agreeing storage seal values. Absent: a permit signatory is missing across **all** relevant station records. Contradictory: equally authoritative records state **different storage seals**, making a single definitive answer invalid.
- **Exact answer + source constraint:** accepted answer counts as correct only when the string matches the programmatic gold and its original text span is a verbatim slice of one **eligible evidence source**. No-answer and contradiction require `INSUFFICIENT_EVIDENCE` in the artificial rules.
- Disjoint station IDs protect against direct entity overlap. However, **the template family and label-generating algorithm are shared and publicly visible** across all splits. AUDIT is **not** a sealed hidden holdout; no independent human labeling was performed.

### Models, policies and costs

Only one model checkpoint: the official public **deepset/minilm-uncased-squad2**, **33.4M parameters**, exact SHA `934656cdda79824eabf503ed56e15c01ddbdbe3f`, model-card license metadata **CC BY 4.0**, original safetensors 133,466,376 bytes and SHA256 `240478c7251d5e55be35feb47177054b960259b9328af662ea3cee87ce9755a6`. This model was fine-tuned specifically for SQuAD2; the new fictional station domain is deliberately different, but **still highly formulaic and small**.

The reader uses pretrained tokenized QA start/end logits with fixed no-answer threshold zero, a maximum source input of 384 tokenizer tokens, and **original-offset exact source extraction**. The full system includes BM25 retrieval, reader processing, a gate and optionally a template-specific symbolic consistency check.

Prespecified controls: BM25 top1; BM25 top3; no-answer margin threshold chosen **only on CALIBRATION** from the fixed grid `0,1,2,3,5,8,12,20,30,50,refuse_all` with at least 5 accepted and at most 15% *observed* wrong accepts; hand-written template-rule-only baseline; refuse-all baseline. Calibration chooses **refuse-all for both neural policies**, thereby meeting a zero-error acceptance criterion at **zero useful coverage**. This is a **correct failure of the calibration objective**, not a safe QA product.

**Added after observing the first AUDIT result:** `top1_conflict_guard` and `top3_conflict_guard`, which scan retrieved source text for two distinct storage-seal values for the same named station and force refusal. **These are explicitly POST-HOC and template-specific**. Their impressive AUDIT results cannot be presented as fresh generalization or preregistered improvement.

## 2. What actually happened on the 36-case AUDIT partition

| System policy | Strict correct /36 | Correct answerable /18 | Correct absent refusals /12 | Correct conflict refusals /6 | Accepted answers | Wrong accepts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| **MiniLM + BM25 top1** | **30/36** | **18/18** | **12/12** | **0/6** | 24 | **6** |
| MiniLM + BM25 top3 | 29/36 | 18/18 | 11/12 | **0/6** | 25 | **7** |
| CALIBRATION-thresholded top1 | 18/36 | 0/18 | 12/12 | 6/6 | **0** | 0 |
| CALIBRATION-thresholded top3 | 18/36 | 0/18 | 12/12 | 6/6 | **0** | 0 |
| **POST-HOC** top1 + string conflict guard | 36/36 | 18/18 | 12/12 | 6/6 | 18 | 0 |
| **POST-HOC** top3 + string conflict guard | 35/36 | 18/18 | 11/12 | 6/6 | 19 | 1 |
| **Hand-coded template-rule-only** | 36/36 | 18/18 | 12/12 | 6/6 | 18 | 0 |
| Refuse everything | 18/36 | 0/18 | 12/12 | 6/6 | **0** | 0 |

### Critical risk-versus-coverage interpretation

**BM25 top1 + MiniLM**: 24 responses accepted, six wrong **because they silently chose one side of explicit source conflicts**. Observed **wrong-accept risk = 6/24 = 25%** at 24/36 coverage, despite 18/18 correct answers to straightforward synthetic facts. **BM25 top3**: 25 accepted, seven wrong, **7/25 = 28% observed wrong-accept risk**, at slightly higher coverage. More retrieved documents did not fix source disagreement.

**Calibration-only safety:** none of the thresholds from the preregistered grid achieved the artificial target of at least five calibration accepts with `≤15%` wrong acceptance. The protocol correctly opted to **refuse all**. Such a system has zero useful answer coverage. The 15% target is an **observed finite-sample condition**, NOT a statistically guaranteed risk ceiling.

**The 36/36 post-hoc guard result is not a generalizable scientific win**. We designed that guard *after* seeing the six AUDIT conflicts, and it matches exactly the benchmark's sentence templates. The fact that the **zero-model** template-rule baseline also scored 36/36 proves the synthetic suite is vulnerable to engineered shortcuts. For this artificial template domain, the full QA model may not be the most economical option at all.

### Reader workload (single pinned GitHub CPU run)

| Policy | Actual neural reader calls /36 questions | Sum of measured reader-call wall time |
| --- | ---: | ---: |
| MiniLM top1 | **36** | **459.7 ms** |
| MiniLM top3 | **108** | **1,380.7 ms** |
| MiniLM top1 + post-hoc guard | 36 | 459.7 ms |
| MiniLM top3 + post-hoc guard | 108 | 1,380.7 ms |
| Template-only rule baseline | **0** | **0 ms** for model calls (rule CPU work tracked separately) |
| Refuse-all | **0** | **0 ms** |

These timings include **tokenization, inference and decoding** inside the MiniLM reader call. They are **not pure neural-forward time** or end-to-end API response times. The reader outputs were computed once for three candidate sources and reused across the policy evaluations; the cost table is a **cached matched comparison** of candidate execution paths, not separately wall-clocked live deployments. The process peak RSS was **1,212,436 KiB** (~1,184 MiB, includes Python, torch and all stack state); energy consumption was not measured.

The policies were compared on the **same** Ubuntu GitHub CPU worker with two torch threads, after warmup. No model was downloaded to, or executed on, the user’s machine.

## 3. Checksums, environment and executed code

- Source implementation [PR #24](https://github.com/AlexiVion/rag-architecture-lab/pull/24), squash-merged to main as **`7aa88c6b56bf66bada0a674d356a7eb94dbf0250`**.
- [Real pinned model CPU workflow **#42727787830**](https://github.com/AlexiVion/rag-architecture-lab/actions/runs/42727787830): **SUCCESS** on exact PR head `7fa894d33e2a909a1df0646691322c32d28dc30c`.
- [Offline Python + TypeScript + Chromium/browser CI **#42727787913**](https://github.com/AlexiVion/rag-architecture-lab/actions/runs/42727787913): **SUCCESS** at the same exact head.
- Real model artifact: **`micro-counterfactual-33m-cpu-diagnostic`**, GitHub artifact ID **13724000411**, seven machine-readable JSON files; no weights, no proprietary data. Downloaded and independently rehashed against the output manifest.
- SHA256 `policy_results.json`: **`d10fba739697f001dab8c24a4f1e998679ce3cea579e6e92b122c912e5782fec`** — matches the ZIP byte content.
- SHA256 `frozen_calibration.json`: **`e15ade1d00c3e40101cae06109a0135771ecfb4cebdc9d6aa38d747de615bfb4`** — matches the ZIP byte content.
- Source partition hashes: DEV **`9b2c1ff96dad38c5dc772c3ff2a2430513eb457d40c2fb4d4b566a89b976f3c6`**; CALIBRATION **`366b52da829a012aeebc48c8d7874ced19ae7f07f39415144ce8e448b5572b59`**; AUDIT **`32dbff8e62f2d079c53ece43f8f0b71e78b23451b0dcf22cf0d655303898a2aa`**. Every generated source JSON matches its recorded hash.
- Real CPU: Python **3.11.18**, PyTorch **2.15.0+cu132 installed, but executed on CPU**, two CPU threads, Azure-hosted Ubuntu. CPU-capable execution is not GPU execution simply because a CUDA wheel was installed.
- Reproduce locally/offline-only control: `python -m pytest -q tests/test_micro_counterfactual.py`; real model via `python scripts/micro/counterfactual_cpu_pilot.py --output-dir runs/micro-counterfactual/mini-33m` after installing project `.[generation]` plus `huggingface-hub>=0.29,<2`. Source and model license metadata checked at download.

## 4. Prior literature and claim boundaries

This research direction is **not new in the literature**. Earlier studies have explicitly examined conflicts and multiple-source answer selection:

- Cattan et al. (2025), **[(D)RAGged Into a Conflict](https://research.google/pubs/dragged-into-a-conflict-detecting-and-addressing-conflicting-sources-in-retrieval-augmented-llms/)**: taxonomy and human-labeled realistic conflicting-source situations.
- Yuan et al. (2026), **[ConfRAG: Benchmarking Reasoning over Conflicting Web References](https://aclanthology.org/2026.acl-long.11/)**: genuine multi-source contradictory web documents and structured conflict tasks.
- Setiawan (2026), **[Prompt-Based Abstention Fails Under Misleading Context](https://aclanthology.org/2026.aacl-long.153/)**: graded abstention conditions; misleading source evidence remains difficult for small frozen language models.

Our contribution **today** is an executable tiny-CPU source/evidence/cost engineering experiment with pinned checkpoints, explicit negative/contradictory labels, disclosed shortcuts and meaningful failure logs — **not** a novel science claim or a validated new benchmark. It must not be used to advertise reliable autonomous customer-facing factual QA.

## 5. Next binding research gates

**MICRO-CF-02 — Truly new independent documents:** source original human-written content in two or more realistic domains (with explicit rights) and blind double-reviewer item labels. Vary question paraphrases, document styles, author/source authority, timestamps, unknown entities, wrong-entity distractors and mutually contradictory evidence. Keep a genuinely sealed source-grouped test cohort; do not inspect audit labels then tune prompts/guards on that same test.

**MICRO-CONFLICT-02 — General conflict detection under CPU budgets:** predeclare compact NLI/claim normalization approaches and compare them to a transparent minimal rules baseline. Require evidence alignment and document identity checks; count **whole-stack** source search, extraction, detection and abstention costs. Detect missing/contradictory evidence **before** answer publication. The present post-hoc template regex is only a development reference and must be tested against unseen linguistic styles before shipping.

**MICRO-CAL-02 — Selective QA with actual utility:** train refusal thresholds **only** on calibration, measure correctness versus false-accept risk/coverage and the confidence bounds from adequately sized independent groups. Refuse-all must never win an answer-quality leaderboard. Incorporate an explicit `CONFLICT` result type rather than conflating contradictory and missing information.

**MICRO-EFF-02 — Minimal total system:** compare a *zero-neural structured extraction/rules solution*, a 33M extractive reader + light symbolic consistency, a small hybrid NLI route and a suitably trained causal generator at matched task/rights/CPU settings. A 0-parameter rule may legitimately win highly structured tasks; evaluate flexibility, manual engineering cost, robustness to paraphrases and out-of-domain transfer.

**No automatic deployment/public research claim yet.** The separate GitHub Pages repository-admin blocker (#13) is unchanged. `MICRO` issue #11 remains OPEN until genuine independent external validation and non-fabricated scientific evidence exist.

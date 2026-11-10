# MICRO-RAG v0.2.0 — Frozen engineering scope and scientific release gates

**Status: engineering implementation under test, NOT reliable factual QA certified.**

This milestone implements a runnable CPU-first retrieval → extraction → source-consistency → decision pipeline. The current narrowly structured demonstrator is a useful software baseline, not a general RAG intelligence result.

## Output contract

| Decision | Invariant | Automatic factual answer |
| --- | --- | --- |
| ANSWER | The named entity/property has one consistent literal value across the bounded complete same-entity structured-source scan, exact source offsets and SHA verified | Yes, only for literal structured documents |
| CONFLICT | Two distinct sources for the same exact entity/property contain different literal values | No |
| INSUFFICIENT | No extractable candidate from the requested entity/property | No |
| REVIEW | Incomplete source scan, malformed source, invalid reader output or model-extractive result without independent semantic validation | No |

A direct quote with a valid citation proves only where the text came from. It is **not** semantic entailment and does not establish truth, authority or temporal precedence. No random document may be cited, and no model text can receive automatic factual ANSWER until independently verified.

## Implemented first deliverable

- Reuses the existing BM25 retrieval and existing exact-offset MiniLM span decoder, with an optional local-only CPU extractive model adapter.
- Transparent zero-neural-model structured baseline for explicit entity/field:value records; recognizes a small documented alias list only, not arbitrary narrative facts.
- Questions naming two different stations, unsupported properties, unknown entities or missing values cannot produce ANSWER.
- Bounded full same-entity scan avoids top-k=1 concealing another structured contradictory source. Malformed or unattributed records, ambiguous entity declarations and overflow become REVIEW; they may not be silently omitted.
- Any malformed nonempty key/value line rejects the whole structured record rather than allowing a false completeness claim.
- Unsupported entity/property questions return REVIEW, not false INSUFFICIENT. Only fully attributed recognized structured lookups can report INSUFFICIENT.
- Optional neural top-k extraction returns REVIEW even with no extracted span, because partial retrieval cannot establish global absence.
- Each claim carries source ID, original offsets, exact substring and document SHA256. The citation and claim are revalidated before output.
- Decision audit carries timings for retrieval, source scan, reading, adjudication and total; reader call counts and accepted/refused states.
- Local JSON CLI and nine entirely fictional software cases. No paid API, hosted agent, real client data, or private credentials involved.

### Reproduce

Install Python 3.11 and the repository project with development extras. From repository root:

    python -m pip install -e ".[dev]"
    python -m pytest -q tests/test_micro_v02.py
    python -m raglab.micro_v02 ask --documents examples/micro-v02/documents.json --question "What is the start year for Station Aurora?"
    python -m raglab.micro_v02 evaluate --documents examples/micro-v02/documents.json --cases examples/micro-v02/cases.json --output runs/micro-v02/evaluation.json

The first query should give CONFLICT and NO answer; two source citations will expose 2012 vs 2015 as fictional examples. Full structured software fixture should pass 9/9. **This is not independently heldout evidence**: its data and labels were created together with the implementation.

For optional local model inference install the generation extras, download a reviewed pinned safetensors checkpoint with its license and hashes separately, and run the CLI with --reader extractive --model-directory PATH. Extractive outputs remain REVIEW unless separately verified and calibrated.

## M0–M6 implementation gates

| Stage | Deliverable | Verification |
| --- | --- | --- |
| M0 | Frozen contract, baselines, targets, evaluation leakage rules | SPEC, tests and review |
| M1 | Ragability source vs oracle short/long answer normalization | Exact external dataset/revision, no test fitting or oracle deployment claims |
| M2 | Source-aware verifier on realistic contradictory documents | Non-template conflict inference, authority/date/source identity, reported false positives |
| M3 | Local runnable full RAG pipeline | Complete retrieval → reader → consistency → refusal, CLI and adversarial E2E tests |
| M4 | Independent QA risk/coverage and confidence bounds | At least 300 **real human-labeled** questions over >=2 domains, two reviewers and adjudication, independent group-wise frozen test |
| M5 | Real CPU performance and quantized parity | Full-stack p50/p95, RAM, disk, initial indexing, INT8/ONNX versus unquantized model with quality parity check |
| M6 | Reproducible research artifact | Accessible source, pinned experiments, source provenance, recorded negative results and external reproduction |

**Verified 2026-11-10 engineering status:** M0 contract and structured M3 E2E software tests PASS (PR #29); M1 author-answer oracle CPU executed (PR #30; *not end-to-end extraction*); M2 partial NLI diagnostics integrated and fail closed (PR #31); M4 reviewer metadata/cluster-risk evaluator implemented but real human dataset OPEN (PR #32); M5 verifier-only pinned PyTorch/ONNX INT8 CPU parity PASS (PR #33; [results](MICRO_V02_ONNX_RESULTS.md)), yet repeated isolated CPU and full-stack hardware evaluation OPEN; M6 independent reproduction OPEN. **None of these verifies independently reliable natural-language RAG.**

## Target scientific thresholds — hypotheses, not achievements

- >=300 newly human-labeled QA items, >=2 realistic domains, independent document-group splits and two distinct real reviewers per item with adjudication. Synthetic labels do not count.
- Wrong accepted response rate target <=5% and **group-aware 95% CI upper bound <=10%**, frozen in advance. If effective sample size is too small, no certification.
- Conflict recall >=90% while controlling false positives; correct answerable coverage >=60% (refuse-all must fail).
- CPU reference target on a defined small indexed corpus: p95 <=2 seconds, process peak RSS <=4 GiB; include retrieval, tokenization, verification and decision, separate initial loading and indexing.
- Audit reported on one untouched source-grouped evaluation run, without choosing thresholds/prompts or model variants after seeing the result.

These are proposed acceptance criteria, not measured model performance. An independent reviewer dataset cannot be fabricated by writing LLM-generated examples; until one exists, label the milestone SCIENCE NO-GO.

## Future comparison policies

Compare the current structured rules baseline against BM25 top1/top3 + MiniLM-33M, small NLI verification (MiniLM2 and DeBERTa), hybrid verification, and refuse-all, under comparable task/data budgets and documented training differences. Never call a SQuAD2 fine-tuned encoder fairly superior to untuned causal LMs.

Original external Ragability NLI results (both 82.08% pairwise accuracy, no clear overall winner) remain diagnostic only, and their source/test groups must not be used for tuning. ConfRAG and independent human review remain next experiments.

## Research scope and reporting boundaries

No production deployment or unrestricted autonomous answer publication is evaluated here. Report only tested behaviors, with explicit dataset/model limits and no unsupported claim of hallucination-free output. Public web hosting is outside the scientific acceptance criteria.

References: [v0.2 GitHub issue #28](https://github.com/AlexiVion/rag-architecture-lab/issues/28), [MICRO science issue #11](https://github.com/AlexiVion/rag-architecture-lab/issues/11), [prior external NLI results](MICRO_RAGABILITY_NLI_RESULTS.md).

# V2 — Grounded Generation, Context Construction, and Citations

## Research question

> **Can the retrieval system be extended into a fully local RAG pipeline that produces evidence-grounded answers with explicit, machine-checkable citations?**

V2 is the first stage where the lab moves beyond retrieval quality into answer generation.

The goal is not to maximize language-model quality. The goal is to make the generation layer inspectable and to preserve a clear chain from retrieved document -> context source -> answer citation.

## Architecture

```text
Question
   |
   v
Retriever
   |
   v
Top-K ranked documents
   |
   v
Context Builder
   |
   +--> [S1] document A
   +--> [S2] document B
   +--> [S3] document C
   |
   v
Local instruction model
   |
   v
Answer with inline citations
   |
   v
Citation integrity validator
```

The default retrieval path remains Hybrid RRF. The optional quality mode uses the 10-candidate cross-encoder configuration selected in V1.1.

## Context contract

The context builder assigns stable source labels in retrieval order:

```text
[S1]
doc_id: ...
title: ...
text: ...
```

The prompt requires the generator to cite only those labels and to state when the retrieved evidence is insufficient.

Context size is bounded explicitly. This keeps the experiment reproducible and prevents an accidental increase in context size from being confused with an architectural improvement.

## Generation provider

V2 uses a local Hugging Face Transformers model by default:

`Qwen/Qwen2.5-0.5B-Instruct`

The model is a dependency, not an implementation claim. The RAG orchestration, retrieval, context construction, source mapping, citation contract, validation, and timing instrumentation are implemented in this repository.

The default is intentionally small enough to run on the designated CPU machine without a paid API. The model can be replaced through the CLI for later experiments.

## Citation integrity vs. semantic faithfulness

V2 deliberately separates two concepts.

### Citation integrity — deterministic in V2

The validator can check:

- whether cited labels exist in the supplied context;
- how many citations are valid or invalid;
- what fraction of generated sentence-like units contain at least one valid source label.

These checks are deterministic and do not require another LLM.

### Semantic citation support — not yet claimed

A syntactically valid citation does **not** prove that the cited passage actually entails the generated claim.

V2 therefore does not call citation validity a faithfulness score. Semantic support evaluation is a later experiment and may use reference answers, NLI, claim decomposition, or controlled model-based judging.

## Initial operating modes

```text
Fast/default:
Dense + BM25 -> RRF -> top 5 -> context -> local model -> answer + citations

Quality/optional:
Dense + BM25 -> RRF -> top 10 -> cross-encoder -> top 5 -> context -> local model -> answer + citations
```

## V2 smoke-test success criteria

The first local V2 run is successful if:

1. the corpus indexes successfully;
2. a benchmark query retrieves context;
3. the local generator returns an answer;
4. inline source labels can be parsed;
5. invalid citations are reported rather than silently accepted;
6. retrieval, context, generation, and total latency are recorded;
7. no paid API is required.

Passing this smoke test means the architecture works. It does **not** yet mean generation quality has been benchmarked.

## Next experiment after the smoke test

Once local execution works, V2.1 should define a small controlled generation benchmark. It should compare at least:

- Hybrid RRF vs. Hybrid + optional reranking;
- answer correctness against a reference or task label where available;
- evidence availability in retrieved context;
- citation integrity;
- semantic faithfulness/support;
- end-to-end latency.

Generation metrics must not be invented or inferred from retrieval scores.

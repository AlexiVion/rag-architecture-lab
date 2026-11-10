# PAPER-01 / P2: real ConfRAG viewpoint-cluster CPU diagnostic — frozen before execution

**Date:** 2026-11-10. **Status:** PUBLIC-DEVELOPMENT EXPERIMENT, not external independently double-human-certified validation. **Results:** PENDING until exact-head model execution and artifact inspection.

## Scientific motivation and label validity

[ConfRAG](https://huggingface.co/datasets/OracleY/ConfRAG) (Yuan et al., ACL 2026, 1,814 questions, CC BY 4.0) contains 3–10 real web pages per question, **author-provided per-website answer extraction** and **author-annotated answer viewpoint clusters**. Its README recommends `ConfRAGsuggested.jsonl`.

**Essential distinction:** two different annotated viewpoints need not logically contradict (e.g., two complementary partial answers). The `contradicts` flag is a question-level coarse annotation; cluster difference is a pairwise perspective-group **disagreement proxy**, not a ground-truth textual contradiction. The NLI classifier's "contradiction" label is compared as a deliberately imperfect proxy for this target. Report false positives and negatives, never rename these scores "contradiction recall" or "true factual support".

The source annotations include LLM-based extraction and human-in-the-loop clustering, not **two independently recruited reviewers of our evaluation**. We cannot convert these to an independently reviewed, held-out experiment.

## Frozen development selection

- On execution, resolve the Hugging Face dataset to its complete commit SHA and validate license `cc-by-4.0`, then **stream only the prefix** of recommended file at that exact SHA, reading at most **128 source JSONL rows**, 8 MB per line and 110 MB total. Do not download all 599 MB or upload copyrighted web content.
- From source order choose the first 8 eligible `contradicts=true` and first 8 `false`, so **16 source-question groups**. Group selection is *order-biased*, not randomized, and source labels are public. All pairs in the same question belong to one group.
- Use at most six sites per group, first ordered by source index. Only sites with nonempty author-provided answer string (length 4–500) and unique membership in exactly one published answer cluster qualify. Exclude ambiguous and duplicated indexed sources. Record exact IDs, raw row SHA256, content-derived pair hashes and dataset revision. The whole-file SHA256 is **not computed**, as the stream stops early.
- Pairs of qualifying sites have label **same/different annotated viewpoint cluster** based on equality of the cluster ID; pair sample sizes vary by group.
- Fixed control: lowercased alphanumeric-token **Jaccard of answer texts only**; predict different if Jaccard less than 0.50. The question prefix must be excluded from Jaccard.
- Fixed model: `cross-encoder/nli-deberta-v3-xsmall` at exact revision `a150876415327c80daeff35ca6f68f5ed8cf5c24`, license Apache 2.0, approximately **70.8M** parameters, off-the-shelf SNLI/MultiNLI task. Author-extracted short answers are rendered as `Question: ...\nAnswer: ...`; score forward and reverse NLI separately, average softmax probabilities, predict **different cluster** only if `contradiction` is the three-way argmax. Do not fit a new threshold from the DEV cases.
- Report the same **pair-level** confusion matrix, accuracy, balanced accuracy, precision, recall, F1 for lexical control and model on *identical* pairs. Include denominators, **number of source-question groups**, the real model's batched CPU timing, weights and artifact hashes. This diagnostic CPU time is **not** complete RAG latency.
- Note: all compared question/answer strings come from a published dataset's privileged author-provided site answers, **not** outputs automatically extracted by our RAG. A 33M extractor is therefore not present in this stage, despite the overall PAPER-01 goal. Do NOT add 33M to the parameter total or label this an end-to-end <=135M RAG experiment.

## Fail/stop conditions

- Dataset license/file missing, unexpected file shape/length, insufficient 8+8 groups, duplicate pair ID, wrong NLI label order, wrong model revision, excessive downloaded prefix or model size: **fail without fabricated results**. CI failure is a real blocker, not permission to manually invent/patch the output.
- Dataset revision is resolved during this *first DEV discovery*, saved in the artifact; full repeatability requires subsequent runs to use that explicit SHA and check the selected input hashes. These rows are **not** a sealed confirmatory test.
- No paper novelty from beating a weak lexical control; report lack of benefit or higher error rates equally. This is a diagnostic follow-up to existing Ragability NLI external results, not a new annotation set.
- Underpowered sample, non-independent pairs within questions, chance of dataset duplication/pretraining overlap and answer extraction as a privileged oracle all preclude reliable statistical inference.
- The next valid stage is **end-to-end** 33M QA extraction on real retrieved documents, followed by calibrated small verifiers and the separate two-domain blinded human-reviewed evaluation. See [PAPER-01 master protocol](PAPER_01_MICRO_CPU_FRONTIER_PROTOCOL.md) and [issue #39](https://github.com/AlexiVion/rag-architecture-lab/issues/39).

## Reproduce

```sh
python -m pip install -e ".[generation,dev]" "huggingface-hub>=0.29,<2"
python -m pytest -q tests/test_confrag_viewpoints.py
python scripts/micro/confrag_viewpoint_nli_cpu.py --output-dir runs/paper01/confrag-nli-dev01 --per-stratum 8 --scan-limit 128
```

Requires first-time download of public dataset *prefix* and a pinned open-weight NLI model; then runs model on CPU with two threads. Artifacts contain numeric metrics, per-pair predictions and hashes only, not full web text or weights. Cite the dataset authors and model license. No paid API keys.

**Paper submission gate:** NONE OF THIS on its own constitutes independent evidence of reliable RAG or a unique discovery. Remain research OPEN.

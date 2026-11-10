# MICRO-RAG M5 — DeBERTa-v3-xsmall ONNX INT8/FP32 parity protocol

**Experimental status:** not a product or scientific certification.
The first goal is a matched execution of one small NLI checkpoint using PyTorch FP32 and the publisher's existing ONNX AVX2 INT8 export, over the exact same **318 derived Ragability source-pair cases in 43 conflict groups**.

## Frozen inputs and checkpoints

- Dataset `ofai/RagabilityCorpus`, immutable revision `2251634ed365bfca55e7d808290b0cf2c5fde730`, source TSV SHA256 `e973f5ac7b4881e2cafe23f39b837643878ea6afdb769d9afa30ff66e93c8285`, license CC-BY-SA-4.0.
- Model `cross-encoder/nli-deberta-v3-xsmall`, immutable revision `a150876415327c80daeff35ca6f68f5ed8cf5c24`, Apache-2.0. Exact model class order verified before inference.
- FP32 source safetensors, exact hash emitted by the downloader, approx. 283 MB.
- Published `onnx/model_quint8_avx2.onnx`, **SHA256 `21b14751a95520953bfcc607ceeb617de7cbeaeb6d60f4c8966716c743985337`** (published by original model author; verified against downloaded bytes). Approx. 87.4 MB. This is an externally published quantized export, **not a model we trained or quantized ourselves**.

## Comparison protocol

- Same dataset, same tokenizer, same CPU process, same two directional premise/hypothesis inputs and softmax-mean aggregation, fixed threshold-free class mapping.
- Run all 318 original pair cases with 636 directed inputs each.
- Two PyTorch CPU threads; ONNX Runtime CPUExecutionProvider, intra-op 2 / inter-op 1; batch size 16 unordered pairs.
- Warm each backend before timing. Record tokenization + model forward + softmax wall time, token counts, batch p50/p95, actual checkpoint bytes, exact file hashes, process-wide peak RSS.
- Compare per-case class agreement, accuracy, balanced accuracy, contradiction recall and false-positive conflict calls.
- **Preset development-quality tolerance**: INT8 accuracy regression no worse than 2 percentage points AND contradiction recall regression no worse than 5 percentage points against same FP32. This is an engineering policy, **not a valid statistical guarantee**. Never select parameters on the test output.
- No automatic promotion to a production NLI verifier. Public Ragability benchmark is small and exposed; the 318 derived pairs are not independent examples.

## Limitations

These sequential runs share the same process, model cache, Python runtime and high-water RSS. Timing may be affected by fixed execution order and GitHub-hosted CPU differences, so **speed and memory superiority are not established from a single run**. This is verifier-only; retrieval, claim extraction, answer generation and end-to-end RAG costs are absent.

If quality regresses, record a **NO-GO** rather than silently tolerating model changes. If quality is retained, repeat latency/RSS on isolated repeated processes on the target Ryzen laptop or equivalent CPU before claiming end-to-end efficiency.

## Reproduce

```sh
python -m pip install -e ".[generation,dev]" "onnxruntime>=1.19,<2" "huggingface-hub>=0.29,<2"
python -m pytest -q tests/test_micro_v02_onnx_parity.py
python scripts/micro/onnx_nli_parity_cpu.py --output-dir runs/micro-v02-onnx/deberta-xsmall --batch-size 16
```

No paid API, private customer data or external model weights are uploaded to GitHub artifacts.

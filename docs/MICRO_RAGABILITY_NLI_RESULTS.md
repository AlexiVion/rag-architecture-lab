# MICRO-RAGABILITY-01 — Small NLI models on an external conflict benchmark

**Execution:** 2026-11-10 UTC, GitHub-hosted Ubuntu CPU  
**Verdict:** **REAL CPU PAIRWISE-NLI PASS / NO OVERALL MODEL WINNER / END-TO-END RAG NOT VALIDATED**  
**Decision:** keep DeBERTa-v3-xsmall as the stronger *implicit-conflict candidate* for the next ablation, not as a selected production verifier. Its higher recall comes with more false positives, and both tested models fail two of three generic sanity controls.

## 1. Research question

Can a compact, off-the-shelf natural-language-inference (NLI) cross-encoder detect conflicting evidence between retrieved snippets, including conflicts that require reasoning beyond a direct lexical mismatch?

The previous MICRO-CF synthetic corpus demonstrated a serious failure mode: a SQuAD2 extractive reader answered conflicting sources as though they agreed, while the artificial templates were vulnerable to regular-expression shortcuts. This experiment replaces those generated examples with a published external benchmark.

**Scope:** pairwise contradiction classification between context snippets. It deliberately does **not** measure retrieval, claim extraction, answer generation, source authority, refusal calibration, or full RAG utility.

## 2. External benchmark and provenance

Dataset: [OFAI Ragability Corpus](https://huggingface.co/datasets/ofai/RagabilityCorpus), version Dataset_v0.4.tsv, immutable revision:

    2251634ed365bfca55e7d808290b0cf2c5fde730

- 53 published rows, 43 unique contradiction_ID groups.
- Original empirical basis: WikiContradict, a benchmark with 253 human-annotated real-world Wikipedia conflict instances. The Ragability authors selected 43 distinct implicit-conflict context pairs and adapted them, including replacing entities and some dates/numbers with fantasy values so models cannot simply recall the original facts.
- The Ragability corpus contains 53 rows because some of the 43 context pairs have query or context variants. Therefore the independent resampling unit is the original contradiction_ID group, **not** each row or each derived pair.
- License verified against the pinned dataset card: **CC-BY-SA-4.0**.
- One row has a blank optional WikiContradict_ID cross-reference. It is preserved and counted; no missing source ID is fabricated.
- Dataset file SHA256: **e973f5ac7b4881e2cafe23f39b837643878ea6afdb769d9afa30ff66e93c8285**.

The published relations are: c1/c2 conflict; c2/c3 conflict; c1/c3 do not conflict; and c1/c4, c2/c4, c3/c4 do not conflict. This gives six pair types per row:

| Pair | Expected label | Cases |
|---|---|---:|
| c1/c2 | contradiction | 53 |
| c2/c3 | contradiction | 53 |
| c1/c3 | non-contradiction | 53 |
| c1/c4 | non-contradiction | 53 |
| c2/c4 | non-contradiction | 53 |
| c3/c4 | non-contradiction | 53 |
| **Total** | **106 contradiction / 212 non-contradiction** | **318** |

The original c1/c2 relation is the harder implicit case: the individual snippets are not themselves contradictory; the conflict emerges when the two snippets are considered together. Context 3 creates a more overt conflict with context 2 while remaining compatible with context 1. Context 4 is compatible with all the others.

**Important boundary:** this is a public, exposed, author-adapted benchmark with human-annotated empirical origins. It is not a sealed holdout, not newly double-reviewed by this project, and not 318 independent human judgments.

References:
- Gross, Petrak & Krenn, [Ragability: A Benchmark for Evaluating the Ability of LLMs to Identify Knowledge Conflicts](https://aclanthology.org/2026.lrec-1.182/) (LREC 2026).
- [Official dataset card, schema, empirical basis and license](https://huggingface.co/datasets/ofai/RagabilityCorpus).
- [Reference implementation](https://github.com/OFAI/python-ragability).

## 3. Registered models and inference

Two public English NLI cross-encoders, both trained on SNLI and MultiNLI, were pinned and run separately on CPU.

| Model | Exact revision | Parameters | Safetensors bytes | License |
|---|---|---:|---:|---|
| cross-encoder/nli-deberta-v3-xsmall | a150876415327c80daeff35ca6f68f5ed8cf5c24 | 70,831,107 | 283,353,172 | Apache-2.0 |
| cross-encoder/nli-MiniLM2-L6-H768 | b95119ce93d3e065de6214e38cd4a97b0f2f2c6d | 82,120,707 | 328,499,560 | Apache-2.0 |

Model weight SHA256:
- DeBERTa: 4e4fc4977f8d29d2a164255c8f69b9d6c158deeb309bb5e70445b94666ccd9e9
- MiniLM: ec9c5b6a08b60d7a01b465c7ed44b496244dfd1bed3274c95875a74cea89ab35

For each pair, both directions are evaluated (A as premise/B as hypothesis and then reversed). Three-class softmax probabilities are averaged, then the symmetric NLI class is mapped to a binary decision: contradiction if contradiction is the highest symmetric score; otherwise non-contradiction. This aggregation was fixed before model execution; no threshold or prompt was tuned on Ragability. Directional predictions and disagreement are retained.

The model output scores are **not calibrated probabilities of a factual conflict**. The symmetry operation is a diagnostic, not a proven optimal NLI aggregation.

## 4. Main results

<text>Each model classified the same 318 pairs. Both achieved the same raw accuracy, but their error profiles differ.</text>

| Metric | DeBERTa-v3-xsmall | MiniLM2 |
|---|---:|---:|
| Accuracy | **82.08% (261/318)** | **82.08% (261/318)** |
| Balanced accuracy | **80.19%** | **78.07%** |
| Macro F1 | **79.97%** | **79.04%** |
| Contradiction precision | 72.48% | **76.92%** |
| Contradiction recall | **74.53%** | 66.04% |
| Contradiction F1 | **73.49%** | 71.07% |
| Non-contradiction false positives | 30/212 | **21/212** |
| Missed contradictions | **27/106** | 36/106 |
| Forward/reverse binary agreement | 82.39% | **85.85%** |

### By relation type

| Relation | DeBERTa | MiniLM2 | Interpretation |
|---|---:|---:|---|
| c1/c2 — implicit conflict | **35/53 (66.04%)** | 24/53 (45.28%) | DeBERTa is materially better on the hardest original relation |
| c2/c3 — overt conflict | 44/53 (83.02%) | **46/53 (86.79%)** | MiniLM is slightly better on this easier conflict |
| c1/c3 — compatible | 39/53 (73.58%) | **43/53 (81.13%)** | DeBERTa over-triggers more often |
| c1/c4 — compatible | 49/53 (92.45%) | **50/53 (94.34%)** | Both strong |
| c2/c4 — compatible | 50/53 (94.34%) | **51/53 (96.23%)** | Both strong |
| c3/c4 — compatible | 44/53 (83.02%) | **47/53 (88.68%)** | MiniLM is more conservative |

DeBERTa detects 11 more of the 53 implicit c1/c2 conflicts, but also raises nine more false-positive conflict labels across the 212 non-conflicting pairs. MiniLM is more conservative; DeBERTa trades some precision for recall.

### Matched model comparison — source-group bootstrap

A separate paired analysis compares both fixed prediction sets using the same 43 contradiction_ID groups resampled together (10,000 repetitions, seed 20261109). Positive values mean DeBERTa minus MiniLM.

| Metric difference | Point estimate | Paired 95% group-bootstrap interval |
|---|---:|---:|
| Accuracy | +0.05 percentage points | [-3.46, +3.92] pp |
| Balanced accuracy | +2.17 pp | [-2.23, +6.94] pp |
| Macro F1 | +1.00 pp | [-3.03, +5.60] pp |

**No overall winner is established:** all three overall intervals include zero. The models also have 20 cases each where only that model is correct, and agree on correctness for 278/318 pairs.

For the original c1/c2 implicit-conflict subgroup, the paired DeBERTa-minus-MiniLM detection-rate difference is **+20.62 pp**, with a group-bootstrap 95% interval of **[+3.92, +38.18] pp**. This is a useful exploratory subgroup signal, but it is based on only 53 derived cases, has no multiple-comparison correction, and does not justify a broad model-superiority claim.

### Sanity-control warning

Both models passed only **one of three** generic NLI sanity controls under the symmetric aggregation:
- generic entailment → predicted neutral;
- generic contradiction → predicted contradiction;
- generic neutral → predicted contradiction.

This is a significant warning. The models' benchmark accuracy must not be interpreted as a general semantic-conflict capability certificate. In particular, the neutral-to-contradiction error is consistent with the higher false-positive rate observed for DeBERTa.

## 5. Real CPU costs

Separate GitHub-hosted Ubuntu CPU jobs; two PyTorch CPU threads; the same 318 pair cases and 636 directional model inputs.

| Cost | DeBERTa-v3-xsmall | MiniLM2 |
|---|---:|---:|
| Model weights | 283.35 MB | 328.50 MB |
| Directional pair inputs | 636 | 636 |
| Forward batches | 20 | 20 |
| Token count | 42,432 | 45,344 |
| Total batch wall time | **19.09 s** | 20.27 s |
| Mean per directional input | **30.02 ms** | 31.87 ms |
| Peak process RSS | 1.741 GB | **1.613 GB** |

These measurements include tokenization, CPU forward and softmax in batches. They are not pure neural-forward latency, not a complete RAG response time, and not energy measurements. The exact CPU SKU is not guaranteed by GitHub-hosted runners. PyTorch was installed as a CUDA-enabled wheel but these jobs executed on CPU only.

DeBERTa used approximately 13.7% fewer weight bytes and was about 5.8% faster on this one benchmark run, but had a higher process peak RSS. This is not sufficient evidence of a universal speed or memory advantage.

## 6. Integrity and exact execution

- Code [PR #26](https://github.com/AlexiVion/rag-architecture-lab/pull/26) merged to main as **5b751d2dbadff32e1fcd338c7dd814f0066839b8**.
- Exact model-evaluation source head: **d1d37fa0acafbd06e2af7e501987ca4ad6e03812**.
- [Offline Python/TypeScript/Chromium CI #42735349153](https://github.com/AlexiVion/rag-architecture-lab/actions/runs/42735349153): **SUCCESS**.
- [Both real CPU model jobs #42735349293](https://github.com/AlexiVion/rag-architecture-lab/actions/runs/42735349293): **SUCCESS**.
- Dataset SHA256: e973f5ac7b4881e2cafe23f39b837643878ea6afdb769d9afa30ff66e93c8285.
- Dataset manifest SHA256: 6e18b48e0090d13a15e50a5c903e7247f2977dc28359950d99b983e5ac630a15.
- DeBERTa result JSON SHA256: 56d670af421f36f7e8dbe583876ad791783f1f0068b131c9eac5e2146ee4489e.
- MiniLM result JSON SHA256: 774aad5ddc096227a6be0bf490a5ed63baeff07657582e483c554b0cf1eeb973.
- DeBERTa artifact ID 13726542626; ZIP SHA256 1014841edfaa9bf7d8b7f80f321fcffd792e61c918af64475ba9c61858c6cbf7.
- MiniLM artifact ID 13726578149; ZIP SHA256 74123d84e093e91011c0eb81d8ac996c97f0d76a75b796d80652c1faabd02008.

Artifacts contain only source identifiers, SHA256 fingerprints, model outputs and metrics; **no raw CC-BY-SA dataset text or model weights are redistributed**. The exact dataset license and model licenses were checked against their pinned cards.

## 7. Scientific decision and next experiments

**Decision:** off-the-shelf NLI is a promising lightweight component for conflict detection, but not a standalone source arbiter. Neither model is a production-ready factual verifier. The overall paired comparison does not select a winner. DeBERTa is a candidate for the implicit-conflict follow-up, but its higher false-positive rate and sanity-control failures must be addressed.

### MICRO-RAGABILITY-02 — Oracle claim normalization

The published Ragability file provides both short and long context-specific answers. This allows a useful diagnostic:
1. run NLI on raw source contexts (already measured);
2. run NLI on the authors' short answer pair;
3. run NLI on the authors' full answer-claim pair;
4. optionally prefix both claims with the same question.

This is an **oracle ablation**, because answer extraction is supplied by the benchmark authors. It is not an end-to-end system result. If long answer claims substantially improve contradiction detection, the bottleneck is likely claim extraction/normalization; if not, the NLI verifier itself remains weak. Keep all variants grouped by the same 43 contradiction IDs.

### MICRO-EFF-03 — Quantized CPU inference

The DeBERTa model repository publishes an AVX2 quantized ONNX file, model_quint8_avx2.onnx, approximately 87.4 MB. Compare it against the pinned FP32 PyTorch checkpoint on the exact same benchmark, measuring prediction parity, conflict recall/false positives, latency, RSS and end-to-end tokenization/runtime. Do not assume quantization preserves quality without testing.

### MICRO-CONFLICT-03 — Real-web multi-source evaluation

Move beyond short adapted snippets to ConfRAG, an ACL 2026 benchmark with 1,814 questions and an average of 9.58 retrieved paragraphs per query. Its answer-cluster and reason-coverage structure is a better next test for multi-source reasoning, but its data provenance and source-site reuse rights must be respected.

### No deployment

Do not automatically publish answers based on these results. Before production use, require query-aware evidence selection, claim extraction, source identity/authority/recency checks, independently human-reviewed multi-domain test data, calibration with nonzero useful coverage, and full-stack CPU measurements.

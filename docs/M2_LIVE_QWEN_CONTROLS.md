# M2-LIVE-01 — Real Qwen citation/abstention controls (no API)

**State:** Code and synthetic tests added, **real model result not yet run**. These are original fictional fixtures and are not part of SciFact TRAIN/DEV/TEST or HotpotQA cohorts. No weights, source texts or prior benchmark results are modified.

## Objective and experimental boundaries

A compact **operational boundary smoke** for the actual `RAGPipeline` + `LocalTransformersGenerator`, not a semantic faithfulness benchmark:

| Case | Fixed supplied evidence | Predeclared expected behavior | What is automatically verified |
|---|---|---|---|
| `answerable_supplied_evidence` | One fictional engineering document stating a maker | Answer with a source citation | Public answer must pass existing citation syntax gate, or be rejected. A separate string-presence diagnostic is reported but never labeled scientific correctness. |
| `irrelevant_nonempty_evidence` | An unrelated fictional mission document | Abstain | Observe output and cite status. **No automatic correctness judgment**; existing RAG runtime has no calibrated semantic evidence adequacy gate. |
| `contradictory_evidence` | Two explicitly conflicting fictional launch dates | Abstain or explicitly discuss conflict | Observe output and citation syntax. Correct contradiction handling is **unreviewed**, not automatically inferred from a citation. |
| `empty_retrieval` | No source documents delivered | Abstain | Generation calls **zero**, status `abstained_no_context`, generation time zero. |

Fixed sources isolate **generation/publication behavior** from retrieval quality: these are *not* retrieved by Hybrid RRF, and they must never be presented as end-to-end retrieval scores. The exact predeclared fixture is recorded by SHA-256. All candidate generations and original evidence remain under gitignored local `runs/m2-live/`, not in the public explorer. The no-context behavior and public citation gate are deterministic *program* properties, not claims of an infallible LLM.

The model `Qwen/Qwen2.5-0.5B-Instruct` is run locally on CPU with greedy decoding and up to 128 tokens per case; its resolved commit is saved if the local runtime exposes it. This first smoke **does not enforce a pinned Qwen revision** and is therefore not a frozen/held-out performance comparison. A strict revision and a separate correctly labeled TRAIN/DEV answer benchmark remain future M2 gates.

## Run once on Windows

From the repository root:

```powershell
.\scripts\run-m2-live-controls-local.ps1
```

It first runs the **complete pytest suite**, then executes three real-generator calls plus one no-context skip. It prints each case's actual `output_status` and citation-contract result, while retaining raw generations and source mappings in a timestamped local JSON+Markdown. Repeating after a successful saved run refuses silent reruns. No prompts to the operator.

**DO NOT claim M2 is closed or semantically perfect from this smoke.** Model answers can be cited but irrelevant, unsupported, inconsistent or wrongly confident. Independent human or independently validated answer-quality labels, correct abstention rates, and a genuinely untouched evaluation set are required to close M2.

Historical context: the previous SciFact TEST Q1 answer was off-task/uncited, and the tested off-domain NLI verifier was **NO-GO** on gold SciFact TRAIN rationales. Those results remain unchanged.

# M2-REVIEW-02 — Source relevance and claim support handoff

**Status:** new no-model reviewer-packet export; full Windows regression execution pending. **The underlying M2-LIVE-02 prompt-development data have already been exposed**, so this is a diagnostic review, not held-out scientific validation.

## Verified previous stage

At commit `c929c32`, the Windows complete pytest suite and original M2-LIVE-02 citation replay **PASS**. Original M2-LIVE-02 report SHA256:

`3c9fc0794ab2d2bd3ca10825585926083b0d40067c1696aa77fc90f230ea7816`.

Counterfactual V1 syntax pass = 0; proposed experimental V2 syntax pass = 1 (adequate-source, `Fact. [S1]`). The invented `[Solis Probe]` label and the uncited contradictory-date assertion remain rejected. No Qwen calls or publication actions occurred. The historical pipeline's original statuses are unchanged and V2 remains opt-in.

## Reviewer packets, no invented semantics

`src/raglab/evaluation/m2_review02.py` reads the original saved M2-LIVE-02 JSON **without loading any model**. It first recomputes its SHA256 and requires the exact observed fingerprint. It then invokes the existing `replay_saved_run` to verify the original prompts, evidence passages, source IDs, model and frozen draft texts. Any mismatch fails closed.

The exporter creates four unlabelled review packets under the ignored `runs/m2-review02/` folder. The packet filenames are opaque (`01_review.json` to `04_review.json`), and the case-to-scenario mapping remains in the separate provenance manifest, which should not be shown to a reviewer before annotation. Each packet includes:

- The original question, verbatim Qwen attempted answer (if any), original source document passages, stable S1/S2 labels and original pipeline output status.
- The **proposed citation V2 syntax verdict**, explicitly marked *not* a semantic support verdict.
- One claim for the adequate-source `Fact. [S1]` (not a phantom second citation-only sentence), and corresponding per-claim fields with `support=unreviewed`.
- Source relevance fields all `unreviewed`; `review.expected_behavior=unreviewed`, reviewer identifier empty, no provided semantic truth labels.
- Separate provenance showing model answer attempts vs the historical pipeline's safe refusal. **The legacy review scorer's observed behavior describes the pipeline output, not the underlying model's attempted draft.**

Because these cases were previously exposed and designed for development, any completed review here is diagnostic, not an unbiased model error rate. Do not use their labels to make new held-out benchmark claims.

## One noninteractive Windows export

From the repository root:

```powershell
.\scripts\prepare-m2-live02-review-local.ps1
```

This runs full pytest first, then verifies the original report and produces **unlabelled** packets and `manifest.json`. It prints source/claim counts and explicitly states `SEMANTIC=UNREVIEWED`. An identical rerun is idempotent; if anyone edits the packet, subsequent runs fail rather than overwrite human annotations. **No model inference, paid API, graph benchmark rerun or external publication.**

After export, a reviewer may use the already existing `raglab review-interactive --path runs/m2-review02/01_review.json --output runs/reviews/annotated_M2_R01.json` and `raglab review-score` commands. A reviewer should inspect the literal source passages before assigning relevance or support. The original packet is never to be edited or mistaken for gold data.

### Separate dimensions to annotate

1. **Source relevance:** whether the source actually discusses the requested entity/fact.
2. **Claim support:** whether the source explicitly entails, contradicts, fails to support or leaves ambiguous each attempted assertion.
3. **Expected behavior:** whether answering, abstaining or expressing uncertainty is justified by the supplied passages.
4. **Original publication decision:** the historical pipeline rejected all three drafts, and the no-context case abstained. This outcome is observed, not an independent judgment of whether the draft was semantically right.

## Proper M2 acceptance remains open

The real M2 science gate requires independently reviewed relevance and entailment labels (preferably two reviewers plus adjudication), an untouched evaluation set, source evidence sufficiency/calibrated refusal metrics and a frozen model revision. Prior off-domain SciFact NLI is NO-GO; do not elevate it to a correctness oracle. No policy promotion results from a citation parser syntax replay or from these four diagnostic packets.

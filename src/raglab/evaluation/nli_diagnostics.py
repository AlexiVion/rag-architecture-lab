from __future__ import annotations

import json
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np

from raglab.evaluation.dev_case_design import (
    ARM_ALTERNATE, ARM_EMPTY, ARM_WITH_REFERENCE,
)
from raglab.evaluation.dev_nli_pilot import (
    DEFAULT_NLI_MODEL, NLI_LABELS, _logit_probabilities,
)

CONTROL_PAIRS = (
    ("A man is eating pizza.", "A man is eating something."),
    ("A dog is asleep on a couch.", "A dog is awake on a couch."),
    ("A woman is reading a book.", "It is raining outside."),
)
CONTROL_EXPECTED = ("entailment", "contradiction", "neutral")
ARM_NAMES = (ARM_WITH_REFERENCE, ARM_ALTERNATE)


def _checked_scores(raw: Any) -> list[float]:
    if not isinstance(raw, dict) or set(raw) != set(NLI_LABELS):
        raise ValueError("Invalid NLI saved score keys")
    scores = [float(raw[name]) for name in NLI_LABELS]
    if not all(np.isfinite(scores)):
        raise ValueError("Saved NLI scores are nonfinite")
    if any(x < 0 or x > 1 for x in scores) or abs(sum(scores) - 1) > 0.001:
        raise ValueError("Invalid NLI score normalization")
    return scores


def build_nli_diagnostic(
    suite: Path,
    saved: dict[str, Any],
    probe_predict: Callable[[list[tuple[str, str]]], Any],
) -> dict[str, Any]:
    """Check archived NLI outputs and a three-pair model sanity control.

    Neither saved SciFact qrels nor toy controls establish biomedical truth.
    """
    if saved.get("dataset") != "beir/scifact/train":
        raise ValueError("Diagnosis accepts SciFact TRAIN only")
    if saved.get("experiment_id") != "M2-DEV-NLI-PILOT-01":
        raise ValueError("Not an M2 NLI pilot report")
    model = saved.get("model")
    if (not isinstance(model, dict)
        or model.get("id") != DEFAULT_NLI_MODEL
        or tuple(model.get("class_order", ())) != NLI_LABELS):
        raise ValueError("Unverified model ID/class order")
    manifest = json.loads((suite / "manifest.json").read_text(encoding="utf-8"))
    if (manifest.get("dataset") != "beir/scifact/train"
        or saved.get("corpus_fingerprint") != manifest.get("corpus_fingerprint")):
        raise ValueError("TRAIN manifest or corpus fingerprint mismatch")
    cases, rows = manifest.get("cases"), saved.get("cases")
    if not isinstance(cases, list) or not isinstance(rows, list):
        raise ValueError("Invalid saved case lists")
    if len(cases) != 18 or len(rows) != 18:
        raise ValueError("Expected exactly 18 suite/report cases")
    arm_counts = {
        arm: Counter({name: 0 for name in NLI_LABELS}) for arm in ARM_NAMES
    }
    lengths = []
    n_empty = 0
    for case, row in zip(cases, rows, strict=True):
        if (row.get("case_id") != case.get("case_id")
            or row.get("source_arm") != case.get("arm")
            or row.get("source_document_ids") != case.get("source_doc_ids")
            or row.get("query_id") != case.get("query_id")):
            raise ValueError("Saved NLI report differs from original case manifest")
        packet = json.loads(
            (suite / case["review_packet_filename"]).read_text(encoding="utf-8")
        )
        if packet.get("provenance", {}).get("dataset") != "beir/scifact/train":
            raise ValueError("Original packet is not TRAIN data")
        if case["arm"] == ARM_EMPTY:
            n_empty += 1
            if (packet.get("sources")
                or row.get("nli_prediction") is not None
                or row.get("runtime_policy") != "abstain_no_context"):
                raise ValueError("No-context control was corrupted")
            continue
        if case["arm"] not in ARM_NAMES:
            raise ValueError("Unrecognized NLI source arm")
        pred = row.get("nli_prediction")
        if pred not in NLI_LABELS:
            raise ValueError("Invalid saved prediction")
        scores = _checked_scores(row.get("softmax_scores_uncalibrated"))
        if pred != NLI_LABELS[int(np.argmax(scores))]:
            raise ValueError("NLI output class does not match logits/softmax")
        sources = packet.get("sources")
        if not isinstance(sources, list) or len(sources) != 1:
            raise ValueError("Nonempty case needs one source")
        lengths.append(len(str(sources[0].get("text", ""))))
        arm_counts[case["arm"]][pred] += 1
    if n_empty != 6 or len(lengths) != 12:
        raise ValueError("Unexpected no-context/nonempty counts")
    overall = Counter()
    for counts in arm_counts.values():
        overall.update(counts)
    if (dict(overall) != saved.get("predicted_label_counts")
        or saved.get("nli_scored_count") != 12
        or saved.get("no_context_count") != 6):
        raise ValueError("NLI aggregate totals inconsistent with archived cases")

    logits = probe_predict(list(CONTROL_PAIRS))
    probabilities = _logit_probabilities(logits, 3)
    controls = []
    for expected, vec in zip(CONTROL_EXPECTED, probabilities, strict=True):
        predicted = NLI_LABELS[int(np.argmax(vec))]
        controls.append({
            "expected_common_language": expected,
            "predicted": predicted,
            "matches": predicted == expected,
            "uncalibrated_scores": {
                name: float(vec[index]) for index, name in enumerate(NLI_LABELS)
            },
        })
    passed = all(x["matches"] for x in controls)
    all_neutral = overall["neutral"] == 12
    decision = (
        "NO_GO_BASIC_CONTROL_FAILED" if not passed
        else "NO_GO_ALL_NEUTRAL_NO_DOMAIN_VALIDATION" if all_neutral
        else "NO_GO_NO_BIOMEDICAL_CALIBRATION"
    )
    return {
        "experiment_id": "M2-NLI-DIAGNOSTIC-01",
        "dataset": "beir/scifact/train",
        "model": model,
        "status": "finished_model_sanity_not_semantic_certification",
        "per_source_arm": {
            arm: {name: arm_counts[arm][name] for name in NLI_LABELS}
            for arm in ARM_NAMES
        },
        "overall": {name: overall[name] for name in NLI_LABELS},
        "no_context_controls": n_empty,
        "all_nonempty_neutral": all_neutral,
        "control_probes": controls,
        "control_probe_passed": passed,
        "premise_char_min": min(lengths),
        "premise_char_max": max(lengths),
        "truncation_note": (
            "Character lengths are diagnostic, not tokenizer token counts. "
            "The NLI maximum is 512 tokens; some original passages may be truncated."
        ),
        "decision": decision,
        "biomedical_accuracy": None,
        "abstention_threshold": None,
        "explanation": (
            "Toy controls only check basic classifier response. "
            "All results are exploratory and cannot validate biomedical entailment, "
            "calibrate live abstention or serve as human-reviewed labels."
        ),
    }


def diagnostic_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# M2 NLI pilot diagnosis",
        "",
        "Decision: **" + report["decision"] + "**",
        "",
        "| Source arm | Contradiction | Entailment | Neutral |",
        "|---|---:|---:|---:|",
    ]
    for arm, counts in report["per_source_arm"].items():
        lines.append(
            f"| {arm} | {counts['contradiction']} | "
            f"{counts['entailment']} | {counts['neutral']} |"
        )
    lines += [
        "",
        "## Simple model controls",
        "",
        "| Expected class | Predicted | Match |",
        "|---|---|---|",
    ]
    for item in report["control_probes"]:
        lines.append(
            f"| {item['expected_common_language']} | "
            f"{item['predicted']} | {item['matches']} |"
        )
    return "\n".join(lines + [
        "", "## Limitations", "", report["explanation"],
        report["truncation_note"], ""
    ])

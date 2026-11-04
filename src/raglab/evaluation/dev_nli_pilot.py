from __future__ import annotations

import json
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np

from raglab.datasets import BenchmarkDataset
from raglab.evaluation.dev_automatic_audit import audit_dev_suite

DEFAULT_NLI_MODEL = "cross-encoder/nli-MiniLM2-L6-H768"
NLI_LABELS = ("contradiction", "entailment", "neutral")
Predictor = Callable[[list[tuple[str, str]]], Any]


def _logit_probabilities(raw: Any, count: int) -> np.ndarray:
    logits = np.asarray(raw, dtype=np.float64)
    if logits.shape != (count, 3):
        raise ValueError(f"NLI prediction shape {logits.shape} != {(count, 3)}")
    if not np.isfinite(logits).all():
        raise ValueError("NLI logits include nonfinite values")
    logits -= np.max(logits, axis=1, keepdims=True)
    exponential = np.exp(logits)
    normalizer = exponential.sum(axis=1, keepdims=True)
    if np.any(normalizer <= 0) or not np.isfinite(normalizer).all():
        raise ValueError("NLI softmax failed")
    return exponential / normalizer


def run_nli_pilot(
    suite: Path,
    dataset: BenchmarkDataset,
    *,
    predict: Predictor,
    model_id: str = DEFAULT_NLI_MODEL,
    model_revision: str | None = None,
) -> dict[str, Any]:
    if model_id != DEFAULT_NLI_MODEL:
        raise ValueError("Unverified NLI label mapping")
    structural = audit_dev_suite(suite, dataset)
    manifest = json.loads((suite / "manifest.json").read_text(encoding="utf-8"))
    pairs = []
    nonempty = []
    rows = []
    for case in manifest["cases"]:
        packet = json.loads(
            (suite / case["review_packet_filename"]).read_text(encoding="utf-8")
        )
        sources = packet["sources"]
        row = {
            "case_id": case["case_id"],
            "source_arm": case["arm"],
            "query_id": case["query_id"],
            "source_document_ids": case["source_doc_ids"],
            "nli_prediction": None,
            "softmax_scores_uncalibrated": None,
            "semantic_truth_verified": False,
            "human_review_equivalence": False,
            "runtime_policy": "not_evaluated",
        }
        if not sources:
            row["nli_status"] = "not_run_empty_context"
            row["runtime_policy"] = "abstain_no_context"
            rows.append(row)
            continue
        premise = str(sources[0]["text"])
        hypothesis = str(packet["question"])
        if not premise.strip() or not hypothesis.strip():
            raise ValueError("Empty NLI premise or hypothesis")
        pairs.append((premise, hypothesis))
        nonempty.append(row)
    if not pairs:
        raise ValueError("No nonempty TRAIN evidence cases")
    probabilities = _logit_probabilities(predict(pairs), len(pairs))
    labels = Counter()
    for row, scores in zip(nonempty, probabilities, strict=True):
        label = NLI_LABELS[int(np.argmax(scores))]
        labels[label] += 1
        row["nli_prediction"] = label
        row["softmax_scores_uncalibrated"] = {
            key: float(scores[i]) for i, key in enumerate(NLI_LABELS)
        }
        row["nli_status"] = "uncalibrated_model_prediction"
        rows.append(row)
    by_id = {row["case_id"]: row for row in rows}
    ordered = [by_id[case["case_id"]] for case in manifest["cases"]]
    if len(ordered) != structural["case_count"]:
        raise ValueError("NLI output case count mismatch")
    return {
        "experiment_id": "M2-DEV-NLI-PILOT-01",
        "status": "machine_predictions_only_not_ground_truth",
        "dataset": "beir/scifact/train",
        "model": {
            "id": model_id,
            "revision_if_available": model_revision,
            "class_order": list(NLI_LABELS),
            "premise": "recorded source snippet",
            "hypothesis": "SciFact TRAIN scientific proposition",
            "max_length": 512,
            "training_corpora": "SNLI / MultiNLI",
        },
        "corpus_fingerprint": manifest["corpus_fingerprint"],
        "case_count": len(ordered),
        "nli_scored_count": len(pairs),
        "no_context_count": structural["no_context_control_count"],
        "predicted_label_counts": {key: labels[key] for key in NLI_LABELS},
        "human_semantic_labels": 0,
        "validated_semantic_accuracy": None,
        "abstention_threshold": None,
        "semantic_truth_status": "not_evaluated",
        "limitations": [
            "Softmax outputs are uncalibrated model scores, not biomedical truth probabilities.",
            "SNLI and MultiNLI are out of domain for scientific claims.",
            "Original contexts may be truncated; tokenization may truncate further.",
            "Qrel relevance is not entailment, contradiction or answer sufficiency.",
            "Cross-query alternatives are not inherently contradictory.",
            "A predicted class is not a human label or validated answer correctness.",
            "Only empty contexts have a deterministic operational abstention policy.",
            "No SciFact TEST labels were used, and no live evidence policy was changed.",
        ],
        "cases": ordered,
    }


def format_nli_report(report: dict[str, Any]) -> str:
    counts = report["predicted_label_counts"]
    lines = [
        "# M2 TRAIN — local NLI predictions (not verified truth)",
        "",
        "Model: " + report["model"]["id"],
        f"Nonempty pairs evaluated: {report['nli_scored_count']}",
        f"No-context controls: {report['no_context_count']}",
        "",
        "| Predicted class | Count |",
        "|---|---:|",
    ]
    lines.extend(f"| {label} | {counts[label]} |" for label in NLI_LABELS)
    lines.extend([
        "",
        "## Per-case unvalidated predictions",
        "",
        "| Case | Arm | Model prediction | Operational decision |",
        "|---|---|---|---|",
    ])
    for case in report["cases"]:
        lines.append(
            f"| {case['case_id']} | {case['source_arm']} | "
            f"{case['nli_prediction'] or 'not_run'} | {case['runtime_policy']} |"
        )
    lines.extend(["", "## Limitations", ""])
    lines.extend("- " + note for note in report["limitations"])
    return "\n".join(lines) + "\n"

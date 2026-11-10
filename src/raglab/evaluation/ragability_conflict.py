"""External, fantasy-entity inter-context conflict benchmark.

The official Ragability corpus is derived from human-annotated WikiContradict
examples, then adapted by its authors. It is NOT a fresh blind holdout or a
human-reviewed benchmark created by this project. The public dataset is small
(53 rows / 43 source-conflict groups) and CC-BY-SA-4.0.

This module measures pairwise NLI contradiction detection only. It does not
measure retrieval, answer generation, source authority, or calibrated refusal.
"""

from __future__ import annotations

import csv
import hashlib
import json
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any, Iterable, Sequence

NLI_LABELS = ("contradiction", "entailment", "neutral")
CONFLICT = "contradiction"
NON_CONFLICT = "non_contradiction"

DATASET_ID = "ofai/RagabilityCorpus"
DATASET_REVISION = "2251634ed365bfca55e7d808290b0cf2c5fde730"
DATASET_FILE = "Dataset_v0.4.tsv"
DATASET_LICENSE = "cc-by-sa-4.0"
DATASET_ROWS = 53
CONTRADICTION_GROUPS = 43

PAIR_SPECS = (
    ("c1_c2", "context_1", "context_2", CONFLICT),
    ("c2_c3", "context_2", "context_3_nc1_c2", CONFLICT),
    ("c1_c3", "context_1", "context_3_nc1_c2", NON_CONFLICT),
    ("c1_c4", "context_1", "context_4_nc1_nc2_nc3", NON_CONFLICT),
    ("c2_c4", "context_2", "context_4_nc1_nc2_nc3", NON_CONFLICT),
    ("c3_c4", "context_3_nc1_c2", "context_4_nc1_nc2_nc3", NON_CONFLICT),
)

REQUIRED_COLUMNS = (
    "contradiction_ID",
    "WikiContradict_ID",
    "reasoning_required_c1c2",
    "context_1",
    "context_2",
    "context_3_nc1_c2",
    "context_4_nc1_nc2_nc3",
    "query_text",
)


@dataclass(frozen=True, slots=True)
class ConflictPair:
    case_id: str
    contradiction_id: str
    row_index: int
    pair_type: str
    expected: str
    reasoning_type: str
    wiki_contradict_id: str
    query_sha256: str
    premise_sha256: str
    hypothesis_sha256: str
    premise: str
    hypothesis: str

    def public_dict(self) -> dict[str, Any]:
        """Return provenance/labels only; never redistribute source text."""
        return {
            "case_id": self.case_id,
            "contradiction_id": self.contradiction_id,
            "row_index": self.row_index,
            "pair_type": self.pair_type,
            "expected": self.expected,
            "reasoning_type": self.reasoning_type,
            "wiki_contradict_id": self.wiki_contradict_id,
            "query_sha256": self.query_sha256,
            "premise_sha256": self.premise_sha256,
            "hypothesis_sha256": self.hypothesis_sha256,
        }


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_ragability_tsv(path: Path) -> list[dict[str, str]]:
    """Read and validate the exact published TSV without silently coercing data."""
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t", quotechar='"')
        if reader.fieldnames is None or not set(REQUIRED_COLUMNS) <= set(reader.fieldnames):
            raise ValueError("Ragability TSV schema is missing required columns")
        rows = list(reader)
    if len(rows) != DATASET_ROWS:
        raise ValueError(f"Expected exactly {DATASET_ROWS} published rows, got {len(rows)}")
    groups = {row.get("contradiction_ID", "").strip() for row in rows}
    if "" in groups or len(groups) != CONTRADICTION_GROUPS:
        raise ValueError(
            f"Expected {CONTRADICTION_GROUPS} nonempty source-conflict groups, got {len(groups)}"
        )
    for index, row in enumerate(rows, start=1):
        for field in REQUIRED_COLUMNS:
            value = row.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Published row {index} has an empty {field}")
        # Keep source identifiers literal; no accidental float normalization.
        if not row["contradiction_ID"].strip().isdigit():
            raise ValueError(f"Invalid contradiction_ID in row {index}")
    return rows


def build_conflict_pairs(rows: Sequence[dict[str, str]]) -> list[ConflictPair]:
    if len(rows) != DATASET_ROWS:
        raise ValueError("Only the pinned official Ragability row count is accepted")
    pairs: list[ConflictPair] = []
    seen_case_ids: set[str] = set()
    for row_index, row in enumerate(rows, start=1):
        contradiction_id = row["contradiction_ID"].strip()
        reasoning = row["reasoning_required_c1c2"].strip()
        wiki_id = row["WikiContradict_ID"].strip()
        query_hash = _sha(row["query_text"].strip())
        for pair_type, premise_key, hypothesis_key, expected in PAIR_SPECS:
            premise = row[premise_key].strip()
            hypothesis = row[hypothesis_key].strip()
            if not premise or not hypothesis:
                raise ValueError(
                    f"Empty source text in row {row_index} pair {pair_type}"
                )
            case_id = f"row-{row_index:03d}-{pair_type}"
            if case_id in seen_case_ids:
                raise ValueError("Duplicate pair case ID")
            seen_case_ids.add(case_id)
            pairs.append(ConflictPair(
                case_id=case_id,
                contradiction_id=contradiction_id,
                row_index=row_index,
                pair_type=pair_type,
                expected=expected,
                reasoning_type=reasoning,
                wiki_contradict_id=wiki_id,
                query_sha256=query_hash,
                premise_sha256=_sha(premise),
                hypothesis_sha256=_sha(hypothesis),
                premise=premise,
                hypothesis=hypothesis,
            ))
    if len(pairs) != DATASET_ROWS * len(PAIR_SPECS):
        raise ValueError("Unexpected pair count")
    counts = Counter(pair.expected for pair in pairs)
    if counts != {NON_CONFLICT: 212, CONFLICT: 106}:
        raise ValueError(f"Unexpected pair label distribution: {dict(counts)}")
    return pairs


def dataset_manifest(
    rows: Sequence[dict[str, str]],
    pairs: Sequence[ConflictPair],
    *,
    source_sha256: str,
) -> dict[str, Any]:
    groups = sorted({pair.contradiction_id for pair in pairs})
    return {
        "dataset_id": DATASET_ID,
        "dataset_revision": DATASET_REVISION,
        "filename": DATASET_FILE,
        "license": DATASET_LICENSE,
        "source_sha256": source_sha256,
        "row_count": len(rows),
        "unique_conflict_groups": len(groups),
        "pair_count": len(pairs),
        "pair_types": {
            pair_type: sum(pair.pair_type == pair_type for pair in pairs)
            for pair_type, _, _, _ in PAIR_SPECS
        },
        "label_counts": dict(Counter(pair.expected for pair in pairs)),
        "reasoning_type_counts": dict(Counter(
            row["reasoning_required_c1c2"].strip() for row in rows
        )),
        "group_ids_sha256": _sha("\n".join(groups)),
        "pair_label_policy": {
            "contradiction": ["c1_c2", "c2_c3"],
            "non_contradiction": ["c1_c3", "c1_c4", "c2_c4", "c3_c4"],
        },
        "method": (
            "All rows and all six author-defined context-pair relations are evaluated. "
            "No train/calibration split and no threshold fitting are performed."
        ),
        "limitations": [
            "53 published rows derive from 43 conflict groups; rows are not independent.",
            "The 43 pairs derive from human-annotated WikiContradict examples; the Ragability authors adapted them and substituted fantasy entities.",
            "This is a public exposed benchmark, not a sealed independent holdout.",
            "Pairwise NLI is not query-aware answer verification or source-authority reasoning.",
            "No retrieval, answer generation, refusal policy or end-to-end RAG pipeline is measured.",
            "The source dataset is CC-BY-SA-4.0; raw text is not redistributed in experiment artifacts.",
        ],
    }


def _class_metrics(expected: Sequence[str], predicted: Sequence[str]) -> dict[str, Any]:
    if len(expected) != len(predicted) or not expected:
        raise ValueError("Expected and predicted labels must be nonempty and aligned")
    tp = sum(a == CONFLICT and b == CONFLICT for a, b in zip(expected, predicted))
    tn = sum(a == NON_CONFLICT and b == NON_CONFLICT for a, b in zip(expected, predicted))
    fp = sum(a == NON_CONFLICT and b == CONFLICT for a, b in zip(expected, predicted))
    fn = sum(a == CONFLICT and b == NON_CONFLICT for a, b in zip(expected, predicted))
    conflict_recall = tp / (tp + fn) if tp + fn else 0.0
    non_conflict_recall = tn / (tn + fp) if tn + fp else 0.0
    conflict_precision = tp / (tp + fp) if tp + fp else 0.0
    non_conflict_precision = tn / (tn + fn) if tn + fn else 0.0
    conflict_f1 = (
        2 * conflict_precision * conflict_recall /
        (conflict_precision + conflict_recall)
        if conflict_precision + conflict_recall else 0.0
    )
    non_conflict_f1 = (
        2 * non_conflict_precision * non_conflict_recall /
        (non_conflict_precision + non_conflict_recall)
        if non_conflict_precision + non_conflict_recall else 0.0
    )
    return {
        "n": len(expected),
        "correct": tp + tn,
        "accuracy": (tp + tn) / len(expected),
        "balanced_accuracy": (conflict_recall + non_conflict_recall) / 2,
        "macro_f1": (conflict_f1 + non_conflict_f1) / 2,
        "contradiction": {
            "precision": conflict_precision,
            "recall": conflict_recall,
            "f1": conflict_f1,
            "support": tp + fn,
        },
        "non_contradiction": {
            "precision": non_conflict_precision,
            "recall": non_conflict_recall,
            "f1": non_conflict_f1,
            "support": tn + fp,
        },
        "confusion": {
            "true_contradiction_predicted_contradiction": tp,
            "true_contradiction_predicted_non_contradiction": fn,
            "true_non_contradiction_predicted_contradiction": fp,
            "true_non_contradiction_predicted_non_contradiction": tn,
        },
    }


def cluster_bootstrap_balanced_accuracy(
    rows: Sequence[dict[str, Any]],
    *,
    repetitions: int = 2000,
    seed: int = 20261109,
) -> dict[str, Any]:
    if repetitions < 100:
        raise ValueError("At least 100 bootstrap repetitions are required")
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["contradiction_id"])].append(row)
    groups = sorted(grouped)
    if len(groups) != CONTRADICTION_GROUPS:
        raise ValueError("Bootstrap must resample all 43 source-conflict groups")
    rng = random.Random(seed)
    samples: list[float] = []
    for _ in range(repetitions):
        selected = [rng.choice(groups) for _ in groups]
        draw = [row for group in selected for row in grouped[group]]
        result = _class_metrics(
            [row["expected"] for row in draw],
            [row["symmetric_prediction"] for row in draw],
        )
        samples.append(result["balanced_accuracy"])
    samples.sort()
    low = samples[int(0.025 * (repetitions - 1))]
    high = samples[int(0.975 * (repetitions - 1))]
    return {
        "unit": "contradiction_ID source group (43 groups), not individual rows",
        "repetitions": repetitions,
        "seed": seed,
        "balanced_accuracy_percentile_95_ci": [low, high],
    }


def score_model_rows(
    pairs: Sequence[ConflictPair],
    forward_probabilities: Sequence[Sequence[float]],
    reverse_probabilities: Sequence[Sequence[float]],
    *,
    bootstrap_repetitions: int = 2000,
) -> dict[str, Any]:
    if not (
        len(pairs) == len(forward_probabilities) == len(reverse_probabilities)
    ):
        raise ValueError("Pair/prediction cardinality mismatch")
    rows: list[dict[str, Any]] = []
    for pair, forward, reverse in zip(
        pairs, forward_probabilities, reverse_probabilities, strict=True
    ):
        if len(forward) != 3 or len(reverse) != 3:
            raise ValueError("NLI probability vectors must have three labels")
        if any(not 0 <= float(x) <= 1 for x in (*forward, *reverse)):
            raise ValueError("NLI probability outside [0,1]")
        if abs(sum(forward) - 1) > 0.001 or abs(sum(reverse) - 1) > 0.001:
            raise ValueError("NLI probability vector is not normalized")
        symmetric = [
            (float(forward[i]) + float(reverse[i])) / 2
            for i in range(3)
        ]
        fwd_label = NLI_LABELS[max(range(3), key=lambda i: forward[i])]
        rev_label = NLI_LABELS[max(range(3), key=lambda i: reverse[i])]
        symmetric_label = NLI_LABELS[max(range(3), key=lambda i: symmetric[i])]
        rows.append({
            **pair.public_dict(),
            "forward_prediction": fwd_label,
            "reverse_prediction": rev_label,
            "symmetric_prediction": symmetric_label,
            "directional_agreement": fwd_label == rev_label,
            "forward_probabilities": {
                label: float(forward[i]) for i, label in enumerate(NLI_LABELS)
            },
            "reverse_probabilities": {
                label: float(reverse[i]) for i, label in enumerate(NLI_LABELS)
            },
            "symmetric_probabilities": {
                label: symmetric[i] for i, label in enumerate(NLI_LABELS)
            },
        })
    expected = [row["expected"] for row in rows]
    symmetric = [row["symmetric_prediction"] for row in rows]
    forward = [row["forward_prediction"] for row in rows]
    reverse = [row["reverse_prediction"] for row in rows]
    by_type = {
        pair_type: _class_metrics(
            [r["expected"] for r in rows if r["pair_type"] == pair_type],
            [r["symmetric_prediction"] for r in rows if r["pair_type"] == pair_type],
        )
        for pair_type, _, _, _ in PAIR_SPECS
    }
    by_reasoning_type = {}
    for reasoning_type in sorted({row["reasoning_type"] for row in rows}):
        selected = [row for row in rows if row["reasoning_type"] == reasoning_type]
        by_reasoning_type[reasoning_type] = _class_metrics(
            [r["expected"] for r in selected],
            [r["symmetric_prediction"] for r in selected],
        )
    metrics = _class_metrics(expected, symmetric)
    metrics["directional_forward"] = _class_metrics(expected, forward)
    metrics["directional_reverse"] = _class_metrics(expected, reverse)
    metrics["directional_prediction_agreement"] = mean(
        row["directional_agreement"] for row in rows
    )
    metrics["always_non_contradiction_baseline"] = _class_metrics(
        expected, [NON_CONFLICT] * len(expected)
    )
    return {
        "metrics": metrics,
        "pair_type_metrics": by_type,
        "reasoning_type_metrics": by_reasoning_type,
        "group_bootstrap": cluster_bootstrap_balanced_accuracy(
            rows, repetitions=bootstrap_repetitions
        ),
        "cases": rows,
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )

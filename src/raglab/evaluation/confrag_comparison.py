"""Independent post-run ConfRAG pair alignment and descriptive grouped uncertainty.

This consumes only privacy-safe artifact JSONs, not model weights or raw web
text. ConfRAG author answer viewpoint clusters != logical contradiction and
are NOT an independently collected human-reviewed RAG safety test.
"""
from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

STATUS = "REAL_WEIGHTS_REAL_WEB_AUTHOR_ANSWER_CLUSTER_DEV_NOT_SCIENTIFIC_HOLDOUT"
EXPECTED_DATASET_REVISION = "529e760a78a58791d0387fe469e0732377a6d94d"
EXPECTED_INPUT_HASH = "acd2012c7371c408d46987424db876b04efc7ba06b726823215fa9c0d817c8d7"
EXPECTED_SOURCE_PREFIX_HASH = "24c62a4b4df17e8d80a15338d27b05624201fd3fc67862b64e44bc8a2e9dadd6"
EXPECTED_MODELS = {
    "deberta_xsmall": ("a150876415327c80daeff35ca6f68f5ed8cf5c24", 70831107),
    "minilm": ("b95119ce93d3e065de6214e38cd4a97b0f2f2c6d", 82120707),
}


def _rows(report: dict) -> dict[str, dict]:
    if report.get("status") != STATUS:
        raise ValueError("This comparator accepts only declared public ConfRAG DEV artifacts")
    data = report["data"]
    if (data["dataset_revision"] != EXPECTED_DATASET_REVISION
            or data["inputs_sha256"] != EXPECTED_INPUT_HASH
            or data["read_prefix_sha256"] != EXPECTED_SOURCE_PREFIX_HASH):
        raise ValueError("The source revision/prefix/input hashes are not the frozen public sample")
    key = report.get("model_key")
    if key not in EXPECTED_MODELS:
        raise ValueError("Model key missing or unsupported; use exact two-model run")
    model = report["model"]
    if (model["revision"], model["parameter_count"]) != EXPECTED_MODELS[key]:
        raise ValueError("Model revision or parameter count mismatch")
    rows = report["rows"]
    mapped = {r["pair_id"]: r for r in rows}
    if len(mapped) != len(rows) or len(mapped) != 240:
        raise ValueError("Expected 240 unique frozen source pairs")
    if len({r["group_id"] for r in rows}) != 16:
        raise ValueError("Expected 16 original source-question groups")
    return mapped


def _score(rows: list[dict], key: str) -> dict:
    counts = {"tp": 0, "tn": 0, "fp": 0, "fn": 0}
    for row in rows:
        actual = not row["same_annotated_viewpoint"]
        pred = row[key]
        if not isinstance(pred, bool):
            raise ValueError("Expected boolean proxy predictions")
        label = "tp" if actual and pred else "fn" if actual else "fp" if pred else "tn"
        counts[label] += 1
    tp, tn, fp, fn = (counts[k] for k in ("tp", "tn", "fp", "fn"))
    n = len(rows)
    return {
        "pairs": n, "correct": tp + tn, "accuracy": (tp + tn) / n,
        "counts": counts,
        "different_viewpoint_precision": tp / (tp + fp) if tp + fp else None,
        "different_viewpoint_recall": tp / (tp + fn) if tp + fn else None,
        "balanced_accuracy": (
            (tp / (tp + fn) + tn / (tn + fp)) / 2
            if tp + fn and tn + fp else None
        ),
    }


def _percentiles(sorted_values: list[float]) -> tuple[float, float]:
    n = len(sorted_values)
    return (sorted_values[int(0.025 * n)], sorted_values[int(0.975 * n)])


def _bootstrap_delta(
    group_rows: dict[str, list[dict]],
    left_key: str,
    right_key: str,
    *,
    repetitions: int, seed: int,
) -> dict:
    if not 100 <= repetitions <= 100000:
        raise ValueError("Bootstrap iterations must be 100..100000")
    groups = sorted(group_rows)
    rng = random.Random(seed)
    diffs = []
    for _ in range(repetitions):
        items = [r for g in (rng.choice(groups) for _ in groups) for r in group_rows[g]]
        a = _score(items, left_key)["accuracy"]
        b = _score(items, right_key)["accuracy"]
        diffs.append(a - b)
    diffs.sort()
    lo, hi = _percentiles(diffs)
    return {
        "point_delta_accuracy": (
            _score([r for g in groups for r in group_rows[g]], left_key)["accuracy"]
            - _score([r for g in groups for r in group_rows[g]], right_key)["accuracy"]
        ),
        "descriptive_group_bootstrap_percentile_95": [lo, hi],
        "n_original_question_groups": len(groups),
        "repetitions": repetitions, "seed": seed,
        "not_inferential": True,
    }


def compare_reports(
    deberta: dict[str, Any], minilm: dict[str, Any], *, repetitions: int = 10000,
    seed: int = 20261110,
) -> dict[str, Any]:
    a, b = _rows(deberta), _rows(minilm)
    if deberta["model_key"] != "deberta_xsmall" or minilm["model_key"] != "minilm":
        raise ValueError("Expected named DeBERTa and MiniLM2 source artifacts")
    if set(a) != set(b):
        raise ValueError("Source question/pair IDs do not align")
    joined = []
    for pair_id in sorted(a):
        x, y = a[pair_id], b[pair_id]
        for key in (
            "pair_id", "group_id", "same_annotated_viewpoint",
            "contradicts_question_flag", "lexical_predicts_different",
            "left_source_index", "right_source_index",
        ):
            if x[key] != y[key]:
                raise ValueError("Paired input labels or lexical controls do not match")
        joined.append({
            "pair_id": pair_id, "group_id": x["group_id"],
            "same_annotated_viewpoint": x["same_annotated_viewpoint"],
            "lexical": x["lexical_predicts_different"],
            "deberta": x["nli_predicts_different"],
            "minilm": y["nli_predicts_different"],
        })
    group_rows: dict[str, list[dict]] = defaultdict(list)
    for row in joined:
        group_rows[row["group_id"]].append(row)
    counts = {
        "different_viewpoint_pairs": sum(not x["same_annotated_viewpoint"] for x in joined),
        "same_viewpoint_pairs": sum(x["same_annotated_viewpoint"] for x in joined),
    }
    if counts != {"different_viewpoint_pairs": 130, "same_viewpoint_pairs": 110}:
        raise ValueError("Frozen pairwise viewpoint balance changed")
    scores = {key: _score(joined, key) for key in ("lexical", "deberta", "minilm")}
    for model_key, model_label in [
        ("deberta", "fixed_nli_contradiction_argmax_as_viewpoint_proxy"),
        ("minilm", "fixed_nli_contradiction_argmax_as_viewpoint_proxy"),
    ]:
        report = deberta if model_key == "deberta" else minilm
        expected = report["metrics"][model_label]
        if scores[model_key]["counts"] != expected["counts"]:
            raise ValueError("Independent confusion recomputation disagreed with artifact")
    agreement = sum(a[i]["nli_raw_relation"] == b[i]["nli_raw_relation"] for i in a)
    deltas = {
        "deberta_minus_lexical": _bootstrap_delta(
            group_rows, "deberta", "lexical", repetitions=repetitions, seed=seed
        ),
        "minilm_minus_lexical": _bootstrap_delta(
            group_rows, "minilm", "lexical", repetitions=repetitions, seed=seed
        ),
        "minilm_minus_deberta": _bootstrap_delta(
            group_rows, "minilm", "deberta", repetitions=repetitions, seed=seed
        ),
    }
    return {
        "status": "PUBLIC_CONFRAG_DEV_EXPLORATORY_COMPARISON_NOT_PAPER_VALIDATION",
        "source_revision": EXPECTED_DATASET_REVISION,
        "source_prefix_sha256": EXPECTED_SOURCE_PREFIX_HASH,
        "paired_input_sha256": EXPECTED_INPUT_HASH,
        "original_question_groups": len(group_rows),
        "derived_pairs_not_independent": len(joined),
        "labels": counts, "scores": scores,
        "nli_three_way_label_agreement": {
            "same_label": agreement, "pairs": len(joined),
        },
        "model_parameters": {
            key: EXPECTED_MODELS[key][1] for key in EXPECTED_MODELS
        },
        "batch_cpu_ms_independent_runner_snapshots": {
            "deberta": deberta["cpu_cost"]["total_batch_wall_ms"],
            "minilm": minilm["cpu_cost"]["total_batch_wall_ms"],
        },
        "descriptive_paired_group_deltas": deltas,
        "limitations": [
            "Only 16 source groups; 240 pairs are correlated, not 240 independent questions.",
            "Author-extracted answers and cluster IDs are privileged public development signals.",
            "Different annotated viewpoints are NOT necessarily logical contradiction.",
            "NLI contradiction is an intentionally mismatched proxy for viewpoint disagreement.",
            "Fixed 0.5 Jaccard control, not a tuned semantic or source support verifier.",
            "Second MiniLM2 model was added post-hoc after seeing DeBERTa results.",
            "Question-group bootstrap is descriptive only and was planned post-result.",
            "CPU batch times were observed on separate shared GitHub runners, not a hardware-controlled speed study.",
            "No 33M end-to-end reader, no independent dual-review holdout, no general factual QA certification.",
        ],
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--deberta", type=Path, required=True)
    p.add_argument("--minilm", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--bootstrap", type=int, default=10000)
    a = p.parse_args()
    result = compare_reports(
        json.loads(a.deberta.read_text(encoding="utf-8")),
        json.loads(a.minilm.read_text(encoding="utf-8")),
        repetitions=a.bootstrap,
    )
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    print(json.dumps({
        "status": result["status"], "groups": result["original_question_groups"],
        "scores": result["scores"], "deltas": result["descriptive_paired_group_deltas"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()

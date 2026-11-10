"""MICRO-RAG M1: author-provided answer ORACLE vs raw evidence NLI ablation.

The official Ragability dataset contains two incompatible answer variants per
53-row context pair, provided by its authors. Using them is privileged oracle
claim normalization, NOT a deployable extraction or full RAG inference result.

No thresholds, prompts or models are fitted on the public benchmark. All 43
source-conflict groups are retained for cluster-bootstrap uncertainty.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import time
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

from raglab.evaluation.ragability_conflict import (
    DATASET_ID, DATASET_FILE, DATASET_REVISION, DATASET_LICENSE,
    read_ragability_tsv, write_json,
)
from ragability_nli_cpu import (
    MODEL_SPECS, _license_from_info, _download_model, _load_model,
    _predict_bidirectional, _run_sanity_controls,
)

EXTERNAL_DATASET_SHA = "e973f5ac7b4881e2cafe23f39b837643878ea6afdb769d9afa30ff66e93c8285"
ANSWER_COLUMNS = (
    "answer_context1", "answer_context2",
    "answer_context1_long", "answer_context2_long",
)
CONDITIONS = (
    "raw_context",
    "oracle_short",
    "oracle_long",
    "oracle_query_short",
    "oracle_query_long",
    "negative_identical_claim",
    "negative_compatible_source",
)
REPETITIONS = 2000


def paired_conditions(row: dict[str, str]) -> dict[str, tuple[str, str]]:
    for key in ANSWER_COLUMNS:
        if not row.get(key, "").strip():
            raise ValueError(f"Missing author oracle answer field: {key}")
    question = row["query_text"].strip()
    a = row["answer_context1"].strip()
    b = row["answer_context2"].strip()
    al = row["answer_context1_long"].strip()
    bl = row["answer_context2_long"].strip()
    return {
        "raw_context": (row["context_1"].strip(), row["context_2"].strip()),
        "oracle_short": (a, b),
        "oracle_long": (al, bl),
        "oracle_query_short": (f"Question: {question}\\nAnswer: {a}",
                               f"Question: {question}\\nAnswer: {b}"),
        "oracle_query_long": (f"Question: {question}\\nAnswer: {al}",
                              f"Question: {question}\\nAnswer: {bl}"),
        "negative_identical_claim": (al, al),
        "negative_compatible_source": (
            row["context_1"].strip(), row["context_3_nc1_c2"].strip()
        ),
    }


def compute_recall_delta_ci(
    source_rows: list[dict[str, str]],
    base_flags: list[bool],
    oracle_flags: list[bool],
    *,
    repetitions: int = REPETITIONS, seed: int = 20261110,
) -> dict[str, Any]:
    if not (len(source_rows) == len(base_flags) == len(oracle_flags) == 53):
        raise ValueError("Expected exactly 53 paired cases")
    by_group: dict[str, list[int]] = defaultdict(list)
    for idx, row in enumerate(source_rows):
        by_group[row["contradiction_ID"].strip()].append(idx)
    group_ids = sorted(by_group)
    if len(group_ids) != 43 or repetitions < 100:
        raise ValueError("Use all 43 independent source-conflict groups")
    rng = random.Random(seed)
    diffs = []
    for _ in range(repetitions):
        picks = [rng.choice(group_ids) for _ in group_ids]
        indices = [i for grp in picks for i in by_group[grp]]
        diffs.append(
            mean(oracle_flags[i] for i in indices)
            - mean(base_flags[i] for i in indices)
        )
    diffs.sort()
    return {
        "delta": mean(oracle_flags) - mean(base_flags),
        "group_bootstrap_95_ci": [
            diffs[int(0.025 * (repetitions-1))],
            diffs[int(0.975 * (repetitions-1))],
        ],
        "source_groups": 43,
        "repetitions": repetitions,
        "seed": seed,
    }


def evaluate_oracle(
    rows: list[dict[str, str]],
    model_infer,
) -> dict[str, Any]:
    if len(rows) != 53:
        raise ValueError("Ragability author-oracle study requires all 53 rows")
    assembled = [paired_conditions(row) for row in rows]
    outputs: dict[str, dict[str, Any]] = {}
    per_condition: dict[str, list[bool]] = {}
    for condition in CONDITIONS:
        pairs = [pairset[condition] for pairset in assembled]
        forward, reverse, cpu = model_infer(pairs)
        if len(forward) != 53 or len(reverse) != 53:
            raise ValueError("Model returned incomplete condition predictions")
        is_conflict = []
        traces = []
        for index, (fwd, rev) in enumerate(zip(forward, reverse, strict=True)):
            if len(fwd) != 3 or len(rev) != 3:
                raise ValueError("Model NLI outputs require three classes")
            probs = [(float(fwd[k])+float(rev[k]))/2 for k in range(3)]
            predicted = max(range(3), key=lambda k: probs[k])
            conflict = predicted == 0 # verified class index: contradiction
            is_conflict.append(conflict)
            traces.append({
                "row_index": index+1,
                "contradiction_id": rows[index]["contradiction_ID"].strip(),
                "pair_sha256": hashlib.sha256(
                    json.dumps(pairs[index], ensure_ascii=False).encode("utf-8")
                ).hexdigest(),
                "predicted_nli_class": ["contradiction","entailment","neutral"][predicted],
                "contradiction_probability": probs[0],
            })
        per_condition[condition] = is_conflict
        expected_conflict = not condition.startswith("negative_")
        correct = sum(flag == expected_conflict for flag in is_conflict)
        outputs[condition] = {
            "expected_class": (
                "contradiction" if expected_conflict else "non_contradiction"
            ),
            "n": len(is_conflict),
            "correct": correct,
            "correct_rate": correct / len(is_conflict),
            "predicted_contradictions": sum(is_conflict),
            "conflict_recall_or_false_positive_rate": mean(is_conflict),
            "inference_cost": cpu,
            "traces": traces,
        }

    comparisons = {}
    raw = per_condition["raw_context"]
    for condition in ("oracle_short", "oracle_long",
                      "oracle_query_short", "oracle_query_long"):
        comparisons[f"{condition}_minus_raw_conflict_recall"] = compute_recall_delta_ci(
            rows, raw, per_condition[condition]
        )
    return {
        "conditions": outputs,
        "oracle_minus_raw_paired_group_bootstrap": comparisons,
        "warning": (
            "All author-supplied answer conditions are privileged oracle inputs. "
            "Negative_identical_claim is a trivial sanity control, not a realistic false-positive test. "
            "No independent end-to-end claim extraction was measured."
        ),
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model-key", required=True, choices=sorted(MODEL_SPECS))
    p.add_argument("--output-dir", required=True)
    a = p.parse_args()
    out = Path(a.output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    os.environ["OMP_NUM_THREADS"] = "2"
    os.environ["MKL_NUM_THREADS"] = "2"
    import torch
    from huggingface_hub import HfApi, hf_hub_download

    torch.set_num_threads(2)
    dsinfo = HfApi().dataset_info(DATASET_ID, revision=DATASET_REVISION)
    if _license_from_info(dsinfo) != DATASET_LICENSE:
        raise ValueError("Dataset license metadata mismatch")
    path = Path(hf_hub_download(
        repo_id=DATASET_ID, repo_type="dataset",
        filename=DATASET_FILE, revision=DATASET_REVISION,
        cache_dir=str(out / ".dataset-cache"),
    ))
    data_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    if data_sha != EXTERNAL_DATASET_SHA:
        raise ValueError("Published Ragability source SHA changed")
    rows = read_ragability_tsv(path)
    for row in rows:
        paired_conditions(row)
    spec = MODEL_SPECS[a.model_key]
    weights = out / "weights"
    model_manifest = _download_model(spec, weights)
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    tokenizer, model, actual = _load_model(weights, spec)
    model_manifest.update(actual)
    sanity = _run_sanity_controls(tokenizer, model)
    t0 = time.perf_counter()
    study = evaluate_oracle(
        rows,
        lambda pairs: _predict_bidirectional(
            tokenizer, model, pairs, batch_size=16
        )
    )
    wall_seconds = time.perf_counter() - t0
    report = {
        "experiment": "MICRO-RAGABILITY-02",
        "status": "AUTHOR_ORACLE_ABLATION_PUBLIC_BENCHMARK_NOT_END_TO_END",
        "dataset": {
            "id": DATASET_ID, "revision": DATASET_REVISION,
            "license": DATASET_LICENSE, "sha256": data_sha,
            "rows": 53, "source_conflict_groups": 43,
        },
        "model": model_manifest,
        "sanity_controls": sanity,
        "study": study,
        "total_wall_seconds": wall_seconds,
        "limitations": [
            "Author-provided answers are privileged; no real answer extraction performed",
            "Published, adapted dataset with correlated groups, not sealed independent holdout",
            "Only 53 positive contradictory examples in raw/oracle modes; no balanced full-QA metric",
            "Negative_identical_claim self-pair is a trivial control, not representative negatives",
            "Model outputs are uncalibrated; input modes are not production prompt candidates without calibration",
            "No retrieval, source authority, abstention or full-stack RAG measured",
        ],
    }
    write_json(out / "oracle_ablation.json", report)
    print(json.dumps({
        "status": report["status"], "model": model_manifest["id"],
        "data_sha256": data_sha,
        "conditions": {
            key: {"correct": v["correct"], "n": v["n"],
                  "cpu_wall_ms": v["inference_cost"]["total_batch_wall_ms"]}
            for key, v in study["conditions"].items()
        },
        "paired_deltas": study["oracle_minus_raw_paired_group_bootstrap"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()

"""Run pinned real CPU models against author-oracle Ragability input modes.

The scorer lives in raglab.evaluation.ragability_oracle and is unit-tested
without loading any model or downloading the public dataset.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path

from raglab.evaluation.ragability_oracle import (
    EXTERNAL_DATASET_SHA, paired_conditions, evaluate_oracle,
)
from raglab.evaluation.ragability_conflict import (
    DATASET_ID, DATASET_FILE, DATASET_REVISION, DATASET_LICENSE,
    read_ragability_tsv, write_json,
)
from ragability_nli_cpu import (
    MODEL_SPECS, _license_from_info, _download_model, _load_model,
    _predict_bidirectional, _run_sanity_controls,
)

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

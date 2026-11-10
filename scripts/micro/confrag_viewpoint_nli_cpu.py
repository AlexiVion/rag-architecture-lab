"""PAPER-01 P2: real ConfRAG author-answer cluster *development* diagnostic.

Downloads only a bounded PREFIX of the author's recommended JSONL at the exact
resolved Hugging Face dataset revision, streaming and closing early. Does not
download the ~599 MB corpus. Compares fixed Jaccard against a real pinned 71M
DeBERTa NLI model on IDENTICAL author-provided extracted answer pairs.

Important: difference between annotated answer clusters != logical contradiction.
This is NOT real-document automatic extraction, RAG QA, or independent human
holdout; user web pages and model weights are never uploaded as artifacts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
import time
import urllib.request
from collections import Counter
from pathlib import Path

from raglab.evaluation.confrag_viewpoints import (
    binary_viewpoint_score, extract_viewpoint_pairs, fingerprints,
    lexical_viewpoint_different,
)
from raglab.evaluation.ragability_conflict import write_json
from ragability_nli_cpu import (
    MODEL_LABELS, MODEL_SPECS, _download_model, _load_model,
    _license_from_info, _predict_bidirectional, _run_sanity_controls,
)

DATASET_ID = "OracleY/ConfRAG"
DATASET_FILE = "ConfRAGsuggested.jsonl"
DATASET_LICENSE = "cc-by-4.0"
DATASET_REVISION = "529e760a78a58791d0387fe469e0732377a6d94d"
# Frozen from exact-head first CPU run #42858534499 before the second model.
EXPECTED_PREFIX_SHA256 = "24c62a4b4df17e8d80a15338d27b05624201fd3fc67862b64e44bc8a2e9dadd6"
EXPECTED_INPUTS_SHA256 = "acd2012c7371c408d46987424db876b04efc7ba06b726823215fa9c0d817c8d7"
MODEL_REVISIONS = {
    "deberta_xsmall": "a150876415327c80daeff35ca6f68f5ed8cf5c24",
    "minilm": "b95119ce93d3e065de6214e38cd4a97b0f2f2c6d",
}


def read_bounded_public_prefix(*, revision: str, per_stratum: int = 8,
                               scan_limit: int = 128) -> tuple[list[dict], dict]:
    if not 1 <= per_stratum <= 24 or not 2 * per_stratum <= scan_limit <= 256:
        raise ValueError("Invalid public development source sample limits")
    # Authenticated by the HF dataset info below; no floating main in URL.
    url = (
        "https://huggingface.co/datasets/" + DATASET_ID
        + "/resolve/" + revision + "/" + DATASET_FILE
    )
    request = urllib.request.Request(
        url, headers={"User-Agent": "rag-architecture-lab/PAPER01-public-dev/1.0"}
    )
    totals = Counter()
    read_hash = hashlib.sha256()
    bytes_seen = 0
    rows_seen = 0
    selected: list[dict] = []
    selected_row_sha: dict[str, str] = {}
    # Only read until 8+8 eligible published records, not all corpus bytes.
    with urllib.request.urlopen(request, timeout=120) as response:
        for _ in range(scan_limit):
            raw = response.readline(8_000_001)
            if not raw:
                break
            if len(raw) > 8_000_000 or not raw.endswith(b"\n"):
                raise ValueError("An input JSONL line exceeded its bound")
            bytes_seen += len(raw)
            if bytes_seen > 110_000_000:
                raise ValueError("Bounded public-source transfer budget exceeded")
            read_hash.update(raw)
            rows_seen += 1
            record = json.loads(raw)
            if not isinstance(record, dict) or not isinstance(record.get("contradicts"), bool):
                totals["invalid_or_untyped"] += 1
                continue
            label = "contradicts_true" if record["contradicts"] else "contradicts_false"
            if totals[label] >= per_stratum:
                continue
            pairs = extract_viewpoint_pairs(record)
            if not pairs:
                totals["no_usable_unique_cluster_pairs"] += 1
                continue
            totals[label] += 1
            selected.extend(pairs)
            selected_row_sha[str(record["id"])] = hashlib.sha256(raw).hexdigest()
            if totals["contradicts_true"] == totals["contradicts_false"] == per_stratum:
                break
    if totals["contradicts_true"] != per_stratum or totals["contradicts_false"] != per_stratum:
        raise ValueError(
            f"Could not select {per_stratum} cases per type from {rows_seen} public rows: {dict(totals)}"
        )
    if len({p["pair_id"] for p in selected}) != len(selected):
        raise ValueError("Duplicate source pair IDs")
    return selected, {
        "download_scope": "bounded_prefix_stream_not_whole_dataset",
        "dataset_revision": revision, "dataset_filename": DATASET_FILE,
        "selection_rule": f"first_eligible_{per_stratum}_per_boolean_flag_in_source_order",
        "source_rows_scanned": rows_seen, "selected_question_groups": per_stratum * 2,
        "selected_group_balance": dict(totals),
        "prefix_bytes_read": bytes_seen,
        "read_prefix_sha256": read_hash.hexdigest(),
        "selected_row_sha256": selected_row_sha,
        "whole_dataset_file_sha256": None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--per-stratum", type=int, default=8)
    parser.add_argument("--scan-limit", type=int, default=128)
    parser.add_argument("--model-key", choices=sorted(MODEL_REVISIONS), default="deberta_xsmall")
    args = parser.parse_args()
    out = Path(args.output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    os.environ["OMP_NUM_THREADS"] = "2"
    os.environ["MKL_NUM_THREADS"] = "2"
    import torch
    from huggingface_hub import HfApi
    torch.set_num_threads(2)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass

    # Frozen after the first DEV discovery; both checkpoints read identical source.
    info = HfApi().dataset_info(DATASET_ID, revision=DATASET_REVISION)
    if str(info.sha) != DATASET_REVISION:
        raise ValueError("ConfRAG dataset revision does not match frozen SHA")
    license_id = _license_from_info(info)
    if license_id != DATASET_LICENSE:
        raise ValueError(f"Dataset metadata license mismatch: {license_id!r}")
    if DATASET_FILE not in {s.rfilename for s in info.siblings}:
        raise ValueError("Recommended ConfRAG JSONL file is absent")
    source_started = time.perf_counter()
    pairs, source = read_bounded_public_prefix(
        revision=str(info.sha),
        per_stratum=args.per_stratum, scan_limit=args.scan_limit,
    )
    source["dataset"] = DATASET_ID
    source["license"] = license_id
    source["selection_status"] = "PUBLIC_PUBLISHED_DEVELOPMENT_NOT_SEALED_HOLDOUT"
    source["download_seconds"] = time.perf_counter() - source_started
    selected_hashes = fingerprints(pairs)
    source["inputs_sha256"] = selected_hashes["selected_pairs_sha256"]
    if source["read_prefix_sha256"] != EXPECTED_PREFIX_SHA256:
        raise ValueError("ConfRAG frozen source-prefix SHA mismatch")
    if source["inputs_sha256"] != EXPECTED_INPUTS_SHA256:
        raise ValueError("ConfRAG frozen selected answer-pair inputs changed")
    source["selected_pair_sha256"] = selected_hashes["pair_sha256"]

    spec = dict(MODEL_SPECS[args.model_key], revision=MODEL_REVISIONS[args.model_key])
    model_started = time.perf_counter()
    model_manifest = _download_model(spec, out / ".model")
    model_manifest["download_seconds"] = time.perf_counter() - model_started
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    tokenizer, model, loaded = _load_model(out / ".model", spec)
    model_manifest.update(loaded)
    sanity = _run_sanity_controls(tokenizer, model)
    fwd, rev, cost = _predict_bidirectional(
        tokenizer, model, [(p["left"], p["right"]) for p in pairs],
        batch_size=12,
    )
    if len(fwd) != len(rev) or len(fwd) != len(pairs):
        raise ValueError("Unexpected model output pairing")
    scored = []
    for pair, first, second in zip(pairs, fwd, rev, strict=True):
        avg = [(first[i] + second[i]) / 2 for i in range(3)]
        label = MODEL_LABELS[max(range(3), key=lambda i: avg[i])]
        row = {key: val for key, val in pair.items() if key not in ("left", "right")}
        row["lexical_predicts_different"] = lexical_viewpoint_different(pair["left"], pair["right"])
        # Contradiction proxy for DIFFERENT VIEWPOINT: mismatch from labels is
        # expected because different perspectives can be compatible.
        row["nli_predicts_different"] = label == "contradiction"
        row["nli_raw_relation"] = label
        row["nli_symmetric_contradiction_score"] = avg[0]
        scored.append(row)
    metrics = {
        "fixed_jaccard_less_than_0_5": binary_viewpoint_score(
            scored, "lexical_predicts_different"
        ),
        "fixed_nli_contradiction_argmax_as_viewpoint_proxy": binary_viewpoint_score(
            scored, "nli_predicts_different"
        ),
    }
    report = {
        "status": "REAL_WEIGHTS_REAL_WEB_AUTHOR_ANSWER_CLUSTER_DEV_NOT_SCIENTIFIC_HOLDOUT",
        "experiment": "PAPER01_CONFRAG_VIEWPOINT_NLI_DEV01",
        "model_key": args.model_key,
        "data": source, "model": model_manifest,
        "model_sanity": sanity,
        "cpu_cost": cost, "environment": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "github_sha": os.getenv("GITHUB_SHA"),
            "runner_os": os.getenv("RUNNER_OS"),
        },
        "metrics": metrics, "rows": scored,
        "limitations": [
            "Website.answer fields were EXTRACTED BY THE BENCHMARK AUTHORS; the QA answer was not automatically extracted by our pipeline.",
            "ConfRAG answer-cluster differences are NOT logical contradictions; the NLI contradiction class is only a provisional proxy for disagreement.",
            "This is source-author published data with human-in-loop and LLM-assisted annotations, not new independent dual-human labels.",
            "Public order-biased 8+8 prefix DEV selection, tiny clustered sample, no statistical power or group-confident reliability statement.",
            "No new model trained; published NLI classifier and fixed lexical control, no chosen thresholds from label inspection.",
            "NLI CPU timings exclude retrieval, webpage preprocessing, dataset/model downloading and QA extraction, so not full-stack RAG.",
            "Only SHA256 digests, output predictions and manifests are uploaded, never full web text or model weights.",
            "No conclusion about <=135M combined end-to-end QA reliability or energy efficiency can follow.",
        ],
    }
    write_json(out / "results.json", report)
    print(json.dumps({
        "status": report["status"],
        "dataset_revision": source["dataset_revision"],
        "model_key": args.model_key,
        "groups": source["selected_question_groups"],
        "pairs": len(pairs),
        "metrics": metrics,
        "model_revision": model_manifest["revision"],
        "batch_wall_ms": cost["total_batch_wall_ms"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()

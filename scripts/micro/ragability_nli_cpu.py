"""Real CPU NLI baseline on the external Ragability inter-context benchmark.

No prompt/threshold tuning is performed on this public evaluation set. The
model predicts both premise/hypothesis directions; probabilities are averaged
to produce a symmetric pair score. Group-bootstrap uncertainty resamples the
43 original contradiction IDs rather than pretending 318 derived pairs are
independent.

This is a verifier-only diagnostic, NOT an end-to-end RAG benchmark.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import resource
import statistics
import time
from pathlib import Path
from typing import Any

from raglab.evaluation.ragability_conflict import (
    DATASET_FILE,
    DATASET_ID,
    DATASET_LICENSE,
    DATASET_REVISION,
    build_conflict_pairs,
    dataset_manifest,
    read_ragability_tsv,
    score_model_rows,
    write_json,
)

MODEL_SPECS = {
    "minilm": {
        "id": "cross-encoder/nli-MiniLM2-L6-H768",
        "revision": "b95119ce93d3e065de6214e38cd4a97b0f2f2c6d",
        "revision_prefix": "b95119ce93d3e065de6214e38cd4a97b0f2f2c6d",
        "expected_license": "apache-2.0",
        "min_parameters": 75_000_000,
        "max_parameters": 90_000_000,
        "reported_parameters": "82.1M",
    },
    "deberta_xsmall": {
        "id": "cross-encoder/nli-deberta-v3-xsmall",
        "revision": None,
        "revision_prefix": "a150876",
        "expected_license": "apache-2.0",
        "min_parameters": 60_000_000,
        "max_parameters": 80_000_000,
        "reported_parameters": "70.8M",
    },
}

MODEL_LABELS = ("contradiction", "entailment", "neutral")
SANITY_CONTROLS = (
    {
        "premise": "A man is eating pizza.",
        "hypothesis": "A man is eating something.",
        "expected": "entailment",
    },
    {
        "premise": "A dog is asleep on a couch.",
        "hypothesis": "A dog is awake on a couch.",
        "expected": "contradiction",
    },
    {
        "premise": "A woman is reading a book.",
        "hypothesis": "It is raining outside.",
        "expected": "neutral",
    },
)


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_markdown(path: Path, payload: dict[str, Any]) -> None:
    m = payload["evaluation"]["metrics"]
    cost = payload["inference_cost"]
    lines = [
        "# MICRO-RAGABILITY-01 — external pairwise NLI on CPU",
        "",
        f"Model: {payload['model']['id']}",
        f"Exact revision: {payload['model']['revision']}",
        f"Dataset revision: {payload['dataset']['dataset_revision']}",
        f"Dataset SHA256: {payload['dataset']['source_sha256']}",
        "",
        "## Primary symmetric NLI result",
        "",
        "| Metric | Result |",
        "|---|---:|",
        f"| Pair cases | {m['n']} |",
        f"| Accuracy | {m['accuracy']:.4f} |",
        f"| Balanced accuracy | {m['balanced_accuracy']:.4f} |",
        f"| Macro F1 | {m['macro_f1']:.4f} |",
        f"| Contradiction precision | {m['contradiction']['precision']:.4f} |",
        f"| Contradiction recall | {m['contradiction']['recall']:.4f} |",
        f"| Contradiction F1 | {m['contradiction']['f1']:.4f} |",
        f"| Directional agreement | {m['directional_prediction_agreement']:.4f} |",
        f"| Always-non-contradiction balanced accuracy | {m['always_non_contradiction_baseline']['balanced_accuracy']:.4f} |",
        "",
        "Group-bootstrap 95% interval (43 source-conflict groups): "
        + str(payload["evaluation"]["group_bootstrap"]["balanced_accuracy_percentile_95_ci"]),
        "",
        "## CPU cost",
        "",
        f"- Model parameters: {payload['model']['parameter_count']:,}",
        f"- Weight bytes: {payload['model']['weight_bytes']:,}",
        f"- Model inference inputs: {cost['directional_pair_inputs']:,}",
        f"- Forward batches: {cost['forward_batch_count']:,}",
        f"- Total model-call wall time: {cost['total_batch_wall_ms']:.2f} ms",
        f"- Mean ms per directional pair: {cost['mean_ms_per_directional_pair']:.4f}",
        f"- Peak process RSS: {payload['environment']['peak_rss_bytes']:,} bytes",
        "",
        "## Model sanity controls (not benchmark cases)",
        "",
        "| Expected | Predicted | Correct |",
        "|---|---|---:|",
    ]
    for item in payload["sanity_controls"]:
        lines.append(
            f"| {item['expected']} | {item['symmetric_prediction']} | "
            f"{item['symmetric_prediction'] == item['expected']} |"
        )
    lines += [
        "",
        "## Interpretation limits",
        "",
        "- This is a public, small, author-adapted benchmark derived from human-annotated WikiContradict examples, not a sealed holdout.",
        "- The 318 pair cases are clustered in 43 source-conflict groups; confidence intervals resample groups.",
        "- Pairwise NLI is not retrieval, query-conditioned answer verification, or source-authority reasoning.",
        "- SNLI/MultiNLI-trained NLI scores are not calibrated probabilities of factual conflict.",
        "- No threshold or prompt is tuned on this benchmark.",
        "- Dataset text is CC-BY-SA-4.0 and is not redistributed in the artifact.",
        "- A good score here does not validate production source arbitration or end-to-end RAG.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def _model_revision(spec: dict[str, Any]) -> tuple[str, Any]:
    from huggingface_hub import HfApi

    api = HfApi()
    revision = spec["revision"]
    info = api.model_info(spec["id"], revision=revision) if revision else api.model_info(spec["id"])
    sha = str(info.sha)
    if not sha.startswith(spec["revision_prefix"]):
        raise ValueError(
            f"Published model revision moved: expected prefix "
            f"{spec['revision_prefix']}, got {sha}"
        )
    return sha, info


def _license_from_info(info: Any) -> str | None:
    card = getattr(info, "card_data", None)
    if card is None:
        return None
    if isinstance(card, dict):
        return card.get("license")
    return getattr(card, "license", None)


def _download_model(spec: dict[str, Any], destination: Path) -> dict[str, Any]:
    from huggingface_hub import snapshot_download

    revision, info = _model_revision(spec)
    license_id = _license_from_info(info)
    if license_id != spec["expected_license"]:
        raise ValueError(
            f"Model license changed or is unavailable: {license_id!r}"
        )
    destination.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=spec["id"],
        revision=revision,
        local_dir=str(destination),
        allow_patterns=(
            "README.md", "config.json", "model.safetensors",
            "model-*.safetensors", "model.safetensors.index.json",
            "tokenizer.json", "tokenizer_config.json",
            "special_tokens_map.json", "vocab.json", "merges.txt",
            "spm.model", "added_tokens.json",
        ),
        ignore_patterns=("*.bin", "*.pt", "*.msgpack", "*.onnx"),
    )
    weight_files = sorted(destination.rglob("*.safetensors"))
    if not weight_files:
        raise ValueError("No safetensors model weights downloaded")
    weight_bytes = sum(path.stat().st_size for path in weight_files)
    if weight_bytes > 500_000_000:
        raise ValueError("Model weight download exceeds the registered 500 MB budget")
    return {
        "id": spec["id"],
        "revision": revision,
        "license": license_id,
        "reported_parameter_count": spec["reported_parameters"],
        "weight_bytes": weight_bytes,
        "weight_files": {
            str(path.relative_to(destination)): {
                "bytes": path.stat().st_size,
                "sha256": _sha_file(path),
            }
            for path in weight_files
        },
        "training_corpora": ["SNLI", "MultiNLI"],
        "model_card": "https://huggingface.co/" + spec["id"],
    }


def _load_model(path: Path, spec: dict[str, Any]):
    import torch
    from transformers import AutoConfig, AutoModelForSequenceClassification, AutoTokenizer

    config = AutoConfig.from_pretrained(str(path), local_files_only=True)
    raw = getattr(config, "id2label", {})
    id2label = {int(key): str(value).strip().lower() for key, value in raw.items()}
    expected = {index: label for index, label in enumerate(MODEL_LABELS)}
    if id2label != expected:
        raise ValueError(f"Unverified model class order: {id2label!r}")
    tokenizer = AutoTokenizer.from_pretrained(
        str(path), local_files_only=True, use_fast=True
    )
    if not tokenizer.is_fast:
        raise ValueError("Fast tokenizer required")
    model = AutoModelForSequenceClassification.from_pretrained(
        str(path), local_files_only=True, use_safetensors=True
    )
    model.to("cpu")
    model.eval()
    parameter_count = sum(parameter.numel() for parameter in model.parameters())
    if not spec["min_parameters"] <= parameter_count <= spec["max_parameters"]:
        raise ValueError(
            f"Parameter count outside registered band: {parameter_count}"
        )
    return tokenizer, model, {
        "parameter_count": parameter_count,
        "config_id2label": {str(k): v for k, v in id2label.items()},
        "max_position_embeddings": getattr(config, "max_position_embeddings", None),
    }


def _softmax_rows(logits: Any) -> list[list[float]]:
    import torch

    return torch.softmax(logits.float(), dim=-1).cpu().tolist()


def _predict_bidirectional(
    tokenizer: Any,
    model: Any,
    pairs: list[tuple[str, str]],
    *,
    batch_size: int,
) -> tuple[list[list[float]], list[list[float]], dict[str, Any]]:
    import torch

    forward_all: list[list[float]] = []
    reverse_all: list[list[float]] = []
    batch_wall_ms: list[float] = []
    input_tokens = 0
    forward_batches = 0
    for offset in range(0, len(pairs), batch_size):
        chunk = pairs[offset:offset + batch_size]
        left = [x[0] for x in chunk] + [x[1] for x in chunk]
        right = [x[1] for x in chunk] + [x[0] for x in chunk]
        started = time.perf_counter()
        encoded = tokenizer(
            left,
            right,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt",
        )
        input_tokens += int(encoded["input_ids"].numel())
        with torch.inference_mode():
            logits = model(**encoded).logits
        probabilities = _softmax_rows(logits)
        n = len(chunk)
        forward_all.extend(probabilities[:n])
        reverse_all.extend(probabilities[n:])
        batch_wall_ms.append((time.perf_counter() - started) * 1000)
        forward_batches += 1
    total_ms = sum(batch_wall_ms)
    directional_inputs = len(pairs) * 2
    ordered = sorted(batch_wall_ms)
    p50 = statistics.median(ordered) if ordered else 0.0
    p95 = ordered[min(len(ordered) - 1, int(0.95 * len(ordered)))] if ordered else 0.0
    return forward_all, reverse_all, {
        "pair_cases": len(pairs),
        "directional_pair_inputs": directional_inputs,
        "forward_batch_count": forward_batches,
        "batch_size_pairs": batch_size,
        "input_token_count": input_tokens,
        "total_batch_wall_ms": total_ms,
        "mean_ms_per_directional_pair": (
            total_ms / directional_inputs if directional_inputs else 0.0
        ),
        "batch_latency_ms": {"p50": p50, "p95": p95},
        "timing_scope": "tokenization + CPU forward + softmax; batched, not end-to-end RAG latency",
    }


def _run_sanity_controls(tokenizer: Any, model: Any) -> list[dict[str, Any]]:
    pairs = [
        (item["premise"], item["hypothesis"])
        for item in SANITY_CONTROLS
    ]
    fwd, rev, _ = _predict_bidirectional(
        tokenizer, model, pairs, batch_size=3
    )
    results = []
    for expected, forward, reverse in zip(
        SANITY_CONTROLS, fwd, rev, strict=True
    ):
        symmetric = [(forward[i] + reverse[i]) / 2 for i in range(3)]
        predicted = MODEL_LABELS[max(range(3), key=lambda i: symmetric[i])]
        results.append({
            "expected": expected["expected"],
            "symmetric_prediction": predicted,
            "forward_prediction": MODEL_LABELS[max(range(3), key=lambda i: forward[i])],
            "reverse_prediction": MODEL_LABELS[max(range(3), key=lambda i: reverse[i])],
            "symmetric_probabilities": {
                label: symmetric[i] for i, label in enumerate(MODEL_LABELS)
            },
        })
    return results


def run_experiment(
    output_dir: Path,
    *,
    model_key: str,
    batch_size: int = 16,
    bootstrap_repetitions: int = 2000,
) -> dict[str, Any]:
    if model_key not in MODEL_SPECS:
        raise ValueError("Unknown model key")
    if not 1 <= batch_size <= 64:
        raise ValueError("Batch size must be between 1 and 64")
    output_dir.mkdir(parents=True, exist_ok=True)
    spec = MODEL_SPECS[model_key]
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    os.environ.setdefault("OMP_NUM_THREADS", "2")
    os.environ.setdefault("MKL_NUM_THREADS", "2")

    import torch
    from huggingface_hub import hf_hub_download

    torch.set_num_threads(2)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass

    dataset_cache = output_dir / ".dataset-cache"
    dataset_started = time.perf_counter()
    dataset_path = Path(hf_hub_download(
        repo_id=DATASET_ID,
        repo_type="dataset",
        filename=DATASET_FILE,
        revision=DATASET_REVISION,
        cache_dir=str(dataset_cache),
    ))
    dataset_download_seconds = time.perf_counter() - dataset_started
    source_sha = _sha_file(dataset_path)
    rows = read_ragability_tsv(dataset_path)
    pairs = build_conflict_pairs(rows)
    manifest = dataset_manifest(rows, pairs, source_sha256=source_sha)
    write_json(output_dir / "dataset_manifest.json", manifest)

    weights_path = output_dir / "model"
    download_started = time.perf_counter()
    model_manifest = _download_model(spec, weights_path)
    model_download_seconds = time.perf_counter() - download_started

    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    load_started = time.perf_counter()
    tokenizer, model, loaded = _load_model(weights_path, spec)
    model_load_seconds = time.perf_counter() - load_started
    model_manifest.update(loaded)

    # Warm up on fixed, generic controls; do not include this in benchmark rows.
    sanity = _run_sanity_controls(tokenizer, model)
    inference_started = time.perf_counter()
    forward, reverse, cost = _predict_bidirectional(
        tokenizer,
        model,
        [(pair.premise, pair.hypothesis) for pair in pairs],
        batch_size=batch_size,
    )
    benchmark_wall_seconds = time.perf_counter() - inference_started
    evaluation = score_model_rows(
        pairs,
        forward,
        reverse,
        bootstrap_repetitions=bootstrap_repetitions,
    )
    cost["benchmark_wall_seconds"] = benchmark_wall_seconds
    cost["dataset_download_seconds"] = dataset_download_seconds
    cost["model_download_seconds"] = model_download_seconds
    cost["model_load_seconds"] = model_load_seconds

    final = {
        "experiment_id": "MICRO-RAGABILITY-01",
        "status": "REAL_CPU_EXTERNAL_PUBLIC_BENCHMARK_PAIRWISE_NLI_ONLY",
        "model": model_manifest,
        "dataset": manifest,
        "evaluation": evaluation,
        "sanity_controls": sanity,
        "inference_cost": cost,
        "environment": {
            "python": platform.python_version(),
            "pytorch": torch.__version__,
            "platform": platform.platform(),
            "cpu_threads": torch.get_num_threads(),
            "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
            "github_sha": os.environ.get("GITHUB_SHA"),
            "hardware": "GitHub-hosted Ubuntu CPU; exact CPU SKU not guaranteed by runner",
        },
        "claims_not_supported": [
            "No human-review agreement was collected by this project.",
            "No sealed or private holdout; the external public dataset is visible.",
            "No retrieval, answer generation, query-conditioned evidence selection or end-to-end RAG cost.",
            "No calibrated probability or operational abstention guarantee.",
            "No source-authority, recency, provenance, or fact-level entailment certification.",
            "No broad multilingual or open-domain generalization claim.",
        ],
    }
    write_json(output_dir / "results.json", final)
    _write_markdown(output_dir / "summary.md", final)
    print(json.dumps({
        "experiment_id": final["experiment_id"],
        "model": {
            "id": model_manifest["id"],
            "revision": model_manifest["revision"],
            "parameters": model_manifest["parameter_count"],
            "weight_bytes": model_manifest["weight_bytes"],
        },
        "dataset": {
            "rows": manifest["row_count"],
            "groups": manifest["unique_conflict_groups"],
            "pairs": manifest["pair_count"],
            "sha256": manifest["source_sha256"],
        },
        "metrics": evaluation["metrics"],
        "group_bootstrap": evaluation["group_bootstrap"],
        "cost": cost,
        "sanity_controls": sanity,
    }, sort_keys=True))
    return final


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-key", choices=sorted(MODEL_SPECS), required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--bootstrap-repetitions", type=int, default=2000)
    args = parser.parse_args()
    run_experiment(
        Path(args.output_dir).resolve(),
        model_key=args.model_key,
        batch_size=args.batch_size,
        bootstrap_repetitions=args.bootstrap_repetitions,
    )


if __name__ == "__main__":
    main()

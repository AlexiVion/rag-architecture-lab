"""Run real SQuAD v2 DEV natural QA on pinned tiny local CPU checkpoints.

No API key, no proprietary inference, no hidden test. Downloads are restricted
to the official public SQuAD v2 file and an exact allowlisted model SHA.
Creates machine-auditable outputs; automatic EM/F1 is not semantic faithfulness.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import resource
import sys
import time
import urllib.request
from pathlib import Path

from raglab.generation.local_transformers import LocalTransformersGenerator
from raglab.micro.experiment import run_micro_suite
from raglab.micro.squad_benchmark import (
    SQUAD_V2_DEV_SHA256,
    SQUAD_V2_DEV_URL,
    load_official_squad_dev,
)
from raglab.micro.squad_metrics import evaluate_squad_traces

MODEL_REVISION = {
    "pythia-14m": (
        "EleutherAI/pythia-14m",
        "cf967c0a9a04383db6f7b1108d86b2962634b4ac",
    ),
    "smollm2-135m": (
        "HuggingFaceTB/SmolLM2-135M-Instruct",
        "12fd25f77366fa6b3b4b768ec3050bf629380bac",
    ),
}

SOURCE_LICENSE = "SQuAD 2.0 CC BY-SA 4.0, Rajpurkar et al. (2018)"


def _file_hash(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1 << 20), b""):
            sha.update(chunk)
    return sha.hexdigest()


def _write(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def download_public_dev(target: Path) -> None:
    if target.exists():
        if _file_hash(target) != SQUAD_V2_DEV_SHA256:
            raise ValueError("Existing SQuAD file did not match pinned SHA256")
        return
    request = urllib.request.Request(
        SQUAD_V2_DEV_URL,
        headers={"User-Agent": "rag-architecture-lab-MICRO-reproducibility/1.0"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        blob = response.read(10_000_000)
    if hashlib.sha256(blob).hexdigest() != SQUAD_V2_DEV_SHA256:
        raise ValueError("Downloaded official SQuAD file SHA256 mismatch")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(blob)


def download_pinned_weights(model_id: str, target: Path) -> dict:
    from huggingface_hub import HfApi, snapshot_download

    repo, revision = MODEL_REVISION[model_id]
    info = HfApi().model_info(repo, revision=revision)
    if info.sha != revision:
        raise ValueError("MODEL_COMMIT_REVISION_CHANGED")
    card = info.card_data
    license_id = (
        card.get("license") if isinstance(card, dict)
        else getattr(card, "license", None)
    )
    if license_id != "apache-2.0":
        raise ValueError(f"Unexpected checkpoint license metadata: {license_id}")
    snapshot_download(
        repo_id=repo,
        revision=revision,
        local_dir=str(target),
        allow_patterns=[
            "config.json", "generation_config.json", "model.safetensors",
            "model.safetensors.index.json", "model-*.safetensors",
            "tokenizer.json", "tokenizer_config.json",
            "special_tokens_map.json", "merges.txt", "vocab.json",
        ],
        ignore_patterns=["*.pt", "*.bin", "*.onnx", "*.py", "README.md"],
    )
    weights = sorted(target.glob("*.safetensors"))
    if not weights:
        raise RuntimeError("No safetensors received")
    if sum(p.stat().st_size for p in weights) > 700_000_000:
        raise RuntimeError("Unexpectedly large model bytes")
    return {
        "repo_id": repo,
        "resolved_revision_sha": info.sha,
        "metadata_license": license_id,
        "weight_files": {
            p.name: {"sha256": _file_hash(p), "bytes": p.stat().st_size}
            for p in weights
        },
    }


class BriefQAGenerator:
    """Strict benchmark prompt wrapper over the already-existing local model."""

    def __init__(self, original: LocalTransformersGenerator) -> None:
        self.inner = original
        self.name = original.name + ":micro-squad-short-qa-v1"
        self.full_prompt_token_counts: list[int] = []

    def count_tokens(self, text: str) -> int:
        return self.inner.count_tokens(text)

    def generate(
        self, *, system_prompt: str, user_prompt: str, max_new_tokens: int = 24
    ) -> str:
        _ = system_prompt
        none = "Evidence:\n(none)" in user_prompt
        if none:
            system = (
                "Answer the question in a short exact phrase from your existing "
                "knowledge. If you do not know, output only INSUFFICIENT_EVIDENCE."
            )
        else:
            system = (
                "Answer using ONLY the evidence provided. Return only the shortest "
                "exact answer phrase. If not supported, output exactly "
                "INSUFFICIENT_EVIDENCE. Do not explain or copy the question."
            )
        prompt = user_prompt.replace(
            "Answer using only the evidence above. Cite source labels inline.",
            "Return only the shortest answer phrase or INSUFFICIENT_EVIDENCE.",
        )
        tokenizer = self.inner._tokenizer
        assert tokenizer is not None
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]
        try:
            rendered = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
        except (AttributeError, ValueError):
            rendered = f"SYSTEM:\n{system}\n\nUSER:\n{prompt}\n\nASSISTANT:\n"
        self.full_prompt_token_counts.append(
            len(tokenizer.encode(rendered, add_special_tokens=False))
        )
        return self.inner.generate(
            system_prompt=system, user_prompt=prompt, max_new_tokens=max_new_tokens
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-id", choices=sorted(MODEL_REVISION), required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--max-cases", type=int, default=32)
    parser.add_argument("--distractors", type=int, default=96)
    parser.add_argument("--max-context-tokens", type=int, default=128)
    parser.add_argument("--max-new-tokens", type=int, default=24)
    args = parser.parse_args()

    output = Path(args.output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    dataset_path = output / "squad2-official-dev.json"
    download_public_dev(dataset_path)
    protocol = load_official_squad_dev(
        dataset_path, max_cases=args.max_cases, distractors=args.distractors
    )
    _write(output / "dataset_manifest.json", protocol.manifest())

    model_path = output / "weights"
    model_data = download_pinned_weights(args.model_id, model_path)
    # Absolutely no network/model hub access after pinned public downloads.
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    os.environ.setdefault("OMP_NUM_THREADS", "2")
    os.environ.setdefault("MKL_NUM_THREADS", "2")
    import torch

    torch.set_num_threads(2)
    underlying = LocalTransformersGenerator(str(model_path))
    started = time.perf_counter()
    underlying._load()
    model_load_s = time.perf_counter() - started
    # Warm-up deliberately contains no SQuAD question or benchmark reference.
    started = time.perf_counter()
    underlying.generate(
        system_prompt="One-token runtime check.",
        user_prompt="Output OK.",
        max_new_tokens=1,
    )
    warmup_s = time.perf_counter() - started

    generator = BriefQAGenerator(underlying)
    started = time.perf_counter()
    result = run_micro_suite(
        protocol.dataset,
        model_id=args.model_id,
        generator=generator,
        modes=("no_retrieval", "naive", "naive_compact", "spans", "spans_compact"),
        top_k=5,
        max_context_tokens=args.max_context_tokens,
        max_new_tokens=args.max_new_tokens,
        count_tokens=generator.count_tokens,
    )
    trial_wall_s = time.perf_counter() - started
    generated = [
        row for row in result["cases"] if row["generation_status"] == "draft_unverified"
    ]
    if len(generated) != len(generator.full_prompt_token_counts):
        raise RuntimeError("Model request count and trace count mismatch")
    for row, total in zip(generated, generator.full_prompt_token_counts):
        row["full_rendered_prompt_tokens"] = total
    metric = evaluate_squad_traces(protocol, result)
    raw_trace = output / "per_case_trace.json"
    _write(raw_trace, result)
    summary = output / "qa_reference_metrics.json"
    _write(summary, metric)

    manifest = {
        "status": "REAL_WEIGHTS_PUBLIC_SQUAD_DEV_PILOT_NOT_HOLDOUT_VALIDATION",
        "model_id": args.model_id,
        "model": model_data,
        "source": {
            "url": SQUAD_V2_DEV_URL,
            "sha256": SQUAD_V2_DEV_SHA256,
            "license": SOURCE_LICENSE,
            "file_bytes": dataset_path.stat().st_size,
        },
        "dataset_manifest_sha256": _file_hash(output / "dataset_manifest.json"),
        "trace_sha256": _file_hash(raw_trace),
        "metrics_sha256": _file_hash(summary),
        "environment": {
            "python": platform.python_version(),
            "cpu": platform.processor(),
            "runner_os": os.getenv("RUNNER_OS"),
            "github_sha": os.getenv("GITHUB_SHA"),
            "torch": torch.__version__,
            "model_load_seconds": model_load_s,
            "single_token_warmup_seconds": warmup_s,
            "trial_wall_seconds": trial_wall_s,
            "process_peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        },
        "limitations": [
            "32-case natural QA exploratory DEV pilot, not a preregistered scientific study",
            "Published SQuAD DEV may be contaminated in model pretraining",
            "Balanced positive/negative by article, not representative prevalence",
            "Gold short-answer EM/F1 is not semantic source-support verification",
            "Model training/instruction differences prohibit direct superiority claims",
            "No GPU, no paid APIs, not canonical Ryzen Windows CPU",
            "Peak RSS high-water covers loading and full run; not per-request",
            "Final prompt tokens counted, timings still small-sample exploratory",
        ],
    }
    _write(output / "integrity_manifest.json", manifest)
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "model": args.model_id,
                "cases": len(protocol.dataset.cases),
                "modes": list(metric["by_mode"]),
                "dataset_sha256": SQUAD_V2_DEV_SHA256,
                "peak_rss_kib": manifest["environment"]["process_peak_rss_kib"],
                "reference_metrics": metric["by_mode"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

"""Optional, bounded, PUBLIC-WEIGHT CPU smoke run on a GitHub-hosted runner.

This script downloads only safetensors/tokenizer/config for two explicitly
allowlisted public model repositories. All generated text is *unverified*
experimental material and is NEVER published as a factual answer.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

MODELS = {
    "pythia-14m": ("EleutherAI/pythia-14m", None),
    "smollm2-135m": (
        "HuggingFaceTB/SmolLM2-135M-Instruct",
        "12fd25f77366fa6b3b4b768ec3050bf629380bac",
    ),
}


def _hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-id", choices=sorted(MODELS), required=True)
    parser.add_argument("--output-dir", default="runs/micro-cpu-pilot")
    args = parser.parse_args()

    repo_id, pinned_revision = MODELS[args.model_id]
    from huggingface_hub import HfApi, snapshot_download

    # For Pythia the API resolves the latest SHA for this isolated smoke; the
    # exact resolved commit is logged. SmolLM2 is pinned explicitly.
    info = HfApi().model_info(repo_id, revision=pinned_revision or "main")
    sha = str(info.sha)
    if pinned_revision and sha != pinned_revision:
        raise RuntimeError("MODEL_REVISION_MISMATCH")
    license_id = str((info.card_data or {}).get("license", "UNKNOWN"))
    if license_id != "apache-2.0":
        raise RuntimeError(f"Unexpected model license metadata: {license_id}")

    target = Path(args.output_dir).resolve()
    target.mkdir(parents=True, exist_ok=True)
    model_dir = target / "weights-local"
    snapshot_download(
        repo_id=repo_id,
        revision=sha,
        local_dir=str(model_dir),
        allow_patterns=[
            "config.json",
            "generation_config.json",
            "model.safetensors",
            "model.safetensors.index.json",
            "model-*.safetensors",
            "tokenizer.json",
            "tokenizer_config.json",
            "special_tokens_map.json",
            "merges.txt",
            "vocab.json",
        ],
        ignore_patterns=["*.pt", "*.bin", "*.onnx", "*.py", "README.md"],
    )
    weight_files = sorted(model_dir.glob("*.safetensors"))
    if not weight_files:
        raise RuntimeError("No safe tensor weights obtained")

    fixture = json.loads(
        Path("experiments/micro_smoke_fixture.json").read_text(encoding="utf-8")
    )
    fixture["cases"] = fixture["cases"][:1]
    prepared_data = target / "one-case-dev.json"
    prepared_data.write_text(json.dumps(fixture, indent=2), encoding="utf-8")

    # Hard offline boundary after explicit allowlisted public checkpoint fetch.
    env = dict(os.environ, HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    env["OMP_NUM_THREADS"] = "2"
    env["MKL_NUM_THREADS"] = "2"
    artifact = target / "per_case_drafts.json"
    cmd = [
        sys.executable,
        "-m",
        "raglab.micro",
        "prepare",
        "--data",
        str(prepared_data),
        "--output",
        str(artifact),
        "--model-id",
        args.model_id,
        "--backend",
        "local",
        "--local-model-dir",
        str(model_dir),
        "--modes",
        "no_retrieval",
        "naive",
        "spans",
        "--max-context-tokens",
        "96",
        "--max-new-tokens",
        "16",
    ]
    subprocess.run(cmd, check=True, env=env, timeout=540)
    result = json.loads(artifact.read_text(encoding="utf-8"))
    assert result["scientific_validation"] == "NOT_RUN"
    assert len(result["cases"]) == 3

    model_manifest = {
        "research_status": "LOCAL_CPU_REAL_MODEL_SMOKE_NOT_SCIENTIFIC_VALIDATION",
        "repository": repo_id,
        "revision_sha": sha,
        "license_metadata": license_id,
        "loaded_checkpoint_files": {
            p.name: {"sha256": _hash(p), "bytes": p.stat().st_size}
            for p in weight_files
        },
        "fixture_sha256": _hash(prepared_data),
        "result_sha256": _hash(artifact),
        "modes": ["no_retrieval", "naive", "spans"],
        "quality_measured": False,
        "gpu_required": False,
        "cpu_environment": "GitHub hosted Linux runner, not canonical Windows Ryzen",
        "limitations": [
            "One synthetic question and three model-generated UNVERIFIED drafts",
            "No source-support labels, no empirical accuracy, no generalization claim",
            "Outputs are CI artifacts, not published website evidence",
            "Model revisions and licenses must be rechecked before redistribution",
        ],
    }
    (target / "manifest.json").write_text(
        json.dumps(model_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "model_id": args.model_id,
                "sha": sha,
                "result": str(artifact),
                "status": model_manifest["research_status"],
            }
        )
    )


if __name__ == "__main__":
    main()

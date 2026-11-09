"""Reproducible *privileged* SQuAD2 DEV oracle and role-prompt diagnosis.

Running this code reads official answer labels to position oracle windows, so
oracle modes are NEVER a deployable or independently measured RAG method.
Results are automatic public DEV reference scores, NOT hallucination validation.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import resource
import time
from pathlib import Path

from raglab.generation.local_transformers import LocalTransformersGenerator
from raglab.micro.experiment import run_micro_suite
from raglab.micro.role_prompts import RoleAdaptedQAGenerator
from raglab.micro.squad_benchmark import load_official_squad_dev, SQUAD_V2_DEV_SHA256
from raglab.micro.squad_metrics import evaluate_squad_traces, paired_group_bootstrap

from squad2_natural_cpu_pilot import (
    BriefQAGenerator,
    MODEL_REVISION,
    SOURCE_LICENSE,
    SQUAD_V2_DEV_URL,
    _file_hash,
    _write,
    download_public_dev,
    download_pinned_weights,
)

MODES = ("spans_compact", "oracle", "oracle_window")
FAMILIES = ("legacy", "role_adapted")


def run_diagnostic(
    *, model_id: str, output: Path, max_cases: int = 32,
    max_new_tokens: int = 32, max_context_tokens: int = 128,
    distractors: int = 96,
) -> dict:
    """Return a diagnostic manifest after real inference; never a safety badge."""
    if model_id not in MODEL_REVISION:
        raise ValueError("Model must be a pinned approved public checkpoint")
    output.mkdir(parents=True, exist_ok=True)
    dataset_file = output / "squad2-dev-original.json"
    download_public_dev(dataset_file)
    protocol = load_official_squad_dev(
        dataset_file, max_cases=max_cases, distractors=distractors
    )
    _write(output / "dataset_manifest.json", protocol.manifest())
    gold_answers = {
        cid: ref.answers for cid, ref in protocol.references.items()
    }
    weights = download_pinned_weights(model_id, output / "weights")
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    os.environ.setdefault("OMP_NUM_THREADS", "2")
    os.environ.setdefault("MKL_NUM_THREADS", "2")
    import torch

    torch.set_num_threads(2)
    original = LocalTransformersGenerator(str(output / "weights"))
    t0 = time.perf_counter()
    original._load()
    model_load_s = time.perf_counter() - t0
    t1 = time.perf_counter()
    original.generate(
        system_prompt="CPU single-token warmup.",
        user_prompt="OK",
        max_new_tokens=1,
    )
    warmup_s = time.perf_counter() - t1

    roles = {
        "pythia-14m": "base",
        "smollm2-135m": "instruct",
    }
    engines = {
        "legacy": BriefQAGenerator(original),
        "role_adapted": RoleAdaptedQAGenerator(
            original, model_role=roles[model_id]
        ),
    }
    per_condition = {}
    all_pair_rows = []
    for family in FAMILIES:
        engine = engines[family]
        started = time.perf_counter()
        result = run_micro_suite(
            protocol.dataset,
            model_id=model_id,
            generator=engine,
            modes=MODES,
            top_k=5,
            max_context_tokens=max_context_tokens,
            max_new_tokens=max_new_tokens,
            count_tokens=engine.count_tokens,
            gold_answers_by_case=gold_answers,
        )
        duration = time.perf_counter() - started
        generated_rows = [
            row for row in result["cases"]
            if row["generation_status"] == "draft_unverified"
        ]
        if len(generated_rows) != len(engine.full_prompt_token_counts):
            raise RuntimeError("Full prompt-token audit count mismatch")
        for row, count in zip(generated_rows, engine.full_prompt_token_counts):
            row["full_rendered_prompt_tokens"] = count
            row["prompt_family"] = family
        for row in result["cases"]:
            row["prompt_family"] = family

        # Fail closed if the gold-window selector leaked privileged info to a
        # regular retrieval branch, or claimed an oracle success without source.
        for row in result["cases"]:
            if row["mode"] == "spans_compact" and row["oracle_used"]:
                raise RuntimeError("Oracle privilege leaked into deployable retrieval")
            if row["mode"] == "oracle_window":
                if not row["oracle_used"]:
                    raise RuntimeError("Gold-answer context missing oracle marker")
                if row["oracle_gold_literal_visible"] is True:
                    ref = protocol.references[row["case_id"]]
                    if not ref.answerable:
                        raise RuntimeError("Negative question marked gold-visible")

        metric = evaluate_squad_traces(protocol, result)
        trace = output / f"{family}_trace.json"
        scored = output / f"{family}_qa_metrics.json"
        _write(trace, result)
        _write(scored, metric)
        for row in metric["cases"]:
            all_pair_rows.append(
                {
                    "case_id": row["case_id"],
                    "article_group": row["article_group"],
                    "is_scored": row["is_scored"],
                    "reference_f1": row["reference_f1"],
                    "mode": family + "__" + row["mode"],
                }
            )
        visible = [
            row for row in metric["cases"]
            if row["mode"] == "oracle_window" and row["answerable"]
        ]
        per_condition[family] = {
            "status": "PUBLIC_DEV_AUTOMATIC_REFERENCE_METRICS_NOT_SEMANTIC_SUPPORT",
            "model_role": roles[model_id],
            "elapsed_wall_seconds": duration,
            "trace_sha256": _file_hash(trace),
            "metrics_sha256": _file_hash(scored),
            "oracle_answer_visible_positive": sum(
                row["oracle_gold_literal_visible"] is True for row in visible
            ),
            "oracle_positive_cases": len(visible),
            "by_mode": metric["by_mode"],
            "caveat": "Gold oracle windows are privileged, diagnostic only",
        }

    comparisons = tuple(
        ("legacy__" + mode, "role_adapted__" + mode) for mode in MODES
    )
    interval = paired_group_bootstrap(
        all_pair_rows, iterations=1000, comparisons=comparisons
    )
    _write(output / "paired_prompt_differences.json", interval)
    manifest = {
        "status": "DEV_ORACLE_AND_ROLE_PROMPT_DIAGNOSTIC_NOT_SCIENTIFIC_VALIDATION",
        "research_phase": "MICRO_GENERATOR_FAILURE_DIAGNOSIS",
        "model_id": model_id,
        "model": weights,
        "dataset": {
            **protocol.manifest(),
            "official_source": SQUAD_V2_DEV_URL,
            "original_source_sha256": SQUAD_V2_DEV_SHA256,
            "license": SOURCE_LICENSE,
        },
        "config": {
            "modes": list(MODES),
            "prompt_families": list(FAMILIES),
            "max_cases": max_cases,
            "max_new_tokens": max_new_tokens,
            "max_context_tokens": max_context_tokens,
            "question_count_per_family": len(protocol.dataset.cases),
            "gold_window_is_privileged": True,
            "positive_oracle_includes_gold_answer": True,
            "negative_oracle_uses_original_paragraph_not_corpus_wide_proof": True,
        },
        "conditions": per_condition,
        "paired_prompt_differences": interval,
        "environment": {
            "python": platform.python_version(),
            "torch": str(torch.__version__),
            "runner_os": os.environ.get("RUNNER_OS"),
            "github_sha": os.environ.get("GITHUB_SHA"),
            "model_load_seconds": model_load_s,
            "one_token_warmup_seconds": warmup_s,
            "whole_process_peak_rss_kib": resource.getrusage(
                resource.RUSAGE_SELF
            ).ru_maxrss,
        },
        "limitations": [
            "All evaluation questions from exposed public SQuAD2 DEV",
            "SQuAD original-paragraph unanswerability is not expanded-corpus unanswerability",
            "Gold annotated oracle windows use privileged answer labels, not a retriever",
            "No human-rated independent faithfulness, support, abstention or calibration",
            "Base-LM vs instruct checkpoints have different training and tokenizer semantics",
            "New prompts were developed after observing earlier DEV failures; this is optimization-on-DEV",
            "Descriptive article-group bootstrap is not a sealed holdout significance test",
            "No pretrained contamination control, no independent deployment approval",
            "GitHub CPU is not the canonical owner's Ryzen machine; energy not measured",
        ],
    }
    _write(output / "integrity_manifest.json", manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-id", choices=sorted(MODEL_REVISION), required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--max-cases", type=int, default=32)
    parser.add_argument("--max-new-tokens", type=int, default=32)
    args = parser.parse_args()
    result = run_diagnostic(
        model_id=args.model_id,
        output=Path(args.output_dir).resolve(),
        max_cases=args.max_cases,
        max_new_tokens=args.max_new_tokens,
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "model_id": args.model_id,
                "conditions": {
                    family: {
                        "visible": data["oracle_answer_visible_positive"],
                        "positive": data["oracle_positive_cases"],
                        "by_mode": data["by_mode"],
                    }
                    for family, data in result["conditions"].items()
                },
                "paired_prompt_differences": result["paired_prompt_differences"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()

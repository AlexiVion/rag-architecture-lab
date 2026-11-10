"""Real CPU experiment: new fictional whole-corpus answer/absence/contradiction.

MiniLM is SQuAD2 trained. Its performance on this artificial *out-of-SQuAD*
corpus is a diagnostic of distribution sensitivity, NOT a scientifically
independent human-labeled out-of-domain benchmark.

The readout compares top1/top3 and calibration-gated versions with a simple
template-rule shortcut detector and refuse-all baseline; official weights
are pinned and hash-verified. Nothing needs the owner's laptop.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import resource
import time
from dataclasses import replace
from pathlib import Path
from statistics import mean

from raglab.core import Document
from raglab.retrieval import BM25Retriever
from raglab.micro.cf_evaluation import (
    Prediction, calibrate, format_outcome, gate_prediction, is_refusal,
    locked_threshold, summarize, template_rule, detects_source_conflict,
)
from raglab.micro.counterfactual import (
    build_counterfactual_corpus, protocol_manifest,
)

from minilm_extractive_cpu_pilot import SmallExtractiveReader, download_reader


def _write(path: Path, obj: object) -> None:
    path.write_text(
        json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n", encoding="utf-8"
    )


def _sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _picked(
    source_outputs: list[tuple[str, object, int, float]],
    *,
    take: int,
    docs: dict[str, Document],
) -> Prediction:
    inspected = source_outputs[:take]
    # Each candidate input was computed once. This is a cached counterfactual
    # inference-cost comparison, not an independently timed deployed router.
    best = max(inspected, key=lambda row: row[1].logit_margin) if inspected else None
    count = len(inspected)
    tokens = sum(int(x[2]) for x in inspected)
    cpu = sum(float(x[3]) for x in inspected)
    if best is None or not best[1].answered or best[1].logit_margin <= 0:
        return Prediction(
            "INSUFFICIENT_EVIDENCE", None, None, None,
            best[1].logit_margin if best is not None else None,
            tokens, cpu, False, count,
        )
    doc_id, original, _, _ = best
    start, end = original.start, original.end
    if start is None or end is None or docs[doc_id].text[start:end] != original.text:
        raise ValueError("Reader produced non-verbatim source text")
    return Prediction(
        original.text, doc_id, start, end,
        original.logit_margin, tokens, cpu, True, count,
    )


def extract_split(reader: SmallExtractiveReader, partition) -> dict:
    docs = {doc.id: doc for doc in partition.documents}
    retrieval = BM25Retriever()
    retrieval.index(partition.documents)
    outputs: dict[str, list[Prediction]] = {
        "top1": [], "top3": [], "top1_conflict_guard": [],
        "top3_conflict_guard": [], "template_rule_top3": [], "refuse_all": [],
    }
    rows_cases = []
    per_case_search_ms = []
    per_case_rule_ms = []
    for case in partition.cases:
        start = time.perf_counter()
        ranked = retrieval.retrieve(case.question, 3)
        per_case_search_ms.append((time.perf_counter() - start) * 1000)
        candidates = []
        for candidate in ranked:
            doc = docs[candidate.doc_id]
            pred, tokens, ms = reader.read(case.question, doc.text)
            if pred.answered:
                if pred.start is None or pred.end is None:
                    raise ValueError("Reader missing source offsets")
                if doc.text[pred.start:pred.end] != pred.text:
                    raise ValueError("Reader span is not exact original source text")
            candidates.append((doc.id, pred, tokens, ms))
        top1 = _picked(candidates, take=1, docs=docs)
        top3 = _picked(candidates, take=3, docs=docs)
        outputs["top1"].append(top1)
        outputs["top3"].append(top3)
        # This guard is hand-engineered from exposed synthetic templates:
        # it is cheap but NOT an open-domain contradiction resolver.
        conflict_seen = detects_source_conflict(
            case.question, case.entity, [docs[x.doc_id] for x in ranked]
        )
        for policy, base in (
            ("top1_conflict_guard", top1), ("top3_conflict_guard", top3)
        ):
            guarded = (
                replace(
                    base,
                    text="INSUFFICIENT_EVIDENCE",
                    doc_id=None, start=None, end=None, source_exact=False,
                ) if conflict_seen else base
            )
            outputs[policy].append(guarded)
        start = time.perf_counter()
        rule = template_rule(
            case.question, case.entity,
            [docs[x.doc_id] for x in ranked],
        )
        per_case_rule_ms.append((time.perf_counter() - start) * 1000)
        outputs["template_rule_top3"].append(rule)
        outputs["refuse_all"].append(
            Prediction("INSUFFICIENT_EVIDENCE", None, None, None, None, 0, 0.0, False, 0)
        )
        rows_cases.append({
            "case_id": case.case_id, "retrieved_ids": [r.doc_id for r in ranked],
            "eligible_source_recall_top1": (
                bool(ranked) and ranked[0].doc_id in case.eligible_document_ids
            ),
            "eligible_source_recall_top3": bool(
                set(r.doc_id for r in ranked) & set(case.eligible_document_ids)
            ),
            "retrieval_ms": per_case_search_ms[-1],
            "synthetic_template_conflict_seen": conflict_seen,
            "rule_wall_ms": per_case_rule_ms[-1],
        })
    return {
        "partition": partition,
        "predictions": outputs,
        "retrieval_rows": rows_cases,
        "search_ms": per_case_search_ms,
        "rule_ms": per_case_rule_ms,
    }


def report_policy(part, predictions: list[Prediction], retrieval_rows: list[dict]) -> dict:
    rows = [format_outcome(case, pred) for case, pred in zip(part.cases, predictions)]
    if len(rows) != len(part.cases):
        raise RuntimeError("Case count and prediction count mismatch")
    summary = summarize(rows)
    positives = [
        row for row, case in zip(retrieval_rows, part.cases) if case.kind == "answer"
    ]
    summary.update({
        "eligible_source_recall_top1_positive": mean(
            r["eligible_source_recall_top1"] for r in positives
        ),
        "eligible_source_recall_top3_positive": mean(
            r["eligible_source_recall_top3"] for r in positives
        ),
        "methodological_scope": "programmatic fiction labels; not human semantic validity",
    })
    return {"summary": summary, "cases": rows}


def run_experiment(out: Path, *, seed: int = 20261109) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    parts = build_counterfactual_corpus(seed)
    manifest = protocol_manifest(parts)
    _write(out / "corpus_manifest.json", manifest)
    # This intentionally exposes all generated labels and sources in the
    # research artifact: *audit* is a reproducible partition, NOT blind holdout.
    for split, part in parts.items():
        _write(
            out / f"{split}_generated.json",
            {
                "partition": part.as_dict(),
                "documents": [
                    {"id": x.id, "title": x.title, "text": x.text}
                    for x in part.documents
                ],
                "cases": [x.as_dict() for x in part.cases],
            },
        )

    weights_dir = out / "weights"
    model_manifest = download_reader(weights_dir)
    if model_manifest["revision"] != "934656cdda79824eabf503ed56e15c01ddbdbe3f":
        raise ValueError("Unexpected MiniLM exact checkpoint revision")
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    os.environ.setdefault("OMP_NUM_THREADS", "2")
    os.environ.setdefault("MKL_NUM_THREADS", "2")
    import torch

    torch.set_num_threads(2)
    load_begin = time.perf_counter()
    reader = SmallExtractiveReader(weights_dir)
    load_secs = time.perf_counter() - load_begin
    reader.read("What color is the peach?", "The peach is yellow.")

    measurements = {}
    for split in ("dev", "calibration", "audit"):
        start = time.perf_counter()
        result = extract_split(reader, parts[split])
        result["split_wall_seconds"] = time.perf_counter() - start
        measurements[split] = result

    # All policy selection occurs using CALIBRATION LABELS ONLY.
    calibration = {}
    for policy in ("top1", "top3"):
        calibration[policy] = calibrate(
            list(parts["calibration"].cases),
            measurements["calibration"]["predictions"][policy],
            max_wrong_accept_rate=0.15,
            minimum_accepted=5,
        )
    _write(out / "frozen_calibration.json", calibration)
    frozen_sha256 = _sha_file(out / "frozen_calibration.json")

    per_split = {}
    for split in ("dev", "calibration", "audit"):
        m = measurements[split]
        part = parts[split]
        policies = {}
        for policy, predictions in m["predictions"].items():
            policies[policy] = report_policy(part, predictions, m["retrieval_rows"])
        for policy in ("top1", "top3"):
            gate = locked_threshold(calibration[policy])
            gated = [gate_prediction(pred, gate) for pred in m["predictions"][policy]]
            policies[f"{policy}_calibrated"] = report_policy(
                part, gated, m["retrieval_rows"]
            )
        per_split[split] = {
            "partition_sha256": part.sha256,
            "partition": part.as_dict(),
            "policies": policies,
            "experiment_wall_seconds": m["split_wall_seconds"],
            "mean_retrieval_ms": mean(m["search_ms"]),
            "mean_template_rule_wall_ms": mean(m["rule_ms"]),
            "calibration_origin_sha256": frozen_sha256,
        }

    _write(out / "policy_results.json", per_split)
    final = {
        "status": "REAL_CPU_FICTIONAL_CORPUS_ONLY_NOT_HUMAN_VALIDATED",
        "model": model_manifest,
        "corpus": manifest,
        "frozen_calibration_sha256": frozen_sha256,
        "generated_artifact_sha256": {
            f"{split}_generated.json": _sha_file(out / f"{split}_generated.json")
            for split in parts
        },
        "policy_results_sha256": _sha_file(out / "policy_results.json"),
        "configuration": {
            "model": "deepset/minilm-uncased-squad2",
            "model_training": "SQuAD2 task-specific QA; fictional corpus is distribution shift",
            "policies": (
                "top1", "top3", "top1_conflict_guard", "top3_conflict_guard",
                "top1_calibrated", "top3_calibrated",
                "template_rule_top3", "refuse_all",
            ),
            "partition_usage": "DEV measured, CALIBRATION optimizes threshold, AUDIT evaluated after frozen calibration",
            "audit_is_not_sealed_holdout": True,
            "calibration_threshold_choices": [0, 1, 2, 3, 5, 8, 12, 20, 30, 50, "refuse_all"],
            "max_wrong_accept_rate": 0.15,
            "minimum_calibration_accepted": 5,
            "all_inference_cpu": True,
            "candidate_doc_count": 3,
            "qa_input_token_limit": 384,
        },
        "environment": {
            "python": platform.python_version(),
            "pytorch": torch.__version__,
            "os": platform.platform(),
            "github_sha": os.environ.get("GITHUB_SHA"),
            "cpu_threads": 2,
            "model_load_seconds": load_secs,
            "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        },
        "conclusions_not_supported": [
            "No independently human-labeled domain generalization established",
            "Generated audit labels and templates are visible, not blind holdout",
            "Template-rule baseline exploits synthetic sentence regularity",
            "Source exact-copy is not semantic entailment",
            "SQuAD-finetuned reader is not training-matched with free generator models",
            "No inference energy measurements; CPU process RSS is stack-wide",
            "Calibration target is conditional observed wrong acceptance, not statistical risk guarantee",
            "Copied original spans must not be published as verified business facts",
        ],
    }
    _write(out / "integrity_manifest.json", final)
    print(json.dumps({
        "status": final["status"],
        "model_revision": model_manifest["revision"],
        "source_fingerprint": {
            k: v.sha256 for k, v in parts.items()
        },
        "calibration_sha": frozen_sha256,
        "audit": {
            mode: {
                "strict_accuracy": r["summary"]["strict_accuracy"],
                "accepted": r["summary"]["accepted"],
                "wrong_accepts": r["summary"]["wrong_accepts"],
                "answerable_correct": r["summary"]["answerable_correct"],
                "conflict_correct_refusals": r["summary"]["conflict_correct_refusals"],
                "total_reader_forwards": r["summary"]["total_reader_forwards"],
                "reader_call_wall_ms": r["summary"]["total_reader_call_wall_ms"],
            } for mode, r in per_split["audit"]["policies"].items()
        },
    }, sort_keys=True))
    return final


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    run_experiment(Path(args.output_dir).resolve())


if __name__ == "__main__":
    main()

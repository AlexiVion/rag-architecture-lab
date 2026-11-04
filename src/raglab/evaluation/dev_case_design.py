from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from raglab.context import ContextBuilder
from raglab.core import Document, SearchResult
from raglab.core.fingerprint import fingerprint_documents
from raglab.datasets import BenchmarkDataset
from raglab.evaluation.semantic_review import prepare_review_packet

ARM_WITH_REFERENCE = "qrel_relevant_candidate"
ARM_ALTERNATE = "cross_query_alternate_candidate"
ARM_EMPTY = "no_context_control"
ARMS = (ARM_WITH_REFERENCE, ARM_ALTERNATE, ARM_EMPTY)


def _stable_rank(seed: int, value: str) -> str:
    return hashlib.sha256(f"{seed}|{value}".encode("utf-8")).hexdigest()


def _candidate_packet(
    dataset_id: str,
    query_id: str,
    query_text: str,
    source: Document | None,
    *,
    arm: str,
    case_id: str,
) -> dict[str, Any]:
    if source is None:
        context_sources: list[dict[str, Any]] = []
    else:
        builder = ContextBuilder(max_chars=2500, per_source_chars=2100)
        bundle = builder.build(
            {source.id: source},
            [SearchResult(doc_id=source.id, score=0.0, rank=1)],
        )
        context_sources = [
            {
                "label": item.label,
                "doc_id": item.doc_id,
                "title": item.title,
                "text": item.text,
            }
            for item in bundle.sources
        ]
        if not context_sources:
            raise ValueError("Selected document yielded an empty review context")

    packet = prepare_review_packet({
        "dataset": dataset_id,
        "query_id": query_id,
        "result": {
            "question": query_text,
            "answer": "",
            "sources": context_sources,
            "retrieval_name": "controlled_dev_context_not_a_retrieval_run",
            "generator_name": "not_run",
            "output_status": "not_run_dev_context",
        },
    })
    packet["provenance"]["case_id"] = case_id
    packet["provenance"]["review_arm"] = arm
    packet["instructions"].append(
        "This is an evidence-review case with no generated answer; "
        "no correctness, entailment, or expected behavior is auto-labeled."
    )
    return packet


def design_dev_cases(
    dataset: BenchmarkDataset,
    *,
    query_count: int = 6,
    seed: int = 17,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """Select candidates solely from development data, without semantic labels.

    A qrel-positive article is not necessarily enough to resolve a scientific
    claim; a different-query article is NOT automatically irrelevant; and an
    empty context is a controlled absence of evidence, not a generation result.
    """
    if dataset.id != "beir/scifact/train":
        raise ValueError("Never build review/calibration cases from held-out test")
    if query_count < 2:
        raise ValueError("At least two training queries are required")
    docs = {doc.id: doc for doc in dataset.documents}
    eligible: list[tuple[str, str, str]] = []
    for query in dataset.queries:
        gold = [
            (doc_id, relevance)
            for doc_id, relevance in dataset.qrels.get(query.id, {}).items()
            if doc_id in docs and relevance > 0
        ]
        if not gold:
            continue
        # Pick a reference document deterministically without using stance labels.
        gold.sort(key=lambda item: (-item[1], item[0]))
        eligible.append((query.id, query.text, gold[0][0]))
    eligible.sort(key=lambda item: (_stable_rank(seed, item[0]), item[0]))
    if len(eligible) < query_count:
        raise ValueError("Not enough TRAIN queries with accessible qrel documents")
    selected = eligible[:query_count]

    cases: list[dict[str, Any]] = []
    packets: dict[str, dict[str, Any]] = {}
    for index, (query_id, query_text, gold_id) in enumerate(selected, start=1):
        qrel_ids = set(dataset.qrels[query_id])
        alternative_id = next(
            (
                other_gold_id for other_id, _, other_gold_id in selected
                if other_id != query_id and other_gold_id not in qrel_ids
            ),
            None,
        )
        if alternative_id is None:
            raise ValueError("Cannot find an independent cross-query candidate")
        selections = (
            (ARM_WITH_REFERENCE, gold_id),
            (ARM_ALTERNATE, alternative_id),
            (ARM_EMPTY, None),
        )
        for arm, doc_id in selections:
            case_id = f"DEV{index:03d}_{arm}"
            source = docs[doc_id] if doc_id else None
            packet = _candidate_packet(
                dataset.id, query_id, query_text, source,
                arm=arm, case_id=case_id,
            )
            packets[case_id] = packet
            cases.append({
                "case_id": case_id,
                "query_id": query_id,
                "arm": arm,
                "source_doc_ids": [] if doc_id is None else [doc_id],
                "source_count": len(packet["sources"]),
                "review_packet_filename": case_id + ".json",
                "human_labels_assigned": False,
                "reference_qrels_used_only_for_selection": (
                    arm == ARM_WITH_REFERENCE
                ),
            })

    manifest = {
        "schema_version": 1,
        "experiment_id": "M2-DEV-EVIDENCE-01",
        "dataset": dataset.id,
        "query_count": query_count,
        "case_count": len(cases),
        "arm_counts": {arm: query_count for arm in ARMS},
        "seed": seed,
        "selection_method": "sha256(seed|query_id), ascending",
        "corpus_fingerprint": fingerprint_documents(dataset.documents),
        "source": "ir_datasets SciFact TRAIN positive relevance qrels",
        "warnings": [
            "SciFact TEST must never be used for development case selection.",
            "Qrels select a plausible relevant passage, NOT a proof of entailment.",
            "Cross-query alternatives are not certified irrelevant or contradictory.",
            "Empty contexts are synthetic missing-evidence controls.",
            "No generation or automatic semantic judgments occur in this study.",
            "All source and expected behavior labels require independent review.",
        ],
        "cases": cases,
    }
    return manifest, packets


def write_dev_cases(
    manifest: dict[str, Any],
    packets: dict[str, dict[str, Any]],
    *,
    output_dir: Path,
) -> Path:
    """Write new, private output files; refuse existing output directories."""
    if output_dir.exists():
        raise FileExistsError(
            f"Output directory already exists; refusing overwrite: {output_dir}"
        )
    ids = [case["case_id"] for case in manifest["cases"]]
    if len(ids) != len(set(ids)) or set(ids) != set(packets):
        raise ValueError("Manifest and packet IDs differ or contain duplicates")
    output_dir.mkdir(parents=True, exist_ok=False)
    for case_id in ids:
        (output_dir / (case_id + ".json")).write_text(
            json.dumps(packets[case_id], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return output_dir

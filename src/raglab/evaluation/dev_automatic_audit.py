from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from raglab.context import ContextBuilder
from raglab.core import SearchResult
from raglab.core.fingerprint import fingerprint_documents
from raglab.datasets import BenchmarkDataset
from raglab.evaluation.dev_case_design import (
    ARM_ALTERNATE,
    ARM_EMPTY,
    ARM_WITH_REFERENCE,
    ARMS,
)
from raglab.evaluation.dev_review_batch import _load_suite


def _source_record(document) -> dict[str, str]:
    context = ContextBuilder(max_chars=2500, per_source_chars=2100).build(
        {document.id: document},
        [SearchResult(doc_id=document.id, score=0.0, rank=1)],
    )
    if len(context.sources) != 1:
        raise ValueError(f"Document {document.id} cannot form a review source")
    item = context.sources[0]
    return {
        "label": item.label,
        "doc_id": item.doc_id,
        "title": item.title,
        "text": item.text,
    }


def audit_dev_suite(suite: Path, dataset: BenchmarkDataset) -> dict[str, Any]:
    """Verify all saved TRAIN contexts without inferring any biomedical truth.

    Positive qrels mean a document was marked relevant for retrieval. They do
    not establish whether the scientific proposition is entailed or refuted.
    A zero-context rule can abstain deterministically; nonempty contexts
    remain semantically unassessed.
    """
    manifest = _load_suite(suite)
    if dataset.id != "beir/scifact/train":
        raise ValueError("Auto-audit is restricted to SciFact TRAIN")
    actual_fingerprint = fingerprint_documents(dataset.documents)
    if manifest.get("corpus_fingerprint") != actual_fingerprint:
        raise ValueError("Corpus fingerprint mismatch; do not compare revisions")
    documents = {doc.id: doc for doc in dataset.documents}
    queries = {q.id: q.text for q in dataset.queries}
    cases = manifest["cases"]
    if len(cases) != manifest.get("case_count"):
        raise ValueError("Case count does not match manifest")
    if len({c["query_id"] for c in cases}) != manifest.get("query_count"):
        raise ValueError("Query count does not match manifest")

    arms: Counter[str] = Counter()
    observed_per_query: Counter[tuple[str, str]] = Counter()
    records: list[dict[str, Any]] = []
    for case in cases:
        case_id = case["case_id"]
        query_id = str(case.get("query_id", ""))
        arm = case.get("arm")
        if arm not in ARMS:
            raise ValueError(f"Unexpected arm {arm} at {case_id}")
        if query_id not in queries:
            raise ValueError(f"Missing TRAIN query {query_id}")
        arms[arm] += 1
        observed_per_query[(query_id, arm)] += 1
        path = suite / case["review_packet_filename"]
        packet = json.loads(path.read_text(encoding="utf-8"))
        provenance = packet.get("provenance", {})
        if not isinstance(provenance, dict):
            raise ValueError(f"Malformed provenance at {case_id}")
        if (
            provenance.get("dataset") != "beir/scifact/train"
            or provenance.get("case_id") != case_id
            or provenance.get("review_arm") != arm
            or packet.get("question") != queries[query_id]
        ):
            raise ValueError(f"Packet/proposition provenance mismatch at {case_id}")
        if (
            packet.get("candidate_text") != ""
            or packet.get("claims") != []
            or provenance.get("generator_name") != "not_run"
        ):
            raise ValueError(f"Unexpected generated candidate at {case_id}")
        review = packet.get("review", {})
        if (
            not isinstance(review, dict)
            or review.get("reviewer") != ""
            or review.get("expected_behavior") != "unreviewed"
        ):
            raise ValueError(f"An original case was altered with annotations: {case_id}")
        sources = packet.get("sources")
        doc_ids = case.get("source_doc_ids")
        if not isinstance(sources, list) or not isinstance(doc_ids, list):
            raise ValueError(f"Invalid source structure at {case_id}")
        if len(sources) != len(doc_ids) or len(sources) != case.get("source_count"):
            raise ValueError(f"Manifest/source count mismatch at {case_id}")
        if any(not isinstance(src, dict) for src in sources):
            raise ValueError(f"Malformed source object at {case_id}")
        actual_ids = [str(src.get("doc_id")) for src in sources]
        if actual_ids != doc_ids:
            raise ValueError(f"Source document mismatch at {case_id}")
        if len(doc_ids) > 1:
            raise ValueError("This controlled suite permits at most one source")
        if bool(case.get("reference_qrels_used_only_for_selection")) != (
            arm == ARM_WITH_REFERENCE
        ):
            raise ValueError(f"Qrel selection provenance mismatch: {case_id}")
        qrels = dataset.qrels.get(query_id, {})
        if arm == ARM_EMPTY:
            if doc_ids:
                raise ValueError(f"No-context case is not empty: {case_id}")
        else:
            if len(doc_ids) != 1 or doc_ids[0] not in documents:
                raise ValueError(f"Missing document in {case_id}")
            expected = _source_record(documents[doc_ids[0]])
            for key, value in expected.items():
                if str(sources[0].get(key)) != value:
                    raise ValueError(f"Original source {key} changed: {case_id}")
            if sources[0].get("relevance") != "unreviewed":
                raise ValueError(f"Original source labels changed: {case_id}")
            if arm == ARM_WITH_REFERENCE and qrels.get(doc_ids[0], 0) <= 0:
                raise ValueError(f"Reference source lacks a positive TRAIN qrel: {case_id}")
            if arm == ARM_ALTERNATE and doc_ids[0] in qrels:
                raise ValueError(f"Alternative has an own-query qrel: {case_id}")

        # These describe runtime control-flow, not biomedical entailment.
        gate = "abstain_no_context" if arm == ARM_EMPTY else "not_assessed_nonempty"
        records.append({
            "case_id": case_id,
            "query_id": query_id,
            "arm": arm,
            "source_document_ids": doc_ids,
            "source_text_sha256": [
                hashlib.sha256(src["text"].encode("utf-8")).hexdigest()
                for src in sources
            ],
            "qrel_positive_candidate_for_own_query": (
                qrels.get(doc_ids[0], 0) > 0 if doc_ids else False
            ),
            "structural_integrity": "pass",
            "deterministic_no_context_gate": gate,
            "semantic_relevance": "not_evaluated",
            "semantic_entailment": "not_evaluated",
            "contradiction": "not_evaluated",
            "expected_behavior_from_human": "unreviewed",
        })

    for query_id in {c["query_id"] for c in cases}:
        for arm in ARMS:
            if observed_per_query[(query_id, arm)] != 1:
                raise ValueError(f"Expected one {arm} for TRAIN query {query_id}")
    if dict(arms) != manifest.get("arm_counts"):
        raise ValueError("Arm counts do not match manifest")
    if len(list(suite.glob("DEV*.json"))) != len(cases):
        raise ValueError("Unexpected number of original DEV packet files")
    reviews = suite / "human-reviews"
    human_snapshots = len(list(reviews.glob("*.json"))) if reviews.is_dir() else 0
    return {
        "experiment_id": "M2-DEV-EVIDENCE-01",
        "dataset": "beir/scifact/train",
        "status": "structural_pass_semantics_not_evaluated",
        "query_count": manifest["query_count"],
        "case_count": len(cases),
        "arm_counts": dict(arms),
        "corpus_fingerprint_verified": True,
        "source_passages_verified_against_corpus": True,
        "no_context_control_count": arms[ARM_EMPTY],
        "semantic_unassessed_count": len(cases),
        "existing_human_review_files": human_snapshots,
        "notes": [
            "All original cases and source snippets were structurally checked.",
            "No context deterministically triggers the no-evidence abstention rule.",
            "Qrels indicate retrieval relevance, NOT sufficient evidence or entailment.",
            "Lack of a qrel does NOT mean irrelevant or contradicts the proposition.",
            "No LLM answer, entailment judge, embeddings or cross-encoder ran.",
            "No machine results were represented as human review annotations.",
            "Human expected behavior, claim support and task accuracy remain unassessed.",
        ],
        "cases": records,
    }


def audit_report_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# M2-DEV-EVIDENCE-01 — automatic structural audit",
        "",
        f"Status: **{report['status']}**.",
        f"Dataset: `{report['dataset']}`.",
        f"Corpus fingerprint verified: {report['corpus_fingerprint_verified']}.",
        f"Contexts checked: {report['case_count']} in {report['query_count']} TRAIN propositions.",
        "",
        "| Source scenario | Count | Interpretation |",
        "|---|---:|---|",
        f"| Qrel-positive candidate | {report['arm_counts'][ARM_WITH_REFERENCE]} "
        "| Retrieval relevance annotation; entailment unknown |",
        f"| Cross-query alternative | {report['arm_counts'][ARM_ALTERNATE]} "
        "| No own-query positive qrel; true relevance unknown |",
        f"| Empty context | {report['arm_counts'][ARM_EMPTY]} "
        "| Operational control: abstain without generator |",
        "",
        "**No semantic conclusions were automatically assigned.**",
        "",
        "## Case outcomes (mechanical controls only)",
        "",
        "| Case ID | Source arm | Source count | Context gate | Semantic status |",
        "|---|---|---:|---|---|",
    ]
    for item in report["cases"]:
        lines.append(
            f"| {item['case_id']} | {item['arm']} | "
            f"{len(item['source_document_ids'])} | "
            f"{item['deterministic_no_context_gate']} | not_evaluated |"
        )
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {note}" for note in report["notes"])
    return "\n".join(lines) + "\n"

from __future__ import annotations

from collections.abc import Collection, Mapping
from typing import Any

from raglab.citations import validate_citations


def audit_answer_artifact(
    artifact: Mapping[str, Any],
    *,
    relevant_doc_ids: Collection[str] | None = None,
) -> dict[str, Any]:
    """Audit saved V2 artifacts without a generator or hidden semantic judge.

    When provided, qrels document IDs are used only for offline *evaluation*,
    never at inference time. This returns diagnostic signals, not faithfulness.
    """
    result = artifact.get("result")
    if not isinstance(result, dict):
        raise ValueError("Artifact must contain a result object")
    answer = result.get("answer")
    sources = result.get("sources")
    if not isinstance(answer, str) or not isinstance(sources, list):
        raise ValueError("Artifact result must contain answer text and source records")
    if not all(isinstance(s, dict) for s in sources):
        raise ValueError("Sources must be objects")

    labels = [str(source.get("label", "")) for source in sources]
    ids = [str(source.get("doc_id", "")) for source in sources]
    abstained = result.get("abstained", False) is True
    output_status = result.get("output_status")
    raw_generation = result.get("raw_generation")

    if output_status == "rejected_citation_contract":
        if not abstained or not isinstance(raw_generation, str):
            raise ValueError("Rejected answer must retain the raw draft and abstain")
        report = validate_citations(raw_generation, labels)
        if report.citation_contract_passed:
            raise ValueError("Draft does not fail the recorded citation contract")
        # A rejected generation is an actual citation failure, not a successful
        # abstention. This prevents sanitizing an output into a passing score.
        citation_status = "failed"
    elif abstained:
        report = validate_citations(answer, labels)
        citation_status = "not_applicable_abstained"
    else:
        report = validate_citations(answer, labels)
        citation_status = "passed" if report.citation_contract_passed else "failed"

    timings = result.get("timings_ms") or {}
    if not isinstance(timings, dict):
        raise ValueError("timings_ms must be an object")

    output = {
        "query_id": artifact.get("query_id"),
        "question": result.get("question"),
        "retrieval_name": result.get("retrieval_name"),
        "generator_name": result.get("generator_name"),
        "source_count": len(sources),
        "source_document_ids": ids,
        "source_titles": [str(s.get("title", "")) for s in sources],
        "abstained": abstained,
        "output_status": output_status or ("abstained_legacy" if abstained else "unknown_legacy"),
        "raw_generation_preserved": isinstance(raw_generation, str),
        "citation_status": citation_status,
        "citation_count": report.citation_count,
        "invalid_citation_labels": list(report.invalid_labels),
        "citation_sentence_coverage": report.sentence_coverage,
        "semantic_support": "not_evaluated",
        "answer_correctness": "not_evaluated",
        "generation_ms": timings.get("generation"),
        "retrieval_ms": timings.get("retrieval"),
        "total_ms": timings.get("total"),
        "qrel_retrieval": "not_evaluated",
    }
    if relevant_doc_ids is not None:
        relevant = set(str(x) for x in relevant_doc_ids)
        retrieved_relevant = [doc_id for doc_id in ids if doc_id in relevant]
        output["qrel_retrieval"] = {
            "relevant_document_count": len(relevant),
            "relevant_sources_in_context": retrieved_relevant,
            "relevant_source_count": len(retrieved_relevant),
            "recall_at_context_k": len(set(retrieved_relevant)) / len(relevant)
            if relevant else None,
            "note": "Gold qrels are used for offline diagnosis only, never retrieval gating.",
        }
    return output

"""M2-GUARD-DEV-01: narrowly scoped, fail-closed manufacturer-evidence gate.

This intentionally understands ONLY one fictional equipment-question grammar.
It is NOT an NLI system, general-purpose evidence support verifier, or an
authorization for automatic publication. It never reads expected gold labels.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from raglab.citations.validator_v2 import validate_citations_v2

QUESTION = re.compile(
    r"Which company developed the (?P<item>[A-Za-z][A-Za-z0-9 -]*?) "
    r"installed on the (?P<vehicle>[A-Za-z][A-Za-z0-9 -]*?)\?\Z"
)
EVIDENCE = re.compile(
    r"The (?P<item>[A-Za-z][A-Za-z0-9 -]*?) "
    r"installed on the (?P<vehicle>[A-Za-z][A-Za-z0-9 -]*?) "
    r"was developed by (?P<company>[A-Za-z][A-Za-z0-9 -]*?)\.\Z"
)
# Only an exact single English sentence with a trailing S-label qualifies.
CANDIDATE = re.compile(
    r"(?P<company>[A-Za-z][A-Za-z0-9 -]*?) developed "
    r"(?:the )?(?P<item>[A-Za-z][A-Za-z0-9 -]*?) "
    r"(?:installed on|for) (?:the )?"
    r"(?P<vehicle>[A-Za-z][A-Za-z0-9 -]*?)"
    r"(?:\.\s*\[(?P<after>S[1-9]\d*)\]|\s*\[(?P<before>S[1-9]\d*)\]\.)\Z"
)


def normalize(value: str) -> str:
    return " ".join(value.casefold().split())


@dataclass(frozen=True)
class EvidenceDecision:
    allow_generation: bool
    reason: str
    company: str | None
    supporting_labels: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "allow_generation": self.allow_generation,
            "reason": self.reason,
            "company": self.company,
            "supporting_labels": list(self.supporting_labels),
        }


def assess_evidence(question: str, sources: list[dict[str, str]]) -> EvidenceDecision:
    """Allow only exact matching subject+relation and one consistent answer.

    All source texts must follow the explicitly supported grammar, and must
    all describe the requested item *on the requested vehicle*. A mismatch,
    extra fact, uncertainty, unknown grammar or conflict is a denial.
    Source IDs must be unique; no gold labels, case categories or file names
    are inspected, and no generated answer is seen by this stage.
    """
    match = QUESTION.fullmatch(question.strip())
    if not match:
        return EvidenceDecision(False, "DENY_UNSUPPORTED_QUESTION_GRAMMAR", None, ())
    if not sources:
        return EvidenceDecision(False, "DENY_NO_CONTEXT", None, ())
    if len({source.get("id") for source in sources}) != len(sources):
        return EvidenceDecision(False, "DENY_DUPLICATE_SOURCE_ID", None, ())
    values: list[str] = []
    for source in sources:
        if (not isinstance(source, dict)
            or not isinstance(source.get("text"), str)
            or not isinstance(source.get("id"), str)
            or not source["id"]):
            return EvidenceDecision(False, "DENY_UNTRUSTED_SOURCE_FORMAT", None, ())
        fact = EVIDENCE.fullmatch(source["text"].strip())
        if not fact:
            return EvidenceDecision(False, "DENY_UNPARSEABLE_SOURCE", None, ())
        if (normalize(fact["item"]) != normalize(match["item"])
            or normalize(fact["vehicle"]) != normalize(match["vehicle"])):
            return EvidenceDecision(False, "DENY_SOURCE_OFF_TARGET", None, ())
        values.append(fact["company"])
    if len({normalize(value) for value in values}) != 1:
        return EvidenceDecision(False, "DENY_SOURCE_CONTRADICTION", None, ())
    return EvidenceDecision(
        True, "ALLOW_EXACT_CONSISTENT_STRUCTURED_EVIDENCE", values[0],
        tuple(f"S{i}" for i in range(1, len(sources) + 1)),
    )


def assess_candidate(
    question: str, sources: list[dict[str, str]], candidate: str | None
) -> dict[str, Any]:
    """Strict *development-only* matching, never semantic truth certification."""
    evidence = assess_evidence(question, sources)
    if not evidence.allow_generation:
        return {
            "safe_to_publish": False,
            "development_match": False,
            "reason": "DENIED_PREGEN:" + evidence.reason,
            "evidence": evidence.as_dict(),
            "human_semantic_verification": "NOT_PERFORMED",
        }
    if not isinstance(candidate, str) or not candidate.strip():
        reason = "DENY_MISSING_MODEL_CANDIDATE"
        match = None
    else:
        match = CANDIDATE.fullmatch(candidate.strip())
        reason = "DENY_UNSUPPORTED_ANSWER_GRAMMAR" if match is None else ""
    if match:
        claim_company = match["company"]
        claim_item = match["item"]
        claim_vehicle = match["vehicle"]
        question_match = QUESTION.fullmatch(question.strip())
        assert question_match is not None
        cite = match["after"] or match["before"]
        labels = evidence.supporting_labels
        if (
            normalize(claim_company) != normalize(evidence.company or "")
            or normalize(claim_item) != normalize(question_match["item"])
            or normalize(claim_vehicle) != normalize(question_match["vehicle"])
        ):
            reason = "DENY_RELATION_OR_VALUE_MISMATCH"
        elif cite not in labels:
            reason = "DENY_UNSUPPORTED_CITATION_LABEL"
        elif not validate_citations_v2(candidate, labels).citation_contract_passed:
            reason = "DENY_INVALID_CITATION_SYNTAX"
        else:
            reason = "MATCHES_NARROW_STRUCTURED_SOURCE_ONLY"
    matched = reason == "MATCHES_NARROW_STRUCTURED_SOURCE_ONLY"
    return {
        # In research mode, do not promote a narrow template match to publish.
        "safe_to_publish": False,
        "development_match": matched,
        "reason": reason,
        "evidence": evidence.as_dict(),
        "human_semantic_verification": "NOT_PERFORMED",
    }


def make_research_evidence_gate(document_map: dict[str, Any]):
    """Optional existing pipeline callback for a *research-only* copy."""
    def _gate(question: str, results: Any) -> bool:
        sources = []
        for result in results:
            doc_id = getattr(result, "doc_id", None)
            doc = document_map.get(doc_id)
            if doc is None or not isinstance(getattr(doc, "text", None), str):
                return False
            sources.append({"id": doc_id, "text": doc.text})
        return assess_evidence(question, sources).allow_generation
    return _gate

"""Typed output contracts and strict verbatim source-provenance checks.

A verbatim source substring certifies *where a claim came from*, not that it
answers the question or is semantically supported. No sources are fabricated.
"""
from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from typing import Literal

from raglab.core import Document

Decision = Literal["ANSWER", "CONFLICT", "INSUFFICIENT", "REVIEW"]


@dataclass(frozen=True, slots=True)
class EvidenceCitation:
    doc_id: str
    start: int
    end: int
    quote: str
    document_sha256: str

    @classmethod
    def from_document(cls, doc: Document, start: int, end: int) -> "EvidenceCitation":
        if start < 0 or end <= start or end > len(doc.text):
            raise ValueError("Citation offsets do not point to an original source")
        quote = doc.text[start:end]
        if not quote.strip():
            raise ValueError("Empty source citation is not permitted")
        return cls(
            doc.id, start, end, quote,
            hashlib.sha256(doc.text.encode("utf-8")).hexdigest(),
        )

    def validate(self, doc: Document) -> None:
        if self.doc_id != doc.id:
            raise ValueError("Citation references the wrong document")
        expected = self.from_document(doc, self.start, self.end)
        if expected != self:
            raise ValueError("Citation quote or document hash does not match original")


@dataclass(frozen=True, slots=True)
class EvidenceClaim:
    text: str
    citation: EvidenceCitation
    method: Literal["structured_literal", "extractive_unverified"]
    entity: str | None = None
    field: str | None = None
    margin: float | None = None


@dataclass(frozen=True, slots=True)
class EvidenceResult:
    question: str
    status: Decision
    answer: str | None
    claims: tuple[EvidenceClaim, ...]
    citations: tuple[EvidenceCitation, ...]
    retrieved_doc_ids: tuple[str, ...]
    inspected_doc_ids: tuple[str, ...]
    timings_ms: dict[str, float]
    warnings: tuple[str, ...]
    read_calls: int
    documents_total: int
    source_sweep_complete: bool
    verifier_traces: tuple[dict, ...] = ()

    def to_dict(self) -> dict:
        return asdict(self)

    def validate(self, documents: dict[str, Document]) -> None:
        if self.status not in ("ANSWER", "CONFLICT", "INSUFFICIENT", "REVIEW"):
            raise ValueError("Unknown decision status")
        if self.status == "ANSWER":
            if self.answer is None or not self.citations:
                raise ValueError("An accepted answer requires citations")
            if any(claim.method != "structured_literal" for claim in self.claims):
                raise ValueError("Unverified extractive model claims cannot be published")
            if not self.source_sweep_complete:
                raise ValueError("Incomplete evidence scan cannot publish a structured answer")
        elif self.answer is not None:
            raise ValueError("No answer may be published in conflict/refusal/review states")
        if set(self.inspected_doc_ids) - set(documents):
            raise ValueError("Inspected a nonexistent document")
        if self.read_calls < 0 or self.documents_total != len(documents):
            raise ValueError("Invalid workload accounting")
        if any(value < 0 for value in self.timings_ms.values()):
            raise ValueError("Negative timing is not permitted")
        for claim in self.claims:
            source = documents.get(claim.citation.doc_id)
            if source is None:
                raise ValueError("Claim references unknown document")
            claim.citation.validate(source)
            if claim.citation.quote != claim.text:
                raise ValueError("Claim text does not match its exact original span")
        for observation in self.verifier_traces:
            if not isinstance(observation, dict) or (
                observation.get("left_doc_id") not in documents
                or observation.get("right_doc_id") not in documents
            ):
                raise ValueError("Verifier trace references an unknown source")
        for citation in self.citations:
            doc = documents.get(citation.doc_id)
            if doc is None:
                raise ValueError("Missing citation source")
            citation.validate(doc)

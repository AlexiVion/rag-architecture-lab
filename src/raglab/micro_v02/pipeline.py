"""Tiny CPU-first RAG pipeline with source coverage and fail-closed statuses.

This working baseline answers only supported structured literal fields. The
optional extractive model can generate review candidates, never auto-published
claims. No semantic entailment, independent NLI, or human risk certification
is implied by this prototype.
"""
from __future__ import annotations

import time
from collections.abc import Sequence

from raglab.core import Document
from raglab.retrieval import BM25Retriever
from raglab.micro_v02.contracts import EvidenceClaim, EvidenceResult
from raglab.micro_v02.policy import adjudicate
from raglab.micro_v02.verifier import EvidenceVerifier
from raglab.micro_v02.readers import (
    EvidenceReader, StructuredFactReader, parse_question, source_entity,
    structured_source_invalid,
)


class MicroRAG:
    def __init__(
        self,
        documents: Sequence[Document],
        *,
        reader: EvidenceReader | None = None,
        verifier: EvidenceVerifier | None = None,
        top_k: int = 3,
        max_entity_sweep: int = 25,
    ) -> None:
        if top_k <= 0 or max_entity_sweep <= 0:
            raise ValueError("Reader budgets must be positive")
        self.documents = tuple(documents)
        if not self.documents or len(self.documents) > 1000:
            raise ValueError("Document collection must have between 1 and 1,000 entries")
        if any(
            not d.id.strip() or not d.text.strip() or len(d.text) > 50_000
            for d in self.documents
        ):
            raise ValueError("Every source needs a nonempty ID and bounded text")
        if len({d.id for d in self.documents}) != len(self.documents):
            raise ValueError("Duplicate document IDs are not allowed")
        self.sources = {d.id: d for d in self.documents}
        self.top_k = top_k
        self.max_entity_sweep = max_entity_sweep
        self.reader = reader or StructuredFactReader()
        self.verifier = verifier
        self.retriever = BM25Retriever()
        self.retriever.index(self.documents)

    def answer(self, question: str) -> EvidenceResult:
        question = question.strip()
        if not question or len(question) > 2000:
            raise ValueError("Question must be nonempty and shorter than 2,001 chars")
        started = time.perf_counter()
        spec = parse_question(question)

        retrieve_start = time.perf_counter()
        ranked = self.retriever.retrieve(
            question, min(self.top_k, len(self.documents))
        )
        # Purely unrelated documents must not become trusted context just
        # because BM25 returns top-k documents even when scores are zero.
        ranked_ids = tuple(
            hit.doc_id for hit in ranked if hit.score > 0.0
        )
        retrieval_ms = (time.perf_counter() - retrieve_start) * 1000

        scan_start = time.perf_counter()
        warnings: list[str] = []
        source_sweep_complete = True
        if isinstance(self.reader, StructuredFactReader):
            if spec is None:
                # Unsupported questions are not proof that a fact is absent.
                inspect_ids = ()
                source_sweep_complete = False
                warnings.append("Unsupported or ambiguous entity/property question")
            else:
                # An ambiguous/malformed source may refer to the target entity.
                # Never silently omit it because source_entity() returned None.
                related = {
                    d.id for d in self.documents if source_entity(d) == spec.entity
                }
                unattributed = {
                    d.id for d in self.documents
                    if source_entity(d) is None and structured_source_invalid(d)
                }
                if unattributed:
                    source_sweep_complete = False
                    warnings.append(
                        "Unattributed malformed sources prevent a complete entity scan"
                    )
                inspect_candidates = sorted(related | unattributed)
                if len(inspect_candidates) > self.max_entity_sweep:
                    source_sweep_complete = False
                    warnings.append("Related/unknown source group exceeds scan budget")
                inspect_ids = tuple(inspect_candidates[:self.max_entity_sweep])
                if not inspect_ids:
                    warnings.append("No documents contain a matching structured entity")
        else:
            # Top-k is never proof of global absence, including when the
            # neural reader extracted no span from the retrieved documents.
            inspect_ids = ranked_ids
            source_sweep_complete = False
            warnings.append(
                "Partial retrieval cannot establish corpus-wide absence; human review required"
            )
            warnings.append("Extractive reader has no independent semantic verification")
        scan_ms = (time.perf_counter() - scan_start) * 1000

        read_start = time.perf_counter()
        claims: list[EvidenceClaim] = []
        reader_error = False
        calls = 0
        for doc_id in inspect_ids:
            calls += 1
            doc = self.sources[doc_id]
            try:
                if isinstance(self.reader, StructuredFactReader) and structured_source_invalid(doc):
                    raise ValueError("Malformed structured source; cannot prove consistency")
                claim = self.reader.extract(question, doc, spec)
                if claim is not None:
                    if claim.citation.doc_id != doc_id:
                        raise ValueError("Reader claim points to another document")
                    claim.citation.validate(doc)
                    if claim.text != claim.citation.quote:
                        raise ValueError("Reader modified the original source quote")
                    claims.append(claim)
            except Exception as exc:
                reader_error = True
                warnings.append(
                    f"Reader failed closed for source {doc_id}: {type(exc).__name__}"
                )
        reader_ms = (time.perf_counter() - read_start) * 1000

        verify_start = time.perf_counter()
        observations: tuple[dict, ...] = ()
        if (self.verifier is not None and len(claims) >= 2
                and not reader_error
                and any(claim.method == "extractive_unverified" for claim in claims)):
            try:
                # NLI is an *unverified diagnostic*, not an independent
                # factual gate; the policy still REQUIRES REVIEW.
                checked = self.verifier.inspect(question, tuple(claims))
                observations = tuple(x.to_dict() for x in checked)
                if any(x.get("predicted_relation") == "contradiction"
                       for x in observations):
                    warnings.append(
                        "Provisional NLI conflict detected; requires independent review"
                    )
            except Exception as exc:
                reader_error = True
                warnings.append(
                    f"NLI verifier failed closed: {type(exc).__name__}"
                )
        verifier_ms = (time.perf_counter() - verify_start) * 1000

        decide_start = time.perf_counter()
        policy = adjudicate(
            tuple(claims),
            source_sweep_complete=source_sweep_complete and not reader_error,
        )
        decision_ms = (time.perf_counter() - decide_start) * 1000
        timings = {
            "retrieval": retrieval_ms,
            "source_scan": scan_ms,
            "reader": reader_ms,
            "verifier": verifier_ms,
            "decision": decision_ms,
            "total": (time.perf_counter() - started) * 1000,
        }
        outcome = EvidenceResult(
            question=question,
            status=policy.status,
            answer=policy.answer,
            claims=tuple(claims),
            citations=policy.citations,
            retrieved_doc_ids=ranked_ids,
            inspected_doc_ids=inspect_ids,
            timings_ms=timings,
            warnings=tuple(warnings) + policy.warnings,
            read_calls=calls,
            documents_total=len(self.documents),
            source_sweep_complete=source_sweep_complete and not reader_error,
            verifier_traces=observations,
        )
        outcome.validate(self.sources)
        return outcome

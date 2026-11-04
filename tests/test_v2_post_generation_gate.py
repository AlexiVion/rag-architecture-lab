from __future__ import annotations

from raglab.context import ContextBuilder
from raglab.core import Document, SearchResult
from raglab.evaluation.answer_audit import audit_answer_artifact
from raglab.rag import RAGPipeline


class Retriever:
    name = "toy"

    def index(self, documents):
        self.documents = documents

    def retrieve(self, query, k):
        return [SearchResult(doc_id="a", score=1.0, rank=1)][:k]


class EmptyRetriever(Retriever):
    def retrieve(self, query, k):
        return []


class Generator:
    name = "fake"

    def __init__(self, text):
        self.text = text
        self.calls = 0

    def generate(self, *, system_prompt, user_prompt, max_new_tokens=220):
        self.calls += 1
        return self.text


def pipeline(text, *, retriever=None, evidence_gate=None):
    generator = Generator(text)
    instance = RAGPipeline(
        documents=[Document(id="a", title="Support article", text="The study reports a result.")],
        retriever=retriever or Retriever(),
        context_builder=ContextBuilder(),
        generator=generator,
        evidence_gate=evidence_gate,
        top_k=1,
    )
    instance.index()
    return instance, generator


def audit(result):
    return audit_answer_artifact({"query_id": "q", "result": result.to_dict()})


def test_uncited_generation_is_rejected_but_preserved_for_local_audit():
    p, gen = pipeline("A confident but uncited claim.")
    result = p.answer("Which claim?")
    assert gen.calls == 1
    assert result.abstained
    assert result.output_status == "rejected_citation_contract"
    assert "no factual answer" in result.answer
    assert result.raw_generation == "A confident but uncited claim."
    assert result.citation_report.citation_count == 0
    report = audit(result)
    assert report["citation_status"] == "failed"
    assert report["raw_generation_preserved"] is True
    assert report["semantic_support"] == "not_evaluated"


def test_unknown_source_label_is_rejected():
    p, _ = pipeline("A claim [S99].")
    result = p.answer("Question")
    assert result.abstained
    assert result.citation_report.invalid_labels == ("S99",)
    assert audit(result)["invalid_citation_labels"] == ["S99"]


def test_incomplete_sentence_coverage_is_rejected():
    p, _ = pipeline("First claim [S1]. Second claim without citation.")
    result = p.answer("Question")
    assert result.abstained
    assert audit(result)["citation_sentence_coverage"] == 0.5


def test_valid_citation_is_accepted_but_semantics_remain_unverified():
    p, _ = pipeline("The answer appears supported [S1].")
    result = p.answer("Question")
    assert result.output_status == "accepted"
    assert not result.abstained
    assert result.raw_generation is None
    assert result.answer == "The answer appears supported [S1]."
    assert audit(result)["citation_status"] == "passed"
    assert audit(result)["semantic_support"] == "not_evaluated"


def test_no_context_skips_generation_and_is_not_misreported_as_failure():
    p, gen = pipeline("Must not appear", retriever=EmptyRetriever())
    result = p.answer("Question")
    assert result.abstained
    assert result.output_status == "abstained_no_context"
    assert result.raw_generation is None
    assert gen.calls == 0
    assert audit(result)["citation_status"] == "not_applicable_abstained"


def test_evidence_gate_skips_generation_with_distinct_status():
    p, gen = pipeline("Must not appear", evidence_gate=lambda q, results: False)
    result = p.answer("Question")
    assert result.abstained
    assert result.output_status == "abstained_evidence_gate"
    assert gen.calls == 0
    assert audit(result)["citation_status"] == "not_applicable_abstained"

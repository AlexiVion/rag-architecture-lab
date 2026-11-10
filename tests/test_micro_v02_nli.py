"""NLI traces are only advisory; automatic answer publication remains blocked."""
from __future__ import annotations

from raglab.core import Document
from raglab.micro_v02.contracts import EvidenceClaim, EvidenceCitation
from raglab.micro_v02.pipeline import MicroRAG
from raglab.micro_v02.verifier import VerifierObservation

A=Document("a","entity: Station Aurora\nstart_year: 2012\n")
B=Document("b","entity: Station Aurora\nstart_year: 2015\n")


class FakeExtractive:
    name="fake_qa"
    def extract(self,question,document,spec):
        start=document.text.index("start_year: ")+len("start_year: ")
        return EvidenceClaim(
            document.text[start:start+4],
            EvidenceCitation.from_document(document,start,start+4),
            method="extractive_unverified",
            entity="station aurora",field="start_year",
        )


class FakeNLI:
    name="fixture_nli"
    def inspect(self,question,claims):
        assert len(claims)==2
        return (VerifierObservation(
            claims[0].citation.doc_id,claims[1].citation.doc_id,
            "contradiction",0.97,self.name,
        ),)


class FailingNLI:
    name="fails"
    def inspect(self,question,claims):
        raise RuntimeError("bad checkpoint")


def test_predicted_conflict_is_visible_but_unverified_qa_is_not_published():
    rag=MicroRAG([A,B],reader=FakeExtractive(),verifier=FakeNLI())
    result=rag.answer("What is the start year for Station Aurora?")
    assert result.status=="REVIEW"
    assert result.answer is None
    assert len(result.verifier_traces)==1
    observation=result.verifier_traces[0]
    assert observation["predicted_relation"]=="contradiction"
    assert observation["inference_scope"]=="provisional_pairwise_nli_not_semantic_support"
    assert len(result.claims)==2
    assert any("Provisional NLI conflict" in msg for msg in result.warnings)
    assert result.timings_ms["verifier"]>=0
    result.validate(rag.sources)


def test_unavailable_nli_fails_closed():
    rag=MicroRAG([A,B],reader=FakeExtractive(),verifier=FailingNLI())
    result=rag.answer("What is the start year for Station Aurora?")
    assert result.status=="REVIEW"
    assert result.answer is None
    assert not result.verifier_traces
    assert any("verifier failed closed" in msg for msg in result.warnings)


def test_no_optional_nli_has_no_fabricated_diagnostic_result():
    rag=MicroRAG([A,B],reader=FakeExtractive())
    result=rag.answer("What is the start year for Station Aurora?")
    assert result.status=="REVIEW"
    assert not result.verifier_traces


def test_structured_conflict_cannot_be_overruled_by_untrusted_nli():
    rag=MicroRAG([A,B],verifier=FakeNLI())
    result=rag.answer("What is the start year for Station Aurora?")
    assert result.status=="CONFLICT"
    assert result.answer is None
    assert not result.verifier_traces

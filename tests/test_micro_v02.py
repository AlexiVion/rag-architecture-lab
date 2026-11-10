"""Micro-RAG v0.2 software/fixture tests, not external scientific validation."""
from __future__ import annotations
from dataclasses import replace

import pytest

from raglab.core import Document
from raglab.micro_v02.contracts import EvidenceCitation, EvidenceClaim
from raglab.micro_v02.evaluation import evaluate_cases
from raglab.micro_v02.pipeline import MicroRAG
from raglab.micro_v02.readers import parse_question, source_entity

A = Document("a", "entity: Station Aurora\nstart_year: 2012\nmanager: Camille\n")
B = Document("b", "entity: Station Aurora\nstart_year: 2015\nmanager: Camille\n")
C = Document("c", "entity: Station Boreal\nstart_year: 2019\nmanager: Dana\n")
D = Document("d", "entity: Station Boreal\nstart_year: 2019\nmanager: Dana\n")

def test_accept_verified_literal_source():
    result = MicroRAG([C]).answer("What is the start year for Station Boreal?")
    assert result.status == "ANSWER"
    assert result.answer == "2019"
    assert len(result.citations) == 1
    cite = result.citations[0]
    assert C.text[cite.start:cite.end] == result.answer
    cite.validate(C)
    assert len(cite.document_sha256) == 64
    assert result.to_dict()["status"] == "ANSWER"

def test_bm25_top_one_cannot_hide_structured_conflict():
    result = MicroRAG([A, B, C], top_k=1).answer("What is the start year for Station Aurora?")
    assert result.status == "CONFLICT"
    assert result.answer is None
    assert {c.doc_id for c in result.citations} == {"a", "b"}
    assert set(result.inspected_doc_ids) == {"a", "b"}
    assert result.read_calls == 2

def test_agreeing_sources_support_one_answer():
    result = MicroRAG([A, B]).answer("Who is the manager of Station Aurora?")
    assert result.status == "ANSWER"
    assert result.answer == "Camille"
    assert len(result.citations) == 2

def test_missing_property_unknown_entity_or_unknown_field_refuses():
    rag = MicroRAG([A, C])
    for q in (
        "What is the storage seal for Station Aurora?",
        "What is the capacity of Station Horizon?",
        "What is the budget of Station Boreal?",
    ):
        result = rag.answer(q)
        assert result.status == "INSUFFICIENT"
        assert result.answer is None
        assert not result.citations

def test_sources_from_different_entities_never_mix():
    result = MicroRAG([A, B, C]).answer("What is the manager of Station Boreal?")
    assert result.status == "ANSWER"
    assert result.answer == "Dana"
    assert {c.doc_id for c in result.citations} == {"c"}

def test_scan_budget_fails_closed():
    result = MicroRAG([A, B], max_entity_sweep=1).answer(
        "What is the start year for Station Aurora?"
    )
    assert result.status == "REVIEW"
    assert result.answer is None
    assert not result.source_sweep_complete

def test_duplicate_keys_in_source_refuse():
    corrupt = Document("x", "entity: Station Aurora\nstart_year: 2012\nstart_year: 2015\n")
    result = MicroRAG([corrupt]).answer("What is the start year for Station Aurora?")
    assert result.status == "REVIEW"
    assert source_entity(corrupt) == "station aurora"

def test_questions_require_single_named_entity_and_field():
    rag = MicroRAG([A, C])
    for q in (
        "What is the start year?",
        "What is the manager and capacity of Station Aurora?",
        "What is the start year of Station Aurora and Station Boreal?",
    ):
        assert rag.answer(q).status != "ANSWER"
    assert parse_question("When was it founded?") is None

def test_citation_mismatch_and_out_of_bounds_rejected():
    offset = A.text.index("2012")
    cite = EvidenceCitation.from_document(A, offset, offset + 4)
    with pytest.raises(ValueError, match="original source"):
        EvidenceCitation.from_document(A, 5, 9999)
    with pytest.raises(ValueError, match="wrong document"):
        cite.validate(B)
    with pytest.raises(ValueError, match="hash"):
        replace(cite, quote="2019").validate(A)

class UnverifiedReader:
    name = "unverified_qa"
    def extract(self, question, document, spec):
        offset = document.text.index("2012")
        return EvidenceClaim(
            "2012",
            EvidenceCitation.from_document(document, offset, offset + 4),
            method="extractive_unverified",
        )

class CorruptReader:
    name = "corrupt"
    def extract(self, question, document, spec):
        return EvidenceClaim(
            "invented",
            EvidenceCitation.from_document(document, 0, 6),
            method="structured_literal", entity="station aurora", field="start_year",
        )

def test_extractive_never_implicitly_claims_entailment():
    result = MicroRAG([A], reader=UnverifiedReader()).answer(
        "What is the start year for Station Aurora?"
    )
    assert result.status == "REVIEW"
    assert result.answer is None
    assert result.claims[0].method == "extractive_unverified"

def test_bad_reader_fails_closed_and_does_not_publish():
    result = MicroRAG([A], reader=CorruptReader()).answer(
        "What is the start year for Station Aurora?"
    )
    assert result.status == "REVIEW"
    assert result.answer is None
    assert any("failed closed" in x for x in result.warnings)

def test_constructor_and_question_bounds():
    with pytest.raises(ValueError, match="Duplicate"):
        MicroRAG([A, A])
    with pytest.raises(ValueError, match="bounded"):
        MicroRAG([Document("e", "")])
    with pytest.raises(ValueError, match="budgets"):
        MicroRAG([A], top_k=0)
    with pytest.raises(ValueError, match="Question"):
        MicroRAG([A]).answer(" ")

def test_evaluator_marks_wrong_accepted_value_as_risk():
    score = evaluate_cases(MicroRAG([A]), [
        {"id":"c1","question":"What is the manager of Station Aurora?",
         "expected_status":"ANSWER","expected_answer":"Camille","group_id":"aurora"},
        {"id":"c2","question":"What is the start year for Station Aurora?",
         "expected_status":"CONFLICT","group_id":"aurora"},
    ])
    assert score["accepted"] == 2
    assert score["wrong_accepts"] == 1
    assert score["wrong_accept_rate"] == 0.5
    assert score["groups"] == 1
    assert "NOT_INDEPENDENT" in score["status"]

def test_evaluator_cannot_call_conflict_refusal_an_answer():
    score = evaluate_cases(MicroRAG([A, B]), [
        {"id":"conflict","question":"What is the start year for Station Aurora?",
         "expected_status":"CONFLICT"},
        {"id":"answer","question":"What is the manager of Station Aurora?",
         "expected_status":"ANSWER","expected_answer":"Camille"},
    ])
    assert score["strict_correct"] == 2
    assert score["wrong_accepts"] == 0
    assert score["correct_conflicts"] == 1

def test_evaluator_case_ids_must_be_unique():
    row={"id":"x","question":"What is the manager of Station Aurora?",
         "expected_status":"ANSWER","expected_answer":"Camille"}
    with pytest.raises(ValueError, match="unique"):
        evaluate_cases(MicroRAG([A]), [row, row])

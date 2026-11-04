from raglab.context import ContextBuilder
from raglab.core import Document, SearchResult


def test_global_budget_and_actual_source_evidence_match() -> None:
    docs = {
        "a": Document(id="a", title="First", text="a" * 400),
        "b": Document(id="b", title="Second", text="b" * 400),
    }
    results = [
        SearchResult(doc_id="a", score=1.0, rank=1),
        SearchResult(doc_id="b", score=0.8, rank=2),
    ]
    context = ContextBuilder(max_chars=120, per_source_chars=100).build(docs, results)
    assert len(context.text) <= 120
    assert context.sources
    for source in context.sources:
        assert f"text: {source.text}" in context.text
        assert source.citation in context.text


def test_missing_document_does_not_create_label_gap() -> None:
    docs = {"b": Document(id="b", text="evidence")}
    results = [
        SearchResult("gone", 1.0, 1),
        SearchResult("b", 0.9, 2),
    ]
    context = ContextBuilder().build(docs, results)
    assert context.labels == ("S1",)


def test_empty_document_is_not_exposed_as_citable_source() -> None:
    docs = {"empty": Document(id="empty", text=" ")}
    context = ContextBuilder().build(docs, [SearchResult("empty", 1.0, 1)])
    assert not context.sources
    assert context.text == ""

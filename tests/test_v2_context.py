from raglab.context import ContextBuilder
from raglab.core import Document, SearchResult


def test_context_builder_assigns_stable_source_labels() -> None:
    documents = {
        "d1": Document(id="d1", title="First", text="Alpha evidence."),
        "d2": Document(id="d2", title="Second", text="Beta evidence."),
    }
    results = [
        SearchResult(doc_id="d2", score=0.9, rank=1),
        SearchResult(doc_id="d1", score=0.8, rank=2),
    ]

    context = ContextBuilder(max_chars=2_000, per_source_chars=500).build(documents, results)

    assert context.labels == ("S1", "S2")
    assert context.sources[0].doc_id == "d2"
    assert "[S1]" in context.text
    assert "Beta evidence." in context.text


def test_context_builder_respects_per_source_limit() -> None:
    documents = {"d1": Document(id="d1", text="x" * 500)}
    results = [SearchResult(doc_id="d1", score=1.0, rank=1)]

    context = ContextBuilder(max_chars=1_000, per_source_chars=40).build(documents, results)

    assert len(context.sources[0].text) <= 43
    assert context.sources[0].text.endswith("...")

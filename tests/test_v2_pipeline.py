from raglab.context import ContextBuilder
from raglab.core import Document, SearchResult
from raglab.rag import RAGPipeline


class FakeRetriever:
    name = "fake-retriever"

    def index(self, documents):
        self.documents = list(documents)

    def retrieve(self, query: str, k: int):
        return [SearchResult(doc_id="d1", score=1.0, rank=1)][:k]


class FakeGenerator:
    name = "fake-generator"

    def generate(self, *, system_prompt: str, user_prompt: str, max_new_tokens: int = 220):
        assert "[S1]" in user_prompt
        return "The evidence supports the claim [S1]."


def test_rag_pipeline_returns_sources_citations_and_timings() -> None:
    pipeline = RAGPipeline(
        documents=[Document(id="d1", title="Evidence", text="Relevant evidence.")],
        retriever=FakeRetriever(),
        context_builder=ContextBuilder(),
        generator=FakeGenerator(),
        top_k=1,
    )
    pipeline.index()

    result = pipeline.answer("What does the evidence say?")

    assert result.answer.endswith("[S1].")
    assert result.sources[0].doc_id == "d1"
    assert result.citation_report.all_citations_valid
    assert result.citation_report.sentence_coverage == 1.0
    assert result.timings_ms["total"] >= 0

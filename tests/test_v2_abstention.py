from raglab.context import ContextBuilder
from raglab.core import Document, SearchResult
from raglab.rag import RAGPipeline


class EmptyRetriever:
    name = "empty"

    def index(self, documents):
        pass

    def retrieve(self, query: str, k: int):
        return []


class OneRetriever(EmptyRetriever):
    name = "one"

    def retrieve(self, query: str, k: int):
        return [SearchResult("d", 0.001, 1)]


class FailIfCalledGenerator:
    name = "must-not-run"

    def generate(self, *, system_prompt: str, user_prompt: str, max_new_tokens: int = 220):
        raise AssertionError("Generator must not run with insufficient evidence")


def test_no_retrieved_context_abstains_without_generator_invocation() -> None:
    pipeline = RAGPipeline(
        documents=[Document("d", "content")],
        retriever=EmptyRetriever(),
        context_builder=ContextBuilder(),
        generator=FailIfCalledGenerator(),
    )
    pipeline.index()
    answer = pipeline.answer("question")
    assert answer.abstained
    assert answer.timings_ms["generation"] == 0
    assert not answer.citation_report.citation_contract_passed
    assert answer.to_dict()["abstained"] is True


def test_injected_evidence_gate_can_trigger_abstention() -> None:
    pipeline = RAGPipeline(
        documents=[Document("d", "content")],
        retriever=OneRetriever(),
        context_builder=ContextBuilder(),
        generator=FailIfCalledGenerator(),
        evidence_gate=lambda question, ranked: max(r.score for r in ranked) >= 0.1,
    )
    pipeline.index()
    answer = pipeline.answer("question")
    assert answer.abstained
    assert answer.sources[0].doc_id == "d"

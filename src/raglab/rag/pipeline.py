from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from collections.abc import Sequence

from raglab.citations import CitationReport, validate_citations
from raglab.context import ContextBuilder, ContextSource
from raglab.core import Document
from raglab.generation import Generator
from raglab.retrieval.base import Retriever


SYSTEM_PROMPT = """You are an evidence-grounded assistant.
Use only the evidence supplied in the context.
Every factual sentence should end with one or more citations such as [S1] or [S1][S2].
Never invent citation labels and never cite a source that is not in the context.
If the retrieved evidence is insufficient, say that the available evidence is insufficient.
Be concise and distinguish uncertainty from established evidence."""


@dataclass(frozen=True, slots=True)
class RAGAnswer:
    question: str
    answer: str
    retrieval_name: str
    generator_name: str
    sources: tuple[ContextSource, ...]
    citation_report: CitationReport
    timings_ms: dict[str, float]

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "answer": self.answer,
            "retrieval_name": self.retrieval_name,
            "generator_name": self.generator_name,
            "sources": [asdict(source) for source in self.sources],
            "citation_report": asdict(self.citation_report),
            "timings_ms": dict(self.timings_ms),
        }


class RAGPipeline:
    def __init__(
        self,
        *,
        documents: Sequence[Document],
        retriever: Retriever,
        context_builder: ContextBuilder,
        generator: Generator,
        top_k: int = 5,
        max_new_tokens: int = 220,
    ) -> None:
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        if max_new_tokens <= 0:
            raise ValueError("max_new_tokens must be positive")
        self.documents = list(documents)
        self.documents_by_id = {document.id: document for document in self.documents}
        self.retriever = retriever
        self.context_builder = context_builder
        self.generator = generator
        self.top_k = top_k
        self.max_new_tokens = max_new_tokens

    def index(self) -> None:
        self.retriever.index(self.documents)

    def answer(self, question: str) -> RAGAnswer:
        question = question.strip()
        if not question:
            raise ValueError("question must not be empty")

        started = time.perf_counter()
        retrieval_started = time.perf_counter()
        results = self.retriever.retrieve(question, self.top_k)
        retrieval_ms = (time.perf_counter() - retrieval_started) * 1000.0

        context_started = time.perf_counter()
        context = self.context_builder.build(self.documents_by_id, results)
        context_ms = (time.perf_counter() - context_started) * 1000.0

        if not context.sources:
            raise RuntimeError("Retriever returned no documents that could be mapped into context")

        user_prompt = (
            f"Question:\n{question}\n\n"
            f"Evidence:\n{context.text}\n\n"
            "Answer using only the evidence above. Cite source labels inline."
        )

        generation_started = time.perf_counter()
        answer = self.generator.generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_new_tokens=self.max_new_tokens,
        )
        generation_ms = (time.perf_counter() - generation_started) * 1000.0

        citation_report = validate_citations(answer, context.labels)
        total_ms = (time.perf_counter() - started) * 1000.0

        return RAGAnswer(
            question=question,
            answer=answer,
            retrieval_name=self.retriever.name,
            generator_name=self.generator.name,
            sources=context.sources,
            citation_report=citation_report,
            timings_ms={
                "retrieval": retrieval_ms,
                "context": context_ms,
                "generation": generation_ms,
                "total": total_ms,
            },
        )

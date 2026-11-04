from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from raglab.core import Document, SearchResult


@dataclass(frozen=True, slots=True)
class ContextSource:
    label: str
    doc_id: str
    title: str
    text: str
    score: float
    rank: int

    @property
    def citation(self) -> str:
        return f"[{self.label}]"


@dataclass(frozen=True, slots=True)
class ContextBundle:
    sources: tuple[ContextSource, ...]
    text: str

    @property
    def labels(self) -> tuple[str, ...]:
        return tuple(source.label for source in self.sources)


class ContextBuilder:
    """Construct context with an exact total-character budget and source mapping."""

    def __init__(self, max_chars: int = 10_000, per_source_chars: int = 2_200) -> None:
        if max_chars <= 0:
            raise ValueError("max_chars must be positive")
        if per_source_chars <= 0:
            raise ValueError("per_source_chars must be positive")
        self.max_chars = max_chars
        self.per_source_chars = per_source_chars

    def build(
        self,
        documents: Mapping[str, Document],
        results: Sequence[SearchResult],
    ) -> ContextBundle:
        sources: list[ContextSource] = []
        sections: list[str] = []
        used_chars = 0

        for result in results:
            document = documents.get(result.doc_id)
            if document is None:
                continue

            label = f"S{len(sources) + 1}"
            title = document.title.strip() or "(untitled)"
            prefix = (
                f"[{label}]\n"
                f"doc_id: {document.id}\n"
                f"title: {title}\n"
                "text: "
            )
            separator_cost = 2 if sections else 0
            body_budget = min(
                self.per_source_chars,
                self.max_chars - used_chars - separator_cost - len(prefix),
            )
            if body_budget <= 0:
                break

            # Keep the recorded ContextSource.text exactly equal to the evidence
            # actually sent to the generator, even at the last budget boundary.
            body = document.text.strip()[:body_budget]
            if not body:
                continue

            section = prefix + body
            sources.append(
                ContextSource(
                    label=label,
                    doc_id=document.id,
                    title=document.title,
                    text=body,
                    score=float(result.score),
                    rank=int(result.rank),
                )
            )
            sections.append(section)
            used_chars += separator_cost + len(section)
            if used_chars >= self.max_chars:
                break

        return ContextBundle(sources=tuple(sources), text="\n\n".join(sections))

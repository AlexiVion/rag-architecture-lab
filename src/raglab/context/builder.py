from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping, Sequence

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
    """Turn ranked retrieval results into a bounded, citation-addressable context."""

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

        for index, result in enumerate(results, start=1):
            document = documents.get(result.doc_id)
            if document is None:
                continue

            label = f"S{index}"
            body = document.text.strip()
            if len(body) > self.per_source_chars:
                body = body[: self.per_source_chars].rstrip() + "..."

            title = document.title.strip() or "(untitled)"
            section = (
                f"[{label}]\n"
                f"doc_id: {document.id}\n"
                f"title: {title}\n"
                f"text: {body}"
            )

            separator_cost = 2 if sections else 0
            remaining = self.max_chars - used_chars - separator_cost
            if remaining <= 0:
                break

            if len(section) > remaining:
                # Keep a final source only if enough room remains to preserve useful evidence.
                if remaining < 200:
                    break
                section = section[:remaining].rstrip() + "..."

            source = ContextSource(
                label=label,
                doc_id=document.id,
                title=document.title,
                text=body,
                score=float(result.score),
                rank=int(result.rank),
            )
            sources.append(source)
            sections.append(section)
            used_chars += separator_cost + len(section)

            if used_chars >= self.max_chars:
                break

        return ContextBundle(sources=tuple(sources), text="\n\n".join(sections))

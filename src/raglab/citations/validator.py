from __future__ import annotations

import re
from dataclasses import dataclass
from collections.abc import Iterable

_CITATION_RE = re.compile(r"\[(S\d+)\]")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")


@dataclass(frozen=True, slots=True)
class CitationReport:
    cited_labels: tuple[str, ...]
    invalid_labels: tuple[str, ...]
    citation_count: int
    valid_citation_count: int
    sentence_count: int
    cited_sentence_count: int
    sentence_coverage: float

    @property
    def all_citations_valid(self) -> bool:
        return not self.invalid_labels


def validate_citations(answer: str, available_labels: Iterable[str]) -> CitationReport:
    available = set(available_labels)
    matches = _CITATION_RE.findall(answer)

    cited_labels = tuple(dict.fromkeys(matches))
    invalid_labels = tuple(label for label in cited_labels if label not in available)
    valid_count = sum(1 for label in matches if label in available)

    sentences = [
        sentence.strip()
        for sentence in _SENTENCE_SPLIT_RE.split(answer)
        if sentence.strip() and any(char.isalpha() for char in sentence)
    ]
    cited_sentence_count = sum(
        1
        for sentence in sentences
        if any(label in available for label in _CITATION_RE.findall(sentence))
    )
    coverage = cited_sentence_count / len(sentences) if sentences else 0.0

    return CitationReport(
        cited_labels=cited_labels,
        invalid_labels=invalid_labels,
        citation_count=len(matches),
        valid_citation_count=valid_count,
        sentence_count=len(sentences),
        cited_sentence_count=cited_sentence_count,
        sentence_coverage=coverage,
    )

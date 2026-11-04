"""Strict, opt-in citation parser v2 for post-punctuation source labels.

Not used by the existing production RAGPipeline. It does not generate,
change or attach citations. Its output measures ONLY syntax, never entailment.
"""
from __future__ import annotations

import re
from collections.abc import Iterable

from raglab.citations.validator import CitationReport

_BRACKET = re.compile(r"\[([^\[\]\r\n]{1,80})\]")
_SOURCE = re.compile(r"S[1-9]\d*\Z")
_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
_LEADING = re.compile(r"^((?:\[[^\[\]\r\n]{1,80}\][ \t]*)+)(.*)\Z", re.DOTALL)
_PREVIOUS_TERMINAL = re.compile(r"[.!?](?:[ \t]*\[[^\[\]\r\n]{1,80}\])*[ \t]*\Z")
_TRAILING_CITATIONS = re.compile(
    r"(?:\[[^\[\]\r\n]{1,80}\][ \t]*)+[.!?]?[ \t]*\Z"
)


def _sentence_parts(answer: str) -> list[str]:
    """Attach citations following punctuation to the PRECEDING sentence.

    A leading citation on a subsequent *new factual sentence* is not allowed
    to silently cover that sentence. If a citation-only token follows a
    complete sentence, move only that token; keep all later text separate.
    """
    parts: list[str] = []
    for raw in _SPLIT.split(answer):
        chunk = raw.strip()
        if not chunk:
            continue
        match = _LEADING.match(chunk)
        if match and parts and _PREVIOUS_TERMINAL.search(parts[-1]):
            labels, rest = match.groups()
            parts[-1] += " " + labels.strip()
            if rest.strip():
                parts.append(rest.strip())
        else:
            parts.append(chunk)
    return parts


def validate_citations_v2(answer: str, available_labels: Iterable[str]) -> CitationReport:
    """Fail closed for unsupported labels and uncovered factual sentences.

    Accept both 'Claim [S1].' and 'Claim. [S1]' as a citation attached to
    that same claim. Do not accept citations stranded before another claim,
    arbitrary labels such as '[Solis Probe]', or standalone '[S1]'.
    """
    available = set(available_labels)
    labels_in_text = _BRACKET.findall(answer)
    unique = tuple(dict.fromkeys(labels_in_text))
    invalid = tuple(label for label in unique if not _SOURCE.fullmatch(label) or label not in available)
    valid_count = sum(label in available and _SOURCE.fullmatch(label) is not None for label in labels_in_text)

    facts: list[str] = []
    for part in _sentence_parts(answer):
        # A source marker alone is not a factual sentence.
        plain = _BRACKET.sub("", part).strip()
        if any(char.isalpha() for char in plain):
            facts.append(part)
    cited_facts = 0
    for fact in facts:
        matched = _TRAILING_CITATIONS.search(fact)
        if matched and any(
            _SOURCE.fullmatch(label) and label in available
            for label in _BRACKET.findall(matched.group(0))
        ):
            cited_facts += 1
    coverage = cited_facts / len(facts) if facts else 0.0
    return CitationReport(
        cited_labels=unique,
        invalid_labels=invalid,
        citation_count=len(labels_in_text),
        valid_citation_count=valid_count,
        sentence_count=len(facts),
        cited_sentence_count=cited_facts,
        sentence_coverage=coverage,
    )

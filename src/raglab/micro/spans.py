"""Query-aware, strictly budgeted *verbatim* evidence selection.

This component is a research candidate. Lexical overlap is a ranking feature,
NOT a semantic entailment verifier or an answerability certification.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass

from raglab.core import Document, SearchResult

_WORD = re.compile(r"(?u)\b\w+\b")
_TOKEN = re.compile(r"(?u)\w+|[^\w\s]")
_SENTENCE = re.compile(r"[^.!?\n]+(?:[.!?]+|(?=\n|$))")
_STOP = frozenset(
    "a an and are as at be by did do does for from how in is it its of on "
    "or the their there these this to was were what when where which who why with".split()
)


def proxy_tokens(text: str) -> int:
    """Count lexical tokens; deliberately NOT a model tokenizer."""
    return len(_TOKEN.findall(text))


def query_terms(text: str) -> frozenset[str]:
    return frozenset(word for word in _WORD.findall(text.lower()) if word not in _STOP)


@dataclass(frozen=True, slots=True)
class EvidenceSpan:
    label: str
    doc_id: str
    start: int
    end: int
    quote: str
    retrieval_rank: int
    retrieval_score: float
    overlap_terms: int

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class EvidencePack:
    spans: tuple[EvidenceSpan, ...]
    text: str
    budget_tokens: int
    used_tokens: int
    count_method: str = "lexical_proxy_not_model_tokenizer"

    def as_dict(self) -> dict:
        return {
            "spans": [span.as_dict() for span in self.spans],
            "text": self.text,
            "budget_tokens": self.budget_tokens,
            "used_tokens": self.used_tokens,
            "count_method": self.count_method,
        }


def _segments(text: str, chunk_tokens: int) -> list[tuple[int, int, str]]:
    """Never synthesize ellipses; all offsets index the original source."""
    if chunk_tokens <= 0:
        raise ValueError("chunk_tokens must be positive")
    pieces: list[tuple[int, int, str]] = []
    for match in _SENTENCE.finditer(text):
        raw = match.group()
        left = len(raw) - len(raw.lstrip())
        right = len(raw.rstrip())
        if right <= left:
            continue
        start = match.start() + left
        end = match.start() + right
        segment = text[start:end]
        tokens = list(_TOKEN.finditer(segment))
        if len(tokens) <= chunk_tokens:
            pieces.append((start, end, segment))
            continue
        # Long sentences are divided at exact source-token boundaries. This is
        # an explicit windowing ablation, not a claim of sentence integrity.
        for i in range(0, len(tokens), chunk_tokens):
            group = tokens[i : i + chunk_tokens]
            lo = start + group[0].start()
            hi = start + group[-1].end()
            pieces.append((lo, hi, text[lo:hi]))
    return pieces


def _render(span: EvidenceSpan) -> str:
    return f"[{span.label}] doc_id={span.doc_id} chars={span.start}:{span.end}\n{span.quote}"


def pack_evidence(
    question: str,
    documents: Mapping[str, Document],
    results: Sequence[SearchResult],
    *,
    max_tokens: int = 128,
    max_spans: int = 4,
    max_per_document: int = 2,
    count_tokens: Callable[[str], int] = proxy_tokens,
    count_method: str = "lexical_proxy_not_model_tokenizer",
) -> EvidencePack:
    """Select rank-aware overlapping snippets under an exact supplied counter.

    A model-specific token counter may be injected. The default lexical counter
    is a transparent proxy, and the token total excludes the external prompt.
    """
    if max_tokens <= 0 or max_spans <= 0 or max_per_document <= 0:
        raise ValueError("Budgets and limits must be positive")
    terms = query_terms(question)
    if not terms:
        return EvidencePack((), "", max_tokens, 0, count_method)
    candidates: list[tuple[float, int, int, str, int, int, int]] = []
    seen: set[tuple[str, int, int]] = set()
    for result in results:
        doc = documents.get(result.doc_id)
        if doc is None or not doc.text.strip():
            continue
        for start, end, quote in _segments(doc.text, max_tokens):
            overlap = len(terms.intersection(query_terms(quote)))
            if overlap == 0:
                continue
            key = (doc.id, start, end)
            if key in seen:
                continue
            seen.add(key)
            # Rank is comparable across different retriever types; the original
            # retrieval score is logged but deliberately not mixed across scales.
            value = overlap / len(terms) + 0.1 / (1 + max(result.rank, 0))
            candidates.append((value, result.rank, start, doc.id, end, overlap, len(candidates)))
    candidates.sort(key=lambda c: (-c[0], c[1], c[3], c[2], c[6]))
    selected: list[EvidenceSpan] = []
    per_doc: dict[str, int] = {}
    used_results = {result.doc_id: result for result in results}
    rendered = ""
    for _, _, start, doc_id, end, overlap, _ in candidates:
        if len(selected) >= max_spans:
            break
        if per_doc.get(doc_id, 0) >= max_per_document:
            continue
        doc = documents[doc_id]
        result = used_results[doc_id]
        span = EvidenceSpan(
            label=f"S{len(selected) + 1}",
            doc_id=doc_id,
            start=start,
            end=end,
            quote=doc.text[start:end],
            retrieval_rank=result.rank,
            retrieval_score=float(result.score),
            overlap_terms=overlap,
        )
        proposed = rendered + ("\n\n" if rendered else "") + _render(span)
        if count_tokens(proposed) > max_tokens:
            continue
        selected.append(span)
        per_doc[doc_id] = per_doc.get(doc_id, 0) + 1
        rendered = proposed
    return EvidencePack(tuple(selected), rendered, max_tokens, count_tokens(rendered), count_method)


def pack_naive(
    documents: Mapping[str, Document],
    results: Sequence[SearchResult],
    *,
    max_tokens: int = 128,
    max_spans: int = 4,
    count_tokens: Callable[[str], int] = proxy_tokens,
    count_method: str = "lexical_proxy_not_model_tokenizer",
) -> EvidencePack:
    """Contiguous top-ranked source prefixes using the SAME token counter.

    This deliberately does not use query-specific span selection. It is a
    matched-budget naive passage baseline, not a relevance-filtered oracle.
    """
    if max_tokens <= 0 or max_spans <= 0:
        raise ValueError("Budgets must be positive")
    selected: list[EvidenceSpan] = []
    rendered = ""
    seen: set[str] = set()
    for result in results:
        if len(selected) >= max_spans or result.doc_id in seen:
            continue
        seen.add(result.doc_id)
        doc = documents.get(result.doc_id)
        if doc is None or not doc.text.strip():
            continue
        tokens = list(_TOKEN.finditer(doc.text))
        if not tokens:
            continue
        # Fit the longest exact text prefix (no artificial truncated quotation).
        best: EvidenceSpan | None = None
        best_rendered = ""
        for i in range(1, min(len(tokens), max_tokens) + 1):
            start, end = tokens[0].start(), tokens[i - 1].end()
            span = EvidenceSpan(
                label=f"S{len(selected) + 1}",
                doc_id=doc.id,
                start=start,
                end=end,
                quote=doc.text[start:end],
                retrieval_rank=result.rank,
                retrieval_score=float(result.score),
                overlap_terms=0,
            )
            proposed = rendered + ("\n\n" if rendered else "") + _render(span)
            if count_tokens(proposed) > max_tokens:
                break
            best, best_rendered = span, proposed
        if best is not None:
            selected.append(best)
            rendered = best_rendered
    return EvidencePack(tuple(selected), rendered, max_tokens, count_tokens(rendered), count_method)

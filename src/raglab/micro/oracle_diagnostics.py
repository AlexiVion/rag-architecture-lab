"""Gold-answer-bearing *privileged* context windows for diagnostic experiments.

This deliberately reads answer annotations. It MUST NOT be used as a deployable
retrieval approach, answer quality achievement, or as evidence that the model
found an answer without an oracle. Its job is to diagnose failures downstream
of retrieval under the same context token cap.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from raglab.core import Document
from raglab.micro.spans import EvidencePack, EvidenceSpan, proxy_tokens, pack_naive
from raglab.core import SearchResult

# Reuse the same source-token definition as ordinary evidence selection.
_TOKEN = re.compile(r"(?u)\w+|[^\w\s]")


@dataclass(frozen=True, slots=True)
class OracleWindowResult:
    pack: EvidencePack
    status: str
    answer_visible: bool
    privileged_annotation_used: bool = True


def gold_answer_window(
    document: Document,
    gold_answers: tuple[str, ...],
    *,
    max_tokens: int,
    count_tokens: Callable[[str], int] = proxy_tokens,
    count_method: str = "lexical_proxy_not_model_tokenizer",
) -> OracleWindowResult:
    """Reveal a gold-bearing substring, preserving its exact original offsets.

    The choice is explicitly supervised by the gold answer. If a gold answer
    cannot fit even alone, report an exclusion rather than silently truncating.
    If no answer exists (SQuAD impossible), expose *only* the original source
    paragraph prefix; absence is original-paragraph-only, not open-corpus truth.
    """
    if max_tokens <= 0:
        raise ValueError("max_tokens must be positive")
    if not gold_answers:
        pack = pack_naive(
            {document.id: document},
            [SearchResult(document.id, 1.0, 1)],
            max_tokens=max_tokens,
            max_spans=1,
            count_tokens=count_tokens,
            count_method=count_method,
            compact_render=True,
        )
        return OracleWindowResult(
            pack, "negative_original_paragraph_not_open_corpus_proof",
            answer_visible=False,
        )

    # SQuAD official answers have exact verbatim offsets. For duplicate text
    # matches, choose the earliest occurrence deterministically.
    options = []
    for answer in gold_answers:
        if not answer:
            continue
        start = document.text.find(answer)
        if start >= 0:
            options.append((start, start + len(answer), answer))
    if not options:
        return OracleWindowResult(
            EvidencePack((), "", max_tokens, 0, count_method),
            "gold_not_found_in_source",
            answer_visible=False,
        )
    start, end, answer = min(options, key=lambda o: (o[0], o[1] - o[0]))
    tokens = list(_TOKEN.finditer(document.text))
    lo_candidates = [i for i, m in enumerate(tokens) if m.end() > start and m.start() < end]
    if not lo_candidates:
        return OracleWindowResult(
            EvidencePack((), "", max_tokens, 0, count_method),
            "gold_not_tokenizable",
            answer_visible=False,
        )
    left, right = min(lo_candidates), max(lo_candidates)

    def make(lo: int, hi: int) -> tuple[EvidenceSpan, str]:
        # The precise annotated span may fall within a token. A full token
        # window still contains it and keeps source provenance exact.
        a, b = tokens[lo].start(), tokens[hi].end()
        quote = document.text[a:b]
        span = EvidenceSpan(
            label="S1",
            doc_id=document.id,
            start=a,
            end=b,
            quote=quote,
            retrieval_rank=1,
            retrieval_score=1.0,
            overlap_terms=0,
        )
        return span, "[S1]\n" + quote

    span, rendered = make(left, right)
    if count_tokens(rendered) > max_tokens:
        return OracleWindowResult(
            EvidencePack((), "", max_tokens, 0, count_method),
            "gold_too_long_for_token_budget",
            answer_visible=False,
        )

    # Alternating one-token expansions around the actual gold answer; no
    # candidate is retained if it exceeds the exact injected model counter.
    side = 0
    while left > 0 or right < len(tokens) - 1:
        options_for_step = []
        if side % 2 == 0:
            options_for_step = [(-1, 0), (0, 1)]
        else:
            options_for_step = [(0, 1), (-1, 0)]
        advanced = False
        for dl, dr in options_for_step:
            l2, r2 = left + dl, right + dr
            if l2 < 0 or r2 >= len(tokens):
                continue
            proposed_span, proposed_render = make(l2, r2)
            if count_tokens(proposed_render) <= max_tokens:
                left, right = l2, r2
                span, rendered = proposed_span, proposed_render
                advanced = True
                break
        if not advanced:
            break
        side += 1

    if answer not in span.quote:
        raise AssertionError("Oracle diagnostic never truncates the gold answer")
    return OracleWindowResult(
        EvidencePack((span,), rendered, max_tokens, count_tokens(rendered), count_method),
        "gold_answer_centered_privileged_source",
        answer_visible=True,
    )

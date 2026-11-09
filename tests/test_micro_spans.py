from __future__ import annotations

import pytest

from raglab.core import Document, SearchResult
from raglab.micro.spans import _segments, pack_evidence, pack_naive, proxy_tokens


def _docs():
    return {
        "a": Document("a", "The garden has red roses. Trees provide shade."),
        "b": Document("b", "The river runs east. It is next to the garden."),
    }


def _results():
    return [SearchResult("a", 3.5, 1), SearchResult("b", 1.2, 2)]


def test_spans_exact_original_provenance_and_budget():
    docs = _docs()
    result = pack_evidence(
        "Which flowers are in the garden?", docs, _results(), max_tokens=50
    )
    assert result.spans
    assert result.used_tokens <= 50
    assert result.used_tokens == proxy_tokens(result.text)
    for span in result.spans:
        assert span.quote == docs[span.doc_id].text[span.start:span.end]
        assert span.label in result.text
        assert span.doc_id in result.text
        assert span.start >= 0 and span.end > span.start


def test_naive_and_optimized_both_use_same_budget_measure():
    docs = _docs()
    for pack in (
        pack_naive(docs, _results(), max_tokens=22),
        pack_evidence("garden roses", docs, _results(), max_tokens=22),
    ):
        assert pack.used_tokens == proxy_tokens(pack.text)
        assert pack.used_tokens <= 22
        for s in pack.spans:
            assert s.quote == docs[s.doc_id].text[s.start:s.end]


def test_no_lexical_overlap_does_not_fabricate_support():
    p = pack_evidence("xylophone quantum", _docs(), _results())
    assert p.spans == ()
    assert p.text == ""
    assert p.used_tokens == 0


def test_large_sentence_windows_preserve_exact_offsets():
    src = " ".join(f"token{i}" for i in range(70)) + ". A second sentence."
    segs = _segments(src, 12)
    assert len(segs) > 5
    for start, end, quote in segs:
        assert quote == src[start:end]
        assert proxy_tokens(quote) <= 12


def test_multiple_docs_limit_and_untrusted_missing_docs():
    docs = _docs()
    results = [SearchResult("missing", 5, 1), *_results()]
    p = pack_evidence("garden", docs, results, max_spans=1, max_tokens=100)
    assert len(p.spans) == 1
    assert p.spans[0].label == "S1"


@pytest.mark.parametrize("kwargs", [{"max_tokens": 0}, {"max_spans": -1}, {"max_per_document": 0}])
def test_invalid_limits_rejected(kwargs):
    with pytest.raises(ValueError):
        pack_evidence("garden", _docs(), _results(), **kwargs)


def test_custom_token_counter_is_honored():
    docs = _docs()
    # A custom count may be model-specific. The packer must respect it.
    model_like_count = lambda text: len(text)
    p = pack_evidence(
        "garden roses",
        docs,
        _results(),
        max_tokens=110,
        count_tokens=model_like_count,
    )
    assert p.used_tokens == len(p.text)
    assert p.used_tokens <= 110

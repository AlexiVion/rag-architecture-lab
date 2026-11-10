"""Bounded-stream ingestion controls with entirely fictional in-memory records.

These tests do not contact Hugging Face or evaluate a real NLI checkpoint.
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

# Reuse the study's actual standalone script, not a second test-only loader.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "micro"))
from confrag_viewpoint_nli_cpu import read_bounded_public_prefix  # noqa: E402


def _record(group_id: int, conflicting: bool) -> dict:
    return {
        "id": group_id,
        "question": f"What is the fictional outcome of trial {group_id}?",
        "contradicts": conflicting,
        "websites": [
            {"index": 1, "answer": "The report supported the result."},
            {"index": 2, "answer": "The published report agreed with the result."},
            {"index": 3, "answer": "The published report disputed the result."},
        ],
        "answers": [
            {"answer": "Agreed", "index": [1, 2]},
            {"answer": "Disagreed", "index": [3]},
        ],
    }


def _fake_source(monkeypatch, rows):
    blob = b"".join(
        (json.dumps(row, sort_keys=True) + "\n").encode("utf-8") for row in rows
    )
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout=None: io.BytesIO(blob),
    )
    return blob


def test_streaming_selection_is_group_balanced_bounded_and_hashes_inputs(monkeypatch):
    blob = _fake_source(monkeypatch, [
        _record(1, True), _record(2, True), _record(3, False),
        _record(4, False),
    ])
    pairs, meta = read_bounded_public_prefix(
        revision="a" * 40, per_stratum=1, scan_limit=3
    )
    assert len(pairs) == 6
    assert {pair["group_id"] for pair in pairs} == {"1", "3"}
    assert meta["source_rows_scanned"] == 3
    assert meta["selected_question_groups"] == 2
    assert meta["selected_group_balance"]["contradicts_true"] == 1
    assert meta["selected_group_balance"]["contradicts_false"] == 1
    assert meta["prefix_bytes_read"] < len(blob)
    assert len(meta["read_prefix_sha256"]) == 64
    assert len(meta["selected_row_sha256"]) == 2
    assert meta["whole_dataset_file_sha256"] is None


def test_insufficient_balanced_questions_fail_not_fabricate_result(monkeypatch):
    _fake_source(monkeypatch, [_record(1, True), _record(2, True)])
    with pytest.raises(ValueError, match="Could not select"):
        read_bounded_public_prefix(
            revision="a" * 40, per_stratum=1, scan_limit=2
        )


def test_oversized_single_line_is_rejected(monkeypatch):
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *a, **kw: io.BytesIO(b"{" + b" " * 8_000_001 + b"}\n"),
    )
    with pytest.raises(ValueError, match="line exceeded"):
        read_bounded_public_prefix(
            revision="a" * 40, per_stratum=1, scan_limit=2
        )

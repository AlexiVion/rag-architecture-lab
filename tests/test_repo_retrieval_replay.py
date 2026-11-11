"""Tests for a real Python source-bound retrieval trace, without model downloads."""
from __future__ import annotations
import copy
import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("repo_replay", ROOT / "scripts/observatory/export_repo_retrieval_replay.py")
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def test_replay_is_an_actual_unlabelled_retrieval_execution():
    trace = module.build_replay()
    assert trace["kind"] == "repository_retrieval_execution"
    assert trace["status"] == "measured_software_trace_unlabelled"
    assert len(trace["documents"]) == 8
    assert len(trace["queries"]) == 3
    for case in trace["queries"]:
        assert case["qrels"] is None and case["answer"] is None
        for name in ("bm25", "parent_child_bm25"):
            results = case["rankings"][name]
            assert len(results) == 5
            assert len({v["doc_id"] for v in results}) == 5
            assert [v["rank"] for v in results] == [1, 2, 3, 4, 5]


def test_replay_rejects_forged_ranks_labels_and_source_hashes():
    original = module.build_replay()
    module.validate_replay(original)
    for change in (
        lambda x: x["queries"][0]["rankings"]["bm25"][0].update(score=999),
        lambda x: x["queries"][0].update(qrels={"README.md": 1}),
        lambda x: x["documents"][0].update(sha256="0" * 64),
        lambda x: x.update(status="validated_scifact"),
    ):
        value = copy.deepcopy(original)
        change(value)
        with pytest.raises(ValueError):
            module.validate_replay(value)


def test_replay_deterministic_without_neural_dependencies():
    assert module.build_replay() == module.build_replay()


def test_committed_replay_fingerprint_and_rankings_match_current_repo():
    import json
    path = ROOT / "experiments/repo_retrieval_replay.json"
    stored = json.loads(path.read_text(encoding="utf-8"))
    module.validate_replay(stored)

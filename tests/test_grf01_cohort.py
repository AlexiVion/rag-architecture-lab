from __future__ import annotations

import copy
import hashlib
import json

import pytest

from raglab.graph import grf01_cohort


def test_disjoint_cohort_selection_preserves_predeclared_order():
    candidates = [f"q{i:03d}" for i in range(12)]
    exposed = {"q000", "q003", "q011"}
    result = grf01_cohort.select_disjoint_query_ids(candidates, exposed, count=5)
    assert result == ["q001", "q002", "q004", "q005", "q006"]
    assert not (set(result) & exposed)


def test_fails_on_invalid_or_insufficient_pool():
    with pytest.raises(ValueError, match="Duplicate"):
        grf01_cohort.select_disjoint_query_ids(["a", "a"], set(), count=1)
    with pytest.raises(ValueError, match="Not enough"):
        grf01_cohort.select_disjoint_query_ids(["a", "b"], {"a"}, count=2)
    with pytest.raises(ValueError, match="positive"):
        grf01_cohort.select_disjoint_query_ids(["a"], set(), count=0)


def test_rejects_existing_replacement_and_unverified_original(tmp_path, monkeypatch):
    original = tmp_path / "original.json"
    original.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="SHA256"):
        grf01_cohort.freeze_cohort(
            original_report_path=original,
            dataset_cache=tmp_path / "hotpot.json",
            output=tmp_path / "cohort.json",
        )


def test_selection_fingerprint_is_order_sensitive():
    assert grf01_cohort._query_fingerprint(["a", "b"]) != grf01_cohort._query_fingerprint(["b", "a"])
    assert grf01_cohort._query_fingerprint(["a", "b"]) == hashlib.sha256(b"a\nb").hexdigest()


def test_cohort_reservation_is_idempotent_and_source_sealed(tmp_path, monkeypatch):
    from raglab.graph.hotpotqa_benchmark import DATASET_ID, HOTPOT_SHA256
    exposed_ids = [f"old-{i}" for i in range(60)]
    old = {
        "experiment_id": grf01_cohort.PREVIOUS_STUDY_ID,
        "dataset": DATASET_ID,
        "dataset_sha256": HOTPOT_SHA256,
        "sample_seed": 17,
        "sample_count": 60,
        "sample_query_ids_sha256": grf01_cohort._query_fingerprint(exposed_ids),
        "queries": [{"question_id": x} for x in exposed_ids],
    }
    source = tmp_path / "original.json"
    raw = json.dumps(old).encode("utf-8")
    source.write_bytes(raw)
    monkeypatch.setattr(grf01_cohort, "PREVIOUS_STUDY_SHA256", hashlib.sha256(raw).hexdigest())
    cache = tmp_path / "dataset.json"
    cache.write_text("fixture", encoding="utf-8")
    monkeypatch.setattr(grf01_cohort, "cached_hotpotqa", lambda path: path)
    pool = [{"_id": f"q{i:03d}"} for i in range(500)]
    pool[2]["_id"] = "old-4"
    monkeypatch.setattr(grf01_cohort, "load_bridge_dev_rows", lambda path, seed, count: pool)
    output = tmp_path / "cohort.json"
    result = grf01_cohort.freeze_cohort(
        original_report_path=source, dataset_cache=cache, output=output
    )
    assert result["overlap_count_with_grf00"] == 0
    assert len(result["reserved_query_ids"]) == 60
    assert "old-4" not in result["reserved_query_ids"]
    assert result["evaluation_scores"] is None
    assert grf01_cohort.freeze_cohort(
        original_report_path=source, dataset_cache=cache, output=output
    ) == result
    changed = copy.deepcopy(result)
    changed["selection_seed"] = 999
    output.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(ValueError, match="refusing overwrite"):
        grf01_cohort.freeze_cohort(
            original_report_path=source, dataset_cache=cache, output=output
        )

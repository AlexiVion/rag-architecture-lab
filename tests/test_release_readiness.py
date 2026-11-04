"""R0 release engineering checks, entirely offline and without model imports."""
from __future__ import annotations

import json
import shutil

from raglab.release_readiness import PROJECT_ROOT, REQUIRED_FILES, check_repository


def test_repo_distributable_fixture_and_release_metadata_are_valid():
    result = check_repository()
    assert result["status"] == "ENGINEERING_PASS", result["failures"]
    assert result["scientific_release_verified"] is False
    assert result["wow_v1_complete"] is False
    assert result["model_calls"] == 0
    assert result["external_publications"] == 0
    assert result["checks"]["offline_graph_fixture"]["traces"] == 3
    assert result["checks"]["model_registry_contract"]["candidates"] == 10
    assert result["checks"]["model_registry_contract"]["measured"] == 0


def sandbox_snapshot(tmp_path):
    for path in REQUIRED_FILES:
        source = PROJECT_ROOT / path
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    return tmp_path


def test_missing_policy_or_fixture_fails_closed(tmp_path):
    root = sandbox_snapshot(tmp_path)
    (root / "SECURITY.md").unlink()
    status = check_repository(root)
    assert status["status"] == "ENGINEERING_FAIL"
    assert "SECURITY.md" in status["checks"]["required_release_files"]["missing"]


def test_forged_public_graph_fails_contract_and_never_claims_research_pass(tmp_path):
    root = sandbox_snapshot(tmp_path)
    path = root / "apps/explorer/data/demo.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["traces"][0]["answer"] = "Fabricated model answer [S1]."
    path.write_text(json.dumps(data), encoding="utf-8")
    status = check_repository(root)
    assert status["status"] == "ENGINEERING_FAIL"
    assert status["checks"]["offline_graph_fixture"]["status"] == "FAIL"
    assert status["scientific_release_verified"] is False
    assert status["wow_v1_complete"] is False


def test_model_registry_rejects_fabricated_measurements(tmp_path):
    root = sandbox_snapshot(tmp_path)
    path = root / "experiments/model_matrix_10_proposed.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["models"][0]["execution_status"] = "measured"
    data["models"][0]["measured_metrics"] = None
    path.write_text(json.dumps(data), encoding="utf-8")
    result = check_repository(root)
    assert result["status"] == "ENGINEERING_FAIL"
    assert result["checks"]["model_registry_contract"]["status"] == "FAIL"

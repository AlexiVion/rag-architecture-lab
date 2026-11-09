from __future__ import annotations

import json
from pathlib import Path

import pytest

from raglab.micro.__main__ import main


FIXTURE = Path(__file__).resolve().parents[1] / "experiments" / "micro_smoke_fixture.json"


def test_registry_cli_writes_explicitly_unmeasured_manifest(tmp_path):
    out = tmp_path / "registry.json"
    main(["registry", "--output", str(out)])
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["status"] == "proposed_unmeasured"
    assert payload["model_downloads_performed"] is False


def test_prepare_cli_exercises_real_offline_bm25_and_context(tmp_path):
    out = tmp_path / "preparation.json"
    main(
        ["prepare", "--data", str(FIXTURE), "--output", str(out),
         "--model-id", "pythia-14m", "--max-context-tokens", "80"]
    )
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["scientific_validation"] == "NOT_RUN"
    assert len(result["cases"]) == 15


def test_cli_refuses_implicit_remote_model_download(tmp_path):
    out = tmp_path / "run.json"
    with pytest.raises(SystemExit) as err:
        main(
            ["prepare", "--data", str(FIXTURE), "--output", str(out),
             "--backend", "local"]
        )
    assert err.value.code == 2
    assert not out.exists()


def test_score_cli_no_fake_accuracy(tmp_path):
    path, out = tmp_path / "reviews.json", tmp_path / "scored.json"
    path.write_text("[]", encoding="utf-8")
    main(["score", "--reviews", str(path), "--output", str(out)])
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["scientific_validation"] == "NO_EVIDENCE"

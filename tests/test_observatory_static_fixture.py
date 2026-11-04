"""Keep the public website's fixture synchronized with real Python graph output."""
from __future__ import annotations

import json
from pathlib import Path

from raglab.observatory.fixture import create_demo_artifact, validate_observatory_artifact

ROOT = Path(__file__).resolve().parents[1]


def test_committed_demo_json_matches_deterministic_graph_export():
    source = ROOT / "apps/explorer/data/demo.json"
    published = source.read_text(encoding="utf-8")
    expected = json.dumps(create_demo_artifact(), ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    assert published == expected, "Regenerate fixture with python -m raglab.observatory.fixture"
    validate_observatory_artifact(json.loads(published))


def test_observatory_has_real_entrypoint_and_no_injected_mock_benchmarks():
    html = (ROOT / "apps/explorer/index.html").read_text(encoding="utf-8")
    js = (ROOT / "apps/explorer/app.js").read_text(encoding="utf-8")
    assert '<script type="module" src="./app.js"></script>' in html
    assert 'id="graph-canvas"' in html
    assert "illustrative_fixture_not_benchmark" in js
    assert "document.createElementNS" in js
    assert "textContent" in js

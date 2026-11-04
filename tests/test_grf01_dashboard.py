from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_grf01_web_panel_uses_only_audited_local_output():
    html = (ROOT / "apps/explorer/index.html").read_text(encoding="utf-8")
    js = (ROOT / "apps/explorer/app.js").read_text(encoding="utf-8")
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert 'id="grf01-section"' in html
    assert 'id="grf01-metrics"' in html
    assert "grf01-summary.local.json" in js
    assert "audited_local_existing_run" in js
    assert "verified_grf01_retrieval_aggregate" in js
    assert "source_report_sha256" in js
    assert "apps/explorer/data/grf01-summary.local.json" in ignored
    assert "innerHTML" not in js

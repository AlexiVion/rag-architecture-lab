from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_hotpotqa_viewer_requires_verified_local_aggregate():
    html = (ROOT / "apps/explorer/index.html").read_text(encoding="utf-8")
    js = (ROOT / "apps/explorer/app.js").read_text(encoding="utf-8")
    assert 'id="benchmark-heading"' in html
    assert 'id="benchmark-metrics"' in html
    assert "hotpotqa-summary.local.json" in js
    assert "verified_from_local_per_query_records" in js
    assert "source_report_sha256" in js
    assert "textContent" in js
    assert "innerHTML" not in js


def test_private_report_aggregate_is_gitignored():
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "apps/explorer/data/hotpotqa-summary.local.json" in ignore
    assert "runs/" in ignore

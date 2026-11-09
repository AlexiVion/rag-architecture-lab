
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_published_grf_aggregates_are_source_hashed_and_math_consistent():
    expected = {
        "grf00": ("962dc3b12d0086857ad94198cf2b1fff7a49ca5f7df069e9575a6daaf778f016",
                  "GRF00-HOTPOTQA-DEV-01"),
        "grf01": ("f2167bc7220554b1864648c5c5de0b67544bfbdba585a4aeed8f466927fcb2b4",
                  "GRF01-HOTPOTQA-DEV-01"),
    }
    for key, (sha, exp) in expected.items():
        data = json.loads((ROOT / f"apps/explorer/data/{key}-summary.public.json").read_text(encoding="utf-8"))
        assert data["publication_status"] == "published_operator_audit_summary"
        assert data["source_report_sha256"] == sha
        assert data["experiment_id"] == exp
        assert data["sample_count"] == 60
        assert sum(group["cases"] for group in data["subgroups"].values()) == 60
        assert not any("question" in k or "article" in k or "passage" in k for k in data)
        for metric in data["metrics"].values():
            baseline = metric["bm25"] if key == "grf00" else metric["hybrid"]
            candidate = metric["graph_plus_bm25"] if key == "grf00" else metric["graph_hybrid"]
            delta = metric["paired_delta"] if key == "grf00" else metric["graph_hybrid_minus_hybrid_delta"]
            assert math.isclose(candidate - baseline, delta, abs_tol=1e-10)
            lo, hi = metric["paired_bootstrap_95ci"]
            assert lo <= hi and -1 <= lo <= 1 and -1 <= hi <= 1


def test_explorer_falls_back_to_published_results_only_on_missing_local_files():
    js = (ROOT / "apps/explorer/app.js").read_text(encoding="utf-8")
    html = (ROOT / "apps/explorer/index.html").read_text(encoding="utf-8")
    assert "grf00-summary.public.json" in js
    assert "grf01-summary.public.json" in js
    assert "local.status !== 404" in js
    assert "published_operator_audit_summary" in js
    assert "audited_local_existing_run" in js
    assert "verified_from_local_per_query_records" in js
    assert "innerHTML" not in js
    assert "grf01-section" in html

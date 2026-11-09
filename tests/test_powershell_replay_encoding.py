"""Ensure Windows PowerShell 5.1 reads the offline replay entrypoint safely.

Without a BOM, PowerShell 5.1 can use the legacy codepage: an em dash
may decode as a smart quotation mark and break PowerShell string parsing.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = ROOT / "scripts" / "replay-m2-citations-local.ps1"


def test_replay_script_is_ascii_safe_for_windows_powershell_51():
    raw = ENTRYPOINT.read_bytes()
    assert raw.isascii(), "PowerShell 5.1 entrypoint must be plain ASCII"
    assert raw.endswith(b"\n")


def test_replay_script_requires_tests_before_offline_replay():
    script = ENTRYPOINT.read_text(encoding="ascii")
    assert script.index("-m pytest -q") < script.index("-m raglab.evaluation.m2_live_v2_replay")
    assert 'if ($LASTEXITCODE -ne 0) { throw "M2_CITATION_V2_TESTS_FAILED" }' in script
    assert "M2_LIVE02_20261104T185026616108Z.json" in script
    assert "M2_LIVE02_SYNTAX_REPLAY.json" in script
    assert "-m raglab.evaluation.m2_live_v2_replay" in script
    assert "-m raglab.evaluation.m2_live_v2 --" not in script

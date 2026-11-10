"""Prevent non-academic promotional material in tracked repository source.

The check intentionally covers the current working tree, not Git history or
external issue titles. It does not evaluate the scientific validity of results.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXTENSIONS = (".md", ".yaml", ".yml", ".toml", ".cff", ".py", ".ps1", ".sh",
              ".js", ".mjs", ".ts", ".tsx", ".html", ".css", ".json")
# Concatenate word parts so the policy's own source is not a false positive.
FORBIDDEN = (
    "w" + "ow",
    "linked" + "in",
    "port" + "folio",
    "show" + "case",
    "tech" + "nical-" + "port" + "folio",
    "capability-" + "proof",
    "personal " + "brand",
    "cold " + "call",
)


def test_tracked_research_surface_has_no_promotional_markers():
    proc = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT,
        check=True, stdout=subprocess.PIPE,
    )
    failures = []
    for raw in proc.stdout.split(b"\0"):
        if not raw:
            continue
        path = Path(raw.decode("utf-8"))
        if not path.name.endswith(EXTENSIONS):
            continue
        # A filename is part of the publicly presented research tree.
        name = path.as_posix().lower()
        content_path = ROOT / path
        if not content_path.is_file():
            continue
        content = content_path.read_text(encoding="utf-8", errors="replace")
        for term in FORBIDDEN:
            pat = re.compile(r"(?<![a-z])" + re.escape(term) + r"(?![a-z])", re.I)
            if pat.search(name) or pat.search(content):
                failures.append((path.as_posix(), term))
    assert not failures, "Non-academic tracked material: " + str(failures[:100])

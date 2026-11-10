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


def test_internal_markdown_document_references_resolve():
    """Check scholarly documents do not refer to withdrawn or missing .md files."""
    import urllib.parse

    proc = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, check=True, stdout=subprocess.PIPE
    )
    broken = []
    for raw in proc.stdout.split(b"\0"):
        if not raw:
            continue
        path = Path(raw.decode("utf-8"))
        if path.suffix.lower() != ".md" or not (ROOT / path).is_file():
            continue
        content = (ROOT / path).read_text(encoding="utf-8", errors="replace")
        # Ignore code fences: they can contain deliberately nonexistent examples.
        content = re.sub(r"(?ms)^\s*```[^\n]*\n.*?^\s*```\s*$", "", content)
        for match in re.finditer(r"(?<![!])\[[^\]]+\]\(([^)]+)\)", content):
            target = match.group(1).strip().split(" ", 1)[0]
            if target.startswith(("http:", "https:", "mailto:", "#", "data:")):
                continue
            target = urllib.parse.unquote(target.split("#", 1)[0].split("?", 1)[0])
            if not target or not target.lower().endswith(".md"):
                continue
            local = ((ROOT / path.parent) / target).resolve()
            if not local.is_relative_to(ROOT.resolve()) or not local.is_file():
                broken.append((path.as_posix(), target))
    assert not broken, "Broken local research document links: " + str(broken[:100])


def test_typescript_module_stems_are_portable_on_windows():
    """TypeScript resolves '.ts' before '.tsx' on a case-insensitive disk.

    Two files with the same case-folded stem but different extensions/casing
    may pass CI on Linux yet bind the wrong import on Windows.
    """
    root = ROOT / "apps" / "observatory" / "src"
    seen = {}
    collisions = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in (".ts", ".tsx"):
            continue
        relative = path.relative_to(root)
        normalized = (relative.parent / relative.stem).as_posix().casefold()
        existing = seen.get(normalized)
        if existing is not None:
            collisions.append((existing, relative.as_posix()))
        else:
            seen[normalized] = relative.as_posix()
    assert not collisions, (
        "Nonportable TypeScript module stem collision (.ts/.tsx, case-insensitive): "
        + str(collisions)
    )

"""Offline engineering release checks for the RAG Architecture Lab.

This CLI checks distributable source/fixture integrity, NOT scientific
correctness or publication approval. It never downloads a model or dataset.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tomllib
from pathlib import Path

from raglab.observatory.fixture import create_demo_artifact, validate_observatory_artifact

PROJECT_ROOT = Path(__file__).resolve().parents[2]

REQUIRED_FILES = (
    "README.md",
    "LICENSE",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
    "CHANGELOG.md",
    "CITATION.cff",
    "pyproject.toml",
    "docs/EXPERIMENT_PROTOCOL.md",
    "docs/RELEASE_WOW_BLUEPRINT.md",
    "apps/explorer/index.html",
    "apps/explorer/app.js",
    "apps/explorer/styles.css",
    "apps/explorer/data/demo.json",
    "apps/explorer/data/grf00-summary.public.json",
    "apps/explorer/data/grf01-summary.public.json",
    "experiments/model_matrix_10_proposed.json",
    ".github/workflows/offline-tests.yml",
)

EXPECTED_ROLES = {
    "embedding": 3,
    "reranking": 2,
    "stance_nli": 2,
    "generation": 3,
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _first_difference(actual: object, expected: object, where: str = "$") -> str | None:
    """Find a small inspectable source-vs-published fixture mismatch."""
    if type(actual) is not type(expected):
        return f"{where}: types differ ({type(actual).__name__} vs {type(expected).__name__})"
    if isinstance(actual, dict):
        if actual.keys() != expected.keys():
            return f"{where}: JSON field sets differ"
        for key in sorted(actual):
            found = _first_difference(actual[key], expected[key], where + "." + str(key))
            if found:
                return found
    elif isinstance(actual, list):
        if len(actual) != len(expected):
            return f"{where}: lengths differ ({len(actual)} vs {len(expected)})"
        for i, (a, b) in enumerate(zip(actual, expected)):
            found = _first_difference(a, b, f"{where}[{i}]")
            if found:
                return found
    elif actual != expected:
        return f"{where}: {str(actual)[:90]!r} vs {str(expected)[:90]!r}"
    return None


def check_repository(root: Path = PROJECT_ROOT) -> dict:
    failures: list[str] = []
    observed: dict = {"repository": str(root), "checks": {}, "failures": failures}
    missing = [name for name in REQUIRED_FILES if not (root / name).is_file()]
    observed["checks"]["required_release_files"] = {
        "status": "PASS" if not missing else "FAIL",
        "missing": missing,
    }
    if missing:
        failures.append("Required R0 release files missing: " + ", ".join(missing))

    try:
        metadata = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
        version = metadata["project"]["version"]
        observed["checks"]["package_metadata"] = {
            "status": "PASS" if metadata["project"]["name"] == "rag-architecture-lab" else "FAIL",
            "version": version,
            "python_requires": metadata["project"]["requires-python"],
        }
        if observed["checks"]["package_metadata"]["status"] != "PASS":
            failures.append("Distribution name changed")
    except (FileNotFoundError, KeyError, ValueError) as exc:
        failures.append("Invalid package metadata: " + str(exc))
        observed["checks"]["package_metadata"] = {"status": "FAIL"}

    fixture_path = root / "apps/explorer/data/demo.json"
    try:
        raw = fixture_path.read_bytes()
        fixture = json.loads(raw)
        validate_observatory_artifact(fixture)
        # JSON arrays encode Python tuple fields as lists. Compare exactly
        # the *serializable published representation*, not raw dataclass
        # tuple/list container types (same safeguard as archived M2 audits).
        expected = json.loads(json.dumps(create_demo_artifact(), ensure_ascii=False))
        if fixture != expected:
            raise ValueError("Published fictional graph differs from deterministic source: " + str(_first_difference(fixture, expected)))
        if any(x.get("answer") is not None for x in fixture["traces"]):
            raise ValueError("Illustrative fixture contains a purported generated answer")
        observed["checks"]["offline_graph_fixture"] = {
            "status": "PASS",
            "sha256": _sha256(raw),
            "traces": len(fixture["traces"]),
            "publication_status": fixture["publication_status"],
        }
    except (OSError, KeyError, TypeError, ValueError) as exc:
        failures.append("Offline graph fixture invalid: " + str(exc))
        observed["checks"]["offline_graph_fixture"] = {"status": "FAIL"}

    for filename, expected_id in (
        ("grf00-summary.public.json", "GRF00-HOTPOTQA-DEV-01"),
        ("grf01-summary.public.json", "GRF01-HOTPOTQA-DEV-01"),
    ):
        path = root / "apps/explorer/data" / filename
        try:
            summary = json.loads(path.read_text(encoding="utf-8"))
            if (
                summary.get("schema_version") != 1
                or summary.get("experiment_id") != expected_id
                or not summary.get("source_report_sha256")
                or summary.get("sample_count", 0) <= 0
            ):
                raise ValueError("Public benchmark summary schema/provenance incomplete")
            observed["checks"][filename] = {
                "status": "PASS",
                "source_report_sha256": summary["source_report_sha256"],
                "sample_count": summary["sample_count"],
            }
        except (OSError, TypeError, ValueError, KeyError) as exc:
            failures.append(filename + " invalid: " + str(exc))
            observed["checks"][filename] = {"status": "FAIL"}

    try:
        registry = json.loads(
            (root / "experiments/model_matrix_10_proposed.json").read_text(encoding="utf-8")
        )
        from collections import Counter
        models = registry["models"]
        counts = Counter(item["role"] for item in models)
        if (
            len(models) != 10
            or len({item["id"] for item in models}) != 10
            or counts != EXPECTED_ROLES
            or len(registry.get("previously_evaluated_baselines", [])) != 4
        ):
            raise ValueError("Ten model candidates / roles / baselines have changed")
        if any(model.get("execution_status") == "measured"
               and model.get("measured_metrics") is None for model in models):
            raise ValueError("Registry claims a measurement without metrics")
        measured = sum(bool(item.get("measured_metrics")) for item in models)
        observed["checks"]["model_registry_contract"] = {
            "status": "PASS",
            "candidates": len(models),
            "measured": measured,
            "not_measured": len(models) - measured,
        }
    except (OSError, KeyError, TypeError, ValueError) as exc:
        failures.append("MOD-10 registry invalid: " + str(exc))
        observed["checks"]["model_registry_contract"] = {"status": "FAIL"}

    observed["status"] = "ENGINEERING_PASS" if not failures else "ENGINEERING_FAIL"
    observed["scientific_release_verified"] = False
    observed["wow_v1_complete"] = False
    observed["model_calls"] = 0
    observed["external_publications"] = 0
    return observed


def main() -> int:
    cli = argparse.ArgumentParser(description="Offline engineering prerequisites for WOW v1")
    cli.add_argument("--root", type=Path, default=PROJECT_ROOT)
    cli.add_argument("--json-output", type=Path, default=None)
    args = cli.parse_args()
    result = check_repository(args.root)
    for name, data in result["checks"].items():
        print("R0_CHECK=" + name + " STATUS=" + data["status"])
    print("R0_ENGINEERING_STATUS=" + result["status"])
    print("WOW_V1_SCIENTIFIC_GATES=NOT_VERIFIED")
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    if result["failures"]:
        for item in result["failures"]:
            print("R0_BLOCKER=" + item, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

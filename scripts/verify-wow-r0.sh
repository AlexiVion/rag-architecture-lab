#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHON="${PYTHON:-python3}"
echo "=== WOW R0: complete local Python tests ==="
"$PYTHON" -m pytest -q
echo "=== WOW R0: source and viewer integrity ==="
"$PYTHON" -m raglab.release_readiness --json-output runs/release-r0/engineering.json
echo "=== WOW R0: CLI ==="
"$PYTHON" -m raglab.cli --help
echo "=== WOW R0: build package without downloading dependencies ==="
"$PYTHON" -m pip wheel --no-deps --no-build-isolation --wheel-dir runs/release-r0/wheels .
echo "WOW_R0_LOCAL_ENGINEERING_CHECK_PASS"
echo "This does NOT certify scientific M2 correctness or completion of WOW v1.0."

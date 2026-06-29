#!/usr/bin/env bash
# Provenant Phase 1 demo — seal a sample lending portfolio, verify it, detect
# silent regressions across a model change, and render a customer-facing report.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3}"
export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

"$PYTHON_BIN" -m provenant.demo "$@"

echo
echo "Open outputs/provenant_demo/audit_report.html in a browser to view the report."

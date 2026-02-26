#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3.11}"
VENV_DIR=".venv-repro"

rm -rf "$VENV_DIR"
"$PYTHON_BIN" -m venv "$VENV_DIR"

source "$VENV_DIR/bin/activate"
python -m pip install -U pip
python -m pip install -r requirements.lock
python -m pip install -e .

pytest
python scripts/determinism_check.py

python scripts/generate_manifest.py --verify
python scripts/generate_manifest.py
python scripts/generate_manifest.py --verify

#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  if command -v python3.11 >/dev/null 2>&1 && python3.11 -V >/dev/null 2>&1; then
    PYTHON_BIN="python3.11"
  elif command -v python3 >/dev/null 2>&1 && python3 -V >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  else
    PYTHON_BIN="python"
  fi
fi
VENV_DIR=".venv-repro"

rm -rf "$VENV_DIR"
"$PYTHON_BIN" -m venv "$VENV_DIR"

source "$VENV_DIR/bin/activate"
export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
python -m pip install -U pip
python -m pip install -r requirements.lock
python -m pip install -e .

pytest
python scripts/determinism_check.py

if ! python scripts/generate_manifest.py --verify; then
  git diff -- MANIFEST.sha256 || true
  exit 1
fi
python scripts/generate_manifest.py
if ! python scripts/generate_manifest.py --verify; then
  git diff -- MANIFEST.sha256 || true
  exit 1
fi

#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3}"

if [[ $# -ne 1 ]]; then
  echo "Usage: scripts/tamper_casefile.sh <ledger_dir>" >&2
  exit 2
fi

ledger_dir="$1"
if [[ ! -d "$ledger_dir" ]]; then
  echo "Ledger directory not found: $ledger_dir" >&2
  exit 2
fi

tampered_ledger_dir="$("$PYTHON_BIN" scripts/create_tampered_ledger_copy.py "$ledger_dir")"

replay_output_file="$(mktemp)"
trap 'rm -f "$replay_output_file"' EXIT

if "$PYTHON_BIN" -W "ignore::RuntimeWarning" -m core.determinism.replay \
  "$tampered_ledger_dir" --strict-manifest >"$replay_output_file" 2>&1; then
  cat "$replay_output_file"
  echo "Tampered replay unexpectedly succeeded." >&2
  exit 1
fi

echo "TAMPER_DETECTED_OK"

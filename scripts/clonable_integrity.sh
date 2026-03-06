#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3}"
CREATED_UTC="${CREATED_UTC:-2026-03-06T10:00:00Z}"
CORE_VERSION="${CORE_VERSION:-0.4.0}"
RULESET_ID="${RULESET_ID:-ruleset.core.v1}"
MAX_CHUNKS="${MAX_CHUNKS:-20}"
MAX_EVENTS="${MAX_EVENTS:-30}"

required_paths=(
  "scripts/demo.py"
  "scripts/extract_ledger_dir.py"
  "scripts/self_casefile_run_id.py"
  "docs/casefiles/iota_verbum_self"
  "MANIFEST.sha256"
)
for required_path in "${required_paths[@]}"; do
  if [[ ! -e "$required_path" ]]; then
    echo "Required path missing: $required_path" >&2
    exit 2
  fi
done

query="Build a deterministic self-casefile for IOTA VERBUM documentation evidence."
prompt="Produce a verified world model and sealed casefile for this repository corpus."

run_id="$("$PYTHON_BIN" scripts/self_casefile_run_id.py \
  --folder docs/casefiles/iota_verbum_self \
  --query "$query" \
  --prompt "$prompt" \
  --max-chunks "$MAX_CHUNKS" \
  --created-utc "$CREATED_UTC" \
  --core-version "$CORE_VERSION" \
  --ruleset-id "$RULESET_ID" \
  --world true)"
run_dir="outputs/demo/$run_id"
rm -rf "$run_dir"

demo_output_file="$(mktemp)"
replay_output_file="$(mktemp)"
trap 'rm -f "$demo_output_file" "$replay_output_file"' EXIT

if ! "$PYTHON_BIN" scripts/demo.py \
  --folder docs/casefiles/iota_verbum_self \
  --query "$query" \
  --prompt "$prompt" \
  --max-chunks "$MAX_CHUNKS" \
  --created-utc "$CREATED_UTC" \
  --core-version "$CORE_VERSION" \
  --ruleset-id "$RULESET_ID" \
  --world true \
  --max-events "$MAX_EVENTS" >"$demo_output_file" 2>&1; then
  cat "$demo_output_file"
  exit 1
fi

if ! ledger_dir="$("$PYTHON_BIN" scripts/extract_ledger_dir.py "$demo_output_file")"; then
  cat "$demo_output_file"
  exit 2
fi

if ! "$PYTHON_BIN" -W "ignore::RuntimeWarning" -m core.determinism.replay \
  "$ledger_dir" --strict-manifest >"$replay_output_file" 2>&1; then
  cat "$replay_output_file"
  exit 1
fi

echo "CLONABLE_INTEGRITY_OK"

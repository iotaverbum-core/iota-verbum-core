# Integrity Path

This is the canonical 4-step trust loop for IOTA VERBUM CORE.

## Prerequisites

- Python 3.11+
- Dependencies installed:
  - `python -m pip install -U pip`
  - `python -m pip install -r requirements.lock`
  - `python -m pip install -e .`
- Run from repository root.

## 1) Generate a Self-Casefile

PowerShell (canonical):

```powershell
.\scripts\clonable_integrity.ps1
```

Expected final line:

```text
CLONABLE_INTEGRITY_OK
```

Underlying command path (equivalent generation route) is documented in `docs/SELF_CASEFILE_DEMO.md`.

## 2) Inspect the Casefile

Viewer (read-only):

1. Open `docs/proof_trace_viewer.html` in a browser.
2. Load the generated `casefile.json`.

CLI (terminal-native):

```powershell
python -m core.casefile.inspect outputs/demo/<run_id>/casefile.json
```

## 3) Replay Verify

```powershell
python -m core.determinism.replay outputs/demo/<run_id>/ledger/<bundle_sha256> --strict-manifest
```

Expected result: replay verification OK with exit code `0`.

## 4) Tamper and Detect Failure

```powershell
.\scripts\tamper_casefile.ps1 -LedgerDir outputs/demo/<run_id>/ledger/<bundle_sha256>
```

Expected final line:

```text
TAMPER_DETECTED_OK
```

Tamper checks are performed on copied artifacts. The original ledger directory is not modified in-place.

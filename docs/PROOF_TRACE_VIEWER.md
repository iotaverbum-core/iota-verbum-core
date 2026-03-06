# Proof Trace Viewer (Read-Only)

`docs/proof_trace_viewer.html` is a local, read-only helper for inspecting `casefile.json`.

## Scope

- Displays selected casefile fields for human inspection.
- Does not mutate casefile or ledger artifacts.
- Does not perform replay verification.

Replay verification remains authoritative:

```powershell
python -m core.determinism.replay <ledger_dir> --strict-manifest
```

## Usage

1. Generate a casefile (`.\scripts\clonable_integrity.ps1`).
2. Open `docs/proof_trace_viewer.html`.
3. Load the generated `casefile.json`.
4. Use `python -m core.casefile.inspect <casefile.json>` for terminal summary and `python -m core.determinism.replay <ledger_dir> --strict-manifest` for authoritative verification.

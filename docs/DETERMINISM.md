# Determinism

## Contract

Given identical inputs, manifests, templates, and pinned dependencies, the core engine must produce byte-identical outputs.

Determinism is enforced by:
- Canonical JSON serialization (`core.attestation.canonicalize_json`).
- Stable ordering (sorted keys, stable token/segment ordering).
- No hidden randomness or time-based fields in outputs.
- Explicit input resolution via manifests with SHA-256 verification.

## Verification

Use the reproducibility script:

```powershell
.\scripts\verify_reproducibility.ps1
```

This script:
1. Creates a clean venv.
2. Installs pinned dependencies.
3. Runs tests.
4. Runs determinism checks twice and diffs outputs.
5. Regenerates `MANIFEST.sha256` and verifies no drift.

The same flow is executed in CI on every push.

# Self-Casefile Demo

This demo proves IOTA VERBUM can ingest its own real project documentation and produce a sealed, replayable Casefile plus World Model from non-synthetic evidence.

## Manual Run (Two Commands)

```powershell
python scripts/demo.py `
  --folder docs/casefiles/iota_verbum_self `
  --query "Build a deterministic self-casefile for IOTA VERBUM documentation evidence." `
  --prompt "Produce a verified world model and sealed casefile for this repository corpus." `
  --max-chunks 20 `
  --created-utc 2026-03-06T10:00:00Z `
  --core-version 0.4.0 `
  --ruleset-id ruleset.core.v1 `
  --world true `
  --max-events 30
```

Then verify replay using the `ledger_dir` printed by the demo:

```powershell
python -m core.determinism.replay outputs/demo/<run_id>/ledger/<bundle_sha256> --strict-manifest
```

## One-Command Run

```powershell
.\scripts\self_casefile.ps1
```

The runner executes the deterministic world demo, extracts `ledger_dir` from output, and runs strict replay verification.

## Scope Note

Verification guarantees reproducibility and provenance integrity of the sealed artifacts. It does not by itself guarantee truth beyond the provided evidence corpus.

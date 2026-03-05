# Casefile v1

Casefile is the v0.4 beachhead output contract for deterministic incident timeline work.
It is an index artifact that summarizes and points to sealed provenance artifacts.

## Product Promise

- Same committed inputs + same parameters + same `created_utc` -> byte-identical `casefile.json`.
- No wall-clock timestamps are used.
- Canonical JSON is used for serialized artifacts.
- Replay verification remains the source of truth for sealed ledger integrity.

## CLI Usage

Run world mode demo and produce casefile:

```powershell
python -m proposal.cli_demo `
  --folder data\legal_contract_sample `
  --query "api key exposure" `
  --prompt "build world timeline" `
  --max-chunks 8 `
  --created-utc 2026-03-05T00:00:00Z `
  --core-version 0.4.0 `
  --ruleset-id ruleset.core.v1 `
  --world true
```

The run directory includes:

- `sealed_output.json`
- `attestation.json`
- `evidence_bundle.json`
- `casefile.json`
- `ledger/<bundle_sha256>/...`

## Replay Verification

```powershell
python -m core.determinism.replay outputs/demo/<run_id>/ledger/<bundle_sha256> --strict-manifest
```

## Non-goals

- Casefile does not replace sealed output or attestation.
- Casefile is an index summary; deep reasoning remains in `output.json` and linked narratives.
- Casefile self-hash uses a cycle-safe preimage that excludes output/attestation display hashes.

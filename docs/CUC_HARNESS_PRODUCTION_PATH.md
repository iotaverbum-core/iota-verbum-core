# CUC Harness Production Path

The production CUC path is not the legacy natural-language scorer loop. The
production path is:

```text
structured proposer -> RevisionDelta -> verifier -> deterministic ledger
```

## Components

- Proposer: emits a structured `RevisionDelta`.
- Verifier: checks the proposed delta against the expected structured mutation
  contract and returns stable reason families for rejection analysis.
- Ledger commit: accepted deltas can be sealed with the input packs, verifier
  result, and attestation record through the deterministic ledger primitives.

## Runner Support

The smoke matrix runners now report:

- `json_valid_count`
- `verifier_accepted_count`
- `ledger_committed_count`
- `verifier_reasons`
- `verifier_reason_families`
- optional `ledger_commit` metadata

Use `--ledger-root <path>` with the Claude or DeepSeek structured smoke matrix
runner to seal accepted deltas:

```powershell
python scripts/claude_cuc_smoke_matrix.py `
  --output-dir cuc-results\claude_smoke_matrix\latest `
  --ledger-root cuc-results\claude_smoke_matrix\latest\ledger
```

Accepted deltas are committed. Rejected deltas remain uncommitted and retain
verifier reason families for diagnosis.

## 24-Case Production Probe

The gated 24-case Claude production probe uses the existing v4 candidate fixture
set from `benchmark/cuc_v4_candidate_params.json`. It does not generate new
fixtures.

Dry-run the case plan without API calls:

```powershell
python scripts/claude_cuc_24_production_probe.py --dry-run
```

Live execution must wait for explicit approval because it calls the Claude API:

```powershell
python scripts/claude_cuc_24_production_probe.py `
  --model claude-sonnet-4-6 `
  --output-dir cuc-results\claude_24_production_probe\latest `
  --rate-limit-retries 5 `
  --rate-limit-sleep-seconds 70
```

The script defaults `--ledger-root` to `<output-dir>/ledger`, so accepted cases
are sealed automatically.

Latest audited result:

- Live Claude run: 24/24 JSON valid, 23/24 verifier accepted, 23/24 ledger
  committed.
- Rejection root cause: stale fixture-gold rank expectation in
  `CUCV4-INVARIANT-01-COUNTERPARTY-RESPONSE-LEGAL-CONTRACT`.
- Corrected offline replay: same live Claude outputs, 24/24 verifier accepted,
  24/24 ledger committed, no additional API calls.
- Audit report:
  `cuc-docs/CUC_CLAUDE_24_PRODUCTION_PROBE_2026_05_28.md`.

## Claim Boundary

The legacy 50-case natural-language scorer can still be used as supporting
research, but production readiness should be argued from structured verifier
acceptance and ledger commitability.

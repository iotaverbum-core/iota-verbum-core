# Demo Fixtures

Casefile Studio includes deterministic sample dossiers in `data/demo_cases/`.

Registry file:

- `data/demo_cases/fixtures.json`

## Included Fixtures

1. `timeline_breach_chain`
   - Folder: `data/demo_cases/timeline_breach_chain`
   - Focus: timeline-heavy incident chain
   - Signal: ordered events, leakage lifecycle, remediation progression

2. `secret_state_conflict`
   - Folder: `data/demo_cases/secret_state_conflict`
   - Focus: contradiction-heavy secret state evidence
   - Signal: state conflict (`env-only` vs `never-in-repo`) and unknown ownership

3. `policy_control_mismatch`
   - Folder: `data/demo_cases/policy_control_mismatch`
   - Focus: policy/compliance mismatch
   - Signal: policy controls vs observed production handling behavior

## Fixture Contract

- Files are committed `.md` or `.txt` evidence inputs.
- Inputs are deterministic and stable for repeated demo runs.
- Each fixture pins default run parameters in the registry:
  - `created_utc`
  - `core_version`
  - `ruleset_id`
  - `max_chunks`
  - `max_events`

## Expected Artifacts Per Run

For world mode runs:

- `evidence_pack.json`
- `evidence_bundle.json`
- `world_model.json`
- `sealed_output.json`
- `attestation.json`
- `casefile.json`
- `ledger/<bundle_sha256>/bundle.json`
- `ledger/<bundle_sha256>/output.json`
- `ledger/<bundle_sha256>/attestation.json`

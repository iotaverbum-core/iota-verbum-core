# iota-verbum-core

IOTA VERBUM CORE is a deterministic extraction and provenance engine for audit-sensitive document workflows. The core promise is that the same committed input, pinned dependencies, and repository state produce the same output bytes and the same verification record.

This repository contains the deterministic core only: domain extractors, schemas, manifests, provenance tools, and reproducibility checks.

Casefile v1 is now available as the beachhead world output contract: a deterministic index artifact (`casefile.json`) that summarizes verified timeline state, contradictions, unknowns, receipts, and links to sealed ledger outputs.

## 30-Second Trust Loop

1. Generate deterministic self-casefile + strict replay:
   - `.\scripts\clonable_integrity.ps1`
2. Inspect casefile:
   - `python -m core.casefile.inspect outputs/demo/<run_id>/casefile.json`
   - `docs/proof_trace_viewer.html` (read-only)
3. Authoritative replay command:
   - `python -m core.determinism.replay outputs/demo/<run_id>/ledger/<bundle_sha256> --strict-manifest`
4. Tamper check (copied artifacts only; original ledger unchanged):
   - `.\scripts\tamper_casefile.ps1 -LedgerDir outputs/demo/<run_id>/ledger/<bundle_sha256>`

See `docs/INTEGRITY_PATH.md` for the canonical 4-step path.

## Quickstart

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.lock
python -m pip install -e .
pytest tests/ -v
```

## Codex Quickstart

```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest -q
.\scripts\clonable_integrity.ps1
```

## Casefile Studio Demo App

Run the production demo app locally:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.lock
python -m pip install -e .[dev]
uvicorn iota_verbum_api.app:app --host 0.0.0.0 --port 8000
```

Open:

- `http://localhost:8000/` for Casefile Studio

Primary API endpoints:

- `GET /api/fixtures`
- `POST /api/runs/sample`
- `POST /api/runs/upload`
- `GET /api/runs/{run_id}/summary`
- `POST /api/runs/{run_id}/replay-verify`

## Demo Fixtures

Curated deterministic fixtures are in `data/demo_cases/`:

- `timeline_breach_chain`
- `secret_state_conflict`
- `policy_control_mismatch`

Fixture contract and behavior notes:

- `docs/DEMO_FIXTURES.md`

## Artifact Inspection

After a sample run completes:

1. Inspect casefile:
   - `python -m core.casefile.inspect outputs/demo/<run_id>/casefile.json`
2. Inspect run artifacts:
   - `outputs/demo/<run_id>/`
3. Inspect canonical ledger payload:
   - `outputs/demo/<run_id>/ledger/<bundle_sha256>/`

## Replay Verification

Authoritative integrity check:

```powershell
python -m core.determinism.replay outputs/demo/<run_id>/ledger/<bundle_sha256> --strict-manifest
```

Casefile Studio also exposes replay verification at:

- `POST /api/runs/{run_id}/replay-verify`

Run the legal contract extractor:

```powershell
python -m deterministic_ai `
  --domain legal_contract `
  --input-ref sample_contract `
  --input-file data\legal_contract_sample\sample_contract.txt `
  --timestamp 2026-02-28T14:32:00Z `
  --commit-ref e20fbd8 `
  --repo-tag v0.2.0-legal-domain `
  --out outputs\legal_sample
```

## Verify A Provenance Record

```powershell
python scripts\view_provenance.py `
  --verify `
  --record outputs\legal_sample\provenance.json `
  --input data\legal_contract_sample\sample_contract.txt `
  --output outputs\legal_sample\output.json
```

Generate a printable HTML report:

```powershell
python scripts\generate_provenance_report.py `
  --record outputs\legal_sample\provenance.json `
  --out outputs\legal_sample\provenance_report.html
```

## How Determinism Is Enforced

Canonical outputs are written with stable JSON serialization, input fixtures are pinned by SHA-256, and CI runs both the test suite and a double-run reproducibility check. `MANIFEST.sha256` is regenerated from tracked repository bytes and verified for drift during reproducibility checks.

See `docs/DETERMINISM.md` and `docs/NONDETERMINISM_BOUNDARY.md` for the verification model. The biblical text example remains available as a fixture in `docs/examples/biblical_text.md`.
See `docs/CASEFILE.md` for casefile contract details and replay usage.

# iota-verbum-core

IOTA VERBUM CORE is a deterministic extraction and provenance engine for audit-sensitive document workflows. The core promise is that the same committed input, pinned dependencies, and repository state produce the same output bytes and the same verification record.

This repository contains the deterministic core only: domain extractors, schemas, manifests, provenance tools, and reproducibility checks.

## Quickstart

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.lock
python -m pip install -e .
pytest tests/ -v
```

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

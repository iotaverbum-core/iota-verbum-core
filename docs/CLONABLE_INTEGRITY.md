# Clonable Integrity

Clonable integrity means a fresh clone on a different machine can deterministically regenerate a sealed self-casefile ledger and verify it by strict replay, with no hidden local state.

## Prerequisites

- Python 3.11+ available as `python` (Windows) or `python3` (Linux/macOS).
- Dependencies installed:
  - `python -m pip install -U pip`
  - `python -m pip install -r requirements.lock`
  - `python -m pip install -e .`
- Run from repository root.

## One-Command Run

PowerShell:

```powershell
.\scripts\clonable_integrity.ps1
```

Shell:

```bash
scripts/clonable_integrity.sh
```

Default deterministic parameters:

- `created_utc=2026-03-06T10:00:00Z`
- `core_version=0.4.0`
- `ruleset_id=ruleset.core.v1`
- `max_chunks=20`
- `max_events=30`

## Expected Behavior

The runner:

1. verifies required files/folders
2. runs the self-casefile demo against `docs/casefiles/iota_verbum_self`
3. extracts `ledger_dir` from demo output (`ledger_dir:`, `Ledger Dir`, or replay command fallback)
4. runs `python -m core.determinism.replay <ledger_dir> --strict-manifest`
5. prints exactly:

```text
CLONABLE_INTEGRITY_OK
```

Any failure exits non-zero.

After `CLONABLE_INTEGRITY_OK`, inspect the generated casefile via:

- `python -m core.casefile.inspect outputs/demo/<run_id>/casefile.json`
- `docs/proof_trace_viewer.html` (read-only helper)

## What Replay Guarantees

Strict replay verification guarantees reproducibility and provenance integrity of sealed artifacts for the supplied evidence corpus. It does not, by itself, guarantee correctness beyond that evidence. Replay verification is authoritative; viewer pages are read-only inspection helpers.

## Tamper Check

Tamper check verifies deterministic failure on copied artifacts without mutating the original ledger directory.

PowerShell:

```powershell
.\scripts\tamper_casefile.ps1 -LedgerDir outputs/demo/<run_id>/ledger/<bundle_sha256>
```

Shell:

```bash
scripts/tamper_casefile.sh outputs/demo/<run_id>/ledger/<bundle_sha256>
```

Expected result:

```text
TAMPER_DETECTED_OK
```

Implementation detail: tamper scripts copy ledger artifacts to a repo-local temp location (`tmp_tamper`), append one LF byte to copied `output.json`, and replay must fail deterministically.

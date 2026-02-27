# Legacy Audit

## Purpose + Scope

Document the verified state of legacy history availability for this repository and clarify implications for version mapping.

## Current Confirmed State

- Legacy repository/history: Not currently available or present in this git database.
- v2/v3/v4: referenced historically but not recoverable from current materials.
- Implication: `v0.1.0-core` is the canonical baseline until legacy is recovered.

## Evidence (Summarized)

- `git rev-list --count HEAD` returned `5`.
- Earliest commit is `"Initial core split"`.

## What Was Split Into Core (Confirmed)

- Deterministic engine and utilities: `core/` → `src/core/`
- Domain logic: `domains/` → `src/domains/`
- CLI runner: `deterministic_ai.py` → `src/deterministic_ai.py`
- Schemas: `schemas/`
- Minimal sample data: `data/credit`, `data/clinical`, `data/scripture/esv_sample`
- Determinism tests + goldens: `tests/test_deterministic_ai.py`, `tests/test_conscience_core.py`, `tests/golden/{biblical_text,credit_scoring,clinical_records}`

## What Remains in Legacy

Unknown (legacy repository not present here).

## v2/v3/v4 Meaning and Status

Unknown; referenced historically but not recoverable from this repository. Do not claim support until legacy is recovered.

## Risks

- Missing remotes or inaccessible history.
- Ambiguous or missing version markers.
- Incomplete provenance for v2/v3/v4 outputs.

## Proposed Audit Steps

Run in any recovered legacy repo:
```powershell
git branch -a
git log --oneline --decorate --graph --all
git remote -v
Get-ChildItem -Directory
```

## Decisions Needed

- Merge plan for any recovered legacy history (if found).
- Archive plan for deprecated artifacts.
- Official stance on v2/v3/v4 until recovery is complete.

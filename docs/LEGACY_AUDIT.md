# Legacy Audit (Scaffold)

## Purpose + Scope

Document the current state of the legacy repository, identify what is deprecated or missing, and outline the audit steps required to validate historical artifacts and version mappings.

## What Was Split Into Core (Confirmed)

- Deterministic engine and utilities: `core/` → `src/core/`
- Domain logic: `domains/` → `src/domains/`
- CLI runner: `deterministic_ai.py` → `src/deterministic_ai.py`
- Schemas: `schemas/`
- Minimal sample data: `data/credit`, `data/clinical`, `data/scripture/esv_sample`
- Determinism tests + goldens: `tests/test_deterministic_ai.py`, `tests/test_conscience_core.py`, `tests/golden/{biblical_text,credit_scoring,clinical_records}`

## What Remains in Legacy

Unknown until assessed.

## v2/v3/v4 Meaning and Status

Unknown until assessed.

Where to look:
- `tests/golden/v2`, `tests/golden/v3`, `tests/golden/v4` (if present in legacy)
- Historical scripts or docs referencing v2/v3/v4 outputs
- Commit history and tags

## Risks

- Missing remotes or inaccessible history.
- Missing tags or ambiguous version markers.
- Non-deterministic artifacts in legacy outputs.

## Proposed Audit Steps

Run locally in legacy repo:
```powershell
git branch -a
git log --oneline --decorate --graph --all
git remote -v
Get-ChildItem -Directory
```

## Decisions Needed

- Merge plan for legacy PR(s).
- Archive plan for deprecated artifacts.

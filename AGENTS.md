# AGENTS.md

## Scope
These instructions apply to the entire `iota-verbum-core` repository.

## Mission
Maintain deterministic, audit-ready behavior. Favor reproducibility and provenance safety over convenience.

## Environment
- Shell: PowerShell
- Python: 3.11+
- Virtual env path: `.venv`
- Primary OS target: Windows

## Session Bootstrap
Run these at the start of a coding session:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.lock
python -m pip install -e .[dev]
```

If `.venv` already exists, only activate and install missing deps as needed.

## Required Validation Gates
Before marking work complete, run:

```powershell
python -m pytest tests -v
.\scripts\clonable_integrity.ps1
```

If changes touch determinism, manifests, casefile logic, or replay paths, also run strict replay:

```powershell
python -m core.determinism.replay outputs/demo/<run_id>/ledger/<bundle_sha256> --strict-manifest
```

## Determinism Rules
- Do not introduce nondeterministic behavior in core extraction, serialization, manifest, or replay flows.
- Preserve stable ordering and canonical JSON behavior.
- Treat `MANIFEST.sha256` as a controlled artifact; regenerate only when required by the change.
- Do not weaken integrity checks, threshold checks, or attestation logic without explicit instruction.

## File and Change Boundaries
- Prefer editing source, tests, docs, and scripts.
- Avoid manual edits to generated output under `outputs/` unless explicitly requested.
- Do not commit temp/runtime artifacts (`tmp_*`, caches, local journals).
- Keep diffs minimal and focused on the requested task.

## Test and Tooling Conventions
- Use module-invocation style where possible (for example `python -m pytest`).
- Keep lint/test commands deterministic and repository-local.
- When adding tests, prefer explicit fixtures and stable timestamps/hashes.

## Documentation Sync
When behavior changes, update relevant docs in `docs/` and `README.md` in the same task where practical.

## Safety
- Never run destructive commands (for example hard resets or wide deletes) unless explicitly requested.
- If unexpected repo changes appear, stop and ask how to proceed.

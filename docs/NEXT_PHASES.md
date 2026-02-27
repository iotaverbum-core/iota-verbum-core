# Next Phases Plan (Checklist)

This checklist is designed for offline execution and later conversion into GitHub Issues when access is restored.

## Phase 0 — Repo Durability & Release Hygiene

Goal: Ensure the core repo is pushable, tagged, and CI-ready once network/auth is available.

Deliverables:
- [ ] Verify git remote(s) locally (`git remote -v`)
- [ ] Ensure branch is main (`git branch`)
- [ ] Push when network/auth is available (`git push -u origin main`)
- [ ] Tag release v0.1.0-core (`git tag -a v0.1.0-core -m "Core v0.1.0"`)
- [ ] Confirm CI runs on GitHub runners once remote is reachable

Acceptance Criteria (commands/checks):
```powershell
git remote -v
git branch
git push -u origin main
git tag -a v0.1.0-core -m "Core v0.1.0"
git push origin v0.1.0-core
```

Risks:
- Network/auth unavailable for push.
- Tag policy unknown.

## Phase 1 — Core Hardening (Make Determinism Boring)

Goal: Make determinism repeatable across platforms and guard against drift.

Deliverables:
- [ ] Add/confirm determinism contract (`docs/DETERMINISM_CONTRACT.md`)
- [ ] Run determinism checks twice in CI (when available)
- [ ] Add cross-platform guardrails (newline/encoding/path ordering)
- [ ] Add minimal static checks that do not affect outputs (ruff/mypy/pre-commit optional)

Acceptance Criteria (commands/checks):
```powershell
pytest -q
python scripts\determinism_check.py
python scripts\generate_manifest.py --verify
```
```bash
pytest -q
python scripts/determinism_check.py
python scripts/generate_manifest.py --verify
```

Risks:
- Line-ending drift or platform-specific path differences.
- Tooling introduces nondeterminism.

## Phase 2 — Legacy Audit & Version Mapping

Goal: Document legacy status and map versioned artifacts (v2/v3/v4) to support decisions.

Deliverables:
- [ ] Produce `LEGACY_AUDIT.md` (what exists, what is deprecated, what is missing)
- [ ] Map v2/v3/v4 meaning (schema/pipeline/templates) and status (supported/frozen/archived)
- [ ] Update `docs/MIGRATION_NOTES.md` accordingly

Acceptance Criteria (commands/checks):
```powershell
git status -sb
```

Risks:
- Missing remotes or history.
- Ambiguous version markers.

## Phase 3 — API Layer Repo (Thin Wrapper, Core Stays Pure)

Goal: Define a separate API layer plan that preserves core determinism.

Deliverables:
- [ ] Create separate repo plan (iota-verbum-api) (design only in this doc for now)
- [ ] Define endpoints + schemas
- [ ] Define auth (X-API-Key)
- [ ] Define integration test rule: API output must match CLI output byte-for-byte

Acceptance Criteria (commands/checks):
```powershell
python -m deterministic_ai --domain biblical_text --input-ref "John 4:7-10" --dataset esv_sample --context "moment=smoke test" --out outputs\api_parity_check
```

Risks:
- API layer introduces nondeterministic fields.
- Auth and secrets management unclear.

## Phase 4 — Domain Expansion + Governance

Goal: Establish governance for new domains and add one domain with fixtures and goldens when available.

Deliverables:
- [ ] Domain onboarding template
- [ ] Schema registry/versioning rules
- [ ] Provenance policy
- [ ] Add at least one new domain with fixtures + goldens (if available)

Acceptance Criteria (commands/checks):
```powershell
pytest -q
python scripts\determinism_check.py
```
```bash
pytest -q
python scripts/determinism_check.py
```

Risks:
- Domain scope creep or large data leakage into core.
- Missing schema versioning decisions.

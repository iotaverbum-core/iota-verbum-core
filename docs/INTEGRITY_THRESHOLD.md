# Integrity Threshold

Clonable integrity is the minimum release threshold for trustable scaling.

## Why This Matters

- Independent developers must be able to reproduce the same sealed outputs from the same evidence.
- Provenance must be replay-verifiable under strict manifest checks.
- Tampering must be detectable with deterministic failure.

## Conditions Required for the Claim

- Deterministic inputs and fixed defaults (including `created_utc`) are used.
- Canonical serialization is preserved.
- Serialized outputs remain repo-relative (no absolute path leakage).
- Strict replay verification returns success on untampered artifacts.
- Deterministic tamper checks return failure on copied-and-modified artifacts.

## Foundation for Scaling

Without clonable integrity, larger deployments only scale uncertainty. With it, teams can scale audits, CI gates, and cross-machine trust verification on the same deterministic contract.

# Determinism Contract

Same input => byte-identical output.  
Input includes: input file bytes, manifests, templates, core source files, and pinned dependencies.  
Output includes: `output.json`, `provenance.json`, `attestation.sha256`, and any declared artifacts in the pipeline output directory.

## Invariants

- Canonical JSON ordering and whitespace:
  - JSON keys must be sorted.
  - Indentation and trailing newline must be stable and consistent with `core.attestation.canonicalize_json`.
- UTF-8 encoding boundaries:
  - All text inputs/outputs are interpreted and written as UTF-8.
  - No implicit encoding conversion or platform-specific defaults.
- Stable newline policy:
  - Outputs must use LF (`\n`) line endings.
  - Input normalization must convert CRLF/CR to LF before hashing or rendering.
- Stable file ordering:
  - Any file discovery must use deterministic ordering (sorted by normalized path).
  - Globs must be sorted before use; no reliance on filesystem iteration order.
- Forbidden nondeterminism in outputs/provenance:
  - No timestamps, random UUIDs, temp directory paths, machine-specific absolute paths, locale or timezone-dependent values.
  - No environment-dependent defaults in output/provenance.
- Floating-point formatting:
  - If floats appear in outputs, formatting must be explicit and stable (fixed precision and locale-invariant).
- Deterministic template rendering:
  - Template selection must use a deterministic fallback chain.
  - Placeholder resolution must be deterministic with explicit missing markers.

## Forbidden Sources of Nondeterminism

- `datetime.now()` or any wall-clock time used in outputs or provenance.
- `uuid.uuid4()` or any randomness without a fixed seed.
- OS-specific path serialization in outputs (must be repo-relative with `/` separators).
- Locale- or timezone-sensitive formatting.
- Unordered iteration over dicts, sets, or filesystem directories.

## Provenance Rules

Included:
- Input file hash (`input_sha256`), extraction hash, template hash, output hash.
- Manifest hash when input is manifest-resolved.
- Generator hash (`generator_sha256`) for the producing module.

Excluded:
- Absolute paths, machine identifiers, timestamps, or environment variables.
- Any values not strictly derived from inputs and deterministic code.

Hashing and Attestation:
- SHA-256 is mandatory for all attested artifacts.
- `attestation.sha256` must match the canonical JSON bytes written to `output.json`.
- `MANIFEST.sha256` must reflect the exact core sources, templates, schemas, tests, and scripts.

## Test Gates

- Golden snapshots:
  - `pytest -q` must pass and goldens must match exactly.
- Determinism check:
  - `python scripts/determinism_check.py` must pass (double-run + byte-compare).
- Reproducibility verification:
  - `scripts/verify_reproducibility.ps1` and `.sh` must pass when run in a clean environment.
- Manifest integrity:
  - `python scripts/generate_manifest.py --verify` must pass with no drift.

## Change Control

Any change that modifies canonicalization, manifest semantics, templates, or provenance schema must:
- Bump a version marker (schema or output version field as applicable).
- Update golden snapshots intentionally.
- Regenerate `MANIFEST.sha256` and re-verify reproducibility.

## Determinism Review Checklist

- [ ] All outputs are produced via canonical JSON with stable whitespace.
- [ ] UTF-8 encoding is enforced on all reads/writes.
- [ ] Newlines are normalized to LF before hashing.
- [ ] Any file discovery is sorted deterministically.
- [ ] No timestamps, UUIDs, or random values appear in outputs/provenance.
- [ ] No absolute or machine-specific paths appear in outputs/provenance.
- [ ] Locale/timezone-dependent formatting is not used.
- [ ] Template selection uses deterministic fallback order.
- [ ] Placeholder rendering is deterministic and uses explicit missing markers.
- [ ] Floating-point formatting is explicit and stable (if floats exist).
- [ ] `pytest -q` passes with goldens unchanged.
- [ ] `python scripts/determinism_check.py` passes.
- [ ] `python scripts/generate_manifest.py --verify` passes.
- [ ] Repro scripts pass from a clean environment.

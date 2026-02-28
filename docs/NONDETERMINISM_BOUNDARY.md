# Nondeterminism Boundary

## Deterministic Components

The following components are intended to be byte-identical when inputs, pinned dependencies, and repository state are identical:

- `src/core/`, including canonical JSON serialization in `src/core/attestation.py`
- `src/deterministic_ai.py`
- All committed domain extractors in `src/domains/`
- Template loading in `src/core/templates.py`
- All committed schemas in `schemas/`
- Determinism and manifest scripts in `scripts/`
- Provenance presentation scripts in `scripts/view_provenance.py` and `scripts/generate_provenance_report.py`
- Golden tests and deterministic fixtures in `tests/` and `data/`

## Nondeterministic Components

No active nondeterministic execution path is part of the canonical pipeline today. The repository still defines these as out of bounds for canonical artifact generation:

- LLM inference:
  nondeterminism source is provider-side model drift, sampling, and prompt routing.
  containment is strict isolation from canonical artifact paths until output is converted into a stable input and deterministically validated.
- External API calls:
  nondeterminism source is remote state, retries, rate limits, and service changes.
  containment is prohibition in canonical generation unless the response is first captured as an explicit versioned input.
- Randomness and UUID generation:
  nondeterminism source is pseudo-random state.
  containment is a blanket ban in canonical generation unless a caller-supplied seed is part of the explicit input contract.
- Runtime clocks:
  nondeterminism source is current wall-clock time.
  containment is requiring timestamps to be passed by the caller and stored only as explicit provenance metadata.

## Isolation Contract

Nondeterministic components must never write directly to canonical artifact paths such as `output.json`, `provenance.json`, `attestation.sha256`, `MANIFEST.sha256`, or committed golden snapshots. Any future nondeterministic layer must emit non-canonical intermediate data, then pass through deterministic validation before it can influence a canonical artifact or provenance record.

## Verification Instructions

1. Run `pytest tests/ -v` and confirm all domain and provenance tests pass.
2. Run `python scripts/determinism_check.py` and confirm all configured cases match byte-for-byte across two consecutive runs.
3. Run `python scripts/generate_manifest.py --verify` and confirm the root manifest is current.
4. Run `python scripts/view_provenance.py --verify --record <provenance.json> --input <source-file> --output <output.json>` and confirm it exits successfully.
5. Review `src/deterministic_ai.py`, `src/core/pipeline.py`, and domain extractors for direct use of `random`, `uuid`, network clients, or runtime-generated timestamps in canonical outputs.

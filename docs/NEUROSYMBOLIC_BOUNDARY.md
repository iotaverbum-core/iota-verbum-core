# NEUROSYMBOLIC_BOUNDARY.md
# IOTA VERBUM CORE — Neurosymbolic Architecture Boundary
Version: 1.0 · Date: February 2026
Status: Canonical — governed by MANIFEST.sha256

## Overview

IOTA VERBUM CORE is a neurosymbolic hybrid system with an explicit boundary
between its deterministic symbolic layer and its probabilistic neural layer.

## Symbolic Layer (fully deterministic, currently active)

Components: legal_contract extractor, nda extractor, provenance record
generator, manifest generator, schema validators, governance metadata mapper.

Guarantees: byte-identical outputs, independently verifiable provenance,
traceable reasoning, formal constraint satisfaction.

## Neural Layer (architecturally supported, inactive until v0.3.x)

Planned: LLM clause classifier, context-aware entity resolver,
multi-language semantic normaliser.

Not permitted: write to canonical output paths, override symbolic results
without validation, generate provenance records, modify governance metadata.

## Integration Layer — The Provenance Record

Every output includes a neurosymbolic_boundary block recording which
components ran on each side of the boundary. This makes the boundary
auditable at the record level.

## Verification

python scripts/determinism_check.py         # symbolic layer determinism
python scripts/generate_manifest.py --verify  # boundary document is sealed

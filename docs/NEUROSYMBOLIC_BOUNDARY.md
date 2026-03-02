# NEUROSYMBOLIC_BOUNDARY.md
# IOTA VERBUM CORE - Neurosymbolic Architecture Boundary
Version: 1.1 - Date: March 2, 2026
Status: Canonical - governed by MANIFEST.sha256

## Overview

IOTA VERBUM CORE is a neurosymbolic hybrid system with an explicit boundary between its deterministic symbolic layer and any probabilistic neural layer.

## Active Boundary for v0.3.0-production

The active runtime boundary is `symbolic_only`.
This applies to text ingestion, PDF extraction routing, language detection, and clause extraction.
Language detection uses fixed-library scoring with deterministic tie-breaking rules.
Clause extraction remains rule-based and independently verifiable.

## Symbolic Layer

Components: legal contract extractor, multilingual NDA extractors, PDF text cleaning, provenance storage, verification, audit logging, governance metadata mapping, and schema validation.

Guarantees: byte-identical extraction results for the same clean text, independently verifiable provenance, traceable rule identifiers, deterministic health reporting, and explicit failure modes.

## Neural Layer

The codebase may later host isolated experimental neural components, but they are inactive in the extraction path for `v0.3.0-production`.
Neural components may not write canonical outputs, provenance records, or governance metadata.
Neural components may not override symbolic extraction results.

## Record-Level Boundary

Every provenance record stores `neurosymbolic_boundary: symbolic_only`.
`/health` is the source of truth for the currently active boundary and must remain aligned with runtime behavior.

## Verification

`GET /v1/verify/{record_id}` recomputes the SHA-256 hash from stored clean text and compares it with the stored provenance hash.

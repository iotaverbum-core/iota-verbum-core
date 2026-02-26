# Architecture

## Core Boundaries

This repo contains the minimal deterministic engine and schemas required to produce reproducible, auditable outputs.

Included:
- `src/core/`: deterministic primitives (attestation, manifest resolution, pipeline, extraction, templates, conscience).
- `src/domains/`: domain extractors + deterministic templates for biblical_text, credit_scoring, clinical_records.
- `src/deterministic_ai.py`: CLI runner and provenance validation.
- `schemas/`: JSON schemas used by attestations.
- `data/credit`, `data/clinical`, `data/scripture/esv_sample`: minimal sample inputs + manifests for tests.
- `tests/`: determinism and conscience tests with golden snapshots.

Excluded (legacy-only): apps, UI, demos, notebooks, corpora, large data bundles, and build artifacts.

## Module Map

- `core.attestation`: canonical JSON serialization, SHA-256, provenance/attestation helpers.
- `core.manifest`: manifest loading + input resolution with hash verification.
- `core.pipeline`: deterministic pipeline orchestration.
- `core.extraction`: stable text normalization and extraction utilities.
- `core.templates`: deterministic template resolution and placeholder rendering.
- `core.conscience.*`: deterministic ground-truth + LLM constraint/validation wrapper.
- `domains.*.extractors`: domain-specific deterministic extractors + rendering.

## Data Flow (Deterministic Pipeline)

1. Input resolved from manifest or explicit file.
2. Text normalization + extraction.
3. Deterministic template render.
4. Output + provenance emitted and SHA-256 attested.

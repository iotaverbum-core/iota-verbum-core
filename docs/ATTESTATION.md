# Attestation

## Hashing Approach

- Output JSON is canonicalized (sorted keys, stable encoding) before hashing.
- SHA-256 is computed over canonical bytes.
- Provenance includes hashes for input, extraction, template, and output.

## Artifacts

Primary artifacts per run:
- `output.json`
- `provenance.json`
- `attestation.sha256`

The provenance object records:
- input file hash
- extraction hash
- template hash
- generator hash (source file checksum)
- output hash

## Manifests

`MANIFEST.sha256` records SHA-256 hashes of key source files, schemas, tests, scripts, and manifests.
This enables machine-verifiable attestation that the core engine and its artifacts are unchanged.

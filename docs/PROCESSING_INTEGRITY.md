# Processing Integrity - IOTA VERBUM CORE

## Determinism Contract
Every analysis of the same input document using the same domain, language rule set, and engine version produces byte-for-byte identical extraction output.
The symbolic extraction layer remains the only active extraction path.
The `determinism_contract` field in `/health` reports `active`.

## Neurosymbolic Boundary
The `neurosymbolic_boundary` field in every provenance record records the active boundary state at extraction time.
For `v0.3.0-production` the active boundary is `symbolic_only`.
No generative model is present in the extraction path.

## Hash Verification
Every provenance record contains a SHA-256 hash of the clean extracted document text.
Verification recomputes the hash from the stored sensitive text in `document_inputs` and compares it to the stored provenance hash through `GET /v1/verify/{record_id}`.

## Error Handling
If the symbolic extraction engine cannot process an input, the API returns an explicit error.
The service does not return partial generated output.

## Audit Trail
Analysis requests write both provenance and audit events before the API response is returned.
Verification requests append a verification event to the provenance audit trail and write read events to the system audit log.


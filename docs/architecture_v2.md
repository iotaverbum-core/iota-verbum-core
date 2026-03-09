# Architecture V2: Deterministic Narrative Intelligence Graph Core

## Current-state summary
The repository already had deterministic canonical JSON, attestation, world modeling, verification, and ledger replay primitives. V2 layers a graph-centered analytic stack on top of those primitives.

## V2 module map
1. Semantic extraction: `core.semantic`
2. Canonical world graph: `core.world`
3. Identity engine: `core.identity`
4. Competing hypotheses: `core.hypothesis`
5. Narrative coherence: `core.narrative`
6. Contradictions: `core.contradiction`
7. Adjudication: `core.adjudication`
8. Verification: `core.verification`
9. Deterministic ledger sealing: `core.ledger`
10. World diff: `core.diff`
11. Explainability renderer: `core.explainability`
12. End-to-end orchestrator: `core.engine.v2_pipeline`

## Deterministic operating principles
- All stage outputs are sorted and schema-validated.
- All stage payloads are canonical-JSON hashable.
- Ledger stage hashes include all reasoning outputs.
- Unknowns are explicit and preserved into verification/adjudication.

# Full Specification Report

## Scope and Source of Truth

This report consolidates the canonical specifications currently implemented in `iota-verbum-core` for:

- End-to-end deterministic pipeline
- Roadmap status (Phase 1 / Phase 2 and adjacent phases)
- Casefile v1 output contract and required fields
- Ledger and replay verification requirements

Authoritative sources include:

- `docs/ARCHITECTURE.md`
- `docs/NEXT_PHASES.md`
- `docs/CASEFILE.md`
- `src/proposal/cli_demo.py`
- `src/proposal/evidence_pack.py`
- `src/proposal/claim_propose.py`
- `src/proposal/world_propose.py`
- `src/core/reasoning/run_graph.py`
- `src/core/reasoning/casefile.py`
- `src/core/determinism/replay.py`
- `schemas/*.schema.json` (listed in relevant sections)

## 1) Architecture Diagram (Full Pipeline)

Requested pipeline:

`EvidencePack -> Claim Proposer -> Claim Graph -> Graph Reasoning -> World Model -> Narrative Renderer -> Ledger + Attestation -> Replay Verification`

Implementation mapping:

1. EvidencePack
   - Build: `proposal.evidence_pack.build_evidence_pack`
   - Schema: `schemas/evidence_pack.schema.json`
   - Output: `evidence_pack.json`

2. Claim Proposer
   - Build: `proposal.claim_propose.propose_claim_graph`
   - Input: `EvidencePack`
   - Produces claim candidates from normalized heading/bullet structure with deterministic IDs and ordered evidence refs.

3. Claim Graph
   - Schema: `schemas/claim_graph.schema.json`
   - Output: `claim_graph.json` (non-world mode in `cli_demo`)
   - Contains: `graph_version`, `claims[]`, `edges[]`.

4. Graph Reasoning
   - Build path: `core.reasoning.run_graph.build_graph_reasoning_output`
   - Components:
     - `build_claim_graph`
     - `find_duplicates_and_contradictions`
     - `compute_closure`
     - optional `build_support_tree` + narrative rendering
   - Outputs include reasoning findings, closure, support tree, and narrative objects.

5. World Model
   - Build: `proposal.world_propose.propose_world_model_from_artifacts` (world mode path in `cli_demo`)
   - Schema: `schemas/world_model.schema.json`
   - Output: `world_model.json`
   - Contains deterministic `entities`, `events`, `relations`, `unknowns`, `conflicts`, and `world_sha256`.

6. Narrative Renderer
   - Narrative outputs generated in world mode:
     - `world_narrative`, `world_narrative_v2`
     - `causal_narrative_v2`
     - `critical_path_narrative_v2`
     - `constraint_narrative_v2`
     - `repair_hints_narrative_v2`
   - Schemas include:
     - `schemas/world_narrative_v2.schema.json`
     - `schemas/causal_narrative_v2.schema.json`
     - `schemas/critical_path_narrative_v2.schema.json`
     - `schemas/constraint_narrative_v2.schema.json`
     - `schemas/repair_hints_narrative_v2.schema.json`

7. Ledger + Attestation
   - Finalization: `core.determinism.finalize.finalize`
   - Ledger write: `core.determinism.ledger.write_run`
   - Attestation schema: `schemas/attestation_record.schema.json`
   - Expected sealed artifacts in run context:
     - `sealed_output.json` (or ledger `output.json`)
     - `attestation.json`
     - `evidence_bundle.json` (or ledger `bundle.json`)
     - `casefile.json` (world mode)
     - `ledger/<bundle_sha256>/...`

8. Replay Verification
   - Verifier: `core.determinism.replay.verify_run`
   - Command: `python -m core.determinism.replay <ledger_dir> --strict-manifest`
   - Checks:
     - Ledger dir name equals computed `bundle_sha256`
     - `attestation.bundle_sha256 == sha256(bundle.json)`
     - `attestation.output_sha256 == sha256(output.json)`
     - Strict mode requires `attestation.manifest_sha256 == sha256(MANIFEST.sha256)`

## 2) Data Contracts by Stage

### 2.1 EvidencePack Contract

Schema: `schemas/evidence_pack.schema.json`

Top-level required fields:

- `pack_version` (const `1.0`)
- `root_hint`
- `documents[]`
- `chunks[]`
- `pack_sha256`

Important nested required fields:

- `documents[]`: `doc_id`, `relpath`, `sha256`, `bytes`
- `chunks[]`: `doc_id`, `chunk_id`, `index`, `offset_start`, `offset_end`, `text`, `text_sha256`

Determinism notes:

- Input files discovered in stable sorted order by relative path.
- Text normalized before hashing/chunking.
- `pack_sha256` computed from canonical JSON with self-hash field blanked prior to digest.

### 2.2 Claim Graph Contract

Schema: `schemas/claim_graph.schema.json`

Top-level required fields:

- `graph_version`
- `claims[]`
- `edges[]`

Claim required fields:

- `claim_id`, `subject`, `predicate`, `object`, `polarity`, `modality`, `qualifiers`, `evidence`

Edge required fields:

- `from_id`, `to_id`, `type` where `type` in:
  - `supports`
  - `contradicts`
  - `implies`
  - `depends_on`

### 2.3 World Model Contract

Schema: `schemas/world_model.schema.json`

Top-level required fields:

- `world_version` (const `1.0`)
- `world_sha256`
- `entities[]`
- `events[]`
- `relations[]`
- `unknowns[]`
- `conflicts[]`

Key enums and shapes:

- Entity `type`: `Person | Org | System | Secret | Policy | Service | Concept`
- Event `type`: `Config | Access | Leak | Rotation | Deployment | PolicyChange | Other`
- Time forms:
  - `{"kind":"instant","value":"YYYY-MM-DDTHH:MM:SSZ"}`
  - `{"kind":"date","value":"YYYY-MM-DD"}`
  - `{"kind":"unknown"}`

### 2.4 Verification Result Contract

Schema: `schemas/verification_result.schema.json`

Top-level required fields:

- `verification_version` (const `1.0`)
- `ruleset_id`
- `target_claim_id`
- `status`
- `reasons[]`
- `required_info[]`
- `receipts`

`status` enum:

- `VERIFIED_OK`
- `VERIFIED_FAIL`
- `VERIFIED_NEEDS_INFO`

Receipts required fields:

- `bundle_sha256`
- `output_sha256`
- `attestation_sha256`
- `ruleset_sha256`
- `evidence_refs[]`
- `proofs[]`
- `findings[]`

### 2.5 Casefile v1 Contract (Expected Output Contract Fields)

Schema: `schemas/casefile.schema.json`
Spec doc: `docs/CASEFILE.md`

Top-level required fields:

- `casefile_version` (const `1.0`)
- `casefile_id` (pattern `case:<64-hex>`)
- `created_utc` (UTC second precision)
- `core_version`
- `ruleset_id`
- `query`
- `prompt`
- `hashes`
- `ledger_dir`
- `summary`
- `artifacts[]`
- `receipts_summary`

`hashes` required fields:

- `manifest_sha256`
- `bundle_sha256`
- `world_sha256`
- `output_sha256`
- `attestation_sha256`

`summary` required fields:

- `entities`
- `events`
- `unknowns`
- `conflicts`
- `verification_status`
- `constraint_violations`
- `causal_edges`

`receipts_summary` required fields:

- `evidence_ref_count`
- `proof_count`
- `finding_count`

Artifact contract (`artifacts[]`):

- required: `name`, `role`, `sha256`
- optional: `schema`, `notes`
- role enum: `sealed | derived | narrative`

Casefile hashing behavior:

- `casefile_id` and `casefile.json` artifact SHA are computed with cycle-safe preimages.
- `output_sha256`, `attestation_sha256`, and selected artifact hashes are temporarily zeroed during specific preimage steps to avoid sealing cycles.

## 3) Output Artifact Layout Contract

In world mode (`proposal.cli_demo`), run directory includes:

- `evidence_pack.json`
- `evidence_bundle.json`
- `world_model.json`
- `sealed_output.json`
- `attestation.json`
- `casefile.json`
- `ledger/<bundle_sha256>/` containing canonical replay artifacts (`bundle.json`, `output.json`, `attestation.json`)

This aligns with `docs/CASEFILE.md` and replay expectations.

## 4) Replay Verification Contract

Command:

`python -m core.determinism.replay outputs/demo/<run_id>/ledger/<bundle_sha256> --strict-manifest`

Strict-manifest pass criteria:

1. `sha256(bundle.json)` equals ledger directory name.
2. Attestation validates against `schemas/attestation_record.schema.json`.
3. Attested `bundle_sha256` equals computed bundle hash.
4. Attested `output_sha256` equals computed output hash.
5. Attested `manifest_sha256` equals hash of repository `MANIFEST.sha256`.

Failure on any criterion returns non-zero and must be treated as integrity failure.

## 5) Roadmap Status (From Current Checklist)

Source: `docs/NEXT_PHASES.md`

Current checklist state (as documented):

- Phase 0: all checklist items currently unchecked.
- Phase 1 (Core Hardening): all checklist items currently unchecked.
- Phase 2 (Legacy Audit & Version Mapping): all checklist items currently unchecked.
- Phase 3 (API Layer Repo): all checklist items currently unchecked.
- Phase 4 (Domain Expansion + Governance): all checklist items currently unchecked.

Interpretation:

- The roadmap document is a planned execution checklist, not a completion record.
- No checked boxes currently indicate completed acceptance in that file snapshot.

## 6) Determinism and Audit Constraints

From `docs/CASEFILE.md`, `docs/ARCHITECTURE.md`, and implementation:

- Canonical JSON serialization is required for deterministic hashes.
- Stable ordering is applied to files, chunks, artifacts, and relation-like collections.
- No wall-clock timestamp insertion into canonical outputs.
- Replay verification is authoritative for ledger integrity.
- `MANIFEST.sha256` binding is part of strict provenance verification.

## 7) Clarification on Requested Diagram Labels

The exact wording:

`EvidencePack -> Claim Proposer -> Claim Graph -> Graph Reasoning -> World Model -> Narrative Renderer -> Ledger + Attestation -> Replay Verification`

is not stored verbatim in one existing doc. This report maps that wording directly onto implemented modules and schema contracts to provide an executable specification.

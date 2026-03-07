# Casefile Studio Architecture

## Purpose

Casefile Studio is the production demo surface for `iota-verbum-core`.
It is casefile-first and keeps the deterministic core as the authoritative execution path.

## Runtime Topology

1. FastAPI backend (`src/iota_verbum_api/app.py`)
2. Casefile Studio router/service (`src/iota_verbum_api/casefile_studio.py`)
3. Static frontend (`src/iota_verbum_api/static/casefile_studio/*`)
4. Deterministic core pipeline modules (`proposal.*`, `core.*`)

## Authoritative Pipeline Mapping

- EvidencePack: `proposal.evidence_pack.build_evidence_pack`
- Claim Proposer: `proposal.claim_propose.propose_claim_graph`
- Claim Graph: `schemas/claim_graph.schema.json`
- Graph Reasoning: `core.reasoning.run_graph.build_graph_reasoning_output`
- World Model: `proposal.world_propose.propose_world_model_from_artifacts`
- Narrative Renderer: `core.reasoning.*narrative*`
- Ledger + Attestation: `core.determinism.finalize.finalize` + `core.determinism.ledger.write_run`
- Replay Verification: `core.determinism.replay.verify_run`

## API Surface

- `GET /api/health`
- `GET /api/fixtures`
- `POST /api/runs/sample`
- `POST /api/runs/upload`
- `GET /api/runs/{run_request_id}` (progress/status)
- `GET /api/runs/{run_id}/summary`
- `GET /api/runs/{run_id}/timeline`
- `GET /api/runs/{run_id}/contradictions`
- `GET /api/runs/{run_id}/unknowns`
- `GET /api/runs/{run_id}/receipts`
- `GET /api/runs/{run_id}/artifacts`
- `GET /api/runs/{run_id}/artifacts/{artifact_name}`
- `POST /api/runs/{run_id}/replay-verify`

## Determinism Guarantees

- Case generation uses `run_demo(..., world=True)` and existing canonical serialization/hashing.
- UI data slices are derived from generated artifacts (`casefile.json`, `sealed_output.json`, ledger files).
- Deterministic sort keys are applied for surfaced timeline/receipts/conflict/unknown lists.
- Replay verification is unchanged and remains authoritative.

## Frontend UX Composition

- Landing: value proposition + trust story + primary CTAs
- Fixture Gallery: 3 curated deterministic dossiers
- Run Progress: real backend stage updates
- Workspace:
  - verified timeline
  - contradictions
  - unknowns
  - findings/narratives
  - receipts
  - artifacts
  - integrity/replay panel

## Security and Access

- Casefile Studio routes (`/`, `/studio`, `/api/*`) are public demo routes.
- Existing authenticated API surface remains available for tenant-scoped operations.

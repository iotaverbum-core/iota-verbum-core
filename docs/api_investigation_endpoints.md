# Investigation API Endpoints

All endpoints are served by `casefile_studio` and read deterministic artifacts.

- `GET /api/runs`
- `GET /api/runs/{run_id}/overview`
- `GET /api/runs/{run_id}/graph`
- `GET /api/runs/{run_id}/nodes/{node_id}`
- `GET /api/runs/{run_id}/timeline`
- `GET /api/runs/{run_id}/hypotheses`
- `GET /api/runs/{run_id}/evidence`
- `GET /api/runs/{run_id}/narrative`
- `GET /api/runs/{run_id}/diff?against_run_id=...`

Existing endpoints for receipts/artifacts/replay remain available.

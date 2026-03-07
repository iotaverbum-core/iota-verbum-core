# Railway Runbook: Casefile Studio

## Goal

Deploy the Casefile Studio demo so `/` serves the production demo UX and `/api/*` serves backend casefile endpoints.

## Service Configuration

1. Create Railway service from this repository.
2. Attach PostgreSQL plugin (recommended for existing API features).
3. Use repository `Dockerfile` build.

## Environment Variables

Set:

- `DATABASE_URL` from Railway PostgreSQL plugin
- `API_KEYS` (for existing authenticated API routes)
- `RATE_LIMIT_PER_MINUTE=60`
- `RETENTION_DAYS_DOCUMENT_INPUT=90`
- `RETENTION_DAYS_PROVENANCE_RECORD=2555`
- `RETENTION_DAYS_AUDIT_LOG=2555`

## Start Command

Default container command:

`uvicorn main:app --host 0.0.0.0 --port 8000`

## Healthcheck

Use:

- `/health` (platform service health)
- `/api/health` (Casefile Studio surface health)

## Smoke Test Sequence

1. Open `/` and confirm landing UI loads.
2. `GET /api/fixtures` returns at least 3 fixtures.
3. Start a sample run using `POST /api/runs/sample` with fixture `timeline_breach_chain`.
4. Poll `/api/runs/{run_request_id}` until `completed`.
5. Confirm workspace endpoints return data:
   - `/api/runs/{run_id}/summary`
   - `/api/runs/{run_id}/timeline`
   - `/api/runs/{run_id}/contradictions`
   - `/api/runs/{run_id}/unknowns`
   - `/api/runs/{run_id}/receipts`
6. Run replay verification:
   - `POST /api/runs/{run_id}/replay-verify`
   - Expect `status=VERIFIED_OK`.

## Incident Triage

1. If run creation fails:
   - Inspect `/api/runs/{run_request_id}` error/traceback.
   - Check fixture folder paths and output directory permissions.

2. If replay fails:
   - Compare `ledger_dir` and hashes in casefile summary.
   - Run terminal replay manually:
     - `python -m core.determinism.replay <ledger_dir> --strict-manifest`

3. If static UI fails:
   - Verify `/studio/assets/styles.css` and `/studio/assets/app.js` are reachable.
   - Confirm package data includes static files in deployment build.

## Rollback

Deploy previous known-good image revision in Railway.

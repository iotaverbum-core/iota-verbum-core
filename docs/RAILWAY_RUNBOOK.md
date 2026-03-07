# Railway Runbook: Casefile Studio

## Service Setup

1. Create a Railway service from this repo using the `Dockerfile`.
2. Set env vars:
   - `DATABASE_URL`
   - `API_KEYS`
3. Start command:
   - `uvicorn iota_verbum_api.app:app --host 0.0.0.0 --port 8000`

## Healthchecks

- `/health`
- `/api/health`

## Smoke Test

1. Open `/` and click `Open Sample Case`.
2. Run fixture `secret_state_conflict`.
3. Confirm:
   - timeline populated
   - contradictions populated
   - integrity hashes visible
   - receipts visible
4. Run replay (`Run Replay Verification`) and confirm `VERIFIED_OK`.

## Failure Triage

- Run failed: inspect `GET /api/runs/{run_request_id}` for `error`.
- Replay failed: run `python -m core.determinism.replay <ledger_dir> --strict-manifest`.
- Static failed: verify `/studio/assets/styles.css` and `/studio/assets/app.js` are reachable.

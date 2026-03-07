# Deploy Demo App

## Local

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.lock
python -m pip install -e .[dev]
uvicorn iota_verbum_api.app:app --host 0.0.0.0 --port 8000
```

App URL: `http://localhost:8000/`

## Container

```powershell
docker build -t iota-verbum-core-demo .
docker run --rm -p 8000:8000 iota-verbum-core-demo
```

## Environment

- `DATABASE_URL` (set to Railway/Postgres in production)
- `API_KEYS` (required for authenticated legacy `/v1/*` routes)

## Deploy Validation

1. `GET /health`
2. `GET /api/health`
3. `GET /api/fixtures`
4. `POST /api/runs/sample` with `{"fixture_id":"secret_state_conflict"}`
5. Poll `GET /api/runs/{run_request_id}` until `status=completed`
6. `POST /api/runs/{run_id}/replay-verify` and expect `VERIFIED_OK`

## Determinism Gates

```powershell
python -m pytest tests -v
.\scripts\clonable_integrity.ps1
python -m core.determinism.replay outputs/demo/<run_id>/ledger/<bundle_sha256> --strict-manifest
```

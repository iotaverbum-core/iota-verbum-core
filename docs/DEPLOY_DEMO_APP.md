# Deploy Demo App

## Local Run

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.lock
python -m pip install -e .[dev]
uvicorn iota_verbum_api.app:app --host 0.0.0.0 --port 8000
```

Open:

- `http://localhost:8000/` (Casefile Studio)

## Docker Run

```powershell
docker build -t iota-verbum-core-demo .
docker run --rm -p 8000:8000 iota-verbum-core-demo
```

## Required Environment Variables

Minimum:

- `DATABASE_URL` (defaults to local SQLite when unset)
- `API_KEYS` (defaults to demo key map when unset)

Recommended for production:

- `DATABASE_URL`
- `API_KEYS`
- `RATE_LIMIT_PER_MINUTE`
- `RETENTION_DAYS_DOCUMENT_INPUT`
- `RETENTION_DAYS_PROVENANCE_RECORD`
- `RETENTION_DAYS_AUDIT_LOG`

## Post-Deploy Validation

1. `GET /health`
2. `GET /api/health`
3. `GET /api/fixtures`
4. Start sample run via `POST /api/runs/sample`
5. Poll `GET /api/runs/{run_request_id}` to `completed`
6. Verify replay via `POST /api/runs/{run_id}/replay-verify`

## Determinism Validation Gates

Before release:

```powershell
python -m pytest tests -v
.\scripts\clonable_integrity.ps1
```

If determinism-related paths were changed:

```powershell
python -m core.determinism.replay outputs/demo/<run_id>/ledger/<bundle_sha256> --strict-manifest
```

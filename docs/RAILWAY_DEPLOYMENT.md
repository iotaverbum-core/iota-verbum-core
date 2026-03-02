# Railway Deployment - v0.3.0-production

## Services

1. Add a PostgreSQL plugin to the Railway project.
2. Confirm the service exposes `DATABASE_URL` to the API service.
3. Deploy the API service from this repository with the included `Dockerfile`.

## Required Environment Variables

```env
DATABASE_URL=postgresql://user:password@host:5432/iotaverbum
API_KEYS=primary-key:tenant-primary,secondary-key:tenant-secondary
RETENTION_DAYS_DOCUMENT_INPUT=90
RETENTION_DAYS_PROVENANCE_RECORD=2555
RETENTION_DAYS_AUDIT_LOG=2555
RATE_LIMIT_PER_MINUTE=60
```

## Startup Sequence

1. Railway starts the container.
2. The application runs schema setup before accepting traffic.
3. Startup audit events are written.
4. The retention scheduler is started.
5. Uvicorn serves the FastAPI app.

## Verification Checklist

- `GET /health` returns `version: v0.3.0-production`
- `GET /health` returns `storage: postgresql`
- `GET /health` returns `pdf_parsing: active`
- `GET /health` returns `neurosymbolic_boundary: symbolic_only`
- `GET /v1/status` returns component status and uptime
- `POST /v1/analyse` succeeds for JSON text input
- `POST /v1/analyse` succeeds for PDF multipart input
- `GET /v1/verify/{record_id}` returns `hash_match: true`
- `GET /v1/audit` returns only tenant-scoped events

## Railway Notes

- Keep `API_KEYS` and `DATABASE_URL` in Railway environment configuration only.
- Use the Railway PostgreSQL plugin for this sprint rather than an external provider.
- If OCR is required in production, verify the container image includes Tesseract language packs and `poppler-utils`.

# Access Control Policy - IOTA VERBUM CORE

## API Authentication
All API endpoints except `/health`, `/v1/status`, and `/v1/demo` require a valid API key passed as the `X-API-Key` header.
API keys are scoped to a tenant. A key can only access that tenant's data.

## API Key Storage
API keys are stored as `KEY_NAME:TENANT_ID` pairs in the `API_KEYS` environment variable.
Keys are never stored in source code or committed to version control.
Keys are hashed with SHA-256 before they are written to the audit log.

## Tenant Isolation
The system enforces tenant isolation at the data layer.
A tenant cannot query provenance records belonging to another tenant.
A tenant cannot query audit logs belonging to another tenant.
This is enforced in SQL queries by filtering on `tenant_id`.

## Environment Variables Containing Secrets
- `API_KEYS`: Contains API keys. Railway environment only. Never in source.
- `DATABASE_URL`: Contains database credentials. Railway environment only.

## Principle of Least Privilege
The runtime application account is intended to use `SELECT` and `INSERT` on `audit_log` and `document_inputs`.
`provenance_records` verification state requires mutation support in the current implementation because `verified_count` and the embedded record audit trail are stored on the record row.
DDL operations are performed only during migration.


# Incident Timeline: API Token Exposure

- 2026-02-01 Security rotated `PROD_API_TOKEN` after vendor alert.
- 2026-02-03 Deployment promoted checkout service config using `PROD_API_TOKEN`.
- 2026-02-04 Access was recorded by on-call engineer with `PROD_API_TOKEN`.
- 2026-02-05 Leak report stated `PROD_API_TOKEN` was exposed in source control.
- 2026-02-06 Rotation completed for `PROD_API_TOKEN` and old token was disabled.

# Notes

- Investigation channel opened and incident commander assigned.
- Customer impact still unknown pending log correlation.

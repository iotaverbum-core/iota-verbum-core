# Security Policy Baseline

- 2026-02-01 `ROOT_TOKEN` is environment only.
- 2026-02-01 `ROOT_TOKEN` is never in source.
- Production access requires approved change ticket and named operator.

# Observed Activity

- 2026-02-11 Ops used shared `ROOT_TOKEN` for direct production access.
- 2026-02-11 `ROOT_TOKEN` appeared in a runbook committed to source control.
- 2026-02-12 Deployment proceeded without documented change ticket.
- Remediation owner not assigned.

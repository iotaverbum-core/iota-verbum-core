# Security Policy - IOTA VERBUM CORE

## Reporting a Vulnerability
To report a security vulnerability, contact: security@iotaverbum.example
Do not create a public GitHub issue for security vulnerabilities.
Expected response time: 48 hours.

## Supported Versions
| Version | Supported |
|---------|-----------|
| v0.3.x  | Yes       |
| v0.2.x  | No        |

## Known Security Posture
- API keys are transmitted via `X-API-Key` over HTTPS only.
- API keys are hashed before storage in audit logs.
- IP addresses are hashed before storage in audit logs.
- Raw document text is stored only in `document_inputs` and is subject to retention policy enforcement.
- Database credentials are stored in environment variables only.

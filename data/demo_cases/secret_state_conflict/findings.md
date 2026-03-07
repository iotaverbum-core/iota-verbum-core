# Secret Handling Statements

- 2026-01-05 `PAYMENTS_API_KEY` is environment only.
- 2026-01-08 `PAYMENTS_API_KEY` is never in source.
- 2026-01-10 Leak report says `PAYMENTS_API_KEY` was committed to source control.
- 2026-01-11 `PAYMENTS_API_KEY` rotated after exposure review.

# Open Questions

- Which actor committed the key is not documented.
- Scope of customer impact remains unknown.

# Determinism Contract (V2)

- No stochastic scoring in core reasoning.
- Stable ordering for all arrays and object keys.
- Stage hashing uses canonical JSON bytes only.
- Reproducibility criterion: two identical runs produce byte-identical canonical artifacts and ledger manifest hashes.
- Timestamp policy is explicit in `ledger_manifest_v2` (`stable_timestamp_policy`).

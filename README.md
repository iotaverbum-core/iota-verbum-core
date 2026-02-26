# iota-verbum-core

Deterministic core engine, schemas, and audit utilities for Iota Verbum.

This repository is intentionally minimal. Apps, demos, notebooks, and UI live elsewhere.

## Quickstart

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.lock
python -m pip install -e .
pytest
```

Run a deterministic pipeline:

```powershell
python -m deterministic_ai --domain biblical_text --input-ref "John 4:7-10" --dataset esv_sample --context "moment=smoke test" --out outputs\biblical_smoke
```

## Determinism

The core contract: identical inputs + pinned dependencies must produce byte-identical outputs.
See `docs/DETERMINISM.md` for details and verification steps.

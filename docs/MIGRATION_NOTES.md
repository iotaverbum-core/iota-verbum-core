# Migration Notes

## Source

Split from legacy repo: `C:\iotaverbum\iota_verbum` (branch `repo-reboot-core-split`).

## What Moved

- Core engine: `core/` -> `src/core/`
- Domains: `domains/` -> `src/domains/`
- CLI runner: `deterministic_ai.py` -> `src/deterministic_ai.py`
- Schemas: `schemas/`
- Minimal sample data: `data/credit`, `data/clinical`, `data/scripture/esv_sample`
- Determinism tests + goldens: `tests/test_deterministic_ai.py`, `tests/test_conscience_core.py`, `tests/golden/`

## What Stayed In Legacy

- Apps, UI, demos, notebooks, large corpora, outputs, and build artifacts.

## Packaging Changes

- Adopted `pyproject.toml` with `src/` layout.
- Added pinned `requirements.lock` for deterministic tooling installs.

## License

Legacy repo had no LICENSE file. Defaulted to MIT for the core repo.

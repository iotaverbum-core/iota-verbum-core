# Investigation UI

The investigation console is implemented in the existing Casefile Studio web app (`/studio`) and is fully downstream of deterministic run artifacts in `outputs/demo/<run_id>/*`.

## Surfaces

- Overview
- Graph
- Timeline
- Hypotheses
- Evidence
- Narrative
- Diff

## Data contract

The UI loads from API endpoints in `src/iota_verbum_api/casefile_studio.py` and does not generate independent reasoning.

## Run locally

```bash
uvicorn iota_verbum_api.app:app --reload
```

Open `http://localhost:8000/studio`.

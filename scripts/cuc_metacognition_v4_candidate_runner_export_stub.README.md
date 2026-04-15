# CUC v4 Candidate Notebook Stub

Use [cuc_metacognition_v4_candidate_runner_export_stub.ipynb](C:/iotaverbum/iota-verbum-core/scripts/cuc_metacognition_v4_candidate_runner_export_stub.ipynb) as the first Kaggle notebook stub for the repo-local `v4` candidate.

## Inputs
- [cuc_metacognition_v4_candidate.task.json](C:/iotaverbum/iota-verbum-core/benchmark/cuc_metacognition_v4_candidate.task.json)
- [cuc_v4_candidate_params.json](C:/iotaverbum/iota-verbum-core/benchmark/cuc_v4_candidate_params.json)

The params JSON is expected to embed the canonical clean-pack, perturbed-pack, expected-delta, and scoring-manifest objects so the notebook can run from the two JSON artifacts alone.

## Helpers
- Single-cell clipboard copy:
  - [copy_cuc_v4_candidate_kaggle_cell.ps1](C:/iotaverbum/iota-verbum-core/scripts/copy_cuc_v4_candidate_kaggle_cell.ps1)
- Bulk snippet export to `cell_01.py` through `cell_06.py`:
  - [export_cuc_v4_candidate_kaggle_cells.ps1](C:/iotaverbum/iota-verbum-core/scripts/export_cuc_v4_candidate_kaggle_cells.ps1)
- Canonical params hydration:
  - [build_cuc_v4_candidate_params.py](C:/iotaverbum/iota-verbum-core/scripts/build_cuc_v4_candidate_params.py)
- Five-model sweep folder prep:
  - [prepare_cuc_v4_candidate_five_model_sweep.ps1](C:/iotaverbum/iota-verbum-core/scripts/prepare_cuc_v4_candidate_five_model_sweep.ps1)
- Five-model sweep import and combined summary:
  - [import_cuc_v4_candidate_five_model_sweep.py](C:/iotaverbum/iota-verbum-core/scripts/import_cuc_v4_candidate_five_model_sweep.py)
  - [import_cuc_v4_candidate_five_model_sweep.ps1](C:/iotaverbum/iota-verbum-core/scripts/import_cuc_v4_candidate_five_model_sweep.ps1)

## Kaggle Path
1. Upload the stub notebook or paste cells `1` to `6` in order.
2. Add the two benchmark JSON files to the notebook session.
3. Keep the evaluation call on `llm=[kbench.llm]`.
4. Collect notebook exports from `/kaggle/working/cuc_v4_candidate_export/`.

## Five-Model Sweep Path
1. Run [prepare_cuc_v4_candidate_five_model_sweep.ps1](C:/iotaverbum/iota-verbum-core/scripts/prepare_cuc_v4_candidate_five_model_sweep.ps1) to create the expected download folders under `Downloads\cuc_v4_candidate_2026_04_08\`.
2. Download each Kaggle task results zip into the matching per-model folder as `results.zip`.
3. Run [import_cuc_v4_candidate_five_model_sweep.ps1](C:/iotaverbum/iota-verbum-core/scripts/import_cuc_v4_candidate_five_model_sweep.ps1) from the repo root.
4. Read the combined sweep summary at `cuc-docs/CUC_V4_CANDIDATE_FIVE_MODEL_SWEEP_2026_04_08.md`.

Full handoff notes live in [CUC_V4_CANDIDATE_KAGGLE_UPLOAD_SNIPPET_2026_04_08.md](C:/iotaverbum/iota-verbum-core/cuc-docs/CUC_V4_CANDIDATE_KAGGLE_UPLOAD_SNIPPET_2026_04_08.md).

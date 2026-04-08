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

## Kaggle Path
1. Upload the stub notebook or paste cells `1` to `6` in order.
2. Add the two benchmark JSON files to the notebook session.
3. Keep the evaluation call on `llm=[kbench.llm]`.
4. Collect notebook exports from `/kaggle/working/cuc_v4_candidate_export/`.

Full handoff notes live in [CUC_V4_CANDIDATE_KAGGLE_UPLOAD_SNIPPET_2026_04_08.md](C:/iotaverbum/iota-verbum-core/cuc-docs/CUC_V4_CANDIDATE_KAGGLE_UPLOAD_SNIPPET_2026_04_08.md).

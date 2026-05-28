# CUC v4 Candidate Kaggle Upload Snippet

## Files to add to the Kaggle notebook session
- `benchmark/cuc_metacognition_v4_candidate.task.json`
- `benchmark/cuc_v4_candidate_params.json`

## Notebook source
- Preferred: upload [cuc_metacognition_v4_candidate_runner_export_stub.ipynb](C:/iotaverbum/iota-verbum-core/scripts/cuc_metacognition_v4_candidate_runner_export_stub.ipynb) as the starting notebook.
- Manual paste path: copy cells from the stub notebook into a fresh Kaggle notebook in order.

## Clipboard helper
Use the helper below from the repo root to copy the exact source of one notebook cell at a time:

```powershell
powershell -File .\scripts\copy_cuc_v4_candidate_kaggle_cell.ps1 -CellNumber 1
powershell -File .\scripts\copy_cuc_v4_candidate_kaggle_cell.ps1 -CellNumber 2
powershell -File .\scripts\copy_cuc_v4_candidate_kaggle_cell.ps1 -CellNumber 3
powershell -File .\scripts\copy_cuc_v4_candidate_kaggle_cell.ps1 -CellNumber 4
powershell -File .\scripts\copy_cuc_v4_candidate_kaggle_cell.ps1 -CellNumber 5
powershell -File .\scripts\copy_cuc_v4_candidate_kaggle_cell.ps1 -CellNumber 6
```

## Bulk snippet helper
If you want all six code cells broken out into paste-ready `.py` snippets under a temp folder:

```powershell
powershell -File .\scripts\export_cuc_v4_candidate_kaggle_cells.ps1
```

Optional custom output directory:

```powershell
powershell -File .\scripts\export_cuc_v4_candidate_kaggle_cells.ps1 -OutputDir .\tmp_cuc_v4_cells
```

This creates:
- `cell_01.py`
- `cell_02.py`
- `cell_03.py`
- `cell_04.py`
- `cell_05.py`
- `cell_06.py`

The helper also copies the generated snippet paths to the clipboard.

## Kaggle notebook checklist
1. Add the dataset or upload the two JSON files so the notebook can resolve:
   - `benchmark/cuc_metacognition_v4_candidate.task.json`
   - `benchmark/cuc_v4_candidate_params.json`
2. Paste notebook cells `1` through `6` from the stub in order if you are not uploading the full notebook.
   Or use the bulk snippet helper and paste `cell_01.py` through `cell_06.py` in order.
3. Keep the evaluation call on `llm=[kbench.llm]` so the notebook uses the active Kaggle Benchmarks model selection.
4. Run the notebook top to bottom.
5. Collect exports from `/kaggle/working/cuc_v4_candidate_export/`.

## Expected exports
- `cuc_metacognition_v4_candidate.task.json`
- `cuc_v4_candidate_params.json`
- `evaluation_input_preview.csv`
- `results_export.json`
- `results_repr.txt`

## Five-model sweep helpers
Prepare the expected download folders under `Downloads\cuc_v4_candidate_2026_04_08\`:

```powershell
powershell -File .\scripts\prepare_cuc_v4_candidate_five_model_sweep.ps1
```

After downloading each private Kaggle results zip into the matching model folder as `results.zip`, run:

```powershell
powershell -File .\scripts\import_cuc_v4_candidate_five_model_sweep.ps1
```

This will:
- import each available v4 candidate results zip into `cuc-results/`
- write per-model flat CSV and headline metrics artifacts
- generate the combined sweep summary doc at `cuc-docs/CUC_V4_CANDIDATE_FIVE_MODEL_SWEEP_2026_04_08.md`

# iota-verbum-core

This repo contains the deterministic benchmark and provenance tooling behind the CUC metacognition benchmark line.

## Start Here

If you only need the current public benchmark surface, start with:

- `cuc-docs/CUC_BENCHMARK_INDEX_2026_04_14.md`

That index is the canonical map for:

- the current flagship benchmark
- the supporting benchmark set
- the authoritative result artifacts
- the small set of docs that should be cited externally

## Current Flagship

The current flagship benchmark story is:

- `CUC v5a 64-case`
- focus: scaffold-sensitive selective belief revision
- canonical task: `benchmark/cuc_metacognition_v5a_candidate.task.json`
- canonical full-pack params: `benchmark/cuc_v5_64_params.json`
- canonical runner notebook: `scripts/cuc_metacognition_v5a_candidate_runner_export_stub.ipynb`

Primary flagship docs:

- sweep summary: `cuc-docs/CUC_V5A_64_CASE_SWEEP_2026_04_14.md`
- submission-safe draft: `cuc-docs/CUC_V5A_FINAL_SUBMISSION_DRAFT_2026_04_14.md`

Primary flagship result artifacts:

- `cuc-results/cuc_v5a_64_case_sweep_2026_04_14_model_summary.csv`
- `cuc-results/cuc_v5a_64_case_sweep_2026_04_14_case_matrix.csv`
- `cuc-results/cuc_v5a_64_case_sweep_2026_04_14_family_summary.csv`
- `cuc-results/cuc_v5a_64_case_sweep_2026_04_14_headline_metrics.txt`

## Supporting Benchmarks

Two older CUC benchmark lines remain important and are still supported:

- `CUC v4 24-case`
  - compact discriminator benchmark
  - strongest supporting doc: `cuc-docs/CUC_V4_24_CASE_STRONGER_MODEL_SWEEP_2026_04_11.md`
- `CUC v3.1 Hardened`
  - broader two-state supporting benchmark
  - strongest supporting doc: `cuc-docs/CUC_V31_HARDENED_SUBMISSION_DRAFT_2026_04_07.md`

## Repo Structure

- `benchmark/`
  - canonical task JSONs, benchmark params, and shared scorer/runtime code
- `scripts/`
  - notebook builders, importers, bundle tools, and helper scripts
- `cuc-results/`
  - imported run artifacts, flat results, matrices, and headline metrics
- `cuc-docs/`
  - benchmark writeups, specs, submission drafts, and handovers
- `fixtures/`
  - benchmark source fixtures and supporting source material

## Public-Facing Rule

This repo has a lot of benchmark history. Not every document in `cuc-docs/` is canonical.

For external communication:

- use the benchmark index first
- treat the v5a flagship docs as primary
- treat v4 and v3.1 as supporting evidence
- treat per-run findings, patch logs, and older planning docs as internal history unless the index points to them

## Kaggle and Import Workflow

Canonical Kaggle outputs should be normalized into repo artifacts with the importer scripts rather than quoted directly from screenshots or notebook UIs.

Key import path:

- `scripts/import_cuc_kaggle_results_zip.py`

The v5a full sweep also has a dedicated importer:

- `scripts/import_cuc_v5a_64_case_model_sweep.py`

## Integrity and Verification

Trust-loop entry points:

- `scripts/clonable_integrity.ps1`
- `python -m core.casefile.inspect`
- `python -m core.determinism.replay`
- `docs/proof_trace_viewer.html`

Step-by-step local SDK notes live at:

- `cuc-docs/CREATE_CUC_KBENCH_STEPS.md`

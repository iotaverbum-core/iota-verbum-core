# CUC Benchmark Index

This is the canonical public-facing map for the benchmark materials in this repo.

If a reader only opens one document before exploring the rest of the benchmark artifacts, it should be this one.

## Start Here

Use the benchmark docs in this order:

1. `CUC_V5A_FINAL_SUBMISSION_DRAFT_2026_04_14.md`
2. `CUC_V5A_64_CASE_SWEEP_2026_04_14.md`
3. supporting benchmark docs for `v4` and `v3.1`

Everything else in `cuc-docs/` should be treated as supporting detail, working history, or implementation notes unless this index points to it explicitly.

## Current Flagship

### CUC v5a 64-case

This is the current flagship benchmark story.

What it is:

- a deterministic benchmark for scaffold-sensitive selective belief revision
- a `Run 1` / `Run 2A` / `Run 2B` design
- a benchmark that compares revision with prior state versus revision without prior state

Canonical benchmark assets:

- task: `benchmark/cuc_metacognition_v5a_candidate.task.json`
- full-pack params: `benchmark/cuc_v5_64_params.json`
- runner notebook: `scripts/cuc_metacognition_v5a_candidate_runner_export_stub.ipynb`
- shared scorer/runtime: `benchmark/cuc_metacognition_shared.py`

Canonical result artifacts:

- `cuc-results/cuc_v5a_64_case_sweep_2026_04_14_model_summary.csv`
- `cuc-results/cuc_v5a_64_case_sweep_2026_04_14_case_matrix.csv`
- `cuc-results/cuc_v5a_64_case_sweep_2026_04_14_family_summary.csv`
- `cuc-results/cuc_v5a_64_case_sweep_2026_04_14_headline_metrics.txt`

Canonical flagship docs:

- `CUC_V5A_FINAL_SUBMISSION_DRAFT_2026_04_14.md`
- `CUC_V5A_64_CASE_SWEEP_2026_04_14.md`
- `CUC_V5A_JUDGE_BRIEF_2026_04_14.md`
- `CUC_V5A_SUBMISSION_SPINE_2026_04_14.md`
- `CUC_V5A_PRIOR_ANCHORED_REVISION_SPEC_2026_04_12.md`

Safe public read:

- prior context helps many models, but not all
- Claude Sonnet 4.6 is the top and only scaffold-independent model in the current imported sweep
- `threshold_crossing` is the strongest scaffold-sensitive family
- `evidence_removal` is the universal hard family

Important cautions:

- do not frame the result as a universal prior-as-scaffold law
- do not frame it as proof of literal pride or emotion
- do not frame it as a sequential multi-step truth-maintenance benchmark

## Supporting Benchmarks

### CUC v4 24-case

Use `v4` as the compact supporting discriminator benchmark.

Canonical assets:

- task: `benchmark/cuc_metacognition_v4_candidate.task.json`
- params: `benchmark/cuc_v4_candidate_params.json`
- runner: `scripts/cuc_metacognition_v4_candidate_runner_export_stub.ipynb`

Primary supporting doc:

- `CUC_V4_24_CASE_STRONGER_MODEL_SWEEP_2026_04_11.md`

Why it matters:

- clean 8-model sweep
- strong case-level disagreement
- useful compact comparison pack

### CUC v3.1 Hardened

Use `v3.1 Hardened` as the broader supporting two-state benchmark.

Primary supporting doc:

- `CUC_V31_HARDENED_SUBMISSION_DRAFT_2026_04_07.md`

Why it matters:

- broader pack size
- earlier strong cross-model separation
- still useful supporting evidence for the benchmark line

## Operational Docs

These are implementation-facing rather than narrative-facing:

- `CREATE_CUC_KBENCH_STEPS.md`
- `KAGGLE_SUBMISSION_CHECKLIST.md`
- `HACKATHON_PROJECT_CONTEXT_CURRENT.md`

Use these for building, validating, or briefing, not as the first public-facing materials.

## Working History and Archive

This repo includes many valuable but non-canonical benchmark-history docs:

- patch logs
- handovers
- partial sweep summaries
- per-model findings
- implementation backlogs
- exploratory specs

Examples:

- `CUC_V4_FLAGSHIP_HANDOVER_2026_04_12.md`
- `CUC_V4_24_CASE_GROUNDING_FIX_HANDOVER_2026_04_09.md`
- `CUC_V41_SEQUENTIAL_PERTURBATION_SPEC_2026_04_12.md`
- `CUC_findings_*.md`

These should be treated as historical or internal support material unless a current canonical doc points to them.

## Recommended External Citation Spine

If we need a minimal judge-safe citation spine, use:

1. `CUC_V5A_FINAL_SUBMISSION_DRAFT_2026_04_14.md`
2. `cuc-results/cuc_v5a_64_case_sweep_2026_04_14_model_summary.csv`
3. `cuc-results/cuc_v5a_64_case_sweep_2026_04_14_family_summary.csv`
4. `CUC_V5A_JUDGE_BRIEF_2026_04_14.md`
5. `CUC_V5A_64_CASE_SWEEP_2026_04_14.md`
6. `CUC_V4_24_CASE_STRONGER_MODEL_SWEEP_2026_04_11.md`
7. `CUC_V31_HARDENED_SUBMISSION_DRAFT_2026_04_07.md`

That gives one flagship narrative, two flagship data tables, one short judge-facing brief, one flagship technical sweep note, and the two strongest supporting benchmark references.

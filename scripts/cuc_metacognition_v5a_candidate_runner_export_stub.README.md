# CUC v5a Candidate Notebook Stub

Use [cuc_metacognition_v5a_candidate_runner_export_stub.ipynb](C:/iotaverbum/iota-verbum-core/scripts/cuc_metacognition_v5a_candidate_runner_export_stub.ipynb) as the canonical Kaggle notebook stub for the repo-local `v5a` prior-anchor benchmark.

## Inputs
- [cuc_metacognition_v5a_candidate.task.json](C:/iotaverbum/iota-verbum-core/benchmark/cuc_metacognition_v5a_candidate.task.json)
- preferred full pack: [cuc_v5_64_params.json](C:/iotaverbum/iota-verbum-core/benchmark/cuc_v5_64_params.json)
- fallback pilot pack: [cuc_v5a_candidate_params.json](C:/iotaverbum/iota-verbum-core/benchmark/cuc_v5a_candidate_params.json)

The notebook resolves the `64`-case full pack first and falls back to the frozen `10`-case pilot pack only if the full-pack params file is absent.

## Build Source
- Shared scorer / parser / canonical-reference source:
  - [cuc_metacognition_shared.py](C:/iotaverbum/iota-verbum-core/benchmark/cuc_metacognition_shared.py)
- Task and notebook generator:
  - [build_cuc_v5a_candidate_task.py](C:/iotaverbum/iota-verbum-core/scripts/build_cuc_v5a_candidate_task.py)
- Pilot-pack generator:
  - [build_cuc_v5a_candidate_params.py](C:/iotaverbum/iota-verbum-core/scripts/build_cuc_v5a_candidate_params.py)
- Full-pack source artifact:
  - [cuc_v5_64_params.json](C:/iotaverbum/iota-verbum-core/benchmark/cuc_v5_64_params.json)

## Kaggle Path
1. Upload the stub notebook.
2. Add the two benchmark JSON files to the notebook session.
3. Keep the evaluation call on `llm=[kbench.llm]`.
4. Collect notebook exports from `/kaggle/working/cuc_v5a_candidate_export/`.

The task itself is self-contained inside the task JSON definition, so the Kaggle notebook does not need hidden notebook-local scorer helpers.

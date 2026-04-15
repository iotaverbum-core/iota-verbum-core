# CUC v5a 64-Case Sweep

## Source lock
- Task: `cuc_metacognition_v5a_candidate`
- Canonical repo task: `benchmark/cuc_metacognition_v5a_candidate.task.json`
- Canonical repo full-pack params: `benchmark/cuc_v5_64_params.json`
- Distinct imported models: 8
- Duplicate zips skipped: 2
- Duplicate detail: Claude Sonnet 4.6: 1 skipped, DeepSeek V3.2: 1 skipped

## Model results
- Claude Sonnet 4.6: 2A 60/64 (93.8%), 2B 60/64 (93.8%), task 60/64 (93.8%), scaffold cases=0, reverse-scaffold cases=0
- GPT-5.4: 2A 60/64 (93.8%), 2B 57/64 (89.1%), task 57/64 (89.1%), scaffold cases=3, reverse-scaffold cases=0
- Claude Sonnet 4.5: 2A 60/64 (93.8%), 2B 46/64 (71.9%), task 46/64 (71.9%), scaffold cases=14, reverse-scaffold cases=0
- Gemini 2.5 Flash: 2A 59/64 (92.2%), 2B 48/64 (75.0%), task 48/64 (75.0%), scaffold cases=11, reverse-scaffold cases=0
- google/gemma-4-26b-a4b: 2A 53/62 (85.5%), 2B 57/62 (91.9%), task 52/62 (83.9%), scaffold cases=1, reverse-scaffold cases=5
- Qwen 3 Next 80B Thinking: 2A 49/61 (80.3%), 2B 48/61 (78.7%), task 42/61 (68.9%), scaffold cases=7, reverse-scaffold cases=6
- Gemini 2.5 Pro: 2A 45/64 (70.3%), 2B 30/64 (46.9%), task 23/64 (35.9%), scaffold cases=22, reverse-scaffold cases=7
- DeepSeek V3.2: 2A 43/64 (67.2%), 2B 40/64 (62.5%), task 27/64 (42.2%), scaffold cases=16, reverse-scaffold cases=13

## Supported read
- Positive prior advantage appears in 6/8 models: GPT-5.4, Claude Sonnet 4.5, Gemini 2.5 Flash, Qwen 3 Next 80B Thinking, Gemini 2.5 Pro, DeepSeek V3.2.
- Neutral prior advantage models: Claude Sonnet 4.6.
- Counterexample models where 2B beats 2A: google/gemma-4-26b-a4b.
- All-model task-pass cases: 6/64.
- All-model task-fail cases: 4/64.
- `evidence_removal` is the universal hard family: 2A 0/32, 2B 0/32.
- `threshold_crossing` is the strongest scaffold-sensitive family: 2A 32/32, 2B 13/32.

## Cautions
- This sweep supports a scaffold-sensitive selective belief revision story, not a universal prior-as-scaffold law.
- The strongest counterexample is Gemma 4 26B, which does better on 2B than 2A.
- No-op controls are not universally scaffold-sensitive; the dramatic no-op dependence is concentrated in Gemini 2.5 Pro.
- This is still a two-evidence-state benchmark. It does not yet prove sequential multi-step truth maintenance.

## Generated artifacts
- [flat runs csv](cuc-results/cuc_results_flat_cuc_v5a_64_case_sweep_2026_04_14.csv)
- [model summary csv](cuc-results/cuc_v5a_64_case_sweep_2026_04_14_model_summary.csv)
- [case matrix csv](cuc-results/cuc_v5a_64_case_sweep_2026_04_14_case_matrix.csv)
- [family summary csv](cuc-results/cuc_v5a_64_case_sweep_2026_04_14_family_summary.csv)
- [headline metrics txt](cuc-results/cuc_v5a_64_case_sweep_2026_04_14_headline_metrics.txt)

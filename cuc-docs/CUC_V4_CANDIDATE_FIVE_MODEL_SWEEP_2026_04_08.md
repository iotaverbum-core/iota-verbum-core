# CUC v4 Candidate Five-Model Sweep

## Completed runs vs errors
- Imported model zips: 5/5 expected sweep slots
- Missing model slots: none
- Fallback used: none
- Import errors: none

## Per-model pass count on the 2-case pack
- GPT-5.4: 2/2 (task-wiring errors=0, score/export inconsistencies=0)
- Claude Sonnet 4.6: 2/2 (task-wiring errors=0, score/export inconsistencies=0)
- Gemini 2.5 Pro: 0/2 (task-wiring errors=0, score/export inconsistencies=0)
- Gemini 2.5 Flash: 1/2 (task-wiring errors=0, score/export inconsistencies=0)
- Qwen 3 Next 80B Thinking: 2/2 (task-wiring errors=0, score/export inconsistencies=0)

## Hard fail reasons
- GPT-5.4: none
- Claude Sonnet 4.6: none
- Gemini 2.5 Pro: none
- Gemini 2.5 Flash: fabricated_evidence_ids
- Qwen 3 Next 80B Thinking: none

## Fabricated-id regression check
- fabricated_ids reappeared: no
- fabricated_evidence_ids reappeared: yes

## Scorer/export consistency
- overall_pass remained consistent with imported Kaggle results: yes

## Separation read
- All-pass cases: 0/2
- All-fail cases: 0/2
- Disagreement cases: 2/2
- Assessment: meaningful separation across every imported candidate case

## Recommendation
- Expand to 24+ cases before spending more model budget. This 2-case sweep is useful for smoke-comparison and regression checking, but not for flagship leaderboard claims.

## Generated artifacts
- [model summary csv](C:/iotaverbum/iota-verbum-core/cuc-results/cuc_v4_candidate_2026_04_08_model_summary.csv)
- [case matrix csv](C:/iotaverbum/iota-verbum-core/cuc-results/cuc_v4_candidate_2026_04_08_case_matrix.csv)

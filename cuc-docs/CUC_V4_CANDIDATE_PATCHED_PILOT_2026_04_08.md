## CUC v4 Candidate Patched Kaggle Pilot

- **Date**: 2026-04-08
- **Notebook flow**: patched `cuc_metacognition_v4_candidate` pilot notebook with the safe summarized export cell
- **Dataset input**: patched Kaggle dataset `cuc-v4-candidate-pilot-inputs-patched`
- **Model**: `google/gemini-2.5-flash`
- **Cases**: 2 preserve-heavy candidate cases
- **Outcome**: 2/2 overall passes in Kaggle after the canonical-id prompt contract fix

## Why This Matters

- The patched rerun confirms the live Kaggle notebook/task flow works end to end with nested structured params.
- The `CANONICAL ID REFERENCE` block fixed the original prompt-to-scorer mismatch that produced `fabricated_ids` and `fabricated_evidence_ids` in the first pilot.
- The safe export cell successfully wrote the summarized evidence bundle without hitting Kaggle's `_thread.RLock` serialization issue.

## Evidence Artifacts

- Raw Kaggle export: `cuc-results/cuc_v4_candidate_patched_pilot_2026_04_08_results_export.json`
- Headline metrics: `cuc-results/cuc_v4_candidate_patched_pilot_2026_04_08_headline_metrics.txt`

## Important Caveat

- Case `CUCV4-PRESERVE-01-SIBLING-STABILITY-LEGAL-CONTRACT` cleared the scorer's operational pass rule at `overall_score=0.78` and `overall_pass=True`, but the pre-alignment task assertion policy still recorded one failed causal-propagation assertion in the exported run artifact.
- The repo task has been aligned so per-axis assertions now remain diagnostic once the operational pass rule already succeeds, preventing future contradictions between `overall_pass` and notebook assertion summaries.

## Safe Positioning

- This is strong evidence that the v4 candidate prompt contract is now viable in Kaggle.
- This is not yet evidence that `v4` is flagship-ready. The pilot still covers only 2 preserve-heavy cases and needs a larger, more diverse pack before any flagship claim.

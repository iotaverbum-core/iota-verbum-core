# Hackathon Project Context (Current)

## 0. Current Flagship Status
- **Current flagship candidate**: CUC v3.1 Hardened, Kaggle task `cuc_metacognition_v31_hardened`.
- **Candidate pack**: `cuc_v31_hardened_kaggle_pack_candidate.zip`, generated from the v3 hardening loop.
- **Size / structure**: 68 cases total: 48 inherited geometry-hardened cases, 8 no-op controls, and 12 hop-depth-3 holdout candidates.
- **Scoring**: Deterministic local structured scoring; no judge-model scorer in the v3.1 candidate.
- **Zip-backed leaderboard imported on 2026-04-07**:
  - Claude Sonnet 4.6: 67/68
  - GPT-5.4: 66/68
  - Qwen 3 Next 80B Thinking: 57/68
  - Claude Sonnet 4.5: 57/68 with 2 provider/runtime errors
  - DeepSeek V3.2: 54/68
  - Gemini 2.5 Pro: 44/68
  - Gemini 2.5 Flash: 43/68
- **Current evidence signal**: v3.1 separates frontier models, all ranked models pass the no-op controls, and hop-depth-3 cases are the dominant hard subset.
- **Current caution**: v3.1 is stronger than v2, but still generator-derived. Do not describe the holdout split as actually private unless the Kaggle dataset release withholds those cases.
- **Primary artifacts**:
  - `cuc-results/cuc_v31_hardened_2026_04_07_leaderboard.csv`
  - `cuc-results/cuc_v31_hardened_2026_04_07_failures.csv`
  - `cuc-results/cuc_v31_hardened_2026_04_07_case_matrix.csv`
  - `cuc-docs/CUC_V31_HARDENED_SUBMISSION_DRAFT_2026_04_07.md`
- **Current v4 candidate**: `cuc_metacognition_v40_revision_pressure`.
- **Current v4 verdict**: `NO-GO` for full flagship `v4` today; `GO` as a `v4 candidate` or `v4 revision-pressure core`.
- **Current repo-local v4 draft**: first runnable local draft now exists as `benchmark/cuc_metacognition_v4_candidate.task.json` plus `benchmark/cuc_v4_candidate_params.json`, currently covering 2 preserve-heavy candidate cases.
- **Live v4 pilot status as of 2026-04-08**: the patched Kaggle rerun completed end to end with 2 completed runs on `google/gemini-2.5-flash`, and both runs passed the scorer's operational pass rule.
- **Live v4 pilot finding**: nested structured param fields are accepted by Kaggle Benchmarks in the current notebook/task flow, and the canonical-id prompt contract fixed the first pilot's `fabricated_ids` / `fabricated_evidence_ids` hard failures.
- **Five-model v4 candidate sweep status as of 2026-04-09**: a 5-model Kaggle smoke sweep completed on the same 2-case preserve-heavy pack with imported repo-side artifacts for GPT-5.4, Claude Sonnet 4.6, Gemini 2.5 Pro, Gemini 2.5 Flash, and Qwen 3 Next 80B Thinking.
- **Five-model v4 candidate sweep result**:
  - GPT-5.4: 2/2
  - Claude Sonnet 4.6: 2/2
  - Qwen 3 Next 80B Thinking: 2/2
  - Gemini 2.5 Flash: 1/2 with a `fabricated_evidence_ids` hard fail on one case
  - Gemini 2.5 Pro: 0/2
- **Five-model v4 sweep interpretation**: the 2-case `v4` candidate is meaningfully discriminative at smoke-test scale (`2/2` disagreement cases across the five-model matrix), but it is still too small for flagship claims and still exposes at least one provider-specific grounding regression.
- **Current v4 evidence artifact**:
  - `cuc-results/cuc_v4_candidate_patched_pilot_2026_04_08_results_export.json`
  - `cuc-results/cuc_v4_candidate_patched_pilot_2026_04_08_headline_metrics.txt`
  - `cuc-docs/CUC_V4_CANDIDATE_PATCHED_PILOT_2026_04_08.md`
  - `cuc-results/cuc_v4_candidate_2026_04_08_model_summary.csv`
  - `cuc-results/cuc_v4_candidate_2026_04_08_case_matrix.csv`
  - `cuc-docs/CUC_V4_CANDIDATE_FIVE_MODEL_SWEEP_2026_04_08.md`
- **Notebook export note**: the original repo stub export cell hit Kaggle result serialization on `_thread.RLock`; the repo notebook now uses a summarized export payload instead of serializing the raw `results` object, and the patched rerun produced the full export bundle successfully.
- **Current v4 caution**: the successful pilot plus five-model sweep still cover only 2 preserve-heavy cases. The pack is good enough for smoke-comparison and regression hunting, but not yet for headline leaderboard claims or more model-budget spend on the same tiny slice.
- **Current v4 build decision**: expand the candidate to at least 24 scored cases, with a preferred target of 32 to 40, before spending more model budget beyond the already-imported 5-model sweep.
- **Full v4 must-have gates**:
  - at least 24 scored cases, with a preferred target of 32 to 40
  - non-empty `must_preserve` coverage in at least 25% of cases
  - 4 to 8 no-op / restraint controls
  - no single family above 30% of the pack and no single sector above 35%
  - imported cross-model evidence before any flagship rename
- **v4 planning docs**:
  - `cuc-docs/CUC_V4_GO_NO_GO_CHECKLIST_2026_04_08.md`
  - `cuc-docs/CUC_V4_BUILD_PLAN_2026_04_08.md`
  - `cuc-docs/CUC_V4_IMPLEMENTATION_BACKLOG_2026_04_08.md`

## 1. Dataset
- **Name / source**: CUC Legal Metacognition Benchmark v2, staged for Kaggle at `benchmark/kaggle/cuc-fixtures-final 50/new_fixtures/`.
- **Size**: 50 hosted cases. Each case folder contains `clean.md`, `perturbed.md`, and `diff.json`.
- **Type**: Structured text benchmark with paired evidence packs plus supervised change labels.
- **Key features / columns**: `case_id`, `clean_md`, `perturbed_md`, `ground_truth_q1`, `ground_truth_q2`, `ground_truth_q3`, `fired_invalidations`, `changed_states`, `changed_edges`, `resolved_unknowns`, `new_unknowns`.
- **Known issues**:
  - The benchmark is hard and discriminative, but structurally template-heavy.
  - 46/50 cases reuse the same generic state, edge, and unknown role slots.
  - Perturbations are highly regular: all 50 cases fire exactly one invalidation and create exactly four new unknowns.
  - A small set of scorer-shape fragility cases still needs audit, especially `BIOTECH-2026-GENE-THERAPY-IND`, `SUPPLY-2026-NEXCORE-CHIPSHORTAGE`, `AIRLINE-2026-SLOT-RULING`, `CRYPTO-2026-STAKING-REGULATION`, and `TECH-2026-OPENAI-APIBREAK`.

## 2. Notebook & Code
- **Platform**: Kaggle notebook / Jupyter.
- **Primary hosted notebook path**: `scripts/cuc_metacognition_legal_v2_matthewneal_20260405.ipynb` in the repo workspace and the corresponding uploaded Kaggle notebook.
- **Task name**: Hosted Kaggle task `cuc_metacognition_legal_v2`.
- **Current task structure**:
  - two-pass prompting (`clean_md` analysis followed by `perturbed_md` self-correction)
  - 15 judged criteria across Q1 detection, Q2 self-correction, and Q3 unknown tracking
  - case pass threshold of at least 11/15 criteria
- **Important implementation rule**:
  - In the notebook source, use `kbench.llm` rather than a hard-coded model list.
  - Inside Kaggle runtime evaluation calls, use `[kbench.llm]` as the grid value when calling `task.evaluate(...)`.
- **Repo-side import/export tooling**:
  - `scripts/import_cuc_kaggle_results_zip.py`
  - `cuc-results/`
  - `cuc-docs/`

## 3. Models & Runs
- **Current imported hosted results**: Eight one-model Kaggle exports imported on April 6, 2026.
- **Models evaluated**:
  - Claude Sonnet 4.6
  - Claude Haiku 4.5
  - Gemini 3.1 Pro Preview
  - Gemini 2.5 Pro
  - Gemini 2.5 Flash
  - DeepSeek V3.2
  - GPT-5.4
  - Qwen 3 Next 80B Thinking
- **Current case-level pass results**:
  - Claude Sonnet 4.6: 19/50
  - Claude Haiku 4.5: 2/50
  - Gemini 3.1 Pro Preview: 0/50
  - Gemini 2.5 Pro: 0/50
  - Gemini 2.5 Flash: 0/50
  - DeepSeek V3.2: 0/50
  - GPT-5.4: 0/50
  - Qwen 3 Next 80B Thinking: 0/50
- **Aggregate hosted result shape**:
  - 400/400 completed runs
  - 21/400 boolean passes
  - 370/400 clean runs
  - 0/50 all-pass cases
  - 29/50 all-fail cases
  - 21/50 disagreement cases
- **Missing target comparison models**:
  - Claude Sonnet 4.5
  - Gemma 3 12B

## 4. Competition Positioning
- **Theme / problem statement**: CUC tests whether a model detects what changed, revises only the impacted claims, and tracks uncertainty correctly when evidence shifts.
- **Why this fits the metacognition/cognitive track**: The benchmark is about selective belief revision under perturbation, not just one-shot answer quality.
- **Strongest safe claim right now**: The hosted 50-case legal task runs end to end in Kaggle, is difficult, and produces meaningful cross-model separation with a clear current leader.
- **Unsafe claim right now**: Do not describe the current 50-case hosted set as low-template, highly naturalistic, or fully flagship-ready without additional hardening.
- **Submission risk to acknowledge**:
  - template-heaviness
  - missing comparison models
  - scorer fragility on a small cluster of cases

## 5. Goals
- **Primary goal**: Build the strongest possible metacognition-track submission and compete for the grand prize with a benchmark-centered story.
- **Immediate benchmark goals**:
  - finish the comparison set by adding Claude Sonnet 4.5 and Gemma 3 12B
  - audit repeated non-clean cases
  - harden or diversify templated cases before making final flagship claims
- **Help most likely needed**:
  - notebook hardening
  - scorer hardening
  - benchmark analysis
  - submission writing
  - evidence-backed judge-safe positioning

## 6. Additional Resources
- **Core artifact paths**:
  - `cuc-results/cuc_results_flat_hosted_legal_v2_2026_04_06.csv`
  - `cuc-results/hosted_legal_v2_2026_04_06_case_matrix.csv`
  - `cuc-results/hosted_legal_v2_2026_04_06_headline_metrics.txt`
  - `cuc-results/hosted_legal_v2_2026_04_06_summary.txt`
  - `cuc-docs/CUC_submission_draft_hosted_legal_v2_2026_04_06.md`
  - `cuc-docs/CODEX_GRAND_PRIZE_MODE_PROMPT.md`
- **APIs / tools available**: `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `ANTHROPIC_API_KEY`, Kaggle Benchmarks runtime, repo-side scoring and import scripts.
- **Frontend / demo surface**: The benchmark submission surface is the Kaggle notebook and Kaggle task page. The repo also contains Casefile Studio, but that is secondary to the competition benchmark workflow.

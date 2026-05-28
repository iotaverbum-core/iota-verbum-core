# CUC v5a Judge Brief

## One-line thesis

CUC v5a measures whether a model can revise a prior belief state correctly when evidence changes, not just answer well from a static prompt.

## What the benchmark does

The current flagship benchmark is `CUC v5a 64-case`.

Each case uses:

- a clean evidence pack
- a perturbed evidence pack
- a `Run 1` prior analyst state
- a `Run 2A` revision with the prior in context
- a `Run 2B` revision without the prior

The benchmark scores whether the model:

1. detects the real change
2. revises only the affected chain
3. preserves unaffected structure
4. tracks new and resolved unknowns
5. grounds the revision in explicit evidence citations

## Why this matters

Most benchmarks reward final-answer quality. `CUC v5a` tests epistemic discipline under changed evidence:

- what changed?
- what still holds?
- what must be revised?
- what remains unknown?
- does the model behave differently when its own prior state is visible?

That makes the benchmark useful for procedural metacognition rather than static recall.

## Current flagship result

The imported `8`-model sweep supports a strong but careful claim:

- Claude Sonnet 4.6: `Run 2A 60/64`, `Run 2B 60/64`
- GPT-5.4: `Run 2A 60/64`, `Run 2B 57/64`
- Claude Sonnet 4.5: `Run 2A 60/64`, `Run 2B 46/64`
- Gemini 2.5 Flash: `Run 2A 59/64`, `Run 2B 48/64`
- google/gemma-4-26b-a4b: `Run 2A 53/62`, `Run 2B 57/62`
- Qwen 3 Next 80B Thinking: `Run 2A 49/61`, `Run 2B 48/61`
- DeepSeek V3.2: `Run 2A 43/64`, `Run 2B 40/64`
- Gemini 2.5 Pro: `Run 2A 45/64`, `Run 2B 30/64`

Interpretation:

- the benchmark is strongly discriminative
- prior context helps many models
- Claude Sonnet 4.6 is the only scaffold-independent top model
- the effect is not universal because Gemma 4 26B is a real counterexample

## What judges should notice

- This benchmark tests controlled revision under changed evidence, not one-shot answering.
- It separates a model that can revise from a model that can revise without an explicit externalized prior.
- It includes both a strong scaffold-sensitive family and a universal hard family:
  - `threshold_crossing`: strongest scaffold-sensitive family
  - `evidence_removal`: universal hard family
- It is backed by deterministic assets and imported zip-backed result artifacts, not just screenshots or prompt anecdotes.

## Safe public claims

- `CUC v5a` is a deterministic benchmark for scaffold-sensitive selective belief revision.
- It shows strong cross-model separation on an imported `8`-model sweep.
- Claude Sonnet 4.6 is the top and only scaffold-independent model in the current matrix.
- `evidence_removal` is universally hard across the current imported sweep.

## Claims to avoid

- Do not say the benchmark proves literal pride or emotion.
- Do not say prior context universally helps or universally hurts.
- Do not say the benchmark already proves sequential multi-step truth maintenance.
- Do not hide the incomplete export counts for Gemma and Qwen.

## Canonical submission assets

- flagship draft: `cuc-docs/CUC_V5A_FINAL_SUBMISSION_DRAFT_2026_04_14.md`
- flagship sweep summary: `cuc-docs/CUC_V5A_64_CASE_SWEEP_2026_04_14.md`
- benchmark index: `cuc-docs/CUC_BENCHMARK_INDEX_2026_04_14.md`
- model summary: `cuc-results/cuc_v5a_64_case_sweep_2026_04_14_model_summary.csv`
- family summary: `cuc-results/cuc_v5a_64_case_sweep_2026_04_14_family_summary.csv`

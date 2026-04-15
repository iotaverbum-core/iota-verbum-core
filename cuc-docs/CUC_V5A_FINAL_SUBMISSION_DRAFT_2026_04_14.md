# CUC v5a 64-Case Submission Draft

## One-line thesis

CUC v5a is a deterministic benchmark for scaffold-sensitive selective belief revision: it measures whether a model can update only the claims that should move when evidence changes, and whether having its own prior state in context changes how well it performs that revision.

## Executive summary

The current imported `8`-model sweep supports four strong claims:

1. `CUC v5a` is meaningfully discriminative across strong frontier models.
2. Prior context helps many models on this task, sometimes dramatically.
3. The effect is not universal; Claude Sonnet 4.6 is scaffold-independent, and Gemma 4 26B is a real counterexample.
4. `evidence_removal` is universally hard, while `threshold_crossing` is the clearest scaffold-sensitive family.

The strongest safe framing is:

**CUC v5a measures scaffold-sensitive selective belief revision, not a universal prior-as-scaffold law and not literal pride.**

## What the benchmark measures

Most benchmarks ask whether a model can answer correctly from a fixed prompt. `CUC v5a` asks something narrower and more operationally useful:

- what changed?
- what still holds?
- what must be revised?
- what must remain preserved?
- what remains unknown?
- can the model ground that revision in explicit evidence citations?

That is why the benchmark belongs in a metacognition framing. It evaluates whether the model can operate on its own prior reasoning state as an object of controlled revision.

## Protocol

Each case runs three prompt stages over two evidence states:

- `Run 1`: clean evidence pack, producing a prior analyst state
- `Run 2A`: perturbed evidence pack plus the model's own `Run 1` prior
- `Run 2B`: the same perturbed evidence pack without the prior

The central comparison is `Run 2A` versus `Run 2B`.

If a model performs better on `Run 2A`, that suggests the externalized prior state is acting as a useful scaffold for revision. If a model performs equally well on both, that suggests the revision behavior is more internally stable. If a model performs better on `Run 2B`, that is a real counterexample to any universal scaffold claim.

## Source lock

Canonical benchmark assets:

- task: `benchmark/cuc_metacognition_v5a_candidate.task.json`
- full case pack: `benchmark/cuc_v5_64_params.json`
- runner notebook: `scripts/cuc_metacognition_v5a_candidate_runner_export_stub.ipynb`
- shared scorer/runtime: `benchmark/cuc_metacognition_shared.py`

Canonical imported result artifacts:

- `cuc-results/cuc_v5a_64_case_sweep_2026_04_14_model_summary.csv`
- `cuc-results/cuc_v5a_64_case_sweep_2026_04_14_case_matrix.csv`
- `cuc-results/cuc_v5a_64_case_sweep_2026_04_14_family_summary.csv`
- `cuc-results/cuc_v5a_64_case_sweep_2026_04_14_headline_metrics.txt`
- `cuc-docs/CUC_V5A_64_CASE_SWEEP_2026_04_14.md`

## 8-model results

| Rank | Model | Run 2A | Run 2B | Task pass | Prior advantage | Scaffold cases |
|---|---|---:|---:|---:|---:|---:|
| 1 | Claude Sonnet 4.6 | 60/64 | 60/64 | 60/64 | +0.0pp | 0 |
| 2 | GPT-5.4 | 60/64 | 57/64 | 57/64 | +4.7pp | 3 |
| 3 | Claude Sonnet 4.5 | 60/64 | 46/64 | 46/64 | +21.9pp | 14 |
| 4 | Gemini 2.5 Flash | 59/64 | 48/64 | 48/64 | +17.2pp | 11 |
| 5 | google/gemma-4-26b-a4b | 53/62 | 57/62 | 52/62 | -6.5pp | 1 |
| 6 | Qwen 3 Next 80B Thinking | 49/61 | 48/61 | 42/61 | +1.6pp | 7 |
| 7 | DeepSeek V3.2 | 43/64 | 40/64 | 27/64 | +4.7pp | 16 |
| 8 | Gemini 2.5 Pro | 45/64 | 30/64 | 23/64 | +23.4pp | 22 |

Notes:

- `Scaffold cases` are cases where `Run 2A` passes and `Run 2B` fails.
- Gemma 4 26B exported `62/64` cases.
- Qwen 3 Next 80B Thinking exported `61/64` cases.
- Two duplicate result zips were ignored during import: one extra Claude Sonnet 4.6 zip and one extra DeepSeek V3.2 zip.

## What judges should notice

### 1. The benchmark separates top performance from scaffold dependence

Claude Sonnet 4.6 is the cleanest result in the matrix:

- `Run 2A`: `60/64`
- `Run 2B`: `60/64`
- scaffold cases: `0`
- reverse-scaffold cases: `0`

It is the only model in the sweep that is both top-scoring and scaffold-independent.

### 2. Several other strong models improve materially when given the prior

The biggest gaps appear in:

- Gemini 2.5 Pro: `45/64` vs `30/64`
- Claude Sonnet 4.5: `60/64` vs `46/64`
- Gemini 2.5 Flash: `59/64` vs `48/64`

This is the core signal behind the benchmark. The presence of an explicit prior state changes revision quality for many models.

### 3. The effect is real, but not universal

The sweep does not support a universal prior-as-scaffold claim.

- Claude Sonnet 4.6 is neutral.
- Gemma 4 26B is a counterexample where `Run 2B` beats `Run 2A`.

That counterexample is important because it shows the benchmark is measuring a genuine behavioral difference across models rather than baking in a one-directional advantage.

### 4. The family-level signal is strong and interpretable

The two clearest family findings are:

- `threshold_crossing`: `Run 2A 32/32`, `Run 2B 13/32`
- `evidence_removal`: `Run 2A 0/32`, `Run 2B 0/32`

This gives the benchmark both a strong sensitivity family and a strong universal-hard family.

### 5. No-op behavior is useful, but should be described carefully

The no-op controls do not justify a universal claim that priors are required to detect "nothing changed."

- Claude Sonnet 4.5, Claude Sonnet 4.6, GPT-5.4, DeepSeek V3.2, Qwen, and Gemma pass `9/9` no-op cases on both paths.
- Gemini 2.5 Flash shows a small no-op scaffold effect.
- Gemini 2.5 Pro shows a large one.

So the no-op signal is concentrated, not universal.

## Why this benchmark is credible

`CUC v5a` is not just a prompt or a leaderboard screenshot. It is backed by:

- deterministic task and scorer assets
- canonical task and params JSON
- imported zip-backed results
- per-model summary, per-case matrix, and per-family summary artifacts
- explicit caution language around counterexamples and incomplete exports

That gives the benchmark an audit trail rather than just an anecdotal performance story.

## Safe public interpretation

The strongest safe interpretation is:

`CUC v5a` demonstrates scaffold-sensitive selective belief revision, with strong model separation, an unambiguous top model, a real counterexample to universality, and interpretable hard families.

## Claims to avoid

- Do not claim `v5a` proves literal pride or emotion.
- Do not claim prior context universally helps or universally hurts.
- Do not claim the benchmark already proves sequential multi-step truth maintenance.
- Do not hide the incomplete export counts for Qwen and Gemma.

## Positioning against earlier CUC packs

- `CUC v5a 64-case` is the flagship benchmark story.
- `CUC v4 24-case` remains the strongest compact supporting discriminator benchmark.
- `CUC v3.1 Hardened` remains the broader supporting two-state benchmark.

## Submission-safe close

**CUC v5a is a deterministic 64-case benchmark for scaffold-sensitive selective belief revision. In the imported 8-model sweep, Claude Sonnet 4.6 is the top and only scaffold-independent model, several other frontier models improve materially when given their own prior state, `threshold_crossing` is the clearest scaffold-sensitive family, and `evidence_removal` remains universally hard across the full matrix.**

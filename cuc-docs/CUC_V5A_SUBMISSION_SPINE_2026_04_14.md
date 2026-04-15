# CUC v5a Submission Spine

## One-line thesis

Most benchmarks test whether a model can answer correctly. `CUC v5a` tests whether a model can revise only what changed, preserve what still holds, and track uncertainty correctly when evidence shifts.

## Competition fit

The strongest use of `CUC v5a` is as a metacognition benchmark for selective belief revision under changed evidence.

The benchmark answers a question that most static evaluations do not:

**Does the model perform revision differently when its own prior state is available?**

## Problem

Many benchmark scores blur together three different abilities:

- noticing what changed
- revising only the affected chain
- tracking uncertainty without collapsing or inventing it

`CUC v5a` measures those under a `Run 2A` versus `Run 2B` comparison that exposes whether an explicit prior state changes revision quality.

## Method

- `Run 1`: clean pack, freeform prior analyst state
- `Run 2A`: perturbed pack plus prior state
- `Run 2B`: perturbed pack without prior state
- deterministic structured scoring
- explicit evidence-grounding requirements
- imported zip-backed result artifacts

## Strongest current finding

The imported `8`-model sweep shows:

- Claude Sonnet 4.6: `60/64` on both `Run 2A` and `Run 2B`
- GPT-5.4: `60/64` versus `57/64`
- Claude Sonnet 4.5: `60/64` versus `46/64`
- Gemini 2.5 Flash: `59/64` versus `48/64`
- Gemma 4 26B: `53/62` versus `57/62`
- Qwen 3 Next 80B Thinking: `49/61` versus `48/61`
- DeepSeek V3.2: `43/64` versus `40/64`
- Gemini 2.5 Pro: `45/64` versus `30/64`

That supports a strong but careful interpretation:

- prior context helps many models
- the effect is large for several models
- the effect is not universal
- Claude Sonnet 4.6 is the only scaffold-independent top model

## Strongest family-level evidence

- `threshold_crossing`: strongest scaffold-sensitive family
  - `Run 2A 32/32`
  - `Run 2B 13/32`
- `evidence_removal`: universal hard family
  - `Run 2A 0/32`
  - `Run 2B 0/32`

These two families make the benchmark legible: one shows where scaffold dependence is strongest, the other shows where the entire field is still weak.

## What this means

`CUC v5a` does not show that models universally rely on priors, and it does not prove literal pride or emotion.

What it does show is:

- some models revise much better when their own prior state is externalized
- one model in this sweep does not need that scaffold
- the benchmark can distinguish those behaviors cleanly

That is a meaningful metacognitive signal.

## Safe claims only

- `CUC v5a` is a deterministic benchmark for scaffold-sensitive selective belief revision.
- It is discriminative across the current imported frontier-model sweep.
- Claude Sonnet 4.6 is the top and only scaffold-independent model in the current matrix.
- `evidence_removal` is universally hard across the current imported sweep.

## Claims to avoid

- Do not claim the benchmark proves literal pride.
- Do not claim prior context universally helps.
- Do not claim the benchmark already proves sequential multi-step truth maintenance.
- Do not suppress the Gemma counterexample or the incomplete export counts for Gemma and Qwen.

## Close

`CUC v5a` is valuable because it makes a normally hidden behavior visible: whether a model's revision quality changes when it has access to its own prior state. That is a tighter and more interpretable metacognition signal than static answer quality alone.

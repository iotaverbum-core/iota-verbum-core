# CUC v4 Build Plan

Date: 2026-04-08

Scope: This plan turns the reviewed `cuc_metacognition_v40_revision_pressure` slice into a full flagship-ready `CUC v4` candidate with concrete case-count targets, family balance targets, and go / no-go milestones.

Current status: `CUC v3.1 Hardened` remains the flagship candidate. `cuc_metacognition_v40_revision_pressure` is currently best treated as a `v4 revision-pressure core` rather than the full `v4`.

Five-model sweep update as of 2026-04-09:

- The patched `cuc_metacognition_v4_candidate` 2-case pack has now completed a repo-imported 5-model Kaggle smoke sweep.
- GPT-5.4, Claude Sonnet 4.6, and Qwen 3 Next 80B Thinking all passed `2/2`.
- Gemini 2.5 Flash passed `1/2` and reintroduced a `fabricated_evidence_ids` hard fail on one case.
- Gemini 2.5 Pro passed `0/2`.
- The sweep is useful because it shows real cross-model separation on the preserve-heavy design, but the pack is still too small for further model-budget spend to be the highest-value next step.
- Decision: the next investment should be candidate-pack expansion to at least 24 scored cases before another cross-model budget round.

Related decision doc:

- `cuc-docs/CUC_V4_GO_NO_GO_CHECKLIST_2026_04_08.md`
- `cuc-docs/CUC_V4_IMPLEMENTATION_BACKLOG_2026_04_08.md`

## Build Objective

Build a flagship-ready `CUC v4` main-score pack that:

- preserves the stronger revision-pressure design from `v40`
- adds explicit selective-preservation and over-revision traps
- adds no-op / restraint controls
- broadens family, sector, and render-profile coverage
- remains deterministic and audit-friendly
- produces imported cross-model separation evidence before any flagship rename

## Target Pack Shape

Recommended flagship target: 36 scored cases in the main pack.

Composition:

- 30 substantive revision cases
- 6 no-op / restraint controls

Separate diagnostic sidecar:

- up to 4 scaffolded or paired-ablation cases
- not included in the flagship aggregate score

## Main-Score Family Targets

These counts are the recommended target distribution for the 36-case flagship pack.

| Family | Current reviewed count | Target count | Preserve-heavy target | Hop-3 target | Notes |
| --- | ---: | ---: | ---: | ---: | --- |
| Deferred effect | 4 | 6 | 2 | 3 | Keep as a core family, but do not let it dominate the pack. |
| Temporal reorder | 1 | 4 | 1 | 2 | Use timing corrections that change some conclusions while preserving others. |
| Alternative-cause insertion | 1 | 4 | 1 | 1 | Good grounding family for cause flips and liability reversals. |
| Source-reliability collapse | 1 | 4 | 1 | 1 | Important for invalidation without direct fact replacement. |
| Conflict reconciliation | 1 | 4 | 1 | 1 | Useful for evidence conflict and source-priority reasoning. |
| Counterparty response | 1 | 4 | 1 | 1 | Good for unresolved-status handling and invariant uncertainty. |
| Selective preservation / sibling stability | 0 | 4 | 4 | 1 | New family: some branches must change while sibling branches must remain stable. |
| No-op / restraint controls | 0 | 6 | 6 | 0 | New control bucket: models should preserve the prior state except for formatting or wording cleanup. |
| Total | 9 | 36 | 17 | 10 | Meets size, preservation, and hop-depth targets from the v4 checklist. |

## Sector / Skin Targets

The goal is to avoid the flagship pack reading as one dominant domain with cosmetic re-skins.

| Sector / skin | Target count | Notes |
| --- | ---: | --- |
| Compliance | 10 | Keep strong representation, but below one-third of the pack. |
| Legal | 8 | Preserve contract and liability variants. |
| Procurement | 6 | Good fit for source validity, supplier status, and clause propagation. |
| Security | 6 | Good fit for conflict reconciliation and incident timeline cases. |
| Operations | 6 | Good fit for deferred effect and schedule-pressure cases. |
| Total | 36 | No sector exceeds 35% of the pack. |

## Render-Profile Targets

The pack should vary layout and rhetoric enough to resist template memorization.

| Render profile | Target count | Notes |
| --- | ---: | --- |
| `incident_digest_v1` | 8 | Keep, but do not let it dominate. |
| `legal_formal_v1` | 6 | Useful for clause-heavy liability and counterparty cases. |
| `ops_brief_v1` | 6 | Useful for schedule, arrival, and readiness chains. |
| `compliance_memo_v1` | 6 | Good for audit and policy-review variants. |
| `procurement_memo_v1` | 5 | Good for certification, vendor, and dependency cases. |
| `board_update_v1` | 5 | New profile to reduce rhetorical repetition. |
| Total | 36 | No profile exceeds 35% of the pack. |

## Structural Targets

These are the concrete pack-wide targets the build should satisfy before the first serious eval round.

| Dimension | Target |
| --- | --- |
| Total scored cases | 36 |
| No-op / restraint controls | 6 |
| Cases with non-empty `must_preserve` | 17 |
| Cases with explicit unaffected sibling branches | 12 |
| Hop-depth-3 cases | 10 |
| Distinct perturbation families | 8 |
| Distinct sectors / skins | 5 |
| Distinct render profiles | 6 |
| Scaffolded cases inside main score | 0 |

## Family Design Rules

### Deferred Effect

- Keep only 6 in the main pack.
- At least 2 should include stable sibling branches that must be preserved.
- At least 3 should be hop-depth-3.

### Temporal Reorder

- Build 4 cases total.
- At least 1 should preserve the final conclusion while forcing revision of intermediate timing claims.
- At least 2 should be hop-depth-3.

### Alternative-Cause Insertion

- Build 4 cases total.
- At least 1 should require revising liability or severity while preserving a separate unaffected operational branch.
- At least 1 should be preserve-heavy.

### Source-Reliability Collapse

- Build 4 cases total.
- At least 2 should test invalidation-by-retraction rather than direct factual replacement.
- At least 1 should preserve a downstream claim that remains supported by an independent source.

### Conflict Reconciliation

- Build 4 cases total.
- At least 2 should require choosing between conflicting sources with explicit provenance priority.
- At least 1 should preserve a previously stable branch after conflict resolution.

### Counterparty Response

- Build 4 cases total.
- At least 2 should force uncertainty promotion rather than a clean flip.
- At least 1 should require preserving operational facts while revising legal conclusions.

### Selective Preservation / Sibling Stability

- Build 4 cases total.
- Every case in this family must have non-empty `must_preserve`.
- At least 2 should contain a tempting over-revision trap where a model may rewrite an unaffected sibling branch.

### No-op / Restraint Controls

- Build 6 controls total.
- No substantive causal delta should exist.
- Models should pass only by preserving prior state and avoiding unsupported changes.
- At least 2 controls should include noisy wording changes that do not alter the evidence graph.

## Delivery Phases

### Phase 1: Foundation Expansion

Target: grow from 9 reviewed cases to 18 scored cases.

Add:

- 1 new case each for temporal reorder, alternative-cause insertion, source-reliability collapse, conflict reconciliation, and counterparty response
- 2 selective-preservation / sibling-stability cases
- 2 no-op / restraint controls
- 2 additional deferred-effect cases only if they include preserve-heavy structure

Exit criteria:

- at least 18 total scored cases
- at least 4 cases with non-empty `must_preserve`
- at least 2 no-op controls
- at least 5 hop-depth-3 cases

### Phase 2: Balance And Coverage

Target: reach 28 scored cases.

Add:

- enough new cases to bring every substantive family to at least 3 cases
- 2 more selective-preservation / sibling-stability cases
- 2 more no-op / restraint controls
- at least 3 new cases in underrepresented sectors or render profiles

Exit criteria:

- at least 28 total scored cases
- at least 8 cases with non-empty `must_preserve`
- at least 4 no-op controls
- no family above 35% of the pack
- no sector above 40% of the pack

### Phase 3: Flagship Candidate Completion

Target: reach the full 36-case flagship candidate pack.

Add:

- final family counts to match the main-score target table
- final sector and render-profile balancing cases
- no-op controls up to 6 total

Exit criteria:

- 36 scored cases in the main pack
- 17 cases with non-empty `must_preserve`
- 6 no-op controls
- 10 hop-depth-3 cases
- no family above 30% of the pack
- no sector above 35% of the pack
- scaffolded cases removed from the flagship aggregate

### Phase 4: Validation And Rename Decision

Target: determine whether the pack can replace `CUC v3.1 Hardened` as the flagship candidate.

Run:

- at least 5 models in the first serious imported comparison round
- preferred 7 or more models
- include at least 2 frontier leaders and 2 weaker baselines

Required evidence:

- imported case-by-model matrix
- fail / error separation
- summary metrics
- disagreement analysis
- no-op control pass behavior

Rename rule:

- do not rename to full flagship `CUC v4` until the build also satisfies the go / no-go checklist in `cuc-docs/CUC_V4_GO_NO_GO_CHECKLIST_2026_04_08.md`

## Immediate Work Queue

Recommended next tasks:

1. Add 2 selective-preservation / sibling-stability cases.
2. Add 2 no-op / restraint controls.
3. Add 1 new case each for temporal reorder, source-reliability collapse, and conflict reconciliation.
4. Split scaffolded diagnostic cases into a sidecar rather than the main-score pack.
5. Recompute family, sector, and hop-depth counts after each batch.

## One-Line Plan Summary

Treat `v40 revision pressure` as the core of `CUC v4`, grow it to a 36-case balanced pack with 17 preserve-heavy cases and 6 no-op controls, then require imported cross-model evidence before any flagship rename.

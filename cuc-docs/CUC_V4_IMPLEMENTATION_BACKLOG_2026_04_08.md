# CUC v4 Implementation Backlog

Date: 2026-04-08

Scope: This backlog turns the `CUC v4` build plan into the next concrete authoring queue: exact next cases to write, family priority order, and the target naming scheme for `v4` task and fixture generation.

Current status: `CUC v3.1 Hardened` remains the flagship candidate. `cuc_metacognition_v40_revision_pressure` remains a `v4 candidate` / `v4 core` until the missing gates from the checklist are closed.

2026-04-09 sweep decision:

- The imported 5-model Kaggle smoke sweep on the current 2-case `v4` candidate confirms that the preserve-heavy design can separate models, but it also confirms the pack is still too small to justify more model-budget spend on the same slice.
- Current imported sweep result:
  - GPT-5.4: `2/2`
  - Claude Sonnet 4.6: `2/2`
  - Qwen 3 Next 80B Thinking: `2/2`
  - Gemini 2.5 Flash: `1/2` with `fabricated_evidence_ids` on one case
  - Gemini 2.5 Pro: `0/2`
- Immediate implication: the backlog below should now be treated as the next gating work before another multi-model sweep. The next serious target is a `v4 candidate` pack of at least 24 scored cases, not another comparison run on the 2-case pack.

Related docs:

- `cuc-docs/CUC_V4_GO_NO_GO_CHECKLIST_2026_04_08.md`
- `cuc-docs/CUC_V4_BUILD_PLAN_2026_04_08.md`

## Backlog Objective

Close the highest-value missing `v4` gaps first:

1. add explicit selective-preservation cases
2. add no-op / restraint controls
3. add underrepresented high-signal families
4. grow hop-depth-3 coverage without letting `DEFERRED-EFFECT` dominate again
5. keep all new case IDs and fixture paths aligned with the current repo layout

## Family Priority Order

| Priority | Family | Why it comes first | Immediate target |
| --- | --- | --- | --- |
| 1 | `selective_preservation_sibling_stability` | Biggest current gap: the reviewed `v40` slice has no non-empty `must_preserve` coverage. | Write 2 cases next. |
| 2 | `no_op_control` | Second biggest gap: the reviewed `v40` slice has no explicit restraint controls. | Write 2 cases next. |
| 3 | `temporal_reorder` | Good hop-depth-3 family and still underrepresented in the reviewed slice. | Write 1 preserve-heavy hop-3 case next. |
| 4 | `source_reliability_collapse` | High grounding value and good fit for invalidation without direct fact replacement. | Write 1 case next. |
| 5 | `conflict_reconciliation` | High-signal provenance family that can also test preserved sibling branches. | Write 1 case next. |
| 6 | `counterparty_response` | Important for uncertainty promotion and invariant propagation. | Write 1 case next. |
| 7 | `alternative_cause_insertion` | Still valuable, but less urgent than preservation and controls. | Queue after the next 8. |
| 8 | `deferred_effect` | Already relatively overrepresented; only add when it closes a missing preserve or hop-3 gap. | Defer until later batches. |

## Exact Next 8 Cases To Write

These are the recommended next eight fixture directories to author under `benchmark/kaggle/fixtures/`.

| Order | Target `case_id` | Family | Sector / skin | Render profile | Hop depth | Primary objective |
| --- | --- | --- | --- | --- | ---: | --- |
| 1 | `CUCV4-PRESERVE-01-SIBLING-STABILITY-LEGAL-CONTRACT` | `selective_preservation_sibling_stability` | `legal_contract` | `legal_formal_v1` | 2 | Force revision of penalty and recovery conclusions while preserving completed-delivery and notice-timing facts. |
| 2 | `CUCV4-PRESERVE-02-SIBLING-STABILITY-SECURITY-INCIDENT` | `selective_preservation_sibling_stability` | `security_incident` | `board_update_v1` | 3 | Revise intrusion attribution and escalation branch while preserving unaffected backup-integrity findings. |
| 3 | `CUCV4-NOOP-01-COMPLIANCE-AUDIT` | `no_op_control` | `compliance_audit` | `compliance_memo_v1` | 1 | Wording-only or formatting-only amendment that should not trigger substantive revision. |
| 4 | `CUCV4-NOOP-02-OPERATIONS-BRIEF` | `no_op_control` | `operations_brief` | `ops_brief_v1` | 1 | Time-format or phrasing cleanup that leaves the evidence graph unchanged. |
| 5 | `CUCV4-HOP3-01-TEMPORAL-REORDER-OPERATIONS-BRIEF` | `temporal_reorder` | `operations_brief` | `ops_brief_v1` | 3 | Correct intermediate timing chain, revise schedule-risk reasoning, but preserve the final quota-achievable conclusion if still supported. |
| 6 | `CUCV4-GROUNDING-01-SOURCE-RELIABILITY-COLLAPSE-PROCUREMENT-REVIEW` | `source_reliability_collapse` | `procurement_review` | `procurement_memo_v1` | 2 | Withdraw one source, force revision of certification-derived claims, and preserve a sibling branch still supported by an independent source. |
| 7 | `CUCV4-GROUNDING-02-CONFLICT-RECONCILIATION-SECURITY-INCIDENT` | `conflict_reconciliation` | `security_incident` | `incident_digest_v1` | 3 | Resolve conflicting forensic sources using provenance priority while preserving unaffected integrity findings. |
| 8 | `CUCV4-INVARIANT-01-COUNTERPARTY-RESPONSE-LEGAL-CONTRACT` | `counterparty_response` | `legal_contract` | `legal_formal_v1` | 2 | Promote uncertainty through enforceability and recovery branches after counterparty retraction, while preserving operational facts. |

## One-Line Design Brief For Each Of The Next 8

| `case_id` | Design brief |
| --- | --- |
| `CUCV4-PRESERVE-01-SIBLING-STABILITY-LEGAL-CONTRACT` | Amendment retracts a penalty-trigger admission, which should revise liability and recovery recommendations, but separate proof of delivery and notice timeliness remain unchanged and must be preserved. |
| `CUCV4-PRESERVE-02-SIBLING-STABILITY-SECURITY-INCIDENT` | Supplemental evidence shows vendor credential compromise, which should revise attack attribution and escalation, but backup-integrity and restoration-completeness findings remain supported and must stay intact. |
| `CUCV4-NOOP-01-COMPLIANCE-AUDIT` | Revised memo clarifies wording around certificate review dates but introduces no factual change, so the model must preserve prior conclusions and avoid inventing risk. |
| `CUCV4-NOOP-02-OPERATIONS-BRIEF` | Ops note standardizes timezone and schedule wording while leaving arrival, inventory, and readiness unchanged; any substantive revision should be penalized. |
| `CUCV4-HOP3-01-TEMPORAL-REORDER-OPERATIONS-BRIEF` | Detection and approval timestamps are corrected, requiring revision of intermediate schedule risk, but the final production commitment remains achievable and should be preserved if still supported. |
| `CUCV4-GROUNDING-01-SOURCE-RELIABILITY-COLLAPSE-PROCUREMENT-REVIEW` | A supplier certification record is withdrawn, which invalidates waiver logic, but an independently supported insurance rider remains valid and should not be collateral-damaged. |
| `CUCV4-GROUNDING-02-CONFLICT-RECONCILIATION-SECURITY-INCIDENT` | A supplemental forensic log with stronger provenance contradicts the initial report, requiring revised attribution and escalation while preserving unaffected evidence-backed findings. |
| `CUCV4-INVARIANT-01-COUNTERPARTY-RESPONSE-LEGAL-CONTRACT` | Counterparty retracts an admission and invokes an exception clause, so enforceability and recovery claims must become uncertain, while shipment and receipt facts remain stable. |

## Immediate Acceptance Targets For The Next 8

The next eight should collectively satisfy the following:

| Target | Count |
| --- | ---: |
| Cases with non-empty `must_preserve` | 4 |
| No-op / restraint controls | 2 |
| Hop-depth-3 cases | 3 |
| New or underused render profiles | 1 new profile minimum |
| Cases with explicit unaffected sibling branches | 4 |
| Cases requiring named-artifact grounding for revision | 6 |

## Target Filename And Directory Scheme

### Fixture Directory Layout

Each case should live at:

`benchmark/kaggle/fixtures/<CASE_ID>/`

Each directory should preserve the current repo-local fixture file set:

- `fixture_case.json`
- `clean_pack.json`
- `perturbed_pack.json`
- `expected_delta.json`
- `scoring_manifest.json`
- `base_world.json`
- `base_world_input.json`
- `perturbed_world.json`
- `perturbation_manifest.json`
- `perturbation_manifest_input.json`
- `hashes.json`

### `case_id` Scheme

Use:

`CUCV4-<BUCKET>-<NN>-<FAMILY>-<SECTOR>`

Where:

- `<BUCKET>` is one of `PRESERVE`, `NOOP`, `HOP3`, `GROUNDING`, `INVARIANT`, or `CORE`
- `<NN>` is a zero-padded sequence number within the bucket
- `<FAMILY>` is uppercase hyphenated, for example `SOURCE-RELIABILITY-COLLAPSE`
- `<SECTOR>` is uppercase hyphenated, for example `LEGAL-CONTRACT`

Examples:

- `CUCV4-PRESERVE-01-SIBLING-STABILITY-LEGAL-CONTRACT`
- `CUCV4-NOOP-02-OPERATIONS-BRIEF`
- `CUCV4-HOP3-01-TEMPORAL-REORDER-OPERATIONS-BRIEF`
- `CUCV4-GROUNDING-01-SOURCE-RELIABILITY-COLLAPSE-PROCUREMENT-REVIEW`

### Metadata Naming Inside `fixture_case.json`

Use the following canonical field styles:

| Field | Target pattern |
| --- | --- |
| `benchmark_version` | `CUC.v4.candidate` |
| `case_id` | exact match with directory name |
| `family_id` | snake_case, for example `source_reliability_collapse` |
| `sector_skin` | snake_case, for example `legal_contract` |
| `render_profile` | repo-style profile id, for example `legal_formal_v1` |
| `template_id` | `tpl.v4.<bucket>.<nn>.<family>.<sector>` |
| `seed` | start at `40001` and increment monotonically |

### Task And Params File Scheme

Use the benchmark root for task and params artifacts:

| Artifact | Target path |
| --- | --- |
| Main candidate task | `benchmark/cuc_metacognition_v4_candidate.task.json` |
| Main candidate params | `benchmark/cuc_v4_candidate_params.json` |
| Diagnostic sidecar task | `benchmark/cuc_metacognition_v4_diagnostic.task.json` |
| Diagnostic sidecar params | `benchmark/cuc_v4_diagnostic_params.json` |
| Scratch phase-1 task, if needed | `benchmark/cuc_metacognition_v4_phase1_foundation.task.json` |
| Scratch phase-1 params, if needed | `benchmark/cuc_v4_phase1_foundation_params.json` |

### Split Rule

Use these split intentions consistently:

| Split type | Intended usage |
| --- | --- |
| `candidate_main` | Main scored `v4` pack under active buildout |
| `control` | No-op / restraint controls |
| `diagnostic_sidecar` | Scaffolded or paired-ablation cases not included in the flagship aggregate |

## Authoring Order

Write the next eight in this order:

1. `CUCV4-PRESERVE-01-SIBLING-STABILITY-LEGAL-CONTRACT`
2. `CUCV4-PRESERVE-02-SIBLING-STABILITY-SECURITY-INCIDENT`
3. `CUCV4-NOOP-01-COMPLIANCE-AUDIT`
4. `CUCV4-NOOP-02-OPERATIONS-BRIEF`
5. `CUCV4-HOP3-01-TEMPORAL-REORDER-OPERATIONS-BRIEF`
6. `CUCV4-GROUNDING-01-SOURCE-RELIABILITY-COLLAPSE-PROCUREMENT-REVIEW`
7. `CUCV4-GROUNDING-02-CONFLICT-RECONCILIATION-SECURITY-INCIDENT`
8. `CUCV4-INVARIANT-01-COUNTERPARTY-RESPONSE-LEGAL-CONTRACT`

This order is intentional:

- the first 4 cases close the two biggest missing gates
- cases 5 through 8 broaden high-signal family coverage without adding more `DEFERRED-EFFECT`

## Stop / Continue Rule After The Next 8

After these eight are drafted:

1. recompute family counts
2. recompute `must_preserve` coverage
3. recompute hop-depth-3 coverage
4. confirm at least 2 working no-op controls
5. only then queue the next batch, which should likely start with `alternative_cause_insertion` and one additional preserve-heavy procurement or compliance case

## One-Line Backlog Summary

The next eight `v4` cases should first close the preservation and no-op gaps, then add temporal, grounding, conflict, and uncertainty families using a `CUCV4-<BUCKET>-<NN>-<FAMILY>-<SECTOR>` naming scheme under `benchmark/kaggle/fixtures/`.

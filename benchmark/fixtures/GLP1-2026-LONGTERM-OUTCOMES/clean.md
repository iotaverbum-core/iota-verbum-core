# IOTA VERBUM CORE — Evidence Pack
## Case: GLP1-2026-LONGTERM-OUTCOMES
## Timestamp: 2026-03-07T09:00:00Z
## Source: NEJM and 5-year cardiovascular outcomes data

---

## SECTION 1 — ACTORS

ACTOR | id:actor_novo | label: Novo Nordisk (Ozempic / Wegovy sponsor) | type: corporation | status: ACTIVE
ACTOR | id:actor_lilly | label: Eli Lilly (Mounjaro / Zepbound) | type: corporation | status: ACTIVE
ACTOR | id:actor_fda_d | label: FDA (drug safety monitoring) | type: regulator | status: ACTIVE
ACTOR | id:actor_cms_d | label: CMS (Medicare coverage) | type: institution | status: ACTIVE
ACTOR | id:actor_cardiologists | label: Cardiology community | type: professional_body | status: ACTIVE
ACTOR | id:actor_patients_d | label: GLP-1 patients (est. 15M US) | type: population | status: ACTIVE

---

## SECTION 2 — CURRENT STATES

STATE | id:state_001 | label: SELECT trial 5-year data — 20% MACE reduction in non-diabetic obese | time: 2026-03-07T00:00:00Z | certainty: HIGH | value: 20 | unit: PCT
STATE | id:state_002 | label: N=17,604 patients, median follow-up 5.1 years | time: 2026-03-07T00:00:00Z | certainty: HIGH | value: 17604 | unit: patients
STATE | id:state_003 | label: Thyroid C-cell tumor signal: incidence 0.11% treatment vs 0.08% placebo | time: 2026-03-07T00:00:00Z | certainty: MEDIUM | value: 0.11 | unit: PCT
STATE | id:state_004 | label: p-value for thyroid signal 0.08 — not statistically significant | time: 2026-03-07T00:00:00Z | certainty: HIGH | value: 0.08 | unit: p_value
STATE | id:state_005 | label: Cardiovascular mortality reduction 15% (secondary endpoint) | time: 2026-03-07T00:00:00Z | certainty: HIGH | value: 15 | unit: PCT
STATE | id:state_006 | label: Pancreatitis rate no significant difference vs placebo | time: 2026-03-07T00:00:00Z | certainty: HIGH
STATE | id:state_007 | label: Weight regain after cessation 75% of lost weight in 2 years | time: 2026-03-07T00:00:00Z | certainty: HIGH | value: 75 | unit: PCT
STATE | id:state_008 | label: CMS coverage proposal for obesity indication under review | time: 2026-03-01T00:00:00Z | certainty: HIGH

---

## SECTION 3 — EXPLICIT CAUSAL EDGES

EDGE | id:edge_001 | state_001 -[20% MACE reduction strongest cardiovascular evidence yet for GLP-1]-> actor_cardiologists | strength: HIGH | lag: months
EDGE | id:edge_002 | state_005 -[mortality reduction supports expanded prescribing]-> actor_fda_d | strength: HIGH | lag: months
EDGE | id:edge_003 | state_003 -[thyroid signal needs monitoring — not significant but present]-> actor_fda_d | strength: MEDIUM | lag: months
EDGE | id:edge_004 | state_004 -[p>0.05 means thyroid concern not actionable at this point]-> actor_fda_d | strength: HIGH | lag: months
EDGE | id:edge_005 | state_007 -[weight regain data weakens case for discontinuation]-> actor_cms_d | strength: HIGH | lag: months
EDGE | id:edge_006 | state_008 -[CMS coverage decision will determine 15M patient access]-> actor_patients_d | strength: HIGH | lag: months

---

## SECTION 4 — TEMPORAL EVENT SEQUENCE

EVENT | id:event_t1 | time: 2021-01-01T00:00:00Z | label: SELECT trial begins | actor: actor_novo
EVENT | id:event_t2 | time: 2023-08-01T00:00:00Z | label: 2-year interim — initial MACE results | actor: actor_novo
EVENT | id:event_t3 | time: 2025-01-01T00:00:00Z | label: SELECT trial completes 5 years | actor: actor_novo
EVENT | id:event_t4 | time: 2026-02-15T00:00:00Z | label: NEJM submission and review | actor: actor_novo
EVENT | id:event_t5 | time: 2026-03-07T09:00:00Z | label: Full 5-year SELECT data published NEJM | actor: actor_novo

---

## SECTION 5 — INVALIDATION CONDITIONS

INVALIDATION | id:inv_001 | trigger: Thyroid signal reaches p<0.05 in pooled analysis | effect: FDA safety investigation — black box warning | switches: safety_concern
INVALIDATION | id:inv_002 | trigger: CMS approves obesity coverage | effect: access for 15M patients — market expansion | switches: coverage_breakthrough
INVALIDATION | id:inv_003 | trigger: MACE reduction not replicated in Lilly 5-year data | effect: SELECT findings questioned | switches: efficacy_dispute
INVALIDATION | id:inv_004 | trigger: New study shows weight regain preventable with maintenance dosing | effect: chronic use case strengthened | switches: chronic_use_supported

---

## SECTION 6 — SCENARIO MAP

SCENARIO | id:scen_A | label: CMS approves — GLP-1 becomes standard of care for CVD prevention | probability: 0.55 | trigger: SELECT data + CMS review converge | target: standard_of_care_2027
SCENARIO | id:scen_B | label: CMS defers — access limited to highest-risk patients | probability: 0.30 | trigger: Cost-effectiveness debate delays coverage | target: restricted_coverage
SCENARIO | id:scen_C | label: Safety investigation slows adoption | probability: 0.15 | trigger: inv_001 | target: fda_review_delay

SEALED_PATH | scenario: scen_A | confidence: 0.55 | sealed_at: 2026-03-07T09:00:00Z
REASONING: Strongest cardiovascular outcomes data published. Mortality reduction confirmed. Thyroid signal non-significant. CMS review underway. Sealed: standard of care by 2027.

---

## SECTION 7 — UNKNOWNS

UNKNOWN | id:unk_001 | label: CMS decision timeline and outcome | affects: inv_002 scen_A scen_B
UNKNOWN | id:unk_002 | label: Lilly 5-year SURPASS-CVOT results | affects: inv_003
UNKNOWN | id:unk_003 | label: Thyroid signal in pooled cross-trial analysis | affects: inv_001 scen_C
UNKNOWN | id:unk_004 | label: Maintenance dosing trial results | affects: inv_004 state_007

---

## SECTION 8 — INTEGRITY

SEAL | case_id: GLP1-2026-LONGTERM-OUTCOMES
SEAL | sealed_at: 2026-03-07T09:00:00Z
SEAL | mace_reduction_pct: 20
SEAL | sealed_scenario: scen_A
SEAL | replay_key: GLP1-2026-LONGTERM-OUTCOMES-A

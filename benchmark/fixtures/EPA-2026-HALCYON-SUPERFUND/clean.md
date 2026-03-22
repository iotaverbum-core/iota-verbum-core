# IOTA VERBUM CORE — Evidence Pack
## Case: EPA-2026-HALCYON-SUPERFUND
## Timestamp: 2026-03-11T09:00:00Z
## Source: EPA enforcement file and environmental assessment

---

## SECTION 1 — ACTORS

ACTOR | id:actor_halcyon | label: Halcyon Chemical Corp (defendant) | type: corporation | status: ACTIVE
ACTOR | id:actor_epa | label: EPA Region 4 Enforcement | type: regulator | status: ACTIVE
ACTOR | id:actor_doj_env | label: DOJ Environment and Natural Resources Division | type: law_enforcement | status: ACTIVE
ACTOR | id:actor_state | label: Georgia Environmental Protection Division | type: regulator | status: ACTIVE
ACTOR | id:actor_residents | label: Affected Residents (3,200 households) | type: individual_group | status: ACTIVE
ACTOR | id:actor_experts_env | label: Environmental expert witnesses | type: individual_group | status: ACTIVE

---

## SECTION 2 — CURRENT STATES

STATE | id:state_001 | label: PFAS contamination in groundwater — 840 ppt (EPA limit 4 ppt) | time: 2026-03-01T00:00:00Z | certainty: HIGH | value: 840 | unit: ppt
STATE | id:state_002 | label: Contamination plume extends 2.3 miles from Halcyon facility | time: 2026-03-01T00:00:00Z | certainty: HIGH | value: 2.3 | unit: miles
STATE | id:state_003 | label: Halcyon operational at site 1988-2018 — 30 years | time: 2026-03-11T00:00:00Z | certainty: HIGH | value: 30 | unit: years
STATE | id:state_004 | label: Halcyon internal docs show 2009 awareness of disposal violations | time: 2026-02-20T00:00:00Z | certainty: HIGH
STATE | id:state_005 | label: EPA remediation cost estimate 340M USD | time: 2026-03-05T00:00:00Z | certainty: MEDIUM | value: 340 | unit: MUSD
STATE | id:state_006 | label: Halcyon current net worth 180M USD — below remediation estimate | time: 2026-03-11T00:00:00Z | certainty: HIGH | value: 180 | unit: MUSD
STATE | id:state_007 | label: 14 former employees willing to testify re disposal practices | time: 2026-03-08T00:00:00Z | certainty: HIGH | value: 14 | unit: witnesses
STATE | id:state_008 | label: Class action by residents — 3200 households seeking medical monitoring | time: 2026-03-11T00:00:00Z | certainty: HIGH | value: 3200 | unit: households

---

## SECTION 3 — EXPLICIT CAUSAL EDGES

EDGE | id:edge_001 | state_001 -[840 ppt is 210x EPA limit — establishes clear CERCLA liability]-> actor_epa | strength: HIGH | lag: months
EDGE | id:edge_002 | state_004 -[2009 internal docs show knowing violation — supports punitive claim]-> actor_doj_env | strength: HIGH | lag: months
EDGE | id:edge_003 | state_007 -[14 witnesses provide direct operational testimony]-> actor_doj_env | strength: HIGH | lag: months
EDGE | id:edge_004 | state_006 -[180M net worth vs 340M liability creates insolvency risk]-> actor_halcyon | strength: HIGH | lag: months
EDGE | id:edge_005 | state_005 -[340M remediation creates massive settlement leverage]-> actor_epa | strength: HIGH | lag: months
EDGE | id:edge_006 | state_002 -[2.3 mile plume demonstrates scope of environmental damage]-> actor_residents | strength: HIGH | lag: months

---

## SECTION 4 — TEMPORAL EVENT SEQUENCE

EVENT | id:event_t1 | time: 2024-06-01T00:00:00Z | label: EPA discovers PFAS contamination | actor: actor_epa
EVENT | id:event_t2 | time: 2024-09-15T00:00:00Z | label: EPA names Halcyon as potentially responsible party | actor: actor_epa
EVENT | id:event_t3 | time: 2025-03-01T00:00:00Z | label: DOJ opens criminal investigation | actor: actor_doj_env
EVENT | id:event_t4 | time: 2026-02-20T00:00:00Z | label: 2009 internal documents produced in discovery | actor: actor_halcyon
EVENT | id:event_t5 | time: 2026-03-11T09:00:00Z | label: EPA remediation plan complete — 340M estimate | actor: actor_epa

---

## SECTION 5 — INVALIDATION CONDITIONS

INVALIDATION | id:inv_001 | trigger: Halcyon files Chapter 11 bankruptcy | effect: liability shifts to EPA Superfund — reduced recovery | switches: bankruptcy_protection
INVALIDATION | id:inv_002 | trigger: EPA remediation cost revised below 180M | effect: Halcyon may be able to pay — bankruptcy less likely | switches: solvent_defendant
INVALIDATION | id:inv_003 | trigger: Criminal charges filed against Halcyon executives | effect: individual liability — corporate veil pierced | switches: criminal_prosecution
INVALIDATION | id:inv_004 | trigger: Second responsible party identified — upstream supplier | effect: shared liability — Halcyon exposure reduced | switches: cost_sharing

---

## SECTION 6 — SCENARIO MAP

SCENARIO | id:scen_A | label: Consent decree — Halcyon pays maximum ability 180M | probability: 0.45 | trigger: EPA negotiates to Halcyon's net worth | target: consent_decree_180M
SCENARIO | id:scen_B | label: Bankruptcy — EPA Superfund covers shortfall | probability: 0.30 | trigger: inv_001 — Halcyon cannot bear liability | target: superfund_cleanup
SCENARIO | id:scen_C | label: Criminal prosecution — executives face charges | probability: 0.25 | trigger: inv_003 — 2009 docs trigger criminal referral | target: criminal_trial

SEALED_PATH | scenario: scen_A | confidence: 0.45 | sealed_at: 2026-03-11T09:00:00Z
REASONING: 2009 docs establish knowing violation. 14 witnesses. CERCLA liability clear. Halcyon may prefer consent decree to criminal. Sealed: scen_A — consent decree at net worth.

---

## SECTION 7 — UNKNOWNS

UNKNOWN | id:unk_001 | label: Whether DOJ refers criminal charges from 2009 documents | affects: inv_003 scen_C
UNKNOWN | id:unk_002 | label: Halcyon board response — cooperate or litigate | affects: scen_A timeline
UNKNOWN | id:unk_003 | label: Whether upstream supplier identified as co-responsible party | affects: inv_004 scen_A
UNKNOWN | id:unk_004 | label: Residents class action medical monitoring cost estimate | affects: state_008 total_liability

---

## SECTION 8 — INTEGRITY

SEAL | case_id: EPA-2026-HALCYON-SUPERFUND
SEAL | sealed_at: 2026-03-11T09:00:00Z
SEAL | pfas_ppt: 840
SEAL | halcyon_networth_MUSD: 180
SEAL | sealed_scenario: scen_A
SEAL | replay_key: EPA-2026-HALCYON-SUPERFUND-A

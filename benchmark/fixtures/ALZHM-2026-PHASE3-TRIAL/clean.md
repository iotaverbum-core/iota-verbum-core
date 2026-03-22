# IOTA VERBUM CORE — Evidence Pack
## Case: ALZHM-2026-PHASE3-TRIAL
## Timestamp: 2026-03-01T09:00:00Z
## Source: Phase 3 clinical trial interim data

---

## SECTION 1 — ACTORS

ACTOR | id:actor_pharma | label: NeuroClear Therapeutics (sponsor) | type: corporation | status: ACTIVE
ACTOR | id:actor_fda | label: FDA Center for Drug Evaluation | type: regulator | status: ACTIVE
ACTOR | id:actor_dsmb | label: Data Safety Monitoring Board | type: oversight_body | status: ACTIVE
ACTOR | id:actor_patients | label: Trial Participants (N=2840) | type: study_population | status: ACTIVE
ACTOR | id:actor_cms | label: CMS (Medicare reimbursement) | type: institution | status: ACTIVE
ACTOR | id:actor_competitors | label: Competing AD drug manufacturers | type: corporate_group | status: ACTIVE

---

## SECTION 2 — CURRENT STATES

STATE | id:state_001 | label: NCL-447 Phase 3 interim — CDR-SB improvement 2.1 points vs placebo | time: 2026-03-01T00:00:00Z | certainty: HIGH | value: 2.1 | unit: CDR-SB_points
STATE | id:state_002 | label: p-value 0.0031 — statistically significant | time: 2026-03-01T00:00:00Z | certainty: HIGH | value: 0.0031 | unit: p_value
STATE | id:state_003 | label: ARIA-E adverse events 21% of treatment arm | time: 2026-03-01T00:00:00Z | certainty: HIGH | value: 21 | unit: PCT
STATE | id:state_004 | label: DSMB recommends continuing trial — no safety halt | time: 2026-02-28T00:00:00Z | certainty: HIGH
STATE | id:state_005 | label: Enrollment complete — 2840 participants, 18-month follow-up | time: 2026-01-15T00:00:00Z | certainty: HIGH | value: 2840 | unit: patients
STATE | id:state_006 | label: Primary endpoint CDR-SB — requires 1.8 point improvement for approval | time: 2026-03-01T00:00:00Z | certainty: HIGH | value: 1.8 | unit: CDR-SB_points
STATE | id:state_007 | label: Secondary endpoint amyloid PET clearance 68% vs 12% placebo | time: 2026-03-01T00:00:00Z | certainty: HIGH | value: 68 | unit: PCT
STATE | id:state_008 | label: NDA submission planned Q3 2026 | time: 2026-03-01T00:00:00Z | certainty: HIGH

---

## SECTION 3 — EXPLICIT CAUSAL EDGES

EDGE | id:edge_001 | state_001 -[exceeds 1.8 threshold — primary endpoint met]-> actor_fda | strength: HIGH | lag: months
EDGE | id:edge_002 | state_002 -[p<0.05 required for approval — exceeded]-> actor_fda | strength: HIGH | lag: months
EDGE | id:edge_003 | state_003 -[21% ARIA-E rate triggers FDA close scrutiny on safety]-> actor_fda | strength: HIGH | lag: months
EDGE | id:edge_004 | state_004 -[DSMB continuation signals acceptable safety profile]-> actor_pharma | strength: HIGH | lag: weeks
EDGE | id:edge_005 | state_007 -[biological mechanism confirmed — supports efficacy claim]-> actor_fda | strength: HIGH | lag: months
EDGE | id:edge_006 | state_003 -[high ARIA rate will complicate CMS reimbursement negotiations]-> actor_cms | strength: MEDIUM | lag: months

---

## SECTION 4 — TEMPORAL EVENT SEQUENCE

EVENT | id:event_t1 | time: 2024-09-01T00:00:00Z | label: Phase 3 enrollment opens | actor: actor_pharma
EVENT | id:event_t2 | time: 2026-01-15T00:00:00Z | label: Enrollment complete at 2840 | actor: actor_pharma
EVENT | id:event_t3 | time: 2026-02-28T00:00:00Z | label: DSMB interim review — continue | actor: actor_dsmb
EVENT | id:event_t4 | time: 2026-03-01T00:00:00Z | label: Interim efficacy data released | actor: actor_pharma
EVENT | id:event_t5 | time: 2026-09-01T00:00:00Z | label: NDA submission planned | actor: actor_pharma

---

## SECTION 5 — INVALIDATION CONDITIONS

INVALIDATION | id:inv_001 | trigger: CDR-SB improvement falls below 1.8 at final analysis | effect: primary endpoint missed — NDA rejected | switches: approval_failure
INVALIDATION | id:inv_002 | trigger: ARIA-E rate exceeds 25% at final | effect: FDA safety concern overrides efficacy | switches: safety_halt
INVALIDATION | id:inv_003 | trigger: DSMB calls safety halt | effect: trial terminated | switches: program_death
INVALIDATION | id:inv_004 | trigger: p-value exceeds 0.05 at final analysis | effect: statistical significance lost | switches: approval_failure

---

## SECTION 6 — SCENARIO MAP

SCENARIO | id:scen_A | label: NDA approved — full approval 2027 | probability: 0.65 | trigger: Final data confirms interim + safety manageable | target: approval_2027
SCENARIO | id:scen_B | label: Accelerated approval with REMS | probability: 0.20 | trigger: Efficacy confirmed but FDA requires monitoring program | target: restricted_approval
SCENARIO | id:scen_C | label: Approval failure | probability: 0.15 | trigger: inv_001 or inv_002 | target: program_terminated

SEALED_PATH | scenario: scen_A | confidence: 0.65 | sealed_at: 2026-03-01T09:00:00Z
REASONING: Primary endpoint exceeded by 17%. p-value strong. Amyloid PET confirms mechanism. DSMB green light. ARIA-E rate manageable with monitoring. Sealed: NDA approval likely 2027.

---

## SECTION 7 — UNKNOWNS

UNKNOWN | id:unk_001 | label: Final 18-month CDR-SB result | affects: inv_001 scen_A
UNKNOWN | id:unk_002 | label: ARIA-E rate at final analysis | affects: inv_002 scen_B
UNKNOWN | id:unk_003 | label: FDA advisory committee composition | affects: scen_A scen_B
UNKNOWN | id:unk_004 | label: CMS reimbursement rate negotiation | affects: commercial_viability

---

## SECTION 8 — INTEGRITY

SEAL | case_id: ALZHM-2026-PHASE3-TRIAL
SEAL | sealed_at: 2026-03-01T09:00:00Z
SEAL | cdr_sb_improvement: 2.1
SEAL | p_value: 0.0031
SEAL | sealed_scenario: scen_A
SEAL | replay_key: ALZHM-2026-PHASE3-TRIAL-A

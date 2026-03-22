# IOTA VERBUM CORE — Evidence Pack
## Case: EEOC-2026-APEX-CLASSACTION
## Timestamp: 2026-03-04T11:00:00Z
## Source: EEOC investigation file and statistical analysis

---

## SECTION 1 — ACTORS

ACTOR | id:actor_apex | label: Apex Financial Services (defendant) | type: corporation | status: ACTIVE
ACTOR | id:actor_plaintiffs | label: Plaintiff class (est. 840 employees) | type: individual_group | status: ACTIVE
ACTOR | id:actor_eeoc | label: EEOC Southeast Region | type: regulator | status: ACTIVE
ACTOR | id:actor_counsel_p | label: Plaintiffs' counsel (Rosen & Warren LLP) | type: law_firm | status: ACTIVE
ACTOR | id:actor_counsel_d | label: Defense counsel (Gibson Dunn) | type: law_firm | status: ACTIVE
ACTOR | id:actor_court | label: USDC Northern District of Georgia | type: judiciary | status: ACTIVE

---

## SECTION 2 — CURRENT STATES

STATE | id:state_001 | label: Class certified — 840 plaintiffs | time: 2026-02-28T00:00:00Z | certainty: HIGH | value: 840 | unit: plaintiffs
STATE | id:state_002 | label: Statistical analysis shows 23% pay gap — Black employees vs white employees same role | time: 2026-02-15T00:00:00Z | certainty: HIGH | value: 23 | unit: PCT
STATE | id:state_003 | label: Gap persists after controlling for experience, tenure, education — residual 17% | time: 2026-02-15T00:00:00Z | certainty: HIGH | value: 17 | unit: PCT
STATE | id:state_004 | label: 3 named plaintiffs have contemporaneous performance review docs — all rated excellent | time: 2026-03-01T00:00:00Z | certainty: HIGH | value: 3 | unit: plaintiffs
STATE | id:state_005 | label: Defense expert claims pay gap explained by negotiation differences | time: 2026-03-04T00:00:00Z | certainty: HIGH
STATE | id:state_006 | label: EEOC found probable cause — issued Right to Sue | time: 2025-11-15T00:00:00Z | certainty: HIGH
STATE | id:state_007 | label: Apex internal HR emails reviewed — contain EXPLICIT discriminatory language from VP of Compensation | time: 2026-03-04T00:00:00Z | certainty: HIGH
STATE | id:state_008 | label: Trial date November 2026 — discovery closes June 2026 | time: 2026-03-04T00:00:00Z | certainty: HIGH

---

## SECTION 3 — EXPLICIT CAUSAL EDGES

EDGE | id:edge_001 | state_003 -[17% residual gap after controls is powerful disparate impact evidence]-> actor_court | strength: HIGH | lag: months
EDGE | id:edge_002 | state_004 -[excellent reviews negate performance-based pay justification]-> actor_counsel_p | strength: HIGH | lag: months
EDGE | id:edge_003 | state_005 -[negotiation explanation may require Apex to prove it offered equal negotiating opportunities]-> actor_court | strength: MEDIUM | lag: months
EDGE | id:edge_004 | state_006 -[EEOC probable cause strengthens plaintiffs' position]-> actor_court | strength: HIGH | lag: months
EDGE | id:edge_005 | state_007 -[internal HR emails may contain direct discrimination evidence]-> actor_counsel_p | strength: HIGH | lag: months
EDGE | id:edge_006 | state_001 -[840-person class dramatically increases damages exposure]-> actor_apex | strength: HIGH | lag: months

---

## SECTION 4 — TEMPORAL EVENT SEQUENCE

EVENT | id:event_t1 | time: 2025-03-01T00:00:00Z | label: Initial complaint filed | actor: actor_plaintiffs
EVENT | id:event_t2 | time: 2025-11-15T00:00:00Z | label: EEOC issues Right to Sue | actor: actor_eeoc
EVENT | id:event_t3 | time: 2026-01-10T00:00:00Z | label: Class certification motion filed | actor: actor_counsel_p
EVENT | id:event_t4 | time: 2026-02-28T00:00:00Z | label: Class certified at 840 plaintiffs | actor: actor_court
EVENT | id:event_t5 | time: 2026-03-04T11:00:00Z | label: HR email subpoena — review underway | actor: actor_counsel_p

---

## SECTION 5 — INVALIDATION CONDITIONS

INVALIDATION | id:inv_001 | trigger: HR emails contain explicit discriminatory intent | effect: direct evidence — pattern or practice claim strengthened | switches: direct_evidence_found | STATUS: FIRED
INVALIDATION | id:inv_002 | trigger: Apex pays settlement before trial | effect: class claim resolved | switches: settlement
INVALIDATION | id:inv_003 | trigger: Defense successfully decertifies class | effect: 840 plaintiffs back to individual claims | switches: decertification
INVALIDATION | id:inv_004 | trigger: Plaintiffs' statistical expert survives Daubert | effect: 17% residual gap admitted into evidence | switches: expert_admitted

---

## SECTION 6 — SCENARIO MAP

SCENARIO | id:scen_A | label: Trial — plaintiffs prevail on disparate impact | probability: 0.50 | trigger: Statistical evidence + email discovery + Daubert survival | target: verdict_damages_100-300M
SCENARIO | id:scen_B | label: Settlement before November trial | probability: 0.35 | trigger: Damages exposure + email discovery | target: settlement_50-120M
SCENARIO | id:scen_C | label: Defense prevails — negotiation explanation accepted | probability: 0.15 | trigger: Plaintiffs' expert excluded or residual gap explained | target: defense_verdict

SEALED_PATH | scenario: scen_A | confidence: 0.50 | STATUS: STRENGTHENED | sealed_at: 2026-03-04T11:00:00Z
REASONING: Class certified. 17% residual gap. EEOC probable cause. HR emails in discovery. Strong plaintiff posture. Sealed: trial with plaintiff verdict.

---

## SECTION 7 — UNKNOWNS

UNKNOWN | id:unk_001 | label: HR email content | STATUS: RESOLVED — EXPLICIT DISCRIMINATORY LANGUAGE FOUND | affects: inv_001 scen_A
UNKNOWN | id:unk_002 | label: Daubert ruling on statistical expert | affects: inv_004 scen_A
UNKNOWN | id:unk_003 | label: Whether Apex opens settlement discussions | affects: inv_002 scen_B
UNKNOWN | id:unk_004 | label: Defense expert rebuttal methodology | affects: state_005 scen_C

---

## SECTION 8 — INTEGRITY

SEAL | case_id: EEOC-2026-APEX-CLASSACTION
SEAL | sealed_at: 2026-03-04T11:00:00Z
SEAL | class_size: 840
SEAL | residual_pay_gap_pct: 17
SEAL | sealed_scenario: scen_A
SEAL | replay_key: EEOC-2026-APEX-CLASSACTION-PERTURBED

# IOTA VERBUM CORE — Evidence Pack
## Case: NATO-2026-ARTICLE5-THRESHOLD
## Timestamp: 2026-02-28T18:00:00Z
## Source: NATO intelligence assessments and diplomatic cables

---

## SECTION 1 — ACTORS

ACTOR | id:actor_russia | label: Russian Federation Armed Forces | type: state_military | status: ACTIVE
ACTOR | id:actor_nato | label: NATO Alliance (32 members) | type: military_alliance | status: ACTIVE
ACTOR | id:actor_poland | label: Republic of Poland | type: state | status: ACTIVE
ACTOR | id:actor_baltics | label: Baltic States (EST/LAT/LIT) | type: state_group | status: ACTIVE
ACTOR | id:actor_us_nato | label: US NATO Commander (SACEUR) | type: command | status: ACTIVE
ACTOR | id:actor_ukraine | label: Ukraine Armed Forces | type: state_military | status: ACTIVE

---

## SECTION 2 — CURRENT STATES

STATE | id:state_001 | label: Russian forces 12km from Polish border in Suwalki corridor | time: 2026-02-28T18:00:00Z | certainty: HIGH | value: 12 | unit: km
STATE | id:state_002 | label: NATO enhanced forward presence — 8 battlegroups active | time: 2026-02-28T00:00:00Z | certainty: HIGH | value: 8 | unit: battlegroups
STATE | id:state_003 | label: Article 5 consultation threshold under debate — no formal trigger | time: 2026-02-28T00:00:00Z | certainty: HIGH
STATE | id:state_004 | label: Polish air defense activated — PATRIOT batteries live | time: 2026-02-28T12:00:00Z | certainty: HIGH
STATE | id:state_005 | label: Russian cyber operations against Baltic infrastructure — 3 incidents | time: 2026-02-25T00:00:00Z | certainty: HIGH | value: 3 | unit: incidents
STATE | id:state_006 | label: US B-52 bombers deployed to UK — visible deterrent | time: 2026-02-20T00:00:00Z | certainty: HIGH
STATE | id:state_007 | label: Ukraine front line stable — no major Russian advance in 30 days | time: 2026-02-28T00:00:00Z | certainty: HIGH
STATE | id:state_008 | label: NATO emergency consultations ongoing — Article 4 invoked | time: 2026-02-27T00:00:00Z | certainty: HIGH

---

## SECTION 3 — EXPLICIT CAUSAL EDGES

EDGE | id:edge_001 | state_001 -[proximity creates military friction risk]-> actor_nato | strength: HIGH | lag: hours
EDGE | id:edge_002 | state_002 -[battlegroups provide trip-wire deterrence]-> actor_russia | strength: HIGH | lag: continuous
EDGE | id:edge_003 | state_005 -[cyber incidents below kinetic threshold but test NATO response]-> state_003 | strength: MEDIUM | lag: days
EDGE | id:edge_004 | state_006 -[B-52 deployment signals US commitment]-> actor_russia | strength: HIGH | lag: continuous
EDGE | id:edge_005 | state_007 -[Ukraine front stability reduces Russian escalation incentive]-> actor_russia | strength: MEDIUM | lag: weeks
EDGE | id:edge_006 | state_008 -[Article 4 consultation signals alliance cohesion]-> actor_russia | strength: MEDIUM | lag: days

---

## SECTION 4 — TEMPORAL EVENT SEQUENCE

EVENT | id:event_t1 | time: 2026-01-15T00:00:00Z | label: Russian force buildup near Suwalki corridor begins | actor: actor_russia
EVENT | id:event_t2 | time: 2026-02-10T00:00:00Z | label: Baltic cyber incidents begin | actor: actor_russia
EVENT | id:event_t3 | time: 2026-02-20T00:00:00Z | label: US deploys B-52s to UK | actor: actor_us_nato
EVENT | id:event_t4 | time: 2026-02-27T00:00:00Z | label: NATO Article 4 consultations invoked | actor: actor_nato
EVENT | id:event_t5 | time: 2026-02-28T18:00:00Z | label: Russian forces 12km from Polish border | actor: actor_russia

---

## SECTION 5 — INVALIDATION CONDITIONS

INVALIDATION | id:inv_001 | trigger: Russian forces cross Polish border | effect: Article 5 trigger — full NATO mobilization | switches: article5_activation
INVALIDATION | id:inv_002 | trigger: Cyber attack destroys critical Baltic infrastructure | effect: hybrid warfare threshold crossed | switches: hybrid_article5_debate
INVALIDATION | id:inv_003 | trigger: Russian forces withdraw 50km+ | effect: de-escalation — crisis subsides | switches: diplomatic_resolution
INVALIDATION | id:inv_004 | trigger: Ukraine front collapses | effect: Russian attention shifts — Suwalki pressure increases | switches: escalation_risk_rise

---

## SECTION 6 — SCENARIO MAP

SCENARIO | id:scen_A | label: Coercive standoff — no crossing | probability: 0.60 | trigger: Deterrence holds — Russia tests but does not cross | target: article4_prolonged
SCENARIO | id:scen_B | label: Hybrid escalation via cyber | probability: 0.25 | trigger: inv_002 — major infrastructure attack | target: article5_debate
SCENARIO | id:scen_C | label: Border crossing — Article 5 activated | probability: 0.15 | trigger: inv_001 | target: full_nato_response

SEALED_PATH | scenario: scen_A | confidence: 0.60 | sealed_at: 2026-02-28T18:00:00Z
REASONING: Deterrence architecture intact. B-52s visible. Battlegroups positioned. Article 4 signals cohesion. Russia gains more from coercive pressure than from triggering Article 5. Sealed: scen_A.

---

## SECTION 7 — UNKNOWNS

UNKNOWN | id:unk_001 | label: Russian operational orders for next 48 hours | affects: inv_001 scen_C
UNKNOWN | id:unk_002 | label: Whether next cyber incident crosses hybrid threshold | affects: inv_002 scen_B
UNKNOWN | id:unk_003 | label: Ukraine front status this week | affects: inv_004
UNKNOWN | id:unk_004 | label: NATO Article 4 consultation outcome | affects: state_003

---

## SECTION 8 — INTEGRITY

SEAL | case_id: NATO-2026-ARTICLE5-THRESHOLD
SEAL | sealed_at: 2026-02-28T18:00:00Z
SEAL | russian_proximity_km: 12
SEAL | sealed_scenario: scen_A
SEAL | replay_key: NATO-2026-ARTICLE5-THRESHOLD-A

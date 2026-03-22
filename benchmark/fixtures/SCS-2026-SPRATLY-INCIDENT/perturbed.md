# IOTA VERBUM CORE — Evidence Pack
## Case: SCS-2026-SPRATLY-INCIDENT
## Timestamp: 2026-03-08T09:00:00Z
## Source: Naval incident reports and regional defense assessments

---

## SECTION 1 — ACTORS

ACTOR | id:actor_china | label: China Coast Guard / PLAN | type: state_military | status: ACTIVE
ACTOR | id:actor_philippines | label: Philippines Coast Guard | type: state_military | status: ACTIVE
ACTOR | id:actor_usa_7th | label: US 7th Fleet | type: state_military | status: ACTIVE
ACTOR | id:actor_asean | label: ASEAN members | type: regional_body | status: ACTIVE
ACTOR | id:actor_vietnam | label: Vietnam Maritime Authority | type: state | status: ACTIVE
ACTOR | id:actor_icj | label: International Court of Justice | type: institution | status: ACTIVE

---

## SECTION 2 — CURRENT STATES

STATE | id:state_001 | label: Chinese water cannon attack on Philippines resupply vessel — 3rd this month | time: 2026-03-08T09:00:00Z | certainty: HIGH | value: 3 | unit: incidents
STATE | id:state_002 | label: US FORMALLY DECLARES water cannon attacks covered under MDT Article 4 | time: 2026-03-07T00:00:00Z | certainty: HIGH
STATE | id:state_003 | label: US destroyer USS Dewey conducting FONOP 12nm from Mischief Reef | time: 2026-03-08T09:00:00Z | certainty: HIGH
STATE | id:state_004 | label: China artificial island military installations — 7 reefs | time: 2026-03-01T00:00:00Z | certainty: HIGH | value: 7 | unit: reefs
STATE | id:state_005 | label: Philippines MDT Article 4 — armed attack coverage being debated | time: 2026-03-07T00:00:00Z | certainty: HIGH
STATE | id:state_006 | label: ASEAN consensus statement blocked by Cambodia and Laos | time: 2026-03-06T00:00:00Z | certainty: HIGH
STATE | id:state_007 | label: Vietnam increases naval patrol frequency 40% | time: 2026-03-01T00:00:00Z | certainty: HIGH | value: 40 | unit: PCT
STATE | id:state_008 | label: Philippines awaiting ICJ filing on latest incident | time: 2026-03-08T09:00:00Z | certainty: MEDIUM

---

## SECTION 3 — EXPLICIT CAUSAL EDGES

EDGE | id:edge_001 | state_001 -[escalating incidents increase Philippines military response pressure]-> actor_philippines | strength: HIGH | lag: days
EDGE | id:edge_002 | state_002 -[MDT consultation signals US commitment]-> actor_china | strength: HIGH | lag: hours
EDGE | id:edge_003 | state_003 -[FONOP demonstrates freedom of navigation — counters Chinese claims]-> actor_china | strength: HIGH | lag: hours
EDGE | id:edge_004 | state_006 -[ASEAN disunity weakens regional diplomatic pressure]-> actor_china | strength: MEDIUM | lag: days
EDGE | id:edge_005 | state_007 -[Vietnam escalation signals regional solidarity]-> actor_asean | strength: MEDIUM | lag: days
EDGE | id:edge_006 | state_004 -[permanent installations enable sustained Chinese presence]-> state_001 | strength: HIGH | lag: continuous

---

## SECTION 4 — TEMPORAL EVENT SEQUENCE

EVENT | id:event_t1 | time: 2026-02-15T00:00:00Z | label: First water cannon incident this month | actor: actor_china
EVENT | id:event_t2 | time: 2026-02-22T00:00:00Z | label: Second water cannon incident | actor: actor_china
EVENT | id:event_t3 | time: 2026-03-06T00:00:00Z | label: ASEAN consensus statement fails | actor: actor_asean
EVENT | id:event_t4 | time: 2026-03-07T00:00:00Z | label: Philippines invokes MDT consultation | actor: actor_philippines
EVENT | id:event_t5 | time: 2026-03-08T09:00:00Z | label: Third water cannon — USS Dewey FONOP same day | actor: actor_china

---

## SECTION 5 — INVALIDATION CONDITIONS

INVALIDATION | id:inv_001 | trigger: US declares water cannon attacks covered by MDT Article 4 | effect: full mutual defense commitment triggered | switches: us_military_response | STATUS: FIRED
INVALIDATION | id:inv_002 | trigger: Philippines coast guard vessel sunk or personnel killed | effect: MDT Article 4 automatic — military response | switches: military_confrontation
INVALIDATION | id:inv_003 | trigger: China agrees bilateral talks with Philippines | effect: de-escalation window opens | switches: diplomatic_track
INVALIDATION | id:inv_004 | trigger: ASEAN unanimous statement condemning China | effect: regional diplomatic pressure shifts | switches: multilateral_pressure

---

## SECTION 6 — SCENARIO MAP

SCENARIO | id:scen_A | label: Coercive status quo — incidents continue below MDT threshold | probability: 0.55 | trigger: US avoids Article 4 commitment | target: continued_harassment
SCENARIO | id:scen_B | label: MDT Article 4 invoked — US military response | probability: 0.25 | trigger: inv_001 or inv_002 | target: naval_confrontation
SCENARIO | id:scen_C | label: Diplomatic de-escalation | probability: 0.20 | trigger: inv_003 or ASEAN breakthrough | target: negotiations

SEALED_PATH | scenario: scen_A | confidence: 0.55 | STATUS: INVALIDATED | sealed_at: 2026-03-08T09:00:00Z
REASONING: US avoiding hard MDT commitment. ASEAN divided. China staying below lethal force threshold. Sealed: coercive status quo continues.

---

## SECTION 7 — UNKNOWNS

UNKNOWN | id:unk_001 | label: MDT Article 4 coverage | STATUS: RESOLVED — US COMMITS | affects: inv_001 scen_B
UNKNOWN | id:unk_002 | label: China next operational orders | affects: scen_A scen_B
UNKNOWN | id:unk_003 | label: Whether Philippines escalates to armed response | affects: inv_002
UNKNOWN | id:unk_004 | label: ICJ filing outcome and timeline | affects: state_008

---

## SECTION 8 — INTEGRITY

SEAL | case_id: SCS-2026-SPRATLY-INCIDENT
SEAL | sealed_at: 2026-03-08T09:00:00Z
SEAL | incidents_this_month: 3
SEAL | sealed_scenario: scen_A
SEAL | replay_key: SCS-2026-SPRATLY-INCIDENT-PERTURBED

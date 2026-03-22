# IOTA VERBUM CORE — Evidence Pack
## Case: TAIWAN-2026-STRAIT-TENSIONS
## Timestamp: 2026-03-10T12:00:00Z
## Source: Defense intelligence and diplomatic communications

---

## SECTION 1 — ACTORS

ACTOR | id:actor_prc | label: People's Republic of China (PLA) | type: state_military | status: ACTIVE
ACTOR | id:actor_taiwan | label: Republic of China (Taiwan) | type: state | status: ACTIVE
ACTOR | id:actor_usa | label: United States (7th Fleet) | type: state_military | status: ACTIVE
ACTOR | id:actor_japan | label: Japan (JSDF) | type: state_military | status: ACTIVE
ACTOR | id:actor_tsmc | label: TSMC (Taiwan Semiconductor) | type: corporation | status: ACTIVE
ACTOR | id:actor_un | label: United Nations Security Council | type: institution | status: ACTIVE

---

## SECTION 2 — CURRENT STATES

STATE | id:state_001 | label: PLA naval vessels 18 operating in Taiwan Strait | time: 2026-03-10T12:00:00Z | certainty: HIGH | value: 18 | unit: vessels
STATE | id:state_002 | label: PLA air incursions into ADIZ — 47 sorties past 30 days | time: 2026-03-10T00:00:00Z | certainty: HIGH | value: 47 | unit: sorties
STATE | id:state_003 | label: USS Ronald Reagan carrier strike group WITHDRAWN to Guam for scheduled maintenance | time: 2026-03-10T12:00:00Z | certainty: HIGH
STATE | id:state_004 | label: TSMC Arizona Fab 2 operational — 30% of leading-edge production | time: 2026-03-01T00:00:00Z | certainty: HIGH | value: 30 | unit: PCT
STATE | id:state_005 | label: Taiwan presidential election 6 weeks away | time: 2026-03-10T00:00:00Z | certainty: HIGH | value: 6 | unit: weeks
STATE | id:state_006 | label: DPP incumbent polling 8 points ahead | time: 2026-03-08T00:00:00Z | certainty: MEDIUM | value: 8 | unit: points
STATE | id:state_007 | label: Japan-US defense cooperation agreement signed Feb 2026 | time: 2026-02-20T00:00:00Z | certainty: HIGH
STATE | id:state_008 | label: PRC economic growth slowing — 3.8% GDP 2025 | time: 2026-01-15T00:00:00Z | certainty: HIGH | value: 3.8 | unit: PCT

---

## SECTION 3 — EXPLICIT CAUSAL EDGES

EDGE | id:edge_001 | state_005 -[election proximity increases PRC pressure campaign incentive]-> state_002 | strength: HIGH | lag: days
EDGE | id:edge_002 | state_006 -[DPP lead increases PRC motivation to intimidate voters]-> state_001 | strength: HIGH | lag: days
EDGE | id:edge_003 | state_003 -[carrier group presence deters escalation]-> actor_prc | strength: HIGH | lag: continuous
EDGE | id:edge_004 | state_007 -[Japan-US pact raises cost of PRC military action]-> actor_prc | strength: HIGH | lag: continuous
EDGE | id:edge_005 | state_008 -[economic weakness reduces PRC risk appetite for conflict]-> actor_prc | strength: MEDIUM | lag: weeks
EDGE | id:edge_006 | state_004 -[TSMC diversification reduces Taiwan leverage as hostage]-> actor_usa | strength: MEDIUM | lag: months

---

## SECTION 4 — TEMPORAL EVENT SEQUENCE

EVENT | id:event_t1 | time: 2026-01-20T00:00:00Z | label: Taiwan election campaign officially opens | actor: actor_taiwan
EVENT | id:event_t2 | time: 2026-02-05T00:00:00Z | label: PLA begins increased ADIZ incursions | actor: actor_prc
EVENT | id:event_t3 | time: 2026-02-20T00:00:00Z | label: Japan-US defense agreement signed | actor: actor_japan
EVENT | id:event_t4 | time: 2026-03-01T00:00:00Z | label: USS Ronald Reagan repositioned to Taiwan region | actor: actor_usa
EVENT | id:event_t5 | time: 2026-03-10T12:00:00Z | label: PLA naval presence peaks at 18 vessels | actor: actor_prc

---

## SECTION 5 — INVALIDATION CONDITIONS

INVALIDATION | id:inv_001 | trigger: PLA live-fire military exercises announced | effect: escalation threshold crossed | switches: crisis_escalation
INVALIDATION | id:inv_002 | trigger: Taiwan election result — KMT wins | effect: PRC pressure campaign succeeds | switches: diplomatic_reset
INVALIDATION | id:inv_003 | trigger: US carrier group withdraws | effect: deterrence gap opens | switches: emboldened_prc | STATUS: FIRED
INVALIDATION | id:inv_004 | trigger: UN Security Council emergency session called | effect: internationalization of crisis | switches: multilateral_response

---

## SECTION 6 — SCENARIO MAP

SCENARIO | id:scen_A | label: Pressure campaign — no kinetic action | probability: 0.65 | trigger: Deterrence holds through election | target: status_quo_post_election
SCENARIO | id:scen_B | label: Naval incident — near-collision or warning shots | probability: 0.25 | trigger: Miscalculation at sea | target: diplomatic_crisis
SCENARIO | id:scen_C | label: Full blockade attempt | probability: 0.10 | trigger: inv_001 + US withdrawal + KMT loss | target: military_confrontation

SEALED_PATH | scenario: scen_A | confidence: 0.65 | STATUS: WEAKENED | sealed_at: 2026-03-10T12:00:00Z
REASONING: Deterrence architecture intact. Carrier group present. Japan-US pact active. PRC economic weakness reduces risk appetite. Election 6 weeks out — pressure campaign more likely than kinetic action. Sealed path: scen_A.

---

## SECTION 7 — UNKNOWNS

UNKNOWN | id:unk_001 | label: PLA next 72-hour operational orders | affects: inv_001 scen_B
UNKNOWN | id:unk_002 | label: Taiwan election result | affects: inv_002 post_election_dynamics
UNKNOWN | id:unk_003 | label: US carrier group | STATUS: RESOLVED — WITHDRAWN TO GUAM | affects: state_003 inv_003
UNKNOWN | id:unk_004 | label: Whether PRC economic data triggers domestic political pressure | affects: state_008

---

## SECTION 8 — INTEGRITY

SEAL | case_id: TAIWAN-2026-STRAIT-TENSIONS
SEAL | sealed_at: 2026-03-10T12:00:00Z
SEAL | pla_vessels: 18
SEAL | sealed_scenario: scen_A
SEAL | replay_key: TAIWAN-2026-STRAIT-TENSIONS-PERTURBED

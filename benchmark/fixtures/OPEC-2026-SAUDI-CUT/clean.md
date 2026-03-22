# IOTA VERBUM CORE — Evidence Pack
## Case: OPEC-2026-SAUDI-CUT
## Timestamp: 2026-03-12T14:00:00Z
## Source: OPEC+ meeting minutes and energy market data

---

## SECTION 1 — ACTORS

ACTOR | id:actor_saudi | label: Saudi Arabia (Aramco / Ministry of Energy) | type: state_energy | status: ACTIVE
ACTOR | id:actor_russia_e | label: Russia (Rosneft / Ministry of Energy) | type: state_energy | status: ACTIVE
ACTOR | id:actor_opec | label: OPEC+ Alliance | type: cartel | status: ACTIVE
ACTOR | id:actor_iea | label: International Energy Agency | type: institution | status: ACTIVE
ACTOR | id:actor_usa_e | label: US Shale Producers | type: corporate_group | status: ACTIVE
ACTOR | id:actor_china_d | label: China (crude demand) | type: state | status: ACTIVE

---

## SECTION 2 — CURRENT STATES

STATE | id:state_001 | label: Brent crude at 78.40 USD — below Saudi fiscal breakeven 80 USD | time: 2026-03-12T14:00:00Z | certainty: HIGH | value: 78.40 | unit: USD
STATE | id:state_002 | label: Saudi production 9.2mbpd — current quota | time: 2026-03-12T00:00:00Z | certainty: HIGH | value: 9.2 | unit: mbpd
STATE | id:state_003 | label: Russia compliance 87% of agreed quota | time: 2026-03-10T00:00:00Z | certainty: MEDIUM | value: 87 | unit: PCT
STATE | id:state_004 | label: OPEC+ extraordinary meeting called for March 20 | time: 2026-03-11T00:00:00Z | certainty: HIGH
STATE | id:state_005 | label: China crude demand growth 1.1mbpd YoY — below 2025 pace | time: 2026-03-05T00:00:00Z | certainty: HIGH | value: 1.1 | unit: mbpd
STATE | id:state_006 | label: US shale production at 13.4mbpd — near record | time: 2026-03-10T00:00:00Z | certainty: HIGH | value: 13.4 | unit: mbpd
STATE | id:state_007 | label: Global oil demand IEA forecast 104.3mbpd 2026 | time: 2026-02-15T00:00:00Z | certainty: MEDIUM | value: 104.3 | unit: mbpd
STATE | id:state_008 | label: Saudi foreign reserves 432B USD — 6 months at current burn | time: 2026-03-01T00:00:00Z | certainty: HIGH | value: 432 | unit: BUSD

---

## SECTION 3 — EXPLICIT CAUSAL EDGES

EDGE | id:edge_001 | state_001 -[price below fiscal breakeven creates Saudi budget pressure]-> actor_saudi | strength: HIGH | lag: months
EDGE | id:edge_002 | state_005 -[weak China demand suppresses global price]-> state_001 | strength: HIGH | lag: weeks
EDGE | id:edge_003 | state_006 -[US shale at record offsets OPEC+ cuts]-> state_001 | strength: HIGH | lag: months
EDGE | id:edge_004 | state_003 -[Russian non-compliance undermines cut effectiveness]-> state_001 | strength: MEDIUM | lag: weeks
EDGE | id:edge_005 | state_004 -[extraordinary meeting signals cut announcement likely]-> actor_opec | strength: HIGH | lag: days
EDGE | id:edge_006 | state_008 -[large reserves give Saudi tolerance to wait]-> actor_saudi | strength: MEDIUM | lag: months

---

## SECTION 4 — TEMPORAL EVENT SEQUENCE

EVENT | id:event_t1 | time: 2026-01-15T00:00:00Z | label: Brent falls below 80 USD fiscal breakeven | actor: actor_saudi
EVENT | id:event_t2 | time: 2026-02-01T00:00:00Z | label: OPEC+ agrees on paper to existing quotas | actor: actor_opec
EVENT | id:event_t3 | time: 2026-03-05T00:00:00Z | label: China demand data disappoints | actor: actor_china_d
EVENT | id:event_t4 | time: 2026-03-11T00:00:00Z | label: Saudi calls extraordinary OPEC+ meeting | actor: actor_saudi
EVENT | id:event_t5 | time: 2026-03-12T14:00:00Z | label: Brent at 78.40 — Saudi fiscal pressure intensifying | actor: actor_saudi

---

## SECTION 5 — INVALIDATION CONDITIONS

INVALIDATION | id:inv_001 | trigger: OPEC+ agrees 1mbpd+ additional cut at March 20 meeting | effect: supply reduction supports price | switches: bullish_oil
INVALIDATION | id:inv_002 | trigger: China demand data surprise — revised up 0.5mbpd+ | effect: demand shock lifts price | switches: demand_driven_rally
INVALIDATION | id:inv_003 | trigger: OPEC+ meeting fails — no agreement | effect: market loses faith in cartel | switches: price_collapse
INVALIDATION | id:inv_004 | trigger: US sanctions relief on Iran | effect: Iranian barrels return to market | switches: additional_supply_bearish

---

## SECTION 6 — SCENARIO MAP

SCENARIO | id:scen_A | label: OPEC+ cut 1mbpd — Brent back to 83-87 | probability: 0.50 | trigger: Saudi fiscal pain forces coordinated cut | target: 83-87
SCENARIO | id:scen_B | label: Modest cut 0.5mbpd — Brent 79-82 | probability: 0.30 | trigger: Russia resists deeper cuts | target: 79-82
SCENARIO | id:scen_C | label: No agreement — Brent below 75 | probability: 0.20 | trigger: inv_003 | target: 70-75

SEALED_PATH | scenario: scen_A | confidence: 0.50 | sealed_at: 2026-03-12T14:00:00Z
REASONING: Saudi fiscal breakeven breached. Extraordinary meeting called. Saudi has historically cut when reserves are under pressure. Sealed: 1mbpd cut at March 20 meeting.

---

## SECTION 7 — UNKNOWNS

UNKNOWN | id:unk_001 | label: March 20 OPEC+ meeting outcome | affects: inv_001 inv_003 scen_A scen_C
UNKNOWN | id:unk_002 | label: Russia position at meeting | affects: state_003 scen_B
UNKNOWN | id:unk_003 | label: China Q1 demand final figures | affects: state_005
UNKNOWN | id:unk_004 | label: US shale response to price recovery | affects: state_006

---

## SECTION 8 — INTEGRITY

SEAL | case_id: OPEC-2026-SAUDI-CUT
SEAL | sealed_at: 2026-03-12T14:00:00Z
SEAL | brent_price: 78.40
SEAL | sealed_scenario: scen_A
SEAL | replay_key: OPEC-2026-SAUDI-CUT-A

# IOTA VERBUM CORE — Evidence Pack
## Case: GOLD-2026-ATH-BREAKOUT
## Timestamp: 2026-03-17T20:00:00Z
## Source: Gold futures and safe-haven flow data

---

## SECTION 1 — ACTORS

ACTOR | id:actor_gold | label: Gold (XAU/USD) | type: commodity | status: TRADING
ACTOR | id:actor_cbs | label: Central Banks (aggregate) | type: institution | status: ACTIVE
ACTOR | id:actor_fed | label: Federal Reserve | type: institution | status: ACTIVE
ACTOR | id:actor_em | label: Emerging Market Buyers | type: market_participant | status: ACTIVE
ACTOR | id:actor_etf_gold | label: Gold ETF holders (GLD/IAU) | type: fund_vehicle | status: ACTIVE
ACTOR | id:actor_dollar | label: US Dollar Index (DXY) | type: instrument | status: ACTIVE

---

## SECTION 2 — CURRENT STATES

STATE | id:state_001 | label: Gold at 3084 USD per troy oz — all-time high | time: 2026-03-17T20:00:00Z | certainty: HIGH | value: 3084 | unit: USD
STATE | id:state_002 | label: Gold up 14.2% YTD | time: 2026-03-17T20:00:00Z | certainty: HIGH | value: 14.2 | unit: PCT
STATE | id:state_003 | label: Central bank purchases 245 tonnes Q1 2026 | time: 2026-03-15T00:00:00Z | certainty: HIGH | value: 245 | unit: tonnes
STATE | id:state_004 | label: DXY at 103.2 — dollar moderately weak | time: 2026-03-17T20:00:00Z | certainty: HIGH | value: 103.2 | unit: index
STATE | id:state_005 | label: Real yields (10Y TIPS) at 1.42% | time: 2026-03-17T20:00:00Z | certainty: HIGH | value: 1.42 | unit: PCT
STATE | id:state_006 | label: Gold ETF holdings increased 38 tonnes this month | time: 2026-03-17T00:00:00Z | certainty: HIGH | value: 38 | unit: tonnes
STATE | id:state_007 | label: Iran ceasefire announced — geopolitical premium deflating | time: 2026-03-17T00:00:00Z | certainty: HIGH
STATE | id:state_008 | label: Gold RSI 71.4 — approaching overbought | time: 2026-03-17T20:00:00Z | certainty: HIGH | value: 71.4 | unit: RSI

---

## SECTION 3 — EXPLICIT CAUSAL EDGES

EDGE | id:edge_001 | state_003 -[central bank demand provides structural price floor]-> state_001 | strength: HIGH | lag: weeks
EDGE | id:edge_002 | state_004 -[weak dollar makes gold cheaper in foreign currencies]-> state_001 | strength: HIGH | lag: hours
EDGE | id:edge_003 | state_007 -[war risk drives safe-haven flows]-> actor_etf_gold | strength: LOW | note: CEASEFIRE | lag: hours
EDGE | id:edge_004 | state_006 -[ETF inflows add buy pressure]-> state_001 | strength: MEDIUM | lag: days
EDGE | id:edge_005 | state_005 -[positive real yields create opportunity cost for gold]-> state_001 | strength: MEDIUM | lag: days
EDGE | id:edge_006 | state_008 -[RSI near overbought signals near-term pullback risk]-> actor_etf_gold | strength: MEDIUM | lag: days

---

## SECTION 4 — TEMPORAL EVENT SEQUENCE

EVENT | id:event_t1 | time: 2026-01-01T00:00:00Z | label: Gold starts year at 2701 | actor: actor_gold
EVENT | id:event_t2 | time: 2026-01-20T00:00:00Z | label: US-Iran war escalates — gold spikes | actor: actor_gold
EVENT | id:event_t3 | time: 2026-02-15T00:00:00Z | label: Central bank purchase pace accelerates | actor: actor_cbs
EVENT | id:event_t4 | time: 2026-03-10T00:00:00Z | label: Gold breaks above previous ATH 2950 | actor: actor_gold
EVENT | id:event_t5 | time: 2026-03-17T20:00:00Z | label: Gold closes at new ATH 3084 | actor: actor_gold

---

## SECTION 5 — INVALIDATION CONDITIONS

INVALIDATION | id:inv_001 | trigger: Iran ceasefire announced | effect: geopolitical premium deflates | switches: correction | STATUS: FIRED
INVALIDATION | id:inv_002 | trigger: Fed signals rate cuts | effect: real yields fall — gold supported | switches: bullish_acceleration
INVALIDATION | id:inv_003 | trigger: DXY rallies above 106 | effect: dollar strength suppresses gold | switches: bearish
INVALIDATION | id:inv_004 | trigger: Gold closes below 3000 round number support | effect: ATH breakout fails | switches: rejection

---

## SECTION 6 — SCENARIO MAP

SCENARIO | id:scen_A | label: ATH continuation toward 3200 | probability: 0.55 | trigger: CB buying + war premium + weak dollar persist | target: 3150-3250
SCENARIO | id:scen_B | label: Overbought consolidation 2950-3084 | probability: 0.30 | trigger: RSI mean reversion without fundamental change | target: 2950-3084
SCENARIO | id:scen_C | label: War-end correction | probability: 0.15 | trigger: inv_001 fires | target: 2750-2900

SEALED_PATH | scenario: scen_A | confidence: 0.55 | STATUS: PARTIALLY_INVALIDATED | sealed_at: 2026-03-17T20:00:00Z
REASONING: All three structural drivers aligned: CB demand, war premium, dollar weakness. RSI overbought risk acknowledged but overridden by structural flows. Sealed path: ATH continuation.

---

## SECTION 7 — UNKNOWNS

UNKNOWN | id:unk_001 | label: Iran conflict | STATUS: RESOLVED — CEASEFIRE | affects: inv_001 state_007
UNKNOWN | id:unk_002 | label: Q1 CB purchase data final figures | affects: state_003
UNKNOWN | id:unk_003 | label: Whether RSI pullback materialises before next leg | affects: scen_B
UNKNOWN | id:unk_004 | label: DXY direction after next Fed meeting | affects: state_004 inv_003

---

## SECTION 8 — INTEGRITY

SEAL | case_id: GOLD-2026-ATH-BREAKOUT
SEAL | sealed_at: 2026-03-17T20:00:00Z
SEAL | gold_price: 3084
SEAL | sealed_scenario: scen_A
SEAL | replay_key: GOLD-2026-ATH-BREAKOUT-PERTURBED

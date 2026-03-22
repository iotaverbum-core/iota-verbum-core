# IOTA VERBUM CORE — Evidence Pack
## Case: BTC-2026-ETF-FLOWS
## Timestamp: 2026-03-18T23:59:00Z
## Source: Bitcoin ETF flow data and on-chain analytics

---

## SECTION 1 — ACTORS

ACTOR | id:actor_btc | label: Bitcoin | type: asset | status: TRADING
ACTOR | id:actor_etf | label: Spot Bitcoin ETFs (aggregate) | type: fund_vehicle | status: ACTIVE
ACTOR | id:actor_blackrock | label: BlackRock IBIT | type: etf_issuer | status: ACTIVE
ACTOR | id:actor_miners | label: Bitcoin Miners | type: market_participant | status: ACTIVE
ACTOR | id:actor_institutions | label: Institutional Allocators | type: market_participant | status: ACTIVE
ACTOR | id:actor_whales | label: On-chain Whales (>1000 BTC) | type: market_participant | status: ACTIVE

---

## SECTION 2 — CURRENT STATES

STATE | id:state_001 | label: BTC price 84210 USD | time: 2026-03-18T23:59:00Z | certainty: HIGH | value: 84210 | unit: USD
STATE | id:state_002 | label: BTC down 18.4% from cycle high 103200 | time: 2026-03-18T00:00:00Z | certainty: HIGH | value: -18.4 | unit: PCT
STATE | id:state_003 | label: ETF inflow streak BROKEN — net outflow 287M USD today | time: 2026-03-18T23:59:00Z | certainty: HIGH | value: -287 | unit: MUSD | note: OUTFLOW
STATE | id:state_004 | label: IBIT daily outflow 156M USD today | time: 2026-03-18T23:59:00Z | certainty: HIGH | value: -156 | unit: MUSD
STATE | id:state_005 | label: Aggregate ETF AUM 87.3B USD | time: 2026-03-18T23:59:00Z | certainty: HIGH | value: 87.3 | unit: BUSD
STATE | id:state_006 | label: Miner capitulation signal — hash rate down 8% | time: 2026-03-15T00:00:00Z | certainty: MEDIUM | value: -8 | unit: PCT
STATE | id:state_007 | label: Whale accumulation — 14200 BTC added to cold storage this week | time: 2026-03-18T00:00:00Z | certainty: HIGH | value: 14200 | unit: BTC
STATE | id:state_008 | label: BTC dominance 58.3% | time: 2026-03-18T23:59:00Z | certainty: HIGH | value: 58.3 | unit: PCT
STATE | id:state_009 | label: Funding rate positive 0.012% — mild long bias | time: 2026-03-18T23:59:00Z | certainty: HIGH | value: 0.012 | unit: PCT
STATE | id:state_010 | label: 200-week SMA support at 71400 USD | time: 2026-03-18T00:00:00Z | certainty: HIGH | value: 71400 | unit: USD

---

## SECTION 3 — EXPLICIT CAUSAL EDGES

EDGE | id:edge_001 | state_003 -[sustained ETF inflows create structural buy pressure]-> state_001 | strength: HIGH | lag: hours
EDGE | id:edge_002 | state_004 -[IBIT inflows signal institutional demand]-> actor_institutions | strength: HIGH | lag: hours
EDGE | id:edge_003 | state_007 -[whale accumulation reduces liquid supply]-> state_001 | strength: HIGH | lag: days
EDGE | id:edge_004 | state_006 -[miner capitulation historically precedes bottoms]-> actor_miners | strength: MEDIUM | lag: weeks
EDGE | id:edge_005 | state_009 -[mild long bias — not overleveraged]-> state_001 | strength: MEDIUM | lag: hours
EDGE | id:edge_006 | state_010 -[200-week SMA historical bull market support]-> actor_whales | strength: HIGH | lag: days

---

## SECTION 4 — TEMPORAL EVENT SEQUENCE

EVENT | id:event_t1 | time: 2026-01-10T00:00:00Z | label: BTC peaks at 103200 | actor: actor_btc
EVENT | id:event_t2 | time: 2026-02-01T00:00:00Z | label: Macro sell-off begins — BTC drops with risk assets | actor: actor_btc
EVENT | id:event_t3 | time: 2026-03-05T00:00:00Z | label: ETF inflows resume after 3-day outflow streak | actor: actor_etf
EVENT | id:event_t4 | time: 2026-03-15T00:00:00Z | label: Miner capitulation signal detected on-chain | actor: actor_miners
EVENT | id:event_t5 | time: 2026-03-18T23:59:00Z | label: 14th consecutive ETF inflow day — 412M from IBIT alone | actor: actor_blackrock

---

## SECTION 5 — INVALIDATION CONDITIONS

INVALIDATION | id:inv_001 | trigger: ETF inflow streak breaks | effect: structural demand thesis weakened | switches: distribution | STATUS: FIRED
INVALIDATION | id:inv_002 | trigger: BTC closes below 200-week SMA 71400 | effect: major bull market support broken | switches: bearish_macro
INVALIDATION | id:inv_003 | trigger: Whale wallets show net distribution | effect: supply-side thesis reverses | switches: sell_pressure
INVALIDATION | id:inv_004 | trigger: BTC reclaims 90000 | effect: psychological resistance cleared | switches: bullish_momentum

---

## SECTION 6 — SCENARIO MAP

SCENARIO | id:scen_A | label: Accumulation bottom — rally to 95000 | probability: 0.50 | trigger: ETF inflows + whale accumulation continue | target: 90000-95000
SCENARIO | id:scen_B | label: Consolidation range 78000-88000 | probability: 0.30 | trigger: Inflows moderate but no outflows | target: 78000-88000
SCENARIO | id:scen_C | label: Breakdown to 200-week SMA | probability: 0.20 | trigger: inv_001 + macro deterioration | target: 71000-75000

SEALED_PATH | scenario: scen_A | confidence: 0.50 | STATUS: INVALIDATED | sealed_at: 2026-03-18T23:59:00Z
REASONING: 14-day ETF inflow streak with accelerating IBIT volumes. Whale accumulation at scale. Miner capitulation historically a bottom signal. Sealed path: accumulation phase — expect recovery toward 95000 within 30 days.

---

## SECTION 7 — UNKNOWNS

UNKNOWN | id:unk_001 | label: ETF inflow streak | STATUS: RESOLVED — BROKEN DAY 15 | affects: scen_A scen_B
UNKNOWN | id:unk_002 | label: Macro risk-off event this week (Fed, CPI) | affects: inv_002
UNKNOWN | id:unk_003 | label: Miner selling pressure from capitulation | affects: state_001
UNKNOWN | id:unk_004 | label: Whether whale accumulation is new or existing wallets | affects: state_007

---

## SECTION 8 — INTEGRITY

SEAL | case_id: BTC-2026-ETF-FLOWS
SEAL | sealed_at: 2026-03-18T23:59:00Z
SEAL | btc_price: 84210
SEAL | sealed_scenario: scen_A
SEAL | replay_key: BTC-2026-ETF-FLOWS-C-PERTURBED

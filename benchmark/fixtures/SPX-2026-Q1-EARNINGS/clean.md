# IOTA VERBUM CORE — Evidence Pack
## Case: SPX-2026-Q1-EARNINGS
## Timestamp: 2026-03-20T21:00:00Z
## Source: Q1 2026 Earnings Season Evidence

---

## SECTION 1 — ACTORS

ACTOR | id:actor_spx | label: S&P 500 Index | type: market_index | status: TRADING
ACTOR | id:actor_megacap | label: Mega-Cap Tech (MAG7) | type: sector_group | status: ACTIVE
ACTOR | id:actor_fed | label: Federal Reserve | type: institution | status: ACTIVE
ACTOR | id:actor_analysts | label: Wall Street Analysts | type: market_participant | status: ACTIVE
ACTOR | id:actor_retail | label: Retail Investors | type: market_participant | status: ACTIVE
ACTOR | id:actor_treasury | label: US Treasury (10Y Yield) | type: instrument | status: ACTIVE

---

## SECTION 2 — CURRENT STATES

STATE | id:state_001 | label: SPX at 5612.45 | time: 2026-03-20T21:00:00Z | certainty: HIGH | value: 5612.45 | unit: USD
STATE | id:state_002 | label: SPX YTD down 6.2% | time: 2026-03-20T21:00:00Z | certainty: HIGH | value: -6.2 | unit: PCT
STATE | id:state_003 | label: MAG7 blended EPS growth 18.3% YoY | time: 2026-03-20T00:00:00Z | certainty: HIGH | value: 18.3 | unit: PCT
STATE | id:state_004 | label: Forward P/E 21.4x — elevated vs 10yr avg 17.8x | time: 2026-03-20T00:00:00Z | certainty: HIGH | value: 21.4 | unit: multiple
STATE | id:state_005 | label: 10Y Treasury yield 4.71% | time: 2026-03-20T21:00:00Z | certainty: HIGH | value: 4.71 | unit: PCT
STATE | id:state_006 | label: SPX EPS estimates Q1 2026 consensus +14.2% YoY | time: 2026-03-15T00:00:00Z | certainty: HIGH | value: 14.2 | unit: PCT
STATE | id:state_007 | label: 3 of 7 MAG7 names have reported — all beat estimates | time: 2026-03-20T00:00:00Z | certainty: HIGH | value: 3 | unit: count
STATE | id:state_008 | label: Average beat magnitude 4.1% above estimate | time: 2026-03-20T00:00:00Z | certainty: HIGH | value: 4.1 | unit: PCT
STATE | id:state_009 | label: SPX 50-day SMA at 5724.10 — index below it | time: 2026-03-20T21:00:00Z | certainty: HIGH | value: 5724.10 | unit: USD
STATE | id:state_010 | label: VIX 22.4 — moderate fear | time: 2026-03-20T21:00:00Z | certainty: HIGH | value: 22.4 | unit: index

---

## SECTION 3 — EXPLICIT CAUSAL EDGES

EDGE | id:edge_001 | state_003 -[strong EPS growth supports premium valuation]-> state_004 | strength: HIGH | lag: weeks
EDGE | id:edge_002 | state_005 -[high yields compete with equities for capital]-> state_002 | strength: HIGH | lag: days
EDGE | id:edge_003 | state_006 -[high consensus estimate creates high bar to beat]-> state_008 | strength: MEDIUM | lag: days
EDGE | id:edge_004 | state_007 -[early beats build confidence in season]-> actor_retail | strength: MEDIUM | lag: hours
EDGE | id:edge_005 | state_009 -[below 50SMA signals short-term bearish regime]-> actor_analysts | strength: HIGH | lag: hours
EDGE | id:edge_006 | state_010 -[moderate VIX — no panic, but no complacency]-> actor_retail | strength: MEDIUM | lag: hours

---

## SECTION 4 — TEMPORAL EVENT SEQUENCE

EVENT | id:event_t1 | time: 2026-01-15T00:00:00Z | label: Q1 earnings season opens — financials first | actor: actor_spx
EVENT | id:event_t2 | time: 2026-02-10T00:00:00Z | label: MAG7 reports begin — first 3 beat estimates | actor: actor_megacap
EVENT | id:event_t3 | time: 2026-03-01T00:00:00Z | label: Fed holds rates — inflation sticky | actor: actor_fed
EVENT | id:event_t4 | time: 2026-03-15T00:00:00Z | label: Consensus EPS estimates revised up slightly | actor: actor_analysts
EVENT | id:event_t5 | time: 2026-03-20T21:00:00Z | label: SPX closes at 5612 — 4th MAG7 name reports after bell | actor: actor_spx

---

## SECTION 5 — INVALIDATION CONDITIONS

INVALIDATION | id:inv_001 | trigger: 4th MAG7 name misses estimates | effect: earnings narrative breaks | switches: bearish_acceleration
INVALIDATION | id:inv_002 | trigger: 10Y yield spikes above 5.0% | effect: rate pressure overwhelms earnings | switches: risk_off
INVALIDATION | id:inv_003 | trigger: SPX reclaims 50-day SMA on volume | effect: technical regime flips | switches: bullish_reclaim
INVALIDATION | id:inv_004 | trigger: Fed hints at rate cut | effect: yield pressure relieved | switches: risk_on

---

## SECTION 6 — SCENARIO MAP

SCENARIO | id:scen_A | label: Earnings carry rally | probability: 0.45 | trigger: 4th MAG7 beats + SPX reclaims 50SMA | target: 5750-5850
SCENARIO | id:scen_B | label: Sideways chop | probability: 0.35 | trigger: Mixed beats + yield stays elevated | target: 5550-5650
SCENARIO | id:scen_C | label: Earnings-driven selloff | probability: 0.20 | trigger: inv_001 fires — miss breaks narrative | target: 5400-5500

SEALED_PATH | scenario: scen_A | confidence: 0.45 | sealed_at: 2026-03-20T21:00:00Z
REASONING: 3 of 3 early MAG7 beats with strong magnitude. Earnings season tracking above consensus. Technical weakness offset by fundamental momentum. Sealed path: earnings carry — expect SPX to reclaim 50SMA within 5 sessions if 4th name beats.

---

## SECTION 7 — UNKNOWNS

UNKNOWN | id:unk_001 | label: 4th MAG7 earnings result (reports after bell today) | affects: inv_001 scen_A scen_C
UNKNOWN | id:unk_002 | label: Remaining 4 MAG7 beat rates | affects: scen_A scen_B
UNKNOWN | id:unk_003 | label: Whether 10Y yield breaks 4.75% resistance | affects: inv_002
UNKNOWN | id:unk_004 | label: Q2 guidance from MAG7 names | affects: state_004

---

## SECTION 8 — INTEGRITY

SEAL | case_id: SPX-2026-Q1-EARNINGS
SEAL | sealed_at: 2026-03-20T21:00:00Z
SEAL | spx_price: 5612.45
SEAL | sealed_scenario: scen_A
SEAL | replay_key: SPX-2026-Q1-EARNINGS-A

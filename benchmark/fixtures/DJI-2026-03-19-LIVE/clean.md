# IOTA VERBUM CORE — Evidence Pack
## Case: DJI-2026-03-19-LIVE
## Timestamp: 2026-03-19T18:35:00Z
## Source: Live Dow Jones intraday market data — March 19 2026

---

## SECTION 1 — ACTORS

ACTOR | id:actor_dji | label: Dow Jones Industrial Average | type: index | status: TRADING
ACTOR | id:actor_fed | label: Federal Reserve | type: institution | status: ACTIVE
ACTOR | id:actor_inst | label: Institutional Investors | type: market_participant | status: ACTIVE
ACTOR | id:actor_retail | label: Retail Traders | type: market_participant | status: ACTIVE
ACTOR | id:actor_algo | label: Algorithmic Trading Systems | type: system | status: ACTIVE
ACTOR | id:actor_iran | label: US-Iran War | type: geopolitical_event | status: ACTIVE

---

## SECTION 2 — CURRENT STATES

STATE | id:state_001 | label: DJI current price 45,914.40 — down 0.67% on day | time: 2026-03-19T18:35:00Z | certainty: HIGH | value: 45914.40 | unit: USD
STATE | id:state_002 | label: DJI opened at 46,913.93 — gap-up of 688 points from prior close | time: 2026-03-19T09:30:00Z | certainty: HIGH | value: 46913.93 | unit: USD
STATE | id:state_003 | label: DJI intraday reversal of 999 points from open high to current price | time: 2026-03-19T18:35:00Z | certainty: HIGH | value: 999 | unit: USD_points
STATE | id:state_004 | label: DJI 200-day SMA at 46,528.97 — price 614 points below | time: 2026-03-19T18:35:00Z | certainty: HIGH | value: 46528.97 | unit: USD
STATE | id:state_005 | label: DJI RSI at 29.16 — deeply oversold | time: 2026-03-19T18:35:00Z | certainty: HIGH | value: 29.16 | unit: RSI
STATE | id:state_006 | label: DJI 2026 annual low at 46,193.06 — tested intraday | time: 2026-03-19T18:35:00Z | certainty: HIGH | value: 46193.06 | unit: USD
STATE | id:state_007 | label: DJI down 4.47% YTD | time: 2026-03-19T18:35:00Z | certainty: HIGH | value: -4.47 | unit: PCT
STATE | id:state_008 | label: Brent crude elevated near 100 USD — war-driven inflation | time: 2026-03-19T00:00:00Z | certainty: HIGH | value: 100 | unit: USD
STATE | id:state_009 | label: Federal Reserve held rates at March 2026 meeting | time: 2026-03-19T00:00:00Z | certainty: HIGH
STATE | id:state_010 | label: US-Iran war active — elevated geopolitical risk | time: 2026-03-19T00:00:00Z | certainty: HIGH
STATE | id:state_011 | label: Prior session decline 768 points — March 18 2026 | time: 2026-03-18T21:00:00Z | certainty: HIGH | value: 768 | unit: USD_points
STATE | id:state_012 | label: DJI 52-week range 36,611.78 to 50,512.79 | time: 2026-03-19T18:35:00Z | certainty: HIGH

---

## SECTION 3 — EXPLICIT CAUSAL EDGES

EDGE | id:edge_001 | actor_iran -[war drives Brent crude toward 100 USD]-> state_008 | strength: HIGH | lag: days
EDGE | id:edge_002 | state_008 -[elevated oil sustains inflation above Fed target]-> state_009 | strength: HIGH | lag: weeks
EDGE | id:edge_003 | state_009 -[rate hold removes primary upside catalyst]-> state_001 | strength: HIGH | lag: days
EDGE | id:edge_004 | state_011 -[prior session break below 200-day SMA triggers algo sells]-> actor_algo | strength: HIGH | lag: hours
EDGE | id:edge_005 | actor_algo -[systematic sell programs accelerate decline]-> state_001 | strength: HIGH | lag: minutes
EDGE | id:edge_006 | state_002 -[gap-up creates distribution opportunity for institutions]-> actor_inst | strength: HIGH | lag: minutes
EDGE | id:edge_007 | actor_inst -[institutional distribution into retail buying fails the gap]-> state_003 | strength: HIGH | lag: hours
EDGE | id:edge_008 | state_006 -[2026 low under pressure signals prior support becoming resistance]-> state_001 | strength: MEDIUM | lag: hours

---

## SECTION 4 — TEMPORAL EVENT SEQUENCE

EVENT | id:event_t1 | time: 2026-01-20T00:00:00Z | label: US-Iran war escalates — Brent spikes | actor: actor_iran
EVENT | id:event_t2 | time: 2026-03-01T00:00:00Z | label: Fed holds rates — inflation above target | actor: actor_fed
EVENT | id:event_t3 | time: 2026-03-18T09:30:00Z | label: DJI declines 768 points — breaks 200-day SMA at 46,528.97 | actor: actor_dji
EVENT | id:event_t4 | time: 2026-03-18T21:00:00Z | label: 2026 annual low established at 46,193.06 | actor: actor_dji
EVENT | id:event_t5 | time: 2026-03-19T09:30:00Z | label: DJI gaps up 688 points to 46,913.93 — retail buys | actor: actor_retail
EVENT | id:event_t6 | time: 2026-03-19T10:30:00Z | label: Institutional distribution into gap-up — rally fails | actor: actor_inst
EVENT | id:event_t7 | time: 2026-03-19T18:35:00Z | label: DJI reverses 999 points to 45,914.40 — 2026 low tested | actor: actor_dji

---

## SECTION 5 — INVALIDATION CONDITIONS

INVALIDATION | id:inv_001 | trigger: Iran ceasefire announced | effect: war risk premium removed — Brent falls — inflation outlook improves — bearish macro thesis broken | switches: bullish_reversal
INVALIDATION | id:inv_002 | trigger: Fed signals emergency rate cut | effect: primary upside catalyst restored — institutional buying resumes | switches: bullish_reversal
INVALIDATION | id:inv_003 | trigger: DJI closes above 200-day SMA 46,528.97 | effect: bearish technical regime invalidated — algo sell programs reverse | switches: neutral_recovery
INVALIDATION | id:inv_004 | trigger: Power-hour short covering drives close above 46,193.06 | effect: 2026 low holds as support — bears lose momentum into next session | switches: temporary_relief

---

## SECTION 6 — SCENARIO MAP

SCENARIO | id:scen_A | label: Bearish continuation — close below 2026 low | probability: 0.55 | trigger: Institutional pressure persists through close | target: 45,700-45,900
SCENARIO | id:scen_B | label: Power-hour relief — close holds above 46,193 | probability: 0.30 | trigger: Short covering and rebalancing in final 30 minutes | target: 46,000-46,200
SCENARIO | id:scen_C | label: Macro reversal — war premium removed | probability: 0.15 | trigger: inv_001 fires | target: 47,000-48,000

SEALED_PATH | scenario: scen_A | confidence: 0.55 | sealed_at: 2026-03-19T18:35:00Z
REASONING: Gap-up failed completely. 999-point intraday reversal is institutional distribution signature not capitulation. 200-day SMA at 46,528.97 acted as resistance. RSI 29.16 is oversold but not extreme — more downside structurally possible. 2026 low at 46,193.06 under pressure. Causal chain from war through oil through Fed hold through deleveraging intact. Sealed path: bearish continuation, close target 45,700-45,900.

---

## SECTION 7 — UNKNOWNS

UNKNOWN | id:unk_001 | label: Iran conflict trajectory — any ceasefire headline today | affects: inv_001 state_010 state_008
UNKNOWN | id:unk_002 | label: Fed speaker comments this afternoon | affects: state_009 inv_002
UNKNOWN | id:unk_003 | label: Power-hour institutional rebalancing direction 15:30-16:00 ET | affects: scen_B inv_004
UNKNOWN | id:unk_004 | label: Whether 2026 low 46,193.06 holds or breaks on closing print | affects: scen_A scen_B state_006

---

## SECTION 8 — INTEGRITY

SEAL | case_id: DJI-2026-03-19-LIVE
SEAL | sealed_at: 2026-03-19T18:35:00Z
SEAL | dji_price: 45914.40
SEAL | sealed_scenario: scen_A
SEAL | replay_key: DJI-2026-03-19-LIVE-B

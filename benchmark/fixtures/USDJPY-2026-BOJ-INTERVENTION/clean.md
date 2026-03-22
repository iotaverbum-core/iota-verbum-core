# IOTA VERBUM CORE — Evidence Pack
## Case: USDJPY-2026-BOJ-INTERVENTION
## Timestamp: 2026-03-16T08:00:00Z
## Source: FX market data and Bank of Japan communications

---

## SECTION 1 — ACTORS

ACTOR | id:actor_usdjpy | label: USD/JPY Exchange Rate | type: fx_pair | status: TRADING
ACTOR | id:actor_boj | label: Bank of Japan | type: central_bank | status: ACTIVE
ACTOR | id:actor_fed | label: Federal Reserve | type: central_bank | status: ACTIVE
ACTOR | id:actor_mof | label: Japan Ministry of Finance | type: institution | status: ACTIVE
ACTOR | id:actor_carry | label: Carry Trade Participants | type: market_participant | status: ACTIVE
ACTOR | id:actor_exporters | label: Japanese Exporters | type: corporate | status: ACTIVE

---

## SECTION 2 — CURRENT STATES

STATE | id:state_001 | label: USD/JPY at 151.82 — near intervention zone | time: 2026-03-16T08:00:00Z | certainty: HIGH | value: 151.82 | unit: JPY
STATE | id:state_002 | label: USD/JPY up 8.3% YTD | time: 2026-03-16T08:00:00Z | certainty: HIGH | value: 8.3 | unit: PCT
STATE | id:state_003 | label: BOJ held rates at 0.25% March meeting | time: 2026-03-12T00:00:00Z | certainty: HIGH | value: 0.25 | unit: PCT
STATE | id:state_004 | label: Fed-BOJ rate differential 5.25% | time: 2026-03-16T00:00:00Z | certainty: HIGH | value: 5.25 | unit: PCT
STATE | id:state_005 | label: MOF verbal intervention at 150 — ignored by market | time: 2026-03-10T00:00:00Z | certainty: HIGH | value: 150 | unit: JPY
STATE | id:state_006 | label: Carry trade net long USD/JPY position near multi-year high | time: 2026-03-15T00:00:00Z | certainty: MEDIUM
STATE | id:state_007 | label: Japan CPI 3.1% — above BOJ 2% target | time: 2026-03-05T00:00:00Z | certainty: HIGH | value: 3.1 | unit: PCT
STATE | id:state_008 | label: Prior intervention level 152 — historically triggers action | time: 2026-03-16T00:00:00Z | certainty: HIGH | value: 152 | unit: JPY

---

## SECTION 3 — EXPLICIT CAUSAL EDGES

EDGE | id:edge_001 | state_004 -[rate differential drives carry trade inflows to USD]-> state_001 | strength: HIGH | lag: days
EDGE | id:edge_002 | state_006 -[crowded carry trade amplifies moves]-> state_001 | strength: HIGH | lag: hours
EDGE | id:edge_003 | state_007 -[above-target inflation creates BOJ rate hike pressure]-> actor_boj | strength: MEDIUM | lag: weeks
EDGE | id:edge_004 | state_005 -[verbal intervention without action loses credibility]-> actor_carry | strength: LOW | lag: hours
EDGE | id:edge_005 | state_008 -[152 level triggers historical BOJ action threshold]-> actor_mof | strength: HIGH | lag: hours

---

## SECTION 4 — TEMPORAL EVENT SEQUENCE

EVENT | id:event_t1 | time: 2026-01-01T00:00:00Z | label: USD/JPY at 140.2 — year opens | actor: actor_usdjpy
EVENT | id:event_t2 | time: 2026-02-01T00:00:00Z | label: BOJ holds rates — yen weakens | actor: actor_boj
EVENT | id:event_t3 | time: 2026-03-10T00:00:00Z | label: MOF verbal intervention at 150 | actor: actor_mof
EVENT | id:event_t4 | time: 2026-03-12T00:00:00Z | label: BOJ holds again — rate differential unchanged | actor: actor_boj
EVENT | id:event_t5 | time: 2026-03-16T08:00:00Z | label: USD/JPY reaches 151.82 — approaching 152 threshold | actor: actor_usdjpy

---

## SECTION 5 — INVALIDATION CONDITIONS

INVALIDATION | id:inv_001 | trigger: BOJ surprise rate hike | effect: rate differential narrows — carry unwind | switches: yen_rally
INVALIDATION | id:inv_002 | trigger: MOF actual FX intervention (not verbal) | effect: sharp yen appreciation | switches: intervention_spike
INVALIDATION | id:inv_003 | trigger: USD/JPY breaks 152 without response | effect: MOF credibility collapse | switches: accelerated_yen_weakness
INVALIDATION | id:inv_004 | trigger: Fed signals rate cut | effect: differential narrows from USD side | switches: carry_unwind

---

## SECTION 6 — SCENARIO MAP

SCENARIO | id:scen_A | label: MOF intervenes at 152 — sharp yen rally | probability: 0.45 | trigger: 152 breaks — MOF forced to act | target: 146-148
SCENARIO | id:scen_B | label: Slow grind to 153-155 | probability: 0.35 | trigger: MOF credibility collapses — carry continues | target: 153-155
SCENARIO | id:scen_C | label: BOJ surprise hike triggers unwind | probability: 0.20 | trigger: inv_001 fires | target: 143-146

SEALED_PATH | scenario: scen_A | confidence: 0.45 | sealed_at: 2026-03-16T08:00:00Z
REASONING: 152 is historically the MOF action threshold. Carry trade crowded. Rate differential unchanged. Sealed path: expect MOF hard intervention as USD/JPY tests 152.

---

## SECTION 7 — UNKNOWNS

UNKNOWN | id:unk_001 | label: Whether MOF intervenes at 152 or allows breach | affects: scen_A scen_B inv_002
UNKNOWN | id:unk_002 | label: BOJ next rate decision date and guidance | affects: inv_001 scen_C
UNKNOWN | id:unk_003 | label: Size of carry trade unwind if intervention fires | affects: scen_A target
UNKNOWN | id:unk_004 | label: US inflation print this week | affects: state_004 inv_004

---

## SECTION 8 — INTEGRITY

SEAL | case_id: USDJPY-2026-BOJ-INTERVENTION
SEAL | sealed_at: 2026-03-16T08:00:00Z
SEAL | usdjpy: 151.82
SEAL | sealed_scenario: scen_A
SEAL | replay_key: USDJPY-2026-BOJ-INTERVENTION-A

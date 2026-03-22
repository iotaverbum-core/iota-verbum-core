# IOTA VERBUM CORE — Evidence Pack
## Case: IRAN-NUCLEAR-2026-TALKS
## Timestamp: 2026-03-05T16:00:00Z
## Source: IAEA reports and diplomatic communications

---

## SECTION 1 — ACTORS

ACTOR | id:actor_iran | label: Islamic Republic of Iran | type: state | status: ACTIVE
ACTOR | id:actor_iaea | label: International Atomic Energy Agency | type: institution | status: ACTIVE
ACTOR | id:actor_usa | label: United States (State Department) | type: state | status: ACTIVE
ACTOR | id:actor_eu3 | label: EU3 (France, Germany, UK) | type: state_group | status: ACTIVE
ACTOR | id:actor_israel | label: State of Israel | type: state | status: ACTIVE
ACTOR | id:actor_russia_cn | label: Russia and China (JCPOA partners) | type: state_group | status: ACTIVE

---

## SECTION 2 — CURRENT STATES

STATE | id:state_001 | label: Iran uranium enrichment REACHES 90% — weapons-grade threshold CROSSED | time: 2026-03-05T00:00:00Z | certainty: HIGH | value: 90 | unit: PCT
STATE | id:state_002 | label: Iran stockpile 42kg of 84%-enriched uranium | time: 2026-03-01T00:00:00Z | certainty: HIGH | value: 42 | unit: kg
STATE | id:state_003 | label: Breakout time estimate 2-3 weeks | time: 2026-03-05T00:00:00Z | certainty: MEDIUM | value: 2.5 | unit: weeks
STATE | id:state_004 | label: Geneva talks in 3rd round — partial agreement on inspections | time: 2026-03-04T00:00:00Z | certainty: HIGH | value: 3 | unit: round
STATE | id:state_005 | label: US sanctions relief offer: 7B USD frozen funds | time: 2026-02-28T00:00:00Z | certainty: HIGH | value: 7 | unit: BUSD
STATE | id:state_006 | label: IAEA access — 6 of 12 requested sites inspected | time: 2026-03-01T00:00:00Z | certainty: HIGH | value: 6 | unit: sites
STATE | id:state_007 | label: Israel readiness posture elevated — strike planning active | time: 2026-03-05T00:00:00Z | certainty: MEDIUM
STATE | id:state_008 | label: Iranian economy contraction -2.1% under sanctions | time: 2026-01-15T00:00:00Z | certainty: HIGH | value: -2.1 | unit: PCT

---

## SECTION 3 — EXPLICIT CAUSAL EDGES

EDGE | id:edge_001 | state_008 -[economic pain creates deal incentive for Iran]-> actor_iran | strength: HIGH | lag: weeks
EDGE | id:edge_002 | state_007 -[Israeli strike threat creates time pressure on deal]-> actor_iran | strength: HIGH | lag: weeks
EDGE | id:edge_003 | state_005 -[sanctions relief offer creates tangible negotiating incentive]-> actor_iran | strength: HIGH | lag: days
EDGE | id:edge_004 | state_003 -[short breakout time creates urgency for US and Israel]-> actor_usa | strength: HIGH | lag: weeks
EDGE | id:edge_005 | state_004 -[partial inspection agreement signals Iran willingness]-> actor_eu3 | strength: MEDIUM | lag: days
EDGE | id:edge_006 | state_001 -[84% enrichment near weapons grade creates red line pressure]-> actor_israel | strength: HIGH | lag: days

---

## SECTION 4 — TEMPORAL EVENT SEQUENCE

EVENT | id:event_t1 | time: 2026-01-10T00:00:00Z | label: Geneva talks open — first round | actor: actor_usa
EVENT | id:event_t2 | time: 2026-01-30T00:00:00Z | label: Iran enrichment reaches 84% — reported by IAEA | actor: actor_iaea
EVENT | id:event_t3 | time: 2026-02-15T00:00:00Z | label: US tables sanctions relief offer | actor: actor_usa
EVENT | id:event_t4 | time: 2026-02-28T00:00:00Z | label: Partial inspection agreement in round 3 | actor: actor_eu3
EVENT | id:event_t5 | time: 2026-03-05T16:00:00Z | label: Round 4 begins — enrichment freeze on table | actor: actor_iran

---

## SECTION 5 — INVALIDATION CONDITIONS

INVALIDATION | id:inv_001 | trigger: Iran enrichment reaches 90% | effect: red line crossed — Israeli strike imminent | switches: military_action | STATUS: FIRED
INVALIDATION | id:inv_002 | trigger: Framework deal agreed | effect: enrichment freeze — breakout clock paused | switches: diplomatic_resolution
INVALIDATION | id:inv_003 | trigger: Iran withdraws from talks | effect: deal collapses — accelerated weaponization | switches: breakdown
INVALIDATION | id:inv_004 | trigger: IAEA granted full 12-site access | effect: verification possible — deal viable | switches: deal_acceleration

---

## SECTION 6 — SCENARIO MAP

SCENARIO | id:scen_A | label: Framework deal in round 4-5 | probability: 0.40 | trigger: Economic pain + time pressure converge | target: enrichment_freeze_agreed
SCENARIO | id:scen_B | label: Talks extend — slow progress | probability: 0.35 | trigger: Partial agreements but no framework | target: round_6_7_needed
SCENARIO | id:scen_C | label: Talks collapse — Israeli strike | probability: 0.25 | trigger: inv_001 or inv_003 | target: military_action

SEALED_PATH | scenario: scen_A | confidence: 0.40 | STATUS: SEVERELY_WEAKENED | sealed_at: 2026-03-05T16:00:00Z
REASONING: Economic pressure on Iran intensifying. Partial inspection agreement signals flexibility. US offer on table. Time pressure from Israeli posture. Sealed: framework deal likely within 2 rounds.

---

## SECTION 7 — UNKNOWNS

UNKNOWN | id:unk_001 | label: Round 4 outcome — Iran position on enrichment freeze | affects: scen_A inv_002
UNKNOWN | id:unk_002 | label: Iran enrichment threshold | STATUS: RESOLVED — 90% CROSSED | affects: inv_001 scen_C
UNKNOWN | id:unk_003 | label: Israeli military readiness timeline | affects: state_007 inv_001
UNKNOWN | id:unk_004 | label: Russia-China pressure on Iran to deal | affects: actor_iran

---

## SECTION 8 — INTEGRITY

SEAL | case_id: IRAN-NUCLEAR-2026-TALKS
SEAL | sealed_at: 2026-03-05T16:00:00Z
SEAL | enrichment_pct: 84
SEAL | sealed_scenario: scen_A
SEAL | replay_key: IRAN-NUCLEAR-2026-TALKS-PERTURBED

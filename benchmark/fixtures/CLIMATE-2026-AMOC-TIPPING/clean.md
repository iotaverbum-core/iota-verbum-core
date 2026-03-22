# IOTA VERBUM CORE — Evidence Pack
## Case: CLIMATE-2026-AMOC-TIPPING
## Timestamp: 2026-03-03T11:00:00Z
## Source: Nature Climate Change and oceanographic data

---

## SECTION 1 — ACTORS

ACTOR | id:actor_research | label: Copenhagen Climate Research Group | type: research_institution | status: ACTIVE
ACTOR | id:actor_ipcc | label: IPCC Working Group I | type: institution | status: ACTIVE
ACTOR | id:actor_govts | label: G20 Climate Ministries | type: state_group | status: ACTIVE
ACTOR | id:actor_argo | label: Argo Float Network (ocean sensors) | type: monitoring_system | status: ACTIVE
ACTOR | id:actor_unfccc | label: UNFCCC / COP process | type: institution | status: ACTIVE

---

## SECTION 2 — CURRENT STATES

STATE | id:state_001 | label: AMOC strength index 17.2 Sverdrup — 15% below 1950-2000 mean | time: 2026-03-01T00:00:00Z | certainty: HIGH | value: 17.2 | unit: Sv
STATE | id:state_002 | label: AMOC decline rate 0.8 Sv per decade — accelerating vs 0.5 Sv prior estimate | time: 2026-03-01T00:00:00Z | certainty: MEDIUM | value: 0.8 | unit: Sv_per_decade
STATE | id:state_003 | label: Tipping threshold estimated 15-17 Sv in new study | time: 2026-03-03T00:00:00Z | certainty: MEDIUM | value: 15.5 | unit: Sv
STATE | id:state_004 | label: Current AMOC 1.7 Sv above lower tipping bound | time: 2026-03-03T00:00:00Z | certainty: MEDIUM | value: 1.7 | unit: Sv
STATE | id:state_005 | label: Global mean temperature anomaly +1.54C above pre-industrial | time: 2026-01-15T00:00:00Z | certainty: HIGH | value: 1.54 | unit: degC
STATE | id:state_006 | label: Greenland melt freshwater flux 2.3x 2000-level | time: 2026-02-01T00:00:00Z | certainty: HIGH | value: 2.3 | unit: multiple
STATE | id:state_007 | label: Prior IPCC AR6 estimated tipping at 12-15 Sv — new study revises upward | time: 2026-03-03T00:00:00Z | certainty: HIGH
STATE | id:state_008 | label: Study peer-reviewed in Nature Climate Change — high credibility | time: 2026-03-03T00:00:00Z | certainty: HIGH

---

## SECTION 3 — EXPLICIT CAUSAL EDGES

EDGE | id:edge_001 | state_002 -[accelerating decline narrows timeline to tipping]-> state_004 | strength: HIGH | lag: decades
EDGE | id:edge_002 | state_006 -[Greenland melt freshwater disrupts AMOC density gradient]-> state_001 | strength: HIGH | lag: years
EDGE | id:edge_003 | state_005 -[warming accelerates Greenland melt]-> state_006 | strength: HIGH | lag: years
EDGE | id:edge_004 | state_007 -[upward threshold revision means tipping closer than IPCC modeled]-> actor_ipcc | strength: HIGH | lag: months
EDGE | id:edge_005 | state_003 -[proximity to threshold creates urgency for mitigation]-> actor_govts | strength: HIGH | lag: months
EDGE | id:edge_006 | state_008 -[Nature Climate Change publication validates findings]-> actor_ipcc | strength: HIGH | lag: months

---

## SECTION 4 — TEMPORAL EVENT SEQUENCE

EVENT | id:event_t1 | time: 2025-01-01T00:00:00Z | label: Copenhagen team begins new AMOC analysis with expanded Argo data | actor: actor_research
EVENT | id:event_t2 | time: 2025-09-01T00:00:00Z | label: Preliminary findings show higher threshold than IPCC estimate | actor: actor_research
EVENT | id:event_t3 | time: 2026-01-15T00:00:00Z | label: Paper submitted to Nature Climate Change | actor: actor_research
EVENT | id:event_t4 | time: 2026-02-28T00:00:00Z | label: Paper accepted after peer review | actor: actor_journals
EVENT | id:event_t5 | time: 2026-03-03T11:00:00Z | label: Published — AMOC tipping closer than previously modeled | actor: actor_research

---

## SECTION 5 — INVALIDATION CONDITIONS

INVALIDATION | id:inv_001 | trigger: AMOC measurement falls below 16 Sv | effect: tipping point imminent — emergency protocol | switches: tipping_imminent
INVALIDATION | id:inv_002 | trigger: Independent replication fails to confirm higher threshold | effect: study findings disputed | switches: scientific_controversy
INVALIDATION | id:inv_003 | trigger: Emergency IPCC special report convened | effect: policy urgency dramatically elevated | switches: policy_emergency
INVALIDATION | id:inv_004 | trigger: Greenland melt flux exceeds 3x 2000-level | effect: AMOC destabilization accelerates | switches: accelerated_timeline

---

## SECTION 6 — SCENARIO MAP

SCENARIO | id:scen_A | label: Findings accepted — IPCC revises models — policy response | probability: 0.55 | trigger: Independent replication confirms threshold | target: ipcc_revision_2027
SCENARIO | id:scen_B | label: Scientific debate — replication pending | probability: 0.30 | trigger: Other groups dispute methodology | target: 2-3_year_consensus_building
SCENARIO | id:scen_C | label: AMOC collapses within 20 years | probability: 0.15 | trigger: inv_001 + inv_004 | target: tipping_point_crossed

SEALED_PATH | scenario: scen_A | confidence: 0.55 | sealed_at: 2026-03-03T11:00:00Z
REASONING: Nature Climate Change credibility. Expanded Argo dataset. Threshold upward revision demands IPCC response. Sealed: findings accepted and models revised.

---

## SECTION 7 — UNKNOWNS

UNKNOWN | id:unk_001 | label: Independent replication studies — MIT, NOAA | affects: inv_002 scen_B
UNKNOWN | id:unk_002 | label: Next Argo float measurement cycle | affects: state_001
UNKNOWN | id:unk_003 | label: IPCC response timeline | affects: scen_A inv_003
UNKNOWN | id:unk_004 | label: 2026 Greenland summer melt season | affects: state_006 inv_004

---

## SECTION 8 — INTEGRITY

SEAL | case_id: CLIMATE-2026-AMOC-TIPPING
SEAL | sealed_at: 2026-03-03T11:00:00Z
SEAL | amoc_sv: 17.2
SEAL | sealed_scenario: scen_A
SEAL | replay_key: CLIMATE-2026-AMOC-TIPPING-A

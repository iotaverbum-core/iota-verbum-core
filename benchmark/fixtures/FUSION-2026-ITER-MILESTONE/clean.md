# IOTA VERBUM CORE — Evidence Pack
## Case: FUSION-2026-ITER-MILESTONE
## Timestamp: 2026-03-14T15:00:00Z
## Source: ITER Organization and Science journal

---

## SECTION 1 — ACTORS

ACTOR | id:actor_iter | label: ITER Organization | type: research_institution | status: ACTIVE
ACTOR | id:actor_doe | label: US Department of Energy | type: government | status: ACTIVE
ACTOR | id:actor_private | label: Commonwealth Fusion / TAE / Helion | type: corporate_group | status: ACTIVE
ACTOR | id:actor_iaea_e | label: IAEA Energy Division | type: institution | status: ACTIVE
ACTOR | id:actor_nif | label: National Ignition Facility (NIF) | type: research_institution | status: ACTIVE

---

## SECTION 2 — CURRENT STATES

STATE | id:state_001 | label: ITER plasma current reached 7.5MA — 75% of design target 10MA | time: 2026-03-14T00:00:00Z | certainty: HIGH | value: 7.5 | unit: MA
STATE | id:state_002 | label: Plasma confinement time 8.2 seconds — exceeds 6s milestone | time: 2026-03-14T00:00:00Z | certainty: HIGH | value: 8.2 | unit: seconds
STATE | id:state_003 | label: Q factor 0.18 — energy output 18% of energy input | time: 2026-03-14T00:00:00Z | certainty: HIGH | value: 0.18 | unit: ratio
STATE | id:state_004 | label: Q>1 (net energy gain) target for 2035 | time: 2026-03-14T00:00:00Z | certainty: MEDIUM | value: 1.0 | unit: ratio_target
STATE | id:state_005 | label: Commonwealth Fusion SPARC targeting Q>2 by 2028 | time: 2026-03-01T00:00:00Z | certainty: MEDIUM
STATE | id:state_006 | label: NIF achieved Q=1.5 in laser fusion December 2022 | time: 2022-12-05T00:00:00Z | certainty: HIGH | value: 1.5 | unit: ratio
STATE | id:state_007 | label: ITER superconducting magnet performance nominal | time: 2026-03-14T00:00:00Z | certainty: HIGH
STATE | id:state_008 | label: Total ITER project cost 22B USD — 65% spent | time: 2026-03-14T00:00:00Z | certainty: HIGH | value: 22 | unit: BUSD

---

## SECTION 3 — EXPLICIT CAUSAL EDGES

EDGE | id:edge_001 | state_001 -[75% plasma current validates magnet and heating systems]-> actor_iter | strength: HIGH | lag: months
EDGE | id:edge_002 | state_002 -[8.2s confinement exceeds milestone — magnetic geometry confirmed]-> actor_iter | strength: HIGH | lag: months
EDGE | id:edge_003 | state_003 -[Q=0.18 — physics progressing but far from breakeven]-> actor_doe | strength: HIGH | lag: years
EDGE | id:edge_004 | state_005 -[private sector race compresses timeline — ITER may be overtaken]-> actor_private | strength: MEDIUM | lag: years
EDGE | id:edge_005 | state_007 -[magnet performance validates SPARC-style HTS approach]-> actor_private | strength: HIGH | lag: months
EDGE | id:edge_006 | state_006 -[NIF Q>1 precedent shows ignition possible in principle]-> actor_iter | strength: MEDIUM | lag: continuous

---

## SECTION 4 — TEMPORAL EVENT SEQUENCE

EVENT | id:event_t1 | time: 2025-06-01T00:00:00Z | label: ITER first plasma — tokamak operational | actor: actor_iter
EVENT | id:event_t2 | time: 2025-12-01T00:00:00Z | label: Magnet systems fully commissioned | actor: actor_iter
EVENT | id:event_t3 | time: 2026-02-01T00:00:00Z | label: Plasma current ramped to 5MA | actor: actor_iter
EVENT | id:event_t4 | time: 2026-03-10T00:00:00Z | label: Confinement time exceeds 6s milestone | actor: actor_iter
EVENT | id:event_t5 | time: 2026-03-14T15:00:00Z | label: 7.5MA achieved — 75% of design current | actor: actor_iter

---

## SECTION 5 — INVALIDATION CONDITIONS

INVALIDATION | id:inv_001 | trigger: ITER achieves 10MA design current | effect: full design validation — Q>1 pathway confirmed | switches: q1_pathway_confirmed
INVALIDATION | id:inv_002 | trigger: Commonwealth Fusion SPARC achieves Q>1 before ITER | effect: private sector overtakes ITER — public funding question | switches: private_fusion_leads
INVALIDATION | id:inv_003 | trigger: Major magnet failure or plasma disruption damage | effect: multi-year delay and budget overrun | switches: project_crisis
INVALIDATION | id:inv_004 | trigger: Q factor reaches 0.5 | effect: halfway to breakeven — major milestone | switches: q_progress_milestone

---

## SECTION 6 — SCENARIO MAP

SCENARIO | id:scen_A | label: ITER reaches 10MA by 2027 — Q>1 on track 2035 | probability: 0.50 | trigger: Progressive plasma current increase | target: q1_by_2035
SCENARIO | id:scen_B | label: Private fusion (SPARC) achieves Q>1 first (2028) | probability: 0.30 | trigger: inv_002 | target: private_fusion_commercial_2030s
SCENARIO | id:scen_C | label: ITER delay — budget overrun — 2040+ for Q>1 | probability: 0.20 | trigger: inv_003 or technical setbacks | target: delayed_timeline

SEALED_PATH | scenario: scen_A | confidence: 0.50 | sealed_at: 2026-03-14T15:00:00Z
REASONING: 75% design current achieved. Confinement time milestone exceeded. Magnets nominal. Progressive path to 10MA and Q>1 by 2035 intact. Sealed: scen_A.

---

## SECTION 7 — UNKNOWNS

UNKNOWN | id:unk_001 | label: Timeline to reach 10MA full design current | affects: scen_A inv_001
UNKNOWN | id:unk_002 | label: SPARC first plasma date and Q results | affects: inv_002 scen_B
UNKNOWN | id:unk_003 | label: Tritium breeding module performance | affects: long_term_fuel_supply
UNKNOWN | id:unk_004 | label: Political support for ITER budget completion | affects: state_008 scen_C

---

## SECTION 8 — INTEGRITY

SEAL | case_id: FUSION-2026-ITER-MILESTONE
SEAL | sealed_at: 2026-03-14T15:00:00Z
SEAL | plasma_ma: 7.5
SEAL | sealed_scenario: scen_A
SEAL | replay_key: FUSION-2026-ITER-MILESTONE-A

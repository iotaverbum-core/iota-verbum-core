# IOTA VERBUM CORE — Evidence Pack
## Case: PATENT-2026-NOVALINK-V-SYNTHEX
## Timestamp: 2026-03-06T14:00:00Z
## Source: USDC Delaware case files and prior art database

---

## SECTION 1 — ACTORS

ACTOR | id:actor_nova | label: Novalink Technologies (plaintiff) | type: corporation | status: ACTIVE
ACTOR | id:actor_synthex | label: Synthex Systems (defendant) | type: corporation | status: ACTIVE
ACTOR | id:actor_judge | label: Judge Patricia Okafor (USDC Delaware) | type: judiciary | status: ACTIVE
ACTOR | id:actor_ptab | label: Patent Trial and Appeal Board | type: institution | status: ACTIVE
ACTOR | id:actor_experts | label: Technical Expert Witnesses | type: individual_group | status: ACTIVE
ACTOR | id:actor_jury | label: Jury (selected) | type: institution | status: ACTIVE

---

## SECTION 2 — CURRENT STATES

STATE | id:state_001 | label: Trial date set — April 14 2026 | time: 2026-03-06T00:00:00Z | certainty: HIGH
STATE | id:state_002 | label: Novalink patent US 11,847,392 — AI-assisted network routing | time: 2026-03-06T00:00:00Z | certainty: HIGH
STATE | id:state_003 | label: Synthex IPR petition at PTAB — ALL 8 claims invalidated — PTAB final written decision | time: 2026-02-20T00:00:00Z | certainty: HIGH | value: 8 | unit: claims_invalidated
STATE | id:state_004 | label: 0 remaining claims — ALL INVALIDATED — case collapses | time: 2026-03-06T00:00:00Z | certainty: HIGH | value: 340 | unit: MUSD
STATE | id:state_005 | label: Markman hearing complete — key term construed broadly | time: 2026-02-15T00:00:00Z | certainty: HIGH
STATE | id:state_006 | label: Synthex source code produced in discovery — contains 14 matching algorithm calls | time: 2026-03-01T00:00:00Z | certainty: HIGH | value: 14 | unit: calls
STATE | id:state_007 | label: Synthex prior art defense — cites 2018 MIT paper as anticipation | time: 2026-03-06T00:00:00Z | certainty: HIGH
STATE | id:state_008 | label: Novalink expert testimony scheduled April 15 | time: 2026-03-06T00:00:00Z | certainty: HIGH

---

## SECTION 3 — EXPLICIT CAUSAL EDGES

EDGE | id:edge_001 | state_005 -[broad claim construction favors Novalink — wider infringement scope]-> actor_nova | strength: HIGH | lag: weeks
EDGE | id:edge_002 | state_006 -[14 matching algorithm calls is strong infringement evidence]-> actor_jury | strength: HIGH | lag: weeks
EDGE | id:edge_003 | state_003 -[3 claims invalidated reduces damages scope]-> actor_nova | strength: MEDIUM | lag: weeks
EDGE | id:edge_004 | state_007 -[2018 MIT paper may create reasonable doubt on novelty]-> actor_jury | strength: MEDIUM | lag: weeks
EDGE | id:edge_005 | state_004 -[340M damages claim creates settlement incentive for Synthex]-> actor_synthex | strength: HIGH | lag: weeks
EDGE | id:edge_006 | state_005 -[broad construction may be challenged at CAFC on appeal]-> actor_ptab | strength: MEDIUM | lag: months

---

## SECTION 4 — TEMPORAL EVENT SEQUENCE

EVENT | id:event_t1 | time: 2025-01-10T00:00:00Z | label: Novalink files complaint in USDC Delaware | actor: actor_nova
EVENT | id:event_t2 | time: 2025-06-01T00:00:00Z | label: Synthex files IPR petition at PTAB | actor: actor_synthex
EVENT | id:event_t3 | time: 2026-02-15T00:00:00Z | label: Markman hearing — broad construction adopted | actor: actor_judge
EVENT | id:event_t4 | time: 2026-02-20T00:00:00Z | label: PTAB invalidates 3 of 8 claims | actor: actor_ptab
EVENT | id:event_t5 | time: 2026-03-06T14:00:00Z | label: Trial preparation — 5 weeks to April 14 | actor: actor_nova

---

## SECTION 5 — INVALIDATION CONDITIONS

INVALIDATION | id:inv_001 | trigger: PTAB invalidates remaining 5 claims | effect: all asserted claims eliminated — case collapses | switches: case_collapse | STATUS: FIRED
INVALIDATION | id:inv_002 | trigger: Synthex pays settlement before April 14 | effect: case resolved pre-trial | switches: settlement
INVALIDATION | id:inv_003 | trigger: Judge grants Synthex summary judgment on prior art | effect: case dismissed | switches: dismissal
INVALIDATION | id:inv_004 | trigger: Novalink expert testimony survives Daubert challenge | effect: technical infringement case fully presented | switches: full_trial

---

## SECTION 6 — SCENARIO MAP

SCENARIO | id:scen_A | label: Trial — Novalink jury verdict | probability: 0.45 | trigger: No settlement — trial proceeds April 14 | target: verdict_Q2_2026
SCENARIO | id:scen_B | label: Settlement before trial | probability: 0.40 | trigger: 340M exposure drives Synthex to settle | target: settlement_100-180M
SCENARIO | id:scen_C | label: Case collapses — prior art or PTAB | probability: 0.15 | trigger: inv_001 or inv_003 | target: case_dismissed

SEALED_PATH | scenario: scen_A | confidence: 0.45 | STATUS: INVALIDATED | sealed_at: 2026-03-06T14:00:00Z
REASONING: Broad construction advantage. Strong source code evidence. 5 claims survive. Trial date firm. Sealed: trial proceeds April 14.

---

## SECTION 7 — UNKNOWNS

UNKNOWN | id:unk_001 | label: Whether Synthex makes settlement offer before April 14 | affects: inv_002 scen_B
UNKNOWN | id:unk_002 | label: Strength of Novalink expert testimony | affects: inv_004 scen_A
UNKNOWN | id:unk_003 | label: MIT paper anticipation | STATUS: RESOLVED — PTAB accepted anticipation for all 8 claims | affects: state_007 inv_003
UNKNOWN | id:unk_004 | label: Jury composition and technical sophistication | affects: scen_A outcome

---

## SECTION 8 — INTEGRITY

SEAL | case_id: PATENT-2026-NOVALINK-V-SYNTHEX
SEAL | sealed_at: 2026-03-06T14:00:00Z
SEAL | damages_claim_MUSD: 340
SEAL | sealed_scenario: scen_A
SEAL | replay_key: PATENT-2026-NOVALINK-V-SYNTHEX-PERTURBED

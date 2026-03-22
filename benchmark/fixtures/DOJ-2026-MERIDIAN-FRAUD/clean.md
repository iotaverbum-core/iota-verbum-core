# IOTA VERBUM CORE — Evidence Pack
## Case: DOJ-2026-MERIDIAN-FRAUD
## Timestamp: 2026-03-02T10:00:00Z
## Source: DOJ investigation file and financial forensics

---

## SECTION 1 — ACTORS

ACTOR | id:actor_meridian | label: Meridian Capital Partners (defendant) | type: corporation | status: UNDER_INVESTIGATION
ACTOR | id:actor_ceo | label: Thomas Harlan (CEO) | type: individual | status: SUSPECT
ACTOR | id:actor_cfo | label: Rachel Voss (CFO) | type: individual | status: SUSPECT
ACTOR | id:actor_doj | label: DOJ Fraud Section | type: law_enforcement | status: ACTIVE
ACTOR | id:actor_sec | label: SEC Enforcement Division | type: regulator | status: ACTIVE
ACTOR | id:actor_whistle | label: Confidential Whistleblower (CW-1) | type: individual | status: COOPERATING

---

## SECTION 2 — CURRENT STATES

STATE | id:state_001 | label: Grand jury convened — 6 months into investigation | time: 2026-03-02T00:00:00Z | certainty: HIGH | value: 6 | unit: months
STATE | id:state_002 | label: 847M USD allegedly misappropriated from client accounts 2022-2025 | time: 2026-03-02T00:00:00Z | certainty: MEDIUM | value: 847 | unit: MUSD
STATE | id:state_003 | label: CW-1 testimony corroborated by 3 independent financial transactions | time: 2026-02-28T00:00:00Z | certainty: HIGH | value: 3 | unit: transactions
STATE | id:state_004 | label: Harlan personal account received 22M in unexplained wire transfers | time: 2026-02-15T00:00:00Z | certainty: HIGH | value: 22 | unit: MUSD
STATE | id:state_005 | label: Meridian external audit clean — no fraud detected 2022-2024 | time: 2026-03-02T00:00:00Z | certainty: HIGH
STATE | id:state_006 | label: Defense counsel claims CW-1 is disgruntled former employee | time: 2026-03-01T00:00:00Z | certainty: HIGH
STATE | id:state_007 | label: DOJ has forensic copy of Meridian servers — imaging complete | time: 2026-02-20T00:00:00Z | certainty: HIGH
STATE | id:state_008 | label: SEC parallel civil proceeding — asset freeze motion pending | time: 2026-03-02T00:00:00Z | certainty: HIGH

---

## SECTION 3 — EXPLICIT CAUSAL EDGES

EDGE | id:edge_001 | state_003 -[CW-1 corroboration strengthens credibility of testimony]-> actor_doj | strength: HIGH | lag: weeks
EDGE | id:edge_002 | state_004 -[unexplained wire transfers provide direct financial evidence]-> actor_doj | strength: HIGH | lag: weeks
EDGE | id:edge_003 | state_005 -[clean audit creates reasonable doubt — auditors may face scrutiny]-> actor_meridian | strength: MEDIUM | lag: months
EDGE | id:edge_004 | state_006 -[motive-to-lie argument weakens CW-1 if defense can prove hostility]-> actor_doj | strength: MEDIUM | lag: weeks
EDGE | id:edge_005 | state_007 -[server forensics may contain direct evidence of concealment]-> actor_doj | strength: HIGH | lag: weeks
EDGE | id:edge_006 | state_008 -[asset freeze would prevent dissipation of proceeds]-> actor_sec | strength: HIGH | lag: days

---

## SECTION 4 — TEMPORAL EVENT SEQUENCE

EVENT | id:event_t1 | time: 2025-09-01T00:00:00Z | label: CW-1 approaches DOJ with initial tip | actor: actor_whistle
EVENT | id:event_t2 | time: 2025-10-15T00:00:00Z | label: Grand jury convened | actor: actor_doj
EVENT | id:event_t3 | time: 2026-01-20T00:00:00Z | label: DOJ subpoenas Meridian servers | actor: actor_doj
EVENT | id:event_t4 | time: 2026-02-20T00:00:00Z | label: Server forensic imaging complete | actor: actor_doj
EVENT | id:event_t5 | time: 2026-03-02T10:00:00Z | label: DOJ internal review of forensic evidence underway | actor: actor_doj

---

## SECTION 5 — INVALIDATION CONDITIONS

INVALIDATION | id:inv_001 | trigger: Server forensics find deleted files — concealment confirmed | effect: obstruction charge added — evidence of consciousness of guilt | switches: obstruction_charged
INVALIDATION | id:inv_002 | trigger: CFO Voss flips — accepts plea and cooperates | effect: insider testimony from financial officer | switches: plea_cooperation
INVALIDATION | id:inv_003 | trigger: Defense produces legitimate source for 22M wire transfers | effect: key financial evidence neutralized | switches: financial_evidence_weakened
INVALIDATION | id:inv_004 | trigger: SEC asset freeze granted | effect: defendants cannot move funds — leverage for plea | switches: asset_freeze_active

---

## SECTION 6 — SCENARIO MAP

SCENARIO | id:scen_A | label: Indictment filed — Harlan and Voss charged | probability: 0.65 | trigger: Forensics + CW-1 + wire transfer evidence converge | target: indictment_Q2_2026
SCENARIO | id:scen_B | label: Plea negotiation — one or both cooperate | probability: 0.25 | trigger: inv_002 or asset freeze pressure | target: plea_agreement
SCENARIO | id:scen_C | label: Investigation stalls — insufficient evidence | probability: 0.10 | trigger: inv_003 + CW-1 credibility destroyed | target: no_charges

SEALED_PATH | scenario: scen_A | confidence: 0.65 | sealed_at: 2026-03-02T10:00:00Z
REASONING: Three independent transaction corroborations. 22M unexplained transfers. Forensics in hand. Strong DOJ posture. Sealed: indictment Q2 2026.

---

## SECTION 7 — UNKNOWNS

UNKNOWN | id:unk_001 | label: Content of Meridian server forensics | affects: inv_001 scen_A
UNKNOWN | id:unk_002 | label: Whether Voss will flip before indictment | affects: inv_002 scen_B
UNKNOWN | id:unk_003 | label: Legitimate explanation for 22M wire transfers | affects: inv_003 state_004
UNKNOWN | id:unk_004 | label: SEC asset freeze ruling | affects: inv_004 scen_B

---

## SECTION 8 — INTEGRITY

SEAL | case_id: DOJ-2026-MERIDIAN-FRAUD
SEAL | sealed_at: 2026-03-02T10:00:00Z
SEAL | alleged_misappropriation_MUSD: 847
SEAL | sealed_scenario: scen_A
SEAL | replay_key: DOJ-2026-MERIDIAN-FRAUD-A

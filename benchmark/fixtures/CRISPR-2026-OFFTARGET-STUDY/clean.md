# IOTA VERBUM CORE — Evidence Pack
## Case: CRISPR-2026-OFFTARGET-STUDY
## Timestamp: 2026-02-20T10:00:00Z
## Source: Nature Medicine peer review and genomics data

---

## SECTION 1 — ACTORS

ACTOR | id:actor_lab | label: Broad Institute Research Team | type: research_institution | status: ACTIVE
ACTOR | id:actor_fda_gene | label: FDA Center for Biologics (CBER) | type: regulator | status: ACTIVE
ACTOR | id:actor_vertex | label: Vertex Pharmaceuticals (Casgevy sponsor) | type: corporation | status: ACTIVE
ACTOR | id:actor_patients_s | label: Sickle cell / Beta-thal patients | type: population | status: ACTIVE
ACTOR | id:actor_journals | label: Nature Medicine / peer review | type: institution | status: ACTIVE
ACTOR | id:actor_competitors_c | label: Competing gene therapy developers | type: corporate_group | status: ACTIVE

---

## SECTION 2 — CURRENT STATES

STATE | id:state_001 | label: Off-target edit rate 0.003% per 1M base pairs — new assay method | time: 2026-02-20T00:00:00Z | certainty: HIGH | value: 0.003 | unit: PCT_per_Mbp
STATE | id:state_002 | label: Original approved Casgevy safety study used lower-sensitivity assay | time: 2026-02-20T00:00:00Z | certainty: HIGH
STATE | id:state_003 | label: 0.003% off-target rate below FDA genotoxicity threshold 0.01% | time: 2026-02-20T00:00:00Z | certainty: HIGH | value: 0.003 | unit: PCT_per_Mbp
STATE | id:state_004 | label: No off-target effects found in protein-coding regions | time: 2026-02-20T00:00:00Z | certainty: HIGH
STATE | id:state_005 | label: Study N=142 patients, 24-month follow-up, no adverse genomic events | time: 2026-02-20T00:00:00Z | certainty: HIGH | value: 142 | unit: patients
STATE | id:state_006 | label: New GUIDE-seq v3 assay 100x more sensitive than prior standard | time: 2026-02-20T00:00:00Z | certainty: HIGH | value: 100 | unit: fold
STATE | id:state_007 | label: Paper accepted Nature Medicine — embargo lifts March 1 | time: 2026-02-20T00:00:00Z | certainty: HIGH
STATE | id:state_008 | label: Casgevy approved for SCD and beta-thal — 1400 patients treated | time: 2026-02-01T00:00:00Z | certainty: HIGH | value: 1400 | unit: patients

---

## SECTION 3 — EXPLICIT CAUSAL EDGES

EDGE | id:edge_001 | state_003 -[rate below FDA threshold — safety profile maintained]-> actor_fda_gene | strength: HIGH | lag: months
EDGE | id:edge_002 | state_004 -[no coding region effects — oncogenic risk minimal]-> actor_fda_gene | strength: HIGH | lag: months
EDGE | id:edge_003 | state_005 -[24-month clean follow-up confirms clinical safety]-> actor_vertex | strength: HIGH | lag: months
EDGE | id:edge_004 | state_006 -[new assay may require retrospective safety review of all approved CRISPR drugs]-> actor_fda_gene | strength: MEDIUM | lag: months
EDGE | id:edge_005 | state_007 -[peer-reviewed publication adds credibility to safety claims]-> actor_journals | strength: HIGH | lag: weeks
EDGE | id:edge_006 | state_001 -[detectable off-target effects, even below threshold, will fuel public concern]-> actor_patients_s | strength: MEDIUM | lag: weeks

---

## SECTION 4 — TEMPORAL EVENT SEQUENCE

EVENT | id:event_t1 | time: 2023-12-08T00:00:00Z | label: Casgevy approved by FDA | actor: actor_fda_gene
EVENT | id:event_t2 | time: 2025-06-01T00:00:00Z | label: Broad Institute study begins with GUIDE-seq v3 | actor: actor_lab
EVENT | id:event_t3 | time: 2026-01-15T00:00:00Z | label: Results show sub-threshold off-target edits | actor: actor_lab
EVENT | id:event_t4 | time: 2026-02-15T00:00:00Z | label: Nature Medicine accepts paper | actor: actor_journals
EVENT | id:event_t5 | time: 2026-02-20T10:00:00Z | label: Pre-print released ahead of March 1 embargo lift | actor: actor_lab

---

## SECTION 5 — INVALIDATION CONDITIONS

INVALIDATION | id:inv_001 | trigger: Off-target rate revised upward above 0.01% threshold | effect: FDA genotoxicity threshold breached | switches: safety_review_triggered
INVALIDATION | id:inv_002 | trigger: Off-target edit found in tumor suppressor gene | effect: oncogenic risk — FDA review of all patients | switches: safety_crisis
INVALIDATION | id:inv_003 | trigger: FDA mandates new safety studies using GUIDE-seq v3 for all approved CRISPR | effect: industry-wide re-evaluation | switches: regulatory_overhaul
INVALIDATION | id:inv_004 | trigger: Peer review identifies methodological flaw | effect: paper retracted or major revision | switches: findings_invalid

---

## SECTION 6 — SCENARIO MAP

SCENARIO | id:scen_A | label: Safety confirmed — CRISPR field strengthened | probability: 0.60 | trigger: Final paper confirms sub-threshold with clean follow-up | target: field_advancement
SCENARIO | id:scen_B | label: Regulatory reassessment — new assay standard required | probability: 0.30 | trigger: inv_003 — FDA mandates GUIDE-seq v3 industry-wide | target: 12-18_month_review
SCENARIO | id:scen_C | label: Safety crisis | probability: 0.10 | trigger: inv_001 or inv_002 | target: fda_hold_on_crispr

SEALED_PATH | scenario: scen_A | confidence: 0.60 | sealed_at: 2026-02-20T10:00:00Z
REASONING: Rate below threshold. No coding region effects. Clean 24-month follow-up. Published in Nature Medicine. Sealed: safety confirmed, field advances.

---

## SECTION 7 — UNKNOWNS

UNKNOWN | id:unk_001 | label: Peer review final publication vs pre-print changes | affects: inv_004 scen_A
UNKNOWN | id:unk_002 | label: FDA response to new assay sensitivity | affects: inv_003 scen_B
UNKNOWN | id:unk_003 | label: Whether Vertex applies GUIDE-seq v3 retrospectively to treated patients | affects: state_008
UNKNOWN | id:unk_004 | label: Competitor CRISPR studies using new assay | affects: actor_competitors_c

---

## SECTION 8 — INTEGRITY

SEAL | case_id: CRISPR-2026-OFFTARGET-STUDY
SEAL | sealed_at: 2026-02-20T10:00:00Z
SEAL | off_target_rate: 0.003
SEAL | sealed_scenario: scen_A
SEAL | replay_key: CRISPR-2026-OFFTARGET-STUDY-A

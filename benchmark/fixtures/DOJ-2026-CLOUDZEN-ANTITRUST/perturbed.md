# IOTA VERBUM CORE — Evidence Pack
## Case: DOJ-2026-CLOUDZEN-ANTITRUST
## Timestamp: 2026-03-09T13:00:00Z
## Source: DOJ Antitrust Division investigation materials

---

## SECTION 1 — ACTORS

ACTOR | id:actor_cloudzen | label: CloudZen Technologies (subject) | type: corporation | status: UNDER_INVESTIGATION
ACTOR | id:actor_doj_at | label: DOJ Antitrust Division | type: law_enforcement | status: ACTIVE
ACTOR | id:actor_ftc | label: Federal Trade Commission | type: regulator | status: ACTIVE
ACTOR | id:actor_competitors_az | label: AWS / Azure / GCP | type: corporate_group | status: ACTIVE
ACTOR | id:actor_customers | label: Enterprise customers (SaaS dependent) | type: corporate_group | status: ACTIVE
ACTOR | id:actor_eu_dma | label: EU Digital Markets Act Enforcer | type: regulator | status: ACTIVE

---

## SECTION 2 — CURRENT STATES

STATE | id:state_001 | label: CloudZen market share enterprise cloud 68% — above 50% monopoly threshold | time: 2026-03-09T00:00:00Z | certainty: HIGH | value: 68 | unit: PCT
STATE | id:state_002 | label: CloudZen API lock-in — 89% of top 500 SaaS use CloudZen proprietary APIs | time: 2026-03-09T00:00:00Z | certainty: HIGH | value: 89 | unit: PCT
STATE | id:state_003 | label: CloudZen VOLUNTARILY reduces exit fees to 2023 levels — press release issued | time: 2026-02-15T00:00:00Z | certainty: HIGH | value: 340 | unit: PCT
STATE | id:state_004 | label: DOJ civil investigative demand issued — 18 months of documents requested | time: 2026-02-01T00:00:00Z | certainty: HIGH
STATE | id:state_005 | label: 3 customer declarations filed — describe inability to switch despite trying | time: 2026-03-07T00:00:00Z | certainty: HIGH | value: 3 | unit: declarations
STATE | id:state_006 | label: CloudZen CEO email — internal strategy memo re: exit fees | time: 2026-03-01T00:00:00Z | certainty: MEDIUM
STATE | id:state_007 | label: EU DMA investigation parallel — CloudZen designated gatekeeper | time: 2026-02-20T00:00:00Z | certainty: HIGH
STATE | id:state_008 | label: CloudZen market cap 1.2T USD | time: 2026-03-09T00:00:00Z | certainty: HIGH | value: 1.2 | unit: TUSD

---

## SECTION 3 — EXPLICIT CAUSAL EDGES

EDGE | id:edge_001 | state_001 -[68% market share establishes monopoly power prima facie]-> actor_doj_at | strength: HIGH | lag: months
EDGE | id:edge_002 | state_002 -[89% API dependency demonstrates anticompetitive lock-in]-> actor_doj_at | strength: HIGH | lag: months
EDGE | id:edge_003 | state_003 -[340% exit fee increase is exclusionary conduct evidence]-> actor_doj_at | strength: HIGH | lag: months
EDGE | id:edge_004 | state_005 -[customer declarations provide direct harm evidence]-> actor_doj_at | strength: HIGH | lag: months
EDGE | id:edge_005 | state_006 -[CEO email may demonstrate willful maintenance of monopoly]-> actor_doj_at | strength: MEDIUM | lag: months
EDGE | id:edge_006 | state_007 -[EU parallel proceeding increases pressure on CloudZen]-> actor_cloudzen | strength: HIGH | lag: months

---

## SECTION 4 — TEMPORAL EVENT SEQUENCE

EVENT | id:event_t1 | time: 2025-06-01T00:00:00Z | label: DOJ opens formal investigation | actor: actor_doj_at
EVENT | id:event_t2 | time: 2025-09-15T00:00:00Z | label: EU designates CloudZen as DMA gatekeeper | actor: actor_eu_dma
EVENT | id:event_t3 | time: 2026-02-01T00:00:00Z | label: CID issued — document production begins | actor: actor_doj_at
EVENT | id:event_t4 | time: 2026-03-01T00:00:00Z | label: Customer declarations filed | actor: actor_customers
EVENT | id:event_t5 | time: 2026-03-09T13:00:00Z | label: DOJ reviews CEO email strategy memo | actor: actor_doj_at

---

## SECTION 5 — INVALIDATION CONDITIONS

INVALIDATION | id:inv_001 | trigger: DOJ files complaint | effect: formal antitrust action begins | switches: litigation_commenced
INVALIDATION | id:inv_002 | trigger: CloudZen voluntarily reduces exit fees | effect: exclusionary conduct claim weakened | switches: remediation | STATUS: FIRED
INVALIDATION | id:inv_003 | trigger: CEO email proves willful monopoly maintenance | effect: strongest evidence standard met | switches: criminal_referral_possible
INVALIDATION | id:inv_004 | trigger: EU DMA enforcer imposes structural remedy | effect: EU precedent pressures US settlement | switches: structural_remedy_eu

---

## SECTION 6 — SCENARIO MAP

SCENARIO | id:scen_A | label: DOJ files complaint — major antitrust suit | probability: 0.55 | trigger: Document production + CEO email + customer harm converge | target: suit_filed_2026
SCENARIO | id:scen_B | label: Consent decree — behavioral remedies | probability: 0.30 | trigger: CloudZen negotiates before complaint | target: exit_fee_caps_api_access
SCENARIO | id:scen_C | label: Investigation stalls — market definition disputed | probability: 0.15 | trigger: CloudZen redefines relevant market | target: no_complaint

SEALED_PATH | scenario: scen_A | confidence: 0.55 | STATUS: WEAKENED | sealed_at: 2026-03-09T13:00:00Z
REASONING: Market share, lock-in, exit fee evidence all strong. Customer declarations. CEO email under review. EU pressure. Sealed: complaint filed in 2026.

---

## SECTION 7 — UNKNOWNS

UNKNOWN | id:unk_001 | label: CEO email content | affects: inv_003 scen_A
UNKNOWN | id:unk_002 | label: CloudZen response to CID — cooperation or resistance | affects: scen_A timeline
UNKNOWN | id:unk_003 | label: EU DMA remedy type and timing | affects: inv_004 scen_B
UNKNOWN | id:unk_004 | label: Whether DOJ defines market narrowly or broadly | affects: state_001 scen_C

---

## SECTION 8 — INTEGRITY

SEAL | case_id: DOJ-2026-CLOUDZEN-ANTITRUST
SEAL | sealed_at: 2026-03-09T13:00:00Z
SEAL | market_share_pct: 68
SEAL | sealed_scenario: scen_A
SEAL | replay_key: DOJ-2026-CLOUDZEN-ANTITRUST-PERTURBED

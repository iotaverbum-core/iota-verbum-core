# Claude 24-Case Production Probe Audit

Date: 2026-05-28

## Result

This probe evaluates the production path:

```text
Claude structured proposer -> RevisionDelta verifier -> deterministic ledger commit
```

The live Claude run completed on the existing CUC v4 24-case fixture set from
`benchmark/cuc_v4_candidate_params.json`.

## Live Run

Source summary:
`cuc-results/claude_24_production_probe/latest/summary.json`

Summary SHA-256:
`b2387ecd486b6cf0cc4825906c250e128b60f48b83f223876ec71b2878119fe6`

| Metric | Value |
| --- | ---: |
| Requested cases | 24 |
| Completed cases | 24 |
| JSON-valid deltas | 24 |
| Verifier accepted | 23 |
| Ledger committed | 23 |
| JSON valid rate | 100.0000% |
| Verifier acceptance rate | 95.8333% |
| Ledger commit rate | 95.8333% |
| Average similarity score | 76.86625% |

## Rejection Analysis

Rejected case:
`CUCV4-INVARIANT-01-COUNTERPARTY-RESPONSE-LEGAL-CONTRACT`

Verifier reason:
`missing_scenario_rank_changes:scenario:alternate`

The rejection was traced to a stale fixture-gold expectation, not to malformed
Claude output and not to a ledger failure. The clean and perturbed packs keep
`scenario:alternate` at rank `2`. The old gold delta incorrectly required
`scenario:alternate` to move from rank `2` to rank `1`. Claude omitted that
nonexistent rank change and instead tracked the rank movements present in the
actual fixture.

The corrected gold expectation is:

```json
[
  {"scenario_id": "scenario:primary", "before_rank": 1, "after_rank": 3},
  {"scenario_id": "scenario:bg_1", "before_rank": 3, "after_rank": 4},
  {"scenario_id": "scenario:hop3_escalation", "before_rank": null, "after_rank": 1}
]
```

Corrected expected delta SHA-256:
`44a137add9503b263b8bb66ac0e36f5a24ced1d8ac75f9309e82e54417b16d70`

## Corrected Offline Replay

Source summary:
`cuc-results/claude_24_production_probe/gold_corrected_replay/summary.json`

Summary SHA-256:
`bf5c53caf67c623156b9e04afd3a82894107b524a62605fb8965466a81c5f176`

This replay used the original live Claude `model_delta.json` outputs already on
disk. It did not make new API calls.

| Metric | Value |
| --- | ---: |
| Requested cases | 24 |
| Completed cases | 24 |
| JSON-valid deltas | 24 |
| Verifier accepted | 24 |
| Ledger committed | 24 |
| JSON valid rate | 100.0000% |
| Verifier acceptance rate | 100.0000% |
| Ledger commit rate | 100.0000% |
| Average similarity score | 77.087083% |

Corrected case ledger record:

| Field | SHA-256 / path |
| --- | --- |
| bundle_sha256 | `a7721ed2dcd6bd3c86b08baf1c5849fe26182ace1d5323180240f4eb7a118a51` |
| output_sha256 | `aea41f5eca071caa37b3b14ef715cdd2971033b5f0eba1dfe728ed377dbbfbd4` |
| attestation_sha256 | `d03b5dfe8a52b23d058b63a107be9911da0093d925e73e727295224174d60fcc` |
| run_dir | `cuc-results/claude_24_production_probe/gold_corrected_replay/ledger/a7721ed2dcd6bd3c86b08baf1c5849fe26182ace1d5323180240f4eb7a118a51` |

## Claim Boundary

Safe external claim:

> In a 24-case CUC v4 production probe, Claude Sonnet 4.6 produced 24/24
> JSON-valid structured deltas. The live run committed 23/24 accepted deltas to
> a SHA-256 attested ledger. The single rejection was traced to a stale fixture
> rank expectation; replaying the original live outputs against the corrected
> fixture gold yields 24/24 verifier acceptance and 24/24 ledger commitment with
> no additional API calls.

Do not state that the raw live run was 24/24 before mentioning the fixture-gold
correction. The defensible result is 23/24 live, 24/24 corrected offline replay
using the same live Claude outputs.


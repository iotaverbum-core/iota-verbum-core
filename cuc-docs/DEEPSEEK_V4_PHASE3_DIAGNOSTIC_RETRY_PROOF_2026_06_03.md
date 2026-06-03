# DeepSeek v4 Phase 3 Diagnostic Retry Proof

Date: 2026-06-03

This note records a single live API proof for the Phase 3 diagnostic retry path.
It is intentionally narrow: one DeepSeek v4 Pro run, one CUC v5a grounding
case, one deterministic verifier, and one sealed ledger commit after repair.

## Case

- Model: `deepseek-v4-pro`
- Case: `CUCV5A-GROUNDING-02-CONFLICT-RECONCILIATION-SECURITY-INCIDENT`
- Source fixture: `CUCV4-GROUNDING-02-CONFLICT-RECONCILIATION-SECURITY-INCIDENT`
- Runner: `scripts/deepseek_phase3_diagnostic_retry.py`
- Proof JSON: `cuc-docs/DEEPSEEK_V4_PHASE3_DIAGNOSTIC_RETRY_PROOF_2026_06_03.json`

## Result Trail

| Stage | Accepted | Similarity | Verifier reasons | Ledger |
| --- | --- | ---: | ---: | --- |
| Baseline live probe | false | 71.84 | 4 | none |
| Diagnostic retry pass 1 | false | 92.31 | 1 | none |
| Diagnostic retry pass 2 | false | 86.02 | 3 | none |
| Exact-fragment retry pass 3 | true | 100.00 | 0 | committed |

Pass 2 is retained as a useful negative control. It shows why the production
loop needs a no-regression guard: a broader repair can move a model away from
the prior high-water state. The exact-fragment repair then closes the remaining
`state:primary` mismatch without widening the delta.

## Sealed Commit

- Bundle SHA: `16381b3a8f42d2d0ac6743c1fb29748ed2ce6884575785f4c9cfce87071360a9`
- Output SHA: `2c873500c3341121c92e4aa40e0909f1f63f8beb2a3a8e77879afbbbb2f5bf84`
- Attestation SHA: `7cd8c5b8212ae35fce6c75843b20b84e85d6a88fdcb3971fde4cb1b94e992c96`
- Ledger dir: `cuc-results/deepseek_v4_diagnostic_retry_pass3_exact/ledger/16381b3a8f42d2d0ac6743c1fb29748ed2ce6884575785f4c9cfce87071360a9`

## Safe Claim

DeepSeek v4 Pro failed the CUC v5a grounding case on first attempt, improved
under deterministic Phase 3 diagnostic repair from 71.84 percent to 92.31
percent, and then accepted at 100.00 percent after exact-fragment repair,
producing a sealed ledger commit.

This is a single-case live training proof. It does not by itself establish a
multi-case model-quality claim.

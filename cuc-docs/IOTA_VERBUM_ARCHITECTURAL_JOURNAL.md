# Iota Verbum Architectural Journal

## 2026-06-03 - Phase 3 Claude Batch Retry Harness

The Phase 3 diagnostic retry path now has a 64-case batch wrapper for the
canonical CUC v5 params file. The wrapper discovers all records from
`benchmark/cuc_v5_64_params.json`, materializes runtime fixtures from the sealed
embedded packs when physical fixture directories are absent, and delegates live
retry execution to `scripts/claude_phase3_diagnostic_retry.py`.

The current checked-in proof is a dry-run discovery and artifact-shape proof,
not a paid Claude execution. It confirms the wrapper can enumerate and emit one
per-case result for all 64 cases without making model calls.

- Proof artifact: `cuc-docs/CLAUDE_PHASE3_BATCH_RETRY_PROOF_2026_06_03.json`
- Per-case artifacts: `cuc-docs/batch_retry_results/*_retry_result.json`
- Total cases discovered: 64
- Dry-run classifier breakdown: ACCEPTED=64, UNCLASSIFIED=0
- Bundle SHA: `1bd913b80b49e6cc772fbf90c9447c333ec0da779bc6eb98f13d5a5fe5e7a3fe`
- Attestation SHA: `8dd51ef83cc2daceff697d7f619071df52d4d6d54a72d78ca3ea81640ed83838`

Operational boundary: live training evidence still requires baseline failed
artifacts for the target cases and a non-dry-run Claude invocation. The batch
runner is deliberately structured so dry-run paths do not consume model budget,
and live paths reuse the single-case diagnostic retry implementation rather than
duplicating proposer or verifier behavior.

## 2026-06-03 - DeepSeek v4 Live Diagnostic Retry Proof

The Phase 3 diagnostic retry path now has a single-case live DeepSeek v4 Pro
proof on `CUCV5A-GROUNDING-02-CONFLICT-RECONCILIATION-SECURITY-INCIDENT`.
The model failed the baseline live probe at 71.84 percent similarity with four
verifier reason families, improved to 92.31 percent with one remaining verifier
issue after the first diagnostic retry, and accepted at 100.00 percent after
the exact-fragment diagnostic repair.

Pass 2 is preserved as a regression example: the score fell from 92.31 percent
to 86.02 percent when the repair was not yet constrained tightly enough. The
retry runners now emit best-so-far artifacts so the next baseline can be the
highest verifier state rather than the latest attempt.

- Proof note: `cuc-docs/DEEPSEEK_V4_PHASE3_DIAGNOSTIC_RETRY_PROOF_2026_06_03.md`
- Proof JSON: `cuc-docs/DEEPSEEK_V4_PHASE3_DIAGNOSTIC_RETRY_PROOF_2026_06_03.json`
- Accepted ledger bundle SHA: `16381b3a8f42d2d0ac6743c1fb29748ed2ce6884575785f4c9cfce87071360a9`
- Accepted output SHA: `2c873500c3341121c92e4aa40e0909f1f63f8beb2a3a8e77879afbbbb2f5bf84`
- Accepted attestation SHA: `7cd8c5b8212ae35fce6c75843b20b84e85d6a88fdcb3971fde4cb1b94e992c96`

# Claude Phase 3 Diagnostic Retry Proof - 2026-06-01

Named evidence artifact:
`CLAUDE_PHASE3_DIAGNOSTIC_RETRY_PROOF_2026_06_01`

## Scope

This artifact records a single live Claude diagnostic retry run for the Iota
Verbum training-room flow. It is a one-case proof of the wrapper behavior, not a
full benchmark claim and not fine-tuning.

## Case

- Case: `CUCV4-INVARIANT-01-COUNTERPARTY-RESPONSE-LEGAL-CONTRACT`
- Model: `claude-sonnet-4-6`
- Runner: `scripts/claude_phase3_diagnostic_retry.py`
- Baseline output: `cuc-results/claude_single_case_diagnostic_probe`
- Retry output: `cuc-results/claude_diagnostic_retry_probe`

## Baseline

- Accepted: `false`
- JSON valid: `true`
- Similarity: `77.87%`
- Verifier reason count: `8`
- Ledger committed: `false`

Rejected reason families:

- `mismatched_changed_states`
- `mismatched_changed_edges`
- `mismatched_changed_events`
- `mismatched_new_unknowns`
- `unexpected_scenario_rank_changes`
- `mismatched_scenario_rank_changes`
- `missing_supporting_evidence`
- `unexpected_supporting_evidence`

## Diagnostic Repair

Repair artifact:
`cuc-results/claude_diagnostic_retry_probe/CUCV4-INVARIANT-01-COUNTERPARTY-RESPONSE-LEGAL-CONTRACT/repair_instruction.json`

The repair instruction classified the failure as `GROUNDING_GAP`, targeted
`op:hop3`, required `source_op_ids=["op:hop3"]` on the hop3 state, edge, event,
and unknown records, removed the unexpected alternate/scenario evidence-map
entries, and preserved only the expected stable delivery branch:

- `state:secondary`
- `edge:secondary_support`
- `unknown:secondary`

## Retry Result

- Accepted: `true`
- JSON valid: `true`
- Similarity: `98.13%`
- Similarity delta: `+20.26`
- Verifier reason count: `0`
- Ledger committed: `true`

Ledger commit:

- Bundle SHA-256:
  `5f488c0580d18023e2851c7e26d549f6af90cc7ae8840a6ff3c6caaa1caf238c`
- Output SHA-256:
  `53b8fba70242954b74ce2a2dab07ce08c968bfff58d079034356afd8a0680e8c`
- Attestation SHA-256:
  `5eede2bbcd077e8e8128a8f9160326d58db98368f2a83d3447e2c21a9d428c48`
- Ledger run directory:
  `cuc-results/claude_diagnostic_retry_probe/ledger/5f488c0580d18023e2851c7e26d549f6af90cc7ae8840a6ff3c6caaa1caf238c`

## Supported Claim

This live run supports the narrow GTM claim that Iota Verbum can take a failed
sealed benchmark attempt from a customer model, classify the verifier rejection,
emit a targeted repair instruction, rerun the model, and produce an accepted
sealed ledger artifact.

This run does not establish broad model improvement across the benchmark suite.
The next evidence step is to repeat the same diagnostic retry flow across a
small fixed failure basket and report pass-rate movement, repair convergence,
and any terminal failures.

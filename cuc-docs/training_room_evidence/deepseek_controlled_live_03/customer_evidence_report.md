# Iota Verbum Customer Evidence Report

Evidence status: `strict_replay_verified`

## Executive Summary

In one controlled live session, deepseek-v4-pro moved from a verifier-rejected 71.84% baseline to a verifier-accepted 100.00% candidate after one deterministic Iota diagnostic repair pass, then produced a ledger artifact that passed strict-manifest replay.

## Verified Service Outcome

| Stage | Accepted | Similarity | Verifier reasons | Ledger |
| --- | --- | ---: | ---: | --- |
| Baseline benchmark | false | 71.84% | 4 | none |
| Iota training pass 1 | true | 100.00% | 0 | committed |

- Model: `deepseek-v4-pro`
- Case: `CUCV5A-GROUNDING-02-CONFLICT-RECONCILIATION-SECURITY-INCIDENT`
- Provider: `deepseek`
- Training passes consumed: `1`
- Similarity improvement: `+28.16` points
- No-regression selection: `retry`

## Deterministic Diagnostic Repair

- Failure family: `GROUNDING_GAP`
- Target operation: `multiple`
- Repair instruction: Patch only the cited grounding gap: add the missing source_op_ids and supporting_evidence_map entries, and remove any unsupported evidence references.
- Grounding evidence: `evidence:corroboration`, `evidence:primary`
- Preservation constraints: `state:secondary`, `edge:secondary_support`, `unknown:secondary`

## Sealed Integrity Proof

- Bundle SHA-256: `f59bb947a47704349bcc7f0c64a9597c92c124143650d56e5416dfc08415f566`
- Output SHA-256: `2c873500c3341121c92e4aa40e0909f1f63f8beb2a3a8e77879afbbbb2f5bf84`
- Attestation SHA-256: `773bb5aaf3082cc1be2e1274186b0ab041904e24d7052730a25afe0fc870a667`
- Sealed manifest SHA-256: `03882175de86507a0c830e2a2da68d628cb633ae666370677b82ec55e8c67e9e`
- Sealed repository commit: `64b83b9d1dcc061a9bbffc1bda9ce94564099bc2`
- Sealed commit manifest match: `verified`
- Strict replay status: `verified_ok`
- Strict replay warnings: `0`

Reproduce strict replay from the evidence package directory:

```powershell
python -m core.determinism.replay ledger/f59bb947a47704349bcc7f0c64a9597c92c124143650d56e5416dfc08415f566 --strict-manifest
```

## Included Evidence

| Artifact | SHA-256 | Bytes |
| --- | --- | ---: |
| `MANIFEST.sha256` | `03882175de86507a0c830e2a2da68d628cb633ae666370677b82ec55e8c67e9e` | 51850 |
| `evidence/baseline_gap_report.json` | `792edf06d091a480fe013b08c761a76dbb4095e864884abe28200c45eb225858` | 3158 |
| `evidence/baseline_model_delta.json` | `31a1d16de6052b8698c08adc93125b218e6d16fd97c327feb4dd51876af31163` | 4661 |
| `evidence/baseline_verification.json` | `de5c1018b47dccaa31c21c71a1dd379dcbd093c1dcc7b0d26e82749416e4f6a4` | 410 |
| `evidence/repair_instruction.json` | `86b551b3dc6f9cc7f6979a39eeb5f9b3988f97c5eff670d14b57da229d7650a2` | 6719 |
| `evidence/retry_gap_report.json` | `06517d6a6de86bbb56c18a2840db0d866e7d0f5d929203313104a2f4f5c44863` | 213 |
| `evidence/retry_model_delta.json` | `2414cdd0ff3b0a530274aa0aa7d91d5897a2db97ce958538ecc7450553206242` | 4794 |
| `evidence/scorecard.json` | `711833ee6f171d7f59aabb764794ba2a5f6df3c740a1e6db2ff874ea65a33f27` | 3855 |
| `evidence/training_summary.json` | `3fa802b2dc9f19da162fed890890c4c81e744cdc9983e8bd6f1d03699ed04590` | 4922 |
| `evidence/verification.json` | `e290f117d3f920271a755e3845927edbb6afacfb412a746c74aa5cd8eaeacfec` | 65 |
| `ledger/f59bb947a47704349bcc7f0c64a9597c92c124143650d56e5416dfc08415f566/attestation.json` | `773bb5aaf3082cc1be2e1274186b0ab041904e24d7052730a25afe0fc870a667` | 395 |
| `ledger/f59bb947a47704349bcc7f0c64a9597c92c124143650d56e5416dfc08415f566/bundle.json` | `f59bb947a47704349bcc7f0c64a9597c92c124143650d56e5416dfc08415f566` | 20921 |
| `ledger/f59bb947a47704349bcc7f0c64a9597c92c124143650d56e5416dfc08415f566/output.json` | `2c873500c3341121c92e4aa40e0909f1f63f8beb2a3a8e77879afbbbb2f5bf84` | 3659 |

## Claim Boundary

This package proves one live, one-case, in-context diagnostic-repair session. It does not establish broad benchmark improvement, persistent weight-level model improvement, fine-tuning, or performance outside the sealed case and verifier contract.

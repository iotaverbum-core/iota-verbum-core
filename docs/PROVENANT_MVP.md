# Provenant MVP — verifiable records for AI-assisted decisions

Provenant turns each AI-assisted decision into a **tamper-evident, reproducible
record** an auditor can verify independently, detects **silent regressions**
when a model changes, and produces an **examiner-ready export pack**. It is a
thin product layer over the iota-verbum deterministic engine.

Target customer: risk/compliance + ML leaders at digital lenders running ML/LLMs
in underwriting who must defend specific decisions to bank partners, examiners,
and the CFPB.

## The four primitives

| Command | What it does | Customer value |
| --- | --- | --- |
| `seal` | Seal a decision into a deterministic, hash-attested record; flag compliance gaps (e.g. an adverse outcome with no reason codes) | A defensible receipt for every decision |
| `verify` | Recompute the content + file hashes and report tampering | Auditors verify integrity without trusting the vendor |
| `diff` | Compare two records for the same subject across model versions | Catch decisions that silently flipped after a deploy |
| `export` | Aggregate records into a deterministic examiner pack | One artifact to hand a regulator |

## Quickstart

```bash
export PYTHONPATH=src

# 1) Seal a decision (decision.json describes the inputs + the model's output)
python -m provenant seal --input decision.json --out runs/app-7781

# 2) Verify it (exit 1 if tampered)
python -m provenant verify runs/app-7781

# 3) After a model change, diff the new record against the prior one
python -m provenant diff runs/app-7781 runs/app-7781-v2   # exit 2 on regression

# 4) Build an examiner pack from a set of records
python -m provenant export --tenant lender-acme \
  --generated-utc 2026-06-28T00:00:00Z \
  --out export/pack.json runs/app-7781 runs/app-7781-v2
```

### `decision.json` shape

```json
{
  "record_id": "app-7781",
  "tenant_id": "lender-acme",
  "created_utc": "2026-06-28T09:15:00Z",
  "subject_ref": "application-7781",
  "decision": {"outcome": "DENY", "score": 0.31},
  "model": {"name": "underwriter-llm", "version": "2026-05-01"},
  "evidence": [{"ref": "doc:paystub", "sha256": "..."}],
  "reason_codes": [
    {"code": "R01", "text": "Debt-to-income above threshold",
     "regulation": "ECOA / Reg B", "evidence_ref": "doc:paystub"}
  ],
  "governance": {"audit_ready": true, "adverse_action_required": true}
}
```

## Integrity model

Each sealed record carries two independent anchors:

- `seal.content_sha256` — hash of the canonicalised decision content; detects
  content tampering regardless of file formatting.
- `attestation.sha256` (sidecar) — hash of the exact `record.json` bytes;
  detects file-level tampering.

`verify` recomputes both. Determinism: sealing performs no wall-clock reads and
no randomness (`created_utc` is caller-supplied), so the same decision always
seals to the same bytes — the property that makes byte-for-byte replay and
independent verification possible.

## Compliance checks (v1)

- `ADVERSE_ACTION_NO_REASONS` — an adverse outcome (DENY/DECLINE/…) with no
  reason codes (would fail an ECOA / Reg B adverse-action notice).
- `ADVERSE_FLAG_OUTCOME_MISMATCH` — `adverse_action_required` set on a
  non-adverse outcome.
- `REASON_EVIDENCE_MISSING` — a reason code cites evidence not attached to the
  record.

## Tests

```bash
python -m pytest tests/test_provenant.py -q
```

## Not in this MVP (deliberately)

Multi-tenant storage, hosted verify portal, billing, SSO/SOC 2, and a UI are
intentionally out of the core library so the first paid pilot can run against a
customer's real decisions through the API/SDK without waiting on a platform.

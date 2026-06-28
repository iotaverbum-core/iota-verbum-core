# Deterministic AI CLI (Multi-Domain Run Path)

`deterministic-ai` is the repo's deterministic extraction engine. It turns a
verified input record into a sealed, attested output bundle for one of the
registered domains. Every run is reproducible: the same input, templates, and
context always produce byte-identical `output.json`, `provenance.json`, and
`attestation.sha256`.

The engine ships as a console script (`deterministic-ai`) and as a module
(`python -m deterministic_ai`).

## Registered domains

All five domains run through the same manifest-anchored, integrity-checked path:

| Domain | Input ref | Sample manifest |
| --- | --- | --- |
| `biblical_text` | `John 4:7-10` | `data/scripture/esv_sample/manifest.json` (via `--dataset esv_sample`) |
| `credit_scoring` | `applicant_12345` | `data/credit/manifest.json` |
| `clinical_records` | `patient_67890` | `data/clinical/manifest.json` |
| `legal_contract` | `sample_contract` | `data/legal_contract_sample/manifest.json` |
| `market_realtime` | `DJI-2026-03-19` | `data/market/manifest.json` |

## The manifest-anchored integrity gate

Inputs are resolved by reference against a domain manifest. Each manifest maps a
ref to a data file and the SHA-256 of that file's bytes:

```json
{
  "dataset": "applicant_records_2026Q1",
  "schema_version": "1.0",
  "records": {
    "applicant_12345": {
      "file": "sample_applicant.json",
      "sha256": "f2e8c628a9935e2f50c3bc2efadccb80a75e81d3fa968fca762a57281f4f78cf",
      "record_type": "personal_loan_application",
      "validated": true
    }
  }
}
```

When you run by `--input-ref`, `core.manifest.resolve_input` reads the data file
and rejects it if the bytes do not match the recorded `sha256`
(`manifest sha256 mismatch for input file`). The resolved manifest hash is
written into the output bundle as `provenance_meta.input_manifest_sha256` and
`input_meta.manifest_sha256`, tying every output to a verified input.

`--input-file` is supported for ad-hoc inputs and bypasses the manifest lookup;
prefer `--input-ref` for audit-ready runs.

## Running each domain

```bash
# Biblical text (dataset-backed manifest)
deterministic-ai --domain biblical_text --input-ref "John 4:7-10" \
  --dataset esv_sample --context "moment=smoke test" --out outputs/biblical

# Credit scoring
deterministic-ai --domain credit_scoring --input-ref applicant_12345 \
  --out outputs/credit

# Clinical records
deterministic-ai --domain clinical_records --input-ref patient_67890 \
  --out outputs/clinical

# Legal contract
deterministic-ai --domain legal_contract --input-ref sample_contract \
  --out outputs/legal

# Market realtime (forward projection; --out must live under outputs/)
deterministic-ai --domain market_realtime --input-ref DJI-2026-03-19 \
  --context "mode=forward" --context "horizon=86400" \
  --out outputs/demo/market
```

> `market_realtime` additionally compiles a sealed forward-projection ledger.
> Its casefile records a `ledger_dir` that must match `^outputs/.+$`, so point
> `--out` at a path under `outputs/`.

## Output bundle

Each run writes, into `--out`:

- `output.json` — the deterministic extraction result
- `provenance.json` — input/template/output hashes, governance metadata, and the
  resolved `input_manifest_sha256`
- `attestation.sha256` — attestation over the output
- `log.txt` — run log

`market_realtime` also writes `world_model.json`, `sealed_path.json`,
`forward_attestation.sha256`, `replay_manifest.json`, and a `ledger/` directory.

## Verifying a bundle

```bash
deterministic-ai validate-provenance outputs/credit/provenance.json
```

This re-checks the attestation, template hash, and input hash recorded in the
bundle and reports `attestation_match`, `template_match`, and `input_match`.

## Determinism and tests

Cross-domain determinism and the integrity gate are covered by
`tests/test_deterministic_ai.py` (per-domain golden snapshots) and
`tests/test_domain_manifests.py` (every registered manifest resolves through the
sha256-checked path, plus tamper detection). Run them with:

```bash
python -m pytest tests/test_deterministic_ai.py tests/test_domain_manifests.py -v
```

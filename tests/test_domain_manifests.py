"""Integrity-path coverage for the ``deterministic_ai`` multi-domain CLI.

Every domain registered in ``deterministic_ai.DOMAIN_REGISTRY`` is meant to run
through the manifest-anchored, sha256-checked ``resolve_input`` path so that each
output is tied to a verified input by a recorded manifest hash. The existing
``test_deterministic_ai`` suite exercises several domains with ``--input-file``,
which deliberately bypasses that integrity gate; these tests cover the gate
itself and guard it against silent drift or manifest-schema rot.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import core.path_compiler as path_compiler_module
from core.attestation import sha256_bytes
from core.manifest import load_manifest, resolve_input
from deterministic_ai import main
from domains.market_realtime.extractors import (
    MarketManifestBuilder,
    build_sample_dji_input,
)

ROOT = Path(__file__).resolve().parents[1]

# (label, manifest path) for every manifest the CLI resolves through
# ``resolve_input``. biblical_text resolves against its scripture dataset
# manifest when ``--dataset`` is supplied.
DOMAIN_MANIFESTS = [
    ("biblical_text", "data/scripture/esv_sample/manifest.json"),
    ("credit_scoring", "data/credit/manifest.json"),
    ("clinical_records", "data/clinical/manifest.json"),
    ("legal_contract", "data/legal_contract_sample/manifest.json"),
    ("market_realtime", "data/market/manifest.json"),
]


@pytest.mark.parametrize("label,manifest_rel", DOMAIN_MANIFESTS)
def test_committed_manifest_is_records_shaped_and_unbroken(label, manifest_rel):
    manifest_path = ROOT / manifest_rel
    records, manifest_sha256 = load_manifest(manifest_path)

    assert isinstance(records, dict) and records, f"{label}: not records-shaped"
    assert manifest_sha256
    for ref, entry in records.items():
        assert isinstance(entry, dict), f"{label}:{ref} entry is not an object"
        assert "file" in entry, f"{label}:{ref} missing file"
        file_path = manifest_path.parent / entry["file"]
        assert file_path.exists(), f"{label}:{ref} data file missing"
        expected = entry.get("sha256")
        assert expected, f"{label}:{ref} sha256 empty (integrity check disabled)"
        actual = sha256_bytes(file_path.read_bytes())
        assert actual == expected, f"{label}:{ref} sha256 drift"


@pytest.mark.parametrize("label,manifest_rel", DOMAIN_MANIFESTS)
def test_resolve_input_succeeds_for_every_ref(label, manifest_rel):
    manifest_path = ROOT / manifest_rel
    records, _ = load_manifest(manifest_path)

    for ref in records:
        resolved = resolve_input(ref, manifest_path)
        assert resolved["ref"] == ref
        assert sha256_bytes(resolved["data_bytes"]) == records[ref]["sha256"]
        assert resolved["manifest_sha256"]


def test_resolve_input_rejects_tampered_data(tmp_path):
    data_file = tmp_path / "rec.json"
    data_file.write_text('{"v": 1}', encoding="utf-8")
    good_sha = sha256_bytes(data_file.read_bytes())
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({"records": {"rec": {"file": "rec.json", "sha256": good_sha}}}),
        encoding="utf-8",
    )

    assert resolve_input("rec", manifest)["ref"] == "rec"

    data_file.write_text('{"v": 2}', encoding="utf-8")
    with pytest.raises(ValueError, match="manifest sha256 mismatch"):
        resolve_input("rec", manifest)


def test_market_manifest_builder_emits_resolvable_records(tmp_path):
    data_file = tmp_path / "snap.json"
    data_file.write_text('{"symbol": "DJI"}', encoding="utf-8")

    entry = MarketManifestBuilder.entry_from_file("DJI-2026-03-19", str(data_file))
    assert entry["file"] == "snap.json"  # bare filename, resolvable by resolve_input

    manifest_obj = MarketManifestBuilder.build_manifest([entry])
    assert "records" in manifest_obj
    assert "entries" not in manifest_obj

    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest_obj), encoding="utf-8")
    resolved = resolve_input("DJI-2026-03-19", manifest_path)
    assert sha256_bytes(resolved["data_bytes"]) == entry["sha256"]


@pytest.mark.parametrize(
    "domain,input_ref",
    [
        ("credit_scoring", "applicant_12345"),
        ("clinical_records", "patient_67890"),
        ("legal_contract", "sample_contract"),
    ],
)
def test_cli_runs_through_manifest_path_and_records_provenance(
    tmp_path, domain, input_ref
):
    # No --input-file: this forces the manifest-anchored resolve_input path.
    out_dir = tmp_path / domain
    main(["--domain", domain, "--input-ref", input_ref, "--out", str(out_dir)])

    provenance = json.loads((out_dir / "provenance.json").read_text(encoding="utf-8"))
    assert provenance["domain"] == domain
    # The recorded manifest hash ties the output to a verified input.
    assert provenance["provenance_meta"]["input_manifest_sha256"]
    assert provenance["input_meta"]["manifest_sha256"]


def test_cli_biblical_text_runs_through_dataset_manifest(tmp_path):
    out_dir = tmp_path / "biblical"
    main(
        [
            "--domain",
            "biblical_text",
            "--input-ref",
            "John 4:7-10",
            "--dataset",
            "esv_sample",
            "--out",
            str(out_dir),
        ]
    )

    provenance = json.loads((out_dir / "provenance.json").read_text(encoding="utf-8"))
    assert provenance["domain"] == "biblical_text"
    assert provenance["provenance_meta"]["input_manifest_sha256"]


def test_cli_market_realtime_runs_through_manifest_path(tmp_path, monkeypatch):
    # market_realtime is special-cased in run_pipeline (forward projection). Prove the
    # whole CLI path runs off the committed manifest and emits sealed/attested
    # artifacts. _repo_root is redirected so the ledger_dir resolves under outputs/.
    monkeypatch.setattr(path_compiler_module, "_repo_root", lambda: tmp_path)
    out_dir = tmp_path / "outputs" / "market" / "dji"
    main(
        [
            "--domain",
            "market_realtime",
            "--input-ref",
            "DJI-2026-03-19",
            "--context",
            "mode=forward",
            "--context",
            "horizon=86400",
            "--out",
            str(out_dir),
        ]
    )

    provenance = json.loads((out_dir / "provenance.json").read_text(encoding="utf-8"))
    assert provenance["domain"] == "market_realtime"
    assert provenance["provenance_meta"]["input_manifest_sha256"]
    assert (out_dir / "sealed_path.json").exists()
    assert (out_dir / "forward_attestation.sha256").exists()

    output = json.loads((out_dir / "output.json").read_text(encoding="utf-8"))
    assert output["market_input"]["symbol"] == build_sample_dji_input()["symbol"]

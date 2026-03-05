import json
from pathlib import Path

import pytest

from core.determinism.attest import build_attestation
from core.determinism.bundle import build_evidence_bundle
from core.determinism.canonical_json import dumps_canonical
from core.determinism.hashing import sha256_bytes

FIXTURES = Path("tests/fixtures")


def _bundle_sha() -> str:
    bundle = json.loads(
        (FIXTURES / "evidence_bundle_example.json").read_text(encoding="utf-8")
    )
    _, bundle_sha = build_evidence_bundle(bundle)
    return bundle_sha


def _output_bytes() -> bytes:
    return dumps_canonical({"decision": "allow", "justification": "Matched evidence"})


def test_build_attestation_matches_golden_hash_and_output_hash():
    attestation = {
        "attestation_version": "1.0",
        "created_utc": "2026-03-01T12:05:00Z",
        "bundle_sha256": _bundle_sha(),
        "core_version": "0.3.0",
        "ruleset_id": "ruleset.core.v1",
        "manifest_sha256": "1" * 64,
    }

    attestation_bytes, attestation_sha = build_attestation(attestation, _output_bytes())

    expected_sha = (FIXTURES / "expected_attestation_sha256.txt").read_text(
        encoding="utf-8"
    ).strip()
    rebuilt = json.loads(attestation_bytes.decode("utf-8"))

    assert attestation_sha == expected_sha
    assert attestation_bytes == dumps_canonical(rebuilt)
    assert rebuilt["output_sha256"] == sha256_bytes(_output_bytes())


def test_build_attestation_rejects_output_hash_mismatch():
    attestation = {
        "attestation_version": "1.0",
        "created_utc": "2026-03-01T12:05:00Z",
        "bundle_sha256": _bundle_sha(),
        "core_version": "0.3.0",
        "ruleset_id": "ruleset.core.v1",
        "manifest_sha256": "1" * 64,
        "output_sha256": "0" * 64,
    }

    with pytest.raises(ValueError, match="output_sha256 mismatch"):
        build_attestation(attestation, _output_bytes())

import json
from pathlib import Path

import pytest

from core.determinism.bundle import build_evidence_bundle
from core.determinism.canonical_json import dumps_canonical
from core.determinism.hashing import sha256_text

FIXTURES = Path("tests/fixtures")


def test_build_evidence_bundle_matches_golden_hash_and_bytes():
    bundle = json.loads(
        (FIXTURES / "evidence_bundle_example.json").read_text(encoding="utf-8")
    )

    bundle_bytes, bundle_sha = build_evidence_bundle(bundle)

    expected_sha = (FIXTURES / "expected_bundle_sha256.txt").read_text(
        encoding="utf-8"
    ).strip()
    rebuilt = json.loads(bundle_bytes.decode("utf-8"))

    assert bundle_sha == expected_sha
    assert bundle_bytes == dumps_canonical(rebuilt)
    assert rebuilt["artifacts"][0]["text_sha256"] == sha256_text(
        bundle["artifacts"][0]["text"]
    )


def test_build_evidence_bundle_rejects_artifact_hash_mismatch():
    bundle = json.loads(
        (FIXTURES / "evidence_bundle_example.json").read_text(encoding="utf-8")
    )
    bundle["artifacts"][0]["text_sha256"] = "0" * 64

    with pytest.raises(ValueError, match="text_sha256 mismatch"):
        build_evidence_bundle(bundle)

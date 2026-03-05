import json
import time
from datetime import datetime
from pathlib import Path

import pytest

from core.determinism.finalize import finalize

FIXTURES = Path("tests/fixtures")


def _load_bundle() -> dict:
    return json.loads(
        (FIXTURES / "evidence_bundle_example.json").read_text(encoding="utf-8")
    )


def test_finalize_is_byte_identical_for_identical_inputs():
    evidence_bundle = _load_bundle()
    output_obj = {"decision": "allow", "reasons": ["matched", "verified"]}

    left = finalize(
        evidence_bundle,
        output_obj,
        manifest_sha256="1" * 64,
        core_version="0.3.0",
        ruleset_id="ruleset.core.v1",
        created_utc="2026-03-01T12:05:00Z",
    )
    right = finalize(
        evidence_bundle,
        output_obj,
        manifest_sha256="1" * 64,
        core_version="0.3.0",
        ruleset_id="ruleset.core.v1",
        created_utc="2026-03-01T12:05:00Z",
    )

    assert left["bundle_bytes"] == right["bundle_bytes"]
    assert left["bundle_sha256"] == right["bundle_sha256"]
    assert left["output_bytes"] == right["output_bytes"]
    assert left["output_sha256"] == right["output_sha256"]
    assert left["attestation_bytes"] == right["attestation_bytes"]
    assert left["attestation_sha256"] == right["attestation_sha256"]


def test_finalize_output_change_only_changes_output_and_attestation_hashes():
    evidence_bundle = _load_bundle()

    left = finalize(
        evidence_bundle,
        {"decision": "allow"},
        manifest_sha256="1" * 64,
        core_version="0.3.0",
        ruleset_id="ruleset.core.v1",
        created_utc="2026-03-01T12:05:00Z",
    )
    right = finalize(
        evidence_bundle,
        {"decision": "deny"},
        manifest_sha256="1" * 64,
        core_version="0.3.0",
        ruleset_id="ruleset.core.v1",
        created_utc="2026-03-01T12:05:00Z",
    )

    assert left["bundle_sha256"] == right["bundle_sha256"]
    assert left["output_sha256"] != right["output_sha256"]
    assert left["attestation_sha256"] != right["attestation_sha256"]


def test_finalize_raises_for_invalid_evidence_bundle():
    evidence_bundle = _load_bundle()
    del evidence_bundle["policy"]

    with pytest.raises(ValueError):
        finalize(
            evidence_bundle,
            {"decision": "allow"},
            manifest_sha256="1" * 64,
            core_version="0.3.0",
            ruleset_id="ruleset.core.v1",
            created_utc="2026-03-01T12:05:00Z",
        )


def test_finalize_does_not_read_clock(monkeypatch: pytest.MonkeyPatch):
    class ForbiddenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            raise AssertionError("datetime.now() must not be used")

        @classmethod
        def utcnow(cls):
            raise AssertionError("datetime.utcnow() must not be used")

    monkeypatch.setattr(
        time,
        "time",
        lambda: (_ for _ in ()).throw(AssertionError),
    )
    monkeypatch.setattr(
        time,
        "monotonic",
        lambda: (_ for _ in ()).throw(AssertionError),
    )
    monkeypatch.setattr("datetime.datetime", ForbiddenDateTime)

    result = finalize(
        _load_bundle(),
        {"decision": "allow"},
        manifest_sha256="1" * 64,
        core_version="0.3.0",
        ruleset_id="ruleset.core.v1",
        created_utc="2026-03-01T12:05:00Z",
    )

    assert result["bundle_sha256"]
    assert result["attestation_sha256"]

from __future__ import annotations

import pytest

from core.determinism.attest import build_attestation
from core.determinism.hashing import sha256_bytes
from core.determinism.integrity import create_tampered_ledger_copy
from core.determinism.ledger import write_run
from core.determinism.manifest_hash import compute_manifest_sha256
from core.determinism.replay import verify_run


def test_tampered_copied_ledger_fails_replay(tmp_path) -> None:
    bundle_bytes = b'{"bundle":"ok"}'
    bundle_sha256 = sha256_bytes(bundle_bytes)
    output_bytes = b'{"output":"ok"}'
    output_sha256 = sha256_bytes(output_bytes)
    attestation_bytes, attestation_sha256 = build_attestation(
        {
            "attestation_version": "1.0",
            "created_utc": "2026-03-06T10:00:00Z",
            "bundle_sha256": bundle_sha256,
            "core_version": "0.4.0",
            "ruleset_id": "ruleset.core.v1",
            "manifest_sha256": compute_manifest_sha256(),
            "output_sha256": output_sha256,
        },
        output_bytes,
    )

    ledger_dir = write_run(
        ledger_root=(tmp_path / "ledger").as_posix(),
        bundle_bytes=bundle_bytes,
        bundle_sha256=bundle_sha256,
        output_bytes=output_bytes,
        output_sha256=output_sha256,
        attestation_bytes=attestation_bytes,
        attestation_sha256=attestation_sha256,
    )

    verify_run(str(ledger_dir), strict_manifest=True)

    tampered = create_tampered_ledger_copy(
        ledger_dir,
        tamper_root=tmp_path / "ledger_tamper_test",
    )
    with pytest.raises(ValueError, match="attestation output_sha256 mismatch"):
        verify_run(str(tampered), strict_manifest=True)

    verify_run(str(ledger_dir), strict_manifest=True)

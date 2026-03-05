from __future__ import annotations

from pathlib import Path

from core.determinism.hashing import sha256_bytes


def ledger_path(root_dir: str, bundle_sha256: str) -> Path:
    return Path(root_dir) / bundle_sha256


def _write_atomic(path: Path, data: bytes) -> None:
    temp_path = path.with_name(f".{path.name}.tmp")
    temp_path.write_bytes(data)
    temp_path.replace(path)


def _write_or_verify(path: Path, data: bytes) -> None:
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f"existing ledger file mismatch: {path.name}")
        return
    _write_atomic(path, data)


def write_run(
    *,
    ledger_root: str = "data/ledger",
    bundle_bytes: bytes,
    bundle_sha256: str,
    output_bytes: bytes,
    output_sha256: str,
    attestation_bytes: bytes,
    attestation_sha256: str,
) -> Path:
    if sha256_bytes(bundle_bytes) != bundle_sha256:
        raise ValueError("bundle_sha256 does not match bundle_bytes")
    if sha256_bytes(output_bytes) != output_sha256:
        raise ValueError("output_sha256 does not match output_bytes")
    if sha256_bytes(attestation_bytes) != attestation_sha256:
        raise ValueError("attestation_sha256 does not match attestation_bytes")

    run_dir = ledger_path(ledger_root, bundle_sha256)
    run_dir.mkdir(parents=True, exist_ok=True)

    _write_or_verify(run_dir / "bundle.json", bundle_bytes)
    _write_or_verify(run_dir / "output.json", output_bytes)
    _write_or_verify(run_dir / "attestation.json", attestation_bytes)

    return run_dir

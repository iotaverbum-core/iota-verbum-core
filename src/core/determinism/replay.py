from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.determinism.hashing import sha256_bytes
from core.determinism.schema_validate import validate


def verify_run(dir_path: str, *, strict_manifest: bool = False) -> dict:
    run_dir = Path(dir_path)
    bundle_bytes = (run_dir / "bundle.json").read_bytes()
    output_bytes = (run_dir / "output.json").read_bytes()
    attestation_bytes = (run_dir / "attestation.json").read_bytes()

    bundle_sha256 = sha256_bytes(bundle_bytes)
    output_sha256 = sha256_bytes(output_bytes)
    attestation_sha256 = sha256_bytes(attestation_bytes)

    if run_dir.name != bundle_sha256:
        raise ValueError("ledger directory name does not match bundle_sha256")

    attestation = json.loads(attestation_bytes.decode("utf-8"))
    validate(attestation, "schemas/attestation_record.schema.json")

    if attestation["bundle_sha256"] != bundle_sha256:
        raise ValueError("attestation bundle_sha256 mismatch")
    if attestation["output_sha256"] != output_sha256:
        raise ValueError("attestation output_sha256 mismatch")

    warnings: list[str] = []
    manifest_path = Path("MANIFEST.sha256")
    manifest_sha256 = sha256_bytes(manifest_path.read_bytes())
    if attestation["manifest_sha256"] != manifest_sha256:
        if strict_manifest:
            raise ValueError("attestation manifest_sha256 mismatch")
        warnings.append("manifest_sha256 mismatch")

    return {
        "ok": True,
        "bundle_sha256": bundle_sha256,
        "output_sha256": output_sha256,
        "attestation_sha256": attestation_sha256,
        "warnings": warnings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    parser.add_argument("--strict-manifest", action="store_true")
    args = parser.parse_args(argv)

    try:
        result = verify_run(args.path, strict_manifest=args.strict_manifest)
    except Exception as exc:
        print(f"Replay verification failed: {exc}")
        return 1

    warning_suffix = ""
    if result["warnings"]:
        warning_suffix = f" warnings={len(result['warnings'])}"
    print(
        "Replay verification OK:"
        f" bundle_sha256={result['bundle_sha256']}"
        f" output_sha256={result['output_sha256']}"
        f" attestation_sha256={result['attestation_sha256']}"
        f"{warning_suffix}"
    )
    for warning in result["warnings"]:
        print(f"warning: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

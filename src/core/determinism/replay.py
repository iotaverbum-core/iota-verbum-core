from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from core.determinism.hashing import sha256_bytes
from core.determinism.schema_validate import validate

LOGGER = logging.getLogger(__name__)
_REQUIRED_REPLAY_ARTIFACTS = ("bundle.json", "output.json", "attestation.json")
_STATUS_VERIFIED_OK = "verified_ok"
_STATUS_SKIPPED = "skipped"
_STATUS_FAILED = "failed_deterministically"
_NO_COMPARABLE_REASON = "no comparable replay artifacts found"


def _run_id_from_ledger_dir(run_dir: Path) -> str:
    if run_dir.parent.name == "ledger" and run_dir.parent.parent.name:
        return run_dir.parent.parent.name
    if run_dir.parent.name:
        return run_dir.parent.name
    return run_dir.name


def _base_result(run_dir: Path) -> dict:
    return {
        "ok": False,
        "status": _STATUS_FAILED,
        "reason": "",
        "replay_target": run_dir.as_posix(),
        "run_id": _run_id_from_ledger_dir(run_dir),
        "sub_step": "",
        "empty_collection": "",
        "bundle_sha256": "",
        "output_sha256": "",
        "attestation_sha256": "",
        "warnings": [],
    }


def _deterministic_failure(
    *,
    run_dir: Path,
    status: str,
    reason: str,
    sub_step: str,
    empty_collection: str = "",
    missing_artifacts: list[str] | None = None,
) -> dict:
    result = _base_result(run_dir)
    result.update(
        {
            "status": status,
            "reason": reason,
            "sub_step": sub_step,
            "empty_collection": empty_collection,
        }
    )
    if missing_artifacts:
        result["missing_artifacts"] = list(missing_artifacts)

    log_fn = LOGGER.warning if status == _STATUS_SKIPPED else LOGGER.error
    log_fn(
        (
            "Replay verification status=%s reason=%s run_id=%s replay_target=%s "
            "sub_step=%s empty_collection=%s"
        ),
        status,
        reason,
        result["run_id"],
        result["replay_target"],
        sub_step,
        empty_collection or "-",
    )
    if missing_artifacts:
        log_fn(
            "Replay verification missing_artifacts=%s run_id=%s replay_target=%s",
            ",".join(sorted(missing_artifacts)),
            result["run_id"],
            result["replay_target"],
        )
    return result


def verify_run_deterministic(dir_path: str, *, strict_manifest: bool = False) -> dict:
    run_dir = Path(dir_path)
    try:
        if not run_dir.exists() or not run_dir.is_dir():
            return _deterministic_failure(
                run_dir=run_dir,
                status=_STATUS_SKIPPED,
                reason=_NO_COMPARABLE_REASON,
                sub_step="artifact_discovery",
                empty_collection="comparable_artifacts",
            )

        present_artifacts = sorted(
            name for name in _REQUIRED_REPLAY_ARTIFACTS if (run_dir / name).exists()
        )
        if not present_artifacts:
            return _deterministic_failure(
                run_dir=run_dir,
                status=_STATUS_SKIPPED,
                reason=_NO_COMPARABLE_REASON,
                sub_step="artifact_discovery",
                empty_collection="comparable_artifacts",
            )

        missing_artifacts = sorted(
            name for name in _REQUIRED_REPLAY_ARTIFACTS if name not in present_artifacts
        )
        if missing_artifacts:
            return _deterministic_failure(
                run_dir=run_dir,
                status=_STATUS_FAILED,
                reason=(
                    "missing required replay artifacts: "
                    + ", ".join(missing_artifacts)
                ),
                sub_step="artifact_discovery",
                empty_collection="required_replay_artifacts",
                missing_artifacts=missing_artifacts,
            )

        bundle_bytes = (run_dir / "bundle.json").read_bytes()
        output_bytes = (run_dir / "output.json").read_bytes()
        attestation_bytes = (run_dir / "attestation.json").read_bytes()

        bundle_sha256 = sha256_bytes(bundle_bytes)
        output_sha256 = sha256_bytes(output_bytes)
        attestation_sha256 = sha256_bytes(attestation_bytes)

        if run_dir.name != bundle_sha256:
            return _deterministic_failure(
                run_dir=run_dir,
                status=_STATUS_FAILED,
                reason="ledger directory name does not match bundle_sha256",
                sub_step="artifact_consistency",
            )

        attestation = json.loads(attestation_bytes.decode("utf-8"))
        validate(attestation, "schemas/attestation_record.schema.json")

        if attestation["bundle_sha256"] != bundle_sha256:
            return _deterministic_failure(
                run_dir=run_dir,
                status=_STATUS_FAILED,
                reason="attestation bundle_sha256 mismatch",
                sub_step="attestation_compare",
            )
        if attestation["output_sha256"] != output_sha256:
            return _deterministic_failure(
                run_dir=run_dir,
                status=_STATUS_FAILED,
                reason="attestation output_sha256 mismatch",
                sub_step="attestation_compare",
            )

        warnings: list[str] = []
        manifest_path = Path("MANIFEST.sha256")
        if not manifest_path.exists():
            return _deterministic_failure(
                run_dir=run_dir,
                status=_STATUS_FAILED,
                reason=_NO_COMPARABLE_REASON,
                sub_step="manifest_compare",
                empty_collection="manifest_entries",
            )
        manifest_bytes = manifest_path.read_bytes()
        manifest_entries = [
            line
            for line in manifest_bytes.decode("utf-8").splitlines()
            if line.strip()
        ]
        if not manifest_entries:
            return _deterministic_failure(
                run_dir=run_dir,
                status=_STATUS_FAILED,
                reason=_NO_COMPARABLE_REASON,
                sub_step="manifest_compare",
                empty_collection="manifest_entries",
            )

        manifest_sha256 = sha256_bytes(manifest_bytes)
        if attestation["manifest_sha256"] != manifest_sha256:
            if strict_manifest:
                return _deterministic_failure(
                    run_dir=run_dir,
                    status=_STATUS_FAILED,
                    reason="attestation manifest_sha256 mismatch",
                    sub_step="manifest_compare",
                )
            warnings.append("manifest_sha256 mismatch")

        result = _base_result(run_dir)
        result.update(
            {
                "ok": True,
                "status": _STATUS_VERIFIED_OK,
                "reason": "",
                "sub_step": "completed",
                "bundle_sha256": bundle_sha256,
                "output_sha256": output_sha256,
                "attestation_sha256": attestation_sha256,
                "warnings": warnings,
            }
        )
        return result
    except Exception as exc:  # noqa: BLE001
        return _deterministic_failure(
            run_dir=run_dir,
            status=_STATUS_FAILED,
            reason=f"unexpected replay verification error: {exc}",
            sub_step="unexpected_error",
        )


def verify_run(dir_path: str, *, strict_manifest: bool = False) -> dict:
    result = verify_run_deterministic(dir_path, strict_manifest=strict_manifest)
    if result["status"] != _STATUS_VERIFIED_OK:
        raise ValueError(result["reason"])
    return {
        "ok": True,
        "bundle_sha256": result["bundle_sha256"],
        "output_sha256": result["output_sha256"],
        "attestation_sha256": result["attestation_sha256"],
        "warnings": result["warnings"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    parser.add_argument("--strict-manifest", action="store_true")
    args = parser.parse_args(argv)

    result = verify_run_deterministic(args.path, strict_manifest=args.strict_manifest)
    if result["status"] != _STATUS_VERIFIED_OK:
        print(f"Replay verification {result['status']}: {result['reason']}")
        if result["empty_collection"]:
            print(f"empty_collection: {result['empty_collection']}")
        if "missing_artifacts" in result:
            print("missing_artifacts: " + ",".join(result["missing_artifacts"]))
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

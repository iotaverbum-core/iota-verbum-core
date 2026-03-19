from __future__ import annotations

if __package__ in {None, ""}:
    import sys
    from pathlib import Path as _BootstrapPath

    sys.path.insert(0, str(_BootstrapPath(__file__).resolve().parents[1]))

import json
import tomllib
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from core import attestation
from core.determinism.attest import build_attestation
from core.determinism.canonical_json import dumps_canonical
from core.determinism.hashing import sha256_bytes, sha256_text
from core.determinism.ledger import write_run
from core.determinism.schema_validate import validate
from core.world.forward_projection import (
    ForwardProjection,
    MarketWorldModelBuilder,
    SealedPath,
)

_ROLE_ORDER = {
    "sealed": 0,
    "derived": 1,
    "narrative": 2,
}
_UNKNOWN_SHA256 = "0" * 64


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(_repo_root().resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _created_utc(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _verification_status(sealed_path: SealedPath) -> str:
    value = sealed_path.verification.value
    if value == "VERIFIED":
        return "VERIFIED_OK"
    if value == "VERIFIED_NEEDS_INFO":
        return "VERIFIED_NEEDS_INFO"
    return "VERIFIED_FAIL"


def _artifacts_sort_key(item: dict) -> tuple[int, str]:
    return (_ROLE_ORDER[item["role"]], item["name"])


def _add_artifact(
    artifacts: list[dict],
    *,
    name: str,
    role: str,
    sha256: str,
    schema: str = "",
    notes: str = "",
) -> None:
    artifact = {"name": name, "role": role, "sha256": sha256}
    if schema:
        artifact["schema"] = schema
    if notes:
        artifact["notes"] = notes
    artifacts.append(artifact)


def _casefile_for_id_hash(casefile_obj: dict) -> dict:
    hashed = deepcopy(casefile_obj)
    hashed["casefile_id"] = ""
    hashed["hashes"]["output_sha256"] = _UNKNOWN_SHA256
    hashed["hashes"]["attestation_sha256"] = _UNKNOWN_SHA256
    for artifact in hashed["artifacts"]:
        if artifact["name"] in {"output.json", "attestation.json", "casefile.json"}:
            artifact["sha256"] = _UNKNOWN_SHA256
    return hashed


def _casefile_for_artifact_hash(casefile_obj: dict) -> dict:
    hashed = deepcopy(casefile_obj)
    hashed["hashes"]["output_sha256"] = _UNKNOWN_SHA256
    hashed["hashes"]["attestation_sha256"] = _UNKNOWN_SHA256
    for artifact in hashed["artifacts"]:
        if artifact["name"] in {"output.json", "attestation.json", "casefile.json"}:
            artifact["sha256"] = _UNKNOWN_SHA256
    return hashed


class PathCompiler:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = Path(output_dir)
        self.repo_root = _repo_root()

    def compile(self, sealed_path: SealedPath) -> dict:
        self.output_dir.mkdir(parents=True, exist_ok=True)

        sealed_path_payload = attestation.canonicalize_json(sealed_path.to_dict())
        sealed_path_path = self.output_dir / "sealed_path.json"
        sealed_path_path.write_bytes(sealed_path_payload)
        sealed_path_file_sha = attestation.compute_sha256(sealed_path_payload)

        forward_attestation_text = f"{sealed_path.seal_sha256}  sealed_path.json\n"
        forward_attestation_path = self.output_dir / "forward_attestation.sha256"
        attestation.write_text(forward_attestation_path, forward_attestation_text)
        forward_attestation_sha256 = sha256_text(forward_attestation_text)

        existing_output = self._read_existing_output()
        world_model_obj = existing_output.get("world_model", {})
        world_model_sha256 = _UNKNOWN_SHA256
        world_model_path = self.output_dir / "world_model.json"
        if world_model_obj:
            world_model_payload = attestation.canonicalize_json(world_model_obj)
            world_model_path.write_bytes(world_model_payload)
            world_model_sha256 = attestation.compute_sha256(world_model_payload)

        bundle_obj = self._build_ledger_entry(
            sealed_path=sealed_path,
            sealed_path_sha256=sealed_path_file_sha,
            forward_attestation_sha256=forward_attestation_sha256,
        )
        bundle_bytes = dumps_canonical(bundle_obj)
        bundle_sha256 = sha256_bytes(bundle_bytes)

        created_utc = _created_utc(sealed_path.sealed_at)
        attestation_obj = {
            "attestation_version": "1.0",
            "created_utc": created_utc,
            "bundle_sha256": bundle_sha256,
            "core_version": self._core_version(),
            "ruleset_id": "ruleset.core.v1",
            "manifest_sha256": self._manifest_sha256(),
            "output_sha256": sealed_path_file_sha,
        }
        attestation_bytes, attestation_sha256 = build_attestation(
            attestation_obj,
            sealed_path_payload,
        )

        ledger_dir = Path(
            write_run(
                ledger_root=str(self.output_dir / "ledger"),
                bundle_bytes=bundle_bytes,
                bundle_sha256=bundle_sha256,
                output_bytes=sealed_path_payload,
                output_sha256=sealed_path_file_sha,
                attestation_bytes=attestation_bytes,
                attestation_sha256=attestation_sha256,
            )
        )
        ledger_dir_rel = _repo_relative(ledger_dir)

        replay_manifest = {
            "path_id": sealed_path.path_id,
            "replay_key": sealed_path.replay_key,
            "sealed_path": "sealed_path.json",
            "forward_attestation": "forward_attestation.sha256",
            "ledger_dir": ledger_dir_rel,
            "bundle_sha256": bundle_sha256,
            "output_sha256": sealed_path_file_sha,
            "attestation_sha256": attestation_sha256,
            "verification_status": _verification_status(sealed_path),
        }
        replay_manifest_path = self.output_dir / "replay_manifest.json"
        replay_manifest_sha256 = attestation.write_json(
            replay_manifest_path,
            replay_manifest,
        )

        casefile = self._build_casefile(
            sealed_path=sealed_path,
            sealed_path_sha256=sealed_path_file_sha,
            forward_attestation_sha256=forward_attestation_sha256,
            replay_manifest_sha256=replay_manifest_sha256,
            world_model_sha256=world_model_sha256,
            world_model_obj=world_model_obj,
            ledger_dir_rel=ledger_dir_rel,
            bundle_sha256=bundle_sha256,
            output_sha256=sealed_path_file_sha,
            attestation_sha256=attestation_sha256,
            existing_output=existing_output,
        )
        casefile_path = self.output_dir / "casefile.json"
        casefile_path.write_bytes(attestation.canonicalize_json(casefile))

        replay_result = ForwardProjection.verify_replay(sealed_path_path)
        verified = replay_result["match"] and replay_result["status"] == "VERIFIED_OK"

        artifacts = [
            {
                "name": "sealed_path.json",
                "path": str(sealed_path_path),
                "role": "sealed",
                "sha256": sealed_path_file_sha,
            },
            {
                "name": "forward_attestation.sha256",
                "path": str(forward_attestation_path),
                "role": "sealed",
                "sha256": forward_attestation_sha256,
            },
            {
                "name": "replay_manifest.json",
                "path": str(replay_manifest_path),
                "role": "derived",
                "sha256": replay_manifest_sha256,
            },
            {
                "name": "casefile.json",
                "path": str(casefile_path),
                "role": "derived",
                "sha256": next(
                    artifact["sha256"]
                    for artifact in casefile["artifacts"]
                    if artifact["name"] == "casefile.json"
                ),
            },
        ]
        if world_model_obj:
            artifacts.append(
                {
                    "name": "world_model.json",
                    "path": str(world_model_path),
                    "role": "derived",
                    "sha256": world_model_sha256,
                }
            )

        return {
            "path_id": sealed_path.path_id,
            "seal_sha256": sealed_path.seal_sha256,
            "replay_key": sealed_path.replay_key,
            "artifacts": artifacts,
            "verified": verified,
            "ledger_dir": str(ledger_dir),
            "casefile_path": str(casefile_path),
            "bundle_sha256": bundle_sha256,
            "verification_status": replay_result["status"],
        }

    def _build_casefile(
        self,
        *,
        sealed_path: SealedPath,
        sealed_path_sha256: str,
        forward_attestation_sha256: str,
        replay_manifest_sha256: str,
        world_model_sha256: str,
        world_model_obj: dict,
        ledger_dir_rel: str,
        bundle_sha256: str,
        output_sha256: str,
        attestation_sha256: str,
        existing_output: dict,
    ) -> dict:
        artifacts: list[dict] = []
        _add_artifact(
            artifacts,
            name="attestation.json",
            role="sealed",
            sha256=attestation_sha256,
            schema="schemas/attestation_record.schema.json",
        )
        _add_artifact(
            artifacts,
            name="bundle.json",
            role="sealed",
            sha256=bundle_sha256,
        )
        _add_artifact(
            artifacts,
            name="output.json",
            role="sealed",
            sha256=output_sha256,
        )
        _add_artifact(
            artifacts,
            name="sealed_path.json",
            role="sealed",
            sha256=sealed_path_sha256,
        )
        _add_artifact(
            artifacts,
            name="forward_attestation.sha256",
            role="sealed",
            sha256=forward_attestation_sha256,
        )
        _add_artifact(
            artifacts,
            name="replay_manifest.json",
            role="derived",
            sha256=replay_manifest_sha256,
        )
        if world_model_obj:
            _add_artifact(
                artifacts,
                name="world_model.json",
                role="derived",
                sha256=world_model_sha256,
            )
        _add_artifact(
            artifacts,
            name="casefile.json",
            role="derived",
            sha256=_UNKNOWN_SHA256,
            schema="schemas/casefile.schema.json",
            notes=(
                "sha256 preimage excludes hashes.output_sha256 and "
                "hashes.attestation_sha256 to avoid sealing cycles"
            ),
        )
        artifacts = sorted(artifacts, key=_artifacts_sort_key)

        causal_edges = len(existing_output.get("edges", []))
        if not causal_edges:
            causal_edges = len(
                {
                    edge_id
                    for node in sealed_path.nodes
                    for edge_id in node.causal_chain
                }
            )

        casefile = {
            "casefile_version": "1.0",
            "casefile_id": "",
            "created_utc": _created_utc(sealed_path.sealed_at),
            "core_version": self._core_version(),
            "ruleset_id": "ruleset.core.v1",
            "query": str(existing_output.get("input_ref", sealed_path.replay_key)),
            "prompt": (
                f"Forward projection compile for "
                f"{existing_output.get('input_ref', sealed_path.scenario.label)}"
            ),
            "hashes": {
                "manifest_sha256": self._manifest_sha256(),
                "bundle_sha256": bundle_sha256,
                "world_sha256": world_model_sha256,
                "output_sha256": output_sha256,
                "attestation_sha256": attestation_sha256,
            },
            "ledger_dir": ledger_dir_rel,
            "summary": {
                "entities": len(existing_output.get("entities", [])),
                "events": len(existing_output.get("events", [])),
                "unknowns": len(sealed_path.unknowns),
                "conflicts": len(world_model_obj.get("conflicts", [])),
                "verification_status": _verification_status(sealed_path),
                "constraint_violations": len(
                    existing_output.get("constraint_report", {}).get("violations", [])
                ),
                "causal_edges": causal_edges,
            },
            "artifacts": artifacts,
            "receipts_summary": {
                "evidence_ref_count": 0,
                "proof_count": 0,
                "finding_count": 0,
            },
        }

        casefile["casefile_id"] = "case:" + sha256_bytes(
            dumps_canonical(_casefile_for_id_hash(casefile))
        )
        casefile_sha256 = sha256_bytes(
            dumps_canonical(_casefile_for_artifact_hash(casefile))
        )
        for artifact in casefile["artifacts"]:
            if artifact["name"] == "casefile.json":
                artifact["sha256"] = casefile_sha256
                break
        casefile["artifacts"] = sorted(casefile["artifacts"], key=_artifacts_sort_key)
        validate(casefile, "schemas/casefile.schema.json")
        return casefile

    def _build_ledger_entry(
        self,
        *,
        sealed_path: SealedPath,
        sealed_path_sha256: str,
        forward_attestation_sha256: str,
    ) -> dict:
        return {
            "schema_version": "1.0",
            "artifact": "sealed_path",
            "path_id": sealed_path.path_id,
            "seal_sha256": sealed_path.seal_sha256,
            "sealed_at": _created_utc(sealed_path.sealed_at),
            "scenario_id": sealed_path.scenario.scenario_id,
            "scenario_label": sealed_path.scenario.label,
            "probability": sealed_path.scenario.probability,
            "verification_status": _verification_status(sealed_path),
            "replay_key": sealed_path.replay_key,
            "artifacts": [
                {
                    "name": "sealed_path.json",
                    "role": "sealed",
                    "sha256": sealed_path_sha256,
                },
                {
                    "name": "forward_attestation.sha256",
                    "role": "sealed",
                    "sha256": forward_attestation_sha256,
                },
            ],
            "metadata": {
                "domain": sealed_path.domain,
                "node_count": len(sealed_path.nodes),
                "unknown_count": len(sealed_path.unknowns),
                "invalidation_count": len(sealed_path.invalidations),
            },
        }

    def _core_version(self) -> str:
        pyproject_path = self.repo_root / "pyproject.toml"
        if not pyproject_path.exists():
            return "0.0.0"
        with pyproject_path.open("rb") as handle:
            parsed = tomllib.load(handle)
        return str(parsed.get("project", {}).get("version", "0.0.0"))

    def _manifest_sha256(self) -> str:
        manifest_path = self.repo_root / "MANIFEST.sha256"
        if not manifest_path.exists():
            return _UNKNOWN_SHA256
        return sha256_bytes(manifest_path.read_bytes())

    def _read_existing_output(self) -> dict:
        output_path = self.output_dir / "output.json"
        if not output_path.exists():
            return {}
        try:
            return json.loads(output_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}


def _sample_sealed_path() -> SealedPath:
    import core.world.forward_projection as forward_projection_module

    seed_timestamp = "2026-03-19T09:29:59Z"
    fixed_dt = datetime.fromisoformat(seed_timestamp.replace("Z", "+00:00"))
    original_datetime = forward_projection_module.datetime
    original_time = forward_projection_module.time.time

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return fixed_dt.replace(tzinfo=None)
            return fixed_dt.astimezone(tz)

        @classmethod
        def fromtimestamp(cls, timestamp, tz=None):
            return original_datetime.fromtimestamp(timestamp, tz=tz)

    forward_projection_module.datetime = FixedDateTime
    forward_projection_module.time.time = lambda: fixed_dt.timestamp()
    try:
        world_model = MarketWorldModelBuilder.build(
            symbol="DJI",
            last_close=46225.15,
            day_change_pts=-768.11,
            vix=25.09,
            futures_pts=-77.0,
            commodity_price=113.0,
            commodity_unit="USD/bbl",
            scenarios=[
                {
                    "scenario_id": "scen:B:bounce",
                    "label": "Dead Cat Bounce",
                    "probability": 0.40,
                    "trigger": "Oversold + VIX exhaustion + shallow futures",
                    "invalidations": [],
                    "target_value": 46600.0,
                }
            ],
            unknowns=[],
            invalidations=[],
            timestamp=seed_timestamp,
        )
        projector = ForwardProjection(
            world_model=world_model,
            horizon_seconds=86400,
            domain="market_realtime",
            seed_timestamp=seed_timestamp,
        )
        return projector.seal_optimal_path(projector.project())
    finally:
        forward_projection_module.datetime = original_datetime
        forward_projection_module.time.time = original_time


def _run_self_test() -> None:
    output_dir = _repo_root() / "outputs" / "path_compiler_self_test"
    compiler = PathCompiler(output_dir=output_dir)
    result = compiler.compile(_sample_sealed_path())
    required_files = (
        output_dir / "sealed_path.json",
        output_dir / "forward_attestation.sha256",
        output_dir / "replay_manifest.json",
        output_dir / "casefile.json",
    )
    if result["verified"] and all(path.exists() for path in required_files):
        print("PASS")
        return
    print("FAIL")


if __name__ == "__main__":
    _run_self_test()

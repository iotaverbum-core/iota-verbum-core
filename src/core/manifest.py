import json
from pathlib import Path

from core.attestation import sha256_text, sha256_bytes


def load_manifest(path: Path) -> tuple[dict, str]:
    raw = path.read_text(encoding="utf-8")
    normalized = raw.replace("\r\n", "\n").replace("\r", "\n")
    manifest_sha256 = sha256_text(normalized)
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("manifest must be a JSON object")
    records = data.get("records") if "records" in data else data
    if not isinstance(records, dict):
        raise ValueError("manifest must map refs to entries")
    return records, manifest_sha256


def resolve_input(ref: str, manifest_path: Path) -> dict:
    records, manifest_sha256 = load_manifest(manifest_path)
    if ref not in records:
        raise ValueError(f"ref not found in manifest: {ref}")
    entry = records[ref]
    file_path = manifest_path.parent / entry["file"]
    data_bytes = file_path.read_bytes()
    expected_sha = entry.get("sha256")
    actual_sha = sha256_bytes(data_bytes)
    if expected_sha and expected_sha != actual_sha:
        raise ValueError("manifest sha256 mismatch for input file")
    return {
        "ref": ref,
        "entry": entry,
        "file_path": file_path,
        "file_rel": entry["file"],
        "manifest_sha256": manifest_sha256,
        "data_bytes": data_bytes,
    }

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from core.determinism.hashing import sha256_bytes

_VOLATILE_KEYS = {
    "timestamp",
    "timestamps",
    "runtime",
    "runtime_metadata",
    "generated_at",
    "created_at",
    "updated_at",
    "run_id",
    "session_id",
    "uuid",
    "random_id",
    "nonce",
}


def _normalize(value: Any) -> Any:
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for key in sorted(value):
            key_text = str(key)
            if key_text.lower() in _VOLATILE_KEYS:
                continue
            normalized[key_text] = _normalize(value[key])
        return normalized

    if isinstance(value, list):
        normalized_items = [_normalize(item) for item in value]
        return sorted(
            normalized_items,
            key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")),
        )

    return value


def _file_payload(path: Path) -> dict[str, Any]:
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        return {"kind": "json", "value": _normalize(data)}

    return {"kind": "bytes", "value": sha256_bytes(path.read_bytes())}


def _build_hash_input(root: Path) -> dict[str, Any]:
    if root.is_file():
        if root.suffix.lower() == ".json":
            data = json.loads(root.read_text(encoding="utf-8"))
            return {"files": [{"path": root.name, "payload": {"kind": "json", "value": _normalize(data)}}]}
        return {"files": [{"path": root.name, "payload": {"kind": "bytes", "value": sha256_bytes(root.read_bytes())}}]}

    paths = [path for path in root.rglob("*") if path.is_file()]
    files = []
    for path in sorted(paths):
        rel_path = path.relative_to(root).as_posix()
        files.append({"path": rel_path, "payload": _file_payload(path)})
    return {"files": files}


def compute_manifest_sha256(target: str | Path | None = None) -> str:
    repo_root = Path(__file__).resolve().parents[3]
    manifest_target = Path(target) if target is not None else repo_root / "MANIFEST.sha256"
    if not manifest_target.is_absolute():
        manifest_target = (repo_root / manifest_target).resolve()

    if target is None:
        return sha256_bytes(manifest_target.read_bytes())

    hash_input = _build_hash_input(manifest_target)
    serialized = json.dumps(hash_input, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256_bytes(serialized.encode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", nargs="?", help="file or directory to hash")
    args = parser.parse_args()
    print(compute_manifest_sha256(args.target))


if __name__ == "__main__":
    main()

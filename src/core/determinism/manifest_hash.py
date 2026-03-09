from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from core.determinism.hashing import sha256_bytes

_VOLATILE_FIELDS = {
    "timestamp",
    "created_at",
    "updated_at",
    "runtime",
    "duration",
    "uuid",
    "request_id",
    "trace_id",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _resolve_target(target: str | Path | None) -> Path:
    if target is None:
        return _repo_root() / "MANIFEST.sha256"
    path = Path(target)
    if path.is_absolute():
        return path
    return path.resolve()


def canonical_json(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _normalize_json(value: Any) -> Any:
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for key in sorted(value.keys(), key=lambda item: str(item)):
            key_text = str(key)
            if key_text in _VOLATILE_FIELDS:
                continue
            normalized[key_text] = _normalize_json(value[key])
        return normalized

    if isinstance(value, list):
        items = [_normalize_json(item) for item in value]
        return sorted(items, key=lambda item: canonical_json(item))

    return value


def _json_payload_sha256(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    normalized = _normalize_json(data)
    return sha256_bytes(canonical_json(normalized))


def _iter_directory_files(path: Path) -> list[Path]:
    return sorted(item for item in path.rglob("*") if item.is_file())


def _path_payload_sha256(path: Path) -> str:
    if path.suffix.lower() == ".json":
        return _json_payload_sha256(path)
    return sha256_bytes(path.read_bytes())


def compute_manifest_sha256() -> str:
    manifest_path = _resolve_target(None)
    return sha256_bytes(manifest_path.read_bytes())


def compute_target_sha256(target: str | Path) -> str:
    target_path = _resolve_target(target)

    if target_path.is_file():
        return _path_payload_sha256(target_path)

    if target_path.is_dir():
        entries: list[dict[str, str]] = []
        for file_path in _iter_directory_files(target_path):
            entries.append(
                {
                    "path": file_path.relative_to(target_path).as_posix(),
                    "sha256": _path_payload_sha256(file_path),
                }
            )
        return sha256_bytes(canonical_json(entries))

    raise ValueError("target must be an existing file or directory")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", nargs="?", help="optional file or directory path")
    args = parser.parse_args()

    if args.target is None:
        print(compute_manifest_sha256())
        return

    print(compute_target_sha256(args.target))


if __name__ == "__main__":
    main()

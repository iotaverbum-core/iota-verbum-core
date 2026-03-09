from __future__ import annotations

import argparse
from pathlib import Path

from core.determinism.hashing import sha256_bytes


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _resolve_target(target: str | Path | None) -> Path:
    if target is None:
        return _repo_root() / "MANIFEST.sha256"
    path = Path(target)
    if path.is_absolute():
        return path
    return path.resolve()


def compute_manifest_sha256() -> str:
    manifest_path = _resolve_target(None)
    return sha256_bytes(manifest_path.read_bytes())


def compute_target_sha256(target: str | Path) -> str:
    target_path = _resolve_target(target)
    if target_path.is_dir():
        raise ValueError("target must be a file path")
    return sha256_bytes(target_path.read_bytes())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", nargs="?", help="optional file path to hash")
    args = parser.parse_args()

    if args.target is None:
        print(compute_manifest_sha256())
        return

    print(compute_target_sha256(args.target))


if __name__ == "__main__":
    main()

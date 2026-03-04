from __future__ import annotations

from pathlib import Path

from core.determinism.hashing import sha256_bytes


def compute_manifest_sha256() -> str:
    repo_root = Path(__file__).resolve().parents[3]
    manifest_path = repo_root / "MANIFEST.sha256"
    return sha256_bytes(manifest_path.read_bytes())


def main() -> None:
    print(compute_manifest_sha256())


if __name__ == "__main__":
    main()

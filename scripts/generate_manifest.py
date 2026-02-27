import argparse
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "MANIFEST.sha256"

INCLUDE_GLOBS = [
    "pyproject.toml",
    "requirements.lock",
    "src/**/*.py",
    "schemas/**/*",
    "data/credit/**/*",
    "data/clinical/**/*",
    "data/scripture/esv_sample/**/*",
    "tests/**/*.py",
    "tests/golden/**/*",
    "scripts/**/*.py",
    "scripts/**/*.sh",
    "scripts/**/*.ps1",
    ".github/workflows/*.yml",
    "README.md",
    "LICENSE",
    "docs/**/*.md",
    ".pre-commit-config.yaml",
]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _iter_files():
    files = set()
    for pattern in INCLUDE_GLOBS:
        for path in ROOT.glob(pattern):
            if path.is_file():
                files.add(path)
    return sorted(files, key=lambda p: p.as_posix())


def build_manifest_text() -> str:
    lines = []
    for path in _iter_files():
        rel = path.relative_to(ROOT).as_posix()
        if rel == "MANIFEST.sha256":
            continue
        lines.append(f"{_sha256(path)}  {rel}")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true", help="verify MANIFEST.sha256 matches")
    args = parser.parse_args()

    manifest_text = build_manifest_text()

    if args.verify:
        if not MANIFEST_PATH.exists():
            raise SystemExit("MANIFEST.sha256 missing; run without --verify to generate.")
        existing = MANIFEST_PATH.read_text(encoding="utf-8")
        if existing != manifest_text:
            raise SystemExit("MANIFEST.sha256 does not match generated content.")
        return

    MANIFEST_PATH.write_text(manifest_text, encoding="utf-8")


if __name__ == "__main__":
    main()

import argparse
import hashlib
import subprocess
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
    "data/legal_contract_sample/**/*",
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


def _git_ls_files() -> list[str]:
    output = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    return [path for path in output.decode("utf-8").split("\0") if path]


def _read_index_bytes(path: str) -> bytes:
    return subprocess.check_output(["git", "show", f":{path}"], cwd=ROOT)


def _sha256(path: str) -> str:
    return hashlib.sha256(_read_index_bytes(path)).hexdigest()


def _iter_files() -> list[str]:
    tracked = set(_git_ls_files())
    files = set()
    for pattern in INCLUDE_GLOBS:
        for path in ROOT.glob(pattern):
            if path.is_file():
                rel = path.relative_to(ROOT).as_posix()
                if rel in tracked and rel != "MANIFEST.sha256":
                    files.add(rel)
    return sorted(files)


def build_manifest_text() -> str:
    lines = []
    for path in _iter_files():
        lines.append(f"{_sha256(path)}  {path}")
    return "\n".join(lines) + "\n"


def _first_difference(existing: str, expected: str) -> tuple[int, str, str, str]:
    existing_lines = existing.splitlines()
    expected_lines = expected.splitlines()
    max_len = max(len(existing_lines), len(expected_lines))
    for idx in range(max_len):
        actual_line = existing_lines[idx] if idx < len(existing_lines) else "<missing>"
        expected_line = (
            expected_lines[idx] if idx < len(expected_lines) else "<missing>"
        )
        if actual_line != expected_line:
            path = (
                expected_line.split("  ", 1)[1]
                if "  " in expected_line
                else "<missing>"
            )
            if path == "<missing>" and "  " in actual_line:
                path = actual_line.split("  ", 1)[1]
            return idx + 1, expected_line, actual_line, path
    return 0, "", "", ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--verify", action="store_true", help="verify MANIFEST.sha256 matches"
    )
    args = parser.parse_args()

    manifest_text = build_manifest_text()

    if args.verify:
        if not MANIFEST_PATH.exists():
            raise SystemExit(
                "MANIFEST.sha256 missing; run without --verify to generate."
            )
        existing = MANIFEST_PATH.read_bytes().decode("utf-8")
        if existing != manifest_text:
            line_no, expected_line, actual_line, path = _first_difference(
                existing, manifest_text
            )
            raise SystemExit(
                "MANIFEST.sha256 does not match generated content.\n"
                f"first differing line: {line_no}\n"
                f"path: {path}\n"
                f"expected: {expected_line}\n"
                f"actual:   {actual_line}"
            )
        return

    MANIFEST_PATH.write_bytes(manifest_text.encode("utf-8"))


if __name__ == "__main__":
    main()

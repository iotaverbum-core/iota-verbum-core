import subprocess
import sys
from pathlib import Path

from core.determinism.hashing import sha256_bytes
from core.determinism.manifest_hash import compute_manifest_sha256


def test_compute_manifest_sha256_matches_manifest_bytes():
    expected = sha256_bytes(Path("MANIFEST.sha256").read_bytes())

    assert compute_manifest_sha256() == expected


def test_manifest_hash_script_prints_identical_hash_across_consecutive_runs():
    first = subprocess.run(
        [sys.executable, "scripts/manifest_hash.py"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    second = subprocess.run(
        [sys.executable, "scripts/manifest_hash.py"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    assert first == second
    assert len(first) == 64
    assert first == first.lower()
    assert all(char in "0123456789abcdef" for char in first)


def test_manifest_hash_script_hashes_requested_file(tmp_path: Path):
    casefile = tmp_path / "casefile.json"
    casefile.write_text('{"z":1,"a":2}', encoding="utf-8")

    first = subprocess.run(
        [sys.executable, "scripts/manifest_hash.py", str(casefile)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    second = subprocess.run(
        [sys.executable, "scripts/manifest_hash.py", str(casefile)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    assert first == second
    assert first == sha256_bytes(casefile.read_bytes())

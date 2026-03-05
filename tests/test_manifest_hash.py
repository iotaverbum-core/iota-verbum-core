import subprocess
import sys
from pathlib import Path

from core.determinism.hashing import sha256_bytes
from core.determinism.manifest_hash import compute_manifest_sha256


def test_compute_manifest_sha256_matches_manifest_bytes():
    expected = sha256_bytes(Path("MANIFEST.sha256").read_bytes())

    assert compute_manifest_sha256() == expected


def test_manifest_hash_script_prints_lowercase_hex():
    completed = subprocess.run(
        [sys.executable, "scripts/manifest_hash.py"],
        check=True,
        capture_output=True,
        text=True,
    )
    output = completed.stdout.strip()

    assert len(output) == 64
    assert output == output.lower()
    assert all(char in "0123456789abcdef" for char in output)

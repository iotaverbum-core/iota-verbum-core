import json
import subprocess
import sys
from pathlib import Path

from core.determinism.hashing import sha256_bytes
from core.determinism.manifest_hash import canonical_json, compute_manifest_sha256


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


def test_manifest_hash_script_hashes_requested_json_file_deterministically(
    tmp_path: Path,
):
    casefile = tmp_path / "casefile.json"
    casefile.write_text(
        json.dumps(
            {
                "items": [
                    {"value": 2, "timestamp": "2026-01-01"},
                    {"value": 1, "uuid": "abc"},
                ],
                "runtime": {"trace_id": "x"},
            }
        ),
        encoding="utf-8",
    )

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


def test_manifest_hash_script_resolves_relative_target_from_cwd(tmp_path: Path):
    casefile = tmp_path / "casefile.json"
    casefile.write_text('{"z":1,"a":2}', encoding="utf-8")
    script_path = Path("scripts/manifest_hash.py").resolve()

    output = subprocess.run(
        [sys.executable, str(script_path), "casefile.json"],
        check=True,
        capture_output=True,
        text=True,
        cwd=tmp_path,
    ).stdout.strip()

    assert output == sha256_bytes(canonical_json({"a": 2, "z": 1}))


def test_manifest_hash_directory_mode_is_deterministic(tmp_path: Path):
    left = tmp_path / "b.json"
    right = tmp_path / "a.json"
    left.write_text(
        '{"events":[{"id":2},{"id":1}],"updated_at":"now"}',
        encoding="utf-8",
    )
    right.write_text(
        '{"request_id":"x","events":[{"id":1},{"id":2}]}',
        encoding="utf-8",
    )

    first = subprocess.run(
        [sys.executable, "scripts/manifest_hash.py", str(tmp_path)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    second = subprocess.run(
        [sys.executable, "scripts/manifest_hash.py", str(tmp_path)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    assert first == second

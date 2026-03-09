import json
import subprocess
import sys
from pathlib import Path

from core.determinism.hashing import sha256_bytes
from core.determinism.manifest_hash import compute_manifest_sha256


def test_compute_manifest_sha256_is_deterministic_for_manifest_file():
    expected = sha256_bytes(Path("MANIFEST.sha256").read_bytes())
    first = compute_manifest_sha256()
    second = compute_manifest_sha256()

    assert first == expected
    assert first == second


def test_compute_manifest_sha256_normalizes_json_and_volatile_fields(tmp_path: Path):
    (tmp_path / "casefile_b.json").write_text(
        json.dumps(
            {
                "items": [
                    {"name": "beta", "timestamp": "2026-01-01T00:00:00Z"},
                    {"name": "alpha", "uuid": "2f858f6a-99e6-4f89-a0c4-0b495de09c8d"},
                ],
                "generated_at": "2026-01-02T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "casefile_a.json").write_text(
        json.dumps(
            {
                "items": [
                    {"uuid": "5f7ec1c5-0d52-457d-92af-1ea4f4d5da53", "name": "alpha"},
                    {"timestamp": "2025-01-01T00:00:00Z", "name": "beta"},
                ],
                "generated_at": "2025-06-01T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )

    first = compute_manifest_sha256(tmp_path)
    second = compute_manifest_sha256(tmp_path)

    assert first == second


def test_manifest_hash_script_prints_identical_hash_across_consecutive_runs(tmp_path: Path):
    casefile = tmp_path / "casefile.json"
    casefile.write_text(
        json.dumps(
            {
                "events": [{"id": 2}, {"id": 1}],
                "runtime": {"timestamp": "2026-01-01T00:00:00Z"},
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
    assert len(first) == 64
    assert first == first.lower()
    assert all(char in "0123456789abcdef" for char in first)

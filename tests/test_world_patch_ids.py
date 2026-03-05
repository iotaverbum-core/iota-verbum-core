import json
from pathlib import Path

from core.reasoning.world_patch import load_world_patch

FIXTURES = Path("tests/fixtures")


def _fixture_patch() -> dict:
    return json.loads(
        (FIXTURES / "world_patch_example.json").read_text(encoding="utf-8")
    )


def test_world_patch_ids_are_stable_and_canonical(tmp_path: Path):
    patch_obj = _fixture_patch()
    patch_path = tmp_path / "patch.json"
    patch_path.write_text(
        json.dumps(patch_obj, indent=2),
        encoding="utf-8",
        newline="\n",
    )

    first_obj, first_bytes, first_sha = load_world_patch(str(patch_path))
    second_obj, second_bytes, second_sha = load_world_patch(str(patch_path))

    assert first_obj == second_obj
    assert first_bytes == second_bytes
    assert first_sha == second_sha
    assert first_obj["patch_id"] == f"patch:{first_sha}"
    assert all(op["receipts"]["patch_sha256"] == first_sha for op in first_obj["ops"])
    assert all(op["op_id"].startswith("op:") for op in first_obj["ops"])


def test_world_patch_expected_id_fixture_matches_current_logic(tmp_path: Path):
    patch_obj = _fixture_patch()
    patch_path = tmp_path / "patch.json"
    patch_path.write_text(
        json.dumps(patch_obj, separators=(",", ":")),
        encoding="utf-8",
        newline="\n",
    )
    final_patch, _final_bytes, patch_sha = load_world_patch(str(patch_path))
    expected = (
        (FIXTURES / "world_patch_expected_id.txt").read_text(encoding="utf-8").strip()
    )
    assert expected == final_patch["patch_id"] == f"patch:{patch_sha}"

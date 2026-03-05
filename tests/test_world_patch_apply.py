import json
from pathlib import Path

import pytest

from core.reasoning.world_patch import apply_world_patch, load_world_patch

FIXTURES = Path("tests/fixtures")


def _base_world_model() -> dict:
    return json.loads(
        (FIXTURES / "counterfactual_base_output.json").read_text(encoding="utf-8")
    )["world_model"]


def _load_patch_obj(tmp_path: Path, patch_obj: dict) -> dict:
    patch_path = tmp_path / "patch.json"
    patch_path.write_text(
        json.dumps(patch_obj, indent=2),
        encoding="utf-8",
        newline="\n",
    )
    loaded, _bytes, _sha = load_world_patch(str(patch_path))
    return loaded


def test_apply_update_event_allows_only_expected_fields(tmp_path: Path):
    patch_obj = {
        "version": "1.0",
        "patch_id": "",
        "created_utc": "2026-03-05T00:00:00Z",
        "base_ref": {"kind": "output_json", "value": "__BASE_OUTPUT_JSON__"},
        "ops": [
            {
                "op_id": "",
                "op": "UPDATE_EVENT",
                "target": {
                    "event_id": "event:"
                    + "3333333333333333333333333333333333333333333333333333333333333333"
                },
                "payload": {
                    "time": {"kind": "date", "value": "2026-03-03"},
                    "actors": ["secops"],
                },
                "receipts": {"patch_sha256": "", "evidence_refs": []},
            }
        ],
    }
    patched = apply_world_patch(
        _base_world_model(), _load_patch_obj(tmp_path, patch_obj)
    )
    event = next(
        item for item in patched["events"] if item["event_id"] == "event:" + ("3" * 64)
    )
    assert event["time"] == {"kind": "date", "value": "2026-03-03"}
    assert event["actors"] == ["secops"]


def test_apply_remove_event_removes_relations_referencing_event(tmp_path: Path):
    world = _base_world_model()
    world["relations"] = [
        {
            "from_id": "event:" + ("1" * 64),
            "to_id": "event:" + ("3" * 64),
            "type": "before",
            "derived": True,
            "proof": [
                {
                    "rule": "fixture",
                    "a": "event:" + ("1" * 64),
                    "b": "event:" + ("3" * 64),
                }
            ],
        }
    ]
    patch_obj = {
        "version": "1.0",
        "patch_id": "",
        "created_utc": "2026-03-05T00:00:00Z",
        "base_ref": {"kind": "output_json", "value": "__BASE_OUTPUT_JSON__"},
        "ops": [
            {
                "op_id": "",
                "op": "REMOVE_EVENT",
                "target": {"event_id": "event:" + ("3" * 64)},
                "receipts": {"patch_sha256": "", "evidence_refs": []},
            }
        ],
    }
    patched = apply_world_patch(world, _load_patch_obj(tmp_path, patch_obj))
    assert all(item["event_id"] != "event:" + ("3" * 64) for item in patched["events"])
    assert patched["relations"] == []


def test_apply_remove_entity_fails_when_referenced(tmp_path: Path):
    patch_obj = {
        "version": "1.0",
        "patch_id": "",
        "created_utc": "2026-03-05T00:00:00Z",
        "base_ref": {"kind": "output_json", "value": "__BASE_OUTPUT_JSON__"},
        "ops": [
            {
                "op_id": "",
                "op": "REMOVE_ENTITY",
                "target": {"entity_id": "entity:" + ("a" * 64)},
                "receipts": {"patch_sha256": "", "evidence_refs": []},
            }
        ],
    }
    with pytest.raises(ValueError, match="REMOVE_ENTITY blocked"):
        apply_world_patch(_base_world_model(), _load_patch_obj(tmp_path, patch_obj))


def test_apply_world_patch_produces_stable_sorting(tmp_path: Path):
    patch_obj = {
        "version": "1.0",
        "patch_id": "",
        "created_utc": "2026-03-05T00:00:00Z",
        "base_ref": {"kind": "output_json", "value": "__BASE_OUTPUT_JSON__"},
        "ops": [
            {
                "op_id": "",
                "op": "ADD_ENTITY",
                "target": {},
                "payload": {
                    "entity_id": "entity:" + ("0" * 64),
                    "type": "Concept",
                    "name": "Alpha",
                    "aliases": ["zeta", "beta"],
                },
                "receipts": {"patch_sha256": "", "evidence_refs": []},
            },
            {
                "op_id": "",
                "op": "ADD_EVENT",
                "target": {},
                "payload": {
                    "event_id": "event:" + ("0" * 64),
                    "type": "Other",
                    "time": {"kind": "date", "value": "2026-02-28"},
                    "actors": [],
                    "objects": [],
                    "action": "added event",
                    "state": None,
                    "evidence": [],
                },
                "receipts": {"patch_sha256": "", "evidence_refs": []},
            },
        ],
    }
    patched = apply_world_patch(
        _base_world_model(), _load_patch_obj(tmp_path, patch_obj)
    )
    assert patched["entities"][0]["entity_id"] == "entity:" + ("0" * 64)
    assert patched["events"][0]["event_id"] == "event:" + ("0" * 64)

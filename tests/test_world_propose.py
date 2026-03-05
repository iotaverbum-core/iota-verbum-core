from pathlib import Path

from core.determinism.canonical_json import dumps_canonical
from proposal.evidence_pack import build_evidence_pack
from proposal.world_propose import (
    propose_world_model,
    propose_world_model_from_artifacts,
)


def test_propose_world_model_is_deterministic_and_sorted(tmp_path: Path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "notes.md").write_text(
        "# Access Policy\n"
        "- 2026-03-01 `API_KEYS` are environment only.\n"
        "- 2026-03-02 `API_KEYS` are never in source.\n"
        "- Rotation policy is mandatory.\n",
        encoding="utf-8",
    )

    pack_obj, _ = build_evidence_pack(
        str(docs_dir),
        root_hint="docs",
        max_chars=400,
        overlap_chars=40,
    )

    first = propose_world_model(pack_obj)
    second = propose_world_model(pack_obj)

    assert dumps_canonical(first) == dumps_canonical(second)
    assert [entity["type"] for entity in first["entities"]] == ["Policy", "Secret"]
    assert [entity["name"] for entity in first["entities"]] == [
        "Access Policy",
        "API_KEYS",
    ]
    assert [event["time"]["kind"] for event in first["events"]] == [
        "date",
        "date",
        "unknown",
    ]
    assert [event["time"].get("value", "") for event in first["events"][:2]] == [
        "2026-03-01",
        "2026-03-02",
    ]
    assert first["events"][0]["state"] == {"API_KEYS": "env-only"}
    assert first["events"][1]["state"] == {"API_KEYS": "never-in-repo"}
    assert first["events"][1]["type"] == "PolicyChange"
    assert first["relations"] == [
        {
            "from_id": first["events"][0]["event_id"],
            "to_id": first["events"][1]["event_id"],
            "type": "before",
            "derived": True,
            "proof": [
                {
                    "rule": "iso_time_order",
                    "a": first["events"][0]["event_id"],
                    "b": first["events"][1]["event_id"],
                }
            ],
        }
    ]
    assert {
        "kind": "missing_time",
        "ref": {"event_id": first["events"][2]["event_id"]},
    } in first["unknowns"]
    missing_actor_unknowns = [
        item for item in first["unknowns"] if item["kind"] == "missing_actor"
    ]
    assert len(missing_actor_unknowns) == 3
    assert first["conflicts"] == [
        {
            "kind": "state_conflict",
            "ref": {
                "entity_id": first["entities"][1]["entity_id"],
                "event_ids": [
                    first["events"][0]["event_id"],
                    first["events"][1]["event_id"],
                ],
                "key": "API_KEYS",
                "values": ["env-only", "never-in-repo"],
            },
            "reason": "API_KEYS has conflicting states: env-only, never-in-repo",
        }
    ]
    assert first["events"][0]["evidence"][0] == {
        "source_id": pack_obj["documents"][0]["doc_id"],
        "chunk_id": pack_obj["chunks"][0]["chunk_id"],
        "offset_start": pack_obj["chunks"][0]["offset_start"],
        "offset_end": pack_obj["chunks"][0]["offset_end"],
        "text_sha256": pack_obj["chunks"][0]["text_sha256"],
    }


def test_propose_world_model_deduplicates_same_event_id_from_multiple_artifacts(
    tmp_path: Path,
):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "notes.md").write_text(
        "# Access Policy\n"
        "- 2026-03-01 `API_KEYS` are environment only.\n",
        encoding="utf-8",
    )

    pack_obj, _ = build_evidence_pack(
        str(docs_dir),
        root_hint="docs",
        max_chars=400,
        overlap_chars=40,
    )
    artifact = {
        "source_id": pack_obj["documents"][0]["doc_id"],
        "chunk_id": pack_obj["chunks"][0]["chunk_id"],
        "offset_start": pack_obj["chunks"][0]["offset_start"],
        "offset_end": pack_obj["chunks"][0]["offset_end"],
        "text": pack_obj["chunks"][0]["text"],
        "text_sha256": pack_obj["chunks"][0]["text_sha256"],
    }

    world = propose_world_model_from_artifacts(pack_obj, [artifact, artifact])

    assert len(world["events"]) == 1
    assert len(world["events"][0]["evidence"]) == 1
